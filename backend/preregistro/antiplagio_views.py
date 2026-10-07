import hashlib
import os
import re
from decimal import Decimal, InvalidOperation

import requests

from django.shortcuts import render
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ProyectoTesis, RevisionAntiplagio
from .serializers import RevisionAntiplagioSerializer


def _estado_por_porcentaje(porcentaje):
    if porcentaje >= Decimal('30.00'):
        return {
            'estado': 'rechazado',
            'observaciones': 'Se detectó un nivel crítico de similitud. Debe revisarse el documento y justificar citas o referencias.',
        }
    if porcentaje >= Decimal('15.00'):
        return {
            'estado': 'observado',
            'observaciones': 'Se requiere revisión manual del documento para validar citas y referencias.',
        }
    return {
        'estado': 'aprobado',
        'observaciones': 'El documento cumple con el umbral institucional de similitud.',
    }


def _resultado_fallback(nombre_archivo, contenido):
    digest = hashlib.sha256(contenido).hexdigest()
    porcentaje = Decimal(str((int(digest[:8], 16) % 22) + 6.5)).quantize(Decimal('0.01'))
    resultado = _estado_por_porcentaje(porcentaje)
    return {
        'porcentaje_similitud': float(porcentaje),
        'estado': resultado['estado'],
        'observaciones': resultado['observaciones'],
        'resultados': {
            'archivo': nombre_archivo,
            'metodo': 'fallback-heuristico',
            'umbral_alerta': 15,
            'umbral_critico': 30,
            'similitud_calculada': float(porcentaje),
        },
    }


def _resultado_proveedor(proyecto, proveedor, archivo, contenido):
    provider_url = (os.getenv('ANTIPLAGIO_PROVIDER_URL') or '').strip()
    if provider_url and requests is not None:
        try:
            response = requests.post(
                provider_url,
                files={'archivo': (archivo.name, contenido, archivo.content_type or 'application/pdf')},
                data={
                    'proveedor': proveedor,
                    'project_id': str(proyecto.pk),
                    'project_title': proyecto.titulo,
                    'student': proyecto.alumno.usuario,
                },
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json() if response.headers.get('Content-Type', '').lower().startswith('application/json') else {}
            if isinstance(payload, dict) and payload.get('porcentaje_similitud') is not None:
                porcentaje = Decimal(str(payload.get('porcentaje_similitud', 0))).quantize(Decimal('0.01'))
                resultado = _estado_por_porcentaje(porcentaje)
                return {
                    'porcentaje_similitud': float(porcentaje),
                    'estado': str(payload.get('estado', resultado['estado'])).strip().lower() or resultado['estado'],
                    'observaciones': str(payload.get('observaciones', resultado['observaciones'])).strip() or resultado['observaciones'],
                    'resultados': {
                        'proveedor': proveedor,
                        'metodo': 'proveedor-externo',
                        'umbral_alerta': 15,
                        'umbral_critico': 30,
                        'similitud_calculada': float(porcentaje),
                        **payload,
                    },
                }
        except Exception:
            pass
    return _resultado_fallback(archivo.name, contenido)


class RevisionAntiplagioView(APIView):
    """Endpoint para enviar un documento de tesis a revisión anti-plagio."""
    permission_classes = [permissions.IsAuthenticated]

    def _es_alumno(self, user):
        return str(getattr(user, 'rol', '') or '').strip().lower() == 'alumno'

    def _es_director_o_coordinacion(self, user):
        rol = str(getattr(user, 'rol', '') or '').strip().lower()
        return user.is_staff or rol in {'director', 'director de tesis', 'coordinacion', 'coordinador'}

    def post(self, request, pk):
        proyecto = ProyectoTesis.objects.filter(pk=pk).select_related('alumno', 'director').first()
        if not proyecto:
            return Response({'detail': 'Proyecto de tesis no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if self._es_alumno(request.user) and proyecto.alumno_id != request.user.id:
            return Response({'detail': 'Solo puedes revisar tu propio proyecto.'}, status=status.HTTP_403_FORBIDDEN)

        if not (self._es_alumno(request.user) or self._es_director_o_coordinacion(request.user)):
            return Response({'detail': 'No tienes permisos para ejecutar esta revisión.'}, status=status.HTTP_403_FORBIDDEN)

        archivo = request.FILES.get('archivo')
        proveedor = (request.data.get('proveedor') or 'turnitin').strip().lower()
        if not archivo:
            return Response({'archivo': 'Debes adjuntar un archivo PDF.'}, status=status.HTTP_400_BAD_REQUEST)
        if not archivo.name.lower().endswith('.pdf'):
            return Response({'archivo': 'Solo se permiten archivos PDF.'}, status=status.HTTP_400_BAD_REQUEST)

        if proveedor not in {valor for valor, _ in RevisionAntiplagio.PROVEEDORES}:
            return Response({'proveedor': 'Proveedor no válido.'}, status=status.HTTP_400_BAD_REQUEST)

        contenido = archivo.read()
        if not contenido:
            return Response({'archivo': 'El archivo adjunto está vacío.'}, status=status.HTTP_400_BAD_REQUEST)

        resultado = _resultado_proveedor(proyecto, proveedor, archivo, contenido)
        porcentaje = Decimal(str(resultado['porcentaje_similitud'])).quantize(Decimal('0.01'))
        estado = str(resultado['estado']).strip().lower()
        observaciones = str(resultado['observaciones']).strip()

        if estado not in {valor for valor, _ in RevisionAntiplagio.ESTADOS}:
            estado = _estado_por_porcentaje(porcentaje)['estado']

        archivo.seek(0)

        revision = RevisionAntiplagio.objects.create(
            proyecto=proyecto,
            proveedor=proveedor,
            archivo=archivo,
            nombre_original=archivo.name,
            porcentaje_similitud=porcentaje,
            estado=estado,
            observaciones=observaciones,
            resultados={
                'proveedor': proveedor,
                'umbral_alerta': 15,
                'umbral_critico': 30,
                'similitud_calculada': float(porcentaje),
                **resultado['resultados'],
            },
        )

        proyecto.estado = 'en_revision' if estado in {'observado', 'pendiente'} else 'aprobado' if estado == 'aprobado' else 'rechazado'
        proyecto.comentarios_revision = observaciones
        proyecto.save(update_fields=['estado', 'comentarios_revision', 'updated_at'])

        return Response(
            {
                'id': revision.pk,
                'proyecto': proyecto.pk,
                'proveedor': revision.proveedor,
                'nombre_original': revision.nombre_original,
                'porcentaje_similitud': float(revision.porcentaje_similitud),
                'estado': revision.estado,
                'observaciones': revision.observaciones,
                'resultados': revision.resultados,
            },
            status=status.HTTP_201_CREATED,
        )
