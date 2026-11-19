"""Egresado: puede iniciar sesión, pero solo en modo consulta."""
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from preregistro.models import EgresoAlumno, Materia, PeriodoInscripcion
from preregistro.roles import MENSAJE_EGRESADO_SOLO_CONSULTA

User = get_user_model()


class AccesoEgresadoTests(APITestCase):
    def setUp(self):
        self.egresado = User.objects.create_user(
            usuario='egr.test',
            correo='egr.test@example.com',
            nombre='Egresado Prueba',
            password='Password1',
            rol='alumno',
            proceso_estado='egresado',
            matricula='EGR-TEST-001',
            curp='EGRT850101HDFXXX01',
            is_active=True,
        )
        EgresoAlumno.objects.create(alumno=self.egresado, fecha_egreso='2026-06-15', titulo_tesis='Tesis de prueba')
        self.periodo = PeriodoInscripcion.objects.create(
            nombre='Periodo prueba egresado',
            apertura='2026-01-01T00:00:00Z',
            cierre='2026-12-31T23:59:59Z',
            activo=True,
        )
        self.materia = Materia.objects.create(clave='EGR-101', nombre='Materia egresado', creditos=5)

    def _login(self):
        response = self.client.post('/api/auth/login/', {'usuario': 'egr.test', 'password': 'Password1'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response

    def test_egresado_puede_iniciar_sesion(self):
        response = self._login()
        self.assertEqual(response.data.get('role') or response.data.get('rol'), 'alumno')

    def test_egresado_puede_consultar_inscripciones(self):
        self._login()
        response = self.client.get('/api/preregistro/inscripciones/')
        self.assertEqual(response.status_code, 200)

    def test_egresado_no_puede_inscribir_materias(self):
        self._login()
        response = self.client.post(
            '/api/preregistro/inscripciones/',
            {'materias': [self.materia.pk]},
            format='json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data.get('codigo'), 'egresado_solo_consulta')
        self.assertIn('egresado', response.data.get('detail', '').lower())

    def test_egresado_no_puede_crear_solicitud_academica(self):
        self._login()
        response = self.client.post(
            '/api/preregistro/solicitudes-academicas/',
            {'tipo': 'historial', 'comentario': 'Necesito historial académico completo.'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data.get('detail'), MENSAJE_EGRESADO_SOLO_CONSULTA)

    def test_egresado_no_puede_solicitar_director(self):
        self._login()
        response = self.client.post(
            '/api/tesis/flujo/',
            {'linea_investigacion': 'IA', 'justificacion': 'Quiero iniciar un proyecto nuevo como egresado.'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data.get('codigo'), 'egresado_solo_consulta')
