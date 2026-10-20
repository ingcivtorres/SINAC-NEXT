"""Registro y consulta de egresados para Coordinación Académica y Servicios Escolares."""
import uuid
from collections import defaultdict
from datetime import date

from django.db import transaction
from django.db.models import Avg, Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .expediente_central_views import _es_gestion
from .models import Aspirante, ConfiguracionPrograma, EgresoAlumno, ExpedienteDigital, Inscripcion, ProyectoTesis
from .servicios_views import evaluar_prevalidacion_egreso
from .views import _registrar_seguimiento


def _permiso(user):
    return bool(user.is_superuser or _es_gestion(user))


def _foto(alumno):
    return alumno.profile_photo.url if alumno.profile_photo else None


def _serializar(egreso):
    alumno = egreso.alumno
    expediente = ExpedienteDigital.objects.filter(aspirante=alumno).first()
    return {
        'id': egreso.id,
        'alumno_id': alumno.id,
        'nombre': alumno.nombre,
        'matricula': alumno.matricula,
        'correo': alumno.correo,
        'telefono': alumno.telefono,
        'curp': alumno.curp,
        'profile_photo': _foto(alumno),
        'programa': alumno.programa,
        'departamento': alumno.departamento,
        'unidad': alumno.unidad,
        'modalidad': alumno.modalidad,
        'fecha_egreso': egreso.fecha_egreso.isoformat(),
        'generacion': egreso.generacion,
        'promedio_final': float(egreso.promedio_final) if egreso.promedio_final is not None else None,
        'titulo_tesis': egreso.titulo_tesis,
        'observaciones': egreso.observaciones,
        'excepcion_motivo': egreso.excepcion_motivo,
        'registrado_por': egreso.registrado_por.nombre if egreso.registrado_por else '',
        'expediente_id': expediente.id if expediente else None,
        'expediente_folio': expediente.folio if expediente else '',
    }


def _promedio(alumno):
    valor = Inscripcion.objects.filter(aspirante=alumno, calificacion__isnull=False).aggregate(valor=Avg('calificacion'))['valor']
    return round(float(valor), 2) if valor is not None else None


def _datos(request_data):
    fecha = request_data.get('fecha_egreso') or date.today().isoformat()
    try:
        fecha = date.fromisoformat(str(fecha)[:10])
    except ValueError:
        raise ValueError('La fecha de egreso no es válida.')
    promedio = request_data.get('promedio_final')
    if promedio in (None, ''):
        promedio = None
    else:
        try:
            promedio = round(float(promedio), 2)
        except (TypeError, ValueError):
            raise ValueError('El promedio final no es válido.')
        if not 0 <= promedio <= 10:
            raise ValueError('El promedio final debe estar entre 0 y 10.')
    return {
        'fecha_egreso': fecha,
        'generacion': str(request_data.get('generacion') or '').strip()[:40],
        'promedio_final': promedio,
        'titulo_tesis': str(request_data.get('titulo_tesis') or '').strip()[:255],
        'observaciones': str(request_data.get('observaciones') or '').strip(),
    }


