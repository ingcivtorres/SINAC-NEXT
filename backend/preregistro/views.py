import logging
import uuid
import hashlib
import csv
from random import choice
from io import StringIO
from decimal import Decimal
import requests as http
from django.conf import settings
from django.db.models import Q
from django.core.mail import send_mail
from django.http import FileResponse
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Aspirante, DocumentoAspirante, ExpedienteDigital, CargaAcademica, SeguimientoSolicitud, Materia, Inscripcion, SolicitudAcademica, ExamenEnLinea, EntrevistaVirtual, EvaluacionColegio, PreguntaExamen, RespuestaExamen, PeriodoInscripcion
from .admin_views import AdminRolePermission
from .serializers import (
    AspiranteRegistroSerializer,
    AspiranteDetalleSerializer,
    PerfilAspiranteSerializer,
    AspiranteAdminSerializer,
    AspiranteCoordinacionSerializer,
    AspiranteCoordinacionUpdateSerializer,
    InicioSesionSerializer,
    DocumentoAspiranteSerializer,
    SeguimientoSolicitudSerializer,
    MateriaSerializer,
    InscripcionSerializer,
    SolicitudAcademicaSerializer,
    ExamenEnLineaSerializer,
    EntrevistaVirtualSerializer,
    EvaluacionColegioSerializer,
    ExpedienteDigitalSerializer,
    ExpedienteDigitalUpdateSerializer,
    FirmaElectronicaSerializer,
)
import csv
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

def _crear_expediente_si_aceptado(aspirante):
    if aspirante.proceso_estado != 'aceptado':
        return None
    expediente, creado = ExpedienteDigital.objects.get_or_create(
        aspirante=aspirante,
        defaults={'folio': f'EXP-{timezone.now():%Y%m%d}-{aspirante.pk:06d}-{uuid.uuid4().hex[:4].upper()}'},
    )
    return expediente
from io import TextIOWrapper, BytesIO

logger = logging.getLogger(__name__)

CAMUNDA_URL = getattr(settings, 'CAMUNDA_REST_URL', 'http://camunda:8080/engine-rest')
MAX_DOCUMENTO_BYTES = 10 * 1024 * 1024


def _camunda_rest_url():
    """Normaliza CAMUNDA_URL para aceptar tanto http://camunda:8080 como engine-rest completo."""
    configured = (getattr(settings, 'CAMUNDA_URL', '') or CAMUNDA_URL).rstrip('/')
    return configured if configured.endswith('/engine-rest') else f'{configured}/engine-rest'


def _iniciar_carga_en_camunda(carga):
    response = http.post(
        f'{_camunda_rest_url()}/process-definition/key/carga_academica/start',
        json={'variables': {
            'cargaId': {'value': carga.id, 'type': 'Integer'},
            'periodo': {'value': carga.periodo, 'type': 'String'},
        }},
        timeout=8,
    )
    response.raise_for_status()
    return response.json().get('id', '')


def _completar_tarea_carga(carga, task_key, variables):
    """Completa una tarea activa de la instancia Camunda asociada a una carga."""
    if not carga.camunda_instance_id:
        return {'conectado': False, 'detalle': 'La carga no tiene una instancia Camunda asociada.'}
    base = _camunda_rest_url()
    tareas = http.get(
        f'{base}/task',
        params={'processInstanceId': carga.camunda_instance_id, 'taskDefinitionKey': task_key, 'active': 'true'},
        timeout=8,
    )
    tareas.raise_for_status()
    disponibles = tareas.json()
    if not disponibles:
        return {'conectado': False, 'detalle': f'No hay una tarea Camunda activa para {task_key}.'}
    task_id = disponibles[0]['id']
    completada = http.post(f'{base}/task/{task_id}/complete', json={'variables': variables}, timeout=8)
    completada.raise_for_status()
    return {'conectado': True, 'task_id': task_id}


