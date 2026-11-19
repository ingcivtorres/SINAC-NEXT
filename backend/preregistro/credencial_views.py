"""Credencial digital del alumno: consulta, PDF, verificación pública y reposición."""
import base64
import calendar
from datetime import date
from io import BytesIO

from django.conf import settings
from django.core import signing
from django.db.models import F
from django.http import HttpResponse
from django.utils import timezone
from reportlab.graphics import renderPDF, renderSVG
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle
from rest_framework.views import APIView

from .models import Aspirante, ConfiguracionPrograma, PeriodoInscripcion, VerificacionCredencial
from .roles import es_alumno, es_gestion_academica
from .seguridad import url_media
from .servicios_views import es_servicios, ruta_logo_constancia
from .views import _registrar_seguimiento

SAL_CREDENCIAL = 'sinac.credencial'
QR_PANTALLA_SEGUNDOS = 60
QR_PANTALLA_TOLERANCIA = 30
MESES_POR_PERIODICIDAD = {'semestral': 6, 'cuatrimestral': 4}
TARJETA = (85.6 * mm, 54 * mm)
VERDE = colors.HexColor('#009383')
VERDE_AA = colors.HexColor('#00796b')
MARINO = colors.HexColor('#17213B')
GRIS = colors.HexColor('#495057')


def _sumar_meses(dia, meses):
    total = dia.month - 1 + meses
    anio, mes = dia.year + total // 12, total % 12 + 1
    return date(anio, mes, min(dia.day, calendar.monthrange(anio, mes)[1]))


def estado_credencial(alumno, hoy=None):
    """Vigente hasta el fin del último periodo en que el alumno está inscrito."""
    hoy = hoy or timezone.localdate()
    configuracion = ConfiguracionPrograma.objects.filter(programa__iexact=alumno.programa).first()
    periodo = (PeriodoInscripcion.objects.filter(inscripciones__aspirante=alumno)
               .distinct().order_by('-apertura').first())
    fin = None
    if periodo:
        meses = MESES_POR_PERIODICIDAD.get(getattr(configuracion, 'periodicidad', ''), 6)
        fin = periodo.fin_periodo or _sumar_meses(timezone.localtime(periodo.apertura).date(), meses)
    if not alumno.is_active or alumno.proceso_estado == 'baja':
        motivo = 'baja'
    elif hasattr(alumno, 'egreso'):
        motivo = 'egresado'
    elif not periodo:
        motivo = 'sin_inscripcion'
    elif hoy > fin:
        motivo = 'periodo_concluido'
    else:
        motivo = None
    return {
        'vigente': motivo is None,
        'motivo': motivo,
        'periodo': periodo.nombre if periodo else None,
        'vigencia_hasta': fin,
        'grado': configuracion.get_grado_display() if configuracion else '',
    }


def folio_credencial(alumno):
    return f'SINAC-{alumno.matricula or alumno.pk}-{alumno.credencial_version:02d}'


def generar_token(alumno, tipo, vigencia_hasta=None):
    datos = {'a': alumno.pk, 'v': alumno.credencial_version, 't': 'p' if tipo == 'pantalla' else 'i'}
    if vigencia_hasta:
        datos['h'] = vigencia_hasta.isoformat()
    # Sin compress: el token comprimido empieza con "." y nginx bloquea las rutas con "/.".
    return signing.dumps(datos, salt=SAL_CREDENCIAL)


def url_verificacion(token):
    return f'{settings.SINAC_URL_PUBLICA}/verificar/{token}'


def _qr(contenido, tamano):
    widget = QrCodeWidget(contenido, barLevel='M')
    x0, y0, x1, y1 = widget.getBounds()
    dibujo = Drawing(tamano, tamano)
    dibujo.add(widget)
    dibujo.scale(tamano / (x1 - x0), tamano / (y1 - y0))
    return dibujo


def qr_data_uri(contenido):
    svg = renderSVG.drawToString(_qr(contenido, 200))
    return 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode('utf-8')).decode('ascii')


def _es_alumno(user):
    return es_alumno(user)


class CredencialAlumnoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        alumno = request.user
        if not _es_alumno(alumno):
            return Response({'detail': 'La credencial digital solo está disponible para alumnos.'}, status=status.HTTP_403_FORBIDDEN)
        estado = estado_credencial(alumno)
        enlace = url_verificacion(generar_token(alumno, 'pantalla'))
        return Response({
            'nombre': alumno.nombre,
            'matricula': alumno.matricula,
            'programa': alumno.programa,
            'grado': estado['grado'],
            'unidad': alumno.unidad,
            'departamento': alumno.departamento,
            'foto': url_media(alumno.profile_photo),
            'folio': folio_credencial(alumno),
            'vigente': estado['vigente'],
            'motivo': estado['motivo'],
            'periodo': estado['periodo'],
            'vigencia_hasta': estado['vigencia_hasta'],
            'qr': qr_data_uri(enlace),
            'url_verificacion': enlace,
            'renovar_en': QR_PANTALLA_SEGUNDOS,
        })


