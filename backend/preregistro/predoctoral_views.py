import uuid
from decimal import Decimal, InvalidOperation

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .director_views import _tesistas_del_director
from .models import Aspirante, ExamenEnLinea
from .serializers import ExamenEnLineaSerializer
from .views import _registrar_seguimiento


def _rol(user):
    return str(getattr(user, 'rol', '') or '').strip().lower()


def _es_director(user):
    return _rol(user) in {'director', 'director de tesis'}


def _es_coordinacion(user):
    return bool(getattr(user, 'is_staff', False) or _rol(user) in {
        'admin', 'administrador', 'coordinacion', 'coordinador',
        'servicios', 'servicios escolares', 'servicios_escolares',
    })


def _puede_evaluar(user, alumno):
    if _es_coordinacion(user):
        return True
    return _es_director(user) and _tesistas_del_director(user).filter(pk=alumno.pk).exists()


def _serializer(examen):
    return ExamenEnLineaSerializer(examen).data


class PredoctoralExamView(APIView):
    """Programación y consulta del examen predoctoral con alcance por rol."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if _es_director(request.user):
            alumnos = _tesistas_del_director(request.user)
            examenes = ExamenEnLinea.objects.filter(tipo='predoctoral', aspirante__in=alumnos).select_related('aspirante')
        elif _es_coordinacion(request.user):
            examenes = ExamenEnLinea.objects.filter(tipo='predoctoral').select_related('aspirante')
        elif _rol(request.user) == 'alumno':
            examenes = ExamenEnLinea.objects.filter(tipo='predoctoral', aspirante=request.user).select_related('aspirante')
        else:
            return Response({'detail': 'No tienes permisos para consultar exámenes predoctorales.'}, status=status.HTTP_403_FORBIDDEN)
        examenes = examenes.order_by('-fecha_programada', '-created_at')
        data = [_serializer(examen) for examen in examenes]
        for item, examen in zip(data, examenes):
            item['alumno'] = {
                'id': examen.aspirante_id,
                'nombre': examen.aspirante.nombre,
                'matricula': examen.aspirante.matricula,
                'programa': examen.aspirante.programa,
            }
        return Response({'examenes': data, 'total': len(data)})

    def post(self, request):
        if not (_es_director(request.user) or _es_coordinacion(request.user)):
            return Response({'detail': 'Solo el Director de Tesis o Coordinación Académica puede programar este examen.'}, status=status.HTTP_403_FORBIDDEN)
        alumno_id = request.data.get('aspirante_id') or request.data.get('alumno_id')
        fecha_programada = request.data.get('fecha_programada')
        if not fecha_programada or not parse_datetime(str(fecha_programada)):
            return Response({'fecha_programada': 'Indica una fecha y hora válidas para el examen.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            alumno = Aspirante.objects.get(pk=alumno_id, rol='alumno', is_staff=False)
        except (Aspirante.DoesNotExist, TypeError, ValueError):
            return Response({'detail': 'Selecciona un alumno válido.'}, status=status.HTTP_400_BAD_REQUEST)
        if not _puede_evaluar(request.user, alumno):
            return Response({'detail': 'El alumno no está asignado a este Director de Tesis.'}, status=status.HTTP_403_FORBIDDEN)
        examen = ExamenEnLinea.objects.create(
            aspirante=alumno,
            tipo='predoctoral',
            titulo=request.data.get('titulo') or 'Examen predoctoral',
            descripcion=request.data.get('descripcion') or '',
            fecha_programada=fecha_programada,
            duracion_minutos=request.data.get('duracion_minutos') or 120,
            max_intentos=1,
            business_key=f'PREDOC-{alumno.pk}-{uuid.uuid4().hex[:10].upper()}',
        )
        _registrar_seguimiento(alumno, 'predoctoral_programado', 'Se programó tu examen predoctoral.', 'Director de Tesis' if _es_director(request.user) else 'Coordinación Académica', notificar=False)
        return Response(_serializer(examen), status=status.HTTP_201_CREATED)


class PredoctoralExamDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, request, pk):
        try:
            examen = ExamenEnLinea.objects.select_related('aspirante').get(pk=pk, tipo='predoctoral')
        except ExamenEnLinea.DoesNotExist:
            return None, Response({'detail': 'Examen predoctoral no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if not (_rol(request.user) == 'alumno' and examen.aspirante_id == request.user.pk) and not _puede_evaluar(request.user, examen.aspirante):
            return None, Response({'detail': 'No tienes permisos para consultar este examen.'}, status=status.HTTP_403_FORBIDDEN)
        return examen, None

    def get(self, request, pk):
        examen, error = self.get_object(request, pk)
        return error or Response(_serializer(examen))

    def patch(self, request, pk):
        examen, error = self.get_object(request, pk)
        if error:
            return error
        if not _puede_evaluar(request.user, examen.aspirante):
            return Response({'detail': 'El alumno no puede modificar el resultado del examen.'}, status=status.HTTP_403_FORBIDDEN)
        allowed = {'titulo', 'descripcion', 'fecha_programada', 'duracion_minutos', 'estado', 'calificacion', 'retroalimentacion'}
        unknown = set(request.data) - allowed
        if unknown:
            return Response({'detail': f'Campos no permitidos: {", ".join(sorted(unknown))}.'}, status=status.HTTP_400_BAD_REQUEST)
        if 'titulo' in request.data:
            examen.titulo = str(request.data['titulo']).strip() or 'Examen predoctoral'
        if 'descripcion' in request.data:
            examen.descripcion = str(request.data['descripcion'])
        if 'fecha_programada' in request.data:
            examen.fecha_programada = request.data['fecha_programada'] or None
        if 'duracion_minutos' in request.data:
            try:
                examen.duracion_minutos = max(15, int(request.data['duracion_minutos']))
            except (TypeError, ValueError):
                return Response({'detail': 'La duración debe ser un número entero.'}, status=status.HTTP_400_BAD_REQUEST)
        if 'retroalimentacion' in request.data:
            examen.retroalimentacion = str(request.data['retroalimentacion'])
        if 'calificacion' in request.data and request.data['calificacion'] not in ('', None):
            try:
                nota = Decimal(str(request.data['calificacion']))
            except (InvalidOperation, ValueError):
                return Response({'detail': 'La calificación debe ser un número entre 0 y 10.'}, status=status.HTTP_400_BAD_REQUEST)
            if nota < 0 or nota > 10:
                return Response({'detail': 'La calificación debe estar entre 0 y 10.'}, status=status.HTTP_400_BAD_REQUEST)
            examen.calificacion = nota
            examen.estado = 'aprobado' if nota >= 8 else 'reprobado'
            examen.fecha_fin = examen.fecha_fin or timezone.now()
        elif 'estado' in request.data:
            estado = str(request.data['estado'])
            if estado not in dict(ExamenEnLinea.ESTADOS_EXAMEN):
                return Response({'detail': 'Estado de examen no válido.'}, status=status.HTTP_400_BAD_REQUEST)
            examen.estado = estado
            if estado == 'iniciado' and not examen.fecha_inicio:
                examen.fecha_inicio = timezone.now()
            if estado in {'completado', 'aprobado', 'reprobado', 'cancelado'} and not examen.fecha_fin:
                examen.fecha_fin = timezone.now()
        examen.save()
        return Response(_serializer(examen))

    put = patch
