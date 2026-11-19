"""Panel y operaciones de Coordinación Académica."""
import logging
import csv
from random import choice
from decimal import Decimal
from django.conf import settings
from django.db.models import Q
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Aspirante, DocumentoAspirante, SeguimientoSolicitud, Materia
from . import camunda
from .admin_views import CoordinacionRolePermission
from .configuracion_sistema import email_notifications_enabled
from .roles import es_gestion_academica
from .serializers import (
    AspiranteCoordinacionSerializer,
    AspiranteCoordinacionUpdateSerializer,
    MateriaSerializer,
)

from io import TextIOWrapper
from .seguridad import url_media, validar_csv
from .views import (
    _crear_expediente_si_aceptado,
    _xlsx_response,
    _pdf_response,
    _registrar_seguimiento,
    _resolver_preregistro_lida,
)

logger = logging.getLogger(__name__)


class PanelCoordinacionView(APIView):
    permission_classes = [CoordinacionRolePermission]

    def get(self, request):
        aspirantes = Aspirante.objects.filter(is_staff=False).order_by('-created_at')
        solicitudes = aspirantes.filter(rol='aspirante')
        personas = AspiranteCoordinacionSerializer(aspirantes, many=True).data
        for item, persona in zip(personas, aspirantes):
            if persona.rol not in ('docente', 'director', 'investigador'):
                continue
            materias = list(Materia.objects.filter(profesor__iexact=persona.nombre).values('id', 'clave', 'nombre', 'creditos', 'horario'))
            tesistas = list(Aspirante.objects.filter(director_tesis=persona, rol='alumno', is_staff=False).values('id', 'nombre', 'matricula', 'programa', 'proceso_estado')) if persona.rol == 'director' else []
            item.update({'materias': materias, 'total_materias': len(materias), 'horarios': [m['horario'] for m in materias if m['horario']], 'creditos_impartidos': sum(m['creditos'] or 0 for m in materias), 'tesistas': tesistas, 'total_tesistas': len(tesistas)})
        return Response({
            'usuario': {
                'id': request.user.id,
                'nombre': request.user.nombre,
                'usuario': request.user.usuario,
                'correo': request.user.correo,
                'telefono': request.user.telefono,
                'profile_photo': url_media(request.user.profile_photo),
            },
            'resumen': {
                'total': solicitudes.count(),
                'por_revisar': solicitudes.filter(proceso_estado__in=['pendiente', 'iniciado']).count(),
                'revision': solicitudes.filter(proceso_estado='revision').count(),
                'aceptado': solicitudes.filter(proceso_estado='aceptado').count(),
            },
            'aspirantes': personas,
        })


