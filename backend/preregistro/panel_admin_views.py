"""Panel de administración de aspirantes."""
import logging
import uuid
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Aspirante
from .admin_views import AdminRolePermission
from .configuracion_sistema import password_meets_policy
from .sesiones import revocar_sesiones
from .serializers import (
    AspiranteAdminSerializer,
)


logger = logging.getLogger(__name__)


class PanelAdministradorView(APIView):
    permission_classes = [AdminRolePermission]

    @staticmethod
    def _normalizar_rol(valor):
        if valor is None:
            return 'aspirante'

        rol = str(valor).strip().lower()
        aliases = {
            'admin': 'admin',
            'administrador': 'admin',
            'coordinacion': 'coordinacion',
            'coordinación': 'coordinacion',
            'coordinador': 'coordinacion',
            'docente': 'docente',
            'teacher': 'docente',
            'alumno': 'alumno',
            'student': 'alumno',
            'aspirante': 'aspirante',
            'candidate': 'aspirante',
            'director': 'director',
            'director de tesis': 'director',
            'servicios': 'servicios',
            'servicios escolares': 'servicios',
        }
        return aliases.get(rol, 'aspirante')

    @staticmethod
    def _normalizar_estado(valor):
        if valor is None:
            return None
        estado = str(valor).strip().lower()
        if estado in ['activo', 'active', 'enabled', 'true']:
            return True
        if estado in ['inactivo', 'inactive', 'disabled', 'false']:
            return False
        if estado in ['pendiente', 'pending']:
            return True
        return None

    def get(self, request):
        personas = Aspirante.objects.filter(is_staff=False).order_by('-created_at')
        solicitudes = personas.filter(rol='aspirante')
        return Response({
            'resumen': {
                'total': solicitudes.count(),
                'pendiente': solicitudes.filter(proceso_estado='pendiente').count(),
                'iniciado': solicitudes.filter(proceso_estado='iniciado').count(),
                'revision': solicitudes.filter(proceso_estado='revision').count(),
                'aceptado': solicitudes.filter(proceso_estado='aceptado').count(),
            },
            'aspirantes': AspiranteAdminSerializer(personas, many=True).data,
        })

    def post(self, request):
        """Create a new aspirante (admin only)"""
        nombre = (request.data.get('name') or '').strip()
        correo = (request.data.get('email') or '').strip().lower()
        usuario = (request.data.get('usuario') or nombre.replace(' ', '').lower()[:20]).strip()
        rol = self._normalizar_rol(request.data.get('role'))
        programa = (request.data.get('area') or 'General').strip()
        password = (request.data.get('password') or '').strip()

        if not nombre or not correo:
            return Response(
                {'error': 'Nombre y correo son obligatorios.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not usuario:
            return Response({'error': 'El nombre de usuario es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(usuario) < 3:
            return Response({'error': 'El nombre de usuario debe tener al menos 3 caracteres.'}, status=status.HTTP_400_BAD_REQUEST)

        if not password:
            return Response(
                {'error': 'La contraseña es obligatoria.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not password_meets_policy(password):
            return Response(
                {'error': 'La contraseña no cumple la política configurada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Aspirante.objects.filter(correo__iexact=correo).exists():
            return Response(
                {'error': 'Ya existe un aspirante con este correo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Aspirante.objects.filter(usuario__iexact=usuario).exists():
            return Response(
                {'error': 'Ya existe un aspirante con este usuario.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            aspirante = Aspirante.objects.create_user(
                usuario=usuario,
                correo=correo,
                nombre=nombre,
                password=password,
                # CURP provisional única; el usuario podrá sustituirla por la oficial.
                curp=f'TEMP{uuid.uuid4().hex[:14].upper()}',
                rol=rol if rol in ('aspirante', 'alumno', 'docente', 'director', 'servicios') else 'aspirante',
                is_staff=rol in ('admin', 'coordinacion'),
                programa=programa,
                unidad='Administración',
                departamento='SINAC',
                seccion='General',
                estado_actual='Ciudad de México',
                municipio_actual='Gustavo A. Madero',
                direccion_actual='Cinvestav',
                estado_permanente='Ciudad de México',
                municipio_permanente='Gustavo A. Madero',
                direccion_permanente='Cinvestav',
                nombre_familiar='No aplica',
                parentesco='No aplica',
                telefono='0000000000',
                telefono_familiar='0000000000',
                ultimo_grado='No aplica',
                institucion='Cinvestav',
                business_key=f'ADMIN-{uuid.uuid4().hex.upper()}',
            )
            return Response(AspiranteAdminSerializer(aspirante).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': f'Error al crear aspirante: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def put(self, request, pk=None):
        """Update an aspirante (admin only)"""
        if not pk and request.data.get('id'):
            pk = request.data['id']

        if not pk:
            return Response(
                {'error': 'Se requiere un ID de usuario.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            aspirante = Aspirante.objects.get(pk=pk, is_staff=False)
        except Aspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if aspirante.rol != 'aspirante':
            return Response({'detail': 'Este flujo solo aplica a aspirantes.'}, status=status.HTTP_400_BAD_REQUEST)

        if 'name' in request.data:
            nombre = str(request.data['name']).strip()
            if nombre:
                aspirante.nombre = nombre
        if 'email' in request.data:
            email = str(request.data['email']).strip().lower()
            if email:
                if Aspirante.objects.exclude(pk=pk).filter(correo__iexact=email).exists():
                    return Response(
                        {'error': 'Ya existe un aspirante con este correo.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                aspirante.correo = email
        if 'role' in request.data:
            aspirante.rol = self._normalizar_rol(request.data['role'])
        if 'area' in request.data:
            area = str(request.data['area']).strip()
            if area:
                aspirante.programa = area
        if 'password' in request.data:
            password = str(request.data['password']).strip()
            if password:
                if not password_meets_policy(password):
                    return Response(
                        {'error': 'La contraseña no cumple la política configurada.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                aspirante.set_password(password)
                aspirante.login_failed_attempts = 0
                aspirante.login_locked_until = None
        if 'status' in request.data:
            status_value = self._normalizar_estado(request.data['status'])
            if status_value is not None:
                aspirante.is_active = status_value

        aspirante.save()
        if str(request.data.get('password') or '').strip() or not aspirante.is_active:
            revocar_sesiones(aspirante)
        return Response(AspiranteAdminSerializer(aspirante).data)

    def delete(self, request, pk=None):
        """Delete an aspirante (admin only)"""
        if not pk and request.data.get('id'):
            pk = request.data['id']

        if not pk:
            return Response(
                {'error': 'Se requiere un ID de usuario.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            aspirante = Aspirante.objects.get(pk=pk, is_staff=False)
        except Aspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        aspirante.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
