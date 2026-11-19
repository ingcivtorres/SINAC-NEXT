"""Operaciones administrativas de Servicios Escolares.

Este módulo separa las funciones administrativas de la captura académica:
Servicios Escolares consulta y valida información, pero no modifica
calificaciones de los docentes.
"""
from io import BytesIO
from pathlib import Path
import uuid
import re
from xml.sax.saxutils import escape

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Q, Sum
from django.http import FileResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Aspirante, CargaAcademicaMateria, ConfiguracionPrograma, DocumentoAspirante, ExpedienteDigital, Inscripcion, PeriodoInscripcion, SeguimientoSolicitud, SolicitudInscripcionExtemporanea
from .roles import es_gestion_academica, es_servicios, rol_efectivo
from .serializers import DocumentoAspiranteSerializer, InscripcionSerializer
from .seguridad import url_media

PIE_CONSTANCIA = 'Documento generado por SINAC NEXT - Cinvestav Unidad Zacatenco.'

MENSAJE_EGRESO_FORMAL = 'El egreso se registra desde Egresados, donde se verifica la prevalidación académica.'
ESTADOS_SIN_CONSTANCIA = {'baja', 'inactivo'}


def es_cambio_a_egresado(alumno, nuevo_estado):
    return (
        str(nuevo_estado or '').strip().lower() == 'egresado'
        and str(alumno.proceso_estado or '').strip().lower() != 'egresado'
    )


def alumno_sin_constancia(alumno):
    return not alumno.is_active or str(alumno.proceso_estado or '').strip().lower() in ESTADOS_SIN_CONSTANCIA


def fecha_texto(value):
    return value.strftime('%d/%m/%Y') if value else '—'


def ruta_logo_constancia(nombre):
    directorios = (
        Path('/app/frontend_assets'),
        Path(settings.BASE_DIR).parent / 'frontend' / 'src' / 'assets',
    )
    for directorio in directorios:
        ruta = directorio / nombre
        if ruta.is_file():
            return str(ruta)
    raise FileNotFoundError(f'No se encontró el recurso requerido para la constancia: {nombre}')


def dibujar_pie_constancia(canvas, documento):
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#41515a'))
    canvas.drawCentredString(
        letter[0] / 2,
        .3 * inch,
        PIE_CONSTANCIA,
    )
    canvas.restoreState()


def construir_pdf_con_pie(doc, story):
    doc.build(
        story,
        onFirstPage=dibujar_pie_constancia,
        onLaterPages=dibujar_pie_constancia,
    )


