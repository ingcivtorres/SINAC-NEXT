"""Directorio de docentes y directores de tesis para Servicios Escolares."""
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .expediente_central_views import _es_gestion
from .models import (
    Aspirante, CargaAcademicaMateria, DocumentoAspirante, EntrevistaVirtual, FirmaElectronica,
    HistorialPersona, JuradoProyecto, Materia, ProyectoTesis, SolicitudDireccionTesis,
)
from .servicios_views import es_servicios

ROLES_DOCENTES = ('docente', 'director', 'investigador')


def _puede_consultar(user):
    return bool(user.is_superuser or _es_gestion(user))


def _puede_gestionar(user):
    return bool(user.is_superuser or es_servicios(user))


def _foto(persona):
    return persona.profile_photo.url if persona.profile_photo else None


def _tesistas_qs(persona):
    return Aspirante.objects.filter(
        Q(director_tesis=persona) | Q(tutor_propuesto__iexact=persona.nombre), rol='alumno', is_staff=False,
    ).distinct()


def _activos_qs(persona):
    return _tesistas_qs(persona).filter(is_active=True, egreso__isnull=True)


def _lineas(persona):
    lineas = {item.strip() for item in (persona.lineas_declaradas or '').replace('\n', ',').split(',') if item.strip()}
    lineas |= set(
        SolicitudDireccionTesis.objects.filter(director_asignado=persona).exclude(linea_investigacion='')
        .values_list('linea_investigacion', flat=True)
    )
    lineas |= set(
        ProyectoTesis.objects.filter(director=persona).exclude(linea_investigacion='')
        .values_list('linea_investigacion', flat=True)
    )
    return sorted(lineas)


def _resumen(persona, activos, graduados, materias):
    return {
        'id': persona.id, 'nombre': persona.nombre, 'usuario': persona.usuario, 'correo': persona.correo,
        'telefono': persona.telefono, 'rol': persona.rol, 'unidad': persona.unidad,
        'departamento': persona.departamento, 'programa': persona.programa,
        'ultimo_grado': persona.ultimo_grado, 'is_active': persona.is_active,
        'profile_photo': _foto(persona), 'lineas_investigacion': _lineas(persona),
        'tesistas_activos': activos, 'tesistas_graduados': graduados, 'total_materias': materias,
    }


def _materias(persona):
    catalogo = list(Materia.objects.filter(profesor__iexact=persona.nombre).values('id', 'clave', 'nombre', 'horario', 'creditos'))
    cargas = CargaAcademicaMateria.objects.filter(docente=persona).select_related('materia', 'carga', 'carga__periodo_inscripcion').order_by('-carga__created_at')
    return catalogo, [{
        'id': item.id, 'clave': item.materia.clave, 'materia': item.materia.nombre,
        'periodo': item.carga.periodo_inscripcion.nombre if item.carga.periodo_inscripcion else item.carga.periodo,
        'estado_carga': item.carga.estado, 'horario': item.horario, 'salon': item.get_salon_display(),
        'modalidad': item.get_modalidad_display(), 'capacidad': item.capacidad,
    } for item in cargas]


