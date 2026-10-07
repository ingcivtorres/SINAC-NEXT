from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DocumentoAspirante, ExpedienteDigital, Inscripcion, ProyectoTesis, SeguimientoSolicitud, SolicitudAcademica
from .serializers import (
    DocumentoAspiranteSerializer,
    ExpedienteDigitalSerializer,
    FirmaElectronicaSerializer,
    InscripcionSerializer,
    ProyectoTesisSerializer,
    SeguimientoSolicitudSerializer,
    SolicitudAcademicaSerializer,
)


def _rol(user):
    return str(getattr(user, 'rol', '') or '').strip().lower()


def _es_gestion(user):
    return bool(user.is_staff or _rol(user) in {'coordinacion', 'coordinador', 'servicios', 'servicios_escolares', 'servicios escolares'})


def _es_director_del_expediente(user, expediente):
    return _rol(user) in {'director', 'director de tesis'} and (
        expediente.aspirante.director_tesis_id == user.id
        or expediente.aspirante.tutor_propuesto.strip().lower() in {
            str(getattr(user, 'nombre', '')).strip().lower(),
            str(getattr(user, 'usuario', '')).strip().lower(),
        }
    )


class ExpedienteCentralizadoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk=None):
        expediente = ExpedienteDigital.objects.select_related('aspirante').filter(pk=pk).first()
        if not expediente:
            return Response({'detail': 'Expediente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if not (_es_gestion(request.user) or request.user == expediente.aspirante or _es_director_del_expediente(request.user, expediente)):
            return Response({'detail': 'No tienes permisos para consultar este expediente.'}, status=status.HTTP_403_FORBIDDEN)

        alumno = expediente.aspirante
        proyectos = ProyectoTesis.objects.filter(alumno=alumno).select_related('director').prefetch_related('jurados__jurado', 'defensa_tesis')
        return Response({
            'expediente': ExpedienteDigitalSerializer(expediente).data,
            'alumno': {
                'id': alumno.id,
                'nombre': alumno.nombre,
                'matricula': alumno.matricula,
                'correo': alumno.correo,
                'programa': alumno.programa,
                'unidad': alumno.unidad,
                'departamento': alumno.departamento,
                'proceso_estado': alumno.proceso_estado,
            },
            'documentos': DocumentoAspiranteSerializer(DocumentoAspirante.objects.filter(aspirante=alumno).order_by('tipo'), many=True).data,
            'inscripciones': InscripcionSerializer(Inscripcion.objects.filter(aspirante=alumno).select_related('materia').order_by('materia__clave'), many=True).data,
            'solicitudes_academicas': SolicitudAcademicaSerializer(SolicitudAcademica.objects.filter(aspirante=alumno).order_by('-created_at'), many=True).data,
            'seguimiento': SeguimientoSolicitudSerializer(SeguimientoSolicitud.objects.filter(aspirante=alumno).order_by('-created_at')[:30], many=True).data,
            'firmas': FirmaElectronicaSerializer(expediente.firmas.select_related('firmante').all(), many=True).data,
            'tesis': ProyectoTesisSerializer(proyectos, many=True).data,
        })
