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

from preregistro.models import Aspirante, ExpedienteDigital
from preregistro.seguridad import celda_segura, nombre_archivo_seguro, url_media, validar_imagen

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


class AutorizacionPorRolTests(TestCase):
    def test_panel_coordinacion_usa_el_rol_y_no_solo_is_staff(self):
        casos = [
            (crear_usuario('SERVSTAFF', rol='servicios', is_staff=True), 403),
            (crear_usuario('ALUMSTAFF', rol='alumno'), 403),
            (crear_usuario('COORDROL', rol='coordinacion'), 200),
            (crear_usuario('ADMINROL', rol='admin'), 200),
            (crear_usuario('ASPSTAFF', is_staff=True), 403),
        ]
        for usuario, esperado in casos:
            cliente = APIClient()
            cliente.force_authenticate(usuario)
            self.assertEqual(cliente.get('/api/coordinacion/panel/').status_code, esperado, usuario.usuario)

    def test_firmas_solo_para_titular_director_o_gestion(self):
        director = crear_usuario('DIRFIRMA', rol='director')
        titular = crear_usuario('TITFIRMA', rol='alumno', director_tesis=director)
        ajeno = crear_usuario('AJEFIRMA', rol='alumno')
        expediente = ExpedienteDigital.objects.create(aspirante=titular, folio='EXP-FIRMA-0001')
        ruta = f'/api/expedientes/{expediente.pk}/firma/'
        for usuario, esperado in ((ajeno, 403), (titular, 200), (director, 200)):
            cliente = APIClient()
            cliente.force_authenticate(usuario)
            self.assertEqual(cliente.get(ruta).status_code, esperado, usuario.usuario)

    def test_is_staff_no_concede_sesion_ni_permisos_de_coordinacion(self):
        from preregistro.serializers import InicioSesionSerializer

        aspirante_staff = crear_usuario('ASPSTAFF2', is_staff=True)
        self.assertEqual(InicioSesionSerializer.obtener_rol(aspirante_staff), 'aspirante')
        cliente = APIClient()
        cliente.force_authenticate(aspirante_staff)
        self.assertEqual(cliente.get('/api/coordinacion/materias/').status_code, 403)
        self.assertEqual(cliente.post('/api/preregistro/evaluaciones-colegio/', {}, format='json').status_code, 403)

    def test_dictamen_colegio_solo_lo_emite_gestion_academica(self):
        aspirante = crear_usuario('ASPCOLEGIO')
        docente = crear_usuario('DOCCOLEGIO', rol='docente')
        coordinacion = crear_usuario('COOCOLEGIO', rol='coordinacion')
        ruta = '/api/preregistro/evaluaciones-colegio/'
        datos = {'aspirante': aspirante.pk, 'estado': 'favorable', 'dictamen': 'Cumple.'}

        cliente = APIClient()
        cliente.force_authenticate(docente)
        self.assertEqual(cliente.post(ruta, datos, format='json').status_code, 403)

        cliente.force_authenticate(coordinacion)
        self.assertEqual(cliente.post(ruta, {**datos, 'fecha_evaluacion': 'mañana'}, format='json').status_code, 400)
        creada = cliente.post(ruta, {**datos, 'fecha_evaluacion': '2026-11-10'}, format='json')
        self.assertEqual(creada.status_code, 201, creada.content)

        cliente.force_authenticate(docente)
        detalle = f"{ruta}{creada.data['id']}/"
        self.assertEqual(cliente.patch(detalle, {'estado': 'no_favorable'}, format='json').status_code, 403)
        self.assertEqual(cliente.get(ruta).data, [])

    def test_migracion_retira_is_staff_a_roles_sin_gestion(self):
        from importlib import import_module
        from django.apps import apps as django_apps

        aspirante = crear_usuario('ASPMIGRA', is_staff=True)
        coordinacion = crear_usuario('COOMIGRA', rol='coordinacion', is_staff=True)
        import_module('preregistro.migrations.0054_retirar_is_staff_sin_rol_de_gestion').retirar_is_staff(django_apps, None)
        aspirante.refresh_from_db()
        coordinacion.refresh_from_db()
        self.assertFalse(aspirante.is_staff)
        self.assertTrue(coordinacion.is_staff)

    def test_superusuario_se_crea_con_rol_admin(self):
        admin = Aspirante.objects.create_superuser(usuario='SUPERROL', correo='super.rol@example.com', password='Segura2026x')
        self.assertEqual(admin.rol, 'admin')

    def test_imagen_con_formato_no_permitido_se_rechaza(self):
        buffer = BytesIO()
        Image.new('RGB', (4, 4), 'teal').save(buffer, 'GIF')
        self.assertIsNotNone(validar_imagen(SimpleUploadedFile('foto.png', buffer.getvalue(), content_type='image/png')))
        self.assertIsNone(validar_imagen(png()))


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


class SesionesJWTTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.usuario = crear_usuario('SESIONJWT', rol='alumno')
        self.cliente = APIClient()

    def iniciar(self):
        respuesta = self.cliente.post('/api/auth/login/', {'usuario': 'SESIONJWT', 'password': 'Segura2026x'}, format='json')
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.data['refresh']

    def renovar(self, refresh):
        return self.cliente.post('/api/auth/refresh/', {'refresh': refresh}, format='json')

    def test_renovar_rota_el_token_y_el_anterior_queda_invalido(self):
        refresh = self.iniciar()
        respuesta = self.renovar(refresh)
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotEqual(respuesta.data['refresh'], refresh)
        self.assertEqual(self.renovar(refresh).status_code, 401)

    def test_cerrar_sesion_invalida_el_token_de_renovacion(self):
        refresh = self.iniciar()
        self.assertEqual(self.cliente.post('/api/auth/logout/', {'refresh': refresh}, format='json').status_code, 205)
        self.assertEqual(self.renovar(refresh).status_code, 401)

    def test_revocar_sesiones_invalida_todos_los_tokens(self):
        from preregistro.sesiones import revocar_sesiones
        tokens = [self.iniciar(), self.iniciar()]
        revocar_sesiones(self.usuario)
        for refresh in tokens:
            self.assertEqual(self.renovar(refresh).status_code, 401)


class RecuperacionContrasenaTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.usuario = crear_usuario('RECUPERA', rol='alumno')
        self.cliente = APIClient()

    def solicitar(self, identificador):
        from django.core import mail
        mail.outbox.clear()
        respuesta = self.cliente.post('/api/auth/recuperar/', {'usuario': identificador}, format='json')
        self.assertEqual(respuesta.status_code, 200)
        return respuesta, mail.outbox

    def enlace(self):
        import re
        _, buzon = self.solicitar('recupera@example.com')
        self.assertEqual(len(buzon), 1)
        return dict(re.findall(r'[?&](uid|token)=([\w-]+)', buzon[0].body))

    def test_respuesta_identica_exista_o_no_la_cuenta(self):
        existente, buzon = self.solicitar('RECUPERA')
        self.assertEqual(len(buzon), 1)
        inexistente, buzon = self.solicitar('nadie@example.com')
        self.assertEqual(len(buzon), 0)
        self.assertEqual(existente.data, inexistente.data)

    def test_restablecer_cambia_la_contrasena_revoca_sesiones_y_el_enlace_es_de_un_uso(self):
        refresh = self.cliente.post('/api/auth/login/', {'usuario': 'RECUPERA', 'password': 'Segura2026x'}, format='json').data['refresh']
        datos = {**self.enlace(), 'password': 'NuevaClave2026'}
        self.assertEqual(self.cliente.post('/api/auth/restablecer/', datos, format='json').status_code, 200)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password('NuevaClave2026'))
        self.assertEqual(self.cliente.post('/api/auth/refresh/', {'refresh': refresh}, format='json').status_code, 401)
        self.assertEqual(self.cliente.post('/api/auth/restablecer/', datos, format='json').status_code, 400)

    def test_restablecer_rechaza_token_invalido_y_contrasena_debil(self):
        datos = self.enlace()
        self.assertEqual(self.cliente.post('/api/auth/restablecer/', {**datos, 'password': 'debil'}, format='json').status_code, 400)
        self.assertEqual(self.cliente.post('/api/auth/restablecer/', {**datos, 'token': 'x-y', 'password': 'NuevaClave2026'}, format='json').status_code, 400)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password('Segura2026x'))


