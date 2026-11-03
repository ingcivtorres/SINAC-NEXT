from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Aspirante, ProyectoTesis
from .serializers import ProyectoTesisSerializer
from .views import _registrar_seguimiento
from .tesis_flujo_views import evaluar_elegibilidad_tesis, tiene_match_tesis


ESTADOS_EDITABLES_ALUMNO = {'borrador', 'observado'}
ESTADOS_PROYECTO = {estado for estado, _ in ProyectoTesis.ESTADOS}
DICTAMENES_DIRECTOR = {'observado', 'aprobado', 'rechazado'}
CAMPOS_DIRECTOR = {'estado', 'comentarios_revision', 'avance_porcentaje'}


def _rol(user):
    return str(getattr(user, 'rol', '') or '').strip().lower()


def _es_coordinacion(user):
    return bool(user.is_staff or _rol(user) in {'admin', 'administrador', 'coordinacion', 'coordinador'})


def _es_director(user):
    return _rol(user) in {'director', 'director de tesis'}


def _proyectos_visibles(user):
    if _es_coordinacion(user):
        return ProyectoTesis.objects.select_related('alumno', 'director').all()
    if _es_director(user):
        return ProyectoTesis.objects.select_related('alumno', 'director').filter(alumno__director_tesis=user)
    if _rol(user) == 'alumno':
        return ProyectoTesis.objects.select_related('alumno', 'director').filter(alumno=user)
    return ProyectoTesis.objects.none()


def _notificar_proyecto(proyecto, detalle, estado='proyecto_tesis'):
    _registrar_seguimiento(
        proyecto.alumno,
        estado,
        detalle,
        'Proyecto de tesis',
        notificar=False,
        asunto='Actualización de tu proyecto de tesis',
    )


