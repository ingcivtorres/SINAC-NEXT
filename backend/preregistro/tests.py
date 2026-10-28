import os
from datetime import timedelta
from io import BytesIO
from unittest.mock import patch

import django
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from PIL import Image

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from preregistro.models import Aspirante, ConfiguracionPrograma, ConfiguracionSistema, ExpedienteDigital, Materia, CargaAcademica, CargaAcademicaMateria, PeriodoInscripcion, SeguimientoSolicitud, ProyectoTesis, JuradoProyecto, DefensaTesis, Inscripcion, PlanEstudioMateria, DocumentoAspirante, EgresoAlumno, SolicitudInscripcionExtemporanea, SolicitudAcademica, ExamenEnLinea
from preregistro.models import SolicitudDireccionTesis
from preregistro.alertas import generar_alertas_automatizadas
from preregistro.serializers import AspiranteRegistroSerializer


def crear_carga_publicada(creador, periodo, materias, capacidades=None):
    carga = CargaAcademica.objects.create(
        creador=creador,
        estado='publicada',
        periodo=periodo.nombre,
        periodo_inscripcion=periodo,
    )
    capacidades = capacidades or {}
    CargaAcademicaMateria.objects.bulk_create([
        CargaAcademicaMateria(
            carga=carga,
            materia=materia,
            horario=f'Lunes {10 + indice}:00-12:00',
            capacidad=capacidades.get(materia.pk, materia.capacidad),
        )
        for indice, materia in enumerate(materias)
    ])
    return carga


