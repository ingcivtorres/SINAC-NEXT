"""Solicitudes académicas y documentos descargables del alumno."""
import logging
from xml.sax.saxutils import escape
from django.db import IntegrityError, transaction
from django.http import FileResponse
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Aspirante, ConfiguracionPrograma, Inscripcion, SolicitudAcademica, PeriodoInscripcion
from .serializers import (
    SolicitudAcademicaSerializer,
)
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

from io import BytesIO
from .views import (
    _registrar_seguimiento,
)
from .inscripciones_views import _periodo_inscripcion_vigente
from .roles import bloquear_si_egresado, es_alumno, es_gestion_academica, rol_efectivo

logger = logging.getLogger(__name__)


class SolicitudAcademicaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def tipos_asignados(user):
        rol = rol_efectivo(user)
        if rol == 'servicios':
            return {'historial', 'reinscripcion'}
        if rol == 'admin':
            return set()
        if rol == 'coordinacion':
            return {'ajuste_materias'}
        return set()

    def get(self, request):
        tipos = self.tipos_asignados(request.user)
        if tipos or es_gestion_academica(request.user):
            if not tipos:
                return Response(status=status.HTTP_403_FORBIDDEN)
            solicitudes = SolicitudAcademica.objects.filter(tipo__in=tipos).select_related(
                'aspirante', 'resuelta_por',
            )
        else:
            solicitudes = request.user.solicitudes_academicas.select_related('aspirante', 'resuelta_por').all()
        return Response(SolicitudAcademicaSerializer(solicitudes, many=True).data)

    def post(self, request):
        if not es_alumno(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        bloqueo = bloquear_si_egresado(request.user)
        if bloqueo:
            return bloqueo
        tipo = request.data.get('tipo')
        comentario = (request.data.get('comentario') or '').strip()
        if tipo not in dict(SolicitudAcademica.TIPOS).keys():
            return Response({'tipo': 'Selecciona un tipo de solicitud válido.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(comentario) < 10:
            return Response({'comentario': 'Describe el motivo de la solicitud (mínimo 10 caracteres).'}, status=status.HTTP_400_BAD_REQUEST)
        if len(comentario) > 2000:
            return Response({'comentario': 'El motivo no puede superar los 2000 caracteres.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                Aspirante.objects.select_for_update().get(pk=request.user.pk)
                if SolicitudAcademica.objects.filter(aspirante=request.user, tipo=tipo, estado='pendiente').exists():
                    return Response({'detail': 'Ya tienes una solicitud de este tipo pendiente de resolución.'}, status=status.HTTP_409_CONFLICT)
                solicitud = SolicitudAcademica.objects.create(
                    aspirante=request.user,
                    tipo=tipo,
                    comentario=comentario,
                )
        except IntegrityError:
            return Response({'detail': 'Ya tienes una solicitud de este tipo pendiente de resolución.'}, status=status.HTTP_409_CONFLICT)
        detalle = f'Solicitud de {solicitud.get_tipo_display()} recibida.'
        _registrar_seguimiento(request.user, 'pendiente', detalle, 'Aspirante', notificar=True, asunto='Nueva solicitud académica')
        return Response(SolicitudAcademicaSerializer(solicitud).data, status=status.HTTP_201_CREATED)

    def patch(self, request, pk=None):
        tipos = self.tipos_asignados(request.user)
        if not tipos:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            solicitud = SolicitudAcademica.objects.select_related('aspirante').get(pk=pk, tipo__in=tipos)
        except SolicitudAcademica.DoesNotExist:
            return Response({'detail': 'No se encontró una solicitud que puedas resolver.'}, status=status.HTTP_404_NOT_FOUND)
        if solicitud.estado != 'pendiente':
            return Response({'detail': 'Esta solicitud ya fue resuelta.'}, status=status.HTTP_409_CONFLICT)

        estado = request.data.get('estado')
        respuesta = (request.data.get('respuesta_revision') or '').strip()
        if estado not in {'aceptado', 'rechazado'}:
            return Response({'estado': 'Selecciona aceptar o rechazar la solicitud.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(respuesta) < 5:
            return Response({'respuesta_revision': 'Escribe una respuesta de al menos 5 caracteres.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(respuesta) > 2000:
            return Response({'respuesta_revision': 'La respuesta no puede superar los 2000 caracteres.'}, status=status.HTTP_400_BAD_REQUEST)

        solicitud.estado = estado
        solicitud.respuesta_revision = respuesta
        solicitud.resuelta_por = request.user
        solicitud.save(update_fields=['estado', 'respuesta_revision', 'resuelta_por', 'updated_at'])
        etiqueta_area = 'Servicios Escolares' if solicitud.tipo in {'historial', 'reinscripcion'} else 'Coordinación Académica'
        detalle = (
            f'Tu solicitud de {solicitud.get_tipo_display()} fue '
            f'{solicitud.get_estado_display().lower()}. Consulta la respuesta en Solicitudes académicas.'
        )
        _registrar_seguimiento(
            solicitud.aspirante,
            estado,
            detalle,
            etiqueta_area,
            notificar=True,
            asunto='Respuesta a solicitud académica',
        )
        return Response(SolicitudAcademicaSerializer(solicitud).data)


class HorarioFormalDescargaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff: return Response(status=status.HTTP_403_FORBIDDEN)
        inscripciones = request.user.inscripciones.select_related('materia', 'periodo_inscripcion')
        periodo_id = request.query_params.get('periodo')
        if periodo_id:
            try:
                periodo = PeriodoInscripcion.objects.get(pk=periodo_id)
            except (PeriodoInscripcion.DoesNotExist, TypeError, ValueError):
                return Response({'detail': 'Selecciona un periodo válido para descargar el horario.'}, status=status.HTTP_400_BAD_REQUEST)
            inscripciones = inscripciones.filter(periodo_inscripcion=periodo)
        else:
            periodo = _periodo_inscripcion_vigente()
            if not periodo:
                periodo = request.user.inscripciones.filter(
                    periodo_inscripcion__isnull=False,
                ).select_related('periodo_inscripcion').order_by('-periodo_inscripcion__apertura').values_list(
                    'periodo_inscripcion', flat=True,
                ).first()
                periodo = PeriodoInscripcion.objects.filter(pk=periodo).first() if periodo else None
            if periodo:
                inscripciones = inscripciones.filter(periodo_inscripcion=periodo)
        inscripciones = inscripciones.order_by('materia__clave')
        datos_academicos = _datos_academicos_boleta(request.user)
        bio = BytesIO(); doc = SimpleDocTemplate(bio, pagesize=landscape(letter), rightMargin=.45*inch, leftMargin=.45*inch, topMargin=.4*inch, bottomMargin=.5*inch)
        styles = getSampleStyleSheet(); title = ParagraphStyle('HorarioFormalTitle', parent=styles['Title'], alignment=1, fontSize=13, leading=16, textColor=colors.HexColor('#00695c'))
        def logo(name, width):
            path = os.path.join('/app/frontend_assets', name)
            return Image(path, width=width, height=width*.62) if os.path.exists(path) else Paragraph('', styles['Normal'])
        header = Table([[logo('logociv.png', .72*inch), Paragraph('<b>Centro de Investigación y de Estudios Avanzados</b><br/><font size="12">Horario Académico</font>', title), logo('6-removebg-preview.png', .9*inch)]], colWidths=[1.05*inch,4.55*inch,1.05*inch])
        header.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('ALIGN',(0,0),(0,0),'LEFT'),('ALIGN',(2,0),(2,0),'RIGHT'),('LINEBELOW',(0,0),(-1,-1),1,colors.HexColor('#00695c')),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        datos = Table([
            [Paragraph(f'<b>Alumno:</b> {request.user.nombre or "—"}', styles['BodyText']), Paragraph(f'<b>Matrícula:</b> {request.user.matricula or request.user.usuario or "—"}', styles['BodyText'])],
            [Paragraph(f'<b>Programa:</b> {request.user.programa or "—"}', styles['BodyText']), Paragraph(f'<b>Unidad:</b> {request.user.unidad or "—"}', styles['BodyText'])],
            [Paragraph(f'<b>Ciclo escolar:</b> {escape(periodo.nombre) if periodo else escape(datos_academicos["periodo_escolar"])}', styles['BodyText']), Paragraph(f'<b>{datos_academicos["etiqueta_ciclo"]}:</b> {datos_academicos["numero_ciclo"]}', styles['BodyText'])],
        ], colWidths=[4.5*inch, 3.2*inch]); datos.setStyle(TableStyle([('BOX',(0,0),(-1,-1),.6,colors.HexColor('#00695c')),('INNERGRID',(0,0),(-1,-1),.3,colors.HexColor('#b8c7d1')),('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f1f8f7')),('PADDING',(0,0),(-1,-1),8)]))
        story = [header, Spacer(1,12), datos, Spacer(1,16)]
        cell = lambda value: Paragraph(str(value), ParagraphStyle('Cell', parent=styles['Normal'], fontSize=8, leading=10, wordWrap='CJK'))
        rows = [[cell('Clave del curso'),cell('Materia'),cell('Profesor'),cell('Horario'),cell('Salón / lugar'),cell('Estado'),cell('Validación')]]
        for ins in inscripciones: rows.append([cell(ins.materia.clave),cell(ins.materia.nombre),cell(ins.profesor_asignado or 'Por asignar'),cell(ins.horario_asignado or 'Por asignar'),cell(ins.salon_asignado or 'Por asignar'),cell(ins.get_estado_display()),cell(ins.get_validacion_servicios_display())])
        if len(rows) > 1:
            table = Table(rows, colWidths=[.8*inch,2.1*inch,1.45*inch,1.8*inch,1.25*inch,.85*inch,.9*inch], repeatRows=1)
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#00695c')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#b8c7d1')),('FONTSIZE',(0,0),(-1,-1),8),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f1f5f9')]),('PADDING',(0,0),(-1,-1),6)])); story.append(table)
        else: story.append(Paragraph('No hay materias inscritas para este periodo escolar.', styles['BodyText']))
        story.extend([
            Spacer(1, 28),
            Table([
                ['________________________________', ''],
                ['Firma de Servicios Escolares', 'Espacio para sello de Servicios Escolares'],
            ], colWidths=[3.7*inch,3.2*inch], rowHeights=[.32*inch,.35*inch]),
        ])
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


def _datos_academicos_boleta(alumno):
    inscripcion = (
        alumno.inscripciones.select_related('periodo_inscripcion')
        .exclude(periodo_inscripcion__isnull=True)
        .order_by('-periodo_inscripcion__apertura')
        .first()
    )
    periodo = inscripcion.periodo_inscripcion if inscripcion else _periodo_inscripcion_vigente()
    if not periodo:
        periodo = PeriodoInscripcion.objects.order_by('-apertura').first()
    configuracion = ConfiguracionPrograma.objects.filter(programa__iexact=alumno.programa, activo=True).first()
    periodicidad = getattr(configuracion, 'periodicidad', None)
    etiqueta_ciclo = {
        'semestral': 'Semestre',
        'cuatrimestral': 'Cuatrimestre',
    }.get(periodicidad, 'Periodo académico')
    return {
        'periodo_escolar': periodo.nombre if periodo else '—',
        'etiqueta_ciclo': etiqueta_ciclo,
        'numero_ciclo': getattr(alumno, 'numero_periodo_actual', None) or '—',
    }


class BoletaInscripcionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        from .servicios_views import seleccionar_inscripciones_constancia
        _, inscripciones_boleta = seleccionar_inscripciones_constancia(
            Inscripcion.objects.filter(aspirante=request.user).select_related('materia', 'periodo_inscripcion').order_by('materia__clave'),
        )
        if not inscripciones_boleta:
            return Response({'detail': 'No tienes materias inscritas en el periodo vigente.'}, status=status.HTTP_404_NOT_FOUND)
        if any(item.validacion_servicios != 'validada' for item in inscripciones_boleta):
            return Response({'detail': 'La boleta estará disponible cuando Servicios Escolares valide todas las materias del periodo.'}, status=status.HTTP_409_CONFLICT)
        matricula = getattr(request.user, 'matricula', None) or getattr(request.user, 'usuario', None) or '—'
        datos_academicos = _datos_academicos_boleta(request.user)
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
        datos = [['Nombre del alumno', request.user.nombre or '—', 'Matrícula', matricula], ['CURP', request.user.curp or '—', 'Periodo Escolar', datos_academicos['periodo_escolar']], [datos_academicos['etiqueta_ciclo'], datos_academicos['numero_ciclo'], 'Departamento', request.user.departamento or '—'], ['Programa', request.user.programa or '—', 'Unidad', request.user.unidad or '—']]
        label_style = ParagraphStyle('BoletaDataLabel', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=10)
        value_style = ParagraphStyle('BoletaDataValue', parent=styles['Normal'], fontSize=8.5, leading=10, wordWrap='CJK')
        datos = [[Paragraph(str(value), label_style if index in (0, 2) else value_style) for index, value in enumerate(row)] for row in datos]
        info = Table(datos, colWidths=[1.55*inch,2.05*inch,1.55*inch,1.85*inch])
        info.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.HexColor('#b8c7d1')),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#e7f3f1')),('BACKGROUND',(2,0),(2,-1),colors.HexColor('#e7f3f1')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        story.extend([info, Spacer(1,16)])
        course_header_style = ParagraphStyle(
            'BoletaCourseHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=10,
            textColor=colors.white,
        )
        course_cell_style = ParagraphStyle(
            'BoletaCourseCell',
            parent=styles['Normal'],
            fontSize=8.5,
            leading=10.5,
            wordWrap='CJK',
            splitLongWords=1,
        )
        course_cell = lambda value, style=course_cell_style: Paragraph(escape(str(value or '—')), style)
        rows = [[course_cell('Clave del Curso', course_header_style), course_cell('Materia', course_header_style), course_cell('Profesor', course_header_style)]]
        for ins in inscripciones_boleta:
            rows.append([
                course_cell(ins.materia.clave),
                course_cell(ins.materia.nombre),
                course_cell(ins.profesor_asignado or 'Por asignar'),
            ])
        courses = Table(rows, colWidths=[1.65*inch,3.55*inch,2.2*inch], repeatRows=1)
        courses.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#00695c')),
            ('GRID',(0,0),(-1,-1),.4,colors.HexColor('#b8c7d1')),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f8fa')]),
            ('LEFTPADDING',(0,0),(-1,-1),7),
            ('RIGHTPADDING',(0,0),(-1,-1),7),
            ('TOPPADDING',(0,0),(-1,-1),7),
            ('BOTTOMPADDING',(0,0),(-1,-1),7),
        ]))
        story.extend([courses, Spacer(1,48), Table([['Firma del estudiante','Jefe del Departamento de Coordinación Académica','Servicios escolares'],['\n\n________________','\n\n________________','\n\n________________']], colWidths=[2.2*inch]*3, style=TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold')])), Spacer(1,24), Paragraph('Documento generado por SINAC NEXT - Cinvestav Unidad Zacatenco', ParagraphStyle('Footer', parent=styles['Normal'], alignment=1, fontSize=8))])
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
        return FileResponse(bio, as_attachment=True, filename=f'{matricula}_boleta_inscripcion.pdf', content_type='application/pdf')
