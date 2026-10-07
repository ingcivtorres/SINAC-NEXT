from uuid import uuid4

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Aspirante, ProyectoTesis, JuradoProyecto, DefensaTesis
from .serializers import JuradoProyectoSerializer, DefensaTesisSerializer


def _rol(user):
    return str(getattr(user, 'rol', '') or '').strip().lower()


def _es_coordinacion(user):
    return bool(user.is_staff or _rol(user) in {'admin', 'administrador', 'coordinacion', 'coordinador'})


def _es_director(user):
    return _rol(user) in {'director', 'director de tesis'}


def _puede_consultar_defensa(user, proyecto):
    return bool(
        _es_coordinacion(user)
        or _es_director(user)
        or user == proyecto.alumno
        or JuradoProyecto.objects.filter(proyecto=proyecto, jurado=user).exists()
    )


def _preparar_enlace_virtual(data):
    if data.get('modalidad') in {'virtual', 'hibrida'} and not data.get('enlace_virtual'):
        data['enlace_virtual'] = f'https://meet.jit.si/sinac-defensa-{uuid4().hex[:12]}'
    return data


class JuradoProyectoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk=None, jurado_id=None):
        proyecto = ProyectoTesis.objects.filter(pk=pk).select_related('alumno', 'director').first()
        if not proyecto:
            return Response({'detail': 'Proyecto de tesis no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if not _puede_consultar_defensa(request.user, proyecto):
            return Response({'detail': 'No tienes permisos para consultar los jurados de este proyecto.'}, status=status.HTTP_403_FORBIDDEN)

        jurados = JuradoProyecto.objects.filter(proyecto=proyecto).select_related('jurado')
        return Response(JuradoProyectoSerializer(jurados, many=True).data)

    def post(self, request, pk=None, jurado_id=None):
        proyecto = ProyectoTesis.objects.filter(pk=pk).select_related('alumno', 'director').first()
        if not proyecto:
            return Response({'detail': 'Proyecto de tesis no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if not (_es_coordinacion(request.user) or _es_director(request.user)):
            return Response({'detail': 'Solo coordinación o el director pueden asignar jurados.'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data.copy()
        data['proyecto'] = proyecto.pk
        jurado_id_value = data.get('jurado')
        if jurado_id_value is None:
            return Response({'jurado': 'Selecciona un jurado.'}, status=status.HTTP_400_BAD_REQUEST)

        jurado = Aspirante.objects.filter(pk=jurado_id_value, rol='docente', is_staff=False).first()
        if not jurado:
            return Response({'jurado': 'El jurado debe ser un docente activo.'}, status=status.HTTP_400_BAD_REQUEST)

        data['jurado'] = jurado.pk
        data['estado'] = data.get('estado', 'pendiente')
        if data.get('rol') not in {valor for valor, _ in JuradoProyecto.ROLES}:
            return Response({'rol': 'Selecciona un rol válido para el jurado.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = JuradoProyectoSerializer(data=data)
        if serializer.is_valid():
            item = serializer.save()
            return Response(JuradoProyectoSerializer(item).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk=None, jurado_id=None):
        if jurado_id is None:
            return Response({'detail': 'Debes indicar el jurado a actualizar.'}, status=status.HTTP_400_BAD_REQUEST)

        proyecto = ProyectoTesis.objects.filter(pk=pk).select_related('alumno', 'director').first()
        if not proyecto:
            return Response({'detail': 'Proyecto de tesis no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if not (_es_coordinacion(request.user) or _es_director(request.user)):
            return Response({'detail': 'No tienes permisos para actualizar la asignación del jurado.'}, status=status.HTTP_403_FORBIDDEN)

        jurado_asignado = JuradoProyecto.objects.filter(pk=jurado_id, proyecto=proyecto).first()
        if not jurado_asignado:
            return Response({'detail': 'No existe ese jurado asignado al proyecto.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = JuradoProyectoSerializer(jurado_asignado, data=request.data, partial=True)
        if serializer.is_valid():
            item = serializer.save()
            return Response(JuradoProyectoSerializer(item).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DefensaTesisView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk=None):
        proyecto = ProyectoTesis.objects.filter(pk=pk).select_related('alumno', 'director').first()
        if not proyecto:
            return Response({'detail': 'Proyecto de tesis no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if not _puede_consultar_defensa(request.user, proyecto):
            return Response({'detail': 'No tienes permisos para consultar la defensa.'}, status=status.HTTP_403_FORBIDDEN)

        defensa = DefensaTesis.objects.filter(proyecto=proyecto).first()
        return Response(DefensaTesisSerializer(defensa).data if defensa else {})

    def post(self, request, pk=None):
        proyecto = ProyectoTesis.objects.filter(pk=pk).select_related('alumno', 'director').first()
        if not proyecto:
            return Response({'detail': 'Proyecto de tesis no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if not (_es_coordinacion(request.user) or _es_director(request.user)):
            return Response({'detail': 'Solo coordinación o el director pueden programar la defensa.'}, status=status.HTTP_403_FORBIDDEN)

        if DefensaTesis.objects.filter(proyecto=proyecto).exists():
            return Response({'detail': 'Ya existe una defensa programada para este proyecto.'}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data.copy()
        data['proyecto'] = proyecto.pk
        _preparar_enlace_virtual(data)
        serializer = DefensaTesisSerializer(data=data)
        if serializer.is_valid():
            item = serializer.save()
            return Response(DefensaTesisSerializer(item).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk=None):
        proyecto = ProyectoTesis.objects.filter(pk=pk).select_related('alumno', 'director').first()
        if not proyecto:
            return Response({'detail': 'Proyecto de tesis no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if not (_es_coordinacion(request.user) or _es_director(request.user)):
            return Response({'detail': 'No tienes permisos para actualizar la defensa.'}, status=status.HTTP_403_FORBIDDEN)

        defensa = DefensaTesis.objects.filter(proyecto=proyecto).first()
        if not defensa:
            return Response({'detail': 'No existe una defensa registrada para este proyecto.'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        _preparar_enlace_virtual(data)
        serializer = DefensaTesisSerializer(defensa, data=data, partial=True)
        if serializer.is_valid():
            item = serializer.save()
            return Response(DefensaTesisSerializer(item).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JuradosDisponiblesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not (_es_coordinacion(request.user) or _es_director(request.user)):
            return Response({'detail': 'No tienes permisos para consultar docentes disponibles.'}, status=status.HTTP_403_FORBIDDEN)
        docentes = Aspirante.objects.filter(rol='docente', is_staff=False).order_by('nombre')
        return Response([
            {'id': docente.pk, 'nombre': docente.nombre, 'correo': docente.correo, 'usuario': docente.usuario}
            for docente in docentes
        ])

