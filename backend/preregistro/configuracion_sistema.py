import re

from .models import ConfiguracionSistema


DEFAULTS = {
    'nombre_sistema': 'SINAC NEXT',
    'campus': 'Cinvestav Unidad Zacatenco',
    'correo_soporte': 'unidaddeenlace@cinvestav.mx',
    'zona_horaria': 'America/Mexico_City',
    'politica_password': '8 caracteres, mayúscula, minúscula y número',
    'bloqueo_intentos': '5',
    'notificaciones_activas': 'true',
}
LOCKOUT_DURATION_MINUTES = 15


def parse_password_policy(value):
    length = re.search(r'(\d+)\s*(?:caracter|character)', value, re.IGNORECASE)
    if not length:
        return None

    normalized = value.casefold()
    policy = {
        'min_length': int(length.group(1)),
        'uppercase': 'mayúscula' in normalized or 'mayuscula' in normalized or 'uppercase' in normalized,
        'lowercase': 'minúscula' in normalized or 'minuscula' in normalized or 'lowercase' in normalized,
        'number': 'número' in normalized or 'numero' in normalized or 'number' in normalized,
    }
    if not 8 <= policy['min_length'] <= 128:
        return None
    return policy


def get_setting(key):
    stored = ConfiguracionSistema.objects.filter(clave=key).values_list('valor', flat=True).first()
    return stored if stored is not None else DEFAULTS[key]


def get_password_policy():
    return parse_password_policy(get_setting('politica_password')) or {
        'min_length': 8, 'uppercase': True, 'lowercase': True, 'number': True,
    }


def password_meets_policy(password):
    policy = get_password_policy()
    return (
        len(password) >= policy['min_length']
        and (not policy['uppercase'] or bool(re.search(r'[A-Z]', password)))
        and (not policy['lowercase'] or bool(re.search(r'[a-z]', password)))
        and (not policy['number'] or bool(re.search(r'[0-9]', password)))
    )


def get_login_attempt_limit():
    try:
        return max(1, min(20, int(get_setting('bloqueo_intentos'))))
    except (TypeError, ValueError):
        return int(DEFAULTS['bloqueo_intentos'])


def email_notifications_enabled():
    return get_setting('notificaciones_activas').strip().casefold() in ('true', '1', 'yes', 'si', 'sí', 'on')
