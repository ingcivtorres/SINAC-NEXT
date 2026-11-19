from datetime import date, timedelta
from unittest.mock import patch

from django.core import signing
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from preregistro.credencial_views import SAL_CREDENCIAL, estado_credencial, generar_token
from preregistro.models import EgresoAlumno, Inscripcion, Materia, PeriodoInscripcion, VerificacionCredencial
from preregistro.tests_seguridad import crear_usuario


class CredencialDigitalTests(TestCase):
    def setUp(self):
        hoy = timezone.now()
        self.periodo = PeriodoInscripcion.objects.create(
            nombre='2026-B', apertura=hoy - timedelta(days=60), cierre=hoy - timedelta(days=30),
            fin_periodo=timezone.localdate() + timedelta(days=60), activo=False,
        )
        self.alumno = crear_usuario('CREDALU01', rol='alumno', matricula='A2026001')
        materia = Materia.objects.create(clave='CRED-101', nombre='Seminario de credenciales')
        Inscripcion.objects.create(aspirante=self.alumno, materia=materia, periodo_inscripcion=self.periodo)
        self.cliente = APIClient()
        self.cliente.force_authenticate(self.alumno)

    def verificar(self, token):
        return APIClient().get(f'/api/credencial/verificar/{token}/')

    def test_alumno_inscrito_tiene_credencial_vigente_con_qr(self):
        respuesta = self.cliente.get('/api/alumno/credencial/')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertTrue(respuesta.data['vigente'])
        self.assertEqual(respuesta.data['vigencia_hasta'], self.periodo.fin_periodo)
        self.assertTrue(respuesta.data['qr'].startswith('data:image/svg+xml;base64,'))
        self.assertIn('/verificar/', respuesta.data['url_verificacion'])

    def test_solo_alumnos_obtienen_credencial(self):
        cliente = APIClient()
        cliente.force_authenticate(crear_usuario('CREDDOC01', rol='docente'))
        self.assertEqual(cliente.get('/api/alumno/credencial/').status_code, 403)
        self.assertEqual(cliente.get('/api/alumno/credencial/pdf/').status_code, 403)

    def test_vigencia_depende_de_inscripcion_baja_y_egreso(self):
        self.assertTrue(estado_credencial(self.alumno)['vigente'])
        self.assertEqual(estado_credencial(self.alumno, self.periodo.fin_periodo + timedelta(days=1))['motivo'], 'periodo_concluido')

        sin_inscripcion = crear_usuario('CREDALU02', rol='alumno')
        self.assertEqual(estado_credencial(sin_inscripcion)['motivo'], 'sin_inscripcion')

        EgresoAlumno.objects.create(alumno=self.alumno, fecha_egreso=date.today())
        self.alumno.refresh_from_db()
        self.assertEqual(estado_credencial(self.alumno)['motivo'], 'egresado')

        self.alumno.proceso_estado = 'baja'
        self.assertEqual(estado_credencial(self.alumno)['motivo'], 'baja')

    def test_sin_fin_de_periodo_se_estima_por_periodicidad(self):
        self.periodo.fin_periodo = None
        self.periodo.save()
        fin = estado_credencial(self.alumno)['vigencia_hasta']
        self.assertGreater(fin, timezone.localtime(self.periodo.apertura).date() + timedelta(days=170))

    def test_verificacion_publica_muestra_solo_datos_minimos(self):
        respuesta = self.verificar(generar_token(self.alumno, 'pantalla'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data['resultado'], 'vigente')
        self.assertEqual(respuesta.data['nombre'], self.alumno.nombre)
        for sensible in ('curp', 'correo', 'telefono', 'nacimiento', 'direccion_actual'):
            self.assertNotIn(sensible, respuesta.data)
        self.assertEqual(VerificacionCredencial.objects.filter(alumno=self.alumno, resultado='vigente').count(), 1)

    def test_token_alterado_o_expirado_es_invalido(self):
        token = generar_token(self.alumno, 'pantalla')
        self.assertEqual(self.verificar(token[:-2] + 'xx').data['motivo'], 'firma')
        otro = signing.dumps({'a': self.alumno.pk + 1000, 'v': 1, 't': 'i'}, salt=SAL_CREDENCIAL)
        self.assertEqual(self.verificar(otro).data['resultado'], 'invalida')
        with patch('django.core.signing.time.time', return_value=timezone.now().timestamp() + 600):
            self.assertEqual(self.verificar(token).data['motivo'], 'qr_expirado')

    def test_credencial_impresa_vence_con_su_periodo(self):
        token = generar_token(self.alumno, 'impresa', date.today() - timedelta(days=1))
        respuesta = self.verificar(token)
        self.assertEqual(respuesta.data['resultado'], 'no_vigente')
        self.assertEqual(respuesta.data['motivo'], 'impresa_vencida')

    def test_reposicion_invalida_credenciales_anteriores(self):
        anterior = generar_token(self.alumno, 'impresa', self.periodo.fin_periodo)
        servicios = crear_usuario('CREDSERV1', rol='servicios')
        cliente = APIClient()
        cliente.force_authenticate(servicios)
        self.assertEqual(self.cliente.post(f'/api/servicios-escolares/alumnos/{self.alumno.pk}/credencial/reponer/').status_code, 403)
        respuesta = cliente.post(f'/api/servicios-escolares/alumnos/{self.alumno.pk}/credencial/reponer/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data['credencial_version'], 2)
        self.assertEqual(self.verificar(anterior).data['motivo'], 'reemplazada')
        self.alumno.refresh_from_db()
        self.assertEqual(self.verificar(generar_token(self.alumno, 'impresa', self.periodo.fin_periodo)).data['resultado'], 'vigente')

    def test_token_es_seguro_para_rutas_publicas(self):
        for tipo in ('pantalla', 'impresa'):
            token = generar_token(self.alumno, tipo, self.periodo.fin_periodo)
            self.assertFalse(token.startswith('.'))
            self.assertNotIn('/', token)

    def test_catalogo_administrativo_guarda_y_conserva_fin_de_periodo(self):
        cliente = APIClient()
        cliente.force_authenticate(crear_usuario('CREDADM01', rol='admin', is_superuser=True))
        datos = {'tipo': 'periodo', 'nombre': '2027-A', 'apertura': '2027-01-05T09:00', 'cierre': '2027-01-20T18:00', 'activo': False}
        respuesta = cliente.post('/api/administracion/catalogos/', {**datos, 'fin_periodo': '2027-06-30'}, format='json')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(PeriodoInscripcion.objects.get(nombre='2027-A').fin_periodo, date(2027, 6, 30))
        cliente.post('/api/administracion/catalogos/', datos, format='json')
        self.assertEqual(PeriodoInscripcion.objects.get(nombre='2027-A').fin_periodo, date(2027, 6, 30))
        invalido = cliente.post('/api/administracion/catalogos/', {**datos, 'fin_periodo': '2027-01-10'}, format='json')
        self.assertEqual(invalido.status_code, 400)

    def test_pdf_tamano_tarjeta_solo_si_esta_vigente(self):
        respuesta = self.cliente.get('/api/alumno/credencial/pdf/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertTrue(respuesta.content.startswith(b'%PDF'))

        self.alumno.proceso_estado = 'baja'
        self.alumno.save(update_fields=['proceso_estado'])
        self.assertEqual(self.cliente.get('/api/alumno/credencial/pdf/').status_code, 409)
