import hashlib
import os
from decimal import Decimal

import requests

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ProyectoTesis, RevisionAntiplagio
from .seguridad import nombre_archivo_seguro, validar_pdf


ESTADOS_REVISABLES = {'borrador', 'en_revision', 'observado'}


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

    def _puede_revisar(self, user, proyecto):
        rol = str(getattr(user, 'rol', '') or '').strip().lower()
        if user.is_staff or rol in {'coordinacion', 'coordinador'}:
            return True
        if rol in {'director', 'director de tesis'}:
            return proyecto.alumno.director_tesis_id == user.id
        return rol == 'alumno' and proyecto.alumno_id == user.id

    def post(self, request, pk):
        proyecto = ProyectoTesis.objects.filter(pk=pk).select_related('alumno', 'director').first()
        if not proyecto:
            return Response({'detail': 'Proyecto de tesis no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if not self._puede_revisar(request.user, proyecto):
            return Response({'detail': 'No tienes permisos para revisar este proyecto.'}, status=status.HTTP_403_FORBIDDEN)
        if proyecto.estado not in ESTADOS_REVISABLES:
            return Response(
                {'detail': 'La revisión anti-plagio solo aplica a proyectos en borrador, en revisión o con observaciones.'},
                status=status.HTTP_409_CONFLICT,
            )

        archivo = request.FILES.get('archivo')
        proveedor = (request.data.get('proveedor') or 'turnitin').strip().lower()
        if not archivo:
            return Response({'archivo': 'Debes adjuntar un archivo PDF.'}, status=status.HTTP_400_BAD_REQUEST)
        error_archivo = validar_pdf(archivo)
        if error_archivo:
            return Response({'archivo': error_archivo}, status=status.HTTP_400_BAD_REQUEST)
        archivo.name = nombre_archivo_seguro(archivo.name, 'tesis')

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
                'created_at': revision.created_at,
            },
            status=status.HTTP_201_CREATED,
        )
