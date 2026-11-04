"""Consulta del histórico de alumnos, docentes y directores de tesis."""
from datetime import date

from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .expediente_central_views import _es_gestion
from .historial import ROLES_HISTORIAL
from .models import Aspirante, HistorialPersona
from .paginacion import paginar
from .seguridad import url_media

LIMITE = 300
LIMITE_PERSONA = 1000
MESES_ACTIVIDAD = 12
CATEGORIAS = [clave for clave, _ in HistorialPersona.CATEGORIAS]
EVENTOS = ['alta', 'cambio', 'baja']


def _sin_permiso(usuario):
    if usuario.is_superuser or _es_gestion(usuario):
        return None
    return Response({'detail': 'No tienes permisos para consultar el histórico.'}, status=status.HTTP_403_FORBIDDEN)


def _evento(e, con_persona=True):
    datos = {
        'id': e.id,
        'categoria': e.categoria,
        'evento': e.evento,
        'campo': e.campo,
        'detalle': e.detalle,
        'valor_anterior': e.valor_anterior,
        'valor_nuevo': e.valor_nuevo,
        'realizado_por': e.realizado_por_nombre,
        'fecha': e.created_at.isoformat(),
        'rol': e.rol,
    }
    if con_persona:
        datos.update({
            'persona_id': e.persona_id,
            'nombre': e.persona.nombre,
            'matricula': e.persona.matricula,
            'programa': e.persona.programa,
            'profile_photo': url_media(e.persona.profile_photo),
        })
    return datos


def _meses(hasta, cantidad):
    anio, mes = hasta.year, hasta.month
    meses = []
    for _ in range(cantidad):
        meses.append(date(anio, mes, 1))
        anio, mes = (anio - 1, 12) if mes == 1 else (anio, mes - 1)
    return list(reversed(meses))


def _resumen(eventos, hasta):
    por_categoria = dict(eventos.values_list('categoria').annotate(n=Count('id')))
    por_evento = dict(eventos.values_list('evento').annotate(n=Count('id')))
    meses = _meses(hasta, MESES_ACTIVIDAD)
    conteo_mes = {
        fila['mes'].date() if hasattr(fila['mes'], 'date') else fila['mes']: fila['n']
        for fila in eventos.filter(created_at__date__gte=meses[0])
        .annotate(mes=TruncMonth('created_at')).values('mes').annotate(n=Count('id'))
    }
    return {
        'personas': eventos.values('persona_id').distinct().count(),
        'por_categoria': {c: por_categoria.get(c, 0) for c in CATEGORIAS},
        'por_evento': {e: por_evento.get(e, 0) for e in EVENTOS},
        'actividad': [{'mes': m.isoformat(), 'total': conteo_mes.get(m, 0)} for m in meses],
    }


class HistoricoPersonasView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        denegado = _sin_permiso(request.user)
        if denegado:
            return denegado
        params = request.query_params
        eventos = HistorialPersona.objects.select_related('persona')
        texto = {nombre: params.get(nombre, '').strip() for nombre in ('rol', 'q', 'persona', 'categoria', 'evento', 'programa', 'responsable')}
        if texto['rol']:
            eventos = eventos.filter(rol=texto['rol'])
        if texto['persona'].isdigit():
            eventos = eventos.filter(persona_id=int(texto['persona']))
        if texto['categoria'] in CATEGORIAS:
            eventos = eventos.filter(categoria=texto['categoria'])
        if texto['evento'] in EVENTOS:
            eventos = eventos.filter(evento=texto['evento'])
        if texto['programa']:
            eventos = eventos.filter(persona__programa=texto['programa'])
        if texto['responsable']:
            eventos = eventos.filter(realizado_por_nombre=texto['responsable'])
        if texto['q']:
            q = texto['q']
            eventos = eventos.filter(
                Q(persona__nombre__icontains=q) | Q(persona__matricula__icontains=q)
                | Q(persona__usuario__icontains=q) | Q(detalle__icontains=q)
            )
        fechas = {}
        for nombre, lookup in (('desde', 'created_at__date__gte'), ('hasta', 'created_at__date__lte')):
            valor = params.get(nombre, '').strip()
            if valor:
                try:
                    fechas[nombre] = date.fromisoformat(valor)
                except ValueError:
                    return Response({'detail': 'Fecha no válida.'}, status=status.HTTP_400_BAD_REQUEST)
                eventos = eventos.filter(**{lookup: fechas[nombre]})
        total = eventos.count()
        resumen = _resumen(eventos, fechas.get('hasta') or timezone.localdate())
        pagina, paginacion = paginar(request, eventos)
        return Response({
            'total': total,
            'truncado': not paginacion and total > LIMITE,
            'paginacion': paginacion,
            'resumen': resumen,
            'opciones': {
                'programas': sorted(
                    Aspirante.objects.filter(rol__in=ROLES_HISTORIAL).exclude(programa='')
                    .values_list('programa', flat=True).distinct()
                ),
                'responsables': sorted(
                    HistorialPersona.objects.exclude(realizado_por_nombre='')
                    .values_list('realizado_por_nombre', flat=True).distinct()
                ),
            },
            'eventos': [_evento(e) for e in (pagina if paginacion else eventos[:LIMITE])],
        })


class HistoricoPersonaDetalleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        denegado = _sin_permiso(request.user)
        if denegado:
            return denegado
        persona = get_object_or_404(Aspirante.objects.select_related('director_tesis'), pk=pk)
        eventos = HistorialPersona.objects.filter(persona=persona)
        total = eventos.count()
        por_categoria = dict(eventos.values_list('categoria').annotate(n=Count('id')))
        primero = eventos.order_by('created_at').values_list('created_at', flat=True).first()
        return Response({
            'persona': {
                'id': persona.id,
                'nombre': persona.nombre,
                'matricula': persona.matricula,
                'usuario': persona.usuario,
                'correo': persona.correo,
                'rol': persona.rol,
                'programa': persona.programa,
                'departamento': persona.departamento,
                'estado': persona.proceso_estado,
                'activo': persona.is_active,
                'periodo_actual': persona.numero_periodo_actual,
                'director_tesis': persona.director_tesis.nombre if persona.director_tesis else '',
                'profile_photo': url_media(persona.profile_photo),
                'alta': persona.created_at.isoformat(),
                'primer_movimiento': primero.isoformat() if primero else None,
            },
            'total': total,
            'truncado': total > LIMITE_PERSONA,
            'por_categoria': {c: por_categoria.get(c, 0) for c in CATEGORIAS},
            'eventos': [_evento(e, con_persona=False) for e in eventos[:LIMITE_PERSONA]],
        })
