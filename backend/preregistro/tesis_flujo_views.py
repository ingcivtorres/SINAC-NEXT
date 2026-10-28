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
    rol = _rol(user)
    if rol in {'servicios', 'servicios_escolares', 'servicios escolares'}:
        return False
    return bool(user.is_staff or rol in {'admin', 'administrador', 'coordinacion', 'coordinador'})


def tiene_match_tesis(alumno):
    match_aprobado = SolicitudDireccionTesis.objects.filter(
        alumno=alumno, estado='aprobada', director_asignado_id=alumno.director_tesis_id,
    ).exists()
    return match_aprobado or (
        alumno.director_tesis_id
        and not SolicitudDireccionTesis.objects.filter(alumno=alumno).exists()
    )


def _puede_gestionar_planes(user):
    rol = _rol(user)
    return rol in {
        'admin', 'administrador', 'servicios', 'servicios_escolares', 'servicios escolares',
    }


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
        'alumno_acepto_director': solicitud.alumno_acepto_director,
        'director_acepto': solicitud.director_acepto,
        'linea_investigacion': solicitud.linea_investigacion,
        'justificacion': solicitud.justificacion,
        'estado': solicitud.estado,
        'estado_label': solicitud.get_estado_display(),
        'observaciones': solicitud.observaciones,
        'created_at': solicitud.created_at,
        'updated_at': solicitud.updated_at,
    }


