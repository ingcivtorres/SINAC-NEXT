from collections import Counter

from django.db import transaction
from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Aspirante, ConfiguracionPrograma, Inscripcion, Materia, PlanEstudioMateria, SolicitudDireccionTesis
from .views import _registrar_seguimiento


def _rol(user):
    return str(getattr(user, 'rol', '') or '').strip().lower()


def _es_coordinacion(user):
    return bool(user.is_staff or _rol(user) in {'admin', 'administrador', 'coordinacion', 'coordinador'})


def _configuracion_data(configuracion):
    return {
        'id': configuracion.id,
        'programa': configuracion.programa,
        'grado': configuracion.grado,
        'grado_label': configuracion.get_grado_display(),
        'periodicidad': configuracion.periodicidad,
        'periodicidad_label': configuracion.get_periodicidad_display(),
        'duracion_anios': configuracion.duracion_anios,
        'periodos_requeridos': configuracion.periodos_requeridos,
        'creditos_requeridos': configuracion.creditos_requeridos,
        'activo': configuracion.activo,
        'materias_plan': [{
            'id': item.id,
            'materia': item.materia_id,
            'clave': item.materia.clave,
            'nombre': item.materia.nombre,
            'creditos': item.materia.creditos,
            'periodo_sugerido': item.periodo_sugerido,
            'obligatoria': item.obligatoria,
        } for item in configuracion.materias_plan.select_related('materia').all()],
    }


def _solicitud_data(solicitud):
    return {
        'id': solicitud.id,
        'alumno': {'id': solicitud.alumno_id, 'nombre': solicitud.alumno.nombre, 'matricula': solicitud.alumno.matricula, 'programa': solicitud.alumno.programa},
        'director_sugerido': {'id': solicitud.director_sugerido_id, 'nombre': solicitud.director_sugerido.nombre} if solicitud.director_sugerido else None,
        'director_asignado': {'id': solicitud.director_asignado_id, 'nombre': solicitud.director_asignado.nombre} if solicitud.director_asignado else None,
        'linea_investigacion': solicitud.linea_investigacion,
        'justificacion': solicitud.justificacion,
        'estado': solicitud.estado,
        'estado_label': solicitud.get_estado_display(),
        'observaciones': solicitud.observaciones,
        'created_at': solicitud.created_at,
        'updated_at': solicitud.updated_at,
    }


def evaluar_elegibilidad_tesis(alumno):
    """Calcula requisitos sin usar una fecha fija: sirve tanto semestres como cuatrimestres."""
    configuracion = ConfiguracionPrograma.objects.filter(programa__iexact=alumno.programa, activo=True).first()
    if not configuracion:
        return {'elegible': False, 'motivos': ['Coordinación Académica aún no configuró el plan de estudios de tu programa.'], 'configuracion': None}

    plan = list(configuracion.materias_plan.select_related('materia').all())
    if not plan:
        return {'elegible': False, 'motivos': ['El plan de estudios aún no contiene materias configuradas.'], 'configuracion': _configuracion_data(configuracion)}

    inscripciones = list(Inscripcion.objects.filter(aspirante=alumno).select_related('materia', 'periodo_inscripcion'))
    aprobadas = {item.materia_id for item in inscripciones if item.calificacion is not None and item.calificacion >= 7}
    finalizadas = [item for item in inscripciones if item.calificacion is not None]
    obligatorias = [item for item in plan if item.obligatoria]
    if not obligatorias:
        return {
            'elegible': False,
            'motivos': ['Coordinación Académica debe configurar al menos una materia obligatoria en el plan.'],
            'configuracion': _configuracion_data(configuracion),
        }
    materias_por_periodo = Counter(item.periodo_sugerido for item in plan)
    periodos_incompletos = [
        periodo for periodo in range(1, configuracion.periodos_requeridos + 1)
        if materias_por_periodo[periodo] < 4
    ]
    pendientes = [item for item in obligatorias if item.materia_id not in aprobadas]
    creditos_aprobados = sum(item.materia.creditos for item in inscripciones if item.materia_id in aprobadas)
    periodos_cursados = len({item.periodo_inscripcion_id for item in finalizadas if item.periodo_inscripcion_id})
    motivos = []
    if configuracion.creditos_requeridos <= 0:
        motivos.append('Coordinación Académica debe configurar un mínimo de créditos para el programa.')
    if configuracion.periodos_requeridos <= 0:
        motivos.append('Coordinación Académica debe configurar el mínimo de periodos académicos.')
    if periodos_incompletos:
        motivos.append('El plan debe ofrecer al menos 4 materias en cada periodo requerido; faltan periodos por configurar.')
    if pendientes:
        motivos.append(f'Faltan {len(pendientes)} materia(s) obligatoria(s) por aprobar.')
    if configuracion.creditos_requeridos and creditos_aprobados < configuracion.creditos_requeridos:
        motivos.append(f'Faltan {configuracion.creditos_requeridos - creditos_aprobados} crédito(s) para completar el programa.')
    if periodos_cursados < configuracion.periodos_requeridos:
        motivos.append(f'Faltan {configuracion.periodos_requeridos - periodos_cursados} periodo(s) concluido(s) de los {configuracion.periodos_requeridos} requeridos.')
    return {
        'elegible': not motivos,
        'motivos': motivos,
        'configuracion': _configuracion_data(configuracion),
        'resumen': {
            'materias_obligatorias': len(obligatorias),
            'materias_obligatorias_aprobadas': len(obligatorias) - len(pendientes),
            'materias_pendientes': [{'clave': item.materia.clave, 'nombre': item.materia.nombre} for item in pendientes],
            'creditos_aprobados': creditos_aprobados,
            'creditos_requeridos': configuracion.creditos_requeridos,
            'periodos_cursados': periodos_cursados,
            'periodos_requeridos': configuracion.periodos_requeridos,
        },
    }


