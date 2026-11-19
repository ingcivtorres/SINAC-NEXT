from io import BytesIO
import logging
from xml.sax.saxutils import escape

from django.http import FileResponse
from PIL import Image as PILImage, ImageOps
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.pdfgen import canvas as pdfgen_canvas
from reportlab.platypus import Image as PDFImage, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DocumentoAspirante, ExpedienteDigital, Inscripcion, ProyectoTesis, SeguimientoSolicitud, SolicitudAcademica
from .serializers import (
    DocumentoAspiranteSerializer,
    ExpedienteDigitalSerializer,
    FirmaElectronicaSerializer,
    InscripcionSerializer,
    ProyectoTesisSerializer,
    SeguimientoSolicitudSerializer,
    SolicitudAcademicaSerializer,
)
from .roles import es_director, es_gestion_academica, es_servicios
from .servicios_views import ruta_logo_constancia
from .seguridad import FORMATOS_IMAGEN, url_media

logger = logging.getLogger(__name__)
PIE_EXPEDIENTE = 'Documento generado por SINAC NEXT - Cinvestav Unidad Zacatenco.'


def _es_gestion(user):
    return bool(es_gestion_academica(user) or es_servicios(user))


def _es_director_del_expediente(user, expediente):
    return es_director(user) and expediente.aspirante.director_tesis_id == user.id


def _imagen_perfil_pdf(alumno):
    if not alumno.profile_photo:
        return None

    try:
        with alumno.profile_photo.open('rb') as archivo:
            imagen = ImageOps.exif_transpose(PILImage.open(archivo, formats=list(FORMATOS_IMAGEN))).convert('RGB')
            imagen.thumbnail((600, 800))
            contenido = BytesIO()
            imagen.save(contenido, format='JPEG', quality=88, optimize=True)
    except OSError:
        logger.warning('No se pudo incluir la foto de perfil del alumno %s en su expediente PDF.', alumno.pk, exc_info=True)
        return None

    contenido.seek(0)
    return PDFImage(contenido, width=1.1 * inch, height=1.35 * inch, kind='proportional')


def _codigo_qr_firma(huella):
    codigo = QrCodeWidget(huella)
    x0, y0, x1, y1 = codigo.getBounds()
    tamano = .95 * inch
    dibujo = Drawing(tamano, tamano)
    dibujo.add(codigo)
    dibujo.scale(tamano / (x1 - x0), tamano / (y1 - y0))
    return dibujo


def _bloque_firma_director_general(styles):
    etiqueta = ParagraphStyle(
        'FirmaDirectorGeneral',
        parent=styles['Normal'],
        alignment=1,
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#123d5a'),
    )
    bloque = Table(
        [[''], [Paragraph('Director General del Cinvestav', etiqueta)]],
        colWidths=[4.2 * inch],
        rowHeights=[.48 * inch, .26 * inch],
    )
    bloque.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEABOVE', (0, 1), (0, 1), .8, colors.HexColor('#526872')),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    return bloque


def _texto_hoja_expediente(pagina, total_paginas=None):
    if total_paginas is None:
        return f'Hoja {pagina}'
    return f'Hoja {pagina} de {total_paginas}'


def _dibujar_pie_expediente(canvas, documento, total_paginas=None):
    canvas.saveState()
    ancho, _ = documento.pagesize
    y = .48 * inch
    canvas.setStrokeColor(colors.HexColor('#d5e0e6'))
    canvas.setLineWidth(.6)
    canvas.line(documento.leftMargin, y, ancho - documento.rightMargin, y)
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(colors.HexColor('#526672'))
    canvas.drawCentredString(ancho / 2, .28 * inch, PIE_EXPEDIENTE)
    canvas.drawRightString(
        ancho - documento.rightMargin,
        .28 * inch,
        _texto_hoja_expediente(canvas.getPageNumber(), total_paginas),
    )
    canvas.restoreState()


