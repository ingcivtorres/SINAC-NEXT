from io import BytesIO

from django.http import FileResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .jurado_views import _es_coordinacion, _es_director
from .models import DefensaTesis, JuradoProyecto, ProyectoTesis


class DiplomaDigitalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk=None):
        proyecto = ProyectoTesis.objects.filter(pk=pk).select_related('alumno', 'director').first()
        if not proyecto:
            return Response({'detail': 'Proyecto de tesis no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        defensa = DefensaTesis.objects.filter(proyecto=proyecto).first()
        puede_consultar = (
            _es_coordinacion(request.user)
            or _es_director(request.user)
            or request.user == proyecto.alumno
            or JuradoProyecto.objects.filter(proyecto=proyecto, jurado=request.user).exists()
        )
        if not puede_consultar:
            return Response({'detail': 'No tienes permisos para consultar el diploma.'}, status=status.HTTP_403_FORBIDDEN)
        if not defensa or defensa.estado not in {'realizada', 'revisada'}:
            return Response({'detail': 'El diploma estará disponible cuando la defensa haya concluido.'}, status=status.HTTP_409_CONFLICT)
        if defensa.calificacion_final is None or float(defensa.calificacion_final) < 7:
            return Response({'detail': 'El diploma requiere una calificación final aprobatoria.'}, status=status.HTTP_409_CONFLICT)

        folio = f'SINAC-DIP-{proyecto.pk:06d}-{defensa.pk:06d}'
        buffer = BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            rightMargin=0.65 * inch,
            leftMargin=0.65 * inch,
            topMargin=0.55 * inch,
            bottomMargin=0.55 * inch,
        )
        styles = getSampleStyleSheet()
        title = ParagraphStyle('DiplomaTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=28, leading=34, alignment=1, textColor=colors.HexColor('#075b61'), spaceAfter=12)
        subtitle = ParagraphStyle('DiplomaSubtitle', parent=styles['Normal'], fontName='Helvetica', fontSize=12, leading=18, alignment=1, textColor=colors.HexColor('#334155'))
        recipient = ParagraphStyle('DiplomaRecipient', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=22, leading=28, alignment=1, textColor=colors.HexColor('#0f172a'), spaceBefore=12, spaceAfter=12)
        body = ParagraphStyle('DiplomaBody', parent=styles['Normal'], fontName='Helvetica', fontSize=12, leading=18, alignment=1, textColor=colors.HexColor('#334155'))
        small = ParagraphStyle('DiplomaSmall', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=11, alignment=1, textColor=colors.HexColor('#64748b'))

        story = [
            Spacer(1, 0.18 * inch),
            Paragraph('CENTRO DE INVESTIGACIÓN Y DE ESTUDIOS AVANZADOS', subtitle),
            Spacer(1, 0.08 * inch),
            Paragraph('DIPLOMA DIGITAL', title),
            Paragraph('Se otorga el presente reconocimiento a', subtitle),
            Paragraph(proyecto.alumno.nombre, recipient),
            Paragraph(f'por haber concluido satisfactoriamente la defensa de su proyecto de tesis:<br/><b>{proyecto.titulo}</b>', body),
            Spacer(1, 0.16 * inch),
        ]
        metadata = [[
            Paragraph(f'<b>Calificación final</b><br/>{defensa.calificacion_final}', body),
            Paragraph(f'<b>Modalidad</b><br/>{defensa.get_modalidad_display()}', body),
            Paragraph(f'<b>Folio</b><br/>{folio}', body),
        ]]
        table = Table(metadata, colWidths=[2.25 * inch] * 3)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ecf7f5')),
            ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#78bdb5')),
            ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#b7d9d4')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.extend([table, Spacer(1, 0.3 * inch), Paragraph('Documento generado por SINAC NEXT. Este diploma puede verificarse mediante su folio institucional.', small)])
        document.build(story)
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=f'diploma-{folio}.pdf', content_type='application/pdf')