def _texto(c, texto, x, y, ancho, fuente='Helvetica', tamano=7, color=colors.black, lineas=2, interlineado=None):
    c.setFont(fuente, tamano)
    c.setFillColor(color)
    partes = simpleSplit(str(texto or '-'), fuente, tamano, ancho)[:lineas]
    paso = interlineado or tamano * 1.2
    for i, parte in enumerate(partes):
        c.drawString(x, y - i * paso, parte)
    return y - len(partes) * paso


def _foto(c, alumno, x, y, ancho, alto):
    c.setStrokeColor(VERDE)
    c.setLineWidth(.8)
    try:
        imagen = ImageReader(alumno.profile_photo.path) if alumno.profile_photo else None
    except (OSError, ValueError):
        imagen = None
    if imagen:
        c.drawImage(imagen, x, y, ancho, alto, preserveAspectRatio=True, anchor='c', mask='auto')
    else:
        c.setFillColor(colors.HexColor('#E6F4F1'))
        c.rect(x, y, ancho, alto, fill=1, stroke=0)
        iniciales = ''.join(p[0] for p in str(alumno.nombre or '?').split()[:2]).upper()
        c.setFillColor(VERDE_AA)
        c.setFont('Helvetica-Bold', 16)
        c.drawCentredString(x + ancho / 2, y + alto / 2 - 5, iniciales)
    c.rect(x, y, ancho, alto, fill=0, stroke=1)