def evaluar_elegibilidad_tesis(alumno):
    """Determina el inicio del segundo año según la periodicidad del programa."""
    configuracion = ConfiguracionPrograma.objects.filter(programa__iexact=alumno.programa, activo=True).first()
    if not configuracion:
        return {'elegible': False, 'motivos': ['Coordinación Académica aún no configuró el plan de estudios de tu programa.'], 'configuracion': None}

    plan = list(configuracion.materias_plan.select_related('materia').all())
    if not plan:
        return {'elegible': False, 'motivos': ['El plan de estudios aún no contiene materias configuradas.'], 'configuracion': _configuracion_data(configuracion)}

    periodos_por_anio = 3 if configuracion.periodicidad == 'cuatrimestral' else 2
    periodo_inicio_tesis = periodos_por_anio + 1
    periodo_actual = alumno.numero_periodo_actual
    etapa = (
        'formacion'
        if not periodo_actual or periodo_actual < periodo_inicio_tesis - 1
        else 'por_iniciar'
        if periodo_actual == periodo_inicio_tesis - 1
        else 'iniciada'
    )
    motivos = []
    if not configuracion.periodos_requeridos:
        motivos.append('Coordinación Académica debe configurar la duración del plan de estudios.')
    if not periodo_actual:
        motivos.append('Coordinación Académica debe asignarte el periodo académico actual.')
    elif periodo_actual < periodo_inicio_tesis:
        motivos.append(
            f'El proyecto de tesis inicia en el segundo año, a partir del periodo {periodo_inicio_tesis}. '
            f'Tu periodo actual es el {periodo_actual}.'
        )
    return {
        'elegible': not motivos,
        'motivos': motivos,
        'configuracion': _configuracion_data(configuracion),
        'resumen': {
            'periodo_actual': periodo_actual,
            'periodo_inicio_tesis': periodo_inicio_tesis,
            'periodos_por_anio': periodos_por_anio,
            'periodos_requeridos': configuracion.periodos_requeridos,
            'etapa': etapa,
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
        if _puede_gestionar_planes(request.user) and _rol(request.user) in {'servicios', 'servicios_escolares', 'servicios escolares'}:
            configuraciones = ConfiguracionPrograma.objects.prefetch_related('materias_plan__materia').all()
            return Response({
                'configuraciones': [_configuracion_data(item) for item in configuraciones],
                'materias': [{'id': item.id, 'clave': item.clave, 'nombre': item.nombre, 'creditos': item.creditos} for item in Materia.objects.order_by('clave')],
            })
        if not _es_coordinacion(request.user):
            return Response({'detail': 'Solo el alumno o Coordinación Académica pueden consultar este flujo.'}, status=status.HTTP_403_FORBIDDEN)
        solicitudes = SolicitudDireccionTesis.objects.select_related('alumno', 'director_sugerido', 'director_asignado').all()
        directores = Aspirante.objects.filter(rol__in=['director', 'director de tesis'], is_active=True).order_by('nombre')
        resultado = {
            'solicitudes': [_solicitud_data(item) for item in solicitudes],
            'directores': [{'id': item.id, 'nombre': item.nombre, 'departamento': item.departamento, 'programa': item.programa} for item in directores],
        }
        if _puede_gestionar_planes(request.user):
            configuraciones = ConfiguracionPrograma.objects.prefetch_related('materias_plan__materia').all()
            resultado.update({
                'configuraciones': [_configuracion_data(item) for item in configuraciones],
                'materias': [{'id': item.id, 'clave': item.clave, 'nombre': item.nombre, 'creditos': item.creditos} for item in Materia.objects.order_by('clave')],
            })
        return Response(resultado)

    def post(self, request):
        if _rol(request.user) == 'alumno':
            elegibilidad = evaluar_elegibilidad_tesis(request.user)
            if not elegibilidad['elegible']:
                return Response({'detail': 'Aún no cumples los requisitos para iniciar tesis.', 'elegibilidad': elegibilidad}, status=status.HTTP_400_BAD_REQUEST)
            if SolicitudDireccionTesis.objects.filter(
                alumno=request.user,
                estado__in={'pendiente', 'pendiente_director', 'pendiente_alumno', 'aprobada'},
            ).exists():
                return Response({'detail': 'Ya tienes una solicitud de dirección de tesis pendiente.'}, status=status.HTTP_400_BAD_REQUEST)
            director_id = request.data.get('director_sugerido')
            director = Aspirante.objects.filter(pk=director_id, rol__in=['director', 'director de tesis'], is_active=True).first() if director_id else None
            if director_id and not director:
                return Response({'director_sugerido': 'Selecciona un Director de Tesis activo.'}, status=status.HTTP_400_BAD_REQUEST)
            solicitud = SolicitudDireccionTesis.objects.create(
                alumno=request.user,
                director_sugerido=director,
                director_asignado=director,
                alumno_acepto_director=bool(director),
                estado='pendiente_director' if director else 'pendiente',
                linea_investigacion=str(request.data.get('linea_investigacion') or '')[:180],
                justificacion=str(request.data.get('justificacion') or ''),
            )
            if director:
                _registrar_seguimiento(
                    director, 'match_tesis_pendiente',
                    f'{request.user.nombre} propone un proyecto de tesis para tu revisión.',
                    'Tesista', notificar=False,
                )
                detalle_solicitud = f'Tu propuesta fue enviada a {director.nombre} para confirmar el match.'
            else:
                detalle_solicitud = 'Tu solicitud de asignación de Director de Tesis fue enviada a Coordinación Académica.'
            _registrar_seguimiento(request.user, 'solicitud_direccion_tesis', detalle_solicitud, 'Tesis', notificar=False)
            return Response(_solicitud_data(solicitud), status=status.HTTP_201_CREATED)
        if not _puede_gestionar_planes(request.user):
            return Response({'detail': 'Solo Servicios Escolares puede configurar planes de estudio.'}, status=status.HTTP_403_FORBIDDEN)
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
        rol = _rol(request.user)
        es_director = rol in {'director', 'director de tesis'}
        es_alumno = rol == 'alumno'
        if not (_es_coordinacion(request.user) or es_director or es_alumno):
            return Response({'detail': 'No tienes permiso para actualizar esta solicitud.'}, status=status.HTTP_403_FORBIDDEN)
        solicitud = SolicitudDireccionTesis.objects.select_related('alumno').filter(pk=pk).first()
        if not solicitud:
            return Response({'detail': 'Solicitud no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        estado = request.data.get('estado')
        if estado not in {'aprobada', 'rechazada', 'cancelada'}:
            return Response({'detail': 'Selecciona un dictamen válido.'}, status=status.HTTP_400_BAD_REQUEST)
        director = None
        if estado == 'aprobada' and not (es_director or es_alumno):
            director = Aspirante.objects.filter(pk=request.data.get('director_asignado'), rol__in=['director', 'director de tesis'], is_active=True).first()
            if not director:
                return Response({'detail': 'Selecciona un Director de Tesis activo.'}, status=status.HTTP_400_BAD_REQUEST)
        if es_director:
            if solicitud.director_asignado_id != request.user.id:
                return Response({'detail': 'Esta solicitud no está asignada a tu panel.'}, status=status.HTTP_403_FORBIDDEN)
            if solicitud.estado != 'pendiente_director' or estado not in {'aprobada', 'rechazada'}:
                return Response({'detail': 'La solicitud no está pendiente de tu respuesta.'}, status=status.HTTP_409_CONFLICT)
            solicitud.director_acepto = estado == 'aprobada'
            solicitud.observaciones = str(request.data.get('observaciones') or '')
            solicitud.estado = 'aprobada' if solicitud.alumno_acepto_director and solicitud.director_acepto else 'pendiente_alumno' if solicitud.director_acepto else 'rechazada'
            solicitud.revisado_por = request.user
            solicitud.save(update_fields=['director_acepto', 'observaciones', 'estado', 'revisado_por', 'updated_at'])
            if solicitud.estado == 'aprobada':
                solicitud.alumno.director_tesis = request.user
                solicitud.alumno.save(update_fields=['director_tesis', 'updated_at'])
                _registrar_seguimiento(
                    solicitud.alumno, 'match_tesis', f'{request.user.nombre} aceptó acompañarte en tu proyecto de tesis.',
                    'Director de Tesis', notificar=False,
                )
            else:
                _registrar_seguimiento(
                    solicitud.alumno, 'match_tesis', f'{request.user.nombre} respondió a tu propuesta de dirección de tesis.',
                    'Director de Tesis', notificar=False,
                )
            return Response(_solicitud_data(solicitud))

        if es_alumno:
            if solicitud.alumno_id != request.user.id or solicitud.estado != 'pendiente_alumno':
                return Response({'detail': 'No tienes una confirmación de dirección pendiente.'}, status=status.HTTP_409_CONFLICT)
            if estado not in {'aprobada', 'rechazada'}:
                return Response({'detail': 'Confirma o rechaza al director propuesto.'}, status=status.HTTP_400_BAD_REQUEST)
            solicitud.alumno_acepto_director = estado == 'aprobada'
            solicitud.estado = 'aprobada' if solicitud.alumno_acepto_director and solicitud.director_acepto else 'cancelada'
            solicitud.save(update_fields=['alumno_acepto_director', 'estado', 'updated_at'])
            if solicitud.estado == 'aprobada':
                solicitud.alumno.director_tesis = solicitud.director_asignado
                solicitud.alumno.save(update_fields=['director_tesis', 'updated_at'])
                _registrar_seguimiento(
                    solicitud.director_asignado, 'match_tesis',
                    f'{solicitud.alumno.nombre} confirmó el match para dirigir su proyecto de tesis.',
                    'Tesista', notificar=False,
                )
            _registrar_seguimiento(
                solicitud.alumno, 'match_tesis',
                'El match de dirección quedó confirmado.' if solicitud.estado == 'aprobada' else 'Rechazaste la propuesta de dirección.',
                'Tesis', notificar=False,
            )
            return Response(_solicitud_data(solicitud))

        if not _es_coordinacion(request.user):
            return Response({'detail': 'No tienes permiso para actualizar esta solicitud.'}, status=status.HTTP_403_FORBIDDEN)
        if estado == 'aprobada':
            solicitud.director_asignado = director
            solicitud.alumno_acepto_director = director.id == solicitud.director_sugerido_id
            solicitud.director_acepto = False
            solicitud.estado = 'pendiente_director'
            solicitud.revisado_por = request.user
            solicitud.observaciones = str(request.data.get('observaciones') or '')
            solicitud.save(update_fields=[
                'director_asignado', 'alumno_acepto_director', 'director_acepto', 'estado',
                'revisado_por', 'observaciones', 'updated_at',
            ])
            if solicitud.alumno.director_tesis_id != director.id:
                solicitud.alumno.director_tesis = None
                solicitud.alumno.save(update_fields=['director_tesis', 'updated_at'])
            _registrar_seguimiento(
                director, 'match_tesis_pendiente',
                f'{solicitud.alumno.nombre} propone un proyecto de tesis para tu revisión.',
                'Coordinación Académica', notificar=False,
            )
            _registrar_seguimiento(
                solicitud.alumno, 'match_tesis_pendiente',
                f'Coordinación propuso a {director.nombre}. El seguimiento iniciará cuando ambos confirmen.',
                'Coordinación Académica', notificar=False,
            )
        else:
            if solicitud.director_asignado_id and solicitud.alumno.director_tesis_id == solicitud.director_asignado_id:
                solicitud.alumno.director_tesis = None
                solicitud.alumno.save(update_fields=['director_tesis', 'updated_at'])
            solicitud.estado = estado
            solicitud.director_asignado = None
            solicitud.alumno_acepto_director = False
            solicitud.director_acepto = False
            solicitud.observaciones = str(request.data.get('observaciones') or '')
            solicitud.revisado_por = request.user
            solicitud.save(update_fields=[
                'estado', 'director_asignado', 'alumno_acepto_director', 'director_acepto',
                'observaciones', 'revisado_por', 'updated_at',
            ])
            _registrar_seguimiento(
                solicitud.alumno, 'direccion_tesis',
                f'Coordinación Académica actualizó tu solicitud de dirección de tesis a: {solicitud.get_estado_display()}.',
                'Coordinación Académica', notificar=False,
            )
        return Response(_solicitud_data(solicitud))
