"""Panel de docentes y endpoints para gestión de calificaciones y cursos."""
import logging
import uuid
from collections import Counter

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
import requests

from .models import (
    Aspirante, CargaAcademicaMateria, EntrevistaVirtual, ExamenEnLinea, Inscripcion, PeriodoInscripcion,
)
from .serializers import (
    CalificacionExamenDocenteSerializer, EntrevistaVirtualSerializer, ExamenEnLineaSerializer,
    InscripcionSerializer, MateriaSerializer,
)
from .views import _registrar_seguimiento
from .seguridad import url_media

logger = logging.getLogger(__name__)

ROLES_DOCENTE = ('docente', 'teacher', 'investigador', 'director')


def _es_docente(user):
    return bool(user and str(getattr(user, 'rol', '')).strip().lower() in ROLES_DOCENTE)


def _asignaciones(docente):
    """Grupos asignados al docente en cargas académicas publicadas."""
    return CargaAcademicaMateria.objects.filter(
        carga__estado='publicada',
        carga__periodo_inscripcion__isnull=False,
        docente=docente,
    ).select_related('materia', 'carga__periodo_inscripcion').order_by(
        '-carga__periodo_inscripcion__apertura', 'materia__clave',
    )


def _inscripciones_docente(docente, asignaciones=None):
    filtro = Q(pk__in=[])
    for asignacion in (asignaciones if asignaciones is not None else _asignaciones(docente)):
        filtro |= Q(materia_id=asignacion.materia_id, periodo_inscripcion_id=asignacion.carga.periodo_inscripcion_id)
    return Inscripcion.objects.filter(filtro)


def _periodo_en_curso():
    """Último periodo cuya inscripción ya abrió: es el que se está impartiendo."""
    return PeriodoInscripcion.objects.filter(apertura__lte=timezone.now()).order_by('-apertura').first()


def _error_calificacion(docente, inscripcion):
    if not _inscripciones_docente(docente).filter(pk=inscripcion.pk).exists():
        return Response({'error': 'Esta inscripción no pertenece a tus grupos asignados.'}, status=status.HTTP_403_FORBIDDEN)
    periodo = _periodo_en_curso()
    if not periodo or inscripcion.periodo_inscripcion_id != periodo.id:
        return Response({'error': 'Solo puedes calificar inscripciones del periodo en curso.'}, status=status.HTTP_409_CONFLICT)
    if inscripcion.validacion_servicios != 'validada':
        return Response({'error': 'La inscripción aún no está validada por Servicios Escolares.'}, status=status.HTTP_409_CONFLICT)
    return None


def _serializar_asignacion(asignacion, inscritos, periodo_en_curso):
    periodo = asignacion.carga.periodo_inscripcion
    data = MateriaSerializer(asignacion.materia).data
    data.update({
        'asignacion_id': asignacion.id,
        'profesor': asignacion.docente.nombre if asignacion.docente else '',
        'horario': asignacion.horario,
        'salon': asignacion.salon,
        'salon_label': asignacion.get_salon_display(),
        'capacidad': asignacion.capacidad,
        'modalidad': asignacion.modalidad,
        'inscritos': inscritos.get((asignacion.materia_id, periodo.id), 0),
        'periodo_inscripcion': periodo.id,
        'periodo_nombre': periodo.nombre,
        'calificable': bool(periodo_en_curso and periodo.id == periodo_en_curso.id),
    })
    return data


def _entrevistas_docente(docente, estudiante_ids):
    # Las entrevistas previas a registrar al docente responsable siguen
    # visibles para los docentes del alumno.
    return EntrevistaVirtual.objects.filter(
        Q(docente=docente) | Q(docente__isnull=True, aspirante_id__in=estudiante_ids)
    ).select_related('aspirante').order_by('-fecha_programada')


def _entrevista_permitida(docente, entrevista):
    if entrevista.docente_id:
        return entrevista.docente_id == docente.id
    return _inscripciones_docente(docente).filter(aspirante_id=entrevista.aspirante_id).exists()