class CargaAcademicaPreparationTests(TestCase):
    def setUp(self):
        datos_base = {
            'password': 'password123',
            'telefono': '5512345678',
            'estado_actual': 'Ciudad de México',
            'municipio_actual': 'Coyoacán',
            'direccion_actual': 'Calle 1',
            'estado_permanente': 'Ciudad de México',
            'municipio_permanente': 'Coyoacán',
            'direccion_permanente': 'Calle 1',
            'nombre_familiar': 'Contacto de prueba',
            'parentesco': 'Familiar',
            'telefono_familiar': '5511111111',
            'ultimo_grado': 'Maestría',
            'institucion': 'Cinvestav',
            'unidad': 'Cinvestav',
            'departamento': 'Pruebas',
            'seccion': 'Posgrado',
            'programa': 'Programa de prueba',
        }
        self.docente = Aspirante.objects.create_user(
            usuario='docente-carga-test',
            correo='docente-carga-test@example.com',
            nombre='Docente de prueba',
            curp='QUGX850101HDFRNN02',
            business_key='DOCENTE-CARGA-TEST',
            rol='docente',
            **datos_base,
        )
        self.coordinacion = Aspirante.objects.create_user(
            usuario='coord-carga-test',
            correo='coordinacion-carga-test@example.com',
            nombre='Coordinación de prueba',
            curp='QUGX850101HDFRNN03',
            business_key='COORD-CARGA-TEST',
            rol='coordinacion',
            **datos_base,
        )
        self.servicios = Aspirante.objects.create_user(
            usuario='servicios-carga-test',
            correo='servicios-carga-test@example.com',
            nombre='Servicios de prueba',
            curp='QUGX850101HDFRNN04',
            business_key='SERVICIOS-CARGA-TEST',
            rol='servicios',
            **datos_base,
        )
        self.materia = Materia.objects.create(
            clave='CARGA-TEST-01',
            nombre='Materia para carga de prueba',
            profesor=self.docente.nombre,
            horario='Lunes 10:00-12:00',
        )
        self.client = APIClient()

    def test_docente_cannot_manage_academic_loads(self):
        self.client.force_authenticate(user=self.docente)
        listed = self.client.get('/api/cargas-academicas/')
        response = self.client.post('/api/cargas-academicas/', {
            'periodo': '2026-2',
            'materias': [{
                'materia': self.materia.id,
                'docente': self.docente.id,
                'horario': 'Martes 10:00-12:00',
                'salon': 'salon_1',
                'capacidad': 30,
                'modalidad': 'presencial',
            }],
        }, format='json')

        self.assertEqual(listed.status_code, 403)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CargaAcademica.objects.filter(creador=self.docente).exists())
        borrador = CargaAcademica.objects.create(
            creador=self.docente,
            periodo='2026-2',
            estado='borrador',
        )
        editado = self.client.patch(
            f'/api/cargas-academicas/{borrador.id}/',
            {'periodo': '2027-1'},
            format='json',
        )
        self.assertEqual(editado.status_code, 403)
        borrador.refresh_from_db()
        self.assertEqual(borrador.periodo, '2026-2')

    def test_coordination_can_view_catalog_and_edit_drafts(self):
        carga = CargaAcademica.objects.create(creador=self.docente, periodo='2026-2', estado='borrador')
        CargaAcademicaMateria.objects.create(
            carga=carga,
            materia=self.materia,
            horario='Lunes 10:00-12:00',
            salon='salon_1',
            capacidad=30,
            modalidad='presencial',
        )
        self.client.force_authenticate(user=self.coordinacion)

        response = self.client.get('/api/cargas-academicas/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['cargas']), 1)
        self.assertEqual(response.data['materias_catalogo'][0]['id'], self.materia.id)
        updated = self.client.patch(
            f'/api/cargas-academicas/{carga.id}/',
            {'periodo': '2027-1', 'materias': [{
                'materia': self.materia.id,
                'docente': self.docente.id,
                'horario': 'Miércoles 10:00-12:00',
                'salon': 'salon_1',
                'capacidad': 24,
                'modalidad': 'hibrida',
            }]},
            format='json',
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data['periodo'], '2027-1')
        self.assertEqual(updated.data['materias'][0]['modalidad'], 'hibrida')

    def test_staff_coordination_without_explicit_role_can_load_academic_loads(self):
        self.coordinacion.rol = ''
        self.coordinacion.is_staff = True
        self.coordinacion.save(update_fields=['rol', 'is_staff'])
        self.client.force_authenticate(user=self.coordinacion)

        response = self.client.get('/api/cargas-academicas/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('cargas', response.data)
        self.assertIn('materias_catalogo', response.data)

    def test_submission_requires_assigned_teacher_and_schedule(self):
        self.client.force_authenticate(user=self.coordinacion)
        draft = self.client.post('/api/cargas-academicas/', {
            'periodo': '2026-2',
            'materias': [{'materia': self.materia.id, 'docente': None, 'horario': ''}],
        }, format='json')
        self.assertEqual(draft.status_code, 201)

        submitted = self.client.patch(
            f"/api/cargas-academicas/{draft.data['id']}/",
            {'estado': 'en_revision'},
            format='json',
        )
        self.assertEqual(submitted.status_code, 400)
        self.assertIn('docente', submitted.data['detail'])

    def test_only_school_services_can_review_and_publish_loads(self):
        carga = CargaAcademica.objects.create(
            creador=self.docente,
            periodo='2026-2',
            estado='en_revision',
        )
        CargaAcademicaMateria.objects.create(
            carga=carga,
            materia=self.materia,
            docente=self.docente,
            horario='Lunes 10:00-12:00',
            salon='salon_1',
            capacidad=30,
            modalidad='presencial',
        )
        self.client.force_authenticate(user=self.coordinacion)

        missing_comment = self.client.patch(
            f'/api/cargas-academicas/{carga.id}/',
            {'estado': 'aprobada', 'comentario': 'Oferta revisada y completa.'},
            format='json',
        )
        self.assertEqual(missing_comment.status_code, 403)
        carga.refresh_from_db()
        self.assertEqual(carga.estado, 'en_revision')

        self.client.force_authenticate(user=self.servicios)
        missing_comment = self.client.patch(
            f'/api/cargas-academicas/{carga.id}/',
            {'estado': 'aprobada'},
            format='json',
        )
        self.assertEqual(missing_comment.status_code, 400)

        approved = self.client.patch(
            f'/api/cargas-academicas/{carga.id}/',
            {'estado': 'aprobada', 'comentario': 'Oferta revisada y completa.'},
            format='json',
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.data['estado'], 'aprobada')
        self.assertEqual(approved.data['comentario'], 'Oferta revisada y completa.')

        sin_periodo = self.client.patch(
            f'/api/cargas-academicas/{carga.id}/',
            {'estado': 'publicada'},
            format='json',
        )
        self.assertEqual(sin_periodo.status_code, 400)

        periodo_cerrado = PeriodoInscripcion.objects.create(
            nombre='2026-1-cerrado',
            apertura=timezone.now() - timedelta(days=30),
            cierre=timezone.now() - timedelta(days=1),
            activo=False,
        )
        no_habilitado = self.client.patch(
            f'/api/cargas-academicas/{carga.id}/',
            {'estado': 'publicada', 'periodo_inscripcion': periodo_cerrado.id},
            format='json',
        )
        self.assertEqual(no_habilitado.status_code, 400)

        periodo = PeriodoInscripcion.objects.create(
            nombre='2026-2',
            apertura=timezone.now() - timedelta(days=1),
            cierre=timezone.now() + timedelta(days=30),
            activo=True,
        )
        published = self.client.patch(
            f'/api/cargas-academicas/{carga.id}/',
            {'estado': 'publicada', 'periodo_inscripcion': periodo.id},
            format='json',
        )
        self.assertEqual(published.status_code, 200)
        self.assertEqual(published.data['periodo_inscripcion_id'], periodo.id)
        self.assertEqual(published.data['periodo'], periodo.nombre)

    def test_school_services_can_list_all_loads_and_periods(self):
        CargaAcademica.objects.create(creador=self.docente, periodo='2026-2', estado='en_revision')
        periodo = PeriodoInscripcion.objects.create(
            nombre='Periodo para Servicios',
            apertura=timezone.now() - timedelta(days=1),
            cierre=timezone.now() + timedelta(days=30),
            activo=True,
        )
        self.client.force_authenticate(user=self.servicios)

        response = self.client.get('/api/cargas-academicas/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['cargas']), 1)
        self.assertEqual(response.data['periodos_inscripcion'][0]['id'], periodo.id)

    def test_cannot_publish_duplicate_subjects_for_same_period(self):
        periodo = PeriodoInscripcion.objects.create(
            nombre='2026-2-duplicado',
            apertura=timezone.now() - timedelta(days=1),
            cierre=timezone.now() + timedelta(days=30),
            activo=True,
        )
        carga = CargaAcademica.objects.create(
            creador=self.docente,
            periodo='2026-2-duplicado',
            estado='aprobada',
        )
        CargaAcademicaMateria.objects.create(
            carga=carga,
            materia=self.materia,
            docente=self.docente,
            horario='Lunes 10:00-12:00',
        )
        crear_carga_publicada(self.docente, periodo, [self.materia])
        self.client.force_authenticate(user=self.servicios)

        response = self.client.patch(
            f'/api/cargas-academicas/{carga.id}/',
            {'estado': 'publicada', 'periodo_inscripcion': periodo.id},
            format='json',
        )

        self.assertEqual(response.status_code, 409)
        carga.refresh_from_db()
        self.assertEqual(carga.estado, 'aprobada')

    def test_teacher_cannot_review_submission(self):
        carga = CargaAcademica.objects.create(
            creador=self.docente,
            periodo='2026-2',
            estado='en_revision',
        )
        self.client.force_authenticate(user=self.docente)
        response = self.client.patch(
            f'/api/cargas-academicas/{carga.id}/',
            {'estado': 'rechazada', 'comentario': 'No procede.'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)


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

    def test_profile_endpoint_accepts_alumno_role_with_display_casing(self):
        image_buffer = BytesIO()
        Image.new('RGB', (2, 2), color='white').save(image_buffer, format='PNG')
        image_buffer.seek(0)
        photo = SimpleUploadedFile('perfil.png', image_buffer.read(), content_type='image/png')
        self.aspirante.rol = ' Alumno '
        self.aspirante.save(update_fields=['rol'])
        self.client.force_authenticate(user=self.aspirante)

        response = self.client.patch('/api/preregistro/perfil/', {'profile_photo': photo}, format='multipart')

        self.assertEqual(response.status_code, 200)
        self.aspirante.refresh_from_db()
        self.assertTrue(self.aspirante.profile_photo.name)
        self.assertTrue(self.aspirante.profile_photo.storage.exists(self.aspirante.profile_photo.name))

    def test_owner_can_read_centralized_digital_record(self):
        expediente = ExpedienteDigital.objects.create(aspirante=self.aspirante, folio='EXP-TEST-0001')
        self.client.force_authenticate(user=self.aspirante)

        response = self.client.get(f'/api/expedientes/{expediente.pk}/centralizado/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['expediente']['folio'], 'EXP-TEST-0001')
        self.assertEqual(response.data['alumno']['id'], self.aspirante.id)
        self.assertIn('documentos', response.data)
        self.assertIn('inscripciones', response.data)
        self.assertIn('seguimiento', response.data)
        self.assertIn('tesis', response.data)


class ServiciosEscolaresDocumentosAlumnoTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.alumno = Aspirante.objects.create_user(
            usuario='ALUMNO_DOCS', correo='alumno.docs@example.com', password='password123',
            nombre='Alumno Documentos', curp='DOCS850101HDFRNN01', telefono='5512345678',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 1',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 1',
            nombre_familiar='Familiar', parentesco='Padre', telefono_familiar='5511111111',
            ultimo_grado='Licenciatura', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Academia', seccion='Posgrado', programa='Ingeniería', business_key='ALUMNO-DOCS',
            rol='alumno',
        )

    def test_alumno_can_download_own_official_document(self):
        self.client.force_authenticate(user=self.alumno)

        response = self.client.get(f'/api/servicios-escolares/alumnos/{self.alumno.pk}/documentos/constancia/')
        payload = b''.join(response.streaming_content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn(b'%PDF', payload[:10])

    def test_boleta_uses_matricula_and_periodo_actual(self):
        self.alumno.matricula = 'CINV-2025-0001'
        self.alumno.numero_periodo_actual = 2
        self.alumno.save(update_fields=['matricula', 'numero_periodo_actual'])
        ConfiguracionPrograma.objects.create(programa='Ingeniería', grado='maestria', periodicidad='cuatrimestral')
        periodo = PeriodoInscripcion.objects.create(
            nombre='2025-1',
            apertura=timezone.now() - timedelta(days=30),
            cierre=timezone.now() + timedelta(days=30),
            activo=True,
        )
        materia = Materia.objects.create(
            clave='MATE-101',
            nombre='Matemáticas Avanzadas',
            profesor='Dr. Prueba',
            creditos=5,
        )
        Inscripcion.objects.create(aspirante=self.alumno, materia=materia, periodo_inscripcion=periodo, estado='cursando')

        self.client.force_authenticate(user=self.alumno)
        response = self.client.get('/api/preregistro/boleta-inscripcion/download/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('CINV-2025-0001_boleta_inscripcion.pdf', response['Content-Disposition'])
        from preregistro.views import _datos_academicos_boleta
        datos_academicos = _datos_academicos_boleta(self.alumno)
        self.assertEqual(datos_academicos['periodo_escolar'], '2025-1')
        self.assertEqual(datos_academicos['etiqueta_ciclo'], 'Cuatrimestre')
        self.assertEqual(datos_academicos['numero_ciclo'], 2)

        response_horario = self.client.get('/api/preregistro/horario/download/')
        self.assertEqual(response_horario.status_code, 200)
        self.assertEqual(response_horario['Content-Type'], 'application/pdf')
        self.assertIn(b'%PDF', b''.join(response_horario.streaming_content)[:10])


    def test_coordinacion_can_assign_student_academic_cycle(self):
        coordinacion = Aspirante.objects.create_superuser(
            usuario='COORD_CICLO', correo='coord.ciclo@example.com', password='password123', rol='coordinacion',
        )
        self.client.force_authenticate(user=coordinacion)

        response = self.client.patch(
            f'/api/coordinacion/aspirantes/{self.alumno.pk}/',
            {'numero_periodo_actual': 3},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.alumno.refresh_from_db()
        self.assertEqual(self.alumno.numero_periodo_actual, 3)

    def test_boleta_uses_latest_period_for_legacy_enrollments(self):
        periodo = PeriodoInscripcion.objects.create(
            nombre='2026-1',
            apertura=timezone.now() - timedelta(days=60),
            cierre=timezone.now() - timedelta(days=30),
            activo=False,
        )
        materia = Materia.objects.create(clave='MATE-102', nombre='Materia Histórica', creditos=4)
        Inscripcion.objects.create(aspirante=self.alumno, materia=materia, periodo_inscripcion=None)

        from preregistro.views import _datos_academicos_boleta
        datos_academicos = _datos_academicos_boleta(self.alumno)

        self.assertEqual(datos_academicos['periodo_escolar'], periodo.nombre)

    def test_servicios_escolares_validation_is_persisted_per_enrollment(self):
        materia = Materia.objects.create(clave='SERV-101', nombre='Materia validable', creditos=4)
        inscripcion = Inscripcion.objects.create(aspirante=self.alumno, materia=materia)
        servicios = Aspirante.objects.create_superuser(
            usuario='SERVICIOS_TEST', correo='servicios.test@example.com', password='password123', rol='servicios',
        )
        self.client.force_authenticate(user=servicios)

        observada = self.client.post(
            f'/api/servicios-escolares/alumnos/{self.alumno.pk}/validar-inscripcion/',
            {'inscripcion_id': inscripcion.pk, 'validar': 'false'},
            format='json',
        )
        self.assertEqual(observada.status_code, 200)
        inscripcion.refresh_from_db()
        self.assertEqual(inscripcion.validacion_servicios, 'observada')
        self.assertEqual(observada.data['inscripciones'][0]['validacion_servicios'], 'observada')

        validada = self.client.post(
            f'/api/servicios-escolares/alumnos/{self.alumno.pk}/validar-inscripcion/',
            {'inscripcion_id': inscripcion.pk, 'validar': True},
            format='json',
        )
        self.assertEqual(validada.status_code, 200)
        inscripcion.refresh_from_db()
        self.assertEqual(inscripcion.validacion_servicios, 'validada')

    def test_egreso_prevalidation_requires_configured_plan_and_all_thresholds(self):
        from preregistro.servicios_views import serializar_alumno

        sin_configuracion = serializar_alumno(self.alumno)
        self.assertFalse(sin_configuracion['prevalidacion_egreso']['completa'])

        configuracion = ConfiguracionPrograma.objects.create(
            programa='Ingeniería', grado='maestria', periodos_requeridos=2, creditos_requeridos=9,
        )
        materia_uno = Materia.objects.create(clave='EGRE-101', nombre='Materia obligatoria 1', creditos=4)
        materia_dos = Materia.objects.create(clave='EGRE-102', nombre='Materia obligatoria 2', creditos=5)
        PlanEstudioMateria.objects.create(configuracion=configuracion, materia=materia_uno, obligatoria=True)
        PlanEstudioMateria.objects.create(configuracion=configuracion, materia=materia_dos, obligatoria=True)
        periodo_uno = PeriodoInscripcion.objects.create(
            nombre='2025-1', apertura=timezone.now() - timedelta(days=120),
            cierre=timezone.now() - timedelta(days=60), activo=False,
        )
        periodo_dos = PeriodoInscripcion.objects.create(
            nombre='2025-2', apertura=timezone.now() - timedelta(days=60),
            cierre=timezone.now() - timedelta(days=1), activo=False,
        )
        inscripcion_uno = Inscripcion.objects.create(
            aspirante=self.alumno, materia=materia_uno, periodo_inscripcion=periodo_uno, calificacion=8,
        )
        inscripcion_dos = Inscripcion.objects.create(
            aspirante=self.alumno, materia=materia_dos, periodo_inscripcion=periodo_dos, calificacion=8,
        )

        completa = serializar_alumno(self.alumno)['prevalidacion_egreso']
        self.assertTrue(completa['completa'])
        self.assertEqual(completa['resumen']['creditos_aprobados'], 9)
        self.assertEqual(completa['resumen']['periodos_cursados'], 2)

        servicios = Aspirante.objects.create_superuser(
            usuario='SERVICIOS_EGRESO', correo='servicios.egreso@example.com', password='password123', rol='servicios',
        )
        self.client.force_authenticate(user=servicios)
        response_completa = self.client.get('/api/servicios-escolares/panel/')
        self.assertEqual(response_completa.data['resumen']['candidatos_egreso'], 1)

        inscripcion_dos.calificacion = 6
        inscripcion_dos.save(update_fields=['calificacion', 'updated_at'])
        incompleta = serializar_alumno(self.alumno)['prevalidacion_egreso']
        self.assertFalse(incompleta['completa'])
        self.assertEqual(incompleta['resumen']['materias_pendientes'][0]['clave'], materia_dos.clave)

        response = self.client.get('/api/servicios-escolares/panel/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['resumen']['candidatos_egreso'], 0)
        response_pdf = self.client.get(f'/api/servicios-escolares/alumnos/{self.alumno.pk}/documentos/egreso/')
        self.assertEqual(response_pdf.status_code, 200)
        self.assertIn(b'%PDF', b''.join(response_pdf.streaming_content)[:10])

    def test_available_courses_are_limited_to_active_program_plan(self):
        self.alumno.numero_periodo_actual = 1
        self.alumno.save(update_fields=['numero_periodo_actual'])
        periodo = PeriodoInscripcion.objects.create(
            nombre='2026-1', apertura=timezone.now() - timedelta(days=1),
            cierre=timezone.now() + timedelta(days=30), activo=True,
        )
        configuracion = ConfiguracionPrograma.objects.create(
            programa='Ingeniería', grado='maestria', periodos_requeridos=4,
        )
        materia_plan = Materia.objects.create(clave='PLAN-101', nombre='Materia del plan')
        materia_fuera_plan = Materia.objects.create(clave='EXTRA-101', nombre='Materia ajena al plan')
        materia_otro_periodo = Materia.objects.create(clave='PLAN-201', nombre='Materia del siguiente periodo')
        materia_no_publicada = Materia.objects.create(clave='PLAN-102', nombre='Materia aún no publicada')
        PlanEstudioMateria.objects.create(configuracion=configuracion, materia=materia_plan)
        PlanEstudioMateria.objects.create(configuracion=configuracion, materia=materia_otro_periodo, periodo_sugerido=2)
        PlanEstudioMateria.objects.create(configuracion=configuracion, materia=materia_no_publicada)
        crear_carga_publicada(
            self.alumno,
            periodo,
            [materia_plan, materia_fuera_plan, materia_otro_periodo],
        )
        self.client.force_authenticate(user=self.alumno)

        response = self.client.get('/api/preregistro/materias/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.data], [materia_plan.id])
        self.assertNotIn(materia_fuera_plan.id, [item['id'] for item in response.data])
        self.assertNotIn(materia_no_publicada.id, [item['id'] for item in response.data])

    def test_enrollment_requires_exactly_four_courses_per_period(self):
        self.alumno.numero_periodo_actual = 1
        self.alumno.save(update_fields=['numero_periodo_actual'])
        periodo = PeriodoInscripcion.objects.create(
            nombre='2026-cuatrimestre-1', apertura=timezone.now() - timedelta(days=1),
            cierre=timezone.now() + timedelta(days=30), activo=True,
        )
        configuracion = ConfiguracionPrograma.objects.create(
            programa='Ingeniería', grado='maestria', periodos_requeridos=6,
        )
        materias = [Materia.objects.create(clave=f'CUAT-{index:03d}', nombre=f'Materia del cuatrimestre {index}') for index in range(1, 6)]
        for materia in materias:
            PlanEstudioMateria.objects.create(configuracion=configuracion, materia=materia, periodo_sugerido=1)
        crear_carga_publicada(self.alumno, periodo, materias[:4])
        self.client.force_authenticate(user=self.alumno)

        incompleta = self.client.post(
            '/api/preregistro/inscripciones/',
            {'materias': [materia.id for materia in materias[:3]]},
            format='json',
        )
        self.assertEqual(incompleta.status_code, 400)
        self.assertEqual(Inscripcion.objects.filter(aspirante=self.alumno, periodo_inscripcion=periodo).count(), 0)

        no_publicada = self.client.post(
            '/api/preregistro/inscripciones/',
            {'materias': [materias[0].id, materias[1].id, materias[2].id, materias[4].id]},
            format='json',
        )
        self.assertEqual(no_publicada.status_code, 400)
        self.assertEqual(Inscripcion.objects.filter(aspirante=self.alumno, periodo_inscripcion=periodo).count(), 0)

        completa = self.client.post(
            '/api/preregistro/inscripciones/',
            {'materias': [materia.id for materia in materias[:4]]},
            format='json',
        )
        self.assertEqual(completa.status_code, 201)
        self.assertEqual(len(completa.data), 4)
        self.assertEqual(completa.data[0]['horario'], 'Lunes 10:00-12:00')
        self.assertEqual(Inscripcion.objects.filter(aspirante=self.alumno, periodo_inscripcion=periodo).count(), 4)

        quinta = self.client.post(
            '/api/preregistro/inscripciones/',
            {'materias': [materias[4].id]},
            format='json',
        )
        self.assertEqual(quinta.status_code, 400)
        self.assertEqual(Inscripcion.objects.filter(aspirante=self.alumno, periodo_inscripcion=periodo).count(), 4)

    def test_failed_required_course_can_be_retaken_in_four_course_next_period_load(self):
        self.alumno.numero_periodo_actual = 2
        self.alumno.save(update_fields=['numero_periodo_actual'])
        periodo_anterior = PeriodoInscripcion.objects.create(
            nombre='2025-cuatrimestre-1', apertura=timezone.now() - timedelta(days=120),
            cierre=timezone.now() - timedelta(days=60), activo=False,
        )
        periodo_actual = PeriodoInscripcion.objects.create(
            nombre='2025-cuatrimestre-2', apertura=timezone.now() - timedelta(days=1),
            cierre=timezone.now() + timedelta(days=30), activo=True,
        )
        configuracion = ConfiguracionPrograma.objects.create(
            programa='Ingeniería', grado='maestria', periodos_requeridos=6,
        )
        materias = [Materia.objects.create(clave=f'RET-{index:03d}', nombre=f'Materia de plan {index}') for index in range(1, 5)]
        PlanEstudioMateria.objects.create(configuracion=configuracion, materia=materias[0], periodo_sugerido=1)
        for materia in materias[1:]:
            PlanEstudioMateria.objects.create(configuracion=configuracion, materia=materia, periodo_sugerido=2)
        crear_carga_publicada(self.alumno, periodo_actual, materias)
        Inscripcion.objects.create(
            aspirante=self.alumno, materia=materias[0], periodo_inscripcion=periodo_anterior, calificacion=6,
        )
        self.client.force_authenticate(user=self.alumno)

        disponibles = self.client.get('/api/preregistro/materias/')
        self.assertEqual(disponibles.status_code, 200)
        self.assertEqual({item['id'] for item in disponibles.data}, {materia.id for materia in materias})

        response = self.client.post(
            '/api/preregistro/inscripciones/',
            {'materias': [materia.id for materia in materias]},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data), 4)
        self.assertEqual(Inscripcion.objects.filter(aspirante=self.alumno, materia=materias[0]).count(), 2)
        self.assertEqual(Inscripcion.objects.filter(aspirante=self.alumno, periodo_inscripcion=periodo_actual).count(), 4)

    def test_missing_plan_hides_courses_and_blocks_thesis_project(self):
        PeriodoInscripcion.objects.create(
            nombre='2026-sin-plan', apertura=timezone.now() - timedelta(days=1),
            cierre=timezone.now() + timedelta(days=30), activo=True,
        )
        materias_catalogo = [Materia.objects.create(clave=f'SINPLAN-{index}', nombre=f'Materia sin plan {index}') for index in range(1, 5)]
        self.client.force_authenticate(user=self.alumno)

        materias = self.client.get('/api/preregistro/materias/')
        intento_inscripcion = self.client.post(
            '/api/preregistro/inscripciones/',
            {'materias': [materia.id for materia in materias_catalogo]},
            format='json',
        )
        flujo = self.client.get('/api/tesis/flujo/')
        proyecto = self.client.post('/api/proyectos-tesis/', {
            'titulo': 'Proyecto de prueba', 'resumen': 'Resumen académico suficientemente extenso para prueba.',
        }, format='json')

        self.assertEqual(materias.status_code, 200)
        self.assertEqual(materias.data, [])
        self.assertEqual(intento_inscripcion.status_code, 409)
        self.assertEqual(Inscripcion.objects.filter(aspirante=self.alumno).count(), 0)
        self.assertEqual(flujo.status_code, 200)
        self.assertFalse(flujo.data['elegibilidad']['elegible'])
        self.assertEqual(proyecto.status_code, 400)

    def test_unassigned_academic_term_hides_courses_and_blocks_enrollment(self):
        PeriodoInscripcion.objects.create(
            nombre='2026-sin-semestre', apertura=timezone.now() - timedelta(days=1),
            cierre=timezone.now() + timedelta(days=30), activo=True,
        )
        configuracion = ConfiguracionPrograma.objects.create(
            programa='Ingeniería', grado='maestria', periodos_requeridos=4,
        )
        materias = [Materia.objects.create(clave=f'SINPERIODO-{index}', nombre=f'Materia sin ciclo {index}') for index in range(1, 5)]
        for materia in materias:
            PlanEstudioMateria.objects.create(configuracion=configuracion, materia=materia, periodo_sugerido=1)
        self.client.force_authenticate(user=self.alumno)

        disponibles = self.client.get('/api/preregistro/materias/')
        intento = self.client.post(
            '/api/preregistro/inscripciones/',
            {'materias': [materia.id for materia in materias]},
            format='json',
        )

        self.assertEqual(disponibles.status_code, 200)
        self.assertEqual(disponibles.data, [])
        self.assertEqual(intento.status_code, 409)
        self.assertEqual(Inscripcion.objects.filter(aspirante=self.alumno).count(), 0)

    def test_thesis_flow_unlocks_at_second_year_and_requires_mutual_director_match(self):
        configuracion = ConfiguracionPrograma.objects.create(
            programa='Ingeniería', grado='maestria', periodicidad='semestral', periodos_requeridos=4, creditos_requeridos=16,
        )
        materias = [Materia.objects.create(clave=f'TESIS-{index:03d}', nombre=f'Materia obligatoria {index}', creditos=4) for index in range(1, 5)]
        for materia in materias:
            PlanEstudioMateria.objects.create(configuracion=configuracion, materia=materia, periodo_sugerido=1)
        self.alumno.numero_periodo_actual = 3
        self.alumno.save(update_fields=['numero_periodo_actual'])
        director = Aspirante.objects.create_user(
            usuario='DIRECTOR_PLAN', correo='director.plan@example.com', password='password123',
            nombre='Director de Prueba', curp='DIRP850101HDFRNN01', telefono='5512345680',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 3',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 3',
            nombre_familiar='Familiar', parentesco='Padre', telefono_familiar='5512345681',
            ultimo_grado='Doctorado', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Computación', seccion='Posgrado', programa='Ingeniería',
            business_key='DIRECTOR-PLAN', rol='director',
        )
        self.client.force_authenticate(user=self.alumno)

        flujo = self.client.get('/api/tesis/flujo/')
        solicitud = self.client.post('/api/tesis/flujo/', {
            'director_sugerido': director.id,
            'linea_investigacion': 'Sistemas inteligentes',
            'justificacion': 'Propuesta de proyecto para iniciar el seguimiento de tesis.',
        }, format='json')

        self.assertEqual(flujo.status_code, 200)
        self.assertTrue(flujo.data['elegibilidad']['elegible'])
        self.assertEqual(flujo.data['elegibilidad']['resumen']['periodo_inicio_tesis'], 3)
        self.assertEqual(solicitud.status_code, 201)
        self.assertEqual(solicitud.data['estado'], 'pendiente_director')
        self.assertTrue(solicitud.data['alumno_acepto_director'])
        self.assertFalse(Inscripcion.objects.filter(aspirante=self.alumno).exists())

        self.client.force_authenticate(user=director)
        director_panel = self.client.get('/api/director/panel/')
        self.assertEqual(director_panel.status_code, 200)
        self.assertEqual([item['id'] for item in director_panel.data['solicitudes_direccion']], [solicitud.data['id']])
        aceptada = self.client.patch(
            f'/api/tesis/solicitudes/{solicitud.data["id"]}/',
            {'estado': 'aprobada'},
            format='json',
        )
        self.assertEqual(aceptada.status_code, 200)
        self.assertEqual(aceptada.data['estado'], 'aprobada')

        self.client.force_authenticate(user=self.alumno)
        proyecto = self.client.post('/api/proyectos-tesis/', {
            'titulo': 'Proyecto habilitado tras el match',
            'resumen': 'Resumen académico suficientemente extenso para el registro del proyecto.',
            'enviar_revision': True,
        }, format='json')
        self.assertEqual(proyecto.status_code, 201)

    def test_coordinated_director_assignment_requires_student_confirmation(self):
        self.alumno.numero_periodo_actual = 3
        self.alumno.save(update_fields=['numero_periodo_actual'])
        configuracion = ConfiguracionPrograma.objects.create(
            programa='Ingeniería', grado='maestria', periodicidad='semestral', periodos_requeridos=4,
        )
        materia = Materia.objects.create(clave='MATCH-COORD', nombre='Materia de primer año')
        PlanEstudioMateria.objects.create(configuracion=configuracion, materia=materia, periodo_sugerido=1)
        director = Aspirante.objects.create_user(
            usuario='DIRECTOR_COORD_MATCH', correo='director.coord.match@example.com', password='password123',
            nombre='Director Coordinado', curp='DCMT850101HDFRNN01', telefono='5512345684',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 5',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 5',
            nombre_familiar='Familiar', parentesco='Padre', telefono_familiar='5512345685',
            ultimo_grado='Doctorado', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Computación', seccion='Posgrado', programa='Ingeniería',
            business_key='DIRECTOR-COORD-MATCH', rol='director',
        )
        self.client.force_authenticate(user=self.alumno)
        solicitud = self.client.post('/api/tesis/flujo/', {
            'linea_investigacion': 'Sistemas inteligentes',
            'justificacion': 'Propuesta sin director sugerido para asignación institucional.',
        }, format='json')
        coordinacion = Aspirante.objects.create_superuser(
            usuario='COORD_MATCH_2', correo='coord.match.2@example.com', password='password123',
            rol='coordinacion', curp='CMAT850101HDFRNN02', business_key='COORD-MATCH-2',
        )
        self.client.force_authenticate(user=coordinacion)
        asignada = self.client.patch(
            f'/api/tesis/solicitudes/{solicitud.data["id"]}/',
            {'estado': 'aprobada', 'director_asignado': director.id},
            format='json',
        )
        self.assertEqual(asignada.status_code, 200)
        self.assertFalse(asignada.data['alumno_acepto_director'])
        self.assertEqual(asignada.data['estado'], 'pendiente_director')

        self.client.force_authenticate(user=director)
        aceptada = self.client.patch(
            f'/api/tesis/solicitudes/{solicitud.data["id"]}/',
            {'estado': 'aprobada'},
            format='json',
        )
        self.assertEqual(aceptada.status_code, 200)
        self.assertEqual(aceptada.data['estado'], 'pendiente_alumno')

        self.client.force_authenticate(user=self.alumno)
        confirmada = self.client.patch(
            f'/api/tesis/solicitudes/{solicitud.data["id"]}/',
            {'estado': 'aprobada'},
            format='json',
        )
        self.assertEqual(confirmada.status_code, 200)
        self.assertEqual(confirmada.data['estado'], 'aprobada')
        self.alumno.refresh_from_db()
        self.assertEqual(self.alumno.director_tesis_id, director.id)

    def test_thesis_stage_uses_term_count_for_semesters_and_quarters(self):
        for periodicidad, periodos_por_anio in [('semestral', 2), ('cuatrimestral', 3)]:
            with self.subTest(periodicidad=periodicidad):
                programa = f'Programa {periodicidad}'
                self.alumno.programa = programa
                self.alumno.numero_periodo_actual = periodos_por_anio
                self.alumno.save(update_fields=['programa', 'numero_periodo_actual'])
                configuracion = ConfiguracionPrograma.objects.create(
                    programa=programa, grado='maestria', periodicidad=periodicidad,
                    periodos_requeridos=periodos_por_anio * 2,
                )
                materia = Materia.objects.create(clave=f'ETAPA-{periodicidad}', nombre='Materia de primer año')
                PlanEstudioMateria.objects.create(configuracion=configuracion, materia=materia, periodo_sugerido=1)
                self.client.force_authenticate(user=self.alumno)
                antes = self.client.get('/api/tesis/flujo/')
                self.assertFalse(antes.data['elegibilidad']['elegible'])
                self.assertEqual(antes.data['elegibilidad']['resumen']['etapa'], 'por_iniciar')

                self.alumno.numero_periodo_actual = periodos_por_anio + 1
                self.alumno.save(update_fields=['numero_periodo_actual'])
                segundo_anio = self.client.get('/api/tesis/flujo/')
                self.assertTrue(segundo_anio.data['elegibilidad']['elegible'])
                self.assertEqual(segundo_anio.data['elegibilidad']['resumen']['etapa'], 'iniciada')

    def test_seminar_enrollment_requires_a_mutual_thesis_match(self):
        self.alumno.numero_periodo_actual = 3
        self.alumno.save(update_fields=['numero_periodo_actual'])
        periodo = PeriodoInscripcion.objects.create(
            nombre='Seminario match', apertura=timezone.now() - timedelta(days=1),
            cierre=timezone.now() + timedelta(days=30), activo=True,
        )
        configuracion = ConfiguracionPrograma.objects.create(
            programa='Ingeniería', grado='maestria', periodicidad='semestral', periodos_requeridos=4,
        )
        materias = [
            Materia.objects.create(clave=f'MATCH-{index}', nombre=f'Materia {index}', categoria='seminario' if index == 4 else 'formativo')
            for index in range(1, 5)
        ]
        for materia in materias:
            PlanEstudioMateria.objects.create(configuracion=configuracion, materia=materia, periodo_sugerido=3)
        crear_carga_publicada(self.alumno, periodo, materias)
        self.client.force_authenticate(user=self.alumno)

        disponibles_sin_match = self.client.get('/api/preregistro/materias/')
        self.assertNotIn(materias[3].id, [item['id'] for item in disponibles_sin_match.data])
        bloqueada = self.client.post(
            '/api/preregistro/inscripciones/',
            {'materias': [materia.id for materia in materias]},
            format='json',
        )
        self.assertEqual(bloqueada.status_code, 403)
        self.assertFalse(Inscripcion.objects.filter(aspirante=self.alumno).exists())

        director = Aspirante.objects.create_user(
            usuario='DIRECTOR_SEMINARIO', correo='director.seminario@example.com', password='password123',
            nombre='Director Seminario', curp='DSEM850101HDFRNN01', telefono='5512345682',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 4',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 4',
            nombre_familiar='Familiar', parentesco='Padre', telefono_familiar='5512345683',
            ultimo_grado='Doctorado', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Computación', seccion='Posgrado', programa='Ingeniería',
            business_key='DIRECTOR-SEMINARIO', rol='director',
        )
        SolicitudDireccionTesis.objects.create(
            alumno=self.alumno, director_asignado=director, alumno_acepto_director=True,
            director_acepto=True, estado='aprobada',
        )
        self.alumno.director_tesis = director
        self.alumno.save(update_fields=['director_tesis', 'updated_at'])

        disponibles_con_match = self.client.get('/api/preregistro/materias/')
        self.assertIn(materias[3].id, [item['id'] for item in disponibles_con_match.data])
        inscritas = self.client.post(
            '/api/preregistro/inscripciones/',
            {'materias': [materia.id for materia in materias]},
            format='json',
        )
        self.assertEqual(inscritas.status_code, 201)
        self.assertEqual(Inscripcion.objects.filter(aspirante=self.alumno, materia=materias[3]).count(), 1)

    def test_thesis_stays_locked_when_plan_has_no_required_thresholds(self):
        configuracion = ConfiguracionPrograma.objects.create(
            programa='Ingeniería', grado='maestria', periodos_requeridos=0, creditos_requeridos=0,
        )
        materia = Materia.objects.create(clave='TESIS-OPT', nombre='Optativa solamente')
        PlanEstudioMateria.objects.create(configuracion=configuracion, materia=materia, obligatoria=False)
        self.client.force_authenticate(user=self.alumno)

        response = self.client.get('/api/tesis/flujo/')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['elegibilidad']['elegible'])
        self.assertTrue(response.data['elegibilidad']['motivos'])


class SolicitudAcademicaWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.alumno = Aspirante.objects.create_user(
            usuario='ALUMNO_SOL_ACAD', correo='alumno.sol.acad@example.com', password='password123',
            nombre='Alumno Solicitudes', curp='SACA850101HDFRNN01', telefono='5512345678',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 1',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 1',
            nombre_familiar='Familiar', parentesco='Padre', telefono_familiar='5511111111',
            ultimo_grado='Licenciatura', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Academia', seccion='Posgrado', programa='Ingeniería',
            business_key='ALUMNO-SOL-ACAD', rol='alumno',
        )
        self.servicios = Aspirante.objects.create_superuser(
            usuario='SERV_SOL_ACAD', correo='serv.sol.acad@example.com', password='password123',
            rol='servicios', curp='SACA850101HDFRNN02', business_key='SERV-SOL-ACAD',
        )
        self.coordinacion = Aspirante.objects.create_superuser(
            usuario='COORD_SOL_ACAD', correo='coord.sol.acad@example.com', password='password123',
            rol='coordinacion', curp='SACA850101HDFRNN03', business_key='COORD-SOL-ACAD',
        )

    @patch('preregistro.views._registrar_seguimiento')
    def test_student_creates_request_and_cannot_duplicate_pending_type(self, registrar_seguimiento):
        self.client.force_authenticate(user=self.alumno)
        invalid = self.client.post('/api/preregistro/solicitudes-academicas/', {
            'tipo': 'historial', 'comentario': 'Hola',
        }, format='json')
        self.assertEqual(invalid.status_code, 400)

        created = self.client.post('/api/preregistro/solicitudes-academicas/', {
            'tipo': 'historial', 'comentario': 'Solicito mi historial académico del ciclo actual.',
        }, format='json')
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['estado'], 'pendiente')
        self.assertEqual(created.data['respuesta_revision'], '')
        registrar_seguimiento.assert_called_once()

        duplicate = self.client.post('/api/preregistro/solicitudes-academicas/', {
            'tipo': 'historial', 'comentario': 'Solicito nuevamente el historial académico.',
        }, format='json')
        self.assertEqual(duplicate.status_code, 409)

    @patch('preregistro.views._registrar_seguimiento')
    def test_review_routing_response_and_student_follow_up(self, registrar_seguimiento):
        historial = SolicitudAcademica.objects.create(
            aspirante=self.alumno, tipo='historial', comentario='Solicito historial académico.',
        )
        ajuste = SolicitudAcademica.objects.create(
            aspirante=self.alumno, tipo='ajuste_materias', comentario='Solicito ajustar mi carga académica.',
        )

        self.client.force_authenticate(user=self.servicios)
        queue = self.client.get('/api/preregistro/solicitudes-academicas/')
        self.assertEqual([item['id'] for item in queue.data], [historial.id])
        denied = self.client.patch(
            f'/api/preregistro/solicitudes-academicas/{ajuste.id}/',
            {'estado': 'aceptado', 'respuesta_revision': 'Ajuste autorizado.'},
            format='json',
        )
        self.assertEqual(denied.status_code, 404)

        self.client.force_authenticate(user=self.coordinacion)
        missing_response = self.client.patch(
            f'/api/preregistro/solicitudes-academicas/{ajuste.id}/',
            {'estado': 'aceptado', 'respuesta_revision': '   '},
            format='json',
        )
        self.assertEqual(missing_response.status_code, 400)
        accepted = self.client.patch(
            f'/api/preregistro/solicitudes-academicas/{ajuste.id}/',
            {'estado': 'aceptado', 'respuesta_revision': 'Ajuste autorizado para el siguiente periodo.'},
            format='json',
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.data['estado'], 'aceptado')
        self.assertEqual(accepted.data['respuesta_revision'], 'Ajuste autorizado para el siguiente periodo.')
        self.assertEqual(accepted.data['resuelta_por_nombre'], self.coordinacion.nombre)
        registrar_seguimiento.assert_called_once()
        self.assertLess(len(registrar_seguimiento.call_args.args[2]), 255)

        self.client.force_authenticate(user=self.alumno)
        own_requests = self.client.get('/api/preregistro/solicitudes-academicas/')
        detalle = next(item for item in own_requests.data if item['id'] == ajuste.id)
        self.assertEqual(detalle['respuesta_revision'], accepted.data['respuesta_revision'])

        repeated_resolution = self.client.patch(
            f'/api/preregistro/solicitudes-academicas/{ajuste.id}/',
            {'estado': 'rechazado', 'respuesta_revision': 'No autorizado.'},
            format='json',
        )
        self.assertEqual(repeated_resolution.status_code, 403)


class PeriodoInscripcionCoordinacionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.coordinacion = Aspirante.objects.create_superuser(
            usuario='SERV_PERIODO', correo='serv.periodo@example.com', password='password123', rol='servicios',
        )
        self.client.force_authenticate(user=self.coordinacion)

    def fechas_futuras(self, inicio=14, fin=30):
        return {
            'apertura': (timezone.now() + timedelta(days=inicio)).isoformat(),
            'cierre': (timezone.now() + timedelta(days=fin)).isoformat(),
        }

    def test_create_and_get_distinguish_enabled_from_currently_open(self):
        response = self.client.post('/api/periodos-inscripcion/', {
            'nombre': 'Inscripción futura', **self.fechas_futuras(), 'activo': True,
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['habilitado'])
        self.assertFalse(response.data['activo'])

        current = self.client.get('/api/periodos-inscripcion/')
        self.assertEqual(current.status_code, 200)
        self.assertEqual(current.data['id'], response.data['id'])
        self.assertTrue(current.data['habilitado'])
        self.assertFalse(current.data['activo'])

    def test_create_accepts_local_datetime_values_from_datetime_local_inputs(self):
        ahora_local = timezone.localtime(timezone.now())
        apertura = (ahora_local + timedelta(days=10)).strftime('%Y-%m-%dT%H:%M')
        cierre = (ahora_local + timedelta(days=20)).strftime('%Y-%m-%dT%H:%M')

        response = self.client.post('/api/periodos-inscripcion/', {
            'nombre': 'Periodo desde formulario local',
            'apertura': apertura,
            'cierre': cierre,
            'activo': True,
        }, format='json')

        self.assertEqual(response.status_code, 201)
        periodo = PeriodoInscripcion.objects.get(pk=response.data['id'])
        self.assertEqual(timezone.localtime(periodo.apertura).strftime('%Y-%m-%dT%H:%M'), apertura)
        self.assertEqual(timezone.localtime(periodo.cierre).strftime('%Y-%m-%dT%H:%M'), cierre)

    def test_coordinator_can_list_all_periods_for_editing(self):
        anterior = PeriodoInscripcion.objects.create(
            nombre='Agosto - Diciembre', apertura=timezone.now() - timedelta(days=20),
            cierre=timezone.now() - timedelta(days=5), activo=True,
        )
        reciente = PeriodoInscripcion.objects.create(
            nombre='Enero - Junio', apertura=timezone.now() + timedelta(days=100),
            cierre=timezone.now() + timedelta(days=110), activo=True,
        )

        response = self.client.get('/api/periodos-inscripcion/?todos=1')

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.data], [reciente.id, anterior.id])
        self.assertTrue(all('habilitado' in item and 'activo' in item for item in response.data))

    def test_coordinator_can_update_existing_period(self):
        periodo = PeriodoInscripcion.objects.create(
            nombre='Periodo modificable',
            apertura=timezone.now() + timedelta(days=5),
            cierre=timezone.now() + timedelta(days=20),
            activo=True,
        )

        response = self.client.put('/api/periodos-inscripcion/', {
            'id': periodo.id, 'nombre': 'Periodo corregido', **self.fechas_futuras(40, 60), 'activo': False,
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['nombre'], 'Periodo corregido')
        self.assertFalse(response.data['habilitado'])
        periodo.refresh_from_db()
        self.assertEqual(periodo.nombre, 'Periodo corregido')
        self.assertFalse(periodo.activo)

    def test_period_update_rejects_overlap_without_changing_existing_values(self):
        ahora = timezone.now()
        periodo = PeriodoInscripcion.objects.create(
            nombre='Periodo original', apertura=ahora + timedelta(days=10),
            cierre=ahora + timedelta(days=20), activo=True,
        )
        PeriodoInscripcion.objects.create(
            nombre='Periodo ocupado', apertura=ahora + timedelta(days=30),
            cierre=ahora + timedelta(days=50), activo=True,
        )

        response = self.client.put('/api/periodos-inscripcion/', {
            'id': periodo.id, 'nombre': 'Periodo original', **self.fechas_futuras(35, 45), 'activo': True,
        }, format='json')

        self.assertEqual(response.status_code, 409)
        periodo.refresh_from_db()
        self.assertEqual(periodo.apertura, ahora + timedelta(days=10))

    def test_student_cannot_update_enrollment_period(self):
        alumno = Aspirante.objects.create_user(
            usuario='ALUMNO_PERIODO', correo='alumno.periodo@example.com', password='password123',
            nombre='Alumno Periodo', curp='PERI850101HDFRNN01', telefono='5512345678',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 1',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 1',
            nombre_familiar='Familiar', parentesco='Padre', telefono_familiar='5511111111',
            ultimo_grado='Licenciatura', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Academia', seccion='Posgrado', programa='Ingeniería',
            business_key='ALUMNO-PERIODO', rol='alumno',
        )
        periodo = PeriodoInscripcion.objects.create(
            nombre='Periodo protegido', apertura=timezone.now() + timedelta(days=10),
            cierre=timezone.now() + timedelta(days=25), activo=True,
        )
        self.client.force_authenticate(user=alumno)

        lista = self.client.get('/api/periodos-inscripcion/?todos=1')
        response = self.client.put('/api/periodos-inscripcion/', {
            'id': periodo.id, 'nombre': 'Cambio no autorizado', **self.fechas_futuras(), 'activo': True,
        }, format='json')

        self.assertEqual(lista.status_code, 403)
        self.assertEqual(response.status_code, 403)
        periodo.refresh_from_db()
        self.assertEqual(periodo.nombre, 'Periodo protegido')

    def test_coordinacion_cannot_list_or_manage_enrollment_periods(self):
        periodo = PeriodoInscripcion.objects.create(
            nombre='Periodo coordinación', apertura=timezone.now() + timedelta(days=10),
            cierre=timezone.now() + timedelta(days=25), activo=True,
        )
        coordinacion = Aspirante.objects.create_superuser(
            usuario='COORD_PERIODO_DENY', correo='coord.periodo.deny@example.com', password='password123',
            rol='coordinacion', curp='COOR000000HDF00002', business_key='COORD-PERIODO-DENY',
        )
        self.client.force_authenticate(user=coordinacion)
        listed = self.client.get('/api/periodos-inscripcion/?todos=1')
        created = self.client.post('/api/periodos-inscripcion/', {
            'nombre': 'Periodo no autorizado', **self.fechas_futuras(), 'activo': True,
        }, format='json')
        updated = self.client.put('/api/periodos-inscripcion/', {
            'id': periodo.id, 'nombre': 'Cambio no autorizado', **self.fechas_futuras(40, 60), 'activo': True,
        }, format='json')
        self.assertEqual(listed.status_code, 403)
        self.assertEqual(created.status_code, 403)
        self.assertEqual(updated.status_code, 403)
        periodo.refresh_from_db()
        self.assertEqual(periodo.nombre, 'Periodo coordinación')


class InscripcionExtemporaneaTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.coordinacion = Aspirante.objects.create_superuser(
            usuario='COORD_EXT', correo='coord.ext@example.com', password='password123', rol='coordinacion',
            curp='COOR850101HDFRNN01', business_key='COORD-EXT-TEST',
        )
        self.servicios = Aspirante.objects.create_superuser(
            usuario='SERV_EXT', correo='serv.ext@example.com', password='password123', rol='servicios',
            curp='SERV850101HDFRNN02', business_key='SERV-EXT-TEST',
        )
        self.alumno = Aspirante.objects.create_user(
            usuario='ALUMNO_EXT', correo='alumno.ext@example.com', password='password123',
            nombre='Alumno Extemporáneo', curp='EXT850101HDFRNN01', telefono='5512345678',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 1',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 1',
            nombre_familiar='Familiar', parentesco='Padre', telefono_familiar='5511111111',
            ultimo_grado='Licenciatura', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Academia', seccion='Posgrado', programa='Programa Ext', business_key='ALUMNO-EXT',
            rol='alumno', numero_periodo_actual=1,
        )
        self.periodo = PeriodoInscripcion.objects.create(
            nombre='Periodo cerrado ext', apertura=timezone.now() - timedelta(days=30),
            cierre=timezone.now() - timedelta(days=1), activo=True,
        )
        self.configuracion = ConfiguracionPrograma.objects.create(
            programa='Programa Ext', grado='maestria', periodos_requeridos=1, creditos_requeridos=16,
        )
        self.materias = [
            Materia.objects.create(clave=f'EXT-{index}', nombre=f'Materia ext {index}')
            for index in range(1, 5)
        ]
        PlanEstudioMateria.objects.bulk_create([
            PlanEstudioMateria(configuracion=self.configuracion, materia=materia, periodo_sugerido=1)
            for materia in self.materias
        ])
        crear_carga_publicada(self.coordinacion, self.periodo, self.materias)
        self.client.force_authenticate(user=self.coordinacion)
        self.url = f'/api/coordinacion/alumnos/{self.alumno.id}/inscripciones-extemporaneas/'

    def test_staff_admin_with_default_role_can_load_enrollment_periods(self):
        self.coordinacion.rol = 'aspirante'
        self.coordinacion.save(update_fields=['rol'])

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([periodo['id'] for periodo in response.data['periodos']], [self.periodo.id])

    def test_submits_extemporaneous_enrollment_request_for_school_services_review(self):
        available = self.client.get(f'{self.url}?periodo={self.periodo.id}')
        self.assertEqual(available.status_code, 200)
        self.assertEqual(len(available.data['materias']), 4)

        response = self.client.post(self.url, {
            'periodo_inscripcion': self.periodo.id,
            'materias': [self.materias[0].id, self.materias[2].id],
            'motivo': 'El alumno se incorporó a mitad del periodo.',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['estado'], 'pendiente')
        self.assertEqual(len(response.data['materias']), 2)
        self.assertEqual(Inscripcion.objects.filter(aspirante=self.alumno).count(), 0)
        solicitud = SolicitudInscripcionExtemporanea.objects.get(pk=response.data['id'])
        self.assertEqual(solicitud.solicitante, self.coordinacion)
        self.assertEqual(solicitud.motivo, 'El alumno se incorporó a mitad del periodo.')
        oficio_url = f'/api/coordinacion/solicitudes-extemporaneas/{solicitud.id}/oficio/'
        oficio_pendiente = self.client.get(oficio_url)
        self.assertEqual(oficio_pendiente.status_code, 409)
        duplicada = self.client.post(self.url, {
            'periodo_inscripcion': self.periodo.id,
            'materias': [self.materias[0].id],
            'motivo': 'Intento duplicado.',
        }, format='json')
        self.assertEqual(duplicada.status_code, 409)

        self.client.force_authenticate(user=self.servicios)
        pendientes = self.client.get('/api/servicios-escolares/solicitudes-extemporaneas/')
        self.assertEqual(pendientes.status_code, 200)
        self.assertEqual([item['id'] for item in pendientes.data], [solicitud.id])
        aprobada = self.client.patch(
            f'/api/servicios-escolares/solicitudes-extemporaneas/{solicitud.id}/',
            {'estado': 'aprobada'},
            format='json',
        )
        self.assertEqual(aprobada.status_code, 200)
        self.assertEqual(aprobada.data['estado'], 'aprobada')
        self.assertEqual(Inscripcion.objects.filter(aspirante=self.alumno).count(), 2)
        self.assertTrue(Inscripcion.objects.filter(aspirante=self.alumno, extemporanea=True, validacion_servicios='validada').exists())

        oficio = self.client.get(f'/api/servicios-escolares/solicitudes-extemporaneas/{solicitud.id}/oficio/')
        self.assertEqual(oficio.status_code, 200)
        self.assertEqual(oficio['Content-Type'], 'application/pdf')
        self.client.force_authenticate(user=self.coordinacion)
        oficio_coordinacion = self.client.get(oficio_url)
        self.assertEqual(oficio_coordinacion.status_code, 200)
        self.assertEqual(oficio_coordinacion['Content-Type'], 'application/pdf')
        solicitudes_alumno = self.client.get(f'{self.url}?periodo={self.periodo.id}')
        self.assertEqual(solicitudes_alumno.data['solicitudes'][0]['estado'], 'aprobada')

    def test_rejected_extemporaneous_request_requires_a_comment_and_does_not_enroll(self):
        response = self.client.post(self.url, {
            'periodo_inscripcion': self.periodo.id,
            'materias': [self.materias[0].id],
            'motivo': 'Solicitud por incorporación tardía.',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.client.force_authenticate(user=self.servicios)
        url = f"/api/servicios-escolares/solicitudes-extemporaneas/{response.data['id']}/"
        sin_comentario = self.client.patch(url, {'estado': 'rechazada'}, format='json')
        self.assertEqual(sin_comentario.status_code, 400)
        rechazada = self.client.patch(url, {
            'estado': 'rechazada', 'comentario_revision': 'Falta documentación de respaldo.',
        }, format='json')
        self.assertEqual(rechazada.status_code, 200)
        self.assertEqual(rechazada.data['estado'], 'rechazada')
        self.assertEqual(Inscripcion.objects.filter(aspirante=self.alumno).count(), 0)
        oficio = self.client.get(f"{url}oficio/")
        self.assertEqual(oficio.status_code, 409)

    def test_extemporaneous_enrollment_requires_reason_and_available_seat(self):
        without_reason = self.client.post(self.url, {
            'periodo_inscripcion': self.periodo.id,
            'materias': [self.materias[0].id],
        }, format='json')
        self.assertEqual(without_reason.status_code, 400)

        sin_cupo = Materia.objects.create(clave='EXT-LLENA', nombre='Materia sin cupo')
        PlanEstudioMateria.objects.create(configuracion=self.configuracion, materia=sin_cupo, periodo_sugerido=1)
        crear_carga_publicada(self.coordinacion, self.periodo, [sin_cupo], {sin_cupo.id: 0})
        full = self.client.post(self.url, {
            'periodo_inscripcion': self.periodo.id,
            'materias': [sin_cupo.id],
            'motivo': 'Ingreso fuera de fecha.',
        }, format='json')
        self.assertEqual(full.status_code, 409)
        self.assertFalse(Inscripcion.objects.filter(aspirante=self.alumno).exists())

    def test_extemporaneous_enrollment_still_requires_a_subject_in_the_student_plan(self):
        fuera_plan = Materia.objects.create(clave='EXT-FUERA', nombre='Materia fuera del plan')
        crear_carga_publicada(self.coordinacion, self.periodo, [fuera_plan])
        response = self.client.post(self.url, {
            'periodo_inscripcion': self.periodo.id,
            'materias': [fuera_plan.id],
            'motivo': 'Solicitud especial.',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Inscripcion.objects.filter(aspirante=self.alumno).exists())


class InscripcionCoordinacionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.coordinacion = Aspirante.objects.create_superuser(
            usuario='COORD_REG', correo='coord.reg@example.com', password='password123', rol='coordinacion',
            curp='COOR860101HDFRNN01', business_key='COORD-REG-TEST',
        )
        self.servicios = Aspirante.objects.create_superuser(
            usuario='SERV_REG', correo='serv.reg@example.com', password='password123', rol='servicios',
            curp='SERV860101HDFRNN02', business_key='SERV-REG-TEST',
        )
        self.alumno = Aspirante.objects.create_user(
            usuario='ALUMNO_REG', correo='alumno.reg@example.com', password='password123',
            nombre='Alumno Regular', curp='REG860101HDFRNN01', telefono='5512345678',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 1',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 1',
            nombre_familiar='Familiar', parentesco='Padre', telefono_familiar='5511111111',
            ultimo_grado='Licenciatura', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Academia', seccion='Posgrado', programa='Programa Regular', business_key='ALUMNO-REG',
            rol='alumno', numero_periodo_actual=1,
        )
        self.periodo = PeriodoInscripcion.objects.create(
            nombre='Periodo regular abierto', apertura=timezone.now() - timedelta(days=1),
            cierre=timezone.now() + timedelta(days=5), activo=True,
        )
        self.configuracion = ConfiguracionPrograma.objects.create(
            programa='Programa Regular', grado='maestria', periodos_requeridos=1, creditos_requeridos=16,
        )
        self.materias = [
            Materia.objects.create(clave=f'REG-{index}', nombre=f'Materia regular {index}')
            for index in range(1, 5)
        ]
        PlanEstudioMateria.objects.bulk_create([
            PlanEstudioMateria(configuracion=self.configuracion, materia=materia, periodo_sugerido=1)
            for materia in self.materias
        ])
        crear_carga_publicada(self.coordinacion, self.periodo, self.materias)
        self.client.force_authenticate(user=self.coordinacion)
        self.url = f'/api/coordinacion/alumnos/{self.alumno.id}/inscripciones-regulares/'

    def test_coordinacion_registers_four_regular_courses_during_open_period(self):
        disponibles = self.client.get(self.url)
        self.assertEqual(disponibles.status_code, 200)
        self.assertEqual(disponibles.data['periodo']['id'], self.periodo.id)
        self.assertEqual(disponibles.data['faltantes'], 4)
        self.assertEqual(len(disponibles.data['materias']), 4)

        response = self.client.post(self.url, {'materias': [materia.id for materia in self.materias]}, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data['registradas']), 4)
        self.assertEqual(Inscripcion.objects.filter(aspirante=self.alumno, periodo_inscripcion=self.periodo).count(), 4)
        inscripcion = Inscripcion.objects.get(aspirante=self.alumno, materia=self.materias[0])
        self.assertFalse(inscripcion.extemporanea)
        self.assertEqual(inscripcion.validacion_servicios, 'pendiente')
        self.assertEqual(inscripcion.registrada_por, self.coordinacion)

    def test_regular_registration_is_unavailable_when_period_is_closed(self):
        self.periodo.cierre = timezone.now() - timedelta(minutes=1)
        self.periodo.save(update_fields=['cierre'])

        disponibles = self.client.get(self.url)
        response = self.client.post(self.url, {'materias': [materia.id for materia in self.materias]}, format='json')

        self.assertIsNone(disponibles.data['periodo'])
        self.assertEqual(response.status_code, 409)
        self.assertFalse(Inscripcion.objects.filter(aspirante=self.alumno).exists())

    def test_regular_registration_requires_exactly_the_remaining_courses(self):
        response = self.client.post(self.url, {'materias': [self.materias[0].id]}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Inscripcion.objects.filter(aspirante=self.alumno).exists())

    def test_regular_registration_completes_only_the_courses_still_missing(self):
        Inscripcion.objects.create(
            aspirante=self.alumno,
            materia=self.materias[0],
            periodo_inscripcion=self.periodo,
        )

        disponibles = self.client.get(self.url)
        response = self.client.post(self.url, {'materias': [materia.id for materia in self.materias[1:]]}, format='json')

        self.assertEqual(disponibles.data['faltantes'], 3)
        self.assertEqual([materia['id'] for materia in disponibles.data['materias']], [materia.id for materia in self.materias[1:]])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Inscripcion.objects.filter(aspirante=self.alumno, periodo_inscripcion=self.periodo).count(), 4)

    def test_school_services_cannot_use_the_coordination_regular_enrollment_endpoint(self):
        self.client.force_authenticate(user=self.servicios)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_formal_regular_slip_requires_services_validation_and_is_downloadable_by_coordination(self):
        Inscripcion.objects.bulk_create([
            Inscripcion(aspirante=self.alumno, materia=materia, periodo_inscripcion=self.periodo)
            for materia in self.materias
        ])
        url = f'{self.url}boleta/?periodo={self.periodo.id}'

        pending = self.client.get(url)
        self.assertEqual(pending.status_code, 409)

        Inscripcion.objects.filter(aspirante=self.alumno, periodo_inscripcion=self.periodo).update(validacion_servicios='validada')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('boleta_inscripcion_regular.pdf', response['Content-Disposition'])

        self.client.force_authenticate(user=self.servicios)
        forbidden = self.client.get(url)
        self.assertEqual(forbidden.status_code, 403)


class CoordinationSubjectCatalogPermissionsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.coordinacion = Aspirante.objects.create_superuser(
            usuario='COORD_CATALOG', correo='coord.catalog@example.com', password='password123', rol='coordinacion',
            curp='CCAT850101HDFRNN01', business_key='COORD-CATALOG-TEST',
        )
        self.servicios = Aspirante.objects.create_superuser(
            usuario='SERV_CATALOG', correo='serv.catalog@example.com', password='password123', rol='servicios',
            curp='SCAT850101HDFRNN02', business_key='SERV-CATALOG-TEST',
        )

    def test_coordination_can_consult_catalog(self):
        materia = Materia.objects.create(clave='CAT-001', nombre='Materia de consulta')
        self.client.force_authenticate(user=self.coordinacion)

        response = self.client.get('/api/coordinacion/materias/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.data], [materia.id])

    def test_staff_member_can_consult_catalog_without_superuser_status(self):
        staff_member = Aspirante.objects.create_superuser(
            usuario='STAFF_CATALOG', correo='staff.catalog@example.com', password='password123',
            curp='STFC850101HDFRNN03', business_key='STAFF-CATALOG-TEST',
        )
        staff_member.is_superuser = False
        staff_member.save(update_fields=['is_superuser'])
        self.client.force_authenticate(user=staff_member)

        response = self.client.get('/api/coordinacion/materias/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_only_school_services_can_upload_subject_catalog(self):
        upload = lambda: self.client.post(
            '/api/coordinacion/cursos/upload/',
            {'file': SimpleUploadedFile('materias.csv', b'clave,nombre\nCAT-002,Materia nueva\n', content_type='text/csv')},
            format='multipart',
        )
        self.client.force_authenticate(user=self.coordinacion)

        denied = upload()
        self.assertEqual(denied.status_code, 403)
        self.assertFalse(Materia.objects.filter(clave='CAT-002').exists())

        self.client.force_authenticate(user=self.servicios)
        allowed = upload()
        self.assertEqual(allowed.status_code, 200)
        self.assertTrue(Materia.objects.filter(clave='CAT-002').exists())


class AdminUsuariosCRUDTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = Aspirante.objects.create_superuser(
            usuario='ADMIN_CRUD', correo='admin.crud@example.com', password='password123',
        )
        self.client.force_authenticate(user=self.admin)

    def test_user_create_read_update_and_soft_delete(self):
        created = self.client.post('/api/administracion/usuarios/', {
            'name': 'Docente CRUD', 'usuario': 'DOC_CRUD', 'email': 'doc.crud@example.com',
            'password': 'Secure123', 'role': 'Director de Tesis', 'area': 'Computación', 'status': 'Activo',
        }, format='json')

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['rol'], 'director')
        self.assertTrue(created.data['is_active'])
        user_id = created.data['id']

        listed = self.client.get('/api/administracion/usuarios/')
        self.assertEqual(listed.status_code, 200)
        self.assertTrue(any(user['id'] == user_id for user in listed.data['usuarios']))

        updated = self.client.patch(f'/api/administracion/usuarios/{user_id}/', {
            'name': 'Docente actualizado', 'role': 'Docente', 'status': 'Inactivo', 'area': 'Computación aplicada',
        }, format='json')
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data['nombre'], 'Docente actualizado')
        self.assertEqual(updated.data['rol'], 'docente')
        self.assertEqual(updated.data['programa'], 'Computación aplicada')
        self.assertEqual(updated.data['departamento'], 'Computación aplicada')
        self.assertFalse(updated.data['is_active'])

        deleted = self.client.delete(f'/api/administracion/usuarios/{user_id}/')
        self.assertEqual(deleted.status_code, 200)
        user = Aspirante.objects.get(pk=user_id)
        self.assertFalse(user.is_active)
        listed_again = self.client.get('/api/administracion/usuarios/')
        self.assertTrue(any(item['id'] == user_id and not item['is_active'] for item in listed_again.data['usuarios']))

    def test_user_creation_rejects_password_outside_policy(self):
        response = self.client.post('/api/administracion/usuarios/', {
            'name': 'Usuario débil', 'usuario': 'WEAK_PASS', 'email': 'weak.pass@example.com',
            'password': 'password', 'role': 'Alumno', 'area': 'Computación', 'status': 'Activo',
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Aspirante.objects.filter(usuario='WEAK_PASS').exists())

    def test_user_creation_rejects_invalid_email_role_and_username(self):
        for username, email, role, active in (
            ('INVALID_EMAIL', 'not-an-email', 'Alumno', 'Activo'),
            ('INVALID_ROLE', 'valid@example.com', 'Unknown role', 'Activo'),
            ('u' * 21, 'long.username@example.com', 'Alumno', 'Activo'),
            ('INVALID_STATUS', 'invalid.status@example.com', 'Alumno', 'unknown'),
        ):
            with self.subTest(username=username, email=email, role=role, active=active):
                response = self.client.post('/api/administracion/usuarios/', {
                    'name': 'Registro inválido', 'usuario': username, 'email': email,
                    'password': 'Secure123', 'role': role, 'status': active,
                }, format='json')
                self.assertEqual(response.status_code, 400)

    def test_last_active_administrator_cannot_be_deactivated(self):
        updated = self.client.patch(
            f'/api/administracion/usuarios/{self.admin.id}/',
            {'name': 'Administrador actualizado'},
            format='json',
        )
        self.assertEqual(updated.status_code, 200)

        response = self.client.delete(f'/api/administracion/usuarios/{self.admin.id}/')

        self.assertEqual(response.status_code, 409)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)


class AdminAlumnosCRUDTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = Aspirante.objects.create_superuser(
            usuario='ADMIN_STUDENT_CRUD', correo='admin.student.crud@example.com', password='password123',
        )
        self.alumno = Aspirante.objects.create_user(
            usuario='STUDENT_CRUD', correo='student.crud@example.com', password='password123',
            nombre='Alumno CRUD', curp='CRUD850101HDFRNN01', telefono='5512345678',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 1',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 1',
            nombre_familiar='Familiar', parentesco='Padre', telefono_familiar='5511111111',
            ultimo_grado='Licenciatura', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Academia', seccion='Posgrado', programa='Ingeniería',
            business_key='STUDENT-CRUD', rol='alumno',
        )
        self.client.force_authenticate(user=self.admin)

    def test_student_read_update_and_deactivate(self):
        listed = self.client.get('/api/administracion/alumnos/')
        self.assertEqual(listed.status_code, 200)
        self.assertTrue(any(item['id'] == self.alumno.id for item in listed.data['alumnos']))

        detail = self.client.get(f'/api/administracion/alumnos/{self.alumno.id}/')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data['nombre'], 'Alumno CRUD')

        updated = self.client.patch(f'/api/administracion/alumnos/{self.alumno.id}/', {
            'programa': 'Ciencias de la Computación', 'matricula': 'M-2026-001', 'is_active': False,
        }, format='json')
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data['programa'], 'Ciencias de la Computación')
        self.assertEqual(updated.data['matricula'], 'M-2026-001')
        self.assertFalse(updated.data['is_active'])

        self.alumno.refresh_from_db()
        self.assertEqual(self.alumno.programa, 'Ciencias de la Computación')
        self.assertFalse(self.alumno.is_active)

    def test_student_update_rejects_matricula_longer_than_model_field(self):
        response = self.client.patch(
            f'/api/administracion/alumnos/{self.alumno.id}/',
            {'matricula': 'M' * 31},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.alumno.refresh_from_db()
        self.assertIsNone(self.alumno.matricula)


class AdminCatalogosMateriaTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = Aspirante.objects.create_superuser(
            usuario='ADMIN_CATALOGO', correo='admin.catalogo@example.com', password='password123',
        )
        self.client.force_authenticate(user=self.admin)

    def test_admin_can_save_course_room_and_capacity(self):
        response = self.client.post('/api/administracion/catalogos/', {
            'tipo': 'materia', 'clave': 'AULA-101', 'nombre': 'Curso con salón',
            'creditos': 5, 'salon': 'laboratorio_harold', 'capacidad': 24,
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['salon'], 'laboratorio_harold')
        self.assertEqual(response.data['capacidad'], 24)
        materia = Materia.objects.get(clave='AULA-101')
        self.assertEqual(materia.get_salon_display(), 'Laboratorio Harold V. McIntosh')

    def test_admin_cannot_save_unknown_course_room(self):
        response = self.client.post('/api/administracion/catalogos/', {
            'tipo': 'materia', 'clave': 'AULA-102', 'nombre': 'Curso sin salón válido',
            'salon': 'salon-inexistente',
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Materia.objects.filter(clave='AULA-102').exists())

    def test_saving_existing_course_key_updates_the_catalog_entry(self):
        Materia.objects.create(clave='AULA-103', nombre='Nombre anterior', creditos=4)

        response = self.client.post('/api/administracion/catalogos/', {
            'tipo': 'materia', 'clave': 'AULA-103', 'nombre': 'Nombre actualizado',
            'creditos': 7, 'salon': 'sala_juntas', 'capacidad': 18,
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Materia.objects.filter(clave='AULA-103').count(), 1)
        materia = Materia.objects.get(clave='AULA-103')
        self.assertEqual(materia.nombre, 'Nombre actualizado')
        self.assertEqual(materia.creditos, 7)
        self.assertEqual(materia.capacidad, 18)


class AdminConfiguracionCRUDTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = Aspirante.objects.create_superuser(
            usuario='ADMIN_CONFIG', correo='admin.config@example.com', password='password123',
        )
        self.client.force_authenticate(user=self.admin)

    def test_settings_read_and_update_are_persisted(self):
        initial = self.client.get('/api/administracion/configuracion/')
        self.assertEqual(initial.status_code, 200)
        self.assertIn('campus', initial.data)

        updated = self.client.put('/api/administracion/configuracion/', {
            'campus': 'Cinvestav Unidad Sur',
        }, format='json')
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data, {'campus': 'Cinvestav Unidad Sur'})

        refreshed = self.client.get('/api/administracion/configuracion/')
        self.assertEqual(refreshed.data['campus'], 'Cinvestav Unidad Sur')
        self.assertNotIn('clave_desconocida', refreshed.data)

    def test_security_settings_validate_and_persist_runtime_values(self):
        response = self.client.put('/api/administracion/configuracion/', {
            'politica_password': '12 caracteres, mayúscula y número',
            'bloqueo_intentos': '2',
            'notificaciones_activas': False,
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['bloqueo_intentos'], '2')
        self.assertEqual(response.data['notificaciones_activas'], 'false')
        refreshed = self.client.get('/api/administracion/configuracion/')
        self.assertEqual(refreshed.data['politica_password'], '12 caracteres, mayúscula y número')

    def test_invalid_security_settings_are_rejected_without_partial_saves(self):
        response = self.client.put('/api/administracion/configuracion/', {
            'bloqueo_intentos': '21',
            'notificaciones_activas': 'quizá',
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(ConfiguracionSistema.objects.filter(clave='bloqueo_intentos').exists())
        self.assertFalse(ConfiguracionSistema.objects.filter(clave='notificaciones_activas').exists())

    def test_password_policy_is_used_by_admin_password_updates(self):
        ConfiguracionSistema.objects.create(clave='politica_password', valor='12 caracteres, mayúscula y número')

        response = self.client.patch(f'/api/administracion/usuarios/{self.admin.id}/', {
            'password': 'Secure123',
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('política configurada', response.data['error'])


class AdminReportesAccuracyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        admin = Aspirante.objects.create_superuser(
            usuario='ADMIN_REPORTS', correo='admin.reports@example.com', password='password123',
        )
        self.client.force_authenticate(user=admin)

    def test_accepted_count_means_current_active_accepted_accounts(self):
        accepted = Aspirante.objects.create_user(
            usuario='OLD_ACCEPTED', correo='old.accepted@example.com', password='password123',
            nombre='Aceptado anteriormente', curp='OLDI850101HDFRNN01', telefono='5512345678',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 1',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 1',
            nombre_familiar='Familiar', parentesco='Padre', telefono_familiar='5511111111',
            ultimo_grado='Licenciatura', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Academia', seccion='Posgrado', programa='Ingeniería',
            business_key='OLD-ACCEPTED', rol='aspirante', proceso_estado='aceptado',
        )
        Aspirante.objects.filter(pk=accepted.pk).update(created_at=timezone.now() - timedelta(days=45))
        Aspirante.objects.create_user(
            usuario='NEW_PENDING', correo='new.pending@example.com', password='password123',
            nombre='Pendiente reciente', curp='NEWP850101HDFRNN01', telefono='5512345679',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 2',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 2',
            nombre_familiar='Familiar', parentesco='Padre', telefono_familiar='5511111112',
            ultimo_grado='Licenciatura', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Academia', seccion='Posgrado', programa='Ingeniería',
            business_key='NEW-PENDING', rol='aspirante', proceso_estado='pendiente',
        )

        response = self.client.get('/api/administracion/reportes/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['aspirantes_aceptados'], 1)


class PlanEstudioCoordinacionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        servicios = Aspirante.objects.create_superuser(
            usuario='SERV_PLAN', correo='serv.plan@example.com', password='password123', rol='servicios',
        )
        self.client.force_authenticate(user=servicios)

    def test_new_plans_default_period_count_from_degree_and_periodicity(self):
        configuraciones = [
            ('Maestría semestral', 'maestria', 'semestral', 4),
            ('Maestría cuatrimestral', 'maestria', 'cuatrimestral', 6),
            ('Doctorado semestral', 'doctorado', 'semestral', 8),
            ('Doctorado cuatrimestral', 'doctorado', 'cuatrimestral', 12),
        ]

        for programa, grado, periodicidad, periodos_esperados in configuraciones:
            with self.subTest(programa=programa):
                materias = [
                    Materia.objects.create(
                        clave=f'PER-{grado[:2].upper()}-{periodicidad[:2].upper()}-{index:02d}',
                        nombre=f'Materia {programa} {index}',
                    )
                    for index in range(periodos_esperados * 4)
                ]
                response = self.client.post('/api/tesis/flujo/', {
                    'programa': programa,
                    'grado': grado,
                    'periodicidad': periodicidad,
                    'materias_plan': [
                        {
                            'materia': materia.id,
                            'periodo_sugerido': index // 4 + 1,
                            'obligatoria': True,
                        }
                        for index, materia in enumerate(materias)
                    ],
                }, format='json')

                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.data['periodos_requeridos'], periodos_esperados)
                self.assertEqual(len(response.data['materias_plan']), periodos_esperados * 4)

    def test_plan_requires_four_courses_per_configured_period(self):
        materias = [Materia.objects.create(clave=f'FORM-{index:03d}', nombre=f'Materia formal {index}') for index in range(1, 9)]
        payload = {
            'programa': 'Maestría — Ciencias de la Computación (2 años)',
            'grado': 'maestria',
            'periodicidad': 'semestral',
            'periodos_requeridos': 2,
            'creditos_requeridos': 32,
            'materias_plan': [
                {'materia': materia.id, 'periodo_sugerido': 1 if index < 4 else 2, 'obligatoria': True}
                for index, materia in enumerate(materias[:7])
            ],
        }

        incompleto = self.client.post('/api/tesis/flujo/', payload, format='json')
        self.assertEqual(incompleto.status_code, 400)
        self.assertFalse(ConfiguracionPrograma.objects.filter(programa=payload['programa']).exists())

        payload['materias_plan'].append({'materia': materias[7].id, 'periodo_sugerido': 2, 'obligatoria': True})
        completo = self.client.post('/api/tesis/flujo/', payload, format='json')

        self.assertEqual(completo.status_code, 201)
        self.assertEqual(len(completo.data['materias_plan']), 8)

    def test_editing_plan_by_id_renames_instead_of_creating_duplicate(self):
        materias = [Materia.objects.create(clave=f'EDIT-{index:03d}', nombre=f'Materia editable {index}') for index in range(1, 5)]
        plan = self.client.post('/api/tesis/flujo/', {
            'programa': 'Programa original', 'grado': 'maestria', 'periodicidad': 'semestral',
            'periodos_requeridos': 1, 'creditos_requeridos': 16,
            'materias_plan': [{'materia': materia.id, 'periodo_sugerido': 1, 'obligatoria': True} for materia in materias],
        }, format='json')
        self.assertEqual(plan.status_code, 201)

        updated = self.client.post('/api/tesis/flujo/', {
            'id': plan.data['id'], 'programa': 'Programa actualizado', 'grado': 'maestria',
            'periodicidad': 'semestral', 'periodos_requeridos': 1, 'creditos_requeridos': 16,
            'activo': False,
            'materias_plan': [{'materia': materia.id, 'periodo_sugerido': 1, 'obligatoria': True} for materia in materias],
        }, format='json')

        self.assertEqual(updated.status_code, 201)
        self.assertEqual(updated.data['id'], plan.data['id'])
        self.assertEqual(updated.data['programa'], 'Programa actualizado')
        self.assertFalse(updated.data['activo'])
        self.assertEqual(ConfiguracionPrograma.objects.count(), 1)

    def test_plan_rejects_duplicate_course_ids(self):
        materias = [Materia.objects.create(clave=f'DUP-{index:03d}', nombre=f'Materia duplicada {index}') for index in range(1, 4)]
        repeated = materias[0]
        response = self.client.post('/api/tesis/flujo/', {
            'programa': 'Programa duplicado', 'grado': 'maestria', 'periodicidad': 'semestral',
            'periodos_requeridos': 1, 'creditos_requeridos': 12,
            'materias_plan': [
                {'materia': materias[0].id, 'periodo_sugerido': 1, 'obligatoria': True},
                {'materia': materias[1].id, 'periodo_sugerido': 1, 'obligatoria': True},
                {'materia': materias[2].id, 'periodo_sugerido': 1, 'obligatoria': True},
                {'materia': repeated.id, 'periodo_sugerido': 1, 'obligatoria': True},
            ],
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(ConfiguracionPrograma.objects.filter(programa='Programa duplicado').exists())

    def test_coordinacion_cannot_create_or_edit_plans(self):
        coordinacion = Aspirante.objects.create_superuser(
            usuario='COORD_PLAN_DENY', correo='coord.plan.deny@example.com', password='password123',
            rol='coordinacion', curp='COOR000000HDF00001', business_key='COORD-PLAN-DENY',
        )
        self.client.force_authenticate(user=coordinacion)
        listed = self.client.get('/api/tesis/flujo/')
        response = self.client.post('/api/tesis/flujo/', {
            'programa': 'Plan no autorizado',
            'grado': 'maestria',
            'periodicidad': 'semestral',
        }, format='json')
        self.assertEqual(listed.status_code, 200)
        self.assertNotIn('configuraciones', listed.data)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ConfiguracionPrograma.objects.filter(programa='Plan no autorizado').exists())


class AlertasAutomatizadasTests(TestCase):
    def setUp(self):
        self.alumno = Aspirante.objects.create_user(
            usuario='ALERTA01', correo='alerta@example.com', password='password123',
            nombre='Alumno Alertas', curp='ALRT850101HDFRNN01', telefono='5512345678',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 1',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 1',
            nombre_familiar='Familiar', parentesco='Padre', telefono_familiar='5511111111',
            ultimo_grado='Licenciatura', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Academia', seccion='Posgrado', programa='Ingeniería', business_key='ALERTA-01',
            rol='alumno', proceso_estado='baja', apoyo_solicitado=True,
        )
        PeriodoInscripcion.objects.create(
            nombre='Periodo de alerta', apertura=timezone.now() - timedelta(days=1),
            cierre=timezone.now() + timedelta(days=3), activo=True,
        )
        self.alumno_activo = Aspirante.objects.create_user(
            usuario='ALERTA02', correo='alerta.activo@example.com', password='password123',
            nombre='Alumno Vigente', curp='ALRV850101HDFRNN02', telefono='5512345679',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 2',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 2',
            nombre_familiar='Familiar', parentesco='Madre', telefono_familiar='5511111112',
            ultimo_grado='Licenciatura', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Academia', seccion='Posgrado', programa='Ingeniería', business_key='ALERTA-02',
            rol='alumno', proceso_estado='activo',
        )

    def test_generar_alertas_crea_baja_vencimiento_apertura_y_beca_sin_duplicados(self):
        resultado = generar_alertas_automatizadas()
        self.assertEqual(resultado['bajas'], 1)
        self.assertEqual(resultado['becas'], 1)
        self.assertEqual(resultado['vencimientos'], 1)
        self.assertEqual(resultado['aperturas'], 1)
        self.assertEqual(SeguimientoSolicitud.objects.filter(aspirante=self.alumno).count(), 2)
        self.assertEqual(SeguimientoSolicitud.objects.filter(aspirante=self.alumno_activo, estado='alerta_vencimiento').count(), 1)
        aviso_apertura = SeguimientoSolicitud.objects.get(aspirante=self.alumno_activo, estado='alerta_apertura_inscripcion')
        self.assertEqual(aviso_apertura.origen, 'Servicios Escolares')

        resultado_repetido = generar_alertas_automatizadas()
        self.assertEqual(resultado_repetido['total'], 0)

    def test_vencimiento_no_se_duplica_cuando_cambia_el_conteo_de_dias(self):
        ahora = timezone.now()
        with patch('preregistro.alertas.timezone.now', return_value=ahora):
            primero = generar_alertas_automatizadas()
        with patch('preregistro.alertas.timezone.now', return_value=ahora + timedelta(days=1)):
            segundo = generar_alertas_automatizadas()

        self.assertEqual(primero['vencimientos'], 1)
        self.assertEqual(segundo['vencimientos'], 0)
        self.assertEqual(primero['aperturas'], 1)
        self.assertEqual(segundo['aperturas'], 0)
        self.assertEqual(SeguimientoSolicitud.objects.filter(aspirante=self.alumno_activo, estado='alerta_vencimiento').count(), 1)
        self.assertEqual(SeguimientoSolicitud.objects.filter(aspirante=self.alumno_activo, estado='alerta_apertura_inscripcion').count(), 1)


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

    def test_staff_services_user_keeps_services_role(self):
        self.user.rol = 'servicios'
        self.user.is_staff = True
        self.user.save(update_fields=['rol', 'is_staff'])

        response = self.client.post('/api/auth/login/', {'usuario': 'DOCENTE01', 'password': 'password123'}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['role'], 'servicios')

    def test_failed_logins_lock_account_for_configured_duration_and_then_reset(self):
        ConfiguracionSistema.objects.create(clave='bloqueo_intentos', valor='2')
        login_time = timezone.now()

        with patch('preregistro.serializers.timezone.now', return_value=login_time):
            first_failure = self.client.post('/api/auth/login/', {'usuario': 'DOCENTE01', 'password': 'wrong'}, format='json')
            second_failure = self.client.post('/api/auth/login/', {'usuario': 'DOCENTE01', 'password': 'wrong'}, format='json')
        self.assertEqual(first_failure.status_code, 401)
        self.assertEqual(second_failure.status_code, 401)

        self.user.refresh_from_db()
        locked_until = self.user.login_locked_until
        self.assertIsNotNone(locked_until)
        self.assertEqual(locked_until, login_time + timedelta(minutes=15))
        self.assertEqual(self.user.login_failed_attempts, 2)
        locked_attempt = self.client.post('/api/auth/login/', {'usuario': 'DOCENTE01', 'password': 'password123'}, format='json')
        self.assertEqual(locked_attempt.status_code, 401)

        with patch('preregistro.serializers.timezone.now', return_value=locked_until + timedelta(seconds=1)):
            after_expiry = self.client.post('/api/auth/login/', {'usuario': 'DOCENTE01', 'password': 'password123'}, format='json')

        self.assertEqual(after_expiry.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.login_failed_attempts, 0)
        self.assertIsNone(self.user.login_locked_until)

    def test_password_policy_is_applied_to_public_registration(self):
        ConfiguracionSistema.objects.create(clave='politica_password', valor='12 caracteres, mayúscula y número')
        payload = {
            'nombre': 'Ana López', 'usuario': 'ANALOPEZ', 'curp': 'LOPA850101HDFRRR01',
            'correo': 'ana@example.com', 'telefono': '5512345678', 'nacimiento': '1985-01-01', 'password': 'Secure123',
            'estado_actual': 'Ciudad de México', 'municipio_actual': 'Coyoacán', 'direccion_actual': 'Calle 1',
            'estado_permanente': 'Ciudad de México', 'municipio_permanente': 'Coyoacán', 'direccion_permanente': 'Calle 1',
            'nombre_familiar': 'Juan López', 'parentesco': 'Padre', 'telefono_familiar': '5511111111',
            'ultimo_grado': 'Licenciatura', 'institucion': 'Cinvestav', 'unidad': 'Cinvestav',
            'departamento': 'Academia', 'seccion': 'Posgrado', 'programa': 'Ingeniería', 'modalidad': 'Presencial',
        }

        response = self.client.post('/api/preregistro/', payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data)
        self.assertFalse(Aspirante.objects.filter(usuario='ANALOPEZ').exists())


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


class InscripcionCupoYSalonTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.alumno = Aspirante.objects.create_user(
            usuario='CUPOS01', correo='cupos@example.com', password='password123',
            nombre='Alumno Cupo', curp='CUPO850101HDFRNN01', telefono='5512345678',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 1',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 1',
            nombre_familiar='Familiar', parentesco='Madre', telefono_familiar='5511111111',
            ultimo_grado='Licenciatura', institucion='Cinvestav', unidad='Cinvestav', departamento='Academia',
            seccion='Posgrado', programa='Ingeniería', business_key='CUPO-PRUEBA', rol='alumno',
        )
        self.materia = Materia.objects.create(clave='CUP-01', nombre='Materia con cupo', profesor='Docente', salon='salon_1', capacidad=42)
        self.periodo = PeriodoInscripcion.objects.create(nombre='Periodo cupo', apertura=timezone.now() - timedelta(days=1), cierre=timezone.now() + timedelta(days=5), activo=True)

    def test_materia_expone_salon_y_rechaza_cupo_lleno(self):
        self.alumno.numero_periodo_actual = 1
        self.alumno.save(update_fields=['numero_periodo_actual'])
        configuracion = ConfiguracionPrograma.objects.create(
            programa='Ingeniería', grado='maestria', periodos_requeridos=4,
        )
        materias = [self.materia] + [
            Materia.objects.create(clave=f'CUP-{index:02d}', nombre=f'Materia disponible {index}')
            for index in range(2, 5)
        ]
        for materia in materias:
            PlanEstudioMateria.objects.create(configuracion=configuracion, materia=materia)
        crear_carga_publicada(
            self.alumno,
            self.periodo,
            materias,
            capacidades={self.materia.pk: 42},
        )
        self.client.force_authenticate(user=self.alumno)
        response = self.client.get('/api/preregistro/materias/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['salon_label'], 'Salón 1')
        self.assertEqual(response.data[0]['capacidad'], 42)
        self.assertEqual(response.data[0]['inscritos'], 0)
        for index in range(42):
            Aspirante.objects.create_user(
                usuario=f'LLENO{index}', correo=f'lleno{index}@example.com', password='password123',
                nombre=f'Alumno Lleno {index}', curp=f'LLNO850101HDFR{index:02d}', telefono='5512345678',
                estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 1', estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 1', nombre_familiar='Familiar', parentesco='Madre', telefono_familiar='5511111111', ultimo_grado='Licenciatura', institucion='Cinvestav', unidad='Cinvestav', departamento='Academia', seccion='Posgrado', programa='Ingeniería', business_key=f'LLENO-{index}', rol='alumno',
            )
        inscritos = list(Aspirante.objects.filter(usuario__startswith='LLENO'))
        Inscripcion.objects.bulk_create([
            Inscripcion(aspirante=alumno, materia=self.materia, periodo_inscripcion=self.periodo)
            for alumno in inscritos
        ])
        disponibles = self.client.get('/api/preregistro/materias/')
        self.assertEqual(disponibles.data[0]['inscritos'], 42)
        response = self.client.post(
            '/api/preregistro/inscripciones/',
            {'materias': [materia.id for materia in materias]},
            format='json',
        )
        self.assertEqual(response.status_code, 409)


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

    def test_aspirante_no_puede_convertirse_por_endpoint_de_autoservicio(self):
        response = self.client.post('/api/preregistro/convertir-misma-cuenta/')

        self.assertEqual(response.status_code, 404)
        self.aspirante.refresh_from_db()
        self.assertEqual(self.aspirante.rol, 'aspirante')


class NotificacionesMasivasCoordinacionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.coordinacion = Aspirante.objects.create_user(
            usuario='COORDBULK', correo='coord.bulk@example.com', password='password123',
            nombre='Coordinación', is_staff=True,
        )
        self.base_aspirante = {
            'password': 'password123',
            'telefono': '5512345678',
            'estado_actual': 'Ciudad de México',
            'municipio_actual': 'Coyoacán',
            'direccion_actual': 'Calle 1',
            'estado_permanente': 'Ciudad de México',
            'municipio_permanente': 'Coyoacán',
            'direccion_permanente': 'Calle 1',
            'nombre_familiar': 'Contacto',
            'parentesco': 'Familiar',
            'telefono_familiar': '5511111111',
            'ultimo_grado': 'Licenciatura',
            'institucion': 'Cinvestav',
            'unidad': 'Cinvestav',
            'departamento': 'Pruebas',
            'seccion': 'Posgrado',
            'programa': 'Ingeniería',
        }
        self.pendiente = self.crear_aspirante(
            'BULKPEND', 'bulk.pend@example.com', 'BULK-PEND-01', 'pendiente',
        )
        self.revision = self.crear_aspirante(
            'BULKREV', 'bulk.rev@example.com', 'BULK-REV-01', 'revision',
        )
        self.aceptado = self.crear_aspirante(
            'BULKACEP', 'bulk.acep@example.com', 'BULK-ACEP-01', 'aceptado',
        )
        self.client.force_authenticate(user=self.coordinacion)

    def crear_aspirante(self, usuario, correo, business_key, estado):
        return Aspirante.objects.create_user(
            usuario=usuario,
            correo=correo,
            nombre=usuario,
            curp=f'{usuario[-4:]}850101HDFRNN01',
            business_key=business_key,
            rol='aspirante',
            proceso_estado=estado,
            **self.base_aspirante,
        )

    @patch('preregistro.views.send_mail', return_value=1)
    def test_envia_a_un_grupo_y_agrega_fechas_guardadas(self, enviar_correo):
        self.pendiente.fecha_entrevista = timezone.now()
        self.pendiente.save(update_fields=['fecha_entrevista'])

        response = self.client.post(
            '/api/coordinacion/notificaciones-masivas/',
            {'grupo': 'por-revisar', 'incluir_fechas': True},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['enviados'], 1)
        self.assertEqual(response.data['total'], 1)
        self.assertEqual(enviar_correo.call_count, 1)
        self.assertIn('Entrevista:', enviar_correo.call_args.args[1])
        self.assertEqual(SeguimientoSolicitud.objects.filter(aspirante=self.pendiente).count(), 1)
        self.assertEqual(SeguimientoSolicitud.objects.filter(aspirante=self.revision).count(), 0)

    @patch('preregistro.views.send_mail', return_value=1)
    def test_rechaza_destinatario_fuera_del_grupo(self, enviar_correo):
        response = self.client.post(
            '/api/coordinacion/notificaciones-masivas/',
            {'grupo': 'por-revisar', 'ids': [self.aceptado.pk]},
            format='json',
        )

        self.assertEqual(response.status_code, 409)
        enviar_correo.assert_not_called()

    @patch('preregistro.views.send_mail', return_value=0)
    def test_reporta_fallo_de_correo_y_no_registra_aviso_enviado(self, enviar_correo):
        response = self.client.post(
            '/api/coordinacion/notificaciones-masivas/',
            {'grupo': 'aceptado'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['enviados'], 0)
        self.assertEqual(len(response.data['fallidos']), 1)
        self.assertEqual(SeguimientoSolicitud.objects.filter(aspirante=self.aceptado).count(), 0)

    @patch('preregistro.views.send_mail', return_value=1)
    def test_email_notifications_can_be_disabled_while_internal_notices_remain(self, enviar_correo):
        ConfiguracionSistema.objects.create(clave='notificaciones_activas', valor='false')

        response = self.client.post(
            '/api/coordinacion/notificaciones-masivas/',
            {'grupo': 'por-revisar', 'incluir_fechas': False},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['correos_desactivados'], 1)
        self.assertEqual(response.data['enviados'], 0)
        self.assertEqual(response.data['avisos_internos'], 1)
        enviar_correo.assert_not_called()
        seguimiento = SeguimientoSolicitud.objects.get(aspirante=self.pendiente)
        self.assertIn('correo desactivado', seguimiento.detalle)

    def test_campana_devuelve_unread_total_y_marca_notificaciones(self):
        SeguimientoSolicitud.objects.bulk_create([
            SeguimientoSolicitud(
                aspirante=self.pendiente,
                estado='pendiente',
                detalle=f'Actualización {index}',
                origen='Coordinación Académica',
            )
            for index in range(55)
        ])
        self.client.force_authenticate(user=self.pendiente)

        response = self.client.get('/api/preregistro/seguimiento/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['eventos']), 50)
        self.assertEqual(response.data['no_leidas'], 55)
        marcada = self.client.post('/api/preregistro/notificaciones/marcar-leidas/')
        self.assertEqual(marcada.data['updated'], 55)
        refreshed = self.client.get('/api/preregistro/seguimiento/')
        self.assertEqual(refreshed.data['no_leidas'], 0)


class AceptacionRequiereRevisionDocumentosTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.coordinacion = Aspirante.objects.create_user(
            usuario='COORD01', correo='coord.docs@example.com', password='password123',
            nombre='Coordinación', is_staff=True,
        )
        self.aspirante = Aspirante.objects.create_user(
            usuario='ASPDOC01', correo='asp.docs@example.com', password='password123',
            nombre='Aspirante Docs', curp='ASPD850101HDFRNN01', telefono='5512345678',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 1',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 1',
            nombre_familiar='Familiar', parentesco='Madre', telefono_familiar='5511111111',
            ultimo_grado='Licenciatura', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Academia', seccion='Posgrado', programa='Ingeniería', business_key='ASPDOC-01',
        )
        self.documento = DocumentoAspirante.objects.create(
            aspirante=self.aspirante, tipo='cv', nombre_original='cv.pdf', tamano=10,
            archivo=SimpleUploadedFile('cv.pdf', b'%PDF-1.4'),
        )
        self.client.force_authenticate(user=self.coordinacion)

    def aceptar(self):
        return self.client.patch(f'/api/coordinacion/aspirantes/{self.aspirante.pk}/estado/', {'proceso_estado': 'aceptado'}, format='json')

    def test_no_acepta_con_documentos_sin_revisar(self):
        response = self.aceptar()

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['codigo'], 'documentos_pendientes')
        self.aspirante.refresh_from_db()
        self.assertNotEqual(self.aspirante.proceso_estado, 'aceptado')

    def test_no_acepta_sin_documentos(self):
        self.documento.delete()

        self.assertEqual(self.aceptar().status_code, 409)

    def test_acepta_tras_revisar_documentos(self):
        revision = self.client.patch(f'/api/coordinacion/documentos/{self.documento.pk}/revision/', {'revisado': True}, format='json')
        self.assertEqual(revision.status_code, 200)

        response = self.aceptar()

        self.assertEqual(response.status_code, 200)
        self.aspirante.refresh_from_db()
        self.assertEqual(self.aspirante.proceso_estado, 'aceptado')
        seguimiento = self.aspirante.seguimientos.filter(estado='aceptado').latest('created_at')
        self.assertIn('ponte en contacto con Coordinación Académica', seguimiento.detalle)
        self.assertIn('Solo Coordinación puede realizar tu alta', seguimiento.detalle)

    def test_coordinacion_puede_ver_documento_en_linea(self):
        response = self.client.get(f'/api/preregistro/documentos/{self.documento.pk}/descarga/?inline=1')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith('inline'))

    def test_documento_sin_sesion_responde_no_autorizado(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(f'/api/preregistro/documentos/{self.documento.pk}/descarga/?inline=1')

        self.assertEqual(response.status_code, 401)

    def test_resubir_documento_reinicia_la_revision(self):
        self.documento.revisado = True
        self.documento.save()
        self.client.force_authenticate(user=self.aspirante)

        self.client.post('/api/preregistro/documentos/', {'tipo': 'cv', 'archivo': SimpleUploadedFile('nuevo.pdf', b'%PDF-1.4')}, format='multipart')

        self.documento.refresh_from_db()
        self.assertFalse(self.documento.revisado)


class RevisionAntiplagioProyectoTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.alumno = Aspirante.objects.create_user(
            usuario='ALUMNOPROJ', correo='alumno.proyecto@example.com', password='password123',
            nombre='Alumno Proyecto', curp='PROY850101HDFRNN01', telefono='5512345678',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 1',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 1',
            nombre_familiar='Familiar', parentesco='Padre', telefono_familiar='5511111111',
            ultimo_grado='Licenciatura', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Academia', seccion='Posgrado', programa='Ingeniería', business_key='ALUMNO-PROYECTO',
            rol='alumno',
        )
        self.director = Aspirante.objects.create_user(
            usuario='DIRECTORP1', correo='director.proyecto@example.com', password='password123',
            nombre='Director Proyecto', curp='DIRP850101HDFRNN01', telefono='5512345678',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 1',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 1',
            nombre_familiar='Familiar', parentesco='Padre', telefono_familiar='5511111111',
            ultimo_grado='Doctorado', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Academia', seccion='Posgrado', programa='Ingeniería', business_key='DIRECTOR-PROYECTO',
            rol='director',
        )
        self.alumno.director_tesis = self.director
        self.alumno.save(update_fields=['director_tesis'])
        self.proyecto = ProyectoTesis.objects.create(
            alumno=self.alumno,
            director=self.director,
            titulo='Diseño de una plataforma para revisión académica',
            resumen='Se propone una plataforma para organizar revisiones académicas y evidencias de tesis.',
            linea_investigacion='Tecnología educativa',
            estado='en_revision',
        )
        self.client.force_authenticate(user=self.alumno)

    def test_alumno_puede_generar_revision_antiplagio_para_su_proyecto(self):
        archivo = SimpleUploadedFile(
            'tesis_antiplagio.pdf',
            b'%PDF-1.4\n%demo-file-for-antiplagio',
            content_type='application/pdf',
        )

        response = self.client.post(
            f'/api/proyectos-tesis/{self.proyecto.pk}/revision-antiplagio/',
            {'archivo': archivo, 'proveedor': 'turnitin'},
            format='multipart',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['proyecto'], self.proyecto.pk)
        self.assertIn(response.data['estado'], {'en_revision', 'aprobado', 'observado'})
        self.assertGreaterEqual(float(response.data['porcentaje_similitud']), 0)


class JuradoYDefensaProyectoTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.alumno = Aspirante.objects.create_user(
            usuario='ALUMNODT', correo='alumno.tesis@example.com', password='password123',
            nombre='Alumno Defensa', curp='DEFN850101HDFRNN01', telefono='5512345678',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 1',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 1',
            nombre_familiar='Familiar', parentesco='Padre', telefono_familiar='5511111111',
            ultimo_grado='Licenciatura', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Academia', seccion='Posgrado', programa='Ingeniería', business_key='ALUMNO-DEFENSA',
            rol='alumno',
        )
        self.director = Aspirante.objects.create_user(
            usuario='DIRECTORDT', correo='director.tesis@example.com', password='password123',
            nombre='Director Defensa', curp='DIRD850101HDFRNN01', telefono='5512345678',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 1',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 1',
            nombre_familiar='Familiar', parentesco='Padre', telefono_familiar='5511111111',
            ultimo_grado='Doctorado', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Academia', seccion='Posgrado', programa='Ingeniería', business_key='DIRECTOR-DEFENSA',
            rol='director',
        )
        self.jurado = Aspirante.objects.create_user(
            usuario='JURADODT', correo='jurado.tesis@example.com', password='password123',
            nombre='Jurado Defensa', curp='JURD850101HDFRNN01', telefono='5512345678',
            estado_actual='Ciudad de México', municipio_actual='Coyoacán', direccion_actual='Calle 1',
            estado_permanente='Ciudad de México', municipio_permanente='Coyoacán', direccion_permanente='Calle 1',
            nombre_familiar='Familiar', parentesco='Padre', telefono_familiar='5511111111',
            ultimo_grado='Doctorado', institucion='Cinvestav', unidad='Cinvestav',
            departamento='Academia', seccion='Posgrado', programa='Ingeniería', business_key='JURADO-DEFENSA',
            rol='docente',
        )
        self.proyecto = ProyectoTesis.objects.create(
            alumno=self.alumno,
            director=self.director,
            titulo='Evaluación final del sistema de gestión de tesis',
            resumen='Se propone un sistema para la gestión y seguimiento de proyectos de tesis con evaluación académica y defensa institucional.',
            linea_investigacion='Ingeniería de software',
            estado='aprobado',
        )

    def test_director_puede_asignar_jurado_y_programar_defensa(self):
        self.client.force_authenticate(user=self.director)

        jurado_response = self.client.post(
            f'/api/proyectos-tesis/{self.proyecto.pk}/jurado/',
            {'jurado': self.jurado.id, 'rol': 'presidente', 'orden': 1},
            format='json',
        )
        self.assertEqual(jurado_response.status_code, 201)
        self.assertEqual(jurado_response.data['jurado'], self.jurado.id)
        self.assertEqual(jurado_response.data['rol'], 'presidente')

        defensa_response = self.client.post(
            f'/api/proyectos-tesis/{self.proyecto.pk}/defensa/',
            {'fecha': '2026-11-15T10:00:00Z', 'lugar': 'Sala de tesis 3', 'modalidad': 'presencial'},
            format='json',
        )
        self.assertEqual(defensa_response.status_code, 201)
        self.assertEqual(defensa_response.data['lugar'], 'Sala de tesis 3')
        self.assertEqual(defensa_response.data['modalidad'], 'presencial')
        self.assertTrue(DefensaTesis.objects.filter(proyecto=self.proyecto).exists())

        jurado = JuradoProyecto.objects.get(proyecto=self.proyecto, jurado=self.jurado)
        self.assertEqual(jurado.estado, 'pendiente')

    def test_defensa_virtual_generates_link_and_is_visible_to_jurado(self):
        self.client.force_authenticate(user=self.director)
        self.client.post(
            f'/api/proyectos-tesis/{self.proyecto.pk}/jurado/',
            {'jurado': self.jurado.id, 'rol': 'vocal', 'orden': 1},
            format='json',
        )

        defensa_response = self.client.post(
            f'/api/proyectos-tesis/{self.proyecto.pk}/defensa/',
            {'fecha': '2026-12-05T10:00:00Z', 'modalidad': 'hibrida', 'lugar': 'Sala virtual CINVESTAV'},
            format='json',
        )
        self.assertEqual(defensa_response.status_code, 201)
        self.assertTrue(defensa_response.data['enlace_virtual'].startswith('https://meet.jit.si/'))

        self.client.force_authenticate(user=self.jurado)
        consulta_response = self.client.get(f'/api/proyectos-tesis/{self.proyecto.pk}/defensa/')
        self.assertEqual(consulta_response.status_code, 200)
        self.assertEqual(consulta_response.data['modalidad'], 'hibrida')
        self.assertEqual(consulta_response.data['enlace_virtual'], defensa_response.data['enlace_virtual'])

    def test_diploma_requires_completed_approved_defense_and_returns_pdf(self):
        self.client.force_authenticate(user=self.alumno)
        unavailable = self.client.get(f'/api/proyectos-tesis/{self.proyecto.pk}/diploma/')
        self.assertEqual(unavailable.status_code, 409)

        defensa = DefensaTesis.objects.create(
            proyecto=self.proyecto,
            fecha='2026-12-12T10:00:00Z',
            modalidad='virtual',
            estado='revisada',
            calificacion_final=9.25,
        )
        response = self.client.get(f'/api/proyectos-tesis/{self.proyecto.pk}/diploma/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        pdf_content = b''.join(response.streaming_content)
        self.assertTrue(pdf_content.startswith(b'%PDF'))
        self.assertIn(f'SINAC-DIP-{self.proyecto.pk:06d}-{defensa.pk:06d}'.encode(), response['Content-Disposition'].encode())


class EgresadosTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.coordinacion = Aspirante.objects.create_user(
            usuario='COORDEG', correo='coord.eg@example.com', password='password123',             nombre='Coordinación', is_staff=True, business_key='COORDEG-01',
        )
        self.alumno = Aspirante.objects.create_user(
            usuario='ALUEG01', correo='alu.eg@example.com', password='password123', nombre='Alumno Egreso',
            curp='ALEG850101HDFRNN01', rol='alumno', matricula='M-100', programa='Ingeniería', business_key='ALUEG-01',
            profile_photo=SimpleUploadedFile('foto.png', b'x', content_type='image/png'),
        )
        self.client.force_authenticate(user=self.coordinacion)

    def registrar(self, **extra):
        return self.client.post('/api/egresados/', {'alumno_id': self.alumno.pk, 'fecha_egreso': '2025-06-30', 'generacion': '2023-2025', **extra}, format='json')

    def test_exige_excepcion_si_prevalidacion_incompleta(self):
        response = self.registrar()

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['codigo'], 'prevalidacion_incompleta')
        self.assertFalse(EgresoAlumno.objects.exists())

    def test_registra_con_excepcion_y_crea_expediente(self):
        response = self.registrar(excepcion_motivo='Convenio especial')

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['profile_photo'])
        self.assertTrue(response.data['expediente_id'])
        self.alumno.refresh_from_db()
        self.assertEqual(self.alumno.proceso_estado, 'egresado')
        self.assertEqual(self.registrar(excepcion_motivo='x').status_code, 409)

    def test_lista_y_busca_egresados(self):
        self.registrar(excepcion_motivo='Convenio especial')

        data = self.client.get('/api/egresados/?q=Egreso').data
        self.assertEqual(len(data['egresados']), 1)
        self.assertEqual(data['candidatos'], [])
        self.assertEqual(len(self.client.get('/api/egresados/?q=zzz').data['egresados']), 0)

    def test_candidato_incluye_prevalidacion_y_motivos_antes_de_registro(self):
        data = self.client.get('/api/egresados/').data

        self.assertEqual(len(data['candidatos']), 1)
        prevalidacion = data['candidatos'][0]['prevalidacion_egreso']
        self.assertFalse(prevalidacion['completa'])
        self.assertIn(
            'El programa no tiene una configuración académica activa.',
            prevalidacion['motivos'],
        )

    def test_candidato_muestra_prevalidacion_completa_con_requisitos_cumplidos(self):
        configuracion = ConfiguracionPrograma.objects.create(
            programa='Ingeniería',
            grado='maestria',
            periodos_requeridos=1,
            creditos_requeridos=4,
        )
        materia = Materia.objects.create(clave='EGRESO-101', nombre='Materia obligatoria', creditos=4)
        PlanEstudioMateria.objects.create(
            configuracion=configuracion,
            materia=materia,
            obligatoria=True,
        )
        periodo = PeriodoInscripcion.objects.create(
            nombre='2025-1',
            apertura=timezone.now() - timedelta(days=180),
            cierre=timezone.now() - timedelta(days=90),
            activo=False,
        )
        Inscripcion.objects.create(
            aspirante=self.alumno,
            materia=materia,
            periodo_inscripcion=periodo,
            calificacion=8,
        )

        candidato = self.client.get('/api/egresados/').data['candidatos'][0]

        self.assertTrue(candidato['prevalidacion_egreso']['completa'])
        self.assertEqual(candidato['prevalidacion_egreso']['resumen']['creditos_aprobados'], 4)
        self.assertEqual(candidato['prevalidacion_egreso']['resumen']['periodos_cursados'], 1)

    def test_alumno_no_puede_consultar(self):
        self.client.force_authenticate(user=self.alumno)

        self.assertEqual(self.client.get('/api/egresados/').status_code, 403)


class HistoricoPersonasTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.coordinacion = Aspirante.objects.create_user(
            usuario='COORDHI', correo='coord.hi@example.com', password='password123',
            nombre='Coord Historial', rol='servicios', business_key='COORDHI-01',
        )
        self.alumno = Aspirante.objects.create_user(
            usuario='ALUHI01', correo='alu.hi@example.com', password='password123', nombre='Alumno Historial',
            curp='ALHI850101HDFRNN01', rol='alumno', programa='Ingeniería', business_key='ALUHI-01',
        )

    def test_registra_alta_y_cambios_con_actor(self):
        login = self.client.post('/api/auth/login/', {'usuario': 'COORDHI', 'password': 'password123'}, format='json')
        token = login.data.get('access')
        self.assertTrue(token, login.data)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.patch(f'/api/servicios-escolares/alumnos/{self.alumno.pk}/', {'programa': 'Maestría', 'proceso_estado': 'inactivo'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)

        data = self.client.get(f'/api/historico/?persona={self.alumno.pk}').data
        eventos = {(e['campo'], e['valor_anterior'], e['valor_nuevo'], e['realizado_por']) for e in data['eventos']}
        self.assertIn(('Programa', 'Ingeniería', 'Maestría', 'Coord Historial'), eventos)
        self.assertTrue(any(e['evento'] == 'alta' for e in data['eventos']))

    def test_historial_de_director_asignado(self):
        director = Aspirante.objects.create_user(
            usuario='DIRHI01', correo='dir.hi@example.com', password='password123', nombre='Director Uno',
            curp='DIHI850101HDFRNN01', rol='director', business_key='DIRHI-01',
        )
        self.alumno.director_tesis = director
        self.alumno.save()
        self.client.force_authenticate(user=self.coordinacion)

        eventos = self.client.get(f'/api/historico/?persona={self.alumno.pk}').data['eventos']
        self.assertTrue(any(e['campo'] == 'Director de tesis' and e['valor_nuevo'] == 'Director Uno' for e in eventos))
        self.assertEqual(len(self.client.get('/api/historico/?rol=director').data['eventos']), 1)

    def test_alumno_no_consulta_historico(self):
        self.client.force_authenticate(user=self.alumno)

        self.assertEqual(self.client.get('/api/historico/').status_code, 403)


class DirectorioDocentesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.servicios = Aspirante.objects.create_user(
            usuario='SERVDOC', correo='serv.doc@example.com', password='password123', nombre='Servicios Docentes',
            rol='servicios', business_key='SERVDOC-01', curp='SEDO850101HDFRNN01',
        )
        self.coord = Aspirante.objects.create_user(
            usuario='COORDDOC', correo='coord.doc@example.com', password='password123', nombre='Coord Docentes',
            rol='coordinacion', business_key='COORDDOC-01', curp='CODO850101HDFRNN01',
        )
        self.director = Aspirante.objects.create_user(
            usuario='DIRDOC', correo='dir.doc@example.com', password='password123', nombre='Dr. Directorio',
            rol='director', business_key='DIRDOC-01', curp='DIDO850101HDFRNN01', departamento='Computación',
        )
        self.alumno = Aspirante.objects.create_user(
            usuario='ALUDOC', correo='alu.doc@example.com', password='password123', nombre='Alumno Tesista',
            rol='alumno', business_key='ALUDOC-01', curp='ALDO850101HDFRNN01', director_tesis=self.director,
        )

    def test_servicios_y_coordinacion_consultan_directorio(self):
        for usuario in (self.servicios, self.coord):
            self.client.force_authenticate(user=usuario)
            data = self.client.get('/api/servicios-escolares/docentes/?q=Directorio').data
            self.assertEqual(data['total'], 1)
            self.assertEqual(data['docentes'][0]['tesistas_activos'], 1)
        self.assertTrue(self.client.get('/api/servicios-escolares/docentes/').data['puede_gestionar'] is False)

    def test_detalle_incluye_tesistas_y_graduados(self):
        egresado = Aspirante.objects.create_user(
            usuario='EGRDOC', correo='egr.doc@example.com', password='password123', nombre='Egresado Doc',
            rol='alumno', business_key='EGRDOC-01', curp='EGDO850101HDFRNN01', director_tesis=self.director,
        )
        EgresoAlumno.objects.create(alumno=egresado, fecha_egreso='2025-06-30', titulo_tesis='Tesis final')
        self.client.force_authenticate(user=self.servicios)
        data = self.client.get(f'/api/servicios-escolares/docentes/{self.director.pk}/').data
        self.assertEqual([t['nombre'] for t in data['tesistas']], ['Alumno Tesista'])
        self.assertEqual(data['graduados'][0]['titulo_tesis'], 'Tesis final')

    def test_no_desactiva_con_tesistas_activos(self):
        self.client.force_authenticate(user=self.servicios)
        url = f'/api/servicios-escolares/docentes/{self.director.pk}/'
        self.assertEqual(self.client.patch(url, {'is_active': False}, format='json').status_code, 409)
        self.alumno.director_tesis = None
        self.alumno.save()
        self.assertEqual(self.client.patch(url, {'is_active': False}, format='json').status_code, 200)
        self.director.refresh_from_db()
        self.assertFalse(self.director.is_active)

    def test_coordinacion_y_alumno_no_modifican_ni_consultan(self):
        self.client.force_authenticate(user=self.coord)
        self.assertEqual(self.client.patch(f'/api/servicios-escolares/docentes/{self.director.pk}/', {'is_active': False}, format='json').status_code, 403)
        self.client.force_authenticate(user=self.alumno)
        self.assertEqual(self.client.get('/api/servicios-escolares/docentes/').status_code, 403)

    def test_valida_documento_del_docente(self):
        doc = DocumentoAspirante.objects.create(
            aspirante=self.director, tipo='cv', archivo=SimpleUploadedFile('cv.pdf', b'x'), nombre_original='cv.pdf', tamano=1,
        )
        self.client.force_authenticate(user=self.servicios)
        data = self.client.patch(f'/api/servicios-escolares/docentes/{self.director.pk}/', {'documento_id': doc.pk, 'revisado': True}, format='json').data
        self.assertTrue(data['documentos'][0]['revisado'])

    def test_servicios_y_el_propio_docente_editan_perfil_academico(self):
        url = f'/api/servicios-escolares/docentes/{self.director.pk}/'
        self.client.force_authenticate(user=self.servicios)
        data = self.client.patch(url, {'sni_nivel': 'II', 'lineas_declaradas': 'IA, Robótica'}, format='json').data
        self.assertEqual(data['sni_nivel'], 'II')
        self.assertIn('Robótica', data['lineas_investigacion'])
        self.client.force_authenticate(user=self.director)
        data = self.client.patch(url, {'orcid': '0000-0001', 'is_active': False}, format='json').data
        self.assertEqual(data['orcid'], '0000-0001')
        self.director.refresh_from_db()
        self.assertTrue(self.director.is_active)
        self.assertEqual(self.client.patch(url, {'sni_nivel': 'x' * 31}, format='json').status_code, 400)

    def test_docente_no_edita_a_otro(self):
        otro = Aspirante.objects.create_user(
            usuario='DOCOTRO', correo='otro.doc@example.com', password='password123', nombre='Otro Docente',
            rol='docente', business_key='DOCOTRO-01', curp='OTDO850101HDFRNN01',
        )
        self.client.force_authenticate(user=otro)
        self.assertEqual(self.client.patch(f'/api/servicios-escolares/docentes/{self.director.pk}/', {'orcid': 'x'}, format='json').status_code, 403)


class ExamenesAspiranteTests(TestCase):
    def setUp(self):
        from preregistro.models import ExamenEnLinea, PreguntaExamen
        self.client = APIClient()
        self.asp = Aspirante.objects.create_user(
            usuario='ASPEXAM', correo='asp.exam@example.com', password='password123', nombre='Aspirante Examen',
            rol='aspirante', business_key='ASPEXAM-01', curp='AXEX850101HDFRNN01',
        )
        self.client.force_authenticate(user=self.asp)
        self.examen = ExamenEnLinea.objects.create(
            aspirante=self.asp, tipo='admision', titulo='Admisión', business_key='EXAM-T1',
            fecha_programada=timezone.now() - timedelta(hours=1), duracion_minutos=30,
        )
        self.p1 = PreguntaExamen.objects.create(examen=self.examen, texto='2+2', opciones=['3', '4'], respuesta_correcta='4', orden=1)
        self.p2 = PreguntaExamen.objects.create(examen=self.examen, texto='1+1', opciones=['2', '5'], respuesta_correcta='2', orden=2)

    def test_preguntas_ocultas_hasta_iniciar(self):
        item = self.client.get('/api/preregistro/examenes/').data['examenes'][0]
        self.assertEqual(item['preguntas'], [])
        self.assertEqual(item['total_preguntas'], 2)

    def test_iniciar_y_enviar_califica(self):
        r = self.client.post('/api/preregistro/examenes/', {'id': self.examen.pk}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['preguntas']), 2)
        self.assertNotIn('respuesta_correcta', r.data['preguntas'][0])
        r = self.client.put('/api/preregistro/examenes/', {'id': self.examen.pk, 'respuestas': {str(self.p1.pk): '4', str(self.p2.pk): '2'}}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['estado'], 'aprobado')

    def test_no_inicia_antes_de_fecha_ni_sin_preguntas(self):
        self.examen.fecha_programada = timezone.now() + timedelta(days=1)
        self.examen.save()
        self.assertEqual(self.client.post('/api/preregistro/examenes/', {'id': self.examen.pk}, format='json').status_code, 400)
        self.examen.fecha_programada = timezone.now() - timedelta(hours=1)
        self.examen.save()
        self.examen.preguntas.all().delete()
        self.assertEqual(self.client.post('/api/preregistro/examenes/', {'id': self.examen.pk}, format='json').status_code, 400)

    def test_envio_fuera_de_tiempo_se_califica_en_cero(self):
        self.client.post('/api/preregistro/examenes/', {'id': self.examen.pk}, format='json')
        self.examen.refresh_from_db()
        self.examen.fecha_inicio = timezone.now() - timedelta(minutes=40)
        self.examen.save()
        r = self.client.put('/api/preregistro/examenes/', {'id': self.examen.pk, 'respuestas': {str(self.p1.pk): '4', str(self.p2.pk): '2'}}, format='json')
        self.assertEqual(r.data['estado'], 'reprobado')


class GestionExamenesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.coord = Aspirante.objects.create_user(
            usuario='COORDEX', correo='coord.ex@example.com', password='password123', nombre='Coord Examen',
            rol='coordinacion', business_key='COORDEX-01', curp='COEX850101HDFRNN01',
        )
        self.serv = Aspirante.objects.create_user(
            usuario='SERVEX', correo='serv.ex@example.com', password='password123', nombre='Serv Examen',
            rol='servicios', business_key='SERVEX-01', curp='SEEX850101HDFRNN01',
        )
        self.asp1 = Aspirante.objects.create_user(
            usuario='ASPEX1', correo='asp.ex1@example.com', password='password123', nombre='Aspirante Uno',
            rol='aspirante', business_key='ASPEX1-01', curp='A1EX850101HDFRNN01',
        )
        self.asp2 = Aspirante.objects.create_user(
            usuario='ASPEX2', correo='asp.ex2@example.com', password='password123', nombre='Aspirante Dos',
            rol='aspirante', business_key='ASPEX2-01', curp='A2EX850101HDFRNN01',
        )
        self.payload = {
            'tipo': 'admision', 'titulo': 'Admisión 2026', 'descripcion': 'Examen', 'duracion_minutos': 60, 'max_intentos': 1,
            'fecha_programada': (timezone.now() + timedelta(days=1)).isoformat(),
            'aspirantes': [self.asp1.pk, self.asp2.pk],
            'preguntas': [
                {'texto': '2+2', 'opciones': ['3', '4'], 'respuesta_correcta': '4'},
                {'texto': 'Capital de México', 'opciones': [], 'respuesta_correcta': 'CDMX'},
            ],
        }

    def test_coordinacion_crea_un_examen_por_aspirante(self):
        self.client.force_authenticate(user=self.coord)
        r = self.client.post('/api/examenes-gestion/', self.payload, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['creados'], 2)
        self.assertEqual(self.asp1.examenes_en_linea.get().preguntas.count(), 2)

    def test_servicios_solo_consulta_y_no_ve_respuestas_correctas(self):
        self.client.force_authenticate(user=self.coord)
        self.client.post('/api/examenes-gestion/', self.payload, format='json')
        self.client.force_authenticate(user=self.serv)
        self.assertEqual(self.client.post('/api/examenes-gestion/', self.payload, format='json').status_code, 403)
        listado = self.client.get('/api/examenes-gestion/').data
        self.assertEqual(listado['total'], 2)
        self.assertFalse(listado['puede_crear'])
        detalle = self.client.get(f"/api/examenes-gestion/{listado['examenes'][0]['id']}/").data
        self.assertNotIn('respuesta_correcta', detalle['preguntas'][0])

    def test_validaciones(self):
        self.client.force_authenticate(user=self.coord)
        malo = {**self.payload, 'preguntas': [{'texto': 'x', 'opciones': ['a', 'b'], 'respuesta_correcta': 'c'}]}
        self.assertEqual(self.client.post('/api/examenes-gestion/', malo, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/examenes-gestion/', {**self.payload, 'aspirantes': []}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/examenes-gestion/', {**self.payload, 'tipo': 'predoctoral'}, format='json').status_code, 400)

    def test_examen_iniciado_no_se_edita_ni_elimina(self):
        self.client.force_authenticate(user=self.coord)
        eid = self.client.post('/api/examenes-gestion/', {**self.payload, 'aspirantes': [self.asp1.pk], 'fecha_programada': (timezone.now() - timedelta(hours=1)).isoformat()}, format='json').data['examenes'][0]['id']
        self.assertEqual(self.client.patch(f'/api/examenes-gestion/{eid}/', {'titulo': 'Nuevo'}, format='json').status_code, 200)
        self.client.force_authenticate(user=self.asp1)
        self.assertEqual(self.client.post('/api/preregistro/examenes/', {'id': eid}, format='json').status_code, 200)
        self.client.force_authenticate(user=self.coord)
        self.assertEqual(self.client.patch(f'/api/examenes-gestion/{eid}/', {'titulo': 'Otro'}, format='json').status_code, 409)
        self.assertEqual(self.client.delete(f'/api/examenes-gestion/{eid}/').status_code, 409)

    def test_otro_intento_y_eliminar_sin_iniciar(self):
        self.client.force_authenticate(user=self.coord)
        eid = self.client.post('/api/examenes-gestion/', {**self.payload, 'aspirantes': [self.asp1.pk], 'fecha_programada': (timezone.now() - timedelta(hours=1)).isoformat()}, format='json').data['examenes'][0]['id']
        self.client.force_authenticate(user=self.asp1)
        self.client.post('/api/preregistro/examenes/', {'id': eid}, format='json')
        self.client.put('/api/preregistro/examenes/', {'id': eid, 'respuestas': {}}, format='json')
        self.client.force_authenticate(user=self.coord)
        r = self.client.patch(f'/api/examenes-gestion/{eid}/', {'accion': 'otro_intento'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.data['estado'], r.data['max_intentos']), ('programado', 2))
        nuevo = self.client.post('/api/examenes-gestion/', {**self.payload, 'aspirantes': [self.asp2.pk]}, format='json').data['examenes'][0]['id']
        self.assertEqual(self.client.delete(f'/api/examenes-gestion/{nuevo}/').status_code, 204)

    def test_candidatos_solo_coordinacion(self):
        self.client.force_authenticate(user=self.coord)
        self.assertEqual(len(self.client.get('/api/examenes-gestion/candidatos/?q=Uno').data['aspirantes']), 1)
        self.client.force_authenticate(user=self.serv)
        self.assertEqual(self.client.get('/api/examenes-gestion/candidatos/').status_code, 403)


class PanelDocenteExamenSolicitudTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.docente = Aspirante.objects.create_user(
            usuario='DOC-PANEL-EXAM', correo='doc.panel.exam@example.com', password='password123',
            nombre='Docente Panel', rol='docente', business_key='DOC-PANEL-EXAM-01',
            curp='DPEX850101HDFRNN01',
        )
        self.alumno = Aspirante.objects.create_user(
            usuario='ALU-PANEL-EXAM', correo='alu.panel.exam@example.com', password='password123',
            nombre='Alumno Panel', rol='alumno', business_key='ALU-PANEL-EXAM-01',
            curp='APEX850101HDFRNN01',
        )
        self.materia = Materia.objects.create(
            clave='PANEL-EXAM-01', nombre='Materia panel examen', profesor=self.docente.nombre,
        )
        Inscripcion.objects.create(aspirante=self.alumno, materia=self.materia)
        self.examen = ExamenEnLinea.objects.create(
            aspirante=self.alumno, tipo='admision', titulo='Examen panel',
            estado='aprobado', calificacion='7.50',
        )
        self.solicitud = SolicitudAcademica.objects.create(
            aspirante=self.alumno, tipo='historial', comentario='Solicito mi historial',
        )
        self.client.force_authenticate(user=self.docente)

    def test_panel_incluye_alumno_en_solicitudes_y_examenes(self):
        response = self.client.get('/api/docente/panel/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['solicitudes'][0]['aspirante']['nombre'], self.alumno.nombre)
        self.assertEqual(response.data['solicitudes'][0]['aspirante']['usuario'], self.alumno.usuario)
        self.assertEqual(response.data['examenes'][0]['aspirante']['nombre'], self.alumno.nombre)
        self.assertEqual(response.data['examenes'][0]['aspirante']['usuario'], self.alumno.usuario)

    def test_docente_puede_ajustar_nota_final_y_estado_derivado(self):
        url = f'/api/docente/examenes/{self.examen.pk}/'
        self.assertEqual(self.client.put(url, ['datos'], format='json').status_code, 400)
        self.assertEqual(self.client.put(url, {'calificacion': '10.01'}, format='json').status_code, 400)

        aprobado = self.client.put(url, {'calificacion': '8.00'}, format='json')
        self.assertEqual(aprobado.status_code, 200)
        self.assertEqual(aprobado.data['estado'], 'aprobado')
        self.assertEqual(aprobado.data['calificacion'], '8.00')

        reprobado = self.client.put(url, {'calificacion': '7.99', 'retroalimentacion': 'Revisar respuestas.'}, format='json')
        self.assertEqual(reprobado.status_code, 200)
        self.assertEqual(reprobado.data['estado'], 'reprobado')
        self.assertEqual(reprobado.data['retroalimentacion'], 'Revisar respuestas.')

    def test_docente_no_puede_iniciar_finalizar_ni_cambiar_fechas(self):
        url = f'/api/docente/examenes/{self.examen.pk}/'
        for cambios in (
            {'estado': 'iniciado'},
            {'fecha_inicio': timezone.now().isoformat()},
            {'fecha_fin': timezone.now().isoformat()},
        ):
            self.assertEqual(self.client.put(url, cambios, format='json').status_code, 400)

        self.examen.refresh_from_db()
        self.assertEqual(self.examen.estado, 'aprobado')
        self.assertIsNone(self.examen.fecha_inicio)
        self.assertIsNone(self.examen.fecha_fin)

        self.examen.estado = 'iniciado'
        self.examen.save(update_fields=['estado'])
        self.assertEqual(self.client.put(url, {'calificacion': '9.00'}, format='json').status_code, 409)

    def test_docente_no_puede_ajustar_examenes_ajenos_o_predoctorales(self):
        otro_docente = Aspirante.objects.create_user(
            usuario='DOC-PANEL-OTRO', correo='doc.panel.otro@example.com', password='password123',
            nombre='Otro Docente', rol='docente', business_key='DOC-PANEL-OTRO-01',
            curp='DOEX850101HDFRNN01',
        )
        self.client.force_authenticate(user=otro_docente)
        self.assertEqual(
            self.client.put(f'/api/docente/examenes/{self.examen.pk}/', {'calificacion': '9.00'}, format='json').status_code,
            403,
        )

        self.client.force_authenticate(user=self.docente)
        predoctoral = ExamenEnLinea.objects.create(
            aspirante=self.alumno, tipo='predoctoral', titulo='Examen predoctoral',
            business_key='PANEL-EXAM-PREDOC', estado='aprobado', calificacion='8.00',
        )
        self.assertEqual(
            self.client.put(f'/api/docente/examenes/{predoctoral.pk}/', {'calificacion': '9.00'}, format='json').status_code,
            403,
        )
