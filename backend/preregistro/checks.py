from django.conf import settings
from django.core.checks import Warning, register

CONSOLA = 'django.core.mail.backends.console.EmailBackend'


@register()
def correo_configurado(app_configs, **kwargs):
    avisos = []
    if not settings.EMAIL_HOST or settings.EMAIL_BACKEND == CONSOLA:
        avisos.append(Warning(
            'No hay servidor SMTP configurado: las notificaciones y la recuperación de contraseña no llegarán a los usuarios.',
            hint='Define EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD y DEFAULT_FROM_EMAIL en .env.',
            id='sinac.W001',
        ))
    if settings.EMAIL_USE_TLS and settings.EMAIL_USE_SSL:
        avisos.append(Warning(
            'EMAIL_USE_TLS y EMAIL_USE_SSL están activos a la vez; el envío fallará.',
            hint='Usa TLS con el puerto 587 o SSL con el puerto 465.',
            id='sinac.W002',
        ))
    return avisos
