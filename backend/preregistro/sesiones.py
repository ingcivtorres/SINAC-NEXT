"""Cierre de sesión, revocación de tokens JWT y recuperación de contraseña."""
import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from .configuracion_sistema import get_setting, password_meets_policy
from .models import Aspirante

logger = logging.getLogger(__name__)

MENSAJE_RECUPERACION = (
    'Si la cuenta existe y tiene un correo registrado, recibirás un enlace para restablecer tu contraseña.'
)


def revocar_sesiones(user):
    """Invalida todos los tokens de renovación emitidos para el usuario."""
    for token in OutstandingToken.objects.filter(user=user).exclude(blacklistedtoken__isnull=False):
        BlacklistedToken.objects.get_or_create(token=token)


class CerrarSesionView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle]
    throttle_scope = 'refresh'

    def post(self, request):
        try:
            RefreshToken(request.data.get('refresh') or '').blacklist()
        except TokenError:
            pass
        return Response(status=status.HTTP_205_RESET_CONTENT)


class SolicitarRecuperacionView(APIView):
    """Envía un enlace de restablecimiento; responde igual exista o no la cuenta."""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle]
    throttle_scope = 'recuperacion'

    def post(self, request):
        from .serializers import InicioSesionSerializer

        identificador = str(request.data.get('usuario') or request.data.get('correo') or '').strip()[:254]
        user = InicioSesionSerializer.get_user_by_identifier(identificador) if identificador else None
        if user is not None and user.is_active and user.correo:
            self._enviar(user)
        return Response({'detail': MENSAJE_RECUPERACION})

    @staticmethod
    def _enviar(user):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        enlace = f'{settings.SINAC_URL_PUBLICA}/restablecer?uid={uid}&token={token}'
        minutos = settings.PASSWORD_RESET_TIMEOUT // 60
        mensaje = (
            f'Hola {user.nombre or user.usuario}:\n\n'
            f'Recibimos una solicitud para restablecer la contraseña de tu cuenta en {get_setting("nombre_sistema")}.\n'
            f'Abre el siguiente enlace (válido durante {minutos} minutos y un solo uso):\n\n{enlace}\n\n'
            'Si no solicitaste el cambio, ignora este mensaje; tu contraseña actual seguirá vigente.'
        )
        try:
            send_mail('Restablecimiento de contraseña', mensaje, settings.DEFAULT_FROM_EMAIL, [user.correo])
        except Exception:
            logger.exception('No se pudo enviar el correo de recuperación a la cuenta %s.', user.pk)


class RestablecerContrasenaView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        password = str(request.data.get('password') or '')
        try:
            pk = force_str(urlsafe_base64_decode(str(request.data.get('uid') or '')))
            user = Aspirante.objects.get(pk=pk, is_active=True)
        except (TypeError, ValueError, OverflowError, Aspirante.DoesNotExist):
            user = None
        if user is None or not default_token_generator.check_token(user, str(request.data.get('token') or '')):
            return Response(
                {'detail': 'El enlace de recuperación no es válido o ya expiró. Solicita uno nuevo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(password) > 128 or not password_meets_policy(password):
            return Response(
                {'detail': f'La contraseña no cumple la política vigente: {get_setting("politica_password")}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(password)
        user.login_failed_attempts = 0
        user.login_locked_until = None
        user.save(update_fields=['password', 'login_failed_attempts', 'login_locked_until', 'updated_at'])
        revocar_sesiones(user)
        return Response({'detail': 'Tu contraseña se actualizó. Ya puedes iniciar sesión.'})