def bloque_firma_constancia(styles):
    estilo_etiqueta = ParagraphStyle(
        'FirmaConstancia',
        parent=styles['Normal'],
        alignment=1,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#263b46'),
    )
    estilo_sello = ParagraphStyle(
        'SelloConstancia',
        parent=estilo_etiqueta,
        textColor=colors.HexColor('#62747c'),
    )
    bloque = Table(
        [
            ['', Paragraph('Sello de Servicios Escolares', estilo_sello)],
            [Paragraph('<b>Firma de Servicios Escolares</b>', estilo_etiqueta), ''],
        ],
        colWidths=[4.35 * inch, 2.45 * inch],
        rowHeights=[.65 * inch, .35 * inch],
    )
    bloque.setStyle(TableStyle([
        ('SPAN', (1, 0), (1, 1)),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEABOVE', (0, 1), (0, 1), .8, colors.HexColor('#526872')),
        ('BOX', (1, 0), (1, 1), .8, colors.HexColor('#9aabb2')),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return bloque


def datos_documento_academico(alumno, inscripciones, prefijo_folio='CE'):
    inscripcion = (
        inscripciones.exclude(periodo_inscripcion__isnull=True)
        .select_related('periodo_inscripcion')
        .order_by('-periodo_inscripcion__apertura')
        .first()
    )
    periodo = inscripcion.periodo_inscripcion if inscripcion else None
    ahora = timezone.now()
    if not periodo:
        periodo = PeriodoInscripcion.objects.filter(
            activo=True,
            apertura__lte=ahora,
            cierre__gte=ahora,
        ).order_by('-apertura').first()
    if not periodo:
        periodo = PeriodoInscripcion.objects.order_by('-apertura').first()

    expediente_folio = ExpedienteDigital.objects.filter(aspirante=alumno).values_list('folio', flat=True).first()
    fecha_emision = timezone.localdate()
    return {
        'periodo_escolar': periodo.nombre if periodo else 'No disponible',
        'fecha_emision': fecha_emision.strftime('%d/%m/%Y'),
        'folio': expediente_folio or f'{prefijo_folio}-{fecha_emision:%Y%m%d}-{alumno.pk:06d}',
    }


def seleccionar_inscripciones_constancia(inscripciones):
    ahora = timezone.now()
    periodo = PeriodoInscripcion.objects.filter(
        activo=True,
        apertura__lte=ahora,
        cierre__gte=ahora,
    ).order_by('-apertura').first()
    if periodo:
        return periodo, list(inscripciones.filter(periodo_inscripcion=periodo))

    inscripcion = (
        inscripciones.exclude(periodo_inscripcion__isnull=True)
        .select_related('periodo_inscripcion')
        .order_by('-periodo_inscripcion__apertura')
        .first()
    )
    if inscripcion:
        periodo = inscripcion.periodo_inscripcion
        return periodo, list(inscripciones.filter(periodo_inscripcion=periodo))

    return None, list(inscripciones.filter(periodo_inscripcion__isnull=True))


def resumen_historial_academico(inscripciones):
    calificaciones = [item.calificacion for item in inscripciones if item.calificacion is not None]
    aprobadas = [item for item in inscripciones if item.calificacion is not None and item.calificacion >= 7]
    reprobadas = [item for item in inscripciones if item.calificacion is not None and item.calificacion < 7]
    en_curso = [item for item in inscripciones if item.calificacion is None]
    return {
        'materias': len(inscripciones),
        'aprobadas': len(aprobadas),
        'reprobadas': len(reprobadas),
        'en_curso': len(en_curso),
        'promedio': sum(calificaciones) / len(calificaciones) if calificaciones else None,
        'creditos_aprobados': sum(item.materia.creditos or 0 for item in aprobadas),
    }


def progreso_posgrado(alumno, inscripciones):
    configuracion = ConfiguracionPrograma.objects.filter(
        programa__iexact=alumno.programa,
        activo=True,
    ).first()
    creditos_requeridos = configuracion.creditos_requeridos if configuracion else 0
    materias_aprobadas = {
        item.materia_id: item.materia.creditos or 0
        for item in inscripciones
        if item.calificacion is not None and item.calificacion >= 7
    }
    creditos_aprobados = sum(materias_aprobadas.values())
    porcentaje = (
        min(100, round(creditos_aprobados * 100 / creditos_requeridos))
        if creditos_requeridos > 0 else None
    )
    return {
        'creditos_aprobados': creditos_aprobados,
        'creditos_requeridos': creditos_requeridos or None,
        'porcentaje': porcentaje,
    }


def celda_historial(texto, estilo):
    return Paragraph(escape(str(texto if texto not in (None, '') else '—')), estilo)


def estado_calificacion(inscripcion):
    if inscripcion.calificacion is None:
        return 'En curso'
    return 'Aprobada' if inscripcion.calificacion >= 7 else 'Reprobada'


def evaluar_prevalidacion_egreso(alumno, inscripciones, configuracion):
    motivos = []
    resumen = {
        'materias_obligatorias': 0,
        'materias_obligatorias_aprobadas': 0,
        'materias_pendientes': [],
        'creditos_aprobados': 0,
        'creditos_requeridos': configuracion.creditos_requeridos if configuracion else 0,
        'periodos_cursados': 0,
        'periodos_requeridos': configuracion.periodos_requeridos if configuracion else 0,
    }
    if not configuracion:
        return {'completa': False, 'motivos': ['El programa no tiene una configuración académica activa.'], 'resumen': resumen}

    obligatorias = [item for item in configuracion.materias_plan.all() if item.obligatoria]
    if not obligatorias:
        motivos.append('El plan no tiene materias obligatorias configuradas.')
    if configuracion.creditos_requeridos <= 0:
        motivos.append('El programa no tiene un mínimo de créditos configurado.')

    aprobadas = {
        item.materia_id
        for item in inscripciones
        if item.calificacion is not None and item.calificacion >= 7
    }
    pendientes = [item for item in obligatorias if item.materia_id not in aprobadas]
    creditos_aprobados = sum(
        item.materia.creditos or 0
        for item in inscripciones
        if item.calificacion is not None and item.calificacion >= 7
    )
    periodos_cursados = len({
        item.periodo_inscripcion_id
        for item in inscripciones
        if item.calificacion is not None and item.periodo_inscripcion_id
    })

    resumen.update({
        'materias_obligatorias': len(obligatorias),
        'materias_obligatorias_aprobadas': len(obligatorias) - len(pendientes),
        'materias_pendientes': [{'clave': item.materia.clave, 'nombre': item.materia.nombre} for item in pendientes],
        'creditos_aprobados': creditos_aprobados,
        'periodos_cursados': periodos_cursados,
    })
    if pendientes:
        motivos.append(f'Faltan {len(pendientes)} materia(s) obligatoria(s) por aprobar.')
    if configuracion.creditos_requeridos and creditos_aprobados < configuracion.creditos_requeridos:
        motivos.append(f'Faltan {configuracion.creditos_requeridos - creditos_aprobados} crédito(s) para alcanzar el umbral configurado.')
    if periodos_cursados < configuracion.periodos_requeridos:
        motivos.append(f'Faltan {configuracion.periodos_requeridos - periodos_cursados} periodo(s) concluido(s).')

    return {'completa': not motivos, 'motivos': motivos, 'resumen': resumen}


def serializar_alumno(alumno, configuraciones=None, inscripciones=None):
    expediente = ExpedienteDigital.objects.filter(aspirante=alumno).first()
    if inscripciones is None:
        inscripciones = list(Inscripcion.objects.filter(aspirante=alumno).select_related('materia', 'periodo_inscripcion').order_by('materia__clave'))
    clave_programa = str(alumno.programa or '').strip().casefold()
    if configuraciones is None:
        configuracion = ConfiguracionPrograma.objects.filter(programa__iexact=alumno.programa, activo=True).prefetch_related('materias_plan__materia').first()
    else:
        configuracion = configuraciones.get(clave_programa)
    prevalidacion_egreso = evaluar_prevalidacion_egreso(alumno, inscripciones, configuracion)
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
        'profile_photo': url_media(alumno.profile_photo),
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
        'prevalidacion_egreso': prevalidacion_egreso,
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
        base = Aspirante.objects.filter(rol='alumno', is_staff=False)
        alumnos_base = list(base.order_by('nombre'))
        alumnos_filtrados = set(alumnos.values_list('id', flat=True))
        configuraciones = {
            str(item.programa).strip().casefold(): item
            for item in ConfiguracionPrograma.objects.filter(activo=True).prefetch_related('materias_plan__materia')
        }
        inscripciones_por_alumno = {}
        for inscripcion in Inscripcion.objects.filter(aspirante_id__in=[item.id for item in alumnos_base]).select_related('materia', 'periodo_inscripcion').order_by('materia__clave'):
            inscripciones_por_alumno.setdefault(inscripcion.aspirante_id, []).append(inscripcion)
        lista = [
            serializar_alumno(alumno, configuraciones, inscripciones_por_alumno.get(alumno.id, []))
            for alumno in alumnos_base if alumno.id in alumnos_filtrados
        ]
        promedio = base.aggregate(valor=Avg('promedio'))['valor']
        programas = list(base.exclude(programa='').values_list('programa', flat=True).distinct().order_by('programa'))
        departamentos = list(base.exclude(departamento='').values_list('departamento', flat=True).distinct().order_by('departamento'))
        return Response({
            'alumnos': lista,
            'filtros': {'programas': programas, 'departamentos': departamentos},
            'resumen': {
                'total': len(alumnos_base),
                'activos': sum(1 for alumno in alumnos_base if alumno.is_active),
                'inactivos': sum(1 for alumno in alumnos_base if not alumno.is_active),
                'candidatos_egreso': sum(
                    1 for alumno in alumnos_base
                    if alumno.is_active
                    and alumno.proceso_estado not in ('baja', 'egresado')
                    and evaluar_prevalidacion_egreso(
                        alumno,
                        inscripciones_por_alumno.get(alumno.id, []),
                        configuraciones.get(str(alumno.programa or '').strip().casefold()),
                    )['completa']
                ),
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
        if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or not re.search(r'[0-9]', password):
            return Response({'detail': 'La contraseña debe tener 8 caracteres, mayúscula, minúscula y número.'}, status=status.HTTP_400_BAD_REQUEST)
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
        if es_cambio_a_egresado(alumno, cambios.get('proceso_estado')):
            return Response({'detail': MENSAJE_EGRESO_FORMAL}, status=status.HTTP_400_BAD_REQUEST)
        if not cambios:
            return Response({'detail': 'No se recibieron datos administrativos para actualizar.'}, status=status.HTTP_400_BAD_REQUEST)
        valores_anteriores = {campo: getattr(alumno, campo) for campo in cambios}
        for campo, valor in cambios.items():
            setattr(alumno, campo, valor)
        try:
            alumno.save(update_fields=[*cambios.keys(), 'updated_at'])
        except IntegrityError:
            return Response({'detail': 'La matrícula o el correo ya están registrados.'}, status=status.HTTP_400_BAD_REQUEST)
        cambios_texto = ', '.join(
            f'{campo}: {valores_anteriores[campo] or "—"} → {getattr(alumno, campo) or "—"}'
            for campo in cambios if valores_anteriores[campo] != getattr(alumno, campo)
        )
        SeguimientoSolicitud.objects.create(aspirante=alumno, estado='actualizado', detalle=f'Datos administrativos actualizados: {cambios_texto or "sin cambios de valor"}.', origen='Servicios Escolares')
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
        if es_cambio_a_egresado(alumno, nuevo_estado):
            return Response({'detail': MENSAJE_EGRESO_FORMAL}, status=status.HTTP_400_BAD_REQUEST)
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
        raw_validar = request.data.get('validar', True)
        if isinstance(raw_validar, bool):
            validar = raw_validar
        elif str(raw_validar).strip().lower() in ('true', '1', 'si', 'sí'):
            validar = True
        elif str(raw_validar).strip().lower() in ('false', '0', 'no'):
            validar = False
        else:
            return Response({'validar': 'Debe ser un valor booleano.'}, status=status.HTTP_400_BAD_REQUEST)
        comentario = str(request.data.get('comentario') or '').strip()
        if not validar and not comentario:
            return Response({'comentario': 'Explica el motivo de la observación.'}, status=status.HTTP_400_BAD_REQUEST)
        detalle = (
            f'Inscripción observada por Servicios Escolares. Motivo: {comentario}'
            if not validar
            else comentario or 'Inscripción validada administrativamente.'
        )
        with transaction.atomic():
            inscripciones.update(validacion_servicios='validada' if validar else 'observada', updated_at=timezone.now())
            movimiento = SeguimientoSolicitud.objects.create(aspirante=alumno, estado='inscripcion_validada' if validar else 'inscripcion_observada', detalle=detalle, origen='Servicios Escolares')
        return Response({'validada': validar, 'movimiento_id': movimiento.id, 'inscripciones': InscripcionSerializer(inscripciones.select_related('materia'), many=True).data})


class SolicitudesExtemporaneasServiciosView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def serializar(solicitud):
        return {
            'id': solicitud.id,
            'folio': f'EXT-{solicitud.created_at.year}-{solicitud.id:06d}',
            'alumno_id': solicitud.alumno_id,
            'alumno_nombre': solicitud.alumno.nombre,
            'alumno_matricula': solicitud.alumno.matricula or '',
            'programa': solicitud.alumno.programa or '',
            'periodo_id': solicitud.periodo_inscripcion_id,
            'periodo': solicitud.periodo_inscripcion.nombre,
            'motivo': solicitud.motivo,
            'estado': solicitud.estado,
            'comentario_revision': solicitud.comentario_revision,
            'solicitante': solicitud.solicitante.nombre,
            'revisor': solicitud.revisado_por.nombre if solicitud.revisado_por else '',
            'materias': [{
                'id': item.carga_materia.materia_id,
                'clave': item.carga_materia.materia.clave,
                'nombre': item.carga_materia.materia.nombre,
                'creditos': item.carga_materia.materia.creditos,
                'profesor': item.carga_materia.docente.nombre if item.carga_materia.docente else item.carga_materia.materia.profesor,
                'horario': item.carga_materia.horario,
                'salon': item.carga_materia.get_salon_display(),
            } for item in solicitud.materias_solicitadas.select_related(
                'carga_materia__materia', 'carga_materia__docente',
            ).order_by('carga_materia__materia__clave')],
            'created_at': solicitud.created_at,
            'updated_at': solicitud.updated_at,
        }

    def get(self, request, pk=None):
        if not es_servicios(request.user):
            return Response({'detail': 'No tienes permisos de Servicios Escolares.'}, status=status.HTTP_403_FORBIDDEN)
        solicitudes = SolicitudInscripcionExtemporanea.objects.select_related(
            'alumno', 'periodo_inscripcion', 'solicitante', 'revisado_por',
        ).prefetch_related('materias_solicitadas__carga_materia__materia', 'materias_solicitadas__carga_materia__docente')
        if pk is not None:
            solicitud = solicitudes.filter(pk=pk).first()
            if not solicitud:
                return Response({'detail': 'No se encontró la solicitud.'}, status=status.HTTP_404_NOT_FOUND)
            return Response(self.serializar(solicitud))
        return Response([self.serializar(solicitud) for solicitud in solicitudes])

    def patch(self, request, pk=None):
        if not es_servicios(request.user):
            return Response({'detail': 'No tienes permisos de Servicios Escolares.'}, status=status.HTTP_403_FORBIDDEN)
        solicitud = SolicitudInscripcionExtemporanea.objects.filter(pk=pk).first()
        if not solicitud:
            return Response({'detail': 'No se encontró la solicitud.'}, status=status.HTTP_404_NOT_FOUND)
        if solicitud.estado != 'pendiente':
            return Response({'detail': 'La solicitud ya fue resuelta.'}, status=status.HTTP_409_CONFLICT)
        estado = request.data.get('estado')
        if estado not in {'aprobada', 'rechazada'}:
            return Response({'estado': 'Selecciona aprobar o rechazar la solicitud.'}, status=status.HTTP_400_BAD_REQUEST)
        comentario = str(request.data.get('comentario_revision') or '').strip()
        if estado == 'rechazada' and not comentario:
            return Response({'comentario_revision': 'Explica el motivo del rechazo.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                solicitud = SolicitudInscripcionExtemporanea.objects.select_for_update().select_related(
                    'alumno', 'periodo_inscripcion', 'solicitante',
                ).get(pk=pk)
                if solicitud.estado != 'pendiente':
                    return Response({'detail': 'La solicitud ya fue resuelta.'}, status=status.HTTP_409_CONFLICT)
                if estado == 'aprobada':
                    carga_materia_ids = list(
                        solicitud.materias_solicitadas.order_by('carga_materia_id').values_list(
                            'carga_materia_id', flat=True,
                        )
                    )
                    if not carga_materia_ids:
                        return Response({'detail': 'La solicitud no contiene materias.'}, status=status.HTTP_409_CONFLICT)
                    list(
                        CargaAcademicaMateria.objects.select_for_update()
                        .filter(pk__in=carga_materia_ids)
                        .order_by('pk')
                        .values_list('pk', flat=True)
                    )
                    detalles = list(
                        CargaAcademicaMateria.objects.filter(pk__in=carga_materia_ids)
                        .select_related('materia', 'docente')
                        .order_by('materia__clave')
                    )
                    materias_ids = [detalle.materia_id for detalle in detalles]
                    if Inscripcion.objects.filter(
                        aspirante=solicitud.alumno,
                        periodo_inscripcion=solicitud.periodo_inscripcion,
                        materia_id__in=materias_ids,
                    ).exists():
                        return Response({'detail': 'El alumno ya tiene una de las materias solicitadas en este periodo.'}, status=status.HTTP_409_CONFLICT)
                    llenas = [
                        detalle.materia.clave for detalle in detalles
                        if Inscripcion.objects.filter(
                            periodo_inscripcion=solicitud.periodo_inscripcion,
                            materia_id=detalle.materia_id,
                        ).count() >= detalle.capacidad
                    ]
                    if llenas:
                        return Response(
                            {'detail': f'Ya no hay cupo en: {", ".join(llenas)}.'},
                            status=status.HTTP_409_CONFLICT,
                        )
                    Inscripcion.objects.bulk_create([
                        Inscripcion(
                            aspirante=solicitud.alumno,
                            materia=detalle.materia,
                            periodo_inscripcion=solicitud.periodo_inscripcion,
                            horario=detalle.horario,
                            extemporanea=True,
                            motivo_extemporanea=solicitud.motivo,
                            registrada_por=solicitud.solicitante,
                            validacion_servicios='validada',
                        )
                        for detalle in detalles
                    ])
                solicitud.estado = estado
                solicitud.comentario_revision = comentario
                solicitud.revisado_por = request.user
                solicitud.save(update_fields=['estado', 'comentario_revision', 'revisado_por', 'updated_at'])
        except IntegrityError:
            return Response({'detail': 'Las inscripciones ya fueron registradas para este periodo.'}, status=status.HTTP_409_CONFLICT)

        detalle = (
            f'La solicitud de inscripción extemporánea para {solicitud.periodo_inscripcion.nombre} fue '
            f'{"aprobada" if estado == "aprobada" else "rechazada"} por Servicios Escolares.'
        )
        if comentario:
            detalle = f'{detalle} Comentario: {comentario}'
        SeguimientoSolicitud.objects.create(
            aspirante=solicitud.alumno,
            estado=f'inscripcion_extemporanea_{estado}',
            detalle=detalle,
            origen='Servicios Escolares',
        )
        solicitud = SolicitudInscripcionExtemporanea.objects.select_related(
            'alumno', 'periodo_inscripcion', 'solicitante', 'revisado_por',
        ).prefetch_related('materias_solicitadas__carga_materia__materia', 'materias_solicitadas__carga_materia__docente').get(pk=solicitud.pk)
        return Response(self.serializar(solicitud))

    @staticmethod
    def descargar_oficio(request, pk, permitir_coordinacion=False):
        es_coordinacion = es_gestion_academica(request.user) and not (
            es_servicios(request.user) and not request.user.is_superuser
        )
        if not es_servicios(request.user) and not (permitir_coordinacion and es_coordinacion):
            return Response({'detail': 'No tienes permisos de Servicios Escolares.'}, status=status.HTTP_403_FORBIDDEN)
        solicitud = SolicitudInscripcionExtemporanea.objects.select_related(
            'alumno', 'periodo_inscripcion', 'revisado_por',
        ).prefetch_related('materias_solicitadas__carga_materia__materia', 'materias_solicitadas__carga_materia__docente').filter(pk=pk).first()
        if not solicitud:
            return Response({'detail': 'No se encontró la solicitud.'}, status=status.HTTP_404_NOT_FOUND)
        if solicitud.estado != 'aprobada':
            return Response({'detail': 'El oficio estará disponible cuando Servicios Escolares apruebe la solicitud.'}, status=status.HTTP_409_CONFLICT)

        folio = f'EXT-{solicitud.created_at.year}-{solicitud.id:06d}'
        buffer = BytesIO()
        document = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=.7 * inch, leftMargin=.7 * inch, topMargin=.65 * inch, bottomMargin=.65 * inch)
        styles = getSampleStyleSheet()
        title = ParagraphStyle('OficioTitle', parent=styles['Title'], alignment=1, textColor=colors.HexColor('#00695c'), fontSize=14)
        body = ParagraphStyle('OficioBody', parent=styles['BodyText'], leading=15, spaceAfter=10)
        safe = lambda value: escape(str(value or '—'))
        story = [
            Paragraph('CENTRO DE INVESTIGACIÓN Y DE ESTUDIOS AVANZADOS', title),
            Paragraph('SERVICIOS ESCOLARES', ParagraphStyle('OficioDept', parent=styles['Heading2'], alignment=1, textColor=colors.HexColor('#00695c'))),
            Paragraph(f'<b>Oficio:</b> {folio}<br/><b>Fecha:</b> {timezone.localtime(solicitud.updated_at).strftime("%d/%m/%Y")}<br/><b>Asunto:</b> Autorización de inscripción extemporánea', body),
            Paragraph('A quien corresponda:', body),
            Paragraph(
                f'Por medio del presente, Servicios Escolares hace constar que fue autorizada la inscripción extemporánea '
                f'de <b>{safe(solicitud.alumno.nombre)}</b>, matrícula <b>{safe(solicitud.alumno.matricula)}</b>, '
                f'del programa <b>{safe(solicitud.alumno.programa)}</b>, correspondiente al periodo '
                f'<b>{safe(solicitud.periodo_inscripcion.nombre)}</b>. La autorización se emite con base en el motivo '
                f'registrado en la solicitud: “{safe(solicitud.motivo)}”.',
                body,
            ),
        ]
        rows = [['Clave', 'Materia', 'Docente', 'Horario', 'Salón']]
        for item in solicitud.materias_solicitadas.select_related('carga_materia__materia', 'carga_materia__docente').order_by('carga_materia__materia__clave'):
            detalle = item.carga_materia
            rows.append([
                safe(detalle.materia.clave), safe(detalle.materia.nombre),
                safe(detalle.docente.nombre if detalle.docente else detalle.materia.profesor),
                safe(detalle.horario), safe(detalle.get_salon_display()),
            ])
        table = Table(rows, colWidths=[.75 * inch, 2.0 * inch, 1.55 * inch, 1.55 * inch, 1.2 * inch], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00695c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), .4, colors.HexColor('#b8c7d1')),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f1f5f9')]),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.extend([
            table,
            Spacer(1, 18),
            Paragraph('Se expide el presente oficio para los fines académicos y administrativos correspondientes.', body),
            Spacer(1, 32),
            Table([
                ['________________________________', ''],
                ['Nombre y firma de quien autoriza', 'Sello de Servicios Escolares'],
            ], colWidths=[3.7 * inch, 3.2 * inch], rowHeights=[.32 * inch, .35 * inch]),
        ])
        document.build(story)
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=f'{folio}_oficio_inscripcion_extemporanea.pdf', content_type='application/pdf')


class OficioInscripcionExtemporaneaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        return SolicitudesExtemporaneasServiciosView.descargar_oficio(request, pk)


class OficioInscripcionExtemporaneaCoordinacionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        return SolicitudesExtemporaneasServiciosView.descargar_oficio(request, pk, permitir_coordinacion=True)


class ServiciosEscolaresReporteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not es_servicios(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        alumnos = Aspirante.objects.filter(rol='alumno', is_staff=False)
        query = (request.query_params.get('q') or '').strip()
        programa = (request.query_params.get('programa') or '').strip()
        departamento = (request.query_params.get('departamento') or '').strip()
        estado = (request.query_params.get('estado') or '').strip()
        if query:
            alumnos = alumnos.filter(Q(nombre__icontains=query) | Q(usuario__icontains=query) | Q(matricula__icontains=query) | Q(correo__icontains=query))
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
        por_programa = list(alumnos.values('programa').annotate(total=Count('id')).order_by('-total'))
        por_departamento = list(alumnos.values('departamento').annotate(total=Count('id')).order_by('-total'))
        inscripciones = Inscripcion.objects.filter(aspirante_id__in=alumnos.values('id'))
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
        es_personal = rol_efectivo(request.user) in {
            'admin', 'coordinacion', 'servicios',
        } or request.user.is_superuser
        if es_personal:
            alumno = Aspirante.objects.filter(pk=pk, rol='alumno', is_staff=False).first()
        elif int(pk) == int(getattr(request.user, 'id', -1)):
            alumno = Aspirante.objects.filter(pk=pk, rol='alumno', is_staff=False).first()
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if not alumno:
            return Response({'detail': 'Alumno no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        orden_inscripciones = (
            ('periodo_inscripcion__apertura', 'materia__clave')
            if tipo in ('historial', 'calificaciones')
            else ('materia__clave',)
        )
        inscripciones = Inscripcion.objects.filter(aspirante=alumno).select_related(
            'materia', 'periodo_inscripcion',
        ).order_by(*orden_inscripciones)
        titulos = {'constancia': 'Constancia de estudios', 'historial': 'Historial académico', 'calificaciones': 'Constancia de calificaciones', 'inscripcion': 'Constancia de inscripción', 'egreso': 'Prevalidación académica de egreso (orientativa)'}
        if tipo not in titulos:
            return Response({'detail': 'Tipo de documento no válido.'}, status=status.HTTP_400_BAD_REQUEST)
        if tipo == 'constancia' and alumno_sin_constancia(alumno):
            return Response(
                {'detail': 'No se emite constancia de estudios para alumnos dados de baja o inactivos.'},
                status=status.HTTP_409_CONFLICT,
            )
        periodo_constancia = None
        inscripciones_constancia = []
        if tipo == 'inscripcion':
            periodo_constancia, inscripciones_constancia = seleccionar_inscripciones_constancia(
                inscripciones,
            )
            if not es_personal and (
                not inscripciones_constancia
                or any(item.validacion_servicios != 'validada' for item in inscripciones_constancia)
            ):
                return Response(
                    {'detail': 'La constancia de inscripción estará disponible cuando Servicios Escolares valide todas las materias del periodo.'},
                    status=status.HTTP_409_CONFLICT,
                )
        styles = getSampleStyleSheet()
        title = ParagraphStyle('ServiciosTitle', parent=styles['Title'], textColor=colors.HexColor('#00695c'), alignment=1, fontSize=16)
        bio = BytesIO()
        doc = SimpleDocTemplate(
            bio,
            pagesize=letter,
            rightMargin=.65 * inch,
            leftMargin=.65 * inch,
            topMargin=.65 * inch,
            bottomMargin=.72 * inch,
        )
        prevalidacion = None
        if tipo == 'egreso':
            configuracion = ConfiguracionPrograma.objects.filter(
                programa__iexact=alumno.programa,
                activo=True,
            ).prefetch_related('materias_plan__materia').first()
            inscripciones_egreso = list(inscripciones)
            prevalidacion = evaluar_prevalidacion_egreso(alumno, inscripciones_egreso, configuracion)
        if tipo in ('constancia', 'historial', 'calificaciones', 'inscripcion', 'egreso'):
            logo_cinvestav = Image(ruta_logo_constancia('logociv.png'), width=1.4 * inch, height=.45 * inch, kind='proportional')
            logo_sinac = Image(ruta_logo_constancia('SINAC5-removebg-preview.png'), width=1.4 * inch, height=.45 * inch, kind='proportional')
            encabezado = Table(
                [[
                    logo_cinvestav,
                    Paragraph(
                        'Centro de Investigación y de Estudios Avanzados',
                        ParagraphStyle('InstitucionConstancia', parent=styles['Heading2'], alignment=1, textColor=colors.HexColor('#00695c'), fontSize=11),
                    ),
                    logo_sinac,
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
            titulo_documento = Table(
                [[Paragraph(
                    titulos[tipo].upper(),
                    ParagraphStyle('DocTitleInstitucional', parent=styles['Heading2'], alignment=1, textColor=colors.white, fontSize=15, leading=18),
                )]],
                colWidths=[6.8 * inch],
            )
            titulo_documento.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#00695c')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            encabezado.setStyle(TableStyle([
                ('LINEBELOW', (0, 0), (-1, -1), 1, colors.HexColor('#d2dfdc')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            story = [
                encabezado,
                Spacer(1, 15),
                titulo_documento,
                Spacer(1, 18),
                Paragraph(
                    'INFORMACIÓN DEL ESTUDIANTE',
                    ParagraphStyle('SeccionInstitucional', parent=styles['Heading3'], textColor=colors.HexColor('#00695c'), fontSize=10, leading=13),
                ),
                Spacer(1, 5),
            ]
        else:
            story = [Paragraph('SINAC NEXT', title), Paragraph('Centro de Investigación y de Estudios Avanzados', ParagraphStyle('Institucion', parent=styles['Heading2'], alignment=1, textColor=colors.HexColor('#00695c'))), Spacer(1, 14), Paragraph(titulos[tipo], ParagraphStyle('DocTitle', parent=styles['Heading2'], alignment=1)), Spacer(1, 14)]
        datos = [
            ['Alumno', alumno.nombre],
            ['Matrícula', alumno.matricula or '—'],
            ['Programa', alumno.programa or '—'],
            ['Departamento', alumno.departamento or '—'],
            ['Estatus', alumno.proceso_estado or '—'],
        ]
        datos_emision = None
        if tipo in ('constancia', 'historial', 'calificaciones', 'inscripcion', 'egreso'):
            prefijo_folio = {
                'constancia': 'CE',
                'historial': 'HA',
                'calificaciones': 'CC',
                'inscripcion': 'CI',
                'egreso': 'PE',
            }[tipo]
            datos_emision = datos_documento_academico(alumno, inscripciones, prefijo_folio)
        if tipo == 'constancia':
            datos.extend([
                ['Periodo escolar', datos_emision['periodo_escolar']],
                ['Fecha de expedición', datos_emision['fecha_emision']],
                ['Folio', datos_emision['folio']],
            ])
        elif tipo in ('historial', 'calificaciones', 'egreso'):
            datos.extend([
                ['Fecha de expedición', datos_emision['fecha_emision']],
                ['Folio', datos_emision['folio']],
            ])
        elif tipo == 'inscripcion':
            datos.extend([
                ['Periodo escolar', periodo_constancia.nombre if periodo_constancia else 'No disponible'],
                ['Fecha de expedición', datos_emision['fecha_emision']],
                ['Folio', datos_emision['folio']],
            ])
        info = Table(datos, colWidths=[1.5 * inch, 5.3 * inch])
        info.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), .35, colors.HexColor('#d5e0e4')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e7f3f1')),
            ('ROWBACKGROUNDS', (1, 0), (1, -1), [colors.white, colors.HexColor('#f7fafb')]),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#264b4b')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 9),
            ('RIGHTPADDING', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(info)
        if tipo == 'constancia':
            story.extend([
                Spacer(1, 18),
                Paragraph(
                    (
                        f'<b>A quien corresponda:</b> Se hace constar que '
                        f'<b>{escape(alumno.nombre or "—")}</b> se encuentra inscrito(a) '
                        f'en el programa de <b>{escape(alumno.programa or "—")}</b> '
                        f'durante el periodo escolar <b>{escape(datos_emision["periodo_escolar"])}</b>.'
                    ),
                    ParagraphStyle(
                        'TextoConstancia',
                        parent=styles['BodyText'],
                        fontSize=10,
                        leading=16,
                        spaceAfter=8,
                    ),
                ),
                Spacer(1, 28),
                bloque_firma_constancia(styles),
            ])
        if tipo in ('historial', 'calificaciones'):
            historial_items = list(inscripciones)
            resumen = resumen_historial_academico(historial_items)
            promedio = f'{resumen["promedio"]:.2f}' if resumen['promedio'] is not None else '—'
            if tipo == 'historial':
                avance_posgrado = progreso_posgrado(alumno, historial_items)
                porcentaje = avance_posgrado['porcentaje']
                if porcentaje is None:
                    avance_texto = 'No disponible: faltan configurar los créditos requeridos del programa.'
                    barra_avance = None
                else:
                    avance_texto = (
                        f'{porcentaje}% del posgrado · '
                        f'{avance_posgrado["creditos_aprobados"]} de '
                        f'{avance_posgrado["creditos_requeridos"]} créditos aprobados'
                    )
                    ancho_barra = 6.8 * inch
                    ancho_progreso = ancho_barra * porcentaje / 100
                    if porcentaje == 0:
                        ancho_progreso = .02 * inch
                    elif porcentaje == 100:
                        ancho_progreso = ancho_barra
                    barra_avance = Table(
                        [['', '']],
                        colWidths=[ancho_progreso, ancho_barra - ancho_progreso],
                        rowHeights=[.16 * inch],
                    )
                    barra_avance.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#008577')),
                        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#e3ecea')),
                        ('BOX', (0, 0), (-1, -1), .35, colors.HexColor('#c6d6d2')),
                    ]))
                elementos_avance = [
                    Spacer(1, 14),
                    Paragraph(
                        'AVANCE DEL POSGRADO',
                        ParagraphStyle('TituloAvancePosgrado', parent=styles['Heading3'], textColor=colors.HexColor('#00695c'), fontSize=10),
                    ),
                    Spacer(1, 5),
                    Paragraph(
                        f'<b>{escape(avance_texto)}</b>',
                        ParagraphStyle('TextoAvancePosgrado', parent=styles['BodyText'], fontSize=9, leading=13, textColor=colors.HexColor('#315c59')),
                    ),
                ]
                if barra_avance:
                    elementos_avance.extend([Spacer(1, 5), barra_avance])
                story.extend(elementos_avance)
            if tipo == 'calificaciones':
                etiquetas_resumen = ['MATERIAS CALIFICADAS', 'APROBADAS', 'REPROBADAS']
                valores_resumen = [
                    str(resumen['aprobadas'] + resumen['reprobadas']),
                    str(resumen['aprobadas']),
                    str(resumen['reprobadas']),
                ]
                etiquetas_extra = ['EN CURSO', 'PROMEDIO', 'CRÉDITOS APROBADOS']
                valores_extra = [
                    str(resumen['en_curso']),
                    promedio,
                    str(resumen['creditos_aprobados']),
                ]
            else:
                etiquetas_resumen = ['MATERIAS', 'APROBADAS', 'EN CURSO']
                valores_resumen = [
                    str(resumen['materias']),
                    str(resumen['aprobadas']),
                    str(resumen['en_curso']),
                ]
                etiquetas_extra = ['REPROBADAS', 'PROMEDIO', 'CRÉDITOS APROBADOS']
                valores_extra = [
                    str(resumen['reprobadas']),
                    promedio,
                    str(resumen['creditos_aprobados']),
                ]
            resumen_tabla = Table(
                [
                    etiquetas_resumen,
                    valores_resumen,
                    etiquetas_extra,
                    valores_extra,
                ],
                colWidths=[6.8 * inch / 3] * 3,
            )
            resumen_tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e7f3f1')),
                ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#e7f3f1')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#315c59')),
                ('TEXTCOLOR', (0, 2), (-1, 2), colors.HexColor('#315c59')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), .4, colors.HexColor('#d5e0e4')),
                ('TOPPADDING', (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ]))
            story.extend([
                Spacer(1, 16),
                Paragraph(
                    'RESUMEN DE CALIFICACIONES' if tipo == 'calificaciones' else 'RESUMEN ACADÉMICO',
                    ParagraphStyle('ResumenHistorial', parent=styles['Heading3'], textColor=colors.HexColor('#00695c'), fontSize=10),
                ),
                Spacer(1, 5),
                resumen_tabla,
                Spacer(1, 16),
            ])
        if tipo == 'egreso':
            resumen = prevalidacion['resumen']
            estado_color = colors.HexColor('#176b4d') if prevalidacion['completa'] else colors.HexColor('#9a4c18')
            estado_texto = 'CUMPLE LOS REQUISITOS CONFIGURADOS' if prevalidacion['completa'] else 'PENDIENTE DE REQUISITOS'
            estado_tabla = Table(
                [[Paragraph(
                    estado_texto,
                    ParagraphStyle('EstadoEgreso', parent=styles['Heading3'], alignment=1, textColor=colors.white, fontSize=11),
                )]],
                colWidths=[6.8 * inch],
            )
            estado_tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), estado_color),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
            ]))
            requisitos = [
                ('Materias obligatorias', resumen['materias_obligatorias_aprobadas'], resumen['materias_obligatorias']),
                ('Créditos aprobados', resumen['creditos_aprobados'], resumen['creditos_requeridos']),
                ('Periodos concluidos', resumen['periodos_cursados'], resumen['periodos_requeridos']),
            ]
            requisitos_rows = [[
                Paragraph('<b>Requisito</b>', styles['BodyText']),
                Paragraph('<b>Avance</b>', styles['BodyText']),
                Paragraph('<b>Meta</b>', styles['BodyText']),
                Paragraph('<b>Estado</b>', styles['BodyText']),
            ]]
            for etiqueta, avance, meta in requisitos:
                verificado = bool(meta and avance >= meta)
                requisitos_rows.append([
                    Paragraph(escape(etiqueta), styles['BodyText']),
                    str(avance),
                    str(meta or 'Sin configurar'),
                    'Cumplido' if verificado else 'Pendiente',
                ])
            requisitos_tabla = Table(
                requisitos_rows,
                colWidths=[2.6 * inch, 1.15 * inch, 1.45 * inch, 1.6 * inch],
                repeatRows=1,
            )
            requisitos_tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e7f3f1')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#315c59')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), .4, colors.HexColor('#d5e0e4')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafb')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ]))
            story.extend([
                Spacer(1, 16),
                Paragraph(
                    'RESULTADO DE LA PREVALIDACIÓN',
                    ParagraphStyle('TituloPrevalidacion', parent=styles['Heading3'], textColor=colors.HexColor('#00695c'), fontSize=10),
                ),
                Spacer(1, 5),
                estado_tabla,
                Spacer(1, 12),
                requisitos_tabla,
                Spacer(1, 14),
                Paragraph(
                    '<b>Alcance:</b> Esta revisión es orientativa y se basa en los requisitos académicos configurados para el programa. No sustituye la validación documental ni el dictamen oficial de egreso.',
                    ParagraphStyle('NotaPrevalidacion', parent=styles['BodyText'], fontSize=8.5, leading=12, textColor=colors.HexColor('#526872')),
                ),
            ])
            if prevalidacion['motivos']:
                story.extend([
                    Spacer(1, 14),
                    Paragraph(
                        'PENDIENTES Y OBSERVACIONES',
                        ParagraphStyle('TituloPendientesEgreso', parent=styles['Heading3'], textColor=colors.HexColor('#9a4c18'), fontSize=10),
                    ),
                    Spacer(1, 4),
                ])
                story.extend(
                    Paragraph(f'• {escape(motivo)}', ParagraphStyle('MotivoEgreso', parent=styles['BodyText'], fontSize=8.5, leading=12, leftIndent=10, spaceAfter=4))
                    for motivo in prevalidacion['motivos']
                )
            if resumen['materias_pendientes']:
                materias_pendientes = Table(
                    [[
                        Paragraph('<b>Clave</b>', styles['BodyText']),
                        Paragraph('<b>Materia obligatoria pendiente</b>', styles['BodyText']),
                    ]] + [
                        [
                            celda_historial(materia['clave'], ParagraphStyle('PendienteClave', parent=styles['BodyText'], fontSize=8, wordWrap='CJK')),
                            celda_historial(materia['nombre'], ParagraphStyle('PendienteNombre', parent=styles['BodyText'], fontSize=8, wordWrap='CJK')),
                        ]
                        for materia in resumen['materias_pendientes']
                    ],
                    colWidths=[1.35 * inch, 5.45 * inch],
                    repeatRows=1,
                )
                materias_pendientes.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8eee4')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#75411f')),
                    ('GRID', (0, 0), (-1, -1), .35, colors.HexColor('#dfcbbb')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fdf9f5')]),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                story.extend([
                    Spacer(1, 10),
                    Paragraph('<b>Materias obligatorias por aprobar</b>', styles['BodyText']),
                    Spacer(1, 7),
                    materias_pendientes,
                ])
        if tipo == 'inscripcion':
            periodo_nombre = periodo_constancia.nombre if periodo_constancia else 'No disponible'
            if inscripciones_constancia:
                mensaje_inscripcion = (
                    f'Se hace constar que <b>{escape(alumno.nombre or "—")}</b> '
                    f'registra las siguientes inscripciones académicas para el periodo '
                    f'<b>{escape(periodo_nombre)}</b>.'
                )
            else:
                mensaje_inscripcion = (
                    f'No se encontraron inscripciones académicas registradas para '
                    f'<b>{escape(periodo_nombre)}</b>.'
                )
            story.extend([
                Spacer(1, 18),
                Paragraph(
                    mensaje_inscripcion,
                    ParagraphStyle('TextoInscripcion', parent=styles['BodyText'], fontSize=10, leading=16),
                ),
                Spacer(1, 15),
                Paragraph(
                    'MATERIAS INSCRITAS',
                    ParagraphStyle('TituloMateriasInscritas', parent=styles['Heading3'], textColor=colors.HexColor('#00695c'), fontSize=10),
                ),
                Spacer(1, 6),
            ])
            if inscripciones_constancia:
                total_creditos = sum(item.materia.creditos or 0 for item in inscripciones_constancia)
                resumen_inscripcion = Table(
                    [[
                        Paragraph('<b>Materias inscritas</b>', styles['BodyText']),
                        Paragraph('<b>Créditos registrados</b>', styles['BodyText']),
                    ], [str(len(inscripciones_constancia)), str(total_creditos)]],
                    colWidths=[3.4 * inch, 3.4 * inch],
                )
                resumen_inscripcion.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e7f3f1')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#315c59')),
                    ('GRID', (0, 0), (-1, -1), .4, colors.HexColor('#d5e0e4')),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ]))
                story.extend([resumen_inscripcion, Spacer(1, 14)])
            else:
                story.append(Spacer(1, 8))

        if tipo in ('historial', 'calificaciones', 'egreso', 'inscripcion'):
            story.append(Spacer(1, 18))
            if tipo in ('historial', 'calificaciones', 'inscripcion'):
                estilo_celda_historial = ParagraphStyle(
                    'CeldaInscripcion' if tipo == 'inscripcion' else ('CeldaHistorial' if tipo == 'historial' else 'CeldaCalificaciones'),
                    parent=styles['BodyText'],
                    fontSize=7.5,
                    leading=9.5,
                    wordWrap='CJK',
                )
                estilo_encabezado_historial = ParagraphStyle(
                    'EncabezadoInscripcion' if tipo == 'inscripcion' else ('EncabezadoHistorial' if tipo == 'historial' else 'EncabezadoCalificaciones'),
                    parent=estilo_celda_historial,
                    textColor=colors.white,
                    fontName='Helvetica-Bold',
                    alignment=1,
                )
                if tipo == 'inscripcion':
                    headers = ['Clave', 'Materia', 'Créditos', 'Docente', 'Horario', 'Estado']
                else:
                    headers = (
                        ['Periodo', 'Clave', 'Materia', 'Créditos', 'Calificación', 'Estado']
                        if tipo == 'historial'
                        else ['Periodo', 'Clave', 'Materia', 'Créditos', 'Calificación', 'Resultado']
                    )
                rows = [[celda_historial(header, estilo_encabezado_historial) for header in headers]]
                items_tabla = inscripciones_constancia if tipo == 'inscripcion' else historial_items
                for item in items_tabla:
                    periodo_nombre = item.periodo_inscripcion.nombre if item.periodo_inscripcion else '—'
                    calificacion = f'{item.calificacion:.2f}' if item.calificacion is not None else 'En curso'
                    if tipo == 'inscripcion':
                        rows.append([
                            celda_historial(item.materia.clave, estilo_celda_historial),
                            celda_historial(item.materia.nombre, estilo_celda_historial),
                            celda_historial(item.materia.creditos or 0, estilo_celda_historial),
                            celda_historial(item.materia.profesor or 'Por asignar', estilo_celda_historial),
                            celda_historial(item.horario or item.materia.horario or 'Por asignar', estilo_celda_historial),
                            celda_historial(item.get_estado_display(), estilo_celda_historial),
                        ])
                        continue
                    rows.append([
                        celda_historial(periodo_nombre, estilo_celda_historial),
                        celda_historial(item.materia.clave, estilo_celda_historial),
                        celda_historial(item.materia.nombre, estilo_celda_historial),
                        celda_historial(item.materia.creditos or 0, estilo_celda_historial),
                        celda_historial(calificacion, estilo_celda_historial),
                        celda_historial(
                            estado_calificacion(item) if tipo == 'calificaciones' else item.get_estado_display(),
                            estilo_celda_historial,
                        ),
                    ])
                if tipo == 'inscripcion':
                    column_widths = [.9 * inch, 1.8 * inch, .6 * inch, .85 * inch, 1.45 * inch, 1.15 * inch]
                else:
                    column_widths = [1.15 * inch, 1.1 * inch, 2 * inch, .55 * inch, .95 * inch, 1.05 * inch]
            else:
                estilo_celda_tabla = ParagraphStyle(
                    'CeldaDocumentoAcademico',
                    parent=styles['BodyText'],
                    fontSize=8,
                    leading=10,
                    wordWrap='CJK',
                )
                estilo_encabezado_tabla = ParagraphStyle(
                    'EncabezadoDocumentoAcademico',
                    parent=estilo_celda_tabla,
                    textColor=colors.white,
                    fontName='Helvetica-Bold',
                    alignment=1,
                )
                headers = ['Clave', 'Materia', 'Créditos', 'Final', 'Estado']
                rows = [[celda_historial(header, estilo_encabezado_tabla) for header in headers]]
                for item in inscripciones:
                    calificacion = f'{item.calificacion:.2f}' if item.calificacion is not None else 'Pendiente'
                    rows.append([
                        celda_historial(item.materia.clave, estilo_celda_tabla),
                        celda_historial(item.materia.nombre, estilo_celda_tabla),
                        celda_historial(item.materia.creditos or 0, estilo_celda_tabla),
                        celda_historial(calificacion, estilo_celda_tabla),
                        celda_historial(item.get_estado_display(), estilo_celda_tabla),
                    ])
                column_widths = [1.25 * inch, 2.8 * inch, .7 * inch, 1.05 * inch, 1.4 * inch]
            table = Table(rows, colWidths=column_widths, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00695c')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), .35, colors.HexColor('#b8c7d1')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f8fa')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 9),
            ]))
            story.append(table)
        if tipo == 'historial':
            story.extend([
                Spacer(1, 24),
                KeepTogether(bloque_firma_constancia(styles)),
            ])
        if tipo in ('calificaciones', 'egreso', 'inscripcion'):
            story.extend([
                Spacer(1, 24),
                KeepTogether(bloque_firma_constancia(styles)),
            ])
        construir_pdf_con_pie(doc, story)
        bio.seek(0)
        return FileResponse(bio, as_attachment=True, filename=f'{alumno.usuario}_{tipo}.pdf', content_type='application/pdf')
