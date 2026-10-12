from io import BytesIO
from xml.sax.saxutils import escape

from django.db.models import Q
from django.http import FileResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
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


def _rol(user):
    return str(getattr(user, 'rol', '') or '').strip().lower()


def _es_gestion(user):
    return bool(user.is_staff or _rol(user) in {'coordinacion', 'coordinador', 'servicios', 'servicios_escolares', 'servicios escolares'})


def _es_director_del_expediente(user, expediente):
    return _rol(user) in {'director', 'director de tesis'} and (
        expediente.aspirante.director_tesis_id == user.id
        or expediente.aspirante.tutor_propuesto.strip().lower() in {
            str(getattr(user, 'nombre', '')).strip().lower(),
            str(getattr(user, 'usuario', '')).strip().lower(),
        }
    )


class ExpedientePDFView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk=None):
        expediente = ExpedienteDigital.objects.select_related('aspirante').filter(pk=pk).first()
        if not expediente:
            return Response({'detail': 'Expediente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if not (_es_gestion(request.user) or request.user == expediente.aspirante or _es_director_del_expediente(request.user, expediente)):
            return Response({'detail': 'No tienes permisos para consultar este expediente.'}, status=status.HTTP_403_FORBIDDEN)

        alumno = expediente.aspirante
        styles = getSampleStyleSheet()
        verde = colors.HexColor('#00695c')
        title = ParagraphStyle('ExpTitle', parent=styles['Title'], textColor=verde, fontSize=18)
        bio = BytesIO()
        doc = SimpleDocTemplate(bio, pagesize=letter, rightMargin=.7*inch, leftMargin=.7*inch, topMargin=.7*inch, bottomMargin=.7*inch)
        story = [Paragraph('SINAC NEXT', title), Paragraph(f'Expediente digital {expediente.folio}', styles['Heading2']), Spacer(1, 8)]

        def tabla(filas, widths, header=False):
            t = Table(filas, colWidths=widths, repeatRows=1 if header else 0)
            estilo = [('GRID', (0, 0), (-1, -1), .35, colors.HexColor('#cbd5e1')), ('FONTSIZE', (0, 0), (-1, -1), 9), ('VALIGN', (0, 0), (-1, -1), 'TOP')]
            if header:
                estilo += [('BACKGROUND', (0, 0), (-1, 0), verde), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white)]
            else:
                estilo += [('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9'))]
            t.setStyle(TableStyle(estilo))
            return t

        celda = lambda v: Paragraph(escape(str(v if v not in (None, '') else '—')), styles['BodyText'])
        story.append(tabla([
            [celda('Alumno'), celda(alumno.nombre)],
            [celda('Matrícula'), celda(alumno.matricula or alumno.usuario)],
            [celda('Programa'), celda(alumno.programa)],
            [celda('Unidad / Departamento'), celda(f'{alumno.unidad or "—"} / {alumno.departamento or "—"}')],
            [celda('Estado del expediente'), celda(expediente.estado)],
            [celda('Fecha de creación'), celda(expediente.fecha_creacion.strftime('%d/%m/%Y %H:%M'))],
        ], [1.8*inch, 5.2*inch]))

        story += [Spacer(1, 14), Paragraph('Documentos', styles['Heading3'])]
        documentos = DocumentoAspirante.objects.filter(aspirante=alumno).order_by('tipo')
        filas = [[celda('Documento'), celda('Archivo'), celda('Revisado')]]
        filas += [[celda(d.get_tipo_display()), celda(d.nombre_original), celda('Sí' if d.revisado else 'No')] for d in documentos]
        story.append(tabla(filas, [2.6*inch, 3.2*inch, 1.2*inch], header=True) if len(filas) > 1 else Paragraph('Sin documentos cargados.', styles['BodyText']))

        story += [Spacer(1, 14), Paragraph('Tesis', styles['Heading3'])]
        proyectos = ProyectoTesis.objects.filter(alumno=alumno).select_related('director')
        filas = [[celda('Título'), celda('Director'), celda('Estado')]]
        filas += [[celda(p.titulo), celda(p.director.nombre if p.director else None), celda(p.get_estado_display())] for p in proyectos]
        story.append(tabla(filas, [3.4*inch, 2.2*inch, 1.4*inch], header=True) if len(filas) > 1 else Paragraph('Sin proyecto de tesis.', styles['BodyText']))

        story += [Spacer(1, 14), Paragraph('Firmas electrónicas', styles['Heading3'])]
        filas = [[celda('Firmante'), celda('Rol'), celda('Fecha'), celda('Huella (SHA-256)')]]
        for f in expediente.firmas.select_related('firmante').all():
            filas.append([celda(f.firmante.nombre), celda(f.get_rol_firmante_display() if hasattr(f, 'get_rol_firmante_display') else f.rol_firmante), celda(f.firmado_at.strftime('%d/%m/%Y %H:%M')), Paragraph(f'<font size="6">{f.huella}</font>', styles['BodyText'])])
        story.append(tabla(filas, [1.7*inch, 1*inch, 1.2*inch, 3.1*inch], header=True) if len(filas) > 1 else Paragraph('El expediente aún no ha sido firmado.', styles['BodyText']))

        story += [Spacer(1, 18), Paragraph('Documento generado por SINAC NEXT - Cinvestav.', styles['Normal'])]
        doc.build(story)
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
                'profile_photo': alumno.profile_photo.url if alumno.profile_photo else None,
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
