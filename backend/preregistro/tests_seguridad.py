import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle

from preregistro.models import Aspirante
from preregistro.seguridad import celda_segura, nombre_archivo_seguro, url_media

DATOS_REGISTRO = {
    'nombre': 'Ana López', 'usuario': 'ANASEGURA', 'curp': 'LOPA850101HDFRRR01',
    'correo': 'ana.segura@example.com', 'telefono': '5512345678', 'nacimiento': '1985-01-01',
    'password': 'Segura2026x', 'estado_actual': 'Ciudad de México', 'municipio_actual': 'Coyoacán',
    'direccion_actual': 'Calle 1', 'estado_permanente': 'Ciudad de México', 'municipio_permanente': 'Coyoacán',
    'direccion_permanente': 'Calle 1', 'nombre_familiar': 'Juan López', 'parentesco': 'Padre',
    'telefono_familiar': '5511111111', 'ultimo_grado': 'Licenciatura', 'institucion': 'Cinvestav',
    'unidad': 'Cinvestav', 'departamento': 'Academia', 'seccion': 'Posgrado', 'programa': 'Ingeniería',
    'modalidad': 'Presencial',
}


def crear_usuario(usuario, **extra):
    datos = {k: v for k, v in DATOS_REGISTRO.items() if k not in ('password', 'usuario', 'correo', 'curp')}
    datos.update(extra)
    return Aspirante.objects.create_user(
        usuario=usuario, correo=f'{usuario.lower()}@example.com', curp=f'{usuario:X<18}'[:18],
        password='Segura2026x', business_key=f'TEST-{usuario}', **datos,
    )


def png(nombre='foto.png'):
    buffer = BytesIO()
    Image.new('RGB', (4, 4), 'teal').save(buffer, 'PNG')
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type='image/png')


class RegistroPublicoSeguroTests(TestCase):
    def test_registro_ignora_campos_de_privilegio(self):
        payload = {**DATOS_REGISTRO, 'is_superuser': True, 'is_staff': True, 'rol': 'docente',
                   'apoyo_autorizado': True, 'matricula': 'A0001', 'curso_propedeutico_aprobado': True}
        response = APIClient().post('/api/preregistro/', payload, format='json')

        self.assertEqual(response.status_code, 201, response.content)
        usuario = Aspirante.objects.get(usuario='ANASEGURA')
        self.assertFalse(usuario.is_superuser)
        self.assertFalse(usuario.is_staff)
        self.assertEqual(usuario.rol, 'aspirante')
        self.assertFalse(usuario.apoyo_autorizado)
        self.assertIsNone(usuario.matricula)
        self.assertFalse(usuario.curso_propedeutico_aprobado)


class MiPerfilSeguroTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario('PERFIL01')
        self.client = APIClient()
        self.client.force_authenticate(self.usuario)

    def test_patch_no_permitido(self):
        response = self.client.patch('/api/preregistro/me/', {'is_superuser': True}, format='json')
        self.assertEqual(response.status_code, 405)
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.is_superuser)

    def test_put_solo_actualiza_campos_editables(self):
        response = self.client.put('/api/preregistro/me/', {
            'nombre': 'Nombre Nuevo', 'is_superuser': True, 'is_staff': True, 'rol': 'docente', 'apoyo_autorizado': True,
        }, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.nombre, 'Nombre Nuevo')
        self.assertFalse(self.usuario.is_superuser)
        self.assertFalse(self.usuario.is_staff)
        self.assertEqual(self.usuario.rol, 'aspirante')
        self.assertFalse(self.usuario.apoyo_autorizado)

    def test_put_rechaza_correo_duplicado(self):
        otro = crear_usuario('PERFIL02')
        response = self.client.put('/api/preregistro/me/', {'correo': otro.correo}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_put_rechaza_imagen_falsa(self):
        falsa = SimpleUploadedFile('foto.png', b'<script>alert(1)</script>', content_type='image/png')
        response = self.client.put('/api/preregistro/me/', {'profile_photo': falsa}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertIn('profile_photo', response.data)


class ArchivosSegurosTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.usuario = crear_usuario('ARCHIVO01')
        self.client = APIClient()
        self.client.force_authenticate(self.usuario)

    def test_documento_que_no_es_pdf_se_rechaza(self):
        falso = SimpleUploadedFile('cv.pdf', b'MZ\x90\x00 ejecutable disfrazado', content_type='application/pdf')
        response = self.client.post('/api/preregistro/documentos/', {'tipo': 'cv', 'archivo': falso}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertIn('archivo', response.data)

    def test_documento_pdf_real_se_acepta_con_nombre_saneado(self):
        pdf = SimpleUploadedFile('../../etc/mi cv<1>.pdf', b'%PDF-1.4\n%contenido\n', content_type='application/pdf')
        response = self.client.post('/api/preregistro/documentos/', {'tipo': 'cv', 'archivo': pdf}, format='multipart')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertNotIn('/', response.data['nombre_original'])
        self.assertNotIn('..', response.data['nombre_original'])

    def test_media_requiere_firma_valida(self):
        self.usuario.profile_photo = png()
        self.usuario.save()
        anonimo = APIClient()
        ruta = f'/media/{self.usuario.profile_photo.name}'

        self.assertEqual(anonimo.get(ruta).status_code, 404)
        self.assertEqual(anonimo.get(f'{ruta}?firma=falsa:firma').status_code, 404)
        firmada = url_media(self.usuario.profile_photo)
        respuesta = anonimo.get(firmada)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['X-Content-Type-Options'], 'nosniff')
        b''.join(respuesta.streaming_content)

        otra = firmada.replace(self.usuario.profile_photo.name, 'profile_photos/otra.png')
        self.assertEqual(anonimo.get(otra).status_code, 404)

    def test_media_no_permite_salir_de_media_root(self):
        self.assertEqual(APIClient().get('/media/../config/settings.py').status_code, 404)

    def test_perfil_expone_foto_firmada(self):
        self.usuario.profile_photo = png()
        self.usuario.save()
        foto = self.client.get('/api/preregistro/me/').data['profile_photo']
        self.assertIn('?firma=', foto)


class UtilidadesSeguridadTests(TestCase):
    def test_celda_segura_neutraliza_formulas(self):
        self.assertEqual(celda_segura('=HYPERLINK("http://x")'), '\'=HYPERLINK("http://x")')
        self.assertEqual(celda_segura('+1'), "'+1")
        self.assertEqual(celda_segura('@SUM(A1)'), "'@SUM(A1)")
        self.assertEqual(celda_segura('Texto normal'), 'Texto normal')
        self.assertEqual(celda_segura(5), 5)

    def test_nombre_archivo_seguro(self):
        self.assertEqual(nombre_archivo_seguro('..\\..\\windows\\evil.PDF'), 'evil.pdf')
        self.assertEqual(nombre_archivo_seguro(''), 'archivo')


class LimiteIntentosTests(TestCase):
    def test_login_responde_429_al_superar_el_limite(self):
        tasas = {'anon': '1000/minute', 'user': '1000/minute', 'login': '3/minute', 'registro': '5/hour', 'refresh': '30/minute'}
        cache.clear()
        self.addCleanup(cache.clear)
        with patch.object(ScopedRateThrottle, 'THROTTLE_RATES', tasas), patch.object(AnonRateThrottle, 'THROTTLE_RATES', tasas):
            cliente = APIClient()
            codigos = [cliente.post('/api/auth/login/', {'usuario': 'nadie', 'password': 'x'}, format='json').status_code for _ in range(4)]
        self.assertEqual(codigos[:3], [401, 401, 401])
        self.assertEqual(codigos[3], 429)
