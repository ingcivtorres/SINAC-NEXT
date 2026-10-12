"""Registro automático del histórico de alumnos, docentes y directores de tesis."""
from contextvars import ContextVar

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Aspirante, HistorialPersona

ROLES_HISTORIAL = {'alumno', 'docente', 'director'}
CAMPOS = {
    'rol': 'Rol',
    'proceso_estado': 'Estado',
    'is_active': 'Cuenta activa',
    'programa': 'Programa',
    'departamento': 'Departamento',
    'unidad': 'Unidad',
    'modalidad': 'Modalidad',
    'matricula': 'Matrícula',
    'numero_periodo_actual': 'Periodo actual',
    'director_tesis_id': 'Director de tesis',
    'nombre': 'Nombre',
    'correo': 'Correo',
}

_actor = ContextVar('historial_actor', default=None)


class HistorialJWTAuthentication(JWTAuthentication):
    """Igual que JWTAuthentication, pero recuerda quién hace la petición."""

    def authenticate(self, request):
        resultado = super().authenticate(request)
        if resultado:
            _actor.set(resultado[0])
        return resultado


def limpiar_actor_middleware(get_response):
    def middleware(request):
        _actor.set(None)
        try:
            return get_response(request)
        finally:
            _actor.set(None)
    return middleware


def _texto(valor):
    return '' if valor is None else str(valor)[:255]


def _director(valor):
    if valor in (None, ''):
        return ''
    persona = Aspirante.objects.filter(pk=valor).only('nombre').first()
    return persona.nombre if persona else str(valor)


def _registrar(persona, evento, campo='', anterior='', nuevo=''):
    actor = _actor.get()
    HistorialPersona.objects.create(
        persona=persona, rol=persona.rol, evento=evento, campo=campo,
        valor_anterior=anterior, valor_nuevo=nuevo,
        realizado_por=actor if actor and actor.pk else None,
        realizado_por_nombre=(actor.nombre if actor and actor.pk else 'Sistema'),
    )


@receiver(pre_save, sender=Aspirante)
def _capturar_estado_previo(sender, instance, **kwargs):
    instance._historial_previo = None
    if instance.pk:
        instance._historial_previo = Aspirante.objects.filter(pk=instance.pk).values(*CAMPOS).first()


@receiver(post_save, sender=Aspirante)
def _registrar_cambios(sender, instance, created, **kwargs):
    if kwargs.get('raw'):
        return
    previo = getattr(instance, '_historial_previo', None)
    if created:
        if instance.rol in ROLES_HISTORIAL:
            _registrar(instance, 'alta', 'rol', '', instance.rol)
        return
    if not previo:
        return
    rol_relevante = instance.rol in ROLES_HISTORIAL or previo['rol'] in ROLES_HISTORIAL
    if not rol_relevante:
        return
    for campo, etiqueta in CAMPOS.items():
        anterior, nuevo = previo[campo], getattr(instance, campo)
        if anterior == nuevo:
            continue
        if campo == 'director_tesis_id':
            anterior, nuevo = _director(anterior), _director(nuevo)
        _registrar(instance, 'cambio', etiqueta, _texto(anterior), _texto(nuevo))
