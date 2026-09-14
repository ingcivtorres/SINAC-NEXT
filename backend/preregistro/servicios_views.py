"""Operaciones administrativas de Servicios Escolares.

Este módulo separa las funciones administrativas de la captura académica:
Servicios Escolares consulta y valida información, pero no modifica
calificaciones de los docentes.
"""
from io import BytesIO
import uuid

from django.db import IntegrityError
from django.db.models import Avg, Count, Q, Sum
from django.http import FileResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Aspirante, DocumentoAspirante, ExpedienteDigital, Inscripcion, SeguimientoSolicitud
from .serializers import DocumentoAspiranteSerializer, InscripcionSerializer


def es_servicios(user):
    return bool(user.is_staff or str(getattr(user, 'rol', '')).strip().lower() in {
        'servicios', 'servicios_escolares', 'servicios escolares',
    })


def fecha_texto(value):
    return value.strftime('%d/%m/%Y') if value else '—'


def serializar_alumno(alumno):
    expediente = ExpedienteDigital.objects.filter(aspirante=alumno).first()
    inscripciones = list(
        Inscripcion.objects.filter(aspirante=alumno)
        .select_related('materia')
        .order_by('materia__clave')
    )
    aprobadas = [i for i in inscripciones if i.calificacion is not None and float(i.calificacion) >= 7]
    promedio = (
        round(sum(float(i.calificacion) for i in inscripciones if i.calificacion is not None) /
              len([i for i in inscripciones if i.calificacion is not None]), 2)
        if any(i.calificacion is not None for i in inscripciones) else None
    )
    documentos = DocumentoAspirante.objects.filter(aspirante=alumno).order_by('tipo')
    movimientos = SeguimientoSolicitud.objects.filter(aspirante=alumno).order_by('-created_at')[:20]
    requisitos = {
        'matricula': bool(alumno.matricula),
        'documentos': documentos.exists(),
        'programa': bool(alumno.programa),
        'contacto': bool(alumno.correo and alumno.telefono),
    }
    return {
        'id': alumno.id,
        'nombre': alumno.nombre,
        'usuario': alumno.usuario,
        'matricula': alumno.matricula,
        'correo': alumno.correo,
        'telefono': alumno.telefono,
        'profile_photo': alumno.profile_photo.url if alumno.profile_photo else None,
        'programa': alumno.programa,
        'departamento': alumno.departamento,
        'unidad': alumno.unidad,
        'modalidad': alumno.modalidad,
        'proceso_estado': alumno.proceso_estado,
        'is_active': alumno.is_active,
        'promedio': float(alumno.promedio) if alumno.promedio is not None else None,
        'promedio_academico': promedio,
        'materias_aprobadas': len(aprobadas),
        'materias_inscritas': len(inscripciones),
        # En el modelo actual no existe un valor de créditos por materia;
        # se reporta el avance por materias aprobadas hasta que Coordinación
        # defina el catálogo oficial de créditos.
        'creditos_obtenidos': sum(int(i.materia.creditos or 0) for i in aprobadas),
        'creditos_registrados': sum(int(i.materia.creditos or 0) for i in inscripciones),
        'expediente': {
            'id': expediente.id,
            'folio': expediente.folio,
            'estado': expediente.estado,
            'fecha_creacion': expediente.fecha_creacion,
        } if expediente else None,
        'requisitos': requisitos,
        'requisitos_completos': all(requisitos.values()),
        'inscripciones': InscripcionSerializer(inscripciones, many=True).data,
        'documentos': DocumentoAspiranteSerializer(documentos, many=True).data,
        'movimientos': [
            {'id': m.id, 'estado': m.estado, 'detalle': m.detalle,
             'origen': m.origen, 'created_at': m.created_at}
            for m in movimientos
        ],
    }


class ServiciosEscolaresPanelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not es_servicios(request.user):
            return Response({'detail': 'No tienes permisos de Servicios Escolares.'}, status=status.HTTP_403_FORBIDDEN)
        alumnos = Aspirante.objects.filter(rol='alumno', is_staff=False).order_by('nombre')
        query = (request.query_params.get('q') or '').strip()
        programa = (request.query_params.get('programa') or '').strip()
        departamento = (request.query_params.get('departamento') or '').strip()
        estado = (request.query_params.get('estado') or '').strip()
        if query:
            alumnos = alumnos.filter(Q(nombre__icontains=query) | Q(usuario__icontains=query) |
                                     Q(matricula__icontains=query) | Q(correo__icontains=query))
        if programa:
            alumnos = alumnos.filter(programa=programa)
        if departamento:
            alumnos = alumnos.filter(departamento=departamento)
        if estado == 'activo':
            alumnos = alumnos.filter(is_active=True)
        elif estado == 'inactivo':
            alumnos = alumnos.filter(is_active=False)
        elif estado:
            alumnos = alumnos.filter(proceso_estado=estado)
        lista = [serializar_alumno(alumno) for alumno in alumnos]
        base = Aspirante.objects.filter(rol='alumno', is_staff=False)
        promedio = base.aggregate(valor=Avg('promedio'))['valor']
        programas = list(base.exclude(programa='').values_list('programa', flat=True).distinct().order_by('programa'))
        departamentos = list(base.exclude(departamento='').values_list('departamento', flat=True).distinct().order_by('departamento'))
        return Response({
            'alumnos': lista,
            'filtros': {'programas': programas, 'departamentos': departamentos},
            'resumen': {
                'total': base.count(),
                'activos': base.filter(is_active=True).count(),
                'inactivos': base.filter(is_active=False).count(),
                'candidatos_egreso': sum(1 for alumno in [serializar_alumno(a) for a in base] if alumno['requisitos_completos'] and alumno['materias_inscritas'] > 0),
                'promedio_institucional': round(float(promedio), 2) if promedio is not None else None,
            },
        })

    def post(self, request):
        if not es_servicios(request.user):
            return Response({'detail': 'No tienes permisos de Servicios Escolares.'}, status=status.HTTP_403_FORBIDDEN)
        requeridos = ('nombre', 'usuario', 'correo', 'curp', 'password')
        faltantes = [campo for campo in requeridos if not str(request.data.get(campo) or '').strip()]
        if faltantes:
            return Response({'detail': f'Completa los campos obligatorios: {", ".join(faltantes)}.'}, status=status.HTTP_400_BAD_REQUEST)
        password = str(request.data.get('password'))
        if len(password) < 8:
            return Response({'detail': 'La contraseña debe tener al menos 8 caracteres.'}, status=status.HTTP_400_BAD_REQUEST)
        usuario = str(request.data.get('usuario')).strip()
        correo = str(request.data.get('correo')).strip().lower()
        curp = str(request.data.get('curp')).strip().upper()
        if Aspirante.objects.filter(usuario__iexact=usuario).exists():
            return Response({'detail': 'El nombre de usuario ya está registrado.'}, status=status.HTTP_400_BAD_REQUEST)
        if Aspirante.objects.filter(correo__iexact=correo).exists():
            return Response({'detail': 'El correo ya está registrado.'}, status=status.HTTP_400_BAD_REQUEST)
        if Aspirante.objects.filter(curp__iexact=curp).exists():
            return Response({'detail': 'La CURP ya está registrada.'}, status=status.HTTP_400_BAD_REQUEST)
        alumno = Aspirante.objects.create_user(
            usuario=usuario,
            correo=correo,
            password=password,
            nombre=str(request.data.get('nombre')).strip(),
            curp=curp,
            telefono=str(request.data.get('telefono') or ''),
            matricula=str(request.data.get('matricula') or '').strip() or None,
            estado_actual='Pendiente', municipio_actual='Pendiente', direccion_actual='Pendiente',
            estado_permanente='Pendiente', municipio_permanente='Pendiente', direccion_permanente='Pendiente',
            nombre_familiar='No registrado', parentesco='No registrado', telefono_familiar='',
            ultimo_grado='No registrado', institucion='No registrado', promedio=None,
            unidad=str(request.data.get('unidad') or 'Zacatenco'),
            departamento=str(request.data.get('departamento') or 'Pendiente'),
            seccion=str(request.data.get('seccion') or 'Pendiente'),
            programa=str(request.data.get('programa') or 'Pendiente'),
            modalidad=str(request.data.get('modalidad') or 'Presencial'),
            rol='alumno', proceso_estado='activo', is_active=True,
            business_key=f'ALUM-{usuario.upper()}-{uuid.uuid4().hex[:8].upper()}',
        )
        SeguimientoSolicitud.objects.create(aspirante=alumno, estado='alta', detalle='Alumno dado de alta por Servicios Escolares.', origen='Servicios Escolares')
        return Response(serializar_alumno(alumno), status=status.HTTP_201_CREATED)


class ServiciosEscolaresAlumnoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _alumno(self, pk):
        return Aspirante.objects.filter(pk=pk, rol='alumno', is_staff=False).first()

    def patch(self, request, pk):
        if not es_servicios(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        alumno = self._alumno(pk)
        if not alumno:
            return Response({'detail': 'Alumno no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        campos = ('nombre', 'matricula', 'correo', 'telefono', 'programa', 'departamento', 'unidad', 'modalidad', 'proceso_estado', 'is_active')
        cambios = {campo: request.data[campo] for campo in campos if campo in request.data}
        if 'matricula' in cambios and not str(cambios['matricula']).strip():
            cambios['matricula'] = None
        if not cambios:
            return Response({'detail': 'No se recibieron datos administrativos para actualizar.'}, status=status.HTTP_400_BAD_REQUEST)
        for campo, valor in cambios.items():
            setattr(alumno, campo, valor)
        try:
            alumno.save(update_fields=[*cambios.keys(), 'updated_at'])
        except IntegrityError:
            return Response({'detail': 'La matrícula o el correo ya están registrados.'}, status=status.HTTP_400_BAD_REQUEST)
        SeguimientoSolicitud.objects.create(aspirante=alumno, estado='actualizado', detalle='Datos administrativos actualizados.', origen='Servicios Escolares')
        return Response(serializar_alumno(alumno))

    def post(self, request, pk):
        if not es_servicios(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        alumno = self._alumno(pk)
        if not alumno:
            return Response({'detail': 'Alumno no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        tipo = request.data.get('tipo', 'movimiento')
        detalle = (request.data.get('detalle') or '').strip()
        nuevo_estado = (request.data.get('estado') or '').strip()
        if not detalle:
            return Response({'detalle': 'Describe el movimiento administrativo.'}, status=status.HTTP_400_BAD_REQUEST)
        if nuevo_estado:
            alumno.proceso_estado = nuevo_estado
            if nuevo_estado.lower() in ('baja', 'inactivo'):
                alumno.is_active = False
            elif nuevo_estado.lower() in ('activo', 'reingreso'):
                alumno.is_active = True
            alumno.save(update_fields=['proceso_estado', 'is_active', 'updated_at'])
        movimiento = SeguimientoSolicitud.objects.create(aspirante=alumno, estado=nuevo_estado or tipo, detalle=detalle, origen='Servicios Escolares')
        return Response({'id': movimiento.id, 'estado': movimiento.estado, 'detalle': movimiento.detalle, 'alumno': serializar_alumno(alumno)}, status=status.HTTP_201_CREATED)


class ServiciosEscolaresValidacionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not es_servicios(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        alumno = Aspirante.objects.filter(pk=pk, rol='alumno', is_staff=False).first()
        if not alumno:
            return Response({'detail': 'Alumno no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        inscripcion_id = request.data.get('inscripcion_id')
        inscripciones = Inscripcion.objects.filter(aspirante=alumno)
        if inscripcion_id:
            inscripciones = inscripciones.filter(pk=inscripcion_id)
        if not inscripciones.exists():
            return Response({'detail': 'No hay inscripciones para validar.'}, status=status.HTTP_400_BAD_REQUEST)
        validar = bool(request.data.get('validar', True))
        detalle = request.data.get('comentario') or ('Inscripción validada administrativamente.' if validar else 'Inscripción devuelta para revisión administrativa.')
        movimiento = SeguimientoSolicitud.objects.create(aspirante=alumno, estado='inscripcion_validada' if validar else 'inscripcion_observada', detalle=detalle, origen='Servicios Escolares')
        return Response({'validada': validar, 'movimiento_id': movimiento.id, 'inscripciones': InscripcionSerializer(inscripciones.select_related('materia'), many=True).data})


class ServiciosEscolaresReporteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not es_servicios(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        alumnos = Aspirante.objects.filter(rol='alumno', is_staff=False)
        por_programa = list(alumnos.values('programa').annotate(total=Count('id')).order_by('-total'))
        por_departamento = list(alumnos.values('departamento').annotate(total=Count('id')).order_by('-total'))
        inscripciones = Inscripcion.objects.filter(aspirante__rol='alumno')
        return Response({
            'por_programa': por_programa,
            'por_departamento': por_departamento,
            'inscripciones': inscripciones.count(),
            'aprobadas': inscripciones.filter(calificacion__gte=7).count(),
            'reprobadas': inscripciones.filter(calificacion__lt=7).count(),
            'en_curso': inscripciones.filter(calificacion__isnull=True).count(),
            'promedio': inscripciones.filter(calificacion__isnull=False).aggregate(valor=Avg('calificacion'))['valor'],
            'creditos_obtenidos': inscripciones.filter(calificacion__gte=7).aggregate(valor=Sum('materia__creditos'))['valor'] or 0,
            'creditos_registrados': inscripciones.aggregate(valor=Sum('materia__creditos'))['valor'] or 0,
            'egresados': alumnos.filter(proceso_estado__iexact='egresado').count(),
        })


class ServiciosEscolaresDocumentoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, tipo):
        if not es_servicios(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        alumno = Aspirante.objects.filter(pk=pk, rol='alumno', is_staff=False).first()
        if not alumno:
            return Response({'detail': 'Alumno no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        inscripciones = Inscripcion.objects.filter(aspirante=alumno).select_related('materia').order_by('materia__clave')
        titulos = {'constancia': 'Constancia de estudios', 'historial': 'Historial académico', 'calificaciones': 'Constancia de calificaciones', 'inscripcion': 'Constancia de inscripción', 'egreso': 'Prevalidación de egreso'}
        if tipo not in titulos:
            return Response({'detail': 'Tipo de documento no válido.'}, status=status.HTTP_400_BAD_REQUEST)
        styles = getSampleStyleSheet()
        title = ParagraphStyle('ServiciosTitle', parent=styles['Title'], textColor=colors.HexColor('#00695c'), alignment=1, fontSize=16)
        bio = BytesIO()
        doc = SimpleDocTemplate(bio, pagesize=letter, rightMargin=.65 * inch, leftMargin=.65 * inch, topMargin=.6 * inch, bottomMargin=.6 * inch)
        story = [Paragraph('SINAC NEXT', title), Paragraph('Centro de Investigación y de Estudios Avanzados', ParagraphStyle('Institucion', parent=styles['Heading2'], alignment=1, textColor=colors.HexColor('#00695c'))), Spacer(1, 14), Paragraph(titulos[tipo], ParagraphStyle('DocTitle', parent=styles['Heading2'], alignment=1)), Spacer(1, 14)]
        datos = [['Alumno', alumno.nombre], ['Matrícula', alumno.matricula or '—'], ['Programa', alumno.programa or '—'], ['Departamento', alumno.departamento or '—'], ['Estatus', alumno.proceso_estado or '—']]
        info = Table(datos, colWidths=[1.5 * inch, 5.3 * inch])
        info.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), .35, colors.HexColor('#b8c7d1')), ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e7f3f1')), ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'), ('PADDING', (0, 0), (-1, -1), 7)]))
        story.append(info)
        if tipo in ('historial', 'calificaciones', 'egreso'):
            story.append(Spacer(1, 18))
            rows = [['Clave', 'Materia', 'Créditos', 'Final', 'Estado']]
            for item in inscripciones:
                rows.append([item.materia.clave, item.materia.nombre, item.materia.creditos, item.calificacion if item.calificacion is not None else 'Pendiente', item.get_estado_display()])
            table = Table(rows, colWidths=[.8 * inch, 3.1 * inch, .8 * inch, 1 * inch, 1.2 * inch], repeatRows=1)
            table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00695c')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), ('GRID', (0, 0), (-1, -1), .35, colors.HexColor('#b8c7d1')), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f8fa')]), ('PADDING', (0, 0), (-1, -1), 6)]))
            story.append(table)
        story.extend([Spacer(1, 30), Paragraph('Documento generado por SINAC NEXT - Cinvestav Unidad Zacatenco', ParagraphStyle('Pie', parent=styles['Normal'], alignment=1, fontSize=8, textColor=colors.HexColor('#41515a')))])
        doc.build(story)
        bio.seek(0)
        return FileResponse(bio, as_attachment=True, filename=f'{alumno.usuario}_{tipo}.pdf', content_type='application/pdf')
