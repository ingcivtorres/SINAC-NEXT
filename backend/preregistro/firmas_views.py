"""Firma electrónica de expedientes."""
import logging
import hashlib
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ExpedienteDigital, FirmaElectronica
from .roles import es_gestion_academica
from .serializers import (
    FirmaElectronicaSerializer,
)


logger = logging.getLogger(__name__)


def _puede_consultar_expediente(user, expediente):
    rol = str(getattr(user, 'rol', '') or '').strip().lower()
    return (
        es_gestion_academica(user)
        or rol in ('servicios', 'servicios_escolares', 'servicios escolares')
        or expediente.aspirante_id == user.id
        or (rol in ('director', 'director de tesis') and expediente.aspirante.director_tesis_id == user.id)
    )


class FirmaElectronicaView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, pk):
        rol_usuario = str(getattr(request.user, 'rol', '')).strip().lower()
        es_gestion = es_gestion_academica(request.user)
        if rol_usuario not in ('director', 'director de tesis') and not es_gestion:
            return Response({'detail': 'Solo el tutor o director puede firmar.'}, status=status.HTTP_403_FORBIDDEN)
        expediente = ExpedienteDigital.objects.select_related('aspirante').filter(pk=pk).first()
        if not expediente: return Response(status=status.HTTP_404_NOT_FOUND)
        if not es_gestion:
            if expediente.aspirante.director_tesis_id != request.user.id:
                return Response({'detail': 'Este expediente no pertenece a uno de tus tesistas.'}, status=status.HTTP_403_FORBIDDEN)
            if request.data.get('rol_firmante', 'director') != 'director':
                return Response({'detail': 'Un director solo puede firmar con el rol director.'}, status=status.HTTP_400_BAD_REQUEST)
        rol = 'director' if not es_gestion else request.data.get('rol_firmante', 'director')
        if FirmaElectronica.objects.filter(expediente=expediente, firmante=request.user, rol_firmante=rol).exists():
            return Response({'detail': 'El expediente ya fue firmado por este usuario.'}, status=status.HTTP_400_BAD_REQUEST)
        huella = hashlib.sha256(f'{expediente.folio}|{request.user.pk}|{rol}|{timezone.now().isoformat()}'.encode()).hexdigest()
        firma = FirmaElectronica.objects.create(expediente=expediente, firmante=request.user, rol_firmante=rol, huella=huella)
        return Response(FirmaElectronicaSerializer(firma).data, status=status.HTTP_201_CREATED)

    def get(self, request, pk):
        expediente = ExpedienteDigital.objects.select_related('aspirante').filter(pk=pk).first()
        if not expediente: return Response(status=status.HTTP_404_NOT_FOUND)
        if not _puede_consultar_expediente(request.user, expediente):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(FirmaElectronicaSerializer(expediente.firmas.select_related('firmante'), many=True).data)
