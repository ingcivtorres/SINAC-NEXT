from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Aspirante, ProyectoTesis
from .serializers import ProyectoTesisSerializer
from .views import _registrar_seguimiento
from .tesis_flujo_views import evaluar_elegibilidad_tesis


ESTADOS_EDITABLES_ALUMNO = {'borrador', 'observado'}
ESTADOS_PROYECTO = {estado for estado, _ in ProyectoTesis.ESTADOS}


def _rol(user):
    return str(getattr(user, 'rol', '') or '').strip().lower()


def _es_coordinacion(user):
    return bool(user.is_staff or _rol(user) in {'admin', 'administrador', 'coordinacion', 'coordinador'})


def _es_director(user):
    return _rol(user) in {'director', 'director de tesis'}


def _tesistas_director(user):
    nombre = (getattr(user, 'nombre', '') or '').strip()
    usuario = (getattr(user, 'usuario', '') or '').strip()
    filtro = Q(director_tesis=user) | Q(director_tesis__isnull=False, director_tesis=user)
    if nombre:
        filtro |= Q(tutor_propuesto__iexact=nombre)
    if usuario:
        filtro |= Q(tutor_propuesto__iexact=usuario)
    return Aspirante.objects.filter(filtro, is_staff=False).exclude(rol__in=('docente', 'director', 'servicios')).distinct()


def _proyectos_visibles(user):
    if _es_coordinacion(user):
        return ProyectoTesis.objects.select_related('alumno', 'director').all()
    if _es_director(user):
        tesistas = _tesistas_director(user)
        return ProyectoTesis.objects.select_related('alumno', 'director').filter(
            Q(director=user) | Q(alumno__in=tesistas)
        ).distinct()
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
            if not alumno.director_tesis_id:
                return Response({'detail': 'Coordinación Académica debe asignarte un Director de Tesis antes de registrar el proyecto.'}, status=status.HTTP_400_BAD_REQUEST)
        if _es_director(user) and alumno not in _tesistas_director(user):
            return Response({'detail': 'El alumno no pertenece a tus tesistas asignados.'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data.copy()
        data['alumno'] = alumno.id
        if rol == 'alumno':
            data['director'] = alumno.director_tesis_id or None
            data['estado'] = 'en_revision' if data.get('enviar_revision') else 'borrador'
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
        es_director_proyecto = _es_director(user) and (proyecto.director_id == user.id or proyecto.alumno in _tesistas_director(user))
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
            allowed = {'en_revision', 'observado', 'aprobado', 'rechazado'}
            if requested_state and requested_state not in allowed:
                return Response({'detail': 'El director solo puede dictaminar la revisión académica.'}, status=status.HTTP_400_BAD_REQUEST)
            data.pop('alumno', None)
            data.pop('director', None)
        if es_alumno:
            for field in ('alumno', 'director', 'estado', 'comentarios_revision'):
                if field in data and field not in ('estado',):
                    data.pop(field, None)
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
        proyecto = serializer.save()
        if proyecto.estado != anterior:
            _notificar_proyecto(proyecto, f'El proyecto “{proyecto.titulo}” cambió a estado: {proyecto.get_estado_display()}.')
        return Response(ProyectoTesisSerializer(proyecto).data)