class EstadoAspiranteCoordinacionView(APIView):
    permission_classes = [CoordinacionRolePermission]
    estados_permitidos = {'revision', 'aceptado', 'rechazado'}

    def patch(self, request, pk):
        estado = request.data.get('proceso_estado')
        if estado not in self.estados_permitidos:
            return Response(
                {'proceso_estado': 'El estado debe ser revisión, aceptado o rechazado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            aspirante = Aspirante.objects.get(pk=pk, is_staff=False)
        except Aspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if estado == 'aceptado':
            documentos = list(aspirante.documentos.all())
            if not documentos:
                return Response(
                    {'detail': 'No se puede aceptar al aspirante: aún no ha cargado documentos para revisar.', 'codigo': 'documentos_pendientes'},
                    status=status.HTTP_409_CONFLICT,
                )
            sin_revisar = [documento.get_tipo_display() for documento in documentos if not documento.revisado]
            if sin_revisar:
                return Response(
                    {'detail': f'Debes revisar todos los documentos antes de aceptar al aspirante. Pendientes: {", ".join(sin_revisar)}.', 'codigo': 'documentos_pendientes', 'pendientes': sin_revisar},
                    status=status.HTTP_409_CONFLICT,
                )

        estado_anterior = aspirante.proceso_estado
        aspirante.proceso_estado = estado
        aspirante.save(update_fields=['proceso_estado', 'updated_at'])
        expediente = _crear_expediente_si_aceptado(aspirante)
        if estado == 'revision':
            detalle = 'La solicitud fue marcada en revisión por la Coordinación Académica.'
            asunto = 'Tu solicitud está en revisión'
        elif estado == 'aceptado':
            detalle = 'La solicitud fue aceptada por la Coordinación Académica. Para dar seguimiento a tu inscripción y completar tu alta como alumno, ponte en contacto con Coordinación Académica. Solo Coordinación puede realizar tu alta.'
            asunto = 'Tu solicitud ha sido aceptada'
        else:
            detalle = 'La solicitud fue rechazada. Consulta con la Coordinación Académica para más detalles.'
            asunto = 'Tu solicitud ha sido rechazada'
        if estado != estado_anterior:
            _registrar_seguimiento(aspirante, estado, detalle, 'Coordinación Académica', notificar=True, asunto=asunto)
            _resolver_preregistro_lida(aspirante)
        respuesta = AspiranteCoordinacionSerializer(aspirante).data
        if expediente:
            respuesta['expediente_digital'] = {'id': expediente.id, 'folio': expediente.folio, 'estado': expediente.estado, 'fecha_creacion': expediente.fecha_creacion}
        return Response(respuesta)


class NotificacionMasivaCoordinacionView(APIView):
    permission_classes = [CoordinacionRolePermission]

    grupos_estado = {
        'por-revisar': ['pendiente', 'iniciado'],
        'revision': ['revision'],
        'aceptado': ['aceptado'],
        'rechazado': ['rechazado'],
        'todos': None,
    }
    etiquetas_estado = {
        'pendiente': 'Pendiente',
        'iniciado': 'Iniciado',
        'revision': 'En revisión',
        'aceptado': 'Aceptado',
        'rechazado': 'Rechazado',
    }
    fechas_aviso = (
        ('fecha_examen_admision', 'Examen de admisión'),
        ('fecha_entrevista', 'Entrevista'),
        ('fecha_inicio_curso_propedeutico', 'Inicio del curso propedéutico'),
    )

    def post(self, request):
        grupo = request.data.get('grupo')
        if not isinstance(grupo, str) or grupo not in self.grupos_estado:
            return Response({'grupo': 'Selecciona un grupo de estatus válido.'}, status=status.HTTP_400_BAD_REQUEST)

        mensaje_personalizado = request.data.get('mensaje', '')
        if not isinstance(mensaje_personalizado, str) or len(mensaje_personalizado) > 1000:
            return Response({'mensaje': 'El mensaje debe tener como máximo 1000 caracteres.'}, status=status.HTTP_400_BAD_REQUEST)

        incluir_fechas = request.data.get('incluir_fechas', True)
        if not isinstance(incluir_fechas, bool):
            return Response({'incluir_fechas': 'Indica verdadero o falso.'}, status=status.HTTP_400_BAD_REQUEST)

        ids = request.data.get('ids')
        if ids is not None and (
            not isinstance(ids, list)
            or any(not isinstance(pk, int) or isinstance(pk, bool) for pk in ids)
            or len(ids) != len(set(ids))
        ):
            return Response({'ids': 'La selección de aspirantes no es válida.'}, status=status.HTTP_400_BAD_REQUEST)

        queryset = Aspirante.objects.filter(rol='aspirante', is_staff=False)
        estados = self.grupos_estado[grupo]
        if estados is not None:
            queryset = queryset.filter(proceso_estado__in=estados)
        if ids is not None:
            encontrados = set(queryset.filter(pk__in=ids).values_list('pk', flat=True))
            if encontrados != set(ids):
                return Response(
                    {'ids': 'Uno o más aspirantes ya no pertenecen al grupo seleccionado.'},
                    status=status.HTTP_409_CONFLICT,
                )
            queryset = queryset.filter(pk__in=ids)

        aspirantes = list(queryset.order_by('pk'))
        if not aspirantes:
            return Response({'detail': 'No hay aspirantes para notificar en este grupo.'}, status=status.HTTP_409_CONFLICT)

        fallidos = []
        sin_correo = []
        correos_desactivados = 0
        avisos_internos = 0
        notificaciones_email_activas = email_notifications_enabled()
        enviados = 0
        for aspirante in aspirantes:
            if not aspirante.correo:
                sin_correo.append({'id': aspirante.pk, 'nombre': aspirante.nombre})
                continue

            estado = self.etiquetas_estado.get(aspirante.proceso_estado, aspirante.proceso_estado)
            asunto = f'Actualización de tu solicitud: {estado}'
            partes = [
                f'Hola {aspirante.nombre},',
                '',
                f'Te informamos que el estatus actual de tu solicitud es: {estado}.',
            ]
            if mensaje_personalizado.strip():
                partes.extend(['', mensaje_personalizado.strip()])
            if incluir_fechas:
                fechas = [
                    (etiqueta, getattr(aspirante, campo))
                    for campo, etiqueta in self.fechas_aviso
                    if getattr(aspirante, campo)
                ]
                if fechas:
                    partes.extend(['', 'Fechas registradas en tu expediente:'])
                    partes.extend(
                        f'{etiqueta}: {timezone.localtime(valor).strftime("%d/%m/%Y %H:%M")}'
                        for etiqueta, valor in fechas
                    )
            partes.extend(['', 'Coordinación Académica'])
            contenido = '\n'.join(partes)

            if notificaciones_email_activas:
                try:
                    resultado = send_mail(
                        asunto,
                        contenido,
                        getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'no-reply@sinac.local',
                        [aspirante.correo],
                        fail_silently=False,
                    )
                    if not resultado:
                        raise RuntimeError('El servidor de correo no confirmó el envío.')
                except Exception:
                    logger.warning(
                        'Falló el envío masivo de Coordinación al aspirante id=%s correo=%s',
                        aspirante.pk,
                        aspirante.correo,
                        exc_info=True,
                    )
                    fallidos.append({'id': aspirante.pk, 'nombre': aspirante.nombre})
                    continue
            else:
                correos_desactivados += 1

            SeguimientoSolicitud.objects.create(
                aspirante=aspirante,
                estado=aspirante.proceso_estado,
                detalle=f'Notificación de Coordinación Académica { "enviada" if notificaciones_email_activas else "registrada; correo desactivado"}: {estado}.'[:255],
                origen='Coordinación Académica',
            )
            avisos_internos += 1
            if notificaciones_email_activas:
                enviados += 1

        return Response({
            'total': len(aspirantes),
            'enviados': enviados,
            'avisos_internos': avisos_internos,
            'fallidos': fallidos,
            'sin_correo': sin_correo,
            'omitidos': len(sin_correo),
            'correos_desactivados': correos_desactivados,
        })


class DocumentoRevisionCoordinacionView(APIView):
    permission_classes = [CoordinacionRolePermission]

    def patch(self, request, pk):
        from django.utils import timezone
        try:
            documento = DocumentoAspirante.objects.get(pk=pk, aspirante__is_staff=False)
        except DocumentoAspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        revisado = request.data.get('revisado', True)
        if not isinstance(revisado, bool):
            return Response({'revisado': 'Envía verdadero o falso.'}, status=status.HTTP_400_BAD_REQUEST)
        documento.revisado = revisado
        documento.revisado_en = timezone.now() if revisado else None
        documento.save(update_fields=['revisado', 'revisado_en', 'updated_at'])
        if revisado:
            camunda.completar_tareas('sinac_documentos_v1', 'validar', filtro={'documentoId': documento.pk}, valido=True)
        aspirante = Aspirante.objects.prefetch_related('documentos', 'seguimientos').get(pk=documento.aspirante_id)
        return Response(AspiranteCoordinacionSerializer(aspirante).data)


class AspiranteCoordinacionDetailView(APIView):
    permission_classes = [CoordinacionRolePermission]

    def get_object(self, pk):
        try:
            return Aspirante.objects.prefetch_related('documentos', 'seguimientos').get(pk=pk, is_staff=False)
        except Aspirante.DoesNotExist:
            return None

    def get(self, request, pk):
        aspirante = self.get_object(pk)
        if not aspirante:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(AspiranteCoordinacionSerializer(aspirante).data)

    def patch(self, request, pk):
        aspirante = self.get_object(pk)
        if not aspirante:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = AspiranteCoordinacionUpdateSerializer(aspirante, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        cambios = {campo: valor for campo, valor in serializer.validated_data.items() if getattr(aspirante, campo) != valor}
        serializer.save()
        expediente = _crear_expediente_si_aceptado(aspirante)

        if 'proceso_estado' in cambios:
            detalle_estado = (
                'Tu solicitud fue aceptada. Para dar seguimiento a tu inscripción y completar tu alta como alumno, '
                'ponte en contacto con Coordinación Académica. Solo Coordinación puede realizar tu alta.'
                if aspirante.proceso_estado == 'aceptado'
                else f'Estado actualizado a {aspirante.proceso_estado}.'
            )
            asunto_estado = 'Tu solicitud ha sido aceptada' if aspirante.proceso_estado == 'aceptado' else 'Actualización de tu solicitud'
            _registrar_seguimiento(aspirante, aspirante.proceso_estado, detalle_estado, 'Coordinación Académica', notificar=True, asunto=asunto_estado)
            _resolver_preregistro_lida(aspirante)
        avisos = {
            'fecha_examen_admision': ('Fecha y hora del examen de admisión', 'Fecha de examen de admisión programada'),
            'fecha_entrevista': ('Fecha y hora de entrevista', 'Entrevista programada'),
            'fecha_inicio_curso_propedeutico': ('Inicio del curso propedéutico', 'Curso propedéutico programado'),
        }
        for campo, (texto, asunto) in avisos.items():
            valor = getattr(aspirante, campo)
            if campo in cambios and valor:
                detalle = f'{texto}: {valor.strftime("%d/%m/%Y %H:%M")}.'
                _registrar_seguimiento(aspirante, 'aceptado', detalle, 'Coordinación Académica', notificar=True, asunto=asunto)

        if 'curso_propedeutico_aprobado' in cambios and aspirante.curso_propedeutico_aprobado:
            nota = Decimal(str(aspirante.curso_propedeutico_nota or '0'))
            _registrar_seguimiento(aspirante, 'aceptado', 'Curso propedéutico aprobado. Ya puedes solicitar apoyo.' if nota >= Decimal('8') else 'Curso propedéutico actualizado.', 'Coordinación Académica', notificar=True, asunto='Resultado del curso propedéutico')
        respuesta = AspiranteCoordinacionSerializer(aspirante).data
        if expediente:
            respuesta['expediente_digital'] = {'id': expediente.id, 'folio': expediente.folio, 'estado': expediente.estado, 'fecha_creacion': expediente.fecha_creacion}
        return Response(respuesta)


class MateriasListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        rol = str(getattr(request.user, 'rol', '')).strip().lower()
        puede_consultar = es_gestion_academica(request.user) or rol in {
            'servicios', 'servicios_escolares', 'servicios escolares',
        }
        if not puede_consultar:
            return Response(status=status.HTTP_403_FORBIDDEN)
        materias = Materia.objects.all().order_by('clave')
        return Response([MateriaSerializer(m).data for m in materias])


class CursosUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        rol = str(getattr(request.user, 'rol', '')).strip().lower()
        if rol not in {'servicios', 'servicios_escolares', 'servicios escolares'}:
            return Response({'detail': 'Solo Servicios Escolares puede cargar el catálogo de materias.'}, status=status.HTTP_403_FORBIDDEN)
        archivo = request.FILES.get('file')
        error_archivo = validar_csv(archivo)
        if error_archivo:
            return Response({'file': error_archivo}, status=status.HTTP_400_BAD_REQUEST)
        try:
            wrapper = TextIOWrapper(archivo.file, encoding='utf-8')
            reader = csv.DictReader(wrapper)
        except Exception:
            return Response({'file': 'No se pudo leer el CSV. Asegúrate de usar UTF-8 y cabeceras: clave,nombre,profesor,horario'}, status=status.HTTP_400_BAD_REQUEST)
        count = 0
        for row in reader:
            clave = (row.get('clave') or row.get('Clave') or '').strip()
            nombre = (row.get('nombre') or row.get('Nombre') or '').strip()
            creditos_raw = (row.get('creditos') or row.get('Créditos') or row.get('creditos_materia') or '').strip()
            profesor = (row.get('profesor') or row.get('Profesor') or '').strip()
            horario = (row.get('horario') or row.get('Horario') or '').strip()
            if not clave or not nombre:
                continue
            try:
                creditos = int(creditos_raw) if creditos_raw else None
            except ValueError:
                creditos = None
            if creditos not in (4, 5, 7):
                creditos = choice((4, 5, 7))
            defaults = {'nombre': nombre, 'profesor': profesor, 'horario': horario}
            if not Materia.objects.filter(clave=clave).exists():
                defaults['creditos'] = creditos
            materia, created = Materia.objects.update_or_create(clave=clave, defaults=defaults)
            count += 1
        return Response({'detail': f'{count} materias procesadas.'})


class CoordinacionReporteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _rows(self, request):
        if not es_gestion_academica(request.user):
            return None
        tipo = (request.query_params.get('tipo') or 'expedientes').lower()
        users = Aspirante.objects.filter(is_staff=False).order_by('nombre')
        if tipo == 'alumnos':
            users = users.filter(rol='alumno')
        elif tipo == 'aspirantes':
            users = users.filter(rol='aspirante')
        elif tipo in ('docentes', 'directores', 'personal'):
            users = users.filter(rol__in=('docente', 'director', 'investigador'))
        search = (request.query_params.get('q') or '').strip()
        if search:
            users = users.filter(Q(nombre__icontains=search) | Q(usuario__icontains=search) | Q(correo__icontains=search))
        headers = ['Nombre', 'Usuario', 'Matrícula', 'Correo', 'Rol', 'Programa', 'Departamento', 'Unidad', 'Estado', 'Activo']
        rows = [[u.nombre, u.usuario, u.matricula or '', u.correo, u.rol, u.programa, u.departamento, u.unidad, u.proceso_estado, 'Sí' if u.is_active else 'No'] for u in users]
        return tipo, headers, rows

    def get(self, request):
        result = self._rows(request)
        if result is None:
            return Response(status=status.HTTP_403_FORBIDDEN)
        tipo, headers, rows = result
        formato = request.query_params.get('format', 'json').lower()
        if formato == 'xlsx':
            return _xlsx_response([headers] + rows, f'reporte_{tipo}_{timezone.now():%Y%m%d}.xlsx', f'Reporte de {tipo} - SINAC NEXT')
        if formato == 'pdf':
            return _pdf_response(f'Reporte de {tipo}', f'Generado el {timezone.localtime():%d/%m/%Y %H:%M}', headers, rows, f'reporte_{tipo}_{timezone.now():%Y%m%d}.pdf')
        return Response({'tipo': tipo, 'total': len(rows), 'columnas': headers, 'filas': rows})


class CalificacionesDownloadView(APIView):
    permission_classes = [CoordinacionRolePermission]

    def get(self, request, pk):
        try:
            aspirante = Aspirante.objects.get(pk=pk, is_staff=False)
        except Aspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if aspirante.rol != 'alumno':
            return Response({'detail': 'Las calificaciones solo están disponibles para alumnos.'}, status=status.HTTP_400_BAD_REQUEST)
        headers = ['Clave', 'Materia', 'Créditos', 'Parcial 1', 'Parcial 2', 'Parcial 3', 'Final', 'Estado']
        rows = [[i.materia.clave, i.materia.nombre, i.materia.creditos, i.parcial_1 or '', i.parcial_2 or '', i.parcial_3 or '', i.calificacion or '', i.get_estado_display()] for i in aspirante.inscripciones.select_related('materia').order_by('materia__clave')]
        if request.query_params.get('format', 'pdf').lower() == 'xlsx':
            return _xlsx_response([headers] + rows, f'{aspirante.usuario}_calificaciones.xlsx', f'Historial académico - {aspirante.nombre}')
        return _pdf_response('Historial académico', f'Alumno: {aspirante.nombre} · Matrícula: {aspirante.matricula or "Pendiente"} · Programa: {aspirante.programa}', headers, rows, f'{aspirante.usuario}_calificaciones.pdf')


class AdscripcionDownloadView(APIView):
    permission_classes = [CoordinacionRolePermission]

    def get(self, request, pk):
        try:
            aspirante = Aspirante.objects.get(pk=pk, is_staff=False)
        except Aspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if aspirante.rol != 'alumno':
            return Response({'detail': 'El formato de adscripción solo aplica a alumnos.'}, status=status.HTTP_400_BAD_REQUEST)
        headers = ['Dato', 'Información']
        rows = [['Nombre', aspirante.nombre], ['Matrícula', aspirante.matricula or 'Pendiente'], ['CURP', aspirante.curp], ['Programa', aspirante.programa], ['Departamento', aspirante.departamento], ['Unidad', aspirante.unidad], ['', ''], ['Firma del alumno', '____________________________'], ['Firma de Coordinación Académica', '____________________________']]
        if request.query_params.get('format', 'pdf').lower() == 'xlsx':
            return _xlsx_response([headers] + rows, f'{aspirante.usuario}_adscripcion.xlsx', f'Formato de adscripción - {aspirante.nombre}')
        return _pdf_response('Formato de adscripción', 'SINAC NEXT · Cinvestav Unidad Zacatenco', headers, rows, f'{aspirante.usuario}_adscripcion.pdf')


class DarBajaView(APIView):
    permission_classes = [CoordinacionRolePermission]

    def post(self, request, pk):
        try:
            aspirante = Aspirante.objects.get(pk=pk, is_staff=False)
        except Aspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if aspirante.rol != 'alumno':
            return Response({'detail': 'Solo se pueden dar de baja alumnos.'}, status=status.HTTP_400_BAD_REQUEST)
        aspirante.is_active = False
        aspirante.proceso_estado = 'baja'
        aspirante.save(update_fields=['is_active', 'proceso_estado', 'updated_at'])
        _registrar_seguimiento(aspirante, 'baja', 'El alumno fue dado de baja por Coordinación Académica.', 'Coordinación Académica')
        return Response({'detail': 'Alumno dado de baja.'})


class ConvertirAlumnoView(APIView):
    permission_classes = [CoordinacionRolePermission]

    def post(self, request, pk):
        try:
            aspirante = Aspirante.objects.get(pk=pk, is_staff=False)
        except Aspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if aspirante.rol != 'aspirante':
            return Response({'detail': 'Solo los aspirantes pueden convertirse en alumnos.'}, status=status.HTTP_400_BAD_REQUEST)
        if aspirante.rol == 'alumno':
            return Response({'detail': 'El aspirante ya es alumno.', 'rol': 'alumno'})
        aspirante.rol = 'alumno'
        if not aspirante.matricula:
            aspirante.matricula = f'CINV-{timezone.now().year}-{Aspirante.objects.filter(matricula__startswith=f"CINV-{timezone.now().year}-").count() + 1:04d}'
        aspirante.save(update_fields=['rol', 'matricula', 'updated_at'])
        _registrar_seguimiento(aspirante, 'aceptado', 'El aspirante fue convertido a alumno por Coordinación Académica.', 'Coordinación Académica')
        return Response({'detail': 'Aspirante convertido a alumno.', 'rol': aspirante.rol, 'matricula': aspirante.matricula})

    def patch(self, request, pk):
        aspirante = self.get_object(pk)
        if not aspirante:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = AspiranteCoordinacionUpdateSerializer(aspirante, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        # El formulario envía todos los campos. Conservamos únicamente los que
        # realmente cambiaron para que cada fecha genere una sola notificación.
        cambios = {
            campo: valor
            for campo, valor in serializer.validated_data.items()
            if getattr(aspirante, campo) != valor
        }
        serializer.save()

        if 'proceso_estado' in cambios:
            if aspirante.proceso_estado == 'revision':
                _registrar_seguimiento(aspirante, 'revision', 'La solicitud fue marcada en revisión por la Coordinación Académica.', 'Coordinación Académica')
            elif aspirante.proceso_estado == 'aceptado':
                _registrar_seguimiento(aspirante, 'aceptado', 'Tu solicitud ha sido aceptada. Pronto recibirás fecha y hora para el examen de admisión.', 'Coordinación Académica')

        if 'fecha_examen_admision' in cambios and aspirante.fecha_examen_admision:
            detalle = f'Fecha y hora del examen de admisión programadas para {aspirante.fecha_examen_admision.strftime("%d/%m/%Y %H:%M")}. '
            _registrar_seguimiento(
                aspirante,
                'aceptado',
                detalle,
                'Coordinación Académica',
            )

        if 'fecha_entrevista' in cambios and aspirante.fecha_entrevista:
            detalle = f'Fecha y hora de entrevista programadas para {aspirante.fecha_entrevista.strftime("%d/%m/%Y %H:%M")}. '
            _registrar_seguimiento(
                aspirante,
                'aceptado',
                detalle,
                'Coordinación Académica',
            )

        if 'fecha_inicio_curso_propedeutico' in cambios and aspirante.fecha_inicio_curso_propedeutico:
            detalle = f'Inicio del curso propedéutico programado para {aspirante.fecha_inicio_curso_propedeutico.strftime("%d/%m/%Y %H:%M")}. '
            _registrar_seguimiento(
                aspirante,
                'aceptado',
                detalle,
                'Coordinación Académica',
            )

        if 'curso_propedeutico_aprobado' in cambios and aspirante.curso_propedeutico_aprobado:
            nota = aspirante.curso_propedeutico_nota or Decimal('0')
            if nota >= Decimal('8.00'):
                _registrar_seguimiento(
                    aspirante,
                    'aceptado',
                    'El curso propedéutico fue aprobado con al menos 8. Ahora puedes solicitar apoyo.',
                    'Coordinación Académica',
                )
            else:
                _registrar_seguimiento(
                    aspirante,
                    'aceptado',
                    'El curso propedéutico fue actualizado, pero no alcanzó la calificación mínima de 8 para el apoyo.',
                    'Coordinación Académica',
                )

        if 'apoyo_autorizado' in cambios and aspirante.apoyo_autorizado:
            _registrar_seguimiento(
                aspirante,
                'aceptado',
                'Tu apoyo ha sido autorizado por Coordinación Académica.',
                'Coordinación Académica',
            )

        return Response(AspiranteCoordinacionSerializer(aspirante).data)
