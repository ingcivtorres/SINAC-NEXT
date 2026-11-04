"""Núcleo compartido: autenticación, notificaciones, integración LIDA y utilidades de exportación.

Las vistas por dominio viven en aspirante_views, inscripciones_views, alumno_views, firmas_views,
panel_admin_views, coordinacion_views y cargas_views.
"""
import logging
import uuid
from io import BytesIO

from django.conf import settings
from django.core.mail import send_mail
from django.http import FileResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import camunda
from .configuracion_sistema import email_notifications_enabled
from .models import ExpedienteDigital, SeguimientoSolicitud
from .seguridad import celda_segura
from .serializers import InicioSesionSerializer

logger = logging.getLogger(__name__)


def _crear_expediente_si_aceptado(aspirante):
    if aspirante.proceso_estado != 'aceptado':
        return None
    expediente, creado = ExpedienteDigital.objects.get_or_create(
        aspirante=aspirante,
        defaults={'folio': f'EXP-{timezone.now():%Y%m%d}-{aspirante.pk:06d}-{uuid.uuid4().hex[:4].upper()}'},
    )
    return expediente

MAX_DOCUMENTO_BYTES = 10 * 1024 * 1024


def _iniciar_carga_en_camunda(carga):
    response = camunda.post(
        '/process-definition/key/carga_academica/start',
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
    if not carga.camunda_instance_id or not camunda.rest_url():
        return {'conectado': False, 'detalle': 'La carga no tiene una instancia Camunda asociada.'}
    tareas = camunda.get(
        '/task',
        params={'processInstanceId': carga.camunda_instance_id, 'taskDefinitionKey': task_key, 'active': 'true'},
        timeout=8,
    )
    tareas.raise_for_status()
    disponibles = tareas.json()
    if not disponibles:
        return {'conectado': False, 'detalle': f'No hay una tarea Camunda activa para {task_key}.'}
    task_id = disponibles[0]['id']
    completada = camunda.post(f'/task/{task_id}/complete', json={'variables': variables}, timeout=8)
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
        sheet.append([celda_segura(valor) for valor in rows[0]])
        for cell in sheet[2]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor='008F83')
            cell.alignment = Alignment(horizontal='center')
        for row in rows[1:]:
            sheet.append([celda_segura(valor) for valor in row])
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
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle]
    throttle_scope = 'login'


class RenovarTokenView(TokenRefreshView):
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle]
    throttle_scope = 'refresh'


def _enviar_correo_notificacion(aspirante, asunto, mensaje):
    if not email_notifications_enabled():
        logger.info('Notificación por correo desactivada; se conserva el aviso interno para %s: %s', aspirante.correo, asunto)
        return False
    remitente = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'no-reply@sinac.local'
    destinatario = [aspirante.correo]
    try:
        enviado = send_mail(asunto, mensaje, remitente, destinatario, fail_silently=False)
        if not enviado:
            logger.warning('El servidor de correo no confirmó la notificación a %s: %s', aspirante.correo, asunto)
            return False
        logger.info('Notificación enviada a %s: %s', aspirante.correo, asunto)
        return True
    except Exception as exc:
        logger.warning('No se pudo enviar email de notificación a %s: %s', aspirante.correo, exc)
        return False


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
    try:
        resp = camunda.post('/process-definition/key/sinac_preregistro_v1/start', json=payload, timeout=4)
        if resp.status_code == 200:
            logger.info('Camunda: proceso iniciado business_key=%s', aspirante.business_key)
            return resp.json().get('id')          # Camunda instance id
        logger.warning('Camunda respondió %s: %s', resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.warning('Camunda no disponible: %s', exc)
    return None


def _resolver_preregistro_lida(aspirante):
    """Cierra la revisión BPMN cuando Coordinación emite una decisión final."""
    if aspirante.proceso_estado in ('aceptado', 'rechazado'):
        camunda.completar_tareas(
            'sinac_preregistro_v1', 'revision', business_key=aspirante.business_key, decision=aspirante.proceso_estado,
        )


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
        response = camunda.post('/message', json=payload, timeout=4)
        if response.status_code in (200, 204):
            logger.info('LIDA: documento notificado id=%s', documento.pk)
            return True
        logger.warning('LIDA no aceptó documento %s: %s', documento.pk, response.status_code)
    except Exception as exc:
        logger.warning('LIDA no disponible al notificar documento %s: %s', documento.pk, exc)
    return False