class PanelDocenteView(APIView):
    """Panel del docente: grupos asignados, estudiantes, exámenes y entrevistas."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        docente = request.user
        if not _es_docente(docente):
            return Response({'error': 'No tienes permisos de docente.'}, status=status.HTTP_403_FORBIDDEN)

        asignaciones = list(_asignaciones(docente))
        inscripciones = _inscripciones_docente(docente, asignaciones).select_related(
            'aspirante', 'materia', 'periodo_inscripcion',
        ).order_by('-created_at')
        inscritos = Counter(inscripciones.values_list('materia_id', 'periodo_inscripcion_id'))
        periodo_en_curso = _periodo_en_curso()
        estudiante_ids = set(inscripciones.values_list('aspirante_id', flat=True))
        examenes = ExamenEnLinea.objects.filter(evaluador=docente).exclude(tipo='predoctoral').select_related('aspirante').order_by('-fecha_programada')
        entrevistas = _entrevistas_docente(docente, estudiante_ids)

        return Response({
            'docente': {
                'id': docente.id,
                'nombre': docente.nombre,
                'usuario': docente.usuario,
                'programa': docente.programa,
                'unidad': docente.unidad,
                'profile_photo': url_media(docente.profile_photo),
            },
            'periodo_en_curso': {'id': periodo_en_curso.id, 'nombre': periodo_en_curso.nombre} if periodo_en_curso else None,
            'materias': [_serializar_asignacion(item, inscritos, periodo_en_curso) for item in asignaciones],
            'inscripciones': InscripcionSerializer(inscripciones, many=True).data,
            'examenes': ExamenEnLineaSerializer(examenes, many=True).data,
            'entrevistas': EntrevistaVirtualSerializer(entrevistas, many=True).data,
            'resumen': {
                'total_materias': len(asignaciones),
                'total_estudiantes': len(estudiante_ids),
                'total_inscripciones': inscripciones.count(),
                'inscripciones_aprobadas': inscripciones.filter(estado='aprobada').count(),
                'inscripciones_reprobadas': inscripciones.filter(estado='reprobada').count(),
                'examenes_total': examenes.count(),
                'examenes_programados': examenes.filter(estado='programado').count(),
                'examenes_completados': examenes.filter(estado__in=['aprobado', 'reprobado']).count(),
                'entrevistas_total': entrevistas.count(),
                'entrevistas_programadas': entrevistas.filter(estado='programada').count(),
                'entrevistas_iniciadas': entrevistas.filter(estado='iniciada').count(),
                'entrevistas_completadas': entrevistas.filter(estado='completada').count(),
            }
        })


class DocenteMateriaView(APIView):
    """Estudiantes inscritos en un grupo asignado al docente."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        docente = request.user
        if not _es_docente(docente):
            return Response(status=status.HTTP_403_FORBIDDEN)

        asignaciones = [item for item in _asignaciones(docente) if item.materia_id == pk]
        if not asignaciones:
            return Response(status=status.HTTP_404_NOT_FOUND)

        inscripciones = _inscripciones_docente(docente, asignaciones).select_related('aspirante')
        return Response({
            'materia': MateriaSerializer(asignaciones[0].materia).data,
            'inscripciones': InscripcionSerializer(inscripciones, many=True).data,
            'estadisticas': {
                'total': inscripciones.count(),
                'cursando': inscripciones.filter(estado='cursando').count(),
                'aprobada': inscripciones.filter(estado='aprobada').count(),
                'reprobada': inscripciones.filter(estado='reprobada').count(),
            }
        })


