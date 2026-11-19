from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Aspirante, ConfiguracionPrograma, ExpedienteDigital, Inscripcion, ProyectoTesis, SolicitudDireccionTesis
from .serializers import ExpedienteDigitalSerializer, FirmaElectronicaSerializer, InscripcionSerializer, ProyectoTesisSerializer
from .seguridad import url_media


from .roles import es_director


def _es_director(user):
    return es_director(user)


def _tesistas_del_director(user):
    """Alumnos cuyo Director de Tesis formal (confirmado por match) es el usuario.

    No se usa ``tutor_propuesto``: es texto libre capturado por el aspirante y
    no acredita la dirección de tesis.
    """
    if not getattr(user, 'pk', None):
        return Aspirante.objects.none()
    return Aspirante.objects.filter(director_tesis=user, rol='alumno', is_staff=False).select_related('director_tesis').order_by('nombre')


def programas_doctorado():
    return {
        programa.strip().lower()
        for programa in ConfiguracionPrograma.objects.filter(grado='doctorado').values_list('programa', flat=True)
    }


def es_programa_doctorado(programa, doctorados=None):
    nombre = (programa or '').strip().lower()
    if not nombre:
        return False
    if doctorados is None:
        doctorados = programas_doctorado()
    return nombre in doctorados or 'doctorado' in nombre


ESTADOS_SIN_CURSAR = {'baja', 'egresado', 'inactivo', 'suspendido'}


def periodo_inicio_tesis(configuracion):
    """Primer periodo del segundo año: 4.º semestre o 4.º cuatrimestre."""
    periodicidad = getattr(configuracion, 'periodicidad', None)
    return (3 if periodicidad == 'cuatrimestral' else 2) + 1


def requisitos_predoctoral(alumno, doctorados=None):
    """Motivos por los que aún no se puede programar el predoctoral; lista vacía si está habilitado."""
    from .tesis_flujo_views import tiene_match_tesis

    if not es_programa_doctorado(alumno.programa, doctorados):
        return ['El examen predoctoral solo aplica a alumnos de doctorado.']
    motivos = []
    if not alumno.is_active or str(alumno.proceso_estado or '').strip().lower() in ESTADOS_SIN_CURSAR:
        motivos.append('El alumno no está cursando actualmente el doctorado (baja, egreso o inactividad).')
    configuracion = ConfiguracionPrograma.objects.filter(programa__iexact=alumno.programa, activo=True).first()
    minimo = periodo_inicio_tesis(configuracion)
    if (alumno.numero_periodo_actual or 0) < minimo:
        motivos.append(f'El alumno debe cursar al menos el periodo {minimo} del doctorado.')
    if not alumno.director_tesis_id or not tiene_match_tesis(alumno):
        motivos.append('El alumno necesita un Director de Tesis con match confirmado.')
    return motivos


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
        proyectos = ProyectoTesis.objects.filter(alumno_id__in=tesista_ids).select_related('alumno', 'director')
        doctorados = programas_doctorado()
        solicitudes_direccion = SolicitudDireccionTesis.objects.filter(
            director_asignado=request.user, estado='pendiente_director',
        ).select_related('alumno', 'director_sugerido', 'director_asignado')
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
                'es_doctorado': es_programa_doctorado(tesista.programa, doctorados),
                'predoctoral_motivos': requisitos_predoctoral(tesista, doctorados),
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
                'profile_photo': url_media(request.user.profile_photo),
            },
            'tesistas': tesistas_data,
            'expedientes': expedientes_data,
            'proyectos_tesis': ProyectoTesisSerializer(proyectos, many=True).data,
            'solicitudes_direccion': [{
                'id': solicitud.id,
                'alumno': {'id': solicitud.alumno_id, 'nombre': solicitud.alumno.nombre, 'matricula': solicitud.alumno.matricula, 'programa': solicitud.alumno.programa},
                'director_sugerido': {'id': solicitud.director_sugerido_id, 'nombre': solicitud.director_sugerido.nombre} if solicitud.director_sugerido else None,
                'linea_investigacion': solicitud.linea_investigacion,
                'justificacion': solicitud.justificacion,
                'estado': solicitud.estado,
                'created_at': solicitud.created_at,
            } for solicitud in solicitudes_direccion],
            'resumen': {
                'tesistas_asignados': len(tesistas_data),
                'expedientes_activos': sum(1 for item in expedientes if item.estado == 'activo'),
                'expedientes_sin_firma': sum(1 for item in expedientes if not any(firma.rol_firmante == 'director' for firma in item.firmas.all())),
                'evaluaciones': len(inscripciones),
                'avances_por_revisar': proyectos.filter(estado='en_revision').count(),
                'solicitudes_direccion_pendientes': solicitudes_direccion.count(),
            },
            'avance_tesis_disponible': True,
            'avance_tesis_mensaje': 'Los proyectos enviados por tus tesistas aparecen aquí para revisión y dictamen.',
        })
