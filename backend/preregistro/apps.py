from django.apps import AppConfig


class PreregistroConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'preregistro'

    def ready(self):
        from . import historial  # noqa: F401
