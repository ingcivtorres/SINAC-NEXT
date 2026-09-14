import os
from io import BytesIO

import django
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient
from PIL import Image

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from preregistro.models import Aspirante, SeguimientoSolicitud
from preregistro.serializers import AspiranteRegistroSerializer


class DocumentoAspiranteViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.aspirante = Aspirante.objects.create_user(
            usuario='XIM9712',
            correo='ximena@example.com',
            password='password123',
            nombre='Ximena Quintana Gante',
            curp='QUGX850101HDFRNN01',
            telefono='5512345678',
            estado_actual='Ciudad de México',
            municipio_actual='Coyoacán',
            direccion_actual='Calle 1',
            estado_permanente='Ciudad de México',
            municipio_permanente='Coyoacán',
            direccion_permanente='Calle 1',
            nombre_familiar='Juan Quintana',
            parentesco='Padre',
            telefono_familiar='5511111111',
            ultimo_grado='Licenciatura',
            institucion='Cinvestav',
            unidad='Cinvestav',
            departamento='Academia',
            seccion='Posgrado',
            programa='Ingeniería',
            business_key='XIM9712',
        )

    def test_upload_document_creates_record_with_size(self):
        self.client.force_authenticate(user=self.aspirante)
        archivo = SimpleUploadedFile(
            'CV.pdf',
            b'%PDF-1.4\n%test',
            content_type='application/pdf',
        )

        response = self.client.post('/api/preregistro/documentos/', {'tipo': 'cv', 'archivo': archivo}, format='multipart')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['tipo'], 'cv')
        self.assertEqual(response.data['tamano'], len(b'%PDF-1.4\n%test'))

    def test_profile_endpoint_updates_photo(self):
        image_buffer = BytesIO()
        Image.new('RGB', (2, 2), color='white').save(image_buffer, format='PNG')
        image_buffer.seek(0)
        photo = SimpleUploadedFile('perfil.png', image_buffer.read(), content_type='image/png')
        self.client.force_authenticate(user=self.aspirante)
        response = self.client.patch('/api/preregistro/perfil/', {'profile_photo': photo, 'nombre': 'Ximena Actualizada'}, format='multipart')
        self.assertEqual(response.status_code, 200)
        self.aspirante.refresh_from_db()
        self.assertEqual(self.aspirante.nombre, 'Ximena Actualizada')
        self.assertTrue(self.aspirante.profile_photo.name)


class AspiranteRegistroSerializerTests(TestCase):
    def setUp(self):
        self.base_payload = {
            'nombre': 'Ana López',
            'usuario': 'ANALOPEZ',
            'curp': 'LOPA850101HDFRRR01',
            'correo': 'ana@example.com',
            'telefono': '5512345678',
            'nacimiento': '1985-01-01',
            'password': 'password123',
            'estado_actual': 'Ciudad de México',
            'municipio_actual': 'Coyoacán',
            'direccion_actual': 'Calle 1',
            'estado_permanente': 'Ciudad de México',
            'municipio_permanente': 'Coyoacán',
            'direccion_permanente': 'Calle 1',
            'nombre_familiar': 'Juan López',
            'parentesco': 'Padre',
            'telefono_familiar': '5511111111',
            'ultimo_grado': 'Licenciatura',
            'institucion': 'Cinvestav',
            'promedio': '9.5',
            'idiomas': '',
            'publicaciones': '',
            'apoyos': '',
            'experiencia': '',
            'unidad': 'Cinvestav',
            'departamento': 'Academia',
            'seccion': 'Posgrado',
            'programa': 'Ingeniería',
            'modalidad': 'Presencial',
            'tutor_propuesto': '',
            'comentarios': '',
        }

    def test_duplicate_usuario_is_rejected(self):
        Aspirante.objects.create_user(**{k: v for k, v in self.base_payload.items() if k != 'password'}, password='password123')
        payload = {**self.base_payload, 'usuario': 'analopez', 'correo': 'otro@example.com', 'curp': 'LOPA850101HDFRRR02'}

        serializer = AspiranteRegistroSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn('usuario', serializer.errors)

    def test_duplicate_curp_is_rejected(self):
        Aspirante.objects.create_user(**{k: v for k, v in self.base_payload.items() if k != 'password'}, password='password123')
        payload = {**self.base_payload, 'usuario': 'OTROUSER', 'correo': 'otro@example.com', 'curp': 'LOPA850101HDFRRR01'}

        serializer = AspiranteRegistroSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn('curp', serializer.errors)

    def test_duplicate_correo_is_rejected(self):
        Aspirante.objects.create_user(**{k: v for k, v in self.base_payload.items() if k != 'password'}, password='password123')
        payload = {**self.base_payload, 'usuario': 'OTROUSER2', 'correo': 'ana@example.com', 'curp': 'LOPA850101HDFRRR03'}

        serializer = AspiranteRegistroSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn('correo', serializer.errors)


class AspiranteLoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = Aspirante.objects.create_user(
            usuario='DOCENTE01',
            correo='docente@institucion.edu.mx',
            password='password123',
            nombre='Docente Prueba',
            curp='DOCU850101HDFRNN01',
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
            ultimo_grado='Doctorado',
            institucion='Cinvestav',
            unidad='Cinvestav',
            departamento='Academia',
            seccion='Posgrado',
            programa='Ingeniería',
            business_key='DOCENTE-PRUEBA',
            rol='docente',
        )

    def test_login_works_with_username_or_email_and_returns_role(self):
        response_by_user = self.client.post('/api/auth/login/', {'usuario': 'DOCENTE01', 'password': 'password123'}, format='json')
        self.assertEqual(response_by_user.status_code, 200)
        self.assertEqual(response_by_user.data['role'], 'docente')

        response_by_email = self.client.post('/api/auth/login/', {'usuario': 'docente@institucion.edu.mx', 'password': 'password123'}, format='json')
        self.assertEqual(response_by_email.status_code, 200)
        self.assertEqual(response_by_email.data['role'], 'docente')


class AspiranteAdminPanelTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = Aspirante.objects.create_superuser(
            usuario='ADMINPANEL',
            correo='admin.panel@example.com',
            password='adminpass123',
            nombre='Administrador Panel',
            curp='ADMN850101HDFRNN01',
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
            ultimo_grado='Licenciatura',
            institucion='Cinvestav',
            unidad='Cinvestav',
            departamento='Academia',
            seccion='Posgrado',
            programa='Ingeniería',
            business_key='ADMIN-PANEL',
        )
        self.client.force_authenticate(user=self.admin)

    def test_admin_can_create_user_with_custom_password(self):
        response = self.client.post(
            '/api/administracion/panel/',
            {
                'name': 'Dr. Juan Pérez',
                'email': 'jperez@sinac.edu.mx',
                'role': 'Docente',
                'area': 'Sistemas',
                'password': 'MiPassword123!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Aspirante.objects.filter(correo='jperez@sinac.edu.mx').exists())
        usuario = Aspirante.objects.get(correo='jperez@sinac.edu.mx')
        self.assertTrue(usuario.check_password('MiPassword123!'))
        self.assertEqual(usuario.rol, 'docente')

    def test_admin_can_activate_and_deactivate_user(self):
        usuario = Aspirante.objects.create_user(
            usuario='USUARIOACT',
            correo='usuario.activo@example.com',
            password='password123',
            nombre='Usuario Activo',
            curp='ACTI850101HDFRNN01',
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
            ultimo_grado='Licenciatura',
            institucion='Cinvestav',
            unidad='Cinvestav',
            departamento='Academia',
            seccion='Posgrado',
            programa='Ingeniería',
            business_key='USUARIO-ACTIVO',
        )
        usuario.is_active = False
        usuario.save(update_fields=['is_active'])

        response = self.client.put(
            f'/api/administracion/aspirantes/{usuario.pk}/',
            {'status': 'Activo'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        usuario.refresh_from_db()
        self.assertTrue(usuario.is_active)

        response = self.client.put(
            f'/api/administracion/aspirantes/{usuario.pk}/',
            {'status': 'Inactivo'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        usuario.refresh_from_db()
        self.assertFalse(usuario.is_active)

    def test_admin_edit_user_accepts_frontend_values_for_role_status_and_password(self):
        usuario = Aspirante.objects.create_user(
            usuario='USUARIOEDIT',
            correo='usuario.edit@example.com',
            password='oldpass123',
            nombre='Usuario Editable',
            curp='EDIT850101HDFRNN01',
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
            ultimo_grado='Licenciatura',
            institucion='Cinvestav',
            unidad='Cinvestav',
            departamento='Academia',
            seccion='Posgrado',
            programa='Ingeniería',
            business_key='USUARIO-EDIT',
        )

        response = self.client.put(
            f'/api/administracion/aspirantes/{usuario.pk}/',
            {
                'name': 'Usuario Actualizado',
                'email': 'usuario.actualizado@example.com',
                'role': 'Docente',
                'area': 'Sistemas',
                'status': 'Inactivo',
                'password': 'NuevaPassword123!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        usuario.refresh_from_db()
        self.assertEqual(usuario.nombre, 'Usuario Actualizado')
        self.assertEqual(usuario.correo, 'usuario.actualizado@example.com')
        self.assertEqual(usuario.rol, 'docente')
        self.assertEqual(usuario.programa, 'Sistemas')
        self.assertFalse(usuario.is_active)
        self.assertTrue(usuario.check_password('NuevaPassword123!'))


class NotificacionesDeFechasTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        datos = {
            'nombre': 'Aspirante de Prueba', 'curp': 'PRUA850101HDFRNN01',
            'correo': 'aspirante.prueba@example.com', 'telefono': '5512345678',
            'estado_actual': 'Ciudad de México', 'municipio_actual': 'Coyoacán', 'direccion_actual': 'Calle 1',
            'estado_permanente': 'Ciudad de México', 'municipio_permanente': 'Coyoacán', 'direccion_permanente': 'Calle 1',
            'nombre_familiar': 'Familiar', 'parentesco': 'Madre', 'telefono_familiar': '5511111111',
            'ultimo_grado': 'Licenciatura', 'institucion': 'Cinvestav', 'unidad': 'Cinvestav',
            'departamento': 'Academia', 'seccion': 'Posgrado', 'programa': 'Ingeniería', 'business_key': 'PRUEBA-NOTIF',
        }
        self.aspirante = Aspirante.objects.create_user(usuario='ASPPRO1', password='password123', **datos)
        coordinador_datos = {**datos, 'nombre': 'Coordinación', 'curp': 'COOR850101HDFRNN01', 'correo': 'coordinacion.prueba@example.com', 'business_key': 'COORD-PRUEBA'}
        self.coordinador = Aspirante.objects.create_user(usuario='COORDP1', password='password123', is_staff=True, **coordinador_datos)
        self.client.force_authenticate(user=self.coordinador)

    def test_cada_fecha_genera_una_sola_notificacion_por_cambio(self):
        url = f'/api/coordinacion/aspirantes/{self.aspirante.pk}/'
        fechas = {
            'fecha_examen_admision': '2026-09-01T10:00:00Z',
            'fecha_inicio_curso_propedeutico': '2026-09-02T09:00:00Z',
            'fecha_entrevista': '2026-09-03T11:00:00Z',
        }

        for campo, valor in fechas.items():
            antes = SeguimientoSolicitud.objects.filter(aspirante=self.aspirante).count()
            respuesta = self.client.patch(url, {campo: valor}, format='json')
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(SeguimientoSolicitud.objects.filter(aspirante=self.aspirante).count(), antes + 1)

            respuesta_repetida = self.client.patch(url, {campo: valor}, format='json')
            self.assertEqual(respuesta_repetida.status_code, 200)
            self.assertEqual(SeguimientoSolicitud.objects.filter(aspirante=self.aspirante).count(), antes + 1)


class SolicitudApoyoTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.aspirante = Aspirante.objects.create_user(
            usuario='APOYO01', correo='apoyo@example.com', password='password123',
            nombre='Aspirante Apoyo', curp='APOY850101HDFRNN01', telefono='5512345678',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 1',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 1',
            nombre_familiar='Familiar', parentesco='Madre', telefono_familiar='5511111111',
            ultimo_grado='Licenciatura', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Academia', seccion='Posgrado', programa='Ingeniería', business_key='APOYO-PRUEBA',
            curso_propedeutico_aprobado=True, curso_propedeutico_nota='8.50',
        )
        self.client.force_authenticate(user=self.aspirante)

    def test_apoyo_requiere_clabe_y_banco_y_luego_guarda_datos(self):
        url = '/api/preregistro/apoyo/solicitar/'
        self.assertEqual(self.client.post(url, {'banco': 'BBVA', 'clabe_interbancaria': '123'}, format='json').status_code, 400)
        response = self.client.post(url, {'banco': 'BBVA México', 'clabe_interbancaria': '012345678901234567'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.aspirante.refresh_from_db()
        self.assertTrue(self.aspirante.apoyo_solicitado)
        self.assertEqual(self.aspirante.banco_apoyo, 'BBVA México')
        self.assertEqual(self.aspirante.clabe_interbancaria, '012345678901234567')


class ConvertirMismaCuentaTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.aspirante = Aspirante.objects.create_user(
            usuario='ALUMNO01', correo='alumno.cuenta@example.com', password='password123',
            nombre='Aspirante Cuenta', curp='CUEN850101HDFRNN01', telefono='5512345678',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 1',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 1',
            nombre_familiar='Familiar', parentesco='Madre', telefono_familiar='5511111111',
            ultimo_grado='Licenciatura', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Academia', seccion='Posgrado', programa='Ingeniería', business_key='CUENTA-PRUEBA',
            proceso_estado='aceptado',
        )
        self.client.force_authenticate(user=self.aspirante)

    def test_convertir_a_alumno_con_misma_cuenta(self):
        response = self.client.post('/api/preregistro/convertir-misma-cuenta/')

        self.assertEqual(response.status_code, 200)
        self.aspirante.refresh_from_db()
        self.assertEqual(self.aspirante.rol, 'alumno')
        self.assertEqual(response.data['rol'], 'alumno')
