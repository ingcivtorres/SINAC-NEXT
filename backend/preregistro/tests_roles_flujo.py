"""Flujo login → rol → panel API para cada perfil operativo."""
from django.test import TestCase
from rest_framework.test import APIClient

from preregistro.models import Aspirante
from preregistro.roles import normalizar_rol, rol_efectivo
from preregistro.serializers import InicioSesionSerializer


def _crear(usuario, rol, **extra):
    return Aspirante.objects.create_user(
        usuario=usuario,
        correo=f'{usuario}@flujo.test',
        password='Password1',
        nombre=f'Usuario {rol}',
        curp=f'CURP{usuario.upper()[:10]}XX01',
        telefono='5512345678',
        estado_actual='Ciudad de México',
        municipio_actual='Coyoacán',
        direccion_actual='Calle 1',
        estado_permanente='Ciudad de México',
        municipio_permanente='Coyoacán',
        direccion_permanente='Calle 1',
        nombre_familiar='Familiar',
        parentesco='Padre',
        telefono_familiar='5511111111',
        ultimo_grado='Maestría',
        institucion='Cinvestav',
        unidad='Zacatenco',
        departamento='Computación',
        seccion='Posgrado',
        programa='Ciencias de la Computación',
        business_key=f'FLUJO-{usuario}',
        rol=rol,
        **extra,
    )


class FlujoRolesPanelTests(TestCase):
    PANEL_POR_ROL = {
        'aspirante': None,
        'alumno': None,
        'docente': '/api/docente/panel/',
        'investigador': '/api/docente/panel/',
        'director': '/api/director/panel/',
        'coordinacion': '/api/coordinacion/panel/',
        'servicios': '/api/servicios-escolares/panel/',
        'admin': '/api/administracion/panel/',
    }

    def setUp(self):
        self.client = APIClient()
        self.usuarios = {
            'aspirante': _crear('flujo_asp', 'aspirante'),
            'alumno': _crear('flujo_alu', 'alumno'),
            'docente': _crear('flujo_doc', 'docente'),
            'investigador': _crear('flujo_inv', 'investigador'),
            'director': _crear('flujo_dir', 'director'),
            'coordinacion': _crear('flujo_coord', 'coordinacion', is_staff=True),
            'servicios': _crear('flujo_serv', 'servicios'),
            'admin': _crear('flujo_admin', 'admin', is_staff=True, is_superuser=True),
        }

    def test_normalizacion_alias_criticos(self):
        self.assertEqual(normalizar_rol('Coordinación Académica'), 'coordinacion')
        self.assertEqual(normalizar_rol('Servicios Escolares'), 'servicios')
        self.assertEqual(normalizar_rol('Director de Tesis'), 'director')
        self.assertEqual(normalizar_rol('administrador'), 'admin')
        self.assertEqual(normalizar_rol('profesor'), 'docente')
        self.assertEqual(normalizar_rol('student'), 'alumno')

    def test_login_devuelve_rol_y_abre_panel(self):
        for rol, user in self.usuarios.items():
            with self.subTest(rol=rol):
                respuesta = self.client.post(
                    '/api/auth/login/',
                    {'usuario': user.usuario, 'password': 'Password1'},
                    format='json',
                )
                self.assertEqual(respuesta.status_code, 200, respuesta.data)
                self.assertEqual(respuesta.data['role'], rol)
                self.assertEqual(InicioSesionSerializer.obtener_rol(user), rol)
                self.assertEqual(rol_efectivo(user), rol)

                panel = self.PANEL_POR_ROL[rol]
                if not panel:
                    continue
                self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
                panel_resp = self.client.get(panel)
                self.assertEqual(panel_resp.status_code, 200, panel_resp.data)
                self.client.credentials()

    def test_roles_no_entran_a_paneles_ajenos(self):
        alumno = self.usuarios['alumno']
        login = self.client.post(
            '/api/auth/login/',
            {'usuario': alumno.usuario, 'password': 'Password1'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        for panel in (
            '/api/docente/panel/',
            '/api/director/panel/',
            '/api/coordinacion/panel/',
            '/api/servicios-escolares/panel/',
            '/api/administracion/panel/',
        ):
            with self.subTest(panel=panel):
                self.assertEqual(self.client.get(panel).status_code, 403)

    def test_administrador_alias_accede_admin(self):
        user = self.usuarios['aspirante']
        user.rol = 'administrador'
        user.is_superuser = False
        user.is_staff = True
        user.save(update_fields=['rol', 'is_superuser', 'is_staff'])
        login = self.client.post(
            '/api/auth/login/',
            {'usuario': user.usuario, 'password': 'Password1'},
            format='json',
        )
        self.assertEqual(login.data['role'], 'admin')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        self.assertEqual(self.client.get('/api/administracion/panel/').status_code, 200)