class ProyectoTesisView(APIView):
    """Registro y revisión del proyecto de tesis con control por rol."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not (_es_coordinacion(request.user) or _es_director(request.user) or _rol(request.user) == 'alumno'):
            return Response({'detail': 'Tu rol no tiene acceso al registro de proyectos de tesis.'}, status=status.HTTP_403_FORBIDDEN)
        qs = _proyectos_visibles(request.user)
        estado = (request.query_params.get('estado') or '').strip()
        if estado:
            qs = qs.filter(estado=estado)
        search = (request.query_params.get('q') or '').strip()
        if search:
            qs = qs.filter(Q(titulo__icontains=search) | Q(alumno__nombre__icontains=search) | Q(alumno__matricula__icontains=search))
        return Response(ProyectoTesisSerializer(qs, many=True).data)

    def post(self, request):
        user = request.user
        rol = _rol(user)
        if not (_es_coordinacion(user) or _es_director(user) or rol == 'alumno'):
            return Response({'detail': 'Tu rol no puede registrar proyectos de tesis.'}, status=status.HTTP_403_FORBIDDEN)

        alumno_id = request.data.get('alumno') if (_es_coordinacion(user) or _es_director(user)) else user.id
        alumno = Aspirante.objects.filter(pk=alumno_id, rol='alumno', is_staff=False).first()
        if not alumno:
            return Response({'alumno': 'Selecciona un alumno válido.'}, status=status.HTTP_400_BAD_REQUEST)
        if rol == 'alumno':
            elegibilidad = evaluar_elegibilidad_tesis(alumno)
            if not elegibilidad['elegible']:
                return Response({'detail': 'Aún no cumples los requisitos académicos para registrar el proyecto de tesis.', 'elegibilidad': elegibilidad}, status=status.HTTP_400_BAD_REQUEST)
            if not alumno.director_tesis_id or not tiene_match_tesis(alumno):
                return Response({'detail': 'El proyecto se habilita después de que tú y tu Director confirmen el match.'}, status=status.HTTP_400_BAD_REQUEST)
        if _es_director(user) and not tiene_match_tesis(alumno):
            return Response({'detail': 'El proyecto se habilita después de que el tesista y tú confirmen el match.'}, status=status.HTTP_400_BAD_REQUEST)
        if _es_director(user) and alumno.director_tesis_id != user.id:
            return Response({'detail': 'El alumno no pertenece a tus tesistas asignados.'}, status=status.HTTP_403_FORBIDDEN)
        if ProyectoTesis.objects.filter(alumno=alumno).exclude(estado='rechazado').exists():
            return Response(
                {'detail': 'El alumno ya tiene un proyecto de tesis activo. Edita ese proyecto en lugar de registrar uno nuevo.'},
                status=status.HTTP_409_CONFLICT,
            )

        data = request.data.copy()
        data['alumno'] = alumno.id
        if rol == 'alumno':
            data['director'] = alumno.director_tesis_id or None
            data['estado'] = 'en_revision' if data.get('enviar_revision') else 'borrador'
            data.pop('avance_porcentaje', None)
        elif _es_director(user):
            data['director'] = user.id
            data['estado'] = 'en_revision'
        else:
            data['estado'] = data.get('estado') if data.get('estado') in ESTADOS_PROYECTO else 'borrador'

        serializer = ProyectoTesisSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        proyecto = serializer.save(fecha_presentacion=timezone.now() if data.get('estado') == 'en_revision' else None)
        if proyecto.estado == 'en_revision':
            _notificar_proyecto(proyecto, f'El proyecto “{proyecto.titulo}” fue enviado a revisión.')
        return Response(ProyectoTesisSerializer(proyecto).data, status=status.HTTP_201_CREATED)

    def patch(self, request, pk=None):
        if not pk:
            return Response({'detail': 'Indica el proyecto que deseas actualizar.'}, status=status.HTTP_400_BAD_REQUEST)
        proyecto = ProyectoTesis.objects.select_related('alumno', 'director').filter(pk=pk).first()
        if not proyecto:
            return Response({'detail': 'Proyecto de tesis no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        user = request.user
        rol = _rol(user)
        es_coord = _es_coordinacion(user)
        es_director_proyecto = _es_director(user) and proyecto.alumno.director_tesis_id == user.id
        es_alumno = rol == 'alumno' and proyecto.alumno_id == user.id
        if not (es_coord or es_director_proyecto or es_alumno):
            return Response({'detail': 'No tienes permisos sobre este proyecto.'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data.copy()
        requested_state = data.get('estado')
        if requested_state and requested_state not in ESTADOS_PROYECTO:
            return Response({'estado': 'Selecciona un estado válido.'}, status=status.HTTP_400_BAD_REQUEST)
        if es_alumno and (proyecto.estado not in ESTADOS_EDITABLES_ALUMNO or requested_state not in (None, 'en_revision', 'borrador', 'observado')):
            return Response({'detail': 'Solo puedes editar un borrador u observación y enviarlo a revisión.'}, status=status.HTTP_400_BAD_REQUEST)
        if es_director_proyecto and not es_coord:
            no_permitidos = set(data) - CAMPOS_DIRECTOR
            if no_permitidos:
                return Response(
                    {'detail': 'El director solo puede dictaminar, comentar y registrar el avance; el contenido del proyecto lo edita el tesista.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if requested_state == proyecto.estado:
                data.pop('estado', None)
            elif requested_state:
                if proyecto.estado != 'en_revision' or requested_state not in DICTAMENES_DIRECTOR:
                    return Response(
                        {'detail': 'Solo puedes dictaminar proyectos en revisión: aprobar, solicitar ajustes o rechazar.'},
                        status=status.HTTP_409_CONFLICT,
                    )
                if requested_state in {'observado', 'rechazado'} and not str(data.get('comentarios_revision') or '').strip():
                    return Response(
                        {'comentarios_revision': 'Explica al tesista el motivo de las observaciones o del rechazo.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        if es_alumno:
            for field in ('alumno', 'director', 'estado', 'comentarios_revision'):
                if field in data and field not in ('estado',):
                    data.pop(field, None)
            data.pop('avance_porcentaje', None)
            if request.data.get('enviar_revision'):
                data['estado'] = 'en_revision'
                data['fecha_presentacion'] = timezone.now()
            else:
                # Al editar observaciones se conserva el estado actual hasta que el alumno
                # pulse explícitamente «Enviar a revisión».
                data.pop('estado', None)

        serializer = ProyectoTesisSerializer(proyecto, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        anterior = proyecto.estado
        avance_anterior = proyecto.avance_porcentaje
        extra = {'director': user} if es_director_proyecto and not es_coord else {}
        proyecto = serializer.save(**extra)
        if proyecto.estado != anterior:
            _notificar_proyecto(proyecto, f'El proyecto “{proyecto.titulo}” cambió a estado: {proyecto.get_estado_display()}.')
        if proyecto.avance_porcentaje != avance_anterior:
            _notificar_proyecto(
                proyecto,
                f'El avance del proyecto “{proyecto.titulo}” se actualizó a {proyecto.avance_porcentaje}%.',
            )
        return Response(ProyectoTesisSerializer(proyecto).data)
