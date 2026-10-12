"""Consulta del histórico de alumnos, docentes y directores de tesis."""
from datetime import date

from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .expediente_central_views import _es_gestion
from .models import HistorialPersona

LIMITE = 300


class HistoricoPersonasView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not (request.user.is_superuser or _es_gestion(request.user)):
            return Response({'detail': 'No tienes permisos para consultar el histórico.'}, status=status.HTTP_403_FORBIDDEN)
        params = request.query_params
        eventos = HistorialPersona.objects.select_related('persona')
        rol = params.get('rol', '').strip()
        q = params.get('q', '').strip()
        persona = params.get('persona', '').strip()
        if rol:
            eventos = eventos.filter(rol=rol)
        if persona.isdigit():
            eventos = eventos.filter(persona_id=int(persona))
        if q:
            eventos = eventos.filter(Q(persona__nombre__icontains=q) | Q(persona__matricula__icontains=q) | Q(persona__usuario__icontains=q))
        for nombre, lookup in (('desde', 'created_at__date__gte'), ('hasta', 'created_at__date__lte')):
            valor = params.get(nombre, '').strip()
            if valor:
                try:
                    eventos = eventos.filter(**{lookup: date.fromisoformat(valor)})
                except ValueError:
                    return Response({'detail': 'Fecha no válida.'}, status=status.HTTP_400_BAD_REQUEST)
        total = eventos.count()
        return Response({
            'total': total,
            'truncado': total > LIMITE,
            'eventos': [{
                'id': e.id,
                'persona_id': e.persona_id,
                'nombre': e.persona.nombre,
                'matricula': e.persona.matricula,
                'profile_photo': e.persona.profile_photo.url if e.persona.profile_photo else None,
                'rol': e.rol,
                'evento': e.evento,
                'campo': e.campo,
                'valor_anterior': e.valor_anterior,
                'valor_nuevo': e.valor_nuevo,
                'realizado_por': e.realizado_por_nombre,
                'fecha': e.created_at.isoformat(),
            } for e in eventos[:LIMITE]],
        })
