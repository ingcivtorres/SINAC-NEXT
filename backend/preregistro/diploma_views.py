from io import BytesIO
from xml.sax.saxutils import escape

from django.http import FileResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .jurado_views import _es_coordinacion, _es_director_del_proyecto
from .models import DefensaTesis, JuradoProyecto, ProyectoTesis
from .servicios_views import ruta_logo_constancia

VERDE = colors.HexColor('#00634F')
VERDE_OSCURO = colors.HexColor('#004738')
AZUL = colors.HexColor('#123d5a')
GRIS = colors.HexColor('#4a5c66')
CREMA = colors.HexColor('#f7faf8')
ORO = colors.HexColor('#9a7b2f')


def _fecha_formal(valor=None):
    meses = (
        'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
        'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
    )
    if not valor:
        fecha = timezone.localdate()
    else:
        fecha = timezone.localtime(valor) if timezone.is_aware(valor) else valor
    return f'{fecha.day} de {meses[fecha.month - 1]} de {fecha.year}'


def _dibujar_marco_diploma(canvas, documento):
    canvas.saveState()
    ancho, alto = documento.pagesize
    margen = 12 * mm
    # Fondo suave
    canvas.setFillColor(CREMA)
    canvas.rect(0, 0, ancho, alto, fill=1, stroke=0)
    # Marco exterior
    canvas.setStrokeColor(VERDE_OSCURO)
    canvas.setLineWidth(2.2)
    canvas.rect(margen, margen, ancho - 2 * margen, alto - 2 * margen)
    # Marco interior
    canvas.setStrokeColor(VERDE)
    canvas.setLineWidth(0.9)
    canvas.rect(margen + 4 * mm, margen + 4 * mm, ancho - 2 * margen - 8 * mm, alto - 2 * margen - 8 * mm)
    # Filete dorado
    canvas.setStrokeColor(ORO)
    canvas.setLineWidth(0.55)
    canvas.rect(margen + 6.5 * mm, margen + 6.5 * mm, ancho - 2 * margen - 13 * mm, alto - 2 * margen - 13 * mm)
    # Esquinas decorativas
    canvas.setStrokeColor(VERDE_OSCURO)
    canvas.setLineWidth(1.1)
    esquina = 8 * mm
    for x, y, dx, dy in (
        (margen + 4 * mm, margen + 4 * mm, 1, 1),
        (ancho - margen - 4 * mm, margen + 4 * mm, -1, 1),
        (margen + 4 * mm, alto - margen - 4 * mm, 1, -1),
        (ancho - margen - 4 * mm, alto - margen - 4 * mm, -1, -1),
    ):
        canvas.line(x, y, x + dx * esquina, y)
        canvas.line(x, y, x, y + dy * esquina)
    canvas.restoreState()


def _bloque_firmas(styles, director_nombre):
    etiqueta = ParagraphStyle(
        'DiplomaFirmaEtiqueta',
        parent=styles['Normal'],
        alignment=1,
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=GRIS,
    )
    nombre = ParagraphStyle(
        'DiplomaFirmaNombre',
        parent=styles['Normal'],
        alignment=1,
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=AZUL,
    )
    firmas = Table(
        [[
            Paragraph(escape(director_nombre or 'Director de tesis'), nombre),
            Paragraph('Coordinación Académica', nombre),
            Paragraph('Servicios Escolares', nombre),
        ], [
            Paragraph('Director de tesis', etiqueta),
            Paragraph('Vo. Bo. académico', etiqueta),
            Paragraph('Registro escolar', etiqueta),
        ]],
        colWidths=[3.05 * inch, 3.05 * inch, 3.05 * inch],
        rowHeights=[.55 * inch, .28 * inch],
    )
    firmas.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('LINEABOVE', (0, 0), (0, 0), .9, colors.HexColor('#526872')),
        ('LINEABOVE', (1, 0), (1, 0), .9, colors.HexColor('#526872')),
        ('LINEABOVE', (2, 0), (2, 0), .9, colors.HexColor('#526872')),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    return firmas


class DiplomaDigitalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk=None):
        proyecto = ProyectoTesis.objects.filter(pk=pk).select_related('alumno', 'director').first()
        if not proyecto:
            return Response({'detail': 'Proyecto de tesis no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        defensa = DefensaTesis.objects.filter(proyecto=proyecto).first()
        puede_consultar = (
            _es_coordinacion(request.user)
            or _es_director_del_proyecto(request.user, proyecto)
            or request.user == proyecto.alumno
            or JuradoProyecto.objects.filter(proyecto=proyecto, jurado=request.user).exists()
        )
        if not puede_consultar:
            return Response({'detail': 'No tienes permisos para consultar el diploma.'}, status=status.HTTP_403_FORBIDDEN)
        if not defensa or defensa.estado not in {'realizada', 'revisada'}:
            return Response({'detail': 'El diploma estará disponible cuando la defensa haya concluido.'}, status=status.HTTP_409_CONFLICT)
        if defensa.calificacion_final is None or float(defensa.calificacion_final) < 7:
            return Response({'detail': 'El diploma requiere una calificación final aprobatoria.'}, status=status.HTTP_409_CONFLICT)

        alumno = proyecto.alumno
        folio = f'SINAC-DIP-{proyecto.pk:06d}-{defensa.pk:06d}'
        fecha_defensa = _fecha_formal(defensa.fecha)
        fecha_emision = _fecha_formal(timezone.now())
        director_nombre = proyecto.director.nombre if proyecto.director_id else (alumno.tutor_propuesto or 'Por asignar')
        programa = alumno.programa or 'Programa de posgrado'
        unidad = alumno.unidad or 'Zacatenco'
        matricula = alumno.matricula or '—'

        buffer = BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            rightMargin=0.85 * inch,
            leftMargin=0.85 * inch,
            topMargin=0.7 * inch,
            bottomMargin=0.65 * inch,
        )
        styles = getSampleStyleSheet()
        institucion = ParagraphStyle(
            'DiplomaInstitucion', parent=styles['Normal'], fontName='Helvetica-Bold',
            fontSize=11, leading=14, alignment=1, textColor=VERDE_OSCURO,
        )
        dependencia = ParagraphStyle(
            'DiplomaDependencia', parent=styles['Normal'], fontName='Helvetica',
            fontSize=9, leading=12, alignment=1, textColor=GRIS,
        )
        titulo = ParagraphStyle(
            'DiplomaTitle', parent=styles['Title'], fontName='Times-Bold',
            fontSize=26, leading=30, alignment=1, textColor=VERDE, spaceBefore=4, spaceAfter=6,
        )
        ceremonial = ParagraphStyle(
            'DiplomaCeremonial', parent=styles['Normal'], fontName='Times-Roman',
            fontSize=11.5, leading=16, alignment=1, textColor=AZUL,
        )
        destinatario = ParagraphStyle(
            'DiplomaRecipient', parent=styles['Normal'], fontName='Times-BoldItalic',
            fontSize=22, leading=26, alignment=1, textColor=VERDE_OSCURO, spaceBefore=6, spaceAfter=6,
        )
        cuerpo = ParagraphStyle(
            'DiplomaBody', parent=styles['Normal'], fontName='Times-Roman',
            fontSize=11, leading=15, alignment=1, textColor=AZUL,
        )
        tesis = ParagraphStyle(
            'DiplomaTesis', parent=styles['Normal'], fontName='Times-Bold',
            fontSize=12, leading=16, alignment=1, textColor=VERDE_OSCURO, spaceBefore=4, spaceAfter=4,
        )
        meta = ParagraphStyle(
            'DiplomaMeta', parent=styles['Normal'], fontName='Helvetica',
            fontSize=8.5, leading=11, alignment=1, textColor=GRIS,
        )
        meta_valor = ParagraphStyle(
            'DiplomaMetaValor', parent=styles['Normal'], fontName='Helvetica-Bold',
            fontSize=9.5, leading=12, alignment=1, textColor=AZUL,
        )
        pie = ParagraphStyle(
            'DiplomaPie', parent=styles['Normal'], fontName='Helvetica',
            fontSize=7.5, leading=10, alignment=1, textColor=GRIS,
        )

        logo_cinvestav = Image(ruta_logo_constancia('logociv.png'), width=1.55 * inch, height=.5 * inch, kind='proportional')
        logo_sinac = Image(ruta_logo_constancia('SINAC5-removebg-preview.png'), width=1.45 * inch, height=.48 * inch, kind='proportional')
        encabezado = Table(
            [[
                logo_cinvestav,
                [
                    Paragraph('CENTRO DE INVESTIGACIÓN Y DE ESTUDIOS AVANZADOS', institucion),
                    Paragraph('DEL INSTITUTO POLITÉCNICO NACIONAL', dependencia),
                    Paragraph(f'Unidad {escape(unidad)} · Sistema SINAC NEXT', dependencia),
                ],
                logo_sinac,
            ]],
            colWidths=[1.7 * inch, 6.0 * inch, 1.7 * inch],
        )
        encabezado.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LINEBELOW', (0, 0), (-1, -1), 1.2, VERDE),
        ]))

        cinta = Table(
            [[Paragraph('DIPLOMA DE CONCLUSIÓN DE TESIS', ParagraphStyle(
                'DiplomaCinta', parent=styles['Normal'], fontName='Helvetica-Bold',
                fontSize=12, leading=15, alignment=1, textColor=colors.white,
            ))]],
            colWidths=[9.4 * inch],
            rowHeights=[.36 * inch],
        )
        cinta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), VERDE),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        metadatos = Table(
            [[
                Paragraph('Matrícula', meta),
                Paragraph('Programa', meta),
                Paragraph('Calificación', meta),
                Paragraph('Modalidad', meta),
                Paragraph('Folio', meta),
            ], [
                Paragraph(escape(str(matricula)), meta_valor),
                Paragraph(escape(programa), meta_valor),
                Paragraph(escape(str(defensa.calificacion_final)), meta_valor),
                Paragraph(escape(defensa.get_modalidad_display()), meta_valor),
                Paragraph(escape(folio), meta_valor),
            ]],
            colWidths=[1.55 * inch, 2.85 * inch, 1.35 * inch, 1.55 * inch, 2.1 * inch],
        )
        metadatos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#eef6f3')),
            ('BOX', (0, 0), (-1, -1), 0.7, VERDE),
            ('INNERGRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#b7d2c8')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))

        story = [
            encabezado,
            Spacer(1, 0.12 * inch),
            cinta,
            Spacer(1, 0.14 * inch),
            Paragraph('El Centro de Investigación y de Estudios Avanzados otorga el presente', ceremonial),
            Paragraph('DIPLOMA', titulo),
            Paragraph('a', ceremonial),
            Paragraph(escape(alumno.nombre), destinatario),
            Paragraph(
                f'quien concluyó satisfactoriamente la defensa de su proyecto de tesis en el programa<br/>'
                f'<b>{escape(programa)}</b>, celebrada el <b>{escape(fecha_defensa)}</b>.',
                cuerpo,
            ),
            Spacer(1, 0.06 * inch),
            Paragraph('Título de la tesis', ceremonial),
            Paragraph(f'«{escape(proyecto.titulo)}»', tesis),
            Paragraph(f'Director de tesis: <b>{escape(director_nombre)}</b>', cuerpo),
            Spacer(1, 0.12 * inch),
            metadatos,
            Spacer(1, 0.1 * inch),
            Paragraph(f'Expedido en la Ciudad de México, a {escape(fecha_emision)}.', cuerpo),
            Spacer(1, 0.18 * inch),
            KeepTogether([_bloque_firmas(styles, director_nombre)]),
            Spacer(1, 0.1 * inch),
            Paragraph(
                f'Documento oficial generado por SINAC NEXT · Folio {escape(folio)} · Emisión {escape(fecha_emision)}. '
                'La autenticidad puede verificarse ante Coordinación Académica o Servicios Escolares.',
                pie,
            ),
        ]
        document.build(story, onFirstPage=_dibujar_marco_diploma, onLaterPages=_dibujar_marco_diploma)
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=f'diploma-{folio}.pdf', content_type='application/pdf')