@override_settings(CAMUNDA_URL='http://camunda:8080')
class IntegracionLidaTests(TestCase):
    def setUp(self):
        from unittest.mock import MagicMock
        from preregistro.models import DocumentoAspirante
        self.coordinacion = APIClient()
        self.coordinacion.force_authenticate(crear_usuario('COORDLIDA', rol='coordinacion'))
        self.aspirante = crear_usuario('ASPLIDA')
        self.documento = DocumentoAspirante.objects.create(
            aspirante=self.aspirante, tipo='cv', archivo='aspirantes/cv.pdf', nombre_original='cv.pdf', tamano=10,
        )
        respuesta = MagicMock(status_code=200)
        respuesta.json.return_value = [{'id': 'tarea-1'}]
        self.post = patch('preregistro.camunda.requests.post', return_value=respuesta).start()
        self.addCleanup(patch.stopall)

    def consulta(self):
        llamada = self.post.call_args_list[0]
        self.assertEqual(llamada.args[0], 'http://camunda:8080/engine-rest/task')
        return llamada.kwargs['json']

    def completado_con(self):
        self.assertEqual(self.post.call_args.args[0], 'http://camunda:8080/engine-rest/task/tarea-1/complete')
        return self.post.call_args.kwargs['json']['variables']

    def test_revisar_documento_completa_la_validacion_bpmn(self):
        ruta = f'/api/coordinacion/documentos/{self.documento.pk}/revision/'
        self.assertEqual(self.coordinacion.patch(ruta, {'revisado': True}, format='json').status_code, 200)
        self.assertEqual(self.consulta()['processVariables'], [{'name': 'documentoId', 'operator': 'eq', 'value': self.documento.pk}])
        self.assertEqual(self.completado_con(), {'valido': {'value': True, 'type': 'Boolean'}})

    def test_decision_final_cierra_la_revision_del_preregistro(self):
        self.documento.revisado = True
        self.documento.save(update_fields=['revisado'])
        ruta = f'/api/coordinacion/aspirantes/{self.aspirante.pk}/estado/'
        self.assertEqual(self.coordinacion.patch(ruta, {'proceso_estado': 'aceptado'}, format='json').status_code, 200)
        self.assertEqual(self.consulta()['processInstanceBusinessKey'], self.aspirante.business_key)
        self.assertEqual(self.completado_con(), {'decision': {'value': 'aceptado', 'type': 'String'}})


class PaginacionOpcionalTests(TestCase):
    def setUp(self):
        self.cliente = APIClient()
        self.cliente.force_authenticate(crear_usuario('ADMINPAG', rol='admin'))
        for numero in range(4):
            crear_usuario(f'PAGINA{numero}')

    def test_sin_page_devuelve_el_listado_completo(self):
        datos = self.cliente.get('/api/administracion/usuarios/').data
        self.assertEqual(len(datos['usuarios']), 5)
        self.assertNotIn('paginacion', datos)

    def test_con_page_devuelve_la_pagina_y_sus_metadatos(self):
        datos = self.cliente.get('/api/administracion/usuarios/?page=2&page_size=2').data
        self.assertEqual(len(datos['usuarios']), 2)
        self.assertEqual(datos['paginacion'], {'pagina': 2, 'paginas': 3, 'total': 5, 'tamano': 2})
        self.assertEqual(self.cliente.get('/api/administracion/usuarios/?page=9').status_code, 404)


class BloqueoPorOrigenTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        from preregistro.models import ConfiguracionSistema
        ConfiguracionSistema.objects.create(clave='bloqueo_intentos', valor='2')
        self.usuario = crear_usuario('BLOQORIGEN', rol='alumno')

    def login(self, password, ip):
        return APIClient().post(
            '/api/auth/login/', {'usuario': 'BLOQORIGEN', 'password': password}, format='json', REMOTE_ADDR=ip,
        ).status_code

    def test_el_bloqueo_aplica_al_origen_que_fallo_y_no_al_titular(self):
        self.assertEqual([self.login('mala', '10.0.0.9') for _ in range(2)], [401, 401])
        self.assertEqual(self.login('Segura2026x', '10.0.0.9'), 401)
        self.assertEqual(self.login('Segura2026x', '10.0.0.20'), 200)

    def test_demasiados_fallos_bloquean_la_cuenta_para_todos(self):
        for numero in range(10):
            self.login('mala', f'10.0.1.{numero}')
        self.assertEqual(self.login('Segura2026x', '10.0.0.20'), 401)