def _xlsx_response(rows, filename, title='SINAC NEXT'):
    """Genera un XLSX real, con encabezado, filtros y columnas legibles."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Reporte'
    if rows:
        sheet.append([title])
        sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(rows[0]))
        sheet['A1'].font = Font(bold=True, size=14, color='FFFFFF')
        sheet['A1'].fill = PatternFill('solid', fgColor='006B63')
        sheet['A1'].alignment = Alignment(horizontal='center')
        sheet.append(rows[0])
        for cell in sheet[2]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor='008F83')
            cell.alignment = Alignment(horizontal='center')
        for row in rows[1:]:
            sheet.append(list(row))
        sheet.freeze_panes = 'A3'
        sheet.auto_filter.ref = f'A2:{get_column_letter(len(rows[0]))}{sheet.max_row}'
        for column in range(1, len(rows[0]) + 1):
            values = [str(sheet.cell(r, column).value or '') for r in range(1, sheet.max_row + 1)]
            sheet.column_dimensions[get_column_letter(column)].width = min(max(max(map(len, values)) + 2, 12), 42)
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return FileResponse(output, as_attachment=True, filename=filename, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


def _pdf_response(title, subtitle, headers, rows, filename):
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=landscape(letter), rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=28)
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles['Title']), Paragraph(subtitle, styles['Normal']), Spacer(1, 14)]
    table = Table([headers] + [list(row) for row in rows], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#006B63')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), .35, colors.HexColor('#B7CDCA')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#EFF6F5')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    story.append(table)
    story.append(Spacer(1, 16))
    story.append(Paragraph('Documento generado por SINAC NEXT - Cinvestav Unidad Zacatenco', styles['Normal']))
    document.build(story)
    output.seek(0)
    return FileResponse(output, as_attachment=True, filename=filename, content_type='application/pdf')


def _obtener_tamano_archivo(archivo):
    """Obtiene el tamaño del archivo de forma robusta para uploads de Django."""
    size = getattr(archivo, 'size', None)
    if size is None:
        try:
            size = getattr(archivo.file, 'size', None)
        except Exception:
            size = None
    if size is None:
        try:
            posicion = archivo.tell()
            archivo.seek(0, 2)
            size = archivo.tell()
            archivo.seek(posicion)
        except Exception:
            size = 0
    return int(size or 0)


class InicioSesionView(TokenObtainPairView):
    serializer_class = InicioSesionSerializer


def _enviar_correo_notificacion(aspirante, asunto, mensaje):
    remitente = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'no-reply@sinac.local'
    destinatario = [aspirante.correo]
    try:
        send_mail(asunto, mensaje, remitente, destinatario, fail_silently=True)
        logger.info('Notificación enviada a %s: %s', aspirante.correo, asunto)
    except Exception as exc:
        logger.warning('No se pudo enviar email de notificación a %s: %s', aspirante.correo, exc)


def _registrar_seguimiento(aspirante, estado, detalle, origen, notificar=False, asunto=None):
    seguimiento = SeguimientoSolicitud.objects.create(
        aspirante=aspirante,
        estado=estado,
        detalle=detalle,
        origen=origen,
    )
    if notificar:
        _enviar_correo_notificacion(aspirante, asunto or 'Actualización de tu solicitud', detalle)
    return seguimiento


def _iniciar_proceso_lida(aspirante):
    """Dispara instancia BPMN en Camunda; falla silenciosamente si el motor no está listo."""
    payload = {
        'businessKey': aspirante.business_key,
        'variables': {
            'aspiranteId':  {'value': aspirante.pk,            'type': 'Integer'},
            'correo':       {'value': aspirante.correo,        'type': 'String'},
            'unidad':       {'value': aspirante.unidad,        'type': 'String'},
            'programa':     {'value': aspirante.programa,      'type': 'String'},
            'lidaSource':   {'value': 'PortalAspirantes',      'type': 'String'},
        },
    }
    url = f'{CAMUNDA_URL}/process-definition/key/sinac_preregistro_v1/start'
    try:
        resp = http.post(url, json=payload, timeout=4)
        if resp.status_code == 200:
            logger.info('Camunda: proceso iniciado business_key=%s', aspirante.business_key)
            return resp.json().get('id')          # Camunda instance id
        logger.warning('Camunda respondió %s: %s', resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.warning('Camunda no disponible: %s', exc)
    return None


def _notificar_documento_lida(documento):
    """Notifica al flujo BPMN sin impedir que el aspirante conserve su archivo."""
    payload = {
        'messageName': 'DocumentoCargado',
        'businessKey': documento.aspirante.business_key,
        'processVariables': {
            'tipoDocumento': {'value': documento.tipo, 'type': 'String'},
            'nombreArchivo': {'value': documento.nombre_original, 'type': 'String'},
            'documentoId': {'value': documento.pk, 'type': 'Integer'},
        },
    }
    try:
        response = http.post(f'{CAMUNDA_URL}/message', json=payload, timeout=4)
        if response.status_code in (200, 204):
            logger.info('LIDA: documento notificado id=%s', documento.pk)
            return True
        logger.warning('LIDA no aceptó documento %s: %s', documento.pk, response.status_code)
    except Exception as exc:
        logger.warning('LIDA no disponible al notificar documento %s: %s', documento.pk, exc)
    return False


class PreregistroCreateView(generics.CreateAPIView):
    queryset = Aspirante.objects.all()
    serializer_class = AspiranteRegistroSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        aspirante = serializer.save()
        _registrar_seguimiento(aspirante, 'pendiente', 'Pre-registro recibido correctamente.', 'Portal Aspirantes')
        camunda_id = _iniciar_proceso_lida(aspirante)
        if camunda_id:
            aspirante.proceso_estado = 'iniciado'
            aspirante.camunda_instance_id = camunda_id
            aspirante.save(update_fields=['proceso_estado', 'camunda_instance_id'])
            _registrar_seguimiento(aspirante, 'iniciado', 'Proceso LIDA iniciado en Camunda.', 'LIDA / Camunda')
        refresh = RefreshToken.for_user(aspirante)
        return Response({
            'mensaje':        'Pre-registro creado correctamente.',
            'business_key':   aspirante.business_key,
            'proceso_estado': aspirante.proceso_estado,
            'camunda_id':     camunda_id,
            'access':         str(refresh.access_token),
            'refresh':        str(refresh),
        }, status=status.HTTP_201_CREATED)


class MiPerfilView(generics.RetrieveUpdateAPIView):
    serializer_class = AspiranteDetalleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def put(self, request, *args, **kwargs):
        """Update profile including photo upload."""
        aspirante = self.get_object()
        
        # Handle file upload
        if 'profile_photo' in request.FILES:
            foto = request.FILES['profile_photo']
            aspirante.profile_photo = foto
        
        # Update text fields
        nombre = request.data.get('nombre')
        if nombre:
            aspirante.nombre = nombre
        
        correo = request.data.get('correo')
        if correo:
            aspirante.correo = correo
        
        telefono = request.data.get('telefono')
        if telefono:
            aspirante.telefono = telefono
        
        # Add more fields as needed
        fields_to_update = [
            'estado_actual', 'municipio_actual', 'direccion_actual',
            'estado_permanente', 'municipio_permanente', 'direccion_permanente',
            'nombre_familiar', 'parentesco', 'telefono_familiar',
            'ultimo_grado', 'institucion', 'promedio', 'idiomas',
            'publicaciones', 'apoyos', 'experiencia', 'tutor_propuesto', 'comentarios'
        ]
        
        for field in fields_to_update:
            if field in request.data:
                setattr(aspirante, field, request.data.get(field))
        
        try:
            aspirante.save()
            return Response(AspiranteDetalleSerializer(aspirante).data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PerfilAspiranteView(APIView):
    """Actualiza datos editables del perfil y la foto mediante multipart/form-data."""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    max_photo_size = 5 * 1024 * 1024

    def get(self, request):
        if request.user.is_staff or getattr(request.user, 'rol', '') != 'alumno':
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(PerfilAspiranteSerializer(request.user, context={'request': request}).data)

    def patch(self, request):
        return self._update(request)

    def put(self, request):
        return self._update(request)

    def _update(self, request):
        if request.user.is_staff or getattr(request.user, 'rol', '') != 'alumno':
            return Response(status=status.HTTP_403_FORBIDDEN)
        photo = request.FILES.get('profile_photo')
        if photo and photo.size > self.max_photo_size:
            return Response({'profile_photo': 'La foto no debe superar 5 MB.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = PerfilAspiranteSerializer(request.user, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SeguimientoAspiranteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff or getattr(request.user, 'rol', '') != 'alumno':
            return Response(status=status.HTTP_403_FORBIDDEN)
        aspirante = request.user
        seguimientos = aspirante.seguimientos.all()
        return Response({
            'estado_actual': aspirante.proceso_estado,
            'business_key': aspirante.business_key,
            'camunda_instance_id': aspirante.camunda_instance_id or None,
            'eventos': SeguimientoSolicitudSerializer(seguimientos, many=True).data,
        })


def _periodo_inscripcion_vigente():
    """Devuelve el único periodo habilitado que contiene la fecha actual."""
    from django.utils import timezone
    return PeriodoInscripcion.objects.filter(
        activo=True,
        apertura__lte=timezone.now(),
        cierre__gte=timezone.now(),
    ).order_by('-apertura').first()


class MisMateriasDisponiblesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff or getattr(request.user, 'rol', '') != 'alumno':
            return Response(status=status.HTTP_403_FORBIDDEN)
        periodo = _periodo_inscripcion_vigente()
        if not periodo: return Response([])
        materias = Materia.objects.all().order_by('clave')
        return Response([MateriaSerializer(m).data for m in materias])

class PeriodoInscripcionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        from django.utils import timezone
        p = _periodo_inscripcion_vigente() or PeriodoInscripcion.objects.order_by('-apertura').first()
        if not p: return Response({'activo': False})
        ahora=timezone.now(); vigente=p.activo and p.apertura<=ahora<=p.cierre
        return Response({'id':p.id,'nombre':p.nombre,'apertura':p.apertura,'cierre':p.cierre,'activo':vigente})
    def post(self, request):
        if not request.user.is_staff: return Response(status=status.HTTP_403_FORBIDDEN)
        from django.utils.dateparse import parse_datetime
        from django.utils import timezone
        nombre = (request.data.get('nombre') or '').strip()
        apertura = parse_datetime(str(request.data.get('apertura') or ''))
        cierre = parse_datetime(str(request.data.get('cierre') or ''))
        activo_raw = request.data.get('activo', False)
        activo = activo_raw if isinstance(activo_raw, bool) else str(activo_raw).strip().lower() in ('1', 'true', 'si', 'sí', 'activo')
        if not nombre or not apertura or not cierre:
            return Response({'detail': 'Nombre, apertura y cierre son obligatorios y deben usar fechas válidas.'}, status=status.HTTP_400_BAD_REQUEST)
        if timezone.is_naive(apertura): apertura = timezone.make_aware(apertura)
        if timezone.is_naive(cierre): cierre = timezone.make_aware(cierre)
        if apertura >= cierre:
            return Response({'detail': 'La fecha de apertura debe ser anterior a la fecha de cierre.'}, status=status.HTTP_400_BAD_REQUEST)
        if PeriodoInscripcion.objects.filter(nombre=nombre).exists():
            return Response({'detail': 'Ya existe un periodo con ese nombre.'}, status=status.HTTP_409_CONFLICT)
        if PeriodoInscripcion.objects.filter(activo=True, apertura__lt=cierre, cierre__gt=apertura).exists():
            return Response({'detail': 'El periodo se traslapa con otro periodo de inscripción activo.'}, status=status.HTTP_409_CONFLICT)
        p=PeriodoInscripcion.objects.create(nombre=nombre, apertura=apertura, cierre=cierre, activo=activo)
        return Response({'id':p.id,'nombre':p.nombre,'apertura':p.apertura,'cierre':p.cierre,'activo':p.activo},status=status.HTTP_201_CREATED)


class MisInscripcionesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        inscripciones = request.user.inscripciones.select_related('materia').order_by('materia__clave')
        return Response(InscripcionSerializer(inscripciones, many=True).data)

    def post(self, request):
        if request.user.is_staff or getattr(request.user, 'rol', '') != 'alumno':
            return Response(status=status.HTTP_403_FORBIDDEN)
        periodo = _periodo_inscripcion_vigente()
        if not periodo:
            return Response({'detail': 'El periodo de inscripción está cerrado o no ha sido habilitado por Coordinación Académica.'}, status=status.HTTP_409_CONFLICT)
        materia_id = request.data.get('materia')
        horario = (request.data.get('horario') or '').strip()
        try:
            materia = Materia.objects.get(pk=materia_id)
        except Materia.DoesNotExist:
            return Response({'materia': 'Materia no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)
        inscripcion, created = Inscripcion.objects.get_or_create(
            aspirante=request.user,
            materia=materia,
            defaults={'horario': horario, 'periodo_inscripcion': periodo},
        )
        if not created:
            return Response({'detail': 'Ya estás inscrito en esta materia.'}, status=status.HTTP_400_BAD_REQUEST)
        _registrar_seguimiento(request.user, 'pendiente', f'Solicitud de inscripción recibida para {materia.clave} - {materia.nombre}.', 'Alumno', notificar=True, asunto='Solicitud de inscripción recibida')
        return Response(InscripcionSerializer(inscripcion).data, status=status.HTTP_201_CREATED)


class SolicitudAcademicaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        solicitudes = request.user.solicitudes_academicas.all()
        return Response(SolicitudAcademicaSerializer(solicitudes, many=True).data)

    def post(self, request):
        if request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        tipo = request.data.get('tipo')
        comentario = (request.data.get('comentario') or '').strip()
        if tipo not in dict(SolicitudAcademica.TIPOS).keys():
            return Response({'tipo': 'Selecciona un tipo de solicitud válido.'}, status=status.HTTP_400_BAD_REQUEST)
        solicitud = SolicitudAcademica.objects.create(
            aspirante=request.user,
            tipo=tipo,
            comentario=comentario,
        )
        detalle = f'Solicitud de {solicitud.get_tipo_display()} recibida.'
        _registrar_seguimiento(request.user, 'pendiente', detalle, 'Aspirante', notificar=True, asunto='Nueva solicitud académica')
        return Response(SolicitudAcademicaSerializer(solicitud).data, status=status.HTTP_201_CREATED)


class MisEntrevistasView(APIView):
    """API para que los alumnos vean sus entrevistas virtuales."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Obtener las entrevistas virtuales del alumno."""
        try:
            aspirante = request.user
            if not isinstance(aspirante, Aspirante):
                return Response(
                    {'error': 'Usuario no válido'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            
            # Obtener entrevistas del aspirante
            entrevistas = EntrevistaVirtual.objects.filter(
                aspirante=aspirante
            ).order_by('-fecha_programada')
            
            # Estadísticas
            entrevistas_total = entrevistas.count()
            entrevistas_programadas = entrevistas.filter(estado='programada').count()
            entrevistas_iniciadas = entrevistas.filter(estado='iniciada').count()
            entrevistas_completadas = entrevistas.filter(estado='completada').count()
            
            serializer = EntrevistaVirtualSerializer(entrevistas, many=True)
            return Response({
                'entrevistas': serializer.data,
                'resumen': {
                    'entrevistas_total': entrevistas_total,
                    'entrevistas_programadas': entrevistas_programadas,
                    'entrevistas_iniciadas': entrevistas_iniciadas,
                    'entrevistas_completadas': entrevistas_completadas,
                }
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MisExamenesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        examenes = request.user.examenes_en_linea.all().order_by('-fecha_programada')
        return Response({'examenes': ExamenEnLineaSerializer(examenes, many=True).data, 'total': examenes.count()})

    def post(self, request):
        try: examen = request.user.examenes_en_linea.get(pk=request.data.get('id'))
        except ExamenEnLinea.DoesNotExist: return Response({'detail': 'Examen no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if examen.estado != 'programado': return Response({'detail': 'Este examen no está disponible.'}, status=status.HTTP_400_BAD_REQUEST)
        examen.estado = 'iniciado'; examen.fecha_inicio = timezone.now(); examen.intentos += 1; examen.save(update_fields=['estado','fecha_inicio','intentos','updated_at'])
        return Response(ExamenEnLineaSerializer(examen).data)

    def put(self, request):
        try: examen = request.user.examenes_en_linea.get(pk=request.data.get('id'))
        except ExamenEnLinea.DoesNotExist: return Response({'detail': 'Examen no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if examen.estado != 'iniciado': return Response({'detail': 'El examen no está iniciado.'}, status=status.HTTP_400_BAD_REQUEST)
        respuestas = request.data.get('respuestas', {})
        preguntas = list(examen.preguntas.all()); correctas = 0
        for pregunta in preguntas:
            valor = str(respuestas.get(str(pregunta.id), respuestas.get(pregunta.id, '')))
            correcta = valor.strip().lower() == pregunta.respuesta_correcta.strip().lower()
            RespuestaExamen.objects.update_or_create(pregunta=pregunta, aspirante=request.user, defaults={'examen': examen, 'respuesta': valor, 'es_correcta': correcta})
            correctas += int(correcta)
        examen.calificacion = round((correctas / len(preguntas)) * 10, 2) if preguntas else 0
        examen.estado = 'aprobado' if examen.calificacion >= 8 else 'reprobado'; examen.fecha_fin = timezone.now(); examen.save(update_fields=['calificacion','estado','fecha_fin','updated_at'])
        return Response(ExamenEnLineaSerializer(examen).data)


class HorarioDescargaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        inscripciones = request.user.inscripciones.select_related('materia').all()
        content_lines = [
            f'Horario de clases de {request.user.nombre}',
            f'Programa: {request.user.programa}',
            '',
            'Materias inscritas:',
            '------------------',
        ]
        for ins in inscripciones:
            content_lines.append(f'{ins.materia.clave} - {ins.materia.nombre}')
            content_lines.append(f'  Profesor: {ins.materia.profesor or "—"}')
            content_lines.append(f'  Horario: {ins.horario or ins.materia.horario or "Por asignar"}')
            content_lines.append(f'  Estado: {ins.get_estado_display()} / Calificación: {ins.calificacion or "—"}')
            content_lines.append('')
        bio = BytesIO()
        doc = SimpleDocTemplate(bio, pagesize=letter, rightMargin=.65*inch, leftMargin=.65*inch, topMargin=.65*inch, bottomMargin=.65*inch)
        styles = getSampleStyleSheet(); title = ParagraphStyle('HorarioTitle', parent=styles['Title'], textColor=colors.HexColor('#00695c'), fontSize=18)
        story = [Paragraph('SINAC NEXT', title), Paragraph('Horario académico', styles['Heading2']), Paragraph(f'<b>Alumno:</b> {request.user.nombre}<br/><b>Programa:</b> {request.user.programa or "—"}<br/><b>Unidad:</b> {request.user.unidad or "—"}', styles['BodyText']), Spacer(1, 18)]
        rows = [['Clave', 'Materia', 'Profesor', 'Horario', 'Estado']]
        for ins in inscripciones: rows.append([ins.materia.clave, ins.materia.nombre, ins.materia.profesor or 'Por asignar', ins.horario or ins.materia.horario or 'Por asignar', ins.get_estado_display()])
        table = Table(rows, colWidths=[.75*inch, 2.05*inch, 1.3*inch, 1.35*inch, .8*inch], repeatRows=1); table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#00695c')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#cbd5e1')),('FONTSIZE',(0,0),(-1,-1),8),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#f1f5f9')])]))
        story.extend([table, Spacer(1, 18), Paragraph('Documento generado por SINAC NEXT.', styles['Normal'])]); doc.build(story); bio.seek(0)
        return FileResponse(bio, as_attachment=True, filename=f'{request.user.usuario}_horario.pdf', content_type='application/pdf')


class HorarioFormalDescargaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff: return Response(status=status.HTTP_403_FORBIDDEN)
        bio = BytesIO(); doc = SimpleDocTemplate(bio, pagesize=landscape(letter), rightMargin=.45*inch, leftMargin=.45*inch, topMargin=.4*inch, bottomMargin=.5*inch)
        styles = getSampleStyleSheet(); title = ParagraphStyle('HorarioFormalTitle', parent=styles['Title'], alignment=1, fontSize=13, leading=16, textColor=colors.HexColor('#00695c'))
        def logo(name, width):
            path = os.path.join('/app/frontend_assets', name)
            return Image(path, width=width, height=width*.62) if os.path.exists(path) else Paragraph('', styles['Normal'])
        header = Table([[logo('logociv.png', .72*inch), Paragraph('<b>Centro de Investigación y de Estudios Avanzados</b><br/><font size="12">Horario Académico</font>', title), logo('6-removebg-preview.png', .9*inch)]], colWidths=[1.05*inch,4.55*inch,1.05*inch])
        header.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('ALIGN',(0,0),(0,0),'LEFT'),('ALIGN',(2,0),(2,0),'RIGHT'),('LINEBELOW',(0,0),(-1,-1),1,colors.HexColor('#00695c')),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        datos = Table([[Paragraph(f'<b>Alumno:</b> {request.user.nombre or "—"}', styles['BodyText']), Paragraph(f'<b>Matrícula:</b> {request.user.matricula or request.user.usuario or "—"}', styles['BodyText'])], [Paragraph(f'<b>Programa:</b> {request.user.programa or "—"}', styles['BodyText']), Paragraph(f'<b>Unidad:</b> {request.user.unidad or "—"}', styles['BodyText'])]], colWidths=[4.5*inch, 3.2*inch]); datos.setStyle(TableStyle([('BOX',(0,0),(-1,-1),.6,colors.HexColor('#00695c')),('INNERGRID',(0,0),(-1,-1),.3,colors.HexColor('#b8c7d1')),('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f1f8f7')),('PADDING',(0,0),(-1,-1),8)]))
        story = [header, Spacer(1,12), datos, Spacer(1,16)]
        cell = lambda value: Paragraph(str(value), ParagraphStyle('Cell', parent=styles['Normal'], fontSize=8, leading=10, wordWrap='CJK'))
        rows = [[cell('Clave del curso'),cell('Materia'),cell('Profesor'),cell('Horario'),cell('Estado')]]
        for ins in request.user.inscripciones.select_related('materia').all(): rows.append([cell(ins.materia.clave),cell(ins.materia.nombre),cell(ins.materia.profesor or 'Por asignar'),cell(ins.horario or ins.materia.horario or 'Por asignar'),cell(ins.get_estado_display())])
        if len(rows) > 1:
            table = Table(rows, colWidths=[1.05*inch,2.75*inch,1.8*inch,2.35*inch,1.05*inch], repeatRows=1)
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#00695c')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#b8c7d1')),('FONTSIZE',(0,0),(-1,-1),8),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f1f5f9')]),('PADDING',(0,0),(-1,-1),6)])); story.append(table)
        else: story.append(Paragraph('No hay materias inscritas para este periodo escolar.', styles['BodyText']))
        def pie_pagina(canvas, documento):
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor('#00695c')); canvas.setLineWidth(.6)
            canvas.line(documento.leftMargin, .38*inch, landscape(letter)[0] - documento.rightMargin, .38*inch)
            canvas.setFont('Helvetica', 8); canvas.setFillColor(colors.HexColor('#52616b'))
            canvas.drawCentredString(landscape(letter)[0] / 2, .2*inch, 'Documento generado por SINAC NEXT - Cinvestav Zacatenco')
            canvas.restoreState()
        doc.build(story, onFirstPage=pie_pagina, onLaterPages=pie_pagina); bio.seek(0)
        return FileResponse(bio, as_attachment=True, filename=f'{request.user.usuario}_horario.pdf', content_type='application/pdf')


class ReinscripcionDescargaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        content = (
            f'Formato de reinscripción\nAlumno: {request.user.nombre}\nCURP: {request.user.curp}\nPrograma: {request.user.programa}\nUnidad: {request.user.unidad}\n\n'
            'Declaro que deseo reinscribirme al programa y acepto los términos académicos.\n'
            'Firma: __________________________\n'
        )
        bio = BytesIO()
        doc = SimpleDocTemplate(bio, pagesize=letter, rightMargin=.8*inch, leftMargin=.8*inch, topMargin=.7*inch, bottomMargin=.7*inch)
        styles = getSampleStyleSheet(); title = ParagraphStyle('ReinsTitle', parent=styles['Title'], textColor=colors.HexColor('#00695c'), alignment=1, fontSize=18)
        story = [Paragraph('SINAC NEXT', title), Paragraph('FORMATO DE REINSCRIPCIÓN', styles['Heading2']), Spacer(1, 18), Paragraph(f'<b>Alumno:</b> {request.user.nombre}<br/><b>CURP:</b> {request.user.curp or "—"}<br/><b>Programa:</b> {request.user.programa or "—"}<br/><b>Unidad:</b> {request.user.unidad or "—"}', styles['BodyText']), Spacer(1, 30), Paragraph('Declaro que deseo reinscribirme al programa y acepto los términos académicos y administrativos vigentes.', styles['BodyText']), Spacer(1, 70), Paragraph('Firma del alumno: ___________________________________________', styles['BodyText'])]
        # Reemplazar el bloque de firmas por un formato formal: línea arriba y etiqueta debajo.
        story = story
        sig_style = ParagraphStyle('SignatureLabel', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=1)
        firmas = Table([
            ['________________________', '________________________', '________________________'],
            [Paragraph('Firma del estudiante', sig_style), Paragraph('Jefe del Departamento de<br/>Coordinación Académica', sig_style), Paragraph('Servicios escolares', sig_style)]
        ], colWidths=[2.2*inch]*3)
        firmas.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,0),14),('BOTTOMPADDING',(0,0),(-1,0),6)]))
        story.extend([])
        def pie_pagina(canvas, documento):
            canvas.saveState(); canvas.setStrokeColor(colors.HexColor('#00695c'))
            canvas.line(documento.leftMargin, .38*inch, letter[0]-documento.rightMargin, .38*inch)
            canvas.setFont('Helvetica', 8); canvas.setFillColor(colors.HexColor('#41515a'))
            canvas.drawCentredString(letter[0]/2, .2*inch, 'Documento generado por SINAC NEXT - Cinvestav Unidad Zacatenco'); canvas.restoreState()
        doc.build(story, onFirstPage=pie_pagina, onLaterPages=pie_pagina); bio.seek(0)
        _registrar_seguimiento(request.user, 'pendiente', 'Se generó una solicitud de reinscripción.', 'Aspirante', notificar=True, asunto='Solicitud de reinscripción')
        return FileResponse(bio, as_attachment=True, filename=f'{request.user.usuario}_reinscripcion.pdf', content_type='application/pdf')


class BoletaInscripcionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        bio = BytesIO()
        doc = SimpleDocTemplate(bio, pagesize=letter, rightMargin=.55*inch, leftMargin=.55*inch, topMargin=.5*inch, bottomMargin=.5*inch)
        styles = getSampleStyleSheet()
        title = ParagraphStyle('BoletaTitle', parent=styles['Title'], alignment=1, textColor=colors.HexColor('#00695c'), fontSize=14)
        def logo(name, width):
            path = os.path.join('/app/frontend_assets', name)
            return Image(path, width=width, height=width*.62) if os.path.exists(path) else Paragraph('', styles['Normal'])
        header = Table([[logo('logociv.png', .72*inch), Paragraph('<b>Centro de Investigación y de Estudios Avanzados</b>', title), logo('6-removebg-preview.png', .9*inch)]], colWidths=[1.05*inch, 4.55*inch, 1.05*inch])
        header.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LINEBELOW',(0,0),(-1,-1),1,colors.HexColor('#00695c'))]))
        story = [header, Spacer(1,12), Paragraph('Boleta de Inscripción', ParagraphStyle('BoletaHead', parent=styles['Heading2'], alignment=1, textColor=colors.HexColor('#00695c'))), Spacer(1,12)]
        datos = [['Nombre del alumno', request.user.nombre or '—', 'Matrícula', request.user.usuario or '—'], ['CURP', request.user.curp or '—', 'Periodo Escolar', getattr(request.user, 'periodo_escolar', None) or '—'], ['Cuatrimestre', getattr(request.user, 'cuatrimestre', None) or '—', 'Departamento', request.user.departamento or '—'], ['Programa', request.user.programa or '—', 'Unidad', request.user.unidad or '—']]
        label_style = ParagraphStyle('BoletaDataLabel', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=10)
        value_style = ParagraphStyle('BoletaDataValue', parent=styles['Normal'], fontSize=8.5, leading=10, wordWrap='CJK')
        datos = [[Paragraph(str(value), label_style if index in (0, 2) else value_style) for index, value in enumerate(row)] for row in datos]
        info = Table(datos, colWidths=[1.55*inch,2.05*inch,1.55*inch,1.85*inch])
        info.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.HexColor('#b8c7d1')),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#e7f3f1')),('BACKGROUND',(2,0),(2,-1),colors.HexColor('#e7f3f1')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        story.extend([info, Spacer(1,16)])
        rows = [['Clave del Curso','Materia','Profesor']]
        for ins in request.user.inscripciones.select_related('materia').all(): rows.append([ins.materia.clave, ins.materia.nombre, ins.materia.profesor or 'Por asignar'])
        courses = Table(rows, colWidths=[1.35*inch,3.2*inch,2.1*inch], repeatRows=1); courses.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#00695c')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#b8c7d1')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f8fa')]),('PADDING',(0,0),(-1,-1),7)])); story.extend([courses, Spacer(1,48), Table([['Firma del estudiante','Jefe del Departamento de Coordinación Académica','Servicios escolares'],['\n\n________________','\n\n________________','\n\n________________']], colWidths=[2.2*inch]*3, style=TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold')])), Spacer(1,24), Paragraph('Documento generado por SINAC NEXT - Cinvestav Unidad Zacatenco', ParagraphStyle('Footer', parent=styles['Normal'], alignment=1, fontSize=8))])
        story = story[:-4]
        sig_style = ParagraphStyle('SignatureLabel', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=1)
        firmas = Table([
            ['________________________', '________________________', '________________________'],
            [Paragraph('Firma del estudiante', sig_style), Paragraph('Jefe del Departamento de<br/>Coordinación Académica', sig_style), Paragraph('Servicios escolares', sig_style)]
        ], colWidths=[2.2*inch]*3)
        firmas.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,0),14),('BOTTOMPADDING',(0,0),(-1,0),6)]))
        story.extend([Spacer(1,42), firmas])
        def pie_pagina(canvas, documento):
            canvas.saveState(); canvas.setStrokeColor(colors.HexColor('#00695c'))
            canvas.line(documento.leftMargin, .38*inch, letter[0]-documento.rightMargin, .38*inch)
            canvas.setFont('Helvetica', 8); canvas.setFillColor(colors.HexColor('#41515a'))
            canvas.drawCentredString(letter[0]/2, .2*inch, 'Documento generado por SINAC NEXT - Cinvestav Unidad Zacatenco'); canvas.restoreState()
        doc.build(story, onFirstPage=pie_pagina, onLaterPages=pie_pagina); bio.seek(0)
        return FileResponse(bio, as_attachment=True, filename=f'{request.user.usuario}_boleta_inscripcion.pdf', content_type='application/pdf')


class ExpedienteDigitalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _permitido(self, user):
        return user.is_staff or getattr(user, 'rol', '') in ('coordinacion', 'servicios', 'servicios_escolares')

    def _es_director_de(self, user, expediente):
        return (
            str(getattr(user, 'rol', '')).strip().lower() in ('director', 'director de tesis')
            and (expediente.aspirante.director_tesis_id == user.id or expediente.aspirante.tutor_propuesto.strip().lower() in {
                str(getattr(user, 'nombre', '')).strip().lower(),
                str(getattr(user, 'usuario', '')).strip().lower(),
            })
        )

    def get(self, request, pk=None):
        if pk:
            expediente = ExpedienteDigital.objects.select_related('aspirante').filter(pk=pk).first()
            if not expediente: return Response(status=status.HTTP_404_NOT_FOUND)
            if not self._permitido(request.user) and expediente.aspirante_id != request.user.id and not self._es_director_de(request.user, expediente):
                return Response(status=status.HTTP_403_FORBIDDEN)
            return Response(ExpedienteDigitalSerializer(expediente).data)
        if self._permitido(request.user):
            qs = ExpedienteDigital.objects.select_related('aspirante').all()
        elif str(getattr(request.user, 'rol', '')).strip().lower() in ('director', 'director de tesis'):
            qs = ExpedienteDigital.objects.select_related('aspirante').filter(Q(aspirante__director_tesis=request.user) | Q(aspirante__tutor_propuesto__iexact=request.user.nombre)).distinct()
        else:
            qs = ExpedienteDigital.objects.filter(aspirante=request.user)
        return Response(ExpedienteDigitalSerializer(qs, many=True).data)

    def patch(self, request, pk):
        if not self._permitido(request.user): return Response(status=status.HTTP_403_FORBIDDEN)
        expediente = ExpedienteDigital.objects.filter(pk=pk).first()
        if not expediente: return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = ExpedienteDigitalUpdateSerializer(expediente, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True); serializer.save()
        _registrar_seguimiento(expediente.aspirante, 'aceptado', f'Expediente oficial actualizado: {expediente.folio}.', 'Servicios Escolares', notificar=True, asunto='Expediente actualizado')
        return Response(ExpedienteDigitalSerializer(expediente).data)


