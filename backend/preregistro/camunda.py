"""Acceso común a la API REST de Camunda."""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TIPOS_VARIABLE = {bool: 'Boolean', int: 'Integer', float: 'Double', str: 'String'}


def rest_url():
    """Acepta tanto http://camunda:8080 como la URL completa de engine-rest; vacío si no está configurado."""
    configurada = (getattr(settings, 'CAMUNDA_URL', '') or '').rstrip('/')
    if not configurada:
        return ''
    return configurada if configurada.endswith('/engine-rest') else f'{configurada}/engine-rest'


def credenciales():
    usuario = getattr(settings, 'CAMUNDA_USER', '')
    return (usuario, getattr(settings, 'CAMUNDA_PASSWORD', '')) if usuario else None


def _url(ruta):
    base = rest_url()
    if not base:
        raise requests.ConnectionError('Camunda no está configurado (CAMUNDA_URL).')
    return f'{base}{ruta}'


def post(ruta, **kwargs):
    return requests.post(_url(ruta), auth=credenciales(), **kwargs)


def get(ruta, **kwargs):
    return requests.get(_url(ruta), auth=credenciales(), **kwargs)


def variables(**valores):
    return {
        nombre: {'value': valor, 'type': TIPOS_VARIABLE.get(type(valor), 'String')}
        for nombre, valor in valores.items() if valor is not None
    }


def iniciar(proceso, business_key, **valores):
    """Inicia una instancia; devuelve su id o None sin interrumpir la operación del sistema."""
    if not rest_url():
        return None
    try:
        respuesta = post(
            f'/process-definition/key/{proceso}/start',
            json={'businessKey': business_key, 'variables': variables(**valores)},
            timeout=6,
        )
        if respuesta.status_code == 200:
            return respuesta.json().get('id')
        logger.warning('Camunda no inició %s (%s): %s', proceso, respuesta.status_code, respuesta.text[:200])
    except requests.RequestException as exc:
        logger.warning('Camunda no disponible al iniciar %s: %s', proceso, exc)
    return None


def completar_tareas(proceso, tarea, business_key=None, filtro=None, **valores):
    """Completa las tareas activas que coincidan; devuelve cuántas se completaron."""
    if not rest_url():
        return 0
    consulta = {'processDefinitionKey': proceso, 'taskDefinitionKey': tarea, 'active': True}
    if business_key:
        consulta['processInstanceBusinessKey'] = business_key
    if filtro:
        consulta['processVariables'] = [
            {'name': nombre, 'operator': 'eq', 'value': valor} for nombre, valor in filtro.items()
        ]
    completadas = 0
    try:
        respuesta = post('/task', json=consulta, timeout=6)
        respuesta.raise_for_status()
        for tarea_activa in respuesta.json():
            post(f'/task/{tarea_activa["id"]}/complete', json={'variables': variables(**valores)}, timeout=6).raise_for_status()
            completadas += 1
    except requests.RequestException as exc:
        logger.warning('Camunda no disponible al completar %s/%s: %s', proceso, tarea, exc)
    return completadas
