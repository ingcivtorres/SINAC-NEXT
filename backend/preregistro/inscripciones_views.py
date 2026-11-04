"""Periodos de inscripción, inscripción regular y extemporánea."""
import logging
from xml.sax.saxutils import escape
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import FileResponse
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Aspirante, ConfiguracionPrograma, CargaAcademicaMateria, Inscripcion, PlanEstudioMateria, SolicitudDireccionTesis, SolicitudInscripcionExtemporanea, SolicitudInscripcionExtemporaneaMateria, PeriodoInscripcion
from .serializers import (
    MateriaSerializer,
    InscripcionSerializer,
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from io import BytesIO
from .views import (
    _registrar_seguimiento,
)

logger = logging.getLogger(__name__)


def _periodo_inscripcion_vigente():
    """Devuelve el único periodo habilitado que contiene la fecha actual."""
    from django.utils import timezone
    return PeriodoInscripcion.objects.filter(
        activo=True,
        apertura__lte=timezone.now(),
        cierre__gte=timezone.now(),
    ).order_by('-apertura').first()


def _materias_plan_disponibles(alumno, configuracion):
    periodo_actual = getattr(alumno, 'numero_periodo_actual', None)
    if not periodo_actual:
        return PlanEstudioMateria.objects.none()
    aprobadas = Inscripcion.objects.filter(aspirante=alumno, calificacion__gte=7).values_list('materia_id', flat=True)
    materias = PlanEstudioMateria.objects.filter(configuracion=configuracion).filter(
        Q(periodo_sugerido=periodo_actual) | Q(periodo_sugerido__lt=periodo_actual, obligatoria=True)
    ).exclude(materia_id__in=aprobadas)
    if not _puede_elegir_seminario(alumno, configuracion):
        materias = materias.exclude(materia__categoria='seminario')
    return materias.select_related('materia').order_by('periodo_sugerido', 'materia__clave')


MATERIAS_POR_PERIODO = 4


def _materias_requeridas_periodo(alumno, configuracion, periodo):
    """Carga obligatoria del periodo: 4 materias, o todas las ofertadas del plan si hay menos."""
    inscritas = set(Inscripcion.objects.filter(aspirante=alumno, periodo_inscripcion=periodo).values_list('materia_id', flat=True))
    plan_ids = set(_materias_plan_disponibles(alumno, configuracion).values_list('materia_id', flat=True))
    ofertadas = set(CargaAcademicaMateria.objects.filter(
        carga__estado='publicada', carga__periodo_inscripcion=periodo, materia_id__in=plan_ids,
    ).values_list('materia_id', flat=True))
    return min(MATERIAS_POR_PERIODO, len(inscritas | ofertadas))


def _tiene_match_tesis(alumno):
    match = SolicitudDireccionTesis.objects.filter(
        alumno=alumno, estado='aprobada', director_asignado_id=alumno.director_tesis_id,
    ).exists()
    return match or (
        alumno.director_tesis_id
        and not SolicitudDireccionTesis.objects.filter(alumno=alumno).exists()
    )


def _puede_elegir_seminario(alumno, configuracion):
    periodos_por_anio = 3 if configuracion.periodicidad == 'cuatrimestral' else 2
    periodo_inicio_tesis = periodos_por_anio + 1
    return bool(
        alumno.numero_periodo_actual
        and alumno.numero_periodo_actual >= periodo_inicio_tesis
        and _tiene_match_tesis(alumno)
    )


class MisMateriasDisponiblesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff or getattr(request.user, 'rol', '') != 'alumno':
            return Response(status=status.HTTP_403_FORBIDDEN)
        periodo = _periodo_inscripcion_vigente()
        if not periodo:
            return Response([])
        configuracion = ConfiguracionPrograma.objects.filter(programa__iexact=request.user.programa, activo=True).first()
        if not configuracion or not request.user.numero_periodo_actual:
            return Response([])
        materias_plan = {
            item['materia_id']: item
            for item in _materias_plan_disponibles(request.user, configuracion).values(
                'materia_id', 'periodo_sugerido', 'obligatoria',
            )
        }
        detalles = CargaAcademicaMateria.objects.filter(
            carga__estado='publicada',
            carga__periodo_inscripcion=periodo,
            materia_id__in=materias_plan,
        ).select_related('materia', 'docente').order_by('materia__clave')
        inscritos = dict(
            Inscripcion.objects.filter(
                periodo_inscripcion=periodo,
                materia_id__in=materias_plan,
            ).values('materia_id').annotate(total=Count('id')).values_list('materia_id', 'total')
        )
        disponibles = []
        for detalle in detalles:
            materia = MateriaSerializer(detalle.materia).data
            materia.update({
                'profesor': detalle.docente.nombre if detalle.docente else detalle.materia.profesor,
                'horario': detalle.horario,
                'salon': detalle.salon,
                'salon_label': detalle.get_salon_display(),
                'capacidad': detalle.capacidad,
                'inscritos': inscritos.get(detalle.materia_id, 0),
                'modalidad': detalle.modalidad,
                'periodo_sugerido': materias_plan[detalle.materia_id]['periodo_sugerido'],
                'obligatoria': materias_plan[detalle.materia_id]['obligatoria'],
            })
            disponibles.append(materia)
        return Response(disponibles)

class PeriodoInscripcionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def puede_gestionar(user):
        rol = str(getattr(user, 'rol', '')).strip().lower()
        return rol in {
            'admin', 'administrador', 'servicios', 'servicios_escolares', 'servicios escolares',
        }

    @staticmethod
    def puede_consultar_todos(user):
        return PeriodoInscripcionView.puede_gestionar(user)

    @staticmethod
    def serializar(periodo):
        from django.utils import timezone
        ahora = timezone.now()
        vigente = periodo.activo and periodo.apertura <= ahora <= periodo.cierre
        return {
            'id': periodo.id,
            'nombre': periodo.nombre,
            'apertura': periodo.apertura,
            'cierre': periodo.cierre,
            'activo': vigente,
            'habilitado': periodo.activo,
        }

    def guardar_periodo(self, request, periodo=None):
        from django.utils.dateparse import parse_datetime
        from django.utils import timezone

        data = request.data
        nombre = str(data.get('nombre', periodo.nombre if periodo else '') or '').strip()
        apertura_raw = data.get('apertura')
        cierre_raw = data.get('cierre')
        apertura = parse_datetime(str(apertura_raw)) if apertura_raw else (periodo.apertura if periodo else None)
        cierre = parse_datetime(str(cierre_raw)) if cierre_raw else (periodo.cierre if periodo else None)
        activo_raw = data.get('activo', periodo.activo if periodo else False)
        activo = activo_raw if isinstance(activo_raw, bool) else str(activo_raw).strip().lower() in ('1', 'true', 'si', 'sí', 'activo')

        if not nombre or not apertura or not cierre:
            return Response({'detail': 'Nombre, apertura y cierre son obligatorios y deben usar fechas válidas.'}, status=status.HTTP_400_BAD_REQUEST)
        if timezone.is_naive(apertura):
            apertura = timezone.make_aware(apertura)
        if timezone.is_naive(cierre):
            cierre = timezone.make_aware(cierre)
        if apertura >= cierre:
            return Response({'detail': 'La fecha de apertura debe ser anterior a la fecha de cierre.'}, status=status.HTTP_400_BAD_REQUEST)

        duplicado = PeriodoInscripcion.objects.filter(nombre=nombre)
        traslapado = PeriodoInscripcion.objects.filter(activo=True, apertura__lt=cierre, cierre__gt=apertura)
        if periodo:
            duplicado = duplicado.exclude(pk=periodo.pk)
            traslapado = traslapado.exclude(pk=periodo.pk)
        if duplicado.exists():
            return Response({'detail': 'Ya existe un periodo con ese nombre.'}, status=status.HTTP_409_CONFLICT)
        if activo and traslapado.exists():
            return Response({'detail': 'El periodo se traslapa con otro periodo de inscripción activo.'}, status=status.HTTP_409_CONFLICT)

        if periodo is None:
            periodo = PeriodoInscripcion.objects.create(nombre=nombre, apertura=apertura, cierre=cierre, activo=activo)
            response_status = status.HTTP_201_CREATED
        else:
            periodo.nombre = nombre
            periodo.apertura = apertura
            periodo.cierre = cierre
            periodo.activo = activo
            periodo.save(update_fields=['nombre', 'apertura', 'cierre', 'activo'])
            response_status = status.HTTP_200_OK
        return Response(self.serializar(periodo), status=response_status)

    def get(self, request):
        if request.query_params.get('todos') in ('1', 'true', 'True'):
            if not self.puede_consultar_todos(request.user):
                return Response(status=status.HTTP_403_FORBIDDEN)
            periodos = PeriodoInscripcion.objects.order_by('-apertura')
            return Response([self.serializar(periodo) for periodo in periodos])
        p = _periodo_inscripcion_vigente() or PeriodoInscripcion.objects.order_by('-apertura').first()
        if not p:
            return Response({'activo': False, 'habilitado': False})
        return Response(self.serializar(p))

    def post(self, request):
        if not self.puede_gestionar(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return self.guardar_periodo(request)

    def put(self, request):
        if not self.puede_gestionar(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        periodo_id = request.data.get('id')
        if not periodo_id:
            return Response({'detail': 'Se requiere el identificador del periodo.'}, status=status.HTTP_400_BAD_REQUEST)
        periodo = PeriodoInscripcion.objects.filter(pk=periodo_id).first()
        if not periodo:
            return Response({'detail': 'No se encontró el periodo de inscripción.'}, status=status.HTTP_404_NOT_FOUND)
        return self.guardar_periodo(request, periodo)


class MisInscripcionesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        inscripciones = request.user.inscripciones.select_related('materia', 'periodo_inscripcion').order_by('materia__clave')
        return Response(InscripcionSerializer(inscripciones, many=True).data)

    def post(self, request):
        if request.user.is_staff or getattr(request.user, 'rol', '') != 'alumno':
            return Response(status=status.HTTP_403_FORBIDDEN)
        periodo = _periodo_inscripcion_vigente()
        if not periodo:
            return Response({'detail': 'El periodo de inscripción está cerrado o no ha sido habilitado por Coordinación Académica.'}, status=status.HTTP_409_CONFLICT)
        numero_periodo = getattr(request.user, 'numero_periodo_actual', None)
        if not numero_periodo:
            return Response({'detail': 'Coordinación Académica debe asignarte el semestre o cuatrimestre actual.'}, status=status.HTTP_409_CONFLICT)
        configuracion = ConfiguracionPrograma.objects.filter(programa__iexact=request.user.programa, activo=True).first()
        if not configuracion:
            return Response({'detail': 'Tu programa aún no tiene un plan de estudios configurado.'}, status=status.HTTP_409_CONFLICT)

        materias_ids = request.data.get('materias')
        if not isinstance(materias_ids, list) or not all(str(item).isdigit() for item in materias_ids):
            return Response({'materias': 'Envía una lista de materias para completar la carga del periodo.'}, status=status.HTTP_400_BAD_REQUEST)
        materias_ids = [int(item) for item in materias_ids]
        if len(set(materias_ids)) != len(materias_ids):
            return Response({'materias': 'No repitas materias en la selección.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                Aspirante.objects.select_for_update().filter(pk=request.user.pk).first()
                existentes_periodo = Inscripcion.objects.filter(aspirante=request.user, periodo_inscripcion=periodo)
                existentes_ids = set(existentes_periodo.values_list('materia_id', flat=True))
                requeridas = _materias_requeridas_periodo(request.user, configuracion, periodo)
                if not _puede_elegir_seminario(request.user, configuracion) and configuracion.materias_plan.filter(
                    materia_id__in=materias_ids, materia__categoria='seminario',
                ).exists():
                    return Response(
                        {'detail': 'La materia de Seminario de tesis se habilita cuando tú y tu Director confirmen el match del proyecto.'},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                if existentes_periodo.count() + len(materias_ids) != requeridas:
                    faltantes = max(0, requeridas - existentes_periodo.count())
                    return Response({'detail': f'Debes completar {requeridas} materias este periodo. Selecciona {faltantes}.'}, status=status.HTTP_400_BAD_REQUEST)
                if existentes_ids.intersection(materias_ids):
                    return Response({'detail': 'Ya tienes una de esas materias inscrita en este periodo.'}, status=status.HTTP_400_BAD_REQUEST)

                plan_ids = set(_materias_plan_disponibles(request.user, configuracion).filter(
                    materia_id__in=materias_ids,
                ).values_list('materia_id', flat=True))
                if plan_ids != set(materias_ids):
                    return Response({'detail': 'Solo puedes inscribir materias del plan correspondiente a tu semestre o cuatrimestre actual.'}, status=status.HTTP_400_BAD_REQUEST)
                if Inscripcion.objects.filter(aspirante=request.user, materia_id__in=materias_ids, periodo_inscripcion=periodo).exists():
                    return Response({'detail': 'Ya tienes una de esas materias inscrita en este periodo.'}, status=status.HTTP_400_BAD_REQUEST)

                detalles = list(
                    CargaAcademicaMateria.objects.select_for_update()
                    .filter(
                        carga__estado='publicada',
                        carga__periodo_inscripcion=periodo,
                        materia_id__in=materias_ids,
                    )
                    .select_related('materia')
                    .order_by('materia__clave')
                )
                detalles_por_materia = {detalle.materia_id: detalle for detalle in detalles}
                if set(detalles_por_materia) != set(materias_ids):
                    return Response(
                        {'materias': 'Una o más materias ya no forman parte de una carga publicada para este periodo.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                materias = [detalles_por_materia[materia_id].materia for materia_id in materias_ids]
                llenas = [
                    detalle.materia
                    for detalle in detalles
                    if Inscripcion.objects.filter(materia_id=detalle.materia_id, periodo_inscripcion=periodo).count()
                    >= detalle.capacidad
                ]
                if llenas:
                    return Response({'detail': f'No hay cupo en: {", ".join(materia.clave for materia in llenas)}.'}, status=status.HTTP_409_CONFLICT)

                inscripciones = [
                    Inscripcion(
                        aspirante=request.user,
                        materia=materia,
                        periodo_inscripcion=periodo,
                        horario=detalles_por_materia[materia.id].horario,
                    )
                    for materia in materias
                ]
                Inscripcion.objects.bulk_create(inscripciones)
        except IntegrityError:
            return Response({'detail': 'Una o más materias ya quedaron registradas en este periodo. Actualiza tu información.'}, status=status.HTTP_409_CONFLICT)

        for materia in materias:
            _registrar_seguimiento(request.user, 'pendiente', f'Solicitud de inscripción recibida para {materia.clave} - {materia.nombre}.', 'Alumno', notificar=True, asunto='Solicitud de inscripción recibida')
        return Response(InscripcionSerializer(inscripciones, many=True).data, status=status.HTTP_201_CREATED)


class InscripcionCoordinacionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    total_materias_periodo = 4

    @staticmethod
    def puede_gestionar(user):
        rol = str(getattr(user, 'rol', '')).strip().lower()
        if rol in {'servicios', 'servicios_escolares', 'servicios escolares'}:
            return False
        return bool(user.is_staff or rol in {'admin', 'administrador', 'coordinacion', 'coordinador'})

    @staticmethod
    def alumno(pk):
        return Aspirante.objects.filter(pk=pk, rol='alumno', is_staff=False).first()

    def get(self, request, pk):
        if not self.puede_gestionar(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        alumno = self.alumno(pk)
        if not alumno:
            return Response({'detail': 'No se encontró el alumno.'}, status=status.HTTP_404_NOT_FOUND)

        periodo = _periodo_inscripcion_vigente()
        inscripciones = Inscripcion.objects.filter(aspirante=alumno, periodo_inscripcion=periodo) if periodo else Inscripcion.objects.none()
        registradas = inscripciones.count()
        materias = []
        configuracion = ConfiguracionPrograma.objects.filter(programa__iexact=alumno.programa, activo=True).first()
        requeridas = (
            _materias_requeridas_periodo(alumno, configuracion, periodo)
            if periodo and configuracion and alumno.numero_periodo_actual else self.total_materias_periodo
        )
        faltantes = max(0, requeridas - registradas)
        if periodo and configuracion and alumno.numero_periodo_actual and faltantes:
            ya_inscritas = set(inscripciones.values_list('materia_id', flat=True))
            plan_ids = set(_materias_plan_disponibles(alumno, configuracion).values_list('materia_id', flat=True)) - ya_inscritas
            detalles = CargaAcademicaMateria.objects.filter(
                carga__estado='publicada',
                carga__periodo_inscripcion=periodo,
                materia_id__in=plan_ids,
            ).select_related('materia').order_by('materia__clave')
            inscritos = dict(
                Inscripcion.objects.filter(
                    periodo_inscripcion=periodo,
                    materia_id__in=[detalle.materia_id for detalle in detalles],
                ).values('materia_id').annotate(total=Count('id')).values_list('materia_id', 'total')
            )
            materias = [{
                'id': detalle.materia_id,
                'clave': detalle.materia.clave,
                'nombre': detalle.materia.nombre,
                'creditos': detalle.materia.creditos,
                'horario': detalle.horario,
                'capacidad': detalle.capacidad,
                'inscritos': inscritos.get(detalle.materia_id, 0),
            } for detalle in detalles]

        return Response({
            'alumno': {'id': alumno.id, 'nombre': alumno.nombre, 'matricula': alumno.matricula, 'programa': alumno.programa},
            'periodo': PeriodoInscripcionView.serializar(periodo) if periodo else None,
            'registradas': registradas,
            'requeridas': requeridas,
            'faltantes': faltantes,
            'validacion_servicios': list(inscripciones.values_list('validacion_servicios', flat=True)),
            'materias': materias,
        })

    def post(self, request, pk):
        if not self.puede_gestionar(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        alumno = self.alumno(pk)
        if not alumno:
            return Response({'detail': 'No se encontró el alumno.'}, status=status.HTTP_404_NOT_FOUND)
        periodo = _periodo_inscripcion_vigente()
        if not periodo:
            return Response({'detail': 'No hay un periodo de inscripción abierto. Servicios Escolares debe habilitarlo.'}, status=status.HTTP_409_CONFLICT)
        if not alumno.numero_periodo_actual:
            return Response({'detail': 'Asigna primero el semestre o cuatrimestre actual del alumno.'}, status=status.HTTP_409_CONFLICT)
        configuracion = ConfiguracionPrograma.objects.filter(programa__iexact=alumno.programa, activo=True).first()
        if not configuracion:
            return Response({'detail': 'El programa del alumno no tiene un plan de estudios activo.'}, status=status.HTTP_409_CONFLICT)

        materias_ids = request.data.get('materias')
        if not isinstance(materias_ids, list) or not materias_ids or not all(str(item).isdigit() for item in materias_ids):
            return Response({'materias': 'Selecciona las materias pendientes del alumno.'}, status=status.HTTP_400_BAD_REQUEST)
        materias_ids = [int(item) for item in materias_ids]
        if len(set(materias_ids)) != len(materias_ids):
            return Response({'materias': 'No repitas materias en la selección.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                periodo = PeriodoInscripcion.objects.select_for_update().filter(
                    pk=periodo.pk,
                    activo=True,
                    apertura__lte=timezone.now(),
                    cierre__gte=timezone.now(),
                ).first()
                if not periodo:
                    return Response({'detail': 'El periodo de inscripción se cerró. No se registraron cambios.'}, status=status.HTTP_409_CONFLICT)

                existentes = Inscripcion.objects.filter(aspirante=alumno, periodo_inscripcion=periodo)
                registradas = existentes.count()
                requeridas = _materias_requeridas_periodo(alumno, configuracion, periodo)
                faltantes = requeridas - registradas
                if faltantes <= 0:
                    return Response({'detail': 'El alumno ya completó su carga de materias de este periodo.'}, status=status.HTTP_409_CONFLICT)
                if len(materias_ids) != faltantes:
                    return Response(
                        {'detail': f'Selecciona exactamente las {faltantes} materias que faltan para completar las {requeridas} del periodo.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                ya_inscritas = set(existentes.values_list('materia_id', flat=True))
                if ya_inscritas.intersection(materias_ids):
                    return Response({'detail': 'El alumno ya tiene una de esas materias inscrita en este periodo.'}, status=status.HTTP_400_BAD_REQUEST)

                plan_ids = set(_materias_plan_disponibles(alumno, configuracion).filter(
                    materia_id__in=materias_ids,
                ).values_list('materia_id', flat=True))
                if plan_ids != set(materias_ids):
                    return Response({'detail': 'Solo puedes inscribir materias del plan correspondiente al periodo académico actual.'}, status=status.HTTP_400_BAD_REQUEST)
                detalles = list(
                    CargaAcademicaMateria.objects.select_for_update()
                    .filter(carga__estado='publicada', carga__periodo_inscripcion=periodo, materia_id__in=materias_ids)
                    .select_related('materia')
                    .order_by('materia__clave')
                )
                detalles_por_materia = {detalle.materia_id: detalle for detalle in detalles}
                if set(detalles_por_materia) != set(materias_ids):
                    return Response({'materias': 'Una o más materias no pertenecen a una carga publicada para el periodo vigente.'}, status=status.HTTP_400_BAD_REQUEST)
                llenas = [
                    detalle.materia.clave for detalle in detalles
                    if Inscripcion.objects.filter(materia_id=detalle.materia_id, periodo_inscripcion=periodo).count() >= detalle.capacidad
                ]
                if llenas:
                    return Response({'detail': f'No hay cupo en: {", ".join(llenas)}.'}, status=status.HTTP_409_CONFLICT)

                materias = [detalles_por_materia[materia_id].materia for materia_id in materias_ids]
                inscripciones = [
                    Inscripcion(
                        aspirante=alumno,
                        materia=materia,
                        periodo_inscripcion=periodo,
                        horario=detalles_por_materia[materia.id].horario,
                        validacion_servicios='pendiente',
                        registrada_por=request.user,
                    )
                    for materia in materias
                ]
                Inscripcion.objects.bulk_create(inscripciones)
        except IntegrityError:
            return Response({'detail': 'Una o más materias ya fueron registradas para el alumno en este periodo.'}, status=status.HTTP_409_CONFLICT)

        for materia in materias:
            _registrar_seguimiento(
                alumno,
                'inscripcion_regular_pendiente',
                f'Coordinación Académica registró {materia.clave} - {materia.nombre} para {periodo.nombre}. La inscripción está pendiente de validación de Servicios Escolares.',
                'Coordinación Académica',
                notificar=True,
                asunto='Inscripción regular registrada',
            )
        return Response({
            'periodo': periodo.nombre,
            'registradas': InscripcionSerializer(inscripciones, many=True).data,
            'validacion_servicios': 'pendiente',
        }, status=status.HTTP_201_CREATED)


class BoletaInscripcionCoordinacionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def puede_gestionar(user):
        rol = str(getattr(user, 'rol', '')).strip().lower()
        return bool(user.is_staff or rol in {'admin', 'administrador', 'coordinacion', 'coordinador'}) and rol not in {
            'servicios', 'servicios_escolares', 'servicios escolares',
        }

    def get(self, request, pk):
        if not self.puede_gestionar(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        alumno = Aspirante.objects.filter(pk=pk, rol='alumno', is_staff=False).first()
        if not alumno:
            return Response({'detail': 'No se encontró el alumno.'}, status=status.HTTP_404_NOT_FOUND)
        periodo_id = request.query_params.get('periodo')
        try:
            periodo = PeriodoInscripcion.objects.get(pk=periodo_id)
        except (PeriodoInscripcion.DoesNotExist, TypeError, ValueError):
            return Response({'detail': 'Selecciona un periodo válido para descargar la boleta.'}, status=status.HTTP_400_BAD_REQUEST)

        inscripciones = list(
            Inscripcion.objects.filter(aspirante=alumno, periodo_inscripcion=periodo)
            .select_related('materia')
            .order_by('materia__clave')
        )
        if not inscripciones:
            return Response({'detail': 'No hay inscripciones registradas para este periodo.'}, status=status.HTTP_404_NOT_FOUND)
        if any(item.validacion_servicios != 'validada' for item in inscripciones):
            return Response({'detail': 'La boleta estará disponible cuando Servicios Escolares valide todas las materias del periodo.'}, status=status.HTTP_409_CONFLICT)

        folio = f'INS-{periodo.apertura.year}-{alumno.pk:06d}-{periodo.pk:04d}'
        buffer = BytesIO()
        document = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=.65 * inch, leftMargin=.65 * inch, topMargin=.65 * inch, bottomMargin=.65 * inch)
        styles = getSampleStyleSheet()
        title = ParagraphStyle('BoletaCoordTitle', parent=styles['Title'], alignment=1, textColor=colors.HexColor('#00695c'), fontSize=14)
        cell = lambda value: Paragraph(escape(str(value or '—')), ParagraphStyle('BoletaCoordCell', parent=styles['Normal'], fontSize=8, leading=10, wordWrap='CJK'))
        story = [
            Paragraph('CENTRO DE INVESTIGACIÓN Y DE ESTUDIOS AVANZADOS', title),
            Paragraph('BOLETA DE INSCRIPCIÓN REGULAR', ParagraphStyle('BoletaCoordSubtitle', parent=styles['Heading2'], alignment=1, textColor=colors.HexColor('#00695c'))),
            Spacer(1, 12),
            Paragraph(
                f'<b>Folio:</b> {escape(folio)}<br/><b>Alumno:</b> {escape(alumno.nombre or "—")}<br/>'
                f'<b>Matrícula:</b> {escape(alumno.matricula or alumno.usuario or "—")}<br/>'
                f'<b>Programa:</b> {escape(alumno.programa or "—")}<br/>'
                f'<b>Periodo escolar:</b> {escape(periodo.nombre)}',
                styles['BodyText'],
            ),
            Spacer(1, 18),
        ]
        rows = [[cell('Clave'), cell('Materia'), cell('Horario'), cell('Validación')]]
        rows.extend([
            [cell(item.materia.clave), cell(item.materia.nombre), cell(item.horario or item.materia.horario), cell(item.get_validacion_servicios_display())]
            for item in inscripciones
        ])
        table = Table(rows, colWidths=[1.0 * inch, 3.0 * inch, 1.8 * inch, 1.0 * inch], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00695c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), .4, colors.HexColor('#b8c7d1')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f1f5f9')]),
            ('PADDING', (0, 0), (-1, -1), 7),
        ]))
        story.extend([
            table,
            Spacer(1, 34),
            Table([
                ['________________________________', '________________________________'],
                ['Coordinación Académica', 'Servicios Escolares'],
            ], colWidths=[3.5 * inch, 3.5 * inch]),
        ])
        document.build(story)
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=f'{folio}_boleta_inscripcion_regular.pdf', content_type='application/pdf')


class InscripcionExtemporaneaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def puede_gestionar(user):
        rol = str(getattr(user, 'rol', '')).strip().lower()
        return user.is_staff or rol in {'admin', 'administrador', 'coordinacion', 'coordinador'}

    def get(self, request, pk):
        if not self.puede_gestionar(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        alumno = Aspirante.objects.filter(pk=pk, rol='alumno', is_staff=False).first()
        if not alumno:
            return Response({'detail': 'No se encontró el alumno.'}, status=status.HTTP_404_NOT_FOUND)
        configuracion = ConfiguracionPrograma.objects.filter(programa__iexact=alumno.programa, activo=True).first()
        periodos = PeriodoInscripcion.objects.order_by('-apertura')
        periodo_id = request.query_params.get('periodo')
        materias = []
        if periodo_id and configuracion and alumno.numero_periodo_actual:
            try:
                periodo = periodos.get(pk=periodo_id)
            except (PeriodoInscripcion.DoesNotExist, ValueError):
                return Response({'detail': 'Selecciona un periodo de inscripción válido.'}, status=status.HTTP_400_BAD_REQUEST)
            plan_ids = set(_materias_plan_disponibles(alumno, configuracion).values_list('materia_id', flat=True))
            detalles = CargaAcademicaMateria.objects.filter(
                carga__estado='publicada',
                carga__periodo_inscripcion=periodo,
                materia_id__in=plan_ids,
            ).select_related('materia').order_by('materia__clave')
            inscritos = dict(
                Inscripcion.objects.filter(
                    periodo_inscripcion=periodo,
                    materia_id__in=[detalle.materia_id for detalle in detalles],
                ).values('materia_id').annotate(total=Count('id')).values_list('materia_id', 'total')
            )
            materias = [{
                'id': detalle.materia_id,
                'clave': detalle.materia.clave,
                'nombre': detalle.materia.nombre,
                'creditos': detalle.materia.creditos,
                'horario': detalle.horario,
                'capacidad': detalle.capacidad,
                'inscritos': inscritos.get(detalle.materia_id, 0),
            } for detalle in detalles]
        return Response({
            'alumno': {'id': alumno.id, 'nombre': alumno.nombre, 'matricula': alumno.matricula, 'programa': alumno.programa},
            'periodos': [PeriodoInscripcionView.serializar(periodo) for periodo in periodos],
            'periodo_seleccionado': int(periodo_id) if periodo_id and str(periodo_id).isdigit() else None,
            'materias': materias,
            'solicitudes': [{
                'id': solicitud.id,
                'folio': f'EXT-{solicitud.created_at.year}-{solicitud.id:06d}',
                'periodo': solicitud.periodo_inscripcion.nombre,
                'estado': solicitud.estado,
            } for solicitud in SolicitudInscripcionExtemporanea.objects.filter(alumno=alumno).select_related('periodo_inscripcion').order_by('-created_at')],
            'motivo_requerido': True,
        })

    def post(self, request, pk):
        if not self.puede_gestionar(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        alumno = Aspirante.objects.filter(pk=pk, rol='alumno', is_staff=False).first()
        if not alumno:
            return Response({'detail': 'No se encontró el alumno.'}, status=status.HTTP_404_NOT_FOUND)
        motivo = str(request.data.get('motivo') or '').strip()
        if not motivo:
            return Response({'motivo': 'El motivo de la inscripción extemporánea es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)
        materias_ids = request.data.get('materias')
        if not isinstance(materias_ids, list) or not materias_ids or not all(str(item).isdigit() for item in materias_ids):
            return Response({'materias': 'Selecciona una o más materias.'}, status=status.HTTP_400_BAD_REQUEST)
        materias_ids = [int(item) for item in materias_ids]
        if len(set(materias_ids)) != len(materias_ids):
            return Response({'materias': 'No repitas materias en la selección.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            periodo = PeriodoInscripcion.objects.get(pk=request.data.get('periodo_inscripcion'))
        except (PeriodoInscripcion.DoesNotExist, TypeError, ValueError):
            return Response({'periodo_inscripcion': 'Selecciona un periodo de inscripción válido.'}, status=status.HTTP_400_BAD_REQUEST)
        configuracion = ConfiguracionPrograma.objects.filter(programa__iexact=alumno.programa, activo=True).first()
        if not configuracion:
            return Response({'detail': 'El programa del alumno no tiene un plan de estudios activo.'}, status=status.HTTP_409_CONFLICT)
        if not alumno.numero_periodo_actual:
            return Response({'detail': 'Asigna primero el semestre o cuatrimestre actual del alumno.'}, status=status.HTTP_409_CONFLICT)

        with transaction.atomic():
            existentes = Inscripcion.objects.filter(aspirante=alumno, periodo_inscripcion=periodo)
            if existentes.filter(materia_id__in=materias_ids).exists():
                return Response({'detail': 'El alumno ya tiene una de esas materias inscrita en este periodo.'}, status=status.HTTP_400_BAD_REQUEST)
            plan_ids = set(_materias_plan_disponibles(alumno, configuracion).filter(
                materia_id__in=materias_ids,
            ).values_list('materia_id', flat=True))
            if plan_ids != set(materias_ids):
                return Response({'detail': 'Solo puedes inscribir materias del plan correspondiente al periodo académico actual.'}, status=status.HTTP_400_BAD_REQUEST)
            detalles = list(
                CargaAcademicaMateria.objects.select_for_update()
                .filter(carga__estado='publicada', carga__periodo_inscripcion=periodo, materia_id__in=materias_ids)
                .select_related('materia')
                .order_by('materia__clave')
            )
            detalles_por_materia = {detalle.materia_id: detalle for detalle in detalles}
            if set(detalles_por_materia) != set(materias_ids):
                return Response({'materias': 'Una o más materias no pertenecen a una carga publicada para ese periodo.'}, status=status.HTTP_400_BAD_REQUEST)
            llenas = [
                detalle.materia
                for detalle in detalles
                if Inscripcion.objects.filter(materia_id=detalle.materia_id, periodo_inscripcion=periodo).count() >= detalle.capacidad
            ]
            if llenas:
                return Response({'detail': f'No hay cupo en: {", ".join(materia.clave for materia in llenas)}.'}, status=status.HTTP_409_CONFLICT)
            if SolicitudInscripcionExtemporanea.objects.filter(
                alumno=alumno, periodo_inscripcion=periodo, estado='pendiente',
            ).exists():
                return Response(
                    {'detail': 'El alumno ya tiene una solicitud extemporánea pendiente para este periodo.'},
                    status=status.HTTP_409_CONFLICT,
                )
            solicitud = SolicitudInscripcionExtemporanea.objects.create(
                alumno=alumno,
                periodo_inscripcion=periodo,
                solicitante=request.user,
                motivo=motivo,
            )
            SolicitudInscripcionExtemporaneaMateria.objects.bulk_create([
                SolicitudInscripcionExtemporaneaMateria(solicitud=solicitud, carga_materia=detalle)
                for detalle in detalles
            ])
        _registrar_seguimiento(
            alumno,
            'inscripcion_extemporanea_pendiente',
            f'La solicitud de inscripción extemporánea para {periodo.nombre} fue enviada a Servicios Escolares para revisión.',
            'Coordinación Académica',
            notificar=True,
            asunto='Solicitud de inscripción extemporánea recibida',
        )
        return Response({
            'id': solicitud.id,
            'estado': solicitud.estado,
            'alumno': {'id': alumno.id, 'nombre': alumno.nombre},
            'periodo': periodo.nombre,
            'motivo': solicitud.motivo,
            'materias': [{'id': detalle.materia_id, 'clave': detalle.materia.clave, 'nombre': detalle.materia.nombre} for detalle in detalles],
            'created_at': solicitud.created_at,
        }, status=status.HTTP_201_CREATED)
