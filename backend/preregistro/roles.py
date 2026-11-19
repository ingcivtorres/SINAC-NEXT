"""Resolución canónica de roles para login, paneles y permisos API.

``is_staff`` solo habilita el sitio de administración de Django; los permisos
de la aplicación se deciden siempre por el rol efectivo.
"""
import unicodedata

ROLE_ALIASES = {
    'admin': 'admin',
    'administrador': 'admin',
    'coordinacion': 'coordinacion',
    'coordinación': 'coordinacion',
    'coordinador': 'coordinacion',
    'coordinacion academica': 'coordinacion',
    'coordinación académica': 'coordinacion',
    'docente': 'docente',
    'profesor': 'docente',
    'teacher': 'docente',
    'director': 'director',
    'director de tesis': 'director',
    'servicios': 'servicios',
    'servicios escolares': 'servicios',
    'servicios_escolares': 'servicios',
    'investigador': 'investigador',
    'alumno': 'alumno',
    'student': 'alumno',
    'aspirante': 'aspirante',
}

ROLES_GESTION = {'admin', 'coordinacion'}
ROLES_DOCENTE = {'docente', 'investigador', 'director'}


def _sin_acentos(value):
    return ''.join(ch for ch in unicodedata.normalize('NFKD', value) if not unicodedata.combining(ch))


def normalizar_rol(value):
    """Normaliza una etiqueta o código de rol al valor canónico de BD."""
    raw = str(value or '').strip().lower()
    plain = _sin_acentos(raw)
    if raw in ROLE_ALIASES:
        return ROLE_ALIASES[raw]
    if plain in ROLE_ALIASES:
        return ROLE_ALIASES[plain]
    if 'coordin' in plain:
        return 'coordinacion'
    if 'servicio' in plain:
        return 'servicios'
    if 'director' in plain:
        return 'director'
    if 'admin' in plain:
        return 'admin'
    if 'investig' in plain:
        return 'investigador'
    if 'docente' in plain or 'profesor' in plain or plain == 'teacher':
        return 'docente'
    if 'alumno' in plain or 'student' in plain:
        return 'alumno'
    return 'aspirante'


def rol_de(user):
    """Versión sin acentos del campo ``rol`` (compatibilidad). Preferir ``rol_efectivo``."""
    return _sin_acentos(str(getattr(user, 'rol', '') or '').strip().lower())


def rol_efectivo(user):
    """Rol de sesión/permisos: el mismo que recibe el frontend tras el login."""
    if getattr(user, 'is_superuser', False):
        return 'admin'
    return normalizar_rol(getattr(user, 'rol', ''))


def es_admin(user):
    return bool(getattr(user, 'is_authenticated', False) and rol_efectivo(user) == 'admin')


def es_coordinacion(user):
    return bool(getattr(user, 'is_authenticated', False) and rol_efectivo(user) in {'coordinacion', 'admin'})


def es_gestion_academica(user):
    """Administración o Coordinación Académica."""
    return bool(getattr(user, 'is_authenticated', False) and rol_efectivo(user) in ROLES_GESTION)


def es_servicios(user):
    return bool(getattr(user, 'is_authenticated', False) and (
        getattr(user, 'is_superuser', False) or rol_efectivo(user) == 'servicios'
    ))


def es_docente(user):
    """Docente, investigador o director (pueden usar el panel docente)."""
    return bool(getattr(user, 'is_authenticated', False) and rol_efectivo(user) in ROLES_DOCENTE)


def es_director(user):
    return bool(getattr(user, 'is_authenticated', False) and rol_efectivo(user) == 'director')


def es_alumno(user):
    return bool(getattr(user, 'is_authenticated', False) and rol_efectivo(user) == 'alumno')


def es_aspirante(user):
    return bool(getattr(user, 'is_authenticated', False) and rol_efectivo(user) == 'aspirante')


MENSAJE_EGRESADO_SOLO_CONSULTA = (
    'Tu cuenta de egresado solo permite consultar y descargar documentos. '
    'Las acciones académicas operativas están deshabilitadas.'
)


def es_egresado(user):
    """Alumno con egreso formal: puede iniciar sesión, pero solo en modo consulta."""
    return es_alumno(user) and str(getattr(user, 'proceso_estado', '') or '').strip().lower() == 'egresado'


def bloquear_si_egresado(user):
    """Devuelve una respuesta 403 si el egresado intenta una acción operativa."""
    if not es_egresado(user):
        return None
    from rest_framework import status
    from rest_framework.response import Response
    return Response(
        {'detail': MENSAJE_EGRESADO_SOLO_CONSULTA, 'codigo': 'egresado_solo_consulta'},
        status=status.HTTP_403_FORBIDDEN,
    )