def _detalle(persona):
    activos = list(_activos_qs(persona).select_related('egreso'))
    graduados = list(_tesistas_qs(persona).filter(egreso__isnull=False).select_related('egreso'))
    catalogo, cargas = _materias(persona)
    proyectos = {p.alumno_id: p for p in ProyectoTesis.objects.filter(director=persona)}
    documentos = DocumentoAspirante.objects.filter(aspirante=persona).order_by('tipo')
    jurados = JuradoProyecto.objects.filter(jurado=persona).select_related('proyecto', 'proyecto__alumno')
    solicitudes = SolicitudDireccionTesis.objects.filter(Q(director_sugerido=persona) | Q(director_asignado=persona)).select_related('alumno')

    def tesista(alumno):
        proyecto = proyectos.get(alumno.id)
        egreso = getattr(alumno, 'egreso', None)
        return {
            'id': alumno.id, 'nombre': alumno.nombre, 'matricula': alumno.matricula, 'programa': alumno.programa,
            'estado': alumno.proceso_estado, 'proyecto': proyecto.titulo if proyecto else '',
            'estado_proyecto': proyecto.estado if proyecto else '',
            'fecha_egreso': egreso.fecha_egreso.isoformat() if egreso else None,
            'titulo_tesis': egreso.titulo_tesis if egreso else '',
        }

    historial = HistorialPersona.objects.filter(persona=persona)[:100]
    resumen = _resumen(persona, len(activos), len(graduados), len(catalogo))
    resumen.update({
        'curp': persona.curp, 'nacimiento': persona.nacimiento.isoformat() if persona.nacimiento else None,
        'institucion': persona.institucion, 'idiomas': persona.idiomas,
        'sni_nivel': persona.sni_nivel, 'orcid': persona.orcid, 'especialidad': persona.especialidad,
        'lineas_declaradas': persona.lineas_declaradas,
        'puede_editar_perfil': False,
        'publicaciones': persona.publicaciones, 'experiencia': persona.experiencia,
        'estado_actual': persona.estado_actual, 'municipio_actual': persona.municipio_actual,
        'created_at': persona.created_at.isoformat(),
        'tesistas': [tesista(a) for a in activos], 'graduados': [tesista(a) for a in graduados],
        'materias_catalogo': catalogo, 'materias_cargas': cargas,
        'documentos': [{
            'id': d.id, 'tipo': d.tipo, 'tipo_texto': d.get_tipo_display(), 'nombre': d.nombre_original,
            'url': d.archivo.url if d.archivo else None, 'revisado': d.revisado,
            'revisado_en': d.revisado_en.isoformat() if d.revisado_en else None,
        } for d in documentos],
        'comites': {
            'jurados': [{
                'id': j.id, 'proyecto': j.proyecto.titulo, 'alumno': j.proyecto.alumno.nombre,
                'rol': j.get_rol_display(), 'estado': j.estado,
            } for j in jurados],
            'solicitudes': [{
                'id': s.id, 'alumno': s.alumno.nombre, 'estado': s.estado,
                'como': 'asignado' if s.director_asignado_id == persona.id else 'sugerido',
            } for s in solicitudes],
            'entrevistas': EntrevistaVirtual.objects.filter(aspirante=persona).count(),
            'firmas': FirmaElectronica.objects.filter(firmante=persona).count(),
            'solicitudes_pendientes': solicitudes.filter(estado='pendiente').count(),
        },
        'historial': [{
            'id': h.id, 'fecha': h.created_at.isoformat(), 'evento': h.evento, 'campo': h.campo,
            'valor_anterior': h.valor_anterior, 'valor_nuevo': h.valor_nuevo, 'realizado_por': h.realizado_por_nombre,
        } for h in historial],
    })
    return resumen


class ServiciosDocentesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not _puede_consultar(request.user):
            return Response({'detail': 'No tienes permiso para consultar docentes.'}, status=status.HTTP_403_FORBIDDEN)
        qs = Aspirante.objects.filter(rol__in=ROLES_DOCENTES, is_staff=False).order_by('nombre')
        params = request.query_params
        q = (params.get('q') or '').strip()
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(usuario__icontains=q) | Q(correo__icontains=q))
        if params.get('rol') in ROLES_DOCENTES:
            qs = qs.filter(rol=params['rol'])
        estatus = params.get('estatus')
        if estatus in ('activo', 'inactivo'):
            qs = qs.filter(is_active=(estatus == 'activo'))
        for campo in ('departamento', 'programa'):
            if params.get(campo):
                qs = qs.filter(**{f'{campo}__iexact': params[campo].strip()})
        linea = (params.get('linea') or '').strip().lower()
        docentes = []
        for persona in qs:
            resumen = _resumen(persona, _activos_qs(persona).count(), _tesistas_qs(persona).filter(egreso__isnull=False).count(), Materia.objects.filter(profesor__iexact=persona.nombre).count())
            if linea and not any(linea in item.lower() for item in resumen['lineas_investigacion']):
                continue
            docentes.append(resumen)
        base = Aspirante.objects.filter(rol__in=ROLES_DOCENTES, is_staff=False)
        filtros = {
            'departamentos': sorted(set(base.exclude(departamento='').values_list('departamento', flat=True))),
            'programas': sorted(set(base.exclude(programa='').values_list('programa', flat=True))),
        }
        return Response({
            'docentes': docentes, 'total': len(docentes), 'filtros': filtros,
            'puede_gestionar': _puede_gestionar(request.user),
        })