class FirmaElectronicaView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, pk):
        if getattr(request.user, 'rol', '') not in ('director', 'docente') and not request.user.is_staff:
            return Response({'detail': 'Solo el tutor o director puede firmar.'}, status=status.HTTP_403_FORBIDDEN)
        expediente = ExpedienteDigital.objects.select_related('aspirante').filter(pk=pk).first()
        if not expediente: return Response(status=status.HTTP_404_NOT_FOUND)
        if not request.user.is_staff and str(getattr(request.user, 'rol', '')).strip().lower() in ('director', 'director de tesis'):
            if not (expediente.aspirante.director_tesis_id == request.user.id or expediente.aspirante.tutor_propuesto.strip().lower() in {
                str(getattr(request.user, 'nombre', '')).strip().lower(),
                str(getattr(request.user, 'usuario', '')).strip().lower(),
            }):
                return Response({'detail': 'Este expediente no pertenece a uno de tus tesistas.'}, status=status.HTTP_403_FORBIDDEN)
        rol = request.data.get('rol_firmante', 'director')
        if FirmaElectronica.objects.filter(expediente=expediente, firmante=request.user, rol_firmante=rol).exists():
            return Response({'detail': 'El expediente ya fue firmado por este usuario.'}, status=status.HTTP_400_BAD_REQUEST)
        huella = hashlib.sha256(f'{expediente.folio}|{request.user.pk}|{rol}|{timezone.now().isoformat()}'.encode()).hexdigest()
        firma = FirmaElectronica.objects.create(expediente=expediente, firmante=request.user, rol_firmante=rol, huella=huella)
        return Response(FirmaElectronicaSerializer(firma).data, status=status.HTTP_201_CREATED)

    def get(self, request, pk):
        expediente = ExpedienteDigital.objects.filter(pk=pk).first()
        if not expediente: return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(FirmaElectronicaSerializer(expediente.firmas.select_related('firmante'), many=True).data)


