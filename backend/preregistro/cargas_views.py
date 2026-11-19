"""Flujo de cargas académicas."""
import logging
import csv
from io import StringIO
import requests as http
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Aspirante, CargaAcademica, CargaAcademicaMateria, Materia, Inscripcion, PeriodoInscripcion
from . import camunda
from .admin_views import CoordinacionRolePermission
from .roles import es_gestion_academica

from io import BytesIO
from .seguridad import celda_segura
from .views import (
    _iniciar_carga_en_camunda,
    _completar_tarea_carga,
    _xlsx_response,
    _pdf_response,
    _registrar_seguimiento,
)
from .inscripciones_views import PeriodoInscripcionView

logger = logging.getLogger(__name__)


FILTRO_DOCENTES_CARGA = Q(rol__iexact='docente') | Q(rol__iexact='investigador') | Q(rol__iexact='director')


class CargaAcademicaWorkflowView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _puede_preparar(self, user):
        role = str(getattr(user, 'rol', '')).strip().lower()
        return user.is_superuser or role in (
            'admin', 'administrador', 'coordinacion', 'coordinador',
            'servicios', 'servicios_escolares', 'servicios escolares',
        )

    def _puede_revisar(self, user):
        role = str(getattr(user, 'rol', '')).strip().lower()
        return user.is_superuser or role in (
            'admin', 'administrador', 'servicios', 'servicios_escolares', 'servicios escolares',
        )

    def _validar_materias(self, items):
        if not isinstance(items, list) or not items:
            raise ValueError('Agrega al menos una materia a la carga.')

        filas = []
        materias_ids = set()
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                raise ValueError(f'La materia {index} tiene un formato inválido.')
            try:
                materia = Materia.objects.get(pk=item.get('materia'))
            except (Materia.DoesNotExist, TypeError, ValueError):
                raise ValueError(f'Selecciona una materia válida en la fila {index}.')
            if materia.pk in materias_ids:
                raise ValueError(f'La materia {materia.clave} está repetida en la carga.')
            materias_ids.add(materia.pk)

            docente = None
            docente_id = item.get('docente')
            if docente_id:
                try:
                    docente = Aspirante.objects.filter(FILTRO_DOCENTES_CARGA).get(pk=docente_id, is_staff=False)
                except (Aspirante.DoesNotExist, TypeError, ValueError):
                    raise ValueError(f'Selecciona un docente válido en la fila {index}.')
            horario = str(item.get('horario', materia.horario) or '').strip()
            salon = str(item.get('salon', materia.salon) or '')
            modalidad = str(item.get('modalidad', 'presencial') or '')
            try:
                capacidad = int(item.get('capacidad', materia.capacidad))
            except (TypeError, ValueError):
                raise ValueError(f'La capacidad de la fila {index} debe ser un número entero positivo.')
            if capacidad < 1 or capacidad > 32767:
                raise ValueError(f'La capacidad de la fila {index} debe ser un número entre 1 y 32767.')
            if salon not in dict(Materia.SALONES):
                raise ValueError(f'Selecciona un salón válido en la fila {index}.')
            if modalidad not in dict(CargaAcademicaMateria.MODALIDADES):
                raise ValueError(f'Selecciona una modalidad válida en la fila {index}.')

            filas.append({
                'materia': materia,
                'docente': docente,
                'horario': horario,
                'salon': salon,
                'capacidad': capacidad,
                'modalidad': modalidad,
            })
        return filas

    def _serializar(self, carga):
        return {
            'id': carga.id,
            'estado': carga.estado,
            'periodo': carga.periodo,
            'comentario': carga.comentario,
            'camunda_instance_id': carga.camunda_instance_id,
            'created_at': carga.created_at,
            'creador_id': carga.creador_id,
            'creador_nombre': carga.creador.nombre,
            'periodo_inscripcion_id': carga.periodo_inscripcion_id,
            'periodo_inscripcion_nombre': carga.periodo_inscripcion.nombre if carga.periodo_inscripcion else '',
            'materias': [{
                'id': item.id,
                'materia': item.materia_id,
                'clave': item.materia.clave,
                'nombre': item.materia.nombre,
                'creditos': item.materia.creditos,
                'docente': item.docente_id,
                'docente_nombre': item.docente.nombre if item.docente else '',
                'horario': item.horario,
                'salon': item.salon,
                'salon_label': item.get_salon_display(),
                'capacidad': item.capacidad,
                'modalidad': item.modalidad,
                'modalidad_label': item.get_modalidad_display(),
            } for item in carga.materias.select_related('materia', 'docente').order_by('materia__clave')],
        }

    def _guardar_materias(self, carga, filas):
        carga.materias.all().delete()
        CargaAcademicaMateria.objects.bulk_create([
            CargaAcademicaMateria(carga=carga, **fila) for fila in filas
        ])

    def get(self, request):
        if not self._puede_preparar(request.user):
            return Response(
                {'detail': 'No tienes permisos para consultar las cargas académicas.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        role = str(getattr(request.user, 'rol', '')).strip().lower()
        qs = CargaAcademica.objects.select_related('creador', 'periodo_inscripcion').prefetch_related('materias__materia', 'materias__docente')
        if not (
            request.user.is_superuser
            or role in (
                'admin', 'administrador', 'coordinacion', 'coordinador',
                'servicios', 'servicios_escolares', 'servicios escolares',
            )
        ):
            qs = qs.filter(creador=request.user)
        materias = Materia.objects.order_by('clave')
        docentes = Aspirante.objects.filter(FILTRO_DOCENTES_CARGA, is_staff=False, is_active=True).order_by('nombre')
        return Response({
            'cargas': [self._serializar(carga) for carga in qs.order_by('-created_at')],
            'materias_catalogo': [{'id': m.id, 'clave': m.clave, 'nombre': m.nombre, 'creditos': m.creditos, 'horario': m.horario, 'salon': m.salon, 'capacidad': m.capacidad, 'profesor': m.profesor} for m in materias],
            'docentes_catalogo': [{'id': d.id, 'nombre': d.nombre} for d in docentes],
            'docente_propio_id': request.user.id if role in ('docente', 'teacher') else None,
            'salones': [{'id': key, 'nombre': label} for key, label in Materia.SALONES],
            'modalidades': [{'id': key, 'nombre': label} for key, label in CargaAcademicaMateria.MODALIDADES],
            'periodos_inscripcion': [
                PeriodoInscripcionView.serializar(periodo)
                for periodo in PeriodoInscripcion.objects.order_by('-apertura')
            ] if request.user.is_superuser or role in (
                'admin', 'administrador', 'servicios', 'servicios_escolares', 'servicios escolares',
            ) else [],
        })
    def post(self, request):
        if not self._puede_preparar(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        periodo = (request.data.get('periodo') or '').strip()
        if not periodo:
            return Response({'detail': 'Indica el periodo escolar antes de enviar la carga.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            filas = self._validar_materias(request.data.get('materias'))
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            carga = CargaAcademica.objects.create(creador=request.user, periodo=periodo, estado='borrador')
            self._guardar_materias(carga, filas)
        return Response(self._serializar(carga), status=status.HTTP_201_CREATED)
    def patch(self, request, pk):
        carga=CargaAcademica.objects.filter(pk=pk).first()
        if not carga: return Response(status=status.HTTP_404_NOT_FOUND)
        estado=request.data.get('estado')
        role = str(getattr(request.user, 'rol', '')).strip().lower()
        es_creador = carga.creador_id == request.user.id

        puede_coordinar = es_gestion_academica(request.user)
        puede_servicios = role in ('servicios', 'servicios_escolares', 'servicios escolares')
        if carga.estado == 'borrador' and (
            es_creador or puede_coordinar or puede_servicios
        ) and ('periodo' in request.data or 'materias' in request.data):
            if not self._puede_preparar(request.user):
                return Response(status=status.HTTP_403_FORBIDDEN)
            periodo = str(request.data.get('periodo', carga.periodo) or '').strip()
            if not periodo:
                return Response({'detail': 'Indica el periodo escolar.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                filas_actuales = [{
                    'materia': item.materia_id,
                    'docente': item.docente_id,
                    'horario': item.horario,
                    'salon': item.salon,
                    'capacidad': item.capacidad,
                    'modalidad': item.modalidad,
                } for item in carga.materias.all()]
                filas = self._validar_materias(request.data.get('materias', filas_actuales))
            except ValueError as exc:
                return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            with transaction.atomic():
                carga.periodo = periodo
                carga.save(update_fields=['periodo', 'updated_at'])
                self._guardar_materias(carga, filas)
            return Response(self._serializar(carga))

        if estado not in dict(CargaAcademica.ESTADOS):
            return Response({'estado':'Estado inválido.'},status=status.HTTP_400_BAD_REQUEST)
        es_envio = carga.estado == 'borrador' and estado == 'en_revision' and (es_creador or puede_coordinar) and self._puede_preparar(request.user)
        es_decision_revision = (
            carga.estado == 'en_revision'
            and estado in ('aprobada', 'rechazada')
            and self._puede_revisar(request.user)
        )
        if es_decision_revision and es_creador:
            return Response(
                {'detail': 'Quien preparó la carga no puede dictaminarla; debe revisarla otra persona de Servicios Escolares.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        es_publicacion = carga.estado == 'aprobada' and estado == 'publicada' and self._puede_revisar(request.user)
        es_reapertura = (
            carga.estado == 'rechazada'
            and estado == 'borrador'
            and (es_creador or puede_coordinar)
            and self._puede_preparar(request.user)
        )
        if not es_envio and not es_decision_revision and not es_publicacion and not es_reapertura:
            return Response(status=status.HTTP_403_FORBIDDEN)
        transiciones = {'borrador': {'en_revision'}, 'en_revision': {'aprobada','rechazada'}, 'aprobada': {'publicada'}, 'rechazada': {'borrador'}}
        if estado != carga.estado and estado not in transiciones.get(carga.estado, set()):
            return Response({'detail': f'No se puede pasar de {carga.estado} a {estado}.'}, status=status.HTTP_400_BAD_REQUEST)
        comentario = str(request.data.get('comentario', '') or '').strip()
        if es_decision_revision and not comentario:
            return Response({'detail': 'Escribe un comentario para justificar la aprobación o el rechazo.'}, status=status.HTTP_400_BAD_REQUEST)
        periodo_publicacion = None
        if es_publicacion:
            periodo_id = request.data.get('periodo_inscripcion')
            try:
                periodo_publicacion = PeriodoInscripcion.objects.get(
                    pk=periodo_id,
                    activo=True,
                    cierre__gte=timezone.now(),
                )
            except (PeriodoInscripcion.DoesNotExist, TypeError, ValueError):
                return Response(
                    {'detail': 'Selecciona un periodo de inscripción habilitado para publicar la carga.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not carga.materias.exists():
                return Response({'detail': 'No se puede publicar una carga sin materias.'}, status=status.HTTP_400_BAD_REQUEST)
            materia_ids = list(carga.materias.values_list('materia_id', flat=True))
            ya_publicadas = CargaAcademicaMateria.objects.filter(
                carga__estado='publicada',
                carga__periodo_inscripcion=periodo_publicacion,
                materia_id__in=materia_ids,
            ).exclude(carga=carga)
            if ya_publicadas.exists():
                claves = list(ya_publicadas.values_list('materia__clave', flat=True).distinct())
                return Response(
                    {'detail': f'Ya existe otra carga publicada con estas materias para {periodo_publicacion.nombre}: {", ".join(claves)}.'},
                    status=status.HTTP_409_CONFLICT,
                )
        camunda_result = {'conectado': False, 'detalle': 'Transición local; no hay instancia Camunda asociada.'}
        if es_envio:
            detalles = list(carga.materias.select_related('materia', 'docente'))
            if not detalles:
                return Response({'detail': 'Agrega al menos una materia antes de enviar la carga.'}, status=status.HTTP_400_BAD_REQUEST)
            sin_docente = [item.materia.clave for item in detalles if not item.docente_id]
            sin_horario = [item.materia.clave for item in detalles if not item.horario.strip()]
            if sin_docente or sin_horario:
                pendientes = []
                if sin_docente:
                    pendientes.append(f'docente: {", ".join(sin_docente)}')
                if sin_horario:
                    pendientes.append(f'horario: {", ".join(sin_horario)}')
                return Response({'detail': f'Completa los datos requeridos antes de enviar ({"; ".join(pendientes)}).'}, status=status.HTTP_400_BAD_REQUEST)
            if camunda.rest_url():
                try:
                    carga.camunda_instance_id = _iniciar_carga_en_camunda(carga)
                    carga.save(update_fields=['camunda_instance_id', 'updated_at'])
                except http.RequestException:
                    logger.exception('No fue posible iniciar el proceso Camunda para la carga %s', carga.pk)
                    return Response({'detail': 'El motor de procesos no está disponible. Intenta nuevamente en unos minutos.'}, status=status.HTTP_502_BAD_GATEWAY)
            _registrar_seguimiento(request.user, 'en_revision', f'Carga académica {carga.periodo} enviada a revisión.', 'Carga académica', notificar=True, asunto='Carga académica en revisión')
        try:
            if not es_envio and carga.estado == 'en_revision' and estado in ('aprobada', 'rechazada'):
                camunda_result = _completar_tarea_carga(carga, 'revision', {'aprobada': {'value': estado == 'aprobada', 'type': 'Boolean'}})
            elif not es_envio and carga.estado == 'aprobada' and estado == 'publicada':
                camunda_result = _completar_tarea_carga(carga, 'publicacion', {'publicada': {'value': True, 'type': 'Boolean'}})
        except http.RequestException:
            logger.exception('No fue posible completar la tarea Camunda de la carga %s', carga.pk)
            return Response({'detail': 'No se pudo completar la aprobación en el motor de procesos. Intenta nuevamente en unos minutos.'}, status=status.HTTP_502_BAD_GATEWAY)
        carga.estado = estado
        if es_publicacion:
            carga.periodo_inscripcion = periodo_publicacion
            carga.periodo = periodo_publicacion.nombre
        if es_decision_revision:
            carga.comentario = comentario
        elif 'comentario' in request.data:
            carga.comentario = comentario or carga.comentario
        update_fields = ['estado', 'updated_at']
        if es_publicacion:
            update_fields.extend(['periodo_inscripcion', 'periodo'])
        if es_decision_revision or 'comentario' in request.data:
            update_fields.append('comentario')
        carga.save(update_fields=update_fields)
        if not es_envio:
            detalle = f'Carga académica actualizada a {estado}.'
            if es_decision_revision:
                detalle += f' Comentario de revisión: {comentario}'
            origen = 'Servicios Escolares' if puede_servicios else 'Administración'
            _registrar_seguimiento(
                carga.creador,
                'aceptado' if estado in ('aprobada', 'publicada') else estado,
                detalle,
                origen,
                notificar=True,
                asunto='Actualización de carga académica',
            )
        carga.refresh_from_db()
        response_data = self._serializar(carga)
        response_data['camunda'] = camunda_result
        return Response(response_data)


class GenerarCargaView(APIView):
    permission_classes = [CoordinacionRolePermission]

    def post(self, request):
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        headers = ['Clave del curso', 'Materia', 'Alumno', 'Matrícula', 'Profesor', 'Horario', 'Estado']
        rows = []
        for row in Inscripcion.objects.select_related('materia', 'aspirante').order_by('materia__clave'):
            alumno = row.aspirante
            rows.append([row.materia.clave, row.materia.nombre, alumno.nombre, alumno.matricula or '', row.materia.profesor or 'Por asignar', row.horario or row.materia.horario or 'Por asignar', row.estado])
        formato = request.query_params.get('format', 'xlsx').lower()
        if formato == 'pdf':
            return _pdf_response('Carga académica', f'Generada el {timezone.localtime():%d/%m/%Y %H:%M}', headers, rows, f'carga_academica_{timestamp}.pdf')
        if formato == 'csv':
            output = StringIO(newline='')
            writer = csv.writer(output)
            writer.writerow(headers)
            writer.writerows([[celda_segura(valor) for valor in row] for row in rows])
            return FileResponse(BytesIO(('\ufeff' + output.getvalue()).encode('utf-8')), as_attachment=True, filename=f'carga_academica_{timestamp}.csv', content_type='text/csv; charset=utf-8')
        return _xlsx_response([headers] + rows, f'carga_academica_{timestamp}.xlsx', 'Carga académica SINAC NEXT')
