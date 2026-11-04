from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from preregistro import camunda

USUARIOS_DEMO = ('john', 'mary', 'peter', 'demo')
GRUPOS_DEMO = ('accounting', 'management', 'sales')
PROCESOS_DEMO = ('invoice', 'ReviewInvoice')
CREDENCIALES_FABRICA = ('demo', 'demo')
DIRECTORIO_BPMN = Path('/app/bpmn')


class Command(BaseCommand):
    help = ('Crea la cuenta de servicio del backend en Camunda, elimina los usuarios y procesos de '
            'demostración y verifica que la API REST exija autenticación.')

    def handle(self, *args, **options):
        usuario = settings.CAMUNDA_USER
        password = settings.CAMUNDA_PASSWORD
        if not usuario.isalnum() or len(password) < 12:
            raise CommandError('Define CAMUNDA_USER (solo letras y números) y CAMUNDA_PASSWORD (al menos 12 caracteres).')
        base = camunda.rest_url()
        if not base:
            raise CommandError('Define CAMUNDA_URL.')
        propia = (usuario, password)

        auth = self._autenticar(base, propia)
        if auth is None:
            auth = self._autenticar(base, CREDENCIALES_FABRICA)
            if auth is None:
                raise CommandError(
                    'No fue posible autenticarse en Camunda. En una instalación nueva crea primero el '
                    'administrador inicial desde http://localhost:8081/camunda y usa esas credenciales.'
                )
            self._crear_o_actualizar(base, auth, usuario, password)
            auth = propia

        for grupo in GRUPOS_DEMO:
            if self._existe(base, auth, f'/group/{grupo}'):
                self._borrar(base, auth, f'/group/{grupo}', f'grupo {grupo}')
        for clave in PROCESOS_DEMO:
            definiciones = requests.get(f'{base}/process-definition', params={'key': clave}, auth=auth, timeout=10)
            definiciones.raise_for_status()
            for despliegue in {d['deploymentId'] for d in definiciones.json()}:
                self._borrar(base, auth, f'/deployment/{despliegue}?cascade=true', f'despliegue {clave}')
        for demo in USUARIOS_DEMO:
            if demo != usuario and self._existe(base, auth, f'/user/{demo}/profile'):
                self._borrar(base, auth, f'/user/{demo}', f'usuario {demo}')
        self._desplegar_procesos(base, auth)

        anonimo = requests.get(f'{base}/user', timeout=10).status_code
        if anonimo != 401:
            raise CommandError(f'La API REST responde {anonimo} sin credenciales; reconstruye la imagen de Camunda.')
        self.stdout.write(self.style.SUCCESS('Camunda configurado: la API REST exige credenciales.'))

    def _autenticar(self, base, auth):
        respuesta = requests.get(f'{base}/user/{auth[0]}/profile', auth=auth, timeout=10)
        return auth if respuesta.status_code == 200 else None

    def _crear_o_actualizar(self, base, auth, usuario, password):
        perfil = requests.get(f'{base}/user/{usuario}/profile', auth=auth, timeout=10)
        if perfil.status_code == 404:
            respuesta = requests.post(f'{base}/user/create', auth=auth, timeout=10, json={
                'profile': {'id': usuario, 'firstName': 'SINAC', 'lastName': 'Backend', 'email': f'{usuario}@sinac.local'},
                'credentials': {'password': password},
            })
            if not respuesta.ok:
                raise CommandError(f'Camunda rechazó la cuenta {usuario}: {respuesta.text[:300]}')
            self.stdout.write(f'Usuario {usuario} creado.')
        else:
            respuesta = requests.put(f'{base}/user/{usuario}/credentials', auth=auth, timeout=10, json={
                'password': password, 'authenticatedUserPassword': auth[1],
            })
            respuesta.raise_for_status()
            self.stdout.write(f'Contraseña de {usuario} actualizada.')
        miembro = requests.put(f'{base}/group/camunda-admin/members/{usuario}', auth=auth, timeout=10)
        if miembro.status_code not in (204, 409):
            miembro.raise_for_status()

    def _desplegar_procesos(self, base, auth):
        archivos = sorted(DIRECTORIO_BPMN.glob('*.bpmn'))
        if not archivos:
            self.stdout.write(self.style.WARNING(f'No hay modelos BPMN en {DIRECTORIO_BPMN}; se omite el despliegue.'))
            return
        respuesta = requests.post(
            f'{base}/deployment/create', auth=auth, timeout=30,
            data={'deployment-name': 'sinac', 'enable-duplicate-filtering': 'true', 'deploy-changed-only': 'true'},
            files=[(archivo.name, (archivo.name, archivo.read_bytes(), 'application/xml')) for archivo in archivos],
        )
        if not respuesta.ok:
            raise CommandError(f'Camunda rechazó los modelos BPMN: {respuesta.text[:300]}')
        nuevos = respuesta.json().get('deployedProcessDefinitions') or {}
        self.stdout.write(f'Modelos BPMN desplegados: {len(nuevos)} nuevos o modificados de {len(archivos)}.')

    @staticmethod
    def _existe(base, auth, ruta):
        # Camunda responde 204 al borrar usuarios o grupos inexistentes, así que se consulta antes.
        return requests.get(f'{base}{ruta}', auth=auth, timeout=10).status_code == 200

    def _borrar(self, base, auth, ruta, descripcion):
        respuesta = requests.delete(f'{base}{ruta}', auth=auth, timeout=20)
        if respuesta.status_code in (200, 204):
            self.stdout.write(f'Eliminado: {descripcion}.')
        elif respuesta.status_code != 404:
            respuesta.raise_for_status()