class CalificacionesView(APIView):
    """Permite al docente registrar calificaciones de sus grupos del periodo en curso."""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def _obtener(docente, pk):
        try:
            inscripcion = Inscripcion.objects.select_related('materia').get(pk=pk)
        except (Inscripcion.DoesNotExist, TypeError, ValueError):
            return None, Response(status=status.HTTP_404_NOT_FOUND)
        error = _error_calificacion(docente, inscripcion)
        return (None, error) if error else (inscripcion, None)

    def post(self, request):
        docente = request.user
        if not _es_docente(docente):
            return Response(status=status.HTTP_403_FORBIDDEN)

        inscripcion_id = request.data.get('inscripcion_id')
        calificacion = request.data.get('calificacion')
        parcial = request.data.get('parcial')

        if not inscripcion_id or (calificacion is None and parcial is None):
            return Response(
                {'error': 'Se requiere inscripcion_id y calificacion.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inscripcion, error = self._obtener(docente, inscripcion_id)
        if error:
            return error

        if parcial is not None:
            try:
                numero = int(request.data.get('numero_parcial', 1))
                valor = float(parcial)
            except (TypeError, ValueError):
                return Response({'error': 'La calificación parcial no es válida.'}, status=status.HTTP_400_BAD_REQUEST)
            if numero not in (1, 2, 3):
                return Response({'error': 'El parcial debe ser 1, 2 o 3.'}, status=status.HTTP_400_BAD_REQUEST)
            if not 0 <= valor <= 10:
                return Response({'error': 'La calificación debe estar entre 0 y 10.'}, status=status.HTTP_400_BAD_REQUEST)
            setattr(inscripcion, f'parcial_{numero}', valor)
            # Los parciales no sustituyen la calificación final. La materia
            # permanece cursando hasta que se capture explícitamente la final.
            if inscripcion.calificacion is None:
                inscripcion.estado = 'cursando'
        else:
            try:
                calificacion = float(calificacion)
            except (TypeError, ValueError):
                return Response({'error': 'La calificación final no es válida.'}, status=status.HTTP_400_BAD_REQUEST)
            if not 0 <= calificacion <= 10:
                return Response({'error': 'La calificación debe estar entre 0 y 10.'}, status=status.HTTP_400_BAD_REQUEST)
            inscripcion.calificacion = calificacion
            # Solo la final determina aprobación o reprobación.
            inscripcion.estado = 'reprobada' if calificacion < 7 else 'aprobada'

        inscripcion.save()
        return Response(InscripcionSerializer(inscripcion).data)

    def put(self, request, pk):
        docente = request.user
        if not _es_docente(docente):
            return Response(status=status.HTTP_403_FORBIDDEN)

        inscripcion, error = self._obtener(docente, pk)
        if error:
            return error

        if 'calificacion' in request.data:
            try:
                calificacion = float(request.data['calificacion'])
            except (TypeError, ValueError):
                return Response({'error': 'La calificación final no es válida.'}, status=status.HTTP_400_BAD_REQUEST)
            if not 0 <= calificacion <= 10:
                return Response({'error': 'La calificación debe estar entre 0 y 10.'}, status=status.HTTP_400_BAD_REQUEST)
            inscripcion.calificacion = calificacion
            inscripcion.estado = 'reprobada' if calificacion < 7 else 'aprobada'
            inscripcion.save()
        return Response(InscripcionSerializer(inscripcion).data)


class ActasCalificacionesView(APIView):
    """Genera actas de calificaciones de un grupo asignado al docente."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, materia_id):
        docente = request.user
        if not _es_docente(docente):
            return Response(status=status.HTTP_403_FORBIDDEN)

        asignaciones = [item for item in _asignaciones(docente) if item.materia_id == materia_id]
        if not asignaciones:
            return Response(status=status.HTTP_404_NOT_FOUND)
        asignacion = asignaciones[0]
        inscripciones = _inscripciones_docente(docente, [asignacion]).select_related('aspirante')

        return Response({
            'materia': {
                'clave': asignacion.materia.clave,
                'nombre': asignacion.materia.nombre,
                'profesor': docente.nombre,
                'horario': asignacion.horario,
                'periodo': asignacion.carga.periodo_inscripcion.nombre,
            },
            'calificaciones': [{
                'estudiante': inscripcion.aspirante.nombre,
                'usuario': inscripcion.aspirante.usuario,
                'calificacion': inscripcion.calificacion,
                'estado': inscripcion.estado,
                'programa': inscripcion.aspirante.programa,
            } for inscripcion in inscripciones],
        })


class DocenteExamenView(APIView):
    """Lista los exámenes en línea en los que el docente es evaluador."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        docente = request.user
        if not _es_docente(docente):
            return Response({'error': 'No tienes permisos de docente.'}, status=status.HTTP_403_FORBIDDEN)

        examenes = ExamenEnLinea.objects.filter(evaluador=docente).exclude(tipo='predoctoral').select_related('aspirante').order_by('-fecha_programada')
        return Response({
            'total': examenes.count(),
            'examenes': ExamenEnLineaSerializer(examenes, many=True).data,
            'resumen': {
                'programados': examenes.filter(estado='programado').count(),
                'iniciados': examenes.filter(estado='iniciado').count(),
                'completados': examenes.filter(estado='completado').count(),
                'aprobados': examenes.filter(estado='aprobado').count(),
                'reprobados': examenes.filter(estado='reprobado').count(),
                'cancelados': examenes.filter(estado='cancelado').count(),
            }
        })


class DocenteExamenDetailView(APIView):
    """Consulta y ajusta la calificación de un examen asignado al docente."""
    permission_classes = [permissions.IsAuthenticated]

    def _get_examen(self, request, pk):
        docente = request.user
        if not _es_docente(docente):
            return None, Response(status=status.HTTP_403_FORBIDDEN)

        try:
            examen = ExamenEnLinea.objects.select_related('aspirante').get(pk=pk)
        except ExamenEnLinea.DoesNotExist:
            return None, Response(status=status.HTTP_404_NOT_FOUND)

        if examen.evaluador_id != docente.id:
            return None, Response(
                {'error': 'Solo el docente evaluador asignado puede consultar este examen.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return examen, None

    def get(self, request, pk):
        examen, error = self._get_examen(request, pk)
        if error:
            return error
        return Response(ExamenEnLineaSerializer(examen).data)

    def put(self, request, pk):
        examen, error = self._get_examen(request, pk)
        if error:
            return error

        if not hasattr(request.data, 'keys'):
            return Response(
                {'error': 'El cuerpo de la solicitud debe ser un objeto.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        campos_permitidos = {'calificacion', 'retroalimentacion'}
        campos_no_permitidos = set(request.data.keys()) - campos_permitidos
        if campos_no_permitidos:
            return Response(
                {'error': f'Campos no permitidos: {", ".join(sorted(campos_no_permitidos))}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if 'calificacion' not in request.data:
            return Response(
                {'error': 'Se requiere una calificación para actualizar el resultado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if examen.tipo == 'predoctoral':
            return Response(
                {'error': 'Los exámenes predoctorales se gestionan desde su flujo especializado.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if examen.estado not in {'aprobado', 'reprobado'}:
            return Response(
                {'error': 'Solo se puede ajustar la calificación de un examen ya concluido.'},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = CalificacionExamenDocenteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'La calificación debe ser un número entre 0 y 10, con hasta dos decimales.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        calificacion = serializer.validated_data['calificacion']
        examen.calificacion = calificacion
        examen.estado = 'aprobado' if calificacion >= 8 else 'reprobado'
        update_fields = ['calificacion', 'estado', 'updated_at']
        if 'retroalimentacion' in serializer.validated_data:
            examen.retroalimentacion = serializer.validated_data['retroalimentacion']
            update_fields.append('retroalimentacion')
        examen.save(update_fields=update_fields)
        return Response(ExamenEnLineaSerializer(examen).data)


class DocenteEntrevistaView(APIView):
    """API para gestión de entrevistas virtuales por docentes."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Obtener lista de entrevistas a cargo del docente."""
        try:
            docente = request.user
            if not isinstance(docente, Aspirante) or not _es_docente(docente):
                return Response(
                    {'error': 'Usuario no válido'},
                    status=status.HTTP_403_FORBIDDEN,
                )

            estudiante_ids = set(_inscripciones_docente(docente).values_list('aspirante_id', flat=True))
            entrevistas = _entrevistas_docente(docente, estudiante_ids)
            serializer = EntrevistaVirtualSerializer(entrevistas, many=True)
            return Response({
                'entrevistas': serializer.data,
                'resumen': {
                    'entrevistas_total': entrevistas.count(),
                    'entrevistas_programadas': entrevistas.filter(estado='programada').count(),
                    'entrevistas_iniciadas': entrevistas.filter(estado='iniciada').count(),
                    'entrevistas_completadas': entrevistas.filter(estado='completada').count(),
                }
            })
        except Exception:
            logger.exception('Error al consultar entrevistas del docente %s', request.user.pk)
            return Response(
                {'error': 'No se pudieron cargar las entrevistas del docente.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request):
        """Crear nueva entrevista virtual."""
        try:
            docente = request.user
            if not isinstance(docente, Aspirante) or not _es_docente(docente):
                return Response(
                    {'error': 'Usuario no válido'},
                    status=status.HTTP_403_FORBIDDEN,
                )

            aspirante_id = request.data.get('aspirante_id')
            if not aspirante_id:
                return Response(
                    {'error': 'aspirante_id es requerido'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                aspirante = Aspirante.objects.get(id=aspirante_id)
            except (Aspirante.DoesNotExist, TypeError, ValueError):
                return Response(
                    {'error': 'Aspirante no encontrado'},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if not _inscripciones_docente(docente).filter(aspirante=aspirante).exists():
                return Response(
                    {'error': 'No tienes permiso para crear entrevista para este estudiante'},
                    status=status.HTTP_403_FORBIDDEN,
                )

            jitsi_room_id = str(uuid.uuid4())[:8]
            jitsi_room_link = f"https://meet.jitsi.si/sinac-{jitsi_room_id}"

            entrevista_data = request.data.copy()
            entrevista_data['aspirante'] = aspirante.id
            entrevista_data['estado'] = 'programada'

            serializer = EntrevistaVirtualSerializer(data=entrevista_data)
            if serializer.is_valid():
                # Los datos de la videoconferencia y el docente responsable los
                # define el servidor; son campos de solo lectura del serializer.
                entrevista = serializer.save(
                    aspirante=aspirante,
                    docente=docente,
                    jitsi_room_id=jitsi_room_id,
                    jitsi_room_link=jitsi_room_link,
                )
                base = getattr(settings, 'CAMUNDA_REST_URL', '')
                if base:
                    try:
                        r = requests.post(f'{base}/process-definition/key/sinac_entrevista_v1/start', json={'businessKey': f'entrevista-{entrevista.id}', 'variables': {'entrevistaId': {'value': entrevista.id, 'type': 'Integer'}, 'aspiranteId': {'value': aspirante.id, 'type': 'Integer'}}}, timeout=6)
                        if r.ok:
                            entrevista.camunda_instance_id = r.json().get('id', ''); entrevista.save(update_fields=['camunda_instance_id','updated_at'])
                    except requests.RequestException:
                        pass
                _registrar_seguimiento(aspirante, 'entrevista_programada', f'Entrevista virtual programada para {entrevista.fecha_programada or "fecha pendiente"}.', 'Docencia', notificar=False)
                return Response(EntrevistaVirtualSerializer(entrevista).data, status=status.HTTP_201_CREATED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception('Error al crear entrevista para el docente %s', request.user.pk)
            return Response(
                {'error': 'No se pudo crear la entrevista virtual.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request, pk):
        """Actualizar entrevista existente."""
        try:
            entrevista = EntrevistaVirtual.objects.get(id=pk)
        except EntrevistaVirtual.DoesNotExist:
            return Response(
                {'error': 'Entrevista no encontrada'},
                status=status.HTTP_404_NOT_FOUND,
            )

        docente = request.user
        if not isinstance(docente, Aspirante) or not _es_docente(docente):
            return Response({'error': 'Solo un docente puede actualizar entrevistas.'}, status=status.HTTP_403_FORBIDDEN)
        if not _entrevista_permitida(docente, entrevista):
            return Response(
                {'error': 'Solo el docente responsable puede actualizar esta entrevista.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if 'estado' in request.data:
            estado = request.data.get('estado')
            valid_estados = ['programada', 'iniciada', 'completada', 'cancelada']
            if estado not in valid_estados:
                return Response(
                    {'error': f'Estado inválido. Debe ser uno de: {", ".join(valid_estados)}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            transiciones = {
                'programada': {'programada', 'iniciada', 'cancelada'},
                'iniciada': {'iniciada', 'completada', 'cancelada'},
                'completada': {'completada'},
                'cancelada': {'cancelada'},
            }
            if estado not in transiciones.get(entrevista.estado, set()):
                return Response({'error': f'No se puede pasar de {entrevista.get_estado_display()} a {dict(EntrevistaVirtual.ESTADOS_ENTREVISTA).get(estado, estado)}.'}, status=status.HTTP_400_BAD_REQUEST)
            entrevista.estado = estado
            if estado == 'iniciada' and not entrevista.fecha_inicio:
                entrevista.fecha_inicio = timezone.now()
            if estado in ('completada', 'cancelada') and not entrevista.fecha_fin:
                entrevista.fecha_fin = timezone.now()

        if 'notas_docente' in request.data:
            entrevista.notas_docente = request.data.get('notas_docente')

        if 'retroalimentacion' in request.data:
            entrevista.retroalimentacion = request.data.get('retroalimentacion')

        if 'recording_link' in request.data:
            entrevista.recording_link = request.data.get('recording_link')

        if 'fecha_inicio' in request.data:
            entrevista.fecha_inicio = request.data.get('fecha_inicio')

        if 'fecha_fin' in request.data:
            entrevista.fecha_fin = request.data.get('fecha_fin')

        if not entrevista.docente_id:
            entrevista.docente = docente

        try:
            entrevista.save()
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _registrar_seguimiento(entrevista.aspirante, f'entrevista_{entrevista.estado}', f'La entrevista “{entrevista.titulo}” ahora está {entrevista.get_estado_display().lower()}.', 'Docencia', notificar=False)
        return Response(EntrevistaVirtualSerializer(entrevista).data)


class DocenteEntrevistaDetailView(APIView):
    """API para detalle de entrevista virtual."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        """Obtener detalle de una entrevista."""
        try:
            entrevista = EntrevistaVirtual.objects.get(id=pk)
        except EntrevistaVirtual.DoesNotExist:
            return Response(
                {'error': 'Entrevista no encontrada'},
                status=status.HTTP_404_NOT_FOUND,
            )

        docente = request.user
        if not isinstance(docente, Aspirante) or not _es_docente(docente):
            return Response({'error': 'Solo un docente puede consultar entrevistas.'}, status=status.HTTP_403_FORBIDDEN)
        if not _entrevista_permitida(docente, entrevista):
            return Response(status=status.HTTP_403_FORBIDDEN)

        return Response(EntrevistaVirtualSerializer(entrevista).data)

    def put(self, request, pk):
        return DocenteEntrevistaView().put(request, pk)

    patch = put