class EvaluacionColegioView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            evaluaciones = EvaluacionColegio.objects.select_related('aspirante').all()
        else:
            evaluaciones = EvaluacionColegio.objects.filter(aspirante=request.user)
        return Response(EvaluacionColegioSerializer(evaluaciones, many=True).data)

    def post(self, request):
        if getattr(request.user, 'rol', '') not in ('docente', 'coordinacion') and not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        aspirante_id = request.data.get('aspirante')
        try:
            aspirante = Aspirante.objects.get(pk=aspirante_id)
        except Aspirante.DoesNotExist:
            return Response({'aspirante': 'Aspirante no encontrado.'}, status=status.HTTP_400_BAD_REQUEST)
        if aspirante.rol != 'aspirante':
            return Response({'aspirante': 'La evaluación del Colegio solo aplica a aspirantes.'}, status=status.HTTP_400_BAD_REQUEST)
        estado = request.data.get('estado', 'en_revision')
        dictamen = (request.data.get('dictamen') or '').strip()
        if estado not in dict(EvaluacionColegio.ESTADOS):
            return Response({'estado': 'Selecciona un estado de evaluación válido.'}, status=status.HTTP_400_BAD_REQUEST)
        if estado in ('favorable', 'no_favorable') and not dictamen:
            return Response({'dictamen': 'El dictamen es obligatorio para cerrar la evaluación.'}, status=status.HTTP_400_BAD_REQUEST)
        evaluacion = EvaluacionColegio.objects.create(aspirante=aspirante, evaluador=request.user, estado=estado, dictamen=dictamen, fecha_evaluacion=request.data.get('fecha_evaluacion') or timezone.now())
        _registrar_seguimiento(aspirante, 'aceptado' if estado == 'favorable' else 'rechazado' if estado == 'no_favorable' else 'revision', f'El Colegio de Profesores registró un dictamen: {evaluacion.get_estado_display()}.', 'Colegio de Profesores', notificar=True, asunto='Actualización del Colegio de Profesores')
        return Response(EvaluacionColegioSerializer(evaluacion).data, status=status.HTTP_201_CREATED)

    def patch(self, request, pk):
        try: evaluacion = EvaluacionColegio.objects.get(pk=pk)
        except EvaluacionColegio.DoesNotExist: return Response(status=status.HTTP_404_NOT_FOUND)
        if not request.user.is_staff and getattr(request.user, 'rol', '') not in ('docente', 'coordinacion'): return Response(status=status.HTTP_403_FORBIDDEN)
        estado = request.data.get('estado', evaluacion.estado)
        dictamen = (request.data.get('dictamen', evaluacion.dictamen) or '').strip()
        if estado not in dict(EvaluacionColegio.ESTADOS):
            return Response({'estado': 'Selecciona un estado de evaluación válido.'}, status=status.HTTP_400_BAD_REQUEST)
        if estado in ('favorable', 'no_favorable') and not dictamen:
            return Response({'dictamen': 'El dictamen es obligatorio para cerrar la evaluación.'}, status=status.HTTP_400_BAD_REQUEST)
        evaluacion.estado = estado
        evaluacion.dictamen = dictamen
        if 'fecha_evaluacion' in request.data:
            evaluacion.fecha_evaluacion = request.data['fecha_evaluacion']
        evaluacion.evaluador = request.user; evaluacion.save()
        _registrar_seguimiento(evaluacion.aspirante, 'aceptado' if estado == 'favorable' else 'rechazado' if estado == 'no_favorable' else 'revision', f'El dictamen del Colegio fue actualizado a {evaluacion.get_estado_display()}.', 'Colegio de Profesores', notificar=True, asunto='Dictamen actualizado')
        return Response(EvaluacionColegioSerializer(evaluacion).data)