PERFIL_EDITABLE = {
    'telefono': 20, 'ultimo_grado': 80, 'institucion': 180, 'sni_nivel': 30, 'orcid': 40,
    'especialidad': 180, 'lineas_declaradas': 2000, 'idiomas': 2000, 'publicaciones': 5000, 'experiencia': 5000,
}


class ServiciosDocenteDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _persona(self, pk):
        return Aspirante.objects.filter(pk=pk, rol__in=ROLES_DOCENTES, is_staff=False).first()

    def _respuesta(self, request, persona):
        data = _detalle(persona)
        data['puede_editar_perfil'] = _puede_gestionar(request.user) or request.user.pk == persona.pk
        return Response(data)

    def get(self, request, pk):
        if not (_puede_consultar(request.user) or request.user.pk == int(pk)):
            return Response({'detail': 'No tienes permiso para consultar docentes.'}, status=status.HTTP_403_FORBIDDEN)
        persona = self._persona(pk)
        if not persona:
            return Response({'detail': 'Docente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        return self._respuesta(request, persona)

    @transaction.atomic
    def patch(self, request, pk):
        gestor = _puede_gestionar(request.user)
        if not (gestor or request.user.pk == int(pk)):
            return Response({'detail': 'Solo Servicios Escolares o el propio docente pueden modificar este perfil.'}, status=status.HTTP_403_FORBIDDEN)
        persona = self._persona(pk)
        if not persona:
            return Response({'detail': 'Docente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        data = request.data
        cambios = []
        for campo, maximo in PERFIL_EDITABLE.items():
            if campo in data:
                valor = str(data.get(campo) or '').strip()
                if len(valor) > maximo:
                    return Response({'detail': f'El campo {campo} excede {maximo} caracteres.'}, status=status.HTTP_400_BAD_REQUEST)
                if valor != getattr(persona, campo):
                    setattr(persona, campo, valor)
                    cambios.append(campo)
        if cambios:
            persona.save(update_fields=cambios + ['updated_at'])
        if not gestor:
            return self._respuesta(request, persona)
        if 'documento_id' in data:
            documento = DocumentoAspirante.objects.filter(pk=data.get('documento_id'), aspirante=persona).first()
            if not documento:
                return Response({'detail': 'Documento no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
            documento.revisado = bool(data.get('revisado'))
            documento.revisado_en = timezone.now() if documento.revisado else None
            documento.save(update_fields=['revisado', 'revisado_en', 'updated_at'])
        if 'is_active' in data:
            activo = data.get('is_active') in (True, 'true', 'True', 1, '1')
            if not activo and persona.is_active:
                pendientes = _activos_qs(persona).count()
                if pendientes:
                    return Response(
                        {'detail': f'No se puede desactivar: tiene {pendientes} tesista(s) activo(s). Reasígnalos primero.'},
                        status=status.HTTP_409_CONFLICT,
                    )
            if persona.is_active != activo:
                persona.is_active = activo
                persona.save(update_fields=['is_active', 'updated_at'])
        return self._respuesta(request, persona)