class EgresadosView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not _permiso(request.user):
            return Response({'detail': 'No tienes permisos para consultar egresados.'}, status=status.HTTP_403_FORBIDDEN)
        egresos = EgresoAlumno.objects.select_related('alumno', 'registrado_por')
        q = request.query_params.get('q', '').strip()
        programa = request.query_params.get('programa', '').strip()
        generacion = request.query_params.get('generacion', '').strip()
        if q:
            egresos = egresos.filter(Q(alumno__nombre__icontains=q) | Q(alumno__matricula__icontains=q) | Q(alumno__correo__icontains=q) | Q(titulo_tesis__icontains=q))
        if programa:
            egresos = egresos.filter(alumno__programa__iexact=programa)
        if generacion:
            egresos = egresos.filter(generacion__iexact=generacion)
        base = EgresoAlumno.objects.select_related('alumno')
        candidatos = list(
            Aspirante.objects.filter(rol='alumno', egreso__isnull=True)
            .exclude(proceso_estado='baja')
            .order_by('nombre')
        )
        configuraciones = {}
        for item in ConfiguracionPrograma.objects.filter(activo=True).order_by('id').prefetch_related('materias_plan__materia'):
            configuraciones.setdefault(str(item.programa or '').strip().casefold(), item)
        inscripciones_por_alumno = defaultdict(list)
        if candidatos:
            for inscripcion in Inscripcion.objects.filter(
                aspirante_id__in=[alumno.pk for alumno in candidatos],
            ).select_related('materia', 'periodo_inscripcion'):
                inscripciones_por_alumno[inscripcion.aspirante_id].append(inscripcion)
        return Response({
            'egresados': [_serializar(item) for item in egresos],
            'filtros': {
                'programas': sorted({item.alumno.programa for item in base if item.alumno.programa}),
                'generaciones': sorted({item.generacion for item in base if item.generacion}),
            },
            'candidatos': [
                {
                    'id': a.id,
                    'nombre': a.nombre,
                    'matricula': a.matricula,
                    'programa': a.programa,
                    'profile_photo': _foto(a),
                    'prevalidacion_egreso': evaluar_prevalidacion_egreso(
                        a,
                        inscripciones_por_alumno[a.pk],
                        configuraciones.get(str(a.programa or '').strip().casefold()),
                    ),
                }
                for a in candidatos
            ],
        })

    @transaction.atomic
    def post(self, request):
        if not _permiso(request.user):
            return Response({'detail': 'No tienes permisos para registrar egresados.'}, status=status.HTTP_403_FORBIDDEN)
        alumno = Aspirante.objects.select_for_update().filter(pk=request.data.get('alumno_id'), rol='alumno').first()
        if not alumno:
            return Response({'detail': 'Selecciona un alumno válido.'}, status=status.HTTP_400_BAD_REQUEST)
        if EgresoAlumno.objects.filter(alumno=alumno).exists():
            return Response({'detail': 'El alumno ya está registrado como egresado.'}, status=status.HTTP_409_CONFLICT)
        try:
            datos = _datos(request.data)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        configuracion = ConfiguracionPrograma.objects.filter(programa__iexact=alumno.programa, activo=True).prefetch_related('materias_plan__materia').first()
        inscripciones = list(Inscripcion.objects.filter(aspirante=alumno).select_related('materia', 'periodo_inscripcion'))
        prevalidacion = evaluar_prevalidacion_egreso(alumno, inscripciones, configuracion)
        excepcion = str(request.data.get('excepcion_motivo') or '').strip()
        if not prevalidacion['completa'] and not excepcion:
            return Response({
                'detail': 'El alumno no cumple la prevalidación de egreso. Indica un motivo de excepción para registrarlo.',
                'codigo': 'prevalidacion_incompleta',
                'motivos': prevalidacion['motivos'],
            }, status=status.HTTP_409_CONFLICT)

        if datos['promedio_final'] is None:
            datos['promedio_final'] = _promedio(alumno)
        if not datos['titulo_tesis']:
            proyecto = ProyectoTesis.objects.filter(alumno=alumno).order_by('-id').first()
            datos['titulo_tesis'] = proyecto.titulo if proyecto else ''

        egreso = EgresoAlumno.objects.create(
            alumno=alumno, registrado_por=request.user,
            excepcion_motivo='' if prevalidacion['completa'] else excepcion,
            **datos,
        )
        alumno.proceso_estado = 'egresado'
        alumno.save(update_fields=['proceso_estado'])
        ExpedienteDigital.objects.get_or_create(
            aspirante=alumno,
            defaults={'folio': f'EXP-{timezone.now():%Y%m%d}-{alumno.pk:06d}-{uuid.uuid4().hex[:4].upper()}'},
        )
        _registrar_seguimiento(alumno, 'egresado', 'Egreso registrado oficialmente.', 'Egresados')
        return Response(_serializar(egreso), status=status.HTTP_201_CREATED)


class EgresadoDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _egreso(self, pk):
        return EgresoAlumno.objects.select_related('alumno', 'registrado_por').filter(pk=pk).first()

    def get(self, request, pk):
        if not _permiso(request.user):
            return Response({'detail': 'No tienes permisos para consultar egresados.'}, status=status.HTTP_403_FORBIDDEN)
        egreso = self._egreso(pk)
        if not egreso:
            return Response({'detail': 'Egresado no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(_serializar(egreso))

    def patch(self, request, pk):
        if not _permiso(request.user):
            return Response({'detail': 'No tienes permisos para editar egresados.'}, status=status.HTTP_403_FORBIDDEN)
        egreso = self._egreso(pk)
        if not egreso:
            return Response({'detail': 'Egresado no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            datos = _datos({**{
                'fecha_egreso': egreso.fecha_egreso.isoformat(),
                'generacion': egreso.generacion,
                'promedio_final': egreso.promedio_final,
                'titulo_tesis': egreso.titulo_tesis,
                'observaciones': egreso.observaciones,
            }, **request.data})
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        for campo, valor in datos.items():
            setattr(egreso, campo, valor)
        egreso.save()
        return Response(_serializar(egreso))