class MarcarNotificacionesLeidasView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        aspirante = request.user
        pendientes = aspirante.seguimientos.filter(leido=False)
        count = pendientes.update(leido=True)
        return Response({'updated': count})


class DocumentoAspiranteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def _aspirante(request):
        return None if request.user.is_staff else request.user

    def get(self, request):
        aspirante = self._aspirante(request)
        if not aspirante:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(DocumentoAspiranteSerializer(aspirante.documentos.order_by('tipo'), many=True, context={'request': request}).data)

    def post(self, request):
        aspirante = self._aspirante(request)
        if not aspirante:
            return Response(status=status.HTTP_403_FORBIDDEN)
        tipo = request.data.get('tipo')
        archivo = request.FILES.get('archivo')
        tipos_validos = {tipo_id for tipo_id, _ in DocumentoAspirante.TIPOS}
        if tipo not in tipos_validos:
            return Response({'tipo': 'Selecciona un tipo de documento válido.'}, status=status.HTTP_400_BAD_REQUEST)
        if not archivo:
            return Response({'archivo': 'Selecciona un archivo PDF.'}, status=status.HTTP_400_BAD_REQUEST)
        if archivo.size > MAX_DOCUMENTO_BYTES:
            return Response({'archivo': 'El archivo no debe exceder 10 MB.'}, status=status.HTTP_400_BAD_REQUEST)
        if not archivo.name.lower().endswith('.pdf'):
            return Response({'archivo': 'Solo se permiten archivos PDF.'}, status=status.HTTP_400_BAD_REQUEST)

        tamano = _obtener_tamano_archivo(archivo)
        documento, created = DocumentoAspirante.objects.get_or_create(
            aspirante=aspirante,
            tipo=tipo,
            defaults={
                'archivo': archivo,
                'nombre_original': archivo.name,
                'tamano': tamano,
                'lida_notificado': False,
            },
        )
        if not created:
            if documento.archivo:
                documento.archivo.delete(save=False)
            documento.archivo = archivo
            documento.nombre_original = archivo.name
            documento.tamano = tamano
            documento.lida_notificado = False
            documento.save()
        documento.lida_notificado = _notificar_documento_lida(documento)
        documento.save(update_fields=['lida_notificado', 'updated_at'])
        return Response(DocumentoAspiranteSerializer(documento, context={'request': request}).data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        aspirante = self._aspirante(request)
        if not aspirante:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            documento = aspirante.documentos.get(pk=pk)
        except DocumentoAspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        documento.archivo.delete(save=False)
        documento.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentoDescargaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            documento = DocumentoAspirante.objects.select_related('aspirante').get(pk=pk)
        except DocumentoAspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not request.user.is_staff and documento.aspirante_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return FileResponse(documento.archivo.open('rb'), as_attachment=True, filename=documento.nombre_original)


class SolicitarApoyoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        aspirante = request.user
        if aspirante.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        nota = Decimal(str(aspirante.curso_propedeutico_nota or '0'))
        if not aspirante.curso_propedeutico_aprobado or nota < Decimal('8.00'):
            return Response(
                {'detail': 'Solo puedes solicitar apoyo después de aprobar el curso propedéutico con al menos 8.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        banco = (request.data.get('banco') or '').strip()
        clabe = ''.join(char for char in (request.data.get('clabe_interbancaria') or '') if char.isdigit())
        if not banco:
            return Response({'banco': 'Captura el nombre del banco.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(clabe) != 18:
            return Response({'clabe_interbancaria': 'La CLABE interbancaria debe tener 18 dígitos.'}, status=status.HTTP_400_BAD_REQUEST)

        es_nueva_solicitud = not aspirante.apoyo_solicitado
        aspirante.banco_apoyo = banco
        aspirante.clabe_interbancaria = clabe
        aspirante.apoyo_solicitado = True
        if es_nueva_solicitud:
            aspirante.solicitud_apoyo_fecha = timezone.now()
        aspirante.save(update_fields=['banco_apoyo', 'clabe_interbancaria', 'apoyo_solicitado', 'solicitud_apoyo_fecha', 'updated_at'])
        if es_nueva_solicitud:
            _registrar_seguimiento(
                aspirante,
                'aceptado',
                'El aspirante solicitó apoyo tras aprobar el curso propedéutico.',
                'Aspirante',
            )
        return Response({
            'detail': 'Datos bancarios guardados. Ya puedes imprimir tu solicitud de apoyo.',
            'solicitud': {
                'banco': aspirante.banco_apoyo,
                'clabe_interbancaria': aspirante.clabe_interbancaria,
                'fecha': aspirante.solicitud_apoyo_fecha,
            },
        })


class PanelAdministradorView(APIView):
    permission_classes = [AdminRolePermission]

    @staticmethod
    def _normalizar_rol(valor):
        if valor is None:
            return 'aspirante'

        rol = str(valor).strip().lower()
        aliases = {
            'admin': 'admin',
            'administrador': 'admin',
            'coordinacion': 'coordinacion',
            'coordinación': 'aspirante',
            'coordinador': 'coordinacion',
            'docente': 'docente',
            'teacher': 'docente',
            'alumno': 'alumno',
            'student': 'alumno',
            'aspirante': 'aspirante',
            'candidate': 'aspirante',
            'director': 'director',
            'director de tesis': 'director',
            'servicios': 'servicios',
            'servicios escolares': 'servicios',
        }
        return aliases.get(rol, 'aspirante')

    @staticmethod
    def _normalizar_estado(valor):
        if valor is None:
            return None
        estado = str(valor).strip().lower()
        if estado in ['activo', 'active', 'enabled', 'true']:
            return True
        if estado in ['inactivo', 'inactive', 'disabled', 'false']:
            return False
        if estado in ['pendiente', 'pending']:
            return True
        return None

    def get(self, request):
        aspirantes = Aspirante.objects.filter(is_staff=False).order_by('-created_at')
        return Response({
            'resumen': {
                'total': aspirantes.count(),
                'pendiente': aspirantes.filter(proceso_estado='pendiente').count(),
                'iniciado': aspirantes.filter(proceso_estado='iniciado').count(),
                'revision': aspirantes.filter(proceso_estado='revision').count(),
                'aceptado': aspirantes.filter(proceso_estado='aceptado').count(),
            },
            'aspirantes': AspiranteAdminSerializer(aspirantes, many=True).data,
        })

    def post(self, request):
        """Create a new aspirante (admin only)"""
        nombre = (request.data.get('name') or '').strip()
        correo = (request.data.get('email') or '').strip().lower()
        usuario = (request.data.get('usuario') or nombre.replace(' ', '').lower()[:20]).strip()
        rol = self._normalizar_rol(request.data.get('role'))
        programa = (request.data.get('area') or 'General').strip()
        password = (request.data.get('password') or '').strip()

        if not nombre or not correo:
            return Response(
                {'error': 'Nombre y correo son obligatorios.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not usuario:
            return Response({'error': 'El nombre de usuario es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(usuario) < 3:
            return Response({'error': 'El nombre de usuario debe tener al menos 3 caracteres.'}, status=status.HTTP_400_BAD_REQUEST)

        if not password:
            return Response(
                {'error': 'La contraseña es obligatoria.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(password) < 8:
            return Response(
                {'error': 'La contraseña debe tener al menos 8 caracteres.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Aspirante.objects.filter(correo__iexact=correo).exists():
            return Response(
                {'error': 'Ya existe un aspirante con este correo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Aspirante.objects.filter(usuario__iexact=usuario).exists():
            return Response(
                {'error': 'Ya existe un aspirante con este usuario.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            aspirante = Aspirante.objects.create_user(
                usuario=usuario,
                correo=correo,
                nombre=nombre,
                password=password,
                # CURP provisional única; el usuario podrá sustituirla por la oficial.
                curp=f'TEMP{uuid.uuid4().hex[:14].upper()}',
                rol=rol if rol in ('aspirante', 'alumno', 'docente', 'director', 'servicios') else 'aspirante',
                is_staff=rol in ('admin', 'coordinacion'),
                programa=programa,
                unidad='Administración',
                departamento='SINAC',
                seccion='General',
                estado_actual='Ciudad de México',
                municipio_actual='Gustavo A. Madero',
                direccion_actual='Cinvestav',
                estado_permanente='Ciudad de México',
                municipio_permanente='Gustavo A. Madero',
                direccion_permanente='Cinvestav',
                nombre_familiar='No aplica',
                parentesco='No aplica',
                telefono='0000000000',
                telefono_familiar='0000000000',
                ultimo_grado='No aplica',
                institucion='Cinvestav',
                business_key=f'ADMIN-{uuid.uuid4().hex.upper()}',
            )
            return Response(AspiranteAdminSerializer(aspirante).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': f'Error al crear aspirante: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def put(self, request, pk=None):
        """Update an aspirante (admin only)"""
        if not pk and request.data.get('id'):
            pk = request.data['id']

        if not pk:
            return Response(
                {'error': 'Se requiere un ID de usuario.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            aspirante = Aspirante.objects.get(pk=pk, is_staff=False)
        except Aspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if aspirante.rol != 'aspirante':
            return Response({'detail': 'Este flujo solo aplica a aspirantes.'}, status=status.HTTP_400_BAD_REQUEST)

        if 'name' in request.data:
            nombre = str(request.data['name']).strip()
            if nombre:
                aspirante.nombre = nombre
        if 'email' in request.data:
            email = str(request.data['email']).strip().lower()
            if email:
                if Aspirante.objects.exclude(pk=pk).filter(correo__iexact=email).exists():
                    return Response(
                        {'error': 'Ya existe un aspirante con este correo.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                aspirante.correo = email
        if 'role' in request.data:
            aspirante.rol = self._normalizar_rol(request.data['role'])
        if 'area' in request.data:
            area = str(request.data['area']).strip()
            if area:
                aspirante.programa = area
        if 'password' in request.data:
            password = str(request.data['password']).strip()
            if password:
                if len(password) < 8:
                    return Response(
                        {'error': 'La contraseña debe tener al menos 8 caracteres.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                aspirante.set_password(password)
        if 'status' in request.data:
            status_value = self._normalizar_estado(request.data['status'])
            if status_value is not None:
                aspirante.is_active = status_value

        aspirante.save()
        return Response(AspiranteAdminSerializer(aspirante).data)

    def delete(self, request, pk=None):
        """Delete an aspirante (admin only)"""
        if not pk and request.data.get('id'):
            pk = request.data['id']

        if not pk:
            return Response(
                {'error': 'Se requiere un ID de usuario.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            aspirante = Aspirante.objects.get(pk=pk, is_staff=False)
        except Aspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        aspirante.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PanelCoordinacionView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        aspirantes = Aspirante.objects.filter(is_staff=False).order_by('-created_at')
        personas = AspiranteCoordinacionSerializer(aspirantes, many=True).data
        for item, persona in zip(personas, aspirantes):
            if persona.rol not in ('docente', 'director', 'investigador'):
                continue
            materias = list(Materia.objects.filter(profesor__iexact=persona.nombre).values('id', 'clave', 'nombre', 'creditos', 'horario'))
            tesistas = list(Aspirante.objects.filter(Q(director_tesis=persona) | Q(tutor_propuesto__iexact=persona.nombre), is_staff=False).exclude(rol__in=('docente', 'director', 'investigador')).values('id', 'nombre', 'matricula', 'programa', 'proceso_estado').distinct()) if persona.rol == 'director' else []
            item.update({'materias': materias, 'total_materias': len(materias), 'horarios': [m['horario'] for m in materias if m['horario']], 'creditos_impartidos': sum(m['creditos'] or 0 for m in materias), 'tesistas': tesistas, 'total_tesistas': len(tesistas)})
        return Response({
            'resumen': {
                'total': aspirantes.count(),
                'por_revisar': aspirantes.filter(proceso_estado__in=['pendiente', 'iniciado']).count(),
                'revision': aspirantes.filter(proceso_estado='revision').count(),
                'aceptado': aspirantes.filter(proceso_estado='aceptado').count(),
            },
            'aspirantes': personas,
        })


class EstadoAspiranteCoordinacionView(APIView):
    permission_classes = [permissions.IsAdminUser]
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

        estado_anterior = aspirante.proceso_estado
        aspirante.proceso_estado = estado
        aspirante.save(update_fields=['proceso_estado', 'updated_at'])
        expediente = _crear_expediente_si_aceptado(aspirante)
        if estado == 'revision':
            detalle = 'La solicitud fue marcada en revisión por la Coordinación Académica.'
            asunto = 'Tu solicitud está en revisión'
        elif estado == 'aceptado':
            detalle = 'La solicitud fue aceptada por la Coordinación Académica.'
            asunto = 'Tu solicitud ha sido aceptada'
        else:
            detalle = 'La solicitud fue rechazada. Consulta con la Coordinación Académica para más detalles.'
            asunto = 'Tu solicitud ha sido rechazada'
        if estado != estado_anterior:
            _registrar_seguimiento(aspirante, estado, detalle, 'Coordinación Académica', notificar=True, asunto=asunto)
        respuesta = AspiranteCoordinacionSerializer(aspirante).data
        if expediente:
            respuesta['expediente_digital'] = {'id': expediente.id, 'folio': expediente.folio, 'estado': expediente.estado, 'fecha_creacion': expediente.fecha_creacion}
        return Response(respuesta)


class AspiranteCoordinacionDetailView(APIView):
    permission_classes = [permissions.IsAdminUser]

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
            _registrar_seguimiento(aspirante, aspirante.proceso_estado, f'Estado actualizado a {aspirante.proceso_estado}.', 'Coordinación Académica', notificar=True, asunto='Actualización de tu solicitud')
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
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        materias = Materia.objects.all().order_by('clave')
        return Response([MateriaSerializer(m).data for m in materias])


class CursosUploadView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        archivo = request.FILES.get('file')
        if not archivo:
            return Response({'file': 'Selecciona un archivo CSV.'}, status=status.HTTP_400_BAD_REQUEST)
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


class CargaAcademicaWorkflowView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        qs = CargaAcademica.objects.order_by('-created_at') if request.user.is_staff else CargaAcademica.objects.filter(creador=request.user)
        return Response([{'id':c.id,'estado':c.estado,'periodo':c.periodo,'comentario':c.comentario,'camunda_instance_id':c.camunda_instance_id,'created_at':c.created_at} for c in qs])
    def post(self, request):
        if not (request.user.is_staff or getattr(request.user,'rol','') in ('docente','coordinacion')): return Response(status=status.HTTP_403_FORBIDDEN)
        periodo = (request.data.get('periodo') or '').strip()
        if not periodo:
            return Response({'detail': 'Indica el periodo escolar antes de enviar la carga.'}, status=status.HTTP_400_BAD_REQUEST)
        carga=CargaAcademica.objects.create(creador=request.user,periodo=periodo,estado='en_revision')
        camunda_configurada = bool(getattr(settings, 'CAMUNDA_URL', '') or CAMUNDA_URL)
        if camunda_configurada:
            try:
                carga.camunda_instance_id = _iniciar_carga_en_camunda(carga)
                carga.save(update_fields=['camunda_instance_id', 'updated_at'])
            except http.RequestException as exc:
                carga.delete()
                logging.exception('No fue posible iniciar el proceso Camunda para la carga')
                return Response({'detail': f'Camunda no está disponible: {exc}'}, status=status.HTTP_502_BAD_GATEWAY)
        _registrar_seguimiento(request.user,'en_revision',f'Carga académica {carga.periodo or "sin periodo"} enviada a revisión.','Carga académica',notificar=True,asunto='Carga académica en revisión')
        return Response({'id':carga.id,'estado':carga.estado,'periodo':carga.periodo,'camunda_instance_id':carga.camunda_instance_id,'camunda': bool(carga.camunda_instance_id)},status=status.HTTP_201_CREATED)
    def patch(self, request, pk):
        if not request.user.is_staff: return Response(status=status.HTTP_403_FORBIDDEN)
        carga=CargaAcademica.objects.filter(pk=pk).first()
        if not carga: return Response(status=status.HTTP_404_NOT_FOUND)
        estado=request.data.get('estado')
        if estado not in dict(CargaAcademica.ESTADOS): return Response({'estado':'Estado inválido.'},status=status.HTTP_400_BAD_REQUEST)
        transiciones = {'en_revision': {'aprobada','rechazada'}, 'aprobada': {'publicada'}}
        if estado != carga.estado and estado not in transiciones.get(carga.estado, set()):
            return Response({'detail': f'No se puede pasar de {carga.estado} a {estado}.'}, status=status.HTTP_400_BAD_REQUEST)
        camunda_result = {'conectado': False, 'detalle': 'Transición local; no hay instancia Camunda asociada.'}
        try:
            if carga.estado == 'en_revision' and estado in ('aprobada', 'rechazada'):
                camunda_result = _completar_tarea_carga(carga, 'revision', {'aprobada': {'value': estado == 'aprobada', 'type': 'Boolean'}})
            elif carga.estado == 'aprobada' and estado == 'publicada':
                camunda_result = _completar_tarea_carga(carga, 'publicacion', {'publicada': {'value': True, 'type': 'Boolean'}})
        except http.RequestException as exc:
            return Response({'detail': f'No se pudo completar la aprobación en Camunda: {exc}'}, status=status.HTTP_502_BAD_GATEWAY)
        carga.estado=estado; carga.comentario=request.data.get('comentario',carga.comentario); carga.save()
        _registrar_seguimiento(carga.creador,'aceptado' if estado in ('aprobada','publicada') else estado,f'Carga académica actualizada a {estado}.','Coordinación Académica',notificar=True,asunto='Actualización de carga académica')
        return Response({'id':carga.id,'estado':carga.estado,'periodo':carga.periodo,'comentario':carga.comentario,'camunda_instance_id':carga.camunda_instance_id,'camunda':camunda_result})


class GenerarCargaView(APIView):
    permission_classes = [permissions.IsAdminUser]

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
            writer.writerows(rows)
            return FileResponse(BytesIO(('\ufeff' + output.getvalue()).encode('utf-8')), as_attachment=True, filename=f'carga_academica_{timestamp}.csv', content_type='text/csv; charset=utf-8')
        return _xlsx_response([headers] + rows, f'carga_academica_{timestamp}.xlsx', 'Carga académica SINAC NEXT')


class CoordinacionReporteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _rows(self, request):
        if not (request.user.is_staff or getattr(request.user, 'rol', '') == 'coordinacion'):
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
    permission_classes = [permissions.IsAdminUser]

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
    permission_classes = [permissions.IsAdminUser]

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
    permission_classes = [permissions.IsAdminUser]

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


class ConvertirMismaCuentaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        aspirante = request.user
        if aspirante.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if aspirante.rol == 'alumno':
            return Response({'detail': 'La cuenta ya está convertida a alumno.', 'rol': 'alumno'})
        aspirante.rol = 'alumno'
        if not aspirante.matricula:
            aspirante.matricula = f'CINV-{timezone.now().year}-{Aspirante.objects.filter(matricula__startswith=f"CINV-{timezone.now().year}-").count() + 1:04d}'
        aspirante.save(update_fields=['rol', 'matricula', 'updated_at'])
        _registrar_seguimiento(
            aspirante,
            'aceptado',
            'La cuenta del aspirante fue convertida a alumno desde el panel de seguimiento.',
            'Aspirante',
        )
        return Response({'detail': 'Tu cuenta fue convertida a alumno.', 'rol': aspirante.rol, 'matricula': aspirante.matricula})


class ConvertirAlumnoView(APIView):
    permission_classes = [permissions.IsAdminUser]

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
