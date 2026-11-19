from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Aspirante, ProyectoTesis, JuradoProyecto, DefensaTesis
from .serializers import JuradoProyectoSerializer, DefensaTesisSerializer
from .views import _registrar_seguimiento


ROLES_JURADO = ('docente', 'investigador', 'director')
CAMPOS_TRAS_RESULTADO = {'acta_url', 'observaciones'}


def _rol(user):
    return str(getattr(user, 'rol', '') or '').strip().lower()


def _es_coordinacion(user):
    return bool(user.is_superuser or _rol(user) in {'admin', 'administrador', 'coordinacion', 'coordinador'})


def _es_director(user):
    return _rol(user) in {'director', 'director de tesis'}


def _es_director_del_proyecto(user, proyecto):
    return _es_director(user) and proyecto.alumno.director_tesis_id == user.id


def _puede_gestionar(user, proyecto):
    return _es_coordinacion(user) or _es_director_del_proyecto(user, proyecto)


def _puede_consultar_defensa(user, proyecto):
    return bool(
        _puede_gestionar(user, proyecto)
        or user == proyecto.alumno
        or JuradoProyecto.objects.filter(proyecto=proyecto, jurado=user).exists()
    )


def _jurados_elegibles():
    return Aspirante.objects.filter(rol__in=ROLES_JURADO, is_staff=False, is_active=True)


def _proyecto(pk):
    return ProyectoTesis.objects.filter(pk=pk).select_related('alumno', 'director').first()


def _proyecto_no_aprobado(proyecto):
    if proyecto.estado != 'aprobado':
        return Response(
            {'detail': 'El proyecto debe estar aprobado por su director antes de integrar jurado o programar la defensa.'},
            status=status.HTTP_409_CONFLICT,
        )
    return None


def _preparar_enlace_virtual(data):
    if data.get('modalidad') in {'virtual', 'hibrida'} and not data.get('enlace_virtual'):
        data['enlace_virtual'] = f'https://meet.jit.si/sinac-defensa-{uuid4().hex[:12]}'
    return data


class JuradoProyectoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk=None, jurado_id=None):
        proyecto = _proyecto(pk)
        if not proyecto:
            return Response({'detail': 'Proyecto de tesis no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if not _puede_consultar_defensa(request.user, proyecto):
            return Response({'detail': 'No tienes permisos para consultar los jurados de este proyecto.'}, status=status.HTTP_403_FORBIDDEN)

        jurados = JuradoProyecto.objects.filter(proyecto=proyecto).select_related('jurado')
        return Response(JuradoProyectoSerializer(jurados, many=True).data)

    def post(self, request, pk=None, jurado_id=None):
        proyecto = _proyecto(pk)
        if not proyecto:
            return Response({'detail': 'Proyecto de tesis no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if not _puede_gestionar(request.user, proyecto):
            return Response({'detail': 'Solo coordinación o el director de tesis del alumno pueden asignar jurados.'}, status=status.HTTP_403_FORBIDDEN)

        conflicto = _proyecto_no_aprobado(proyecto)
        if conflicto:
            return conflicto

        data = request.data.copy()
        data['proyecto'] = proyecto.pk
        jurado_id_value = data.get('jurado')
        if jurado_id_value in (None, ''):
            return Response({'jurado': 'Selecciona un jurado.'}, status=status.HTTP_400_BAD_REQUEST)

        jurado = _jurados_elegibles().filter(pk=jurado_id_value).exclude(pk=proyecto.alumno_id).first()
        if not jurado:
            return Response({'jurado': 'El jurado debe ser un docente, investigador o director activo.'}, status=status.HTTP_400_BAD_REQUEST)
        if JuradoProyecto.objects.filter(proyecto=proyecto, jurado=jurado).exists():
            return Response({'jurado': 'Esa persona ya forma parte del jurado de este proyecto.'}, status=status.HTTP_400_BAD_REQUEST)

        data['jurado'] = jurado.pk
        data['estado'] = data.get('estado', 'pendiente')
        if data.get('rol') not in {valor for valor, _ in JuradoProyecto.ROLES}:
            return Response({'rol': 'Selecciona un rol válido para el jurado.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = JuradoProyectoSerializer(data=data)
        serializer.fields['jurado'].queryset = _jurados_elegibles()
        if serializer.is_valid():
            item = serializer.save()
            return Response(JuradoProyectoSerializer(item).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk=None, jurado_id=None):
        if jurado_id is None:
            return Response({'detail': 'Debes indicar el jurado a actualizar.'}, status=status.HTTP_400_BAD_REQUEST)

        proyecto = _proyecto(pk)
        if not proyecto:
            return Response({'detail': 'Proyecto de tesis no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if not _puede_gestionar(request.user, proyecto):
            return Response({'detail': 'No tienes permisos para actualizar la asignación del jurado.'}, status=status.HTTP_403_FORBIDDEN)

        jurado_asignado = JuradoProyecto.objects.filter(pk=jurado_id, proyecto=proyecto).first()
        if not jurado_asignado:
            return Response({'detail': 'No existe ese jurado asignado al proyecto.'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data.pop('proyecto', None)
        data.pop('jurado', None)
        serializer = JuradoProyectoSerializer(jurado_asignado, data=data, partial=True)
        if serializer.is_valid():
            item = serializer.save()
            return Response(JuradoProyectoSerializer(item).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DefensaTesisView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk=None):
        proyecto = _proyecto(pk)
        if not proyecto:
            return Response({'detail': 'Proyecto de tesis no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if not _puede_consultar_defensa(request.user, proyecto):
            return Response({'detail': 'No tienes permisos para consultar la defensa.'}, status=status.HTTP_403_FORBIDDEN)

        defensa = DefensaTesis.objects.filter(proyecto=proyecto).first()
        return Response(DefensaTesisSerializer(defensa).data if defensa else {})

    def post(self, request, pk=None):
        proyecto = _proyecto(pk)
        if not proyecto:
            return Response({'detail': 'Proyecto de tesis no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if not _puede_gestionar(request.user, proyecto):
            return Response({'detail': 'Solo coordinación o el director de tesis del alumno pueden programar la defensa.'}, status=status.HTTP_403_FORBIDDEN)

        conflicto = _proyecto_no_aprobado(proyecto)
        if conflicto:
            return conflicto

        if DefensaTesis.objects.filter(proyecto=proyecto).exists():
            return Response({'detail': 'Ya existe una defensa programada para este proyecto.'}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data.copy()
        data['proyecto'] = proyecto.pk
        data['estado'] = 'programada'
        data.pop('calificacion_final', None)
        _preparar_enlace_virtual(data)
        serializer = DefensaTesisSerializer(data=data)
        if serializer.is_valid():
            item = serializer.save()
            return Response(DefensaTesisSerializer(item).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk=None):
        proyecto = _proyecto(pk)
        if not proyecto:
            return Response({'detail': 'Proyecto de tesis no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if not _puede_gestionar(request.user, proyecto):
            return Response({'detail': 'No tienes permisos para actualizar la defensa.'}, status=status.HTTP_403_FORBIDDEN)

        defensa = DefensaTesis.objects.filter(proyecto=proyecto).first()
        if not defensa:
            return Response({'detail': 'No existe una defensa registrada para este proyecto.'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data.pop('proyecto', None)
        if defensa.calificacion_final is not None and set(data) - CAMPOS_TRAS_RESULTADO:
            return Response(
                {'detail': 'La defensa ya tiene resultado registrado; solo puedes actualizar el acta y las observaciones.'},
                status=status.HTTP_409_CONFLICT,
            )
        registra_resultado = data.get('calificacion_final') not in (None, '')
        if registra_resultado:
            try:
                nota = Decimal(str(data['calificacion_final']))
            except (InvalidOperation, ValueError):
                return Response({'calificacion_final': 'La calificación debe ser un número entre 0 y 10.'}, status=status.HTTP_400_BAD_REQUEST)
            if nota < 0 or nota > 10:
                return Response({'calificacion_final': 'La calificación debe estar entre 0 y 10.'}, status=status.HTTP_400_BAD_REQUEST)
            if defensa.estado == 'cancelada' or not defensa.fecha or defensa.fecha > timezone.now():
                return Response(
                    {'detail': 'Solo puedes registrar el resultado de una defensa vigente cuya fecha ya pasó.'},
                    status=status.HTTP_409_CONFLICT,
                )
            data['estado'] = 'realizada'
        else:
            data.pop('calificacion_final', None)
        _preparar_enlace_virtual(data)
        serializer = DefensaTesisSerializer(defensa, data=data, partial=True)
        if serializer.is_valid():
            item = serializer.save()
            if registra_resultado:
                dictamen = 'aprobatoria' if item.calificacion_final >= 7 else 'no aprobatoria'
                _registrar_seguimiento(
                    proyecto.alumno, 'defensa_resultado',
                    f'Se registró el resultado de tu defensa: {item.calificacion_final} ({dictamen}).',
                    'Jurado de tesis', notificar=False,
                )
            return Response(DefensaTesisSerializer(item).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JuradosDisponiblesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not (_es_coordinacion(request.user) or _es_director(request.user)):
            return Response({'detail': 'No tienes permisos para consultar docentes disponibles.'}, status=status.HTTP_403_FORBIDDEN)
        candidatos = _jurados_elegibles().order_by('nombre')
        return Response([
            {'id': persona.pk, 'nombre': persona.nombre, 'correo': persona.correo, 'usuario': persona.usuario, 'rol': persona.rol}
            for persona in candidatos
        ])