class ExpedienteNumberedCanvas(pdfgen_canvas.Canvas):
    """Dibuja el pie con el total de hojas tras conocer cuántas páginas se generaron."""

    def __init__(self, *args, documento=None, **kwargs):
        self._documento = documento
        self._saved_page_states = []
        super().__init__(*args, **kwargs)

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_page_states)
        for estado in self._saved_page_states:
            self.__dict__.update(estado)
            if self._documento is not None:
                _dibujar_pie_expediente(self, self._documento, total_paginas=total)
            pdfgen_canvas.Canvas.showPage(self)
        pdfgen_canvas.Canvas.save(self)


class ExpedientePDFView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk=None):
        expediente = ExpedienteDigital.objects.select_related('aspirante', 'aspirante__egreso').filter(pk=pk).first()
        if not expediente:
            return Response({'detail': 'Expediente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if not (_es_gestion(request.user) or request.user == expediente.aspirante or _es_director_del_expediente(request.user, expediente)):
            return Response({'detail': 'No tienes permisos para consultar este expediente.'}, status=status.HTTP_403_FORBIDDEN)

        alumno = expediente.aspirante
        styles = getSampleStyleSheet()
        azul = colors.HexColor('#123d5a')
        turquesa = colors.HexColor('#168b91')
        title = ParagraphStyle('ExpTitle', parent=styles['Title'], textColor=colors.white, fontSize=16, leading=18, alignment=1)
        subtitle = ParagraphStyle('ExpSubtitle', parent=styles['Normal'], textColor=colors.white, fontSize=8, leading=10, alignment=1)
        heading = ParagraphStyle('ExpSection', parent=styles['Heading3'], textColor=azul, fontSize=10, leading=12, spaceBefore=4, spaceAfter=3)
        label = ParagraphStyle('ExpLabel', parent=styles['Normal'], textColor=colors.HexColor('#536674'), fontSize=7, leading=9)
        value = ParagraphStyle('ExpValue', parent=styles['Normal'], textColor=colors.HexColor('#1e293b'), fontSize=9, leading=11)
        small = ParagraphStyle('ExpSmall', parent=styles['Normal'], textColor=colors.HexColor('#475569'), fontSize=7, leading=9)
        column_header = ParagraphStyle('ExpTableHeader', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=colors.white, fontSize=8, leading=10)
        bio = BytesIO()
        doc = SimpleDocTemplate(
            bio,
            pagesize=letter,
            rightMargin=.65 * inch,
            leftMargin=.65 * inch,
            topMargin=.45 * inch,
            bottomMargin=.72 * inch,
        )

        logo_cinvestav = PDFImage(
            ruta_logo_constancia('logociv.png'),
            width=1.4 * inch,
            height=.45 * inch,
            kind='proportional',
        )
        encabezado = Table(
            [[
                logo_cinvestav,
                Paragraph(
                    'Centro de Investigación y de Estudios Avanzados',
                    ParagraphStyle(
                        'ExpInstitucion',
                        parent=styles['Heading2'],
                        alignment=1,
                        textColor=azul,
                        fontSize=11,
                        leading=14,
                    ),
                ),
                '',
            ]],
            colWidths=[1.55 * inch, 4.1 * inch, 1.55 * inch],
            rowHeights=[.58 * inch],
        )
        encabezado.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        banner = Table(
            [[
                Paragraph('EXPEDIENTE DIGITAL', title),
                Paragraph(f'FOLIO<br/><b>{escape(expediente.folio)}</b>', subtitle),
            ]],
            colWidths=[5.35 * inch, 1.85 * inch],
            rowHeights=[.55 * inch],
        )
        banner.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), azul),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBEFORE', (1, 0), (1, 0), 1, turquesa),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story = [encabezado, Spacer(1, 4), banner, Spacer(1, 8)]

        def tabla(filas, widths, header=False, padding=4):
            t = Table(filas, colWidths=widths, repeatRows=1 if header else 0)
            estilo = [
                ('GRID', (0, 0), (-1, -1), .35, colors.HexColor('#d5e0e6')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), padding),
                ('RIGHTPADDING', (0, 0), (-1, -1), padding),
                ('TOPPADDING', (0, 0), (-1, -1), padding),
                ('BOTTOMPADDING', (0, 0), (-1, -1), padding),
            ]
            if header:
                estilo += [('BACKGROUND', (0, 0), (-1, 0), azul), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white)]
            else:
                estilo += [('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9'))]
            t.setStyle(TableStyle(estilo))
            return t

        def celda(v, estilo=value):
            return Paragraph(escape(str(v if v not in (None, '') else '—')), estilo)

        perfil = _imagen_perfil_pdf(alumno)
        if perfil is None:
            perfil = Table([[Paragraph('FOTO<br/>NO DISPONIBLE', small)]], colWidths=[1.1 * inch], rowHeights=[1.35 * inch])
            perfil.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#edf3f6')),
                ('BOX', (0, 0), (-1, -1), .7, colors.HexColor('#b8c8d0')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
        datos_alumno = tabla([
            [celda('ALUMNO', label), celda(alumno.nombre)],
            [celda('MATRÍCULA', label), celda(alumno.matricula or alumno.usuario)],
            [celda('PROGRAMA', label), celda(alumno.programa)],
            [celda('UNIDAD / DEPARTAMENTO', label), celda(f'{alumno.unidad or "—"} / {alumno.departamento or "—"}')],
            [celda('ESTADO DEL EXPEDIENTE', label), celda(expediente.estado)],
            [celda('FECHA DE CREACIÓN', label), celda(expediente.fecha_creacion.strftime('%d/%m/%Y %H:%M'))],
        ], [1.65 * inch, 4.2 * inch], padding=5)
        perfil_y_datos = Table([[perfil, datos_alumno]], colWidths=[1.25 * inch, 5.9 * inch])
        perfil_y_datos.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(perfil_y_datos)

        egreso = getattr(alumno, 'egreso', None)
        if egreso:
            story += [Spacer(1, 6), Paragraph('Datos de egreso', heading)]
            story.append(tabla([
                [celda('Fecha de egreso', label), celda(egreso.fecha_egreso.strftime('%d/%m/%Y'))],
                [celda('Generación', label), celda(egreso.generacion)],
                [celda('Promedio final', label), celda(egreso.promedio_final)],
                [celda('Título de tesis', label), celda(egreso.titulo_tesis)],
            ], [1.65 * inch, 5.5 * inch], padding=4))

        story += [Spacer(1, 6), Paragraph('Documentos', heading)]
        documentos = DocumentoAspirante.objects.filter(aspirante=alumno).order_by('tipo')
        filas = [[celda('Documento', column_header), celda('Archivo', column_header), celda('Revisado', column_header)]]
        filas += [[celda(d.get_tipo_display()), celda(d.nombre_original), celda('Sí' if d.revisado else 'No')] for d in documentos]
        story.append(tabla(filas, [2.3 * inch, 3.5 * inch, 1.35 * inch], header=True) if len(filas) > 1 else Paragraph('Sin documentos cargados.', styles['BodyText']))

        story += [Spacer(1, 6), Paragraph('Tesis', heading)]
        proyectos = ProyectoTesis.objects.filter(alumno=alumno).select_related('director')
        filas = [[celda('Título', column_header), celda('Director', column_header), celda('Estado', column_header)]]
        filas += [[celda(p.titulo), celda(p.director.nombre if p.director else None), celda(p.get_estado_display())] for p in proyectos]
        story.append(tabla(filas, [3.3 * inch, 2.2 * inch, 1.65 * inch], header=True) if len(filas) > 1 else Paragraph('Sin proyecto de tesis.', styles['BodyText']))

        story += [Spacer(1, 6), Paragraph('Firmas electrónicas', heading)]
        firmas = list(expediente.firmas.select_related('firmante').order_by('firmado_at'))
        for firma in firmas:
            huella = firma.huella
            huella_texto = f'{escape(huella[:32])}<br/>{escape(huella[32:])}'
            detalle_firma = Table([
                [Paragraph(f'<b>{escape(firma.firmante.nombre)}</b>', value)],
                [celda(firma.get_rol_firmante_display() if hasattr(firma, 'get_rol_firmante_display') else firma.rol_firmante, small)],
                [celda(f'Firmado el {firma.firmado_at.strftime("%d/%m/%Y %H:%M")}', small)],
                [Paragraph(f'<font size="6">{huella_texto}</font>', small)],
            ], colWidths=[5.75 * inch])
            firma_card = Table([[_codigo_qr_firma(huella), detalle_firma]], colWidths=[1.15 * inch, 5.95 * inch])
            firma_card.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f9fb')),
                ('BOX', (0, 0), (-1, -1), .6, colors.HexColor('#cfdae0')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(KeepTogether([firma_card, Spacer(1, 4)]))
        cierre_firma = [_bloque_firma_director_general(styles)]
        if not firmas:
            story.append(Paragraph('El expediente aún no ha sido firmado.', styles['BodyText']))
            story.append(Spacer(1, 8))
        else:
            cierre_firma = [
                Spacer(1, 4),
                Paragraph('Escanea el código QR para consultar la huella SHA-256 de la firma electrónica.', small),
                Spacer(1, 8),
                _bloque_firma_director_general(styles),
            ]
        # Mantener la firma del director junto al cierre para que no quede aislada en otra hoja.
        story.append(KeepTogether(cierre_firma))

        doc.build(story, canvasmaker=lambda *args, **kwargs: ExpedienteNumberedCanvas(*args, documento=doc, **kwargs))
        bio.seek(0)
        return FileResponse(bio, as_attachment=request.query_params.get('inline') != '1', filename=f'{expediente.folio}.pdf', content_type='application/pdf')


class ExpedienteCentralizadoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk=None):
        expediente = ExpedienteDigital.objects.select_related('aspirante').filter(pk=pk).first()
        if not expediente:
            return Response({'detail': 'Expediente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if not (_es_gestion(request.user) or request.user == expediente.aspirante or _es_director_del_expediente(request.user, expediente)):
            return Response({'detail': 'No tienes permisos para consultar este expediente.'}, status=status.HTTP_403_FORBIDDEN)

        alumno = expediente.aspirante
        proyectos = ProyectoTesis.objects.filter(alumno=alumno).select_related('director').prefetch_related('jurados__jurado', 'defensa_tesis')
        return Response({
            'expediente': ExpedienteDigitalSerializer(expediente).data,
            'alumno': {
                'id': alumno.id,
                'nombre': alumno.nombre,
                'matricula': alumno.matricula,
                'correo': alumno.correo,
                'profile_photo': url_media(alumno.profile_photo),
                'programa': alumno.programa,
                'unidad': alumno.unidad,
                'departamento': alumno.departamento,
                'proceso_estado': alumno.proceso_estado,
            },
            'documentos': DocumentoAspiranteSerializer(DocumentoAspirante.objects.filter(aspirante=alumno).order_by('tipo'), many=True).data,
            'inscripciones': InscripcionSerializer(Inscripcion.objects.filter(aspirante=alumno).select_related('materia').order_by('materia__clave'), many=True).data,
            'solicitudes_academicas': SolicitudAcademicaSerializer(SolicitudAcademica.objects.filter(aspirante=alumno).order_by('-created_at'), many=True).data,
            'seguimiento': SeguimientoSolicitudSerializer(SeguimientoSolicitud.objects.filter(aspirante=alumno).order_by('-created_at')[:30], many=True).data,
            'firmas': FirmaElectronicaSerializer(expediente.firmas.select_related('firmante').all(), many=True).data,
            'tesis': ProyectoTesisSerializer(proyectos, many=True).data,
        })