class FlujoTesisView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if _rol(request.user) == 'alumno':
            solicitud = SolicitudDireccionTesis.objects.filter(alumno=request.user).select_related('alumno', 'director_sugerido', 'director_asignado').first()
            directores = Aspirante.objects.filter(rol__in=['director', 'director de tesis'], is_active=True).order_by('nombre')
            return Response({
                'elegibilidad': evaluar_elegibilidad_tesis(request.user),
                'solicitud': _solicitud_data(solicitud) if solicitud else None,
                'directores': [{'id': item.id, 'nombre': item.nombre, 'departamento': item.departamento, 'programa': item.programa} for item in directores],
            })
        if not _es_coordinacion(request.user):
            return Response({'detail': 'Solo el alumno o Coordinación Académica pueden consultar este flujo.'}, status=status.HTTP_403_FORBIDDEN)
        solicitudes = SolicitudDireccionTesis.objects.select_related('alumno', 'director_sugerido', 'director_asignado').all()
        configuraciones = ConfiguracionPrograma.objects.prefetch_related('materias_plan__materia').all()
        directores = Aspirante.objects.filter(rol__in=['director', 'director de tesis'], is_active=True).order_by('nombre')
        return Response({
            'solicitudes': [_solicitud_data(item) for item in solicitudes],
            'configuraciones': [_configuracion_data(item) for item in configuraciones],
            'directores': [{'id': item.id, 'nombre': item.nombre, 'departamento': item.departamento, 'programa': item.programa} for item in directores],
            'materias': [{'id': item.id, 'clave': item.clave, 'nombre': item.nombre, 'creditos': item.creditos} for item in Materia.objects.order_by('clave')],
        })

    def post(self, request):
        if _rol(request.user) == 'alumno':
            elegibilidad = evaluar_elegibilidad_tesis(request.user)
            if not elegibilidad['elegible']:
                return Response({'detail': 'Aún no cumples los requisitos para iniciar tesis.', 'elegibilidad': elegibilidad}, status=status.HTTP_400_BAD_REQUEST)
            if SolicitudDireccionTesis.objects.filter(alumno=request.user, estado='pendiente').exists():
                return Response({'detail': 'Ya tienes una solicitud de dirección de tesis pendiente.'}, status=status.HTTP_400_BAD_REQUEST)
            director_id = request.data.get('director_sugerido')
            director = Aspirante.objects.filter(pk=director_id, rol__in=['director', 'director de tesis'], is_active=True).first() if director_id else None
            if director_id and not director:
                return Response({'director_sugerido': 'Selecciona un Director de Tesis activo.'}, status=status.HTTP_400_BAD_REQUEST)
            solicitud = SolicitudDireccionTesis.objects.create(alumno=request.user, director_sugerido=director, linea_investigacion=str(request.data.get('linea_investigacion') or '')[:180], justificacion=str(request.data.get('justificacion') or ''))
            _registrar_seguimiento(request.user, 'solicitud_direccion_tesis', 'Tu solicitud de asignación de Director de Tesis fue enviada a Coordinación Académica.', 'Tesis', notificar=False)
            return Response(_solicitud_data(solicitud), status=status.HTTP_201_CREATED)
        if not _es_coordinacion(request.user):
            return Response({'detail': 'No tienes permisos para configurar planes de estudio.'}, status=status.HTTP_403_FORBIDDEN)
        programa = str(request.data.get('programa') or '').strip()
        grado = request.data.get('grado')
        if not programa or grado not in {'maestria', 'doctorado'}:
            return Response({'detail': 'Indica el programa y el grado académico.'}, status=status.HTTP_400_BAD_REQUEST)
        configuracion_id = request.data.get('id')
        configuracion_existente = None
        if configuracion_id:
            configuracion_existente = ConfiguracionPrograma.objects.filter(pk=configuracion_id).first()
            if not configuracion_existente:
                return Response({'detail': 'No se encontró el plan de estudios.'}, status=status.HTTP_404_NOT_FOUND)
        programa_duplicado = ConfiguracionPrograma.objects.filter(programa__iexact=programa)
        if configuracion_existente:
            programa_duplicado = programa_duplicado.exclude(pk=configuracion_existente.pk)
        if programa_duplicado.exists():
            return Response({'detail': 'Ya existe un plan configurado para ese programa.'}, status=status.HTTP_409_CONFLICT)
        periodicidad = request.data.get('periodicidad', 'semestral')
        if periodicidad not in {'semestral', 'cuatrimestral'}:
            return Response({'detail': 'La periodicidad debe ser semestral o cuatrimestral.'}, status=status.HTTP_400_BAD_REQUEST)
        periodos = request.data.get('periodos_requeridos') or ((4 if grado == 'maestria' else 8) if periodicidad == 'semestral' else (6 if grado == 'maestria' else 12))
        try:
            periodos = int(periodos)
            creditos = int(request.data.get('creditos_requeridos') or 0)
            if periodos < 1 or creditos < 0:
                raise ValueError
            if 'materias_plan' in request.data:
                if not isinstance(request.data['materias_plan'], list):
                    raise ValueError
                materias_por_periodo = Counter()
                for item in request.data['materias_plan']:
                    numero_periodo = int(item.get('periodo_sugerido') or 1)
                    if not 1 <= numero_periodo <= periodos:
                        raise ValueError
                    materias_por_periodo[numero_periodo] += 1
                materias_ids = [int(item['materia']) for item in request.data['materias_plan']]
                if len(set(materias_ids)) != len(materias_ids):
                    return Response({'detail': 'No repitas materias dentro del plan de estudios.'}, status=status.HTTP_400_BAD_REQUEST)
                faltan_materias = [numero for numero in range(1, periodos + 1) if materias_por_periodo[numero] < 4]
                if faltan_materias:
                    return Response({'detail': 'El plan debe incluir al menos 4 materias por cada semestre o cuatrimestre requerido.'}, status=status.HTTP_400_BAD_REQUEST)
            with transaction.atomic():
                activo_raw = request.data.get('activo', configuracion_existente.activo if configuracion_existente else True)
                activo = activo_raw if isinstance(activo_raw, bool) else str(activo_raw).strip().lower() not in {'false', '0', 'no', 'inactivo'}
                if configuracion_existente:
                    configuracion = configuracion_existente
                    configuracion.programa = programa
                    configuracion.grado = grado
                    configuracion.periodicidad = periodicidad
                    configuracion.periodos_requeridos = periodos
                    configuracion.creditos_requeridos = creditos
                    configuracion.activo = activo
                    configuracion.save()
                else:
                    configuracion, _ = ConfiguracionPrograma.objects.update_or_create(programa=programa, defaults={'grado': grado, 'periodicidad': periodicidad, 'periodos_requeridos': periodos, 'creditos_requeridos': creditos, 'activo': activo})
                if 'materias_plan' in request.data:
                    configuracion.materias_plan.all().delete()
                    for item in request.data['materias_plan']:
                        materia = Materia.objects.get(pk=item['materia'])
                        PlanEstudioMateria.objects.create(configuracion=configuracion, materia=materia, periodo_sugerido=max(1, int(item.get('periodo_sugerido') or 1)), obligatoria=bool(item.get('obligatoria', True)))
        except (Materia.DoesNotExist, TypeError, ValueError, KeyError):
            return Response({'detail': 'La configuración del plan contiene una materia o periodo no válido.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_configuracion_data(configuracion), status=status.HTTP_201_CREATED)


class SolicitudDireccionTesisDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        if not _es_coordinacion(request.user):
            return Response({'detail': 'Solo Coordinación Académica puede asignar un Director de Tesis.'}, status=status.HTTP_403_FORBIDDEN)
        solicitud = SolicitudDireccionTesis.objects.select_related('alumno').filter(pk=pk).first()
        if not solicitud:
            return Response({'detail': 'Solicitud no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        estado = request.data.get('estado')
        if estado not in {'aprobada', 'rechazada', 'cancelada'}:
            return Response({'detail': 'Selecciona un dictamen válido.'}, status=status.HTTP_400_BAD_REQUEST)
        director = None
        if estado == 'aprobada':
            director = Aspirante.objects.filter(pk=request.data.get('director_asignado'), rol__in=['director', 'director de tesis'], is_active=True).first()
            if not director:
                return Response({'detail': 'Selecciona un Director de Tesis activo.'}, status=status.HTTP_400_BAD_REQUEST)
        solicitud.estado = estado
        solicitud.director_asignado = director
        solicitud.observaciones = str(request.data.get('observaciones') or '')
        solicitud.revisado_por = request.user
        solicitud.save()
        if director:
            solicitud.alumno.director_tesis = director
            solicitud.alumno.save(update_fields=['director_tesis', 'updated_at'])
            detalle = f'Coordinación Académica asignó a {director.nombre} como tu Director de Tesis.'
            _registrar_seguimiento(director, 'tesista_asignado', f'Se te asignó como Director de Tesis de {solicitud.alumno.nombre}.', 'Coordinación Académica', notificar=False)
        else:
            detalle = f'Coordinación Académica actualizó tu solicitud de dirección de tesis a: {solicitud.get_estado_display()}.'
        _registrar_seguimiento(solicitud.alumno, 'direccion_tesis', detalle, 'Coordinación Académica', notificar=False)
        return Response(_solicitud_data(solicitud))