def pdf_credencial(alumno, estado):
    ancho, alto = TARJETA
    salida = BytesIO()
    c = canvas.Canvas(salida, pagesize=TARJETA)
    c.setTitle(f'Credencial {folio_credencial(alumno)}')
    c.setAuthor('SINAC NEXT · Cinvestav')

    # Frente
    c.setFillColor(VERDE_AA)
    c.rect(0, alto - 11 * mm, ancho, 11 * mm, fill=1, stroke=0)
    c.setFillColor(VERDE)
    c.rect(0, alto - 11 * mm, ancho, 1.2 * mm, fill=1, stroke=0)
    _texto(c, 'CREDENCIAL DE ALUMNO', 4 * mm, alto - 5.2 * mm, ancho - 8 * mm, 'Helvetica-Bold', 8.5, colors.white, 1)
    _texto(c, 'Cinvestav · SINAC NEXT', 4 * mm, alto - 8.8 * mm, ancho - 8 * mm, 'Helvetica', 6.5, colors.white, 1)
    _foto(c, alumno, 4 * mm, 9.5 * mm, 21 * mm, 26 * mm)
    x, w = 28.5 * mm, ancho - 32 * mm
    y = alto - 15.5 * mm
    y = _texto(c, alumno.nombre, x, y, w, 'Helvetica-Bold', 8, MARINO, 2, 9) - 1.2 * mm
    for etiqueta, valor in (('Matrícula', alumno.matricula), ('Programa', alumno.programa),
                            ('Grado', estado['grado']), ('Unidad', alumno.unidad)):
        _texto(c, etiqueta.upper(), x, y, w, 'Helvetica-Bold', 4.8, GRIS, 1)
        y = _texto(c, valor, x, y - 2.2 * mm, w, 'Helvetica', 6.4, colors.black, 2 if etiqueta == 'Programa' else 1, 7) - .9 * mm
    c.setFillColor(MARINO)
    c.rect(0, 0, ancho, 7 * mm, fill=1, stroke=0)
    vigencia = estado['vigencia_hasta'].strftime('%d/%m/%Y') if estado['vigencia_hasta'] else '-'
    _texto(c, f'VIGENTE HASTA {vigencia}', 4 * mm, 2.6 * mm, ancho / 2, 'Helvetica-Bold', 6.8, colors.white, 1)
    c.setFont('Helvetica', 6)
    c.drawRightString(ancho - 4 * mm, 2.6 * mm, f'Periodo {estado["periodo"] or "-"}')
    c.showPage()

    # Reverso
    token = generar_token(alumno, 'impresa', estado['vigencia_hasta'])
    try:
        c.drawImage(ImageReader(ruta_logo_constancia('logociv.png')), 4 * mm, alto - 15 * mm, 24 * mm, 11 * mm,
                    preserveAspectRatio=True, anchor='w', mask='auto')
    except FileNotFoundError:
        pass
    lado_qr = 32 * mm
    renderPDF.draw(_qr(url_verificacion(token), lado_qr), c, ancho - lado_qr - 3 * mm, alto - lado_qr - 4 * mm)
    y = alto - 20 * mm
    y = _texto(c, 'Verifica esta credencial escaneando el código QR.', 4 * mm, y, 44 * mm, 'Helvetica-Bold', 6.4, MARINO, 3, 7.4) - 1.5 * mm
    y = _texto(c, 'La vigencia se confirma en línea con los registros de Servicios Escolares.', 4 * mm, y, 44 * mm, 'Helvetica', 5.6, GRIS, 3, 6.6) - 1.5 * mm
    _texto(c, f'Folio: {folio_credencial(alumno)}', 4 * mm, y, 44 * mm, 'Helvetica-Bold', 5.8, colors.black, 1)
    c.setFillColor(VERDE)
    c.rect(0, 0, ancho, 5 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica', 5.4)
    c.drawCentredString(ancho / 2, 1.8 * mm, 'Documento personal e intransferible · Centro de Investigación y de Estudios Avanzados del IPN')
    c.showPage()
    c.save()
    return salida.getvalue()


class CredencialPdfView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        alumno = request.user
        if not _es_alumno(alumno):
            return Response(status=status.HTTP_403_FORBIDDEN)
        estado = estado_credencial(alumno)
        if not estado['vigente']:
            return Response({'detail': 'Tu credencial no está vigente; no se puede generar la versión impresa.', 'motivo': estado['motivo']},
                            status=status.HTTP_409_CONFLICT)
        respuesta = HttpResponse(pdf_credencial(alumno, estado), content_type='application/pdf')
        respuesta['Content-Disposition'] = f'attachment; filename="credencial-{alumno.matricula or alumno.pk}.pdf"'
        respuesta['Cache-Control'] = 'no-store'
        return respuesta


class VerificarCredencialView(APIView):
    """Consulta pública: solo expone lo necesario para identificar al alumno y su vigencia."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle]
    throttle_scope = 'verificacion'

    @staticmethod
    def _invalida(motivo, alumno=None, tipo=''):
        VerificacionCredencial.objects.create(alumno=alumno, resultado='invalida', tipo=tipo)
        return Response({'resultado': 'invalida', 'motivo': motivo, 'verificado_en': timezone.now()})

    def get(self, request, token):
        try:
            datos = signing.loads(token, salt=SAL_CREDENCIAL)
        except signing.BadSignature:
            return self._invalida('firma')
        tipo = 'pantalla' if datos.get('t') == 'p' else 'impresa'
        alumno = Aspirante.objects.filter(pk=datos.get('a'), rol='alumno').first()
        if not alumno:
            return self._invalida('firma', tipo=tipo)
        if tipo == 'pantalla':
            try:
                signing.loads(token, salt=SAL_CREDENCIAL, max_age=QR_PANTALLA_SEGUNDOS + QR_PANTALLA_TOLERANCIA)
            except signing.SignatureExpired:
                return self._invalida('qr_expirado', alumno, tipo)
        if datos.get('v') != alumno.credencial_version:
            return self._invalida('reemplazada', alumno, tipo)

        estado = estado_credencial(alumno)
        motivo = estado['motivo']
        if not motivo and tipo == 'impresa' and datos.get('h') and timezone.localdate().isoformat() > datos['h']:
            motivo = 'impresa_vencida'
        resultado = 'no_vigente' if motivo else 'vigente'
        VerificacionCredencial.objects.create(alumno=alumno, resultado=resultado, tipo=tipo)
        return Response({
            'resultado': resultado,
            'motivo': motivo,
            'tipo': tipo,
            'nombre': alumno.nombre,
            'matricula': alumno.matricula,
            'programa': alumno.programa,
            'grado': estado['grado'],
            'foto': url_media(alumno.profile_photo),
            'periodo': estado['periodo'],
            'vigencia_hasta': estado['vigencia_hasta'],
            'verificado_en': timezone.now(),
        })


class ReponerCredencialView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not (es_servicios(request.user) or es_gestion_academica(request.user)):
            return Response(status=status.HTTP_403_FORBIDDEN)
        alumno = Aspirante.objects.filter(pk=pk, rol='alumno').first()
        if not alumno:
            return Response({'detail': 'Alumno no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        Aspirante.objects.filter(pk=alumno.pk).update(credencial_version=F('credencial_version') + 1)
        alumno.refresh_from_db(fields=['credencial_version'])
        _registrar_seguimiento(alumno, 'credencial', 'Se repuso tu credencial digital; las versiones anteriores ya no son válidas.',
                               'Servicios Escolares', notificar=True, asunto='Credencial digital repuesta')
        return Response({'folio': folio_credencial(alumno), 'credencial_version': alumno.credencial_version})
