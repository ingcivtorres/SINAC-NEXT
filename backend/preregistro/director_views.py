from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Aspirante, ExpedienteDigital, Inscripcion
from .serializers import ExpedienteDigitalSerializer, FirmaElectronicaSerializer, InscripcionSerializer


def _es_director(user):
    return str(getattr(user, 'rol', '')).strip().lower() in ('director', 'director de tesis')


def _tesistas_del_director(user):
    """Usa la relación formal y conserva compatibilidad con tutor_propuesto legado."""
    nombre = (getattr(user, 'nombre', '') or '').strip()
    usuario = (getattr(user, 'usuario', '') or '').strip()
    filtro = Q(director_tesis=user) | Q(tutor_propuesto__iexact=nombre)
    if usuario:
        filtro |= Q(tutor_propuesto__iexact=usuario)
    return Aspirante.objects.filter(filtro, is_staff=False).exclude(rol__in=('docente', 'director', 'servicios')).select_related('director_tesis').order_by('nombre').distinct()


def _estado_materia(inscripcion):
    if inscripcion.calificacion is None:
        return 'cursando'
    if inscripcion.calificacion < 7:
        return 'reprobada'
    if inscripcion.calificacion < 8:
        return 'aprobada_con_seguimiento'
    return 'aprobada'


class DirectorPanelView(APIView):
    """Panel conectado al director autenticado y únicamente a sus tesistas."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not _es_director(request.user):
            return Response({'detail': 'Solo un Director de Tesis puede consultar este panel.'}, status=status.HTTP_403_FORBIDDEN)

        tesistas = list(_tesistas_del_director(request.user))
        tesista_ids = [tesista.id for tesista in tesistas]
        inscripciones = list(
            Inscripcion.objects.filter(aspirante_id__in=tesista_ids)
            .select_related('aspirante', 'materia')
            .order_by('aspirante__nombre', 'materia__clave')
        )
        expedientes = list(
            ExpedienteDigital.objects.filter(aspirante_id__in=tesista_ids)
            .select_related('aspirante')
            .prefetch_related('firmas__firmante')
        )
        inscripciones_por_alumno = {tesista.id: [] for tesista in tesistas}
        for inscripcion in inscripciones:
            inscripciones_por_alumno.setdefault(inscripcion.aspirante_id, []).append(inscripcion)

        tesistas_data = []
        for tesista in tesistas:
            materias = inscripciones_por_alumno.get(tesista.id, [])
            finales = [float(item.calificacion) for item in materias if item.calificacion is not None]
            tesistas_data.append({
                'id': tesista.id,
                'nombre': tesista.nombre,
                'usuario': tesista.usuario,
                'correo': tesista.correo,
                'matricula': tesista.matricula,
                'programa': tesista.programa,
                'departamento': tesista.departamento,
                'proceso_estado': tesista.proceso_estado,
                'materias': InscripcionSerializer(materias, many=True).data,
                'total_materias': len(materias),
                'materias_aprobadas': sum(1 for item in materias if _estado_materia(item) == 'aprobada'),
                'materias_reprobadas': sum(1 for item in materias if _estado_materia(item) == 'reprobada'),
                'materias_cursando': sum(1 for item in materias if _estado_materia(item) == 'cursando'),
                'creditos_aprobados': sum(item.materia.creditos for item in materias if item.calificacion is not None and item.calificacion >= 7),
                'promedio': round(sum(finales) / len(finales), 2) if finales else None,
            })

        expedientes_data = []
        for expediente in expedientes:
            item = ExpedienteDigitalSerializer(expediente).data
            item['firmas'] = FirmaElectronicaSerializer(expediente.firmas.all(), many=True).data
            expedientes_data.append(item)

        return Response({
            'director': {
                'id': request.user.id,
                'nombre': request.user.nombre,
                'usuario': request.user.usuario,
                'correo': request.user.correo,
                'departamento': request.user.departamento,
                'programa': request.user.programa,
            },
            'tesistas': tesistas_data,
            'expedientes': expedientes_data,
            'resumen': {
                'tesistas_asignados': len(tesistas_data),
                'expedientes_activos': sum(1 for item in expedientes if item.estado == 'activo'),
                'expedientes_sin_firma': sum(1 for item in expedientes if not any(firma.rol_firmante == 'director' for firma in item.firmas.all())),
                'evaluaciones': len(inscripciones),
                'avances_por_revisar': 0,
            },
            'avance_tesis_disponible': False,
            'avance_tesis_mensaje': 'El avance de tesis requiere el módulo de seguimiento de tesis; la asignación y el expediente ya están conectados.',
        })
