from datetime import date, timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from preregistro.models import (
    Aspirante, ConfiguracionPrograma, DefensaTesis, DocumentoAspirante, EgresoAlumno, EntrevistaVirtual,
    EvaluacionColegio, ExamenEnLinea, ExpedienteDigital, Inscripcion, JuradoProyecto, Materia,
    PeriodoInscripcion, PlanEstudioMateria, PreguntaExamen, ProyectoTesis, RespuestaExamen,
    SeguimientoSolicitud, SolicitudAcademica, SolicitudDireccionTesis, SolicitudInscripcionExtemporanea,
)

PROGRAMAS = [
    'Maestría — Teoría de la Computación (2 años)',
    'Maestría — Inteligencia Artificial (2 años)',
    'Maestría — Sistemas de Cómputo (2 años)',
    'Doctorado — Sistemas de Información (4 años)',
    'Doctorado — Ciencias de la Computación (4 años)',
]

DIRECTORES = ['Dr. Alberto Mendoza Rivas', 'Dra. Beatriz Salinas Ortega', 'Dr. Carlos Ibarra Fuentes', 'Dra. Daniela Quiroz Lara', 'Dr. Eduardo Valdés Pineda']
DOCENTES = ['Dra. Fernanda Aguilar Soto', 'Dr. Gustavo Herrera Luna', 'Dra. Helena Cortés Ramos', 'Dr. Ignacio Paredes Vega', 'Dra. Julia Navarro Cruz']
ASPIRANTES = ['Karla Ortiz Medina', 'Luis Fernando Reyes Campos', 'Mariana Duarte Olvera', 'Néstor Alcántara Gil', 'Olivia Santana Ríos']
ALUMNOS = ['Pablo Escobedo Torres', 'Quetzal Domínguez Mora', 'Rocío Villalobos Peña', 'Sergio Camacho Núñez', 'Tania Benítez Ochoa']
EGRESADOS = ['Ulises Montes Barrera', 'Valeria Solís Acosta', 'Wilfrido Cabrera Lima', 'Ximena Arredondo Paz', 'Yahir Lozano Estrada']

TESIS = [
    'Modelos de lenguaje eficientes para el español de México',
    'Verificación formal de autómatas celulares reversibles',
    'Optimización de planificadores en sistemas de cómputo distribuido',
    'Ontologías para la interoperabilidad de sistemas de información clínica',
    'Redes neuronales de grafos aplicadas a la detección de fraude',
    'Algoritmos de aproximación para problemas de empaquetado',
    'Aprendizaje por refuerzo en robótica móvil de bajo costo',
    'Arquitecturas serverless para cómputo científico',
    'Minería de procesos en sistemas académicos universitarios',
    'Complejidad parametrizada en teoría de grafos',
]

MATERIAS = [
    'Algoritmos Avanzados', 'Aprendizaje Automático', 'Sistemas Distribuidos', 'Bases de Datos Avanzadas', 'Teoría de la Complejidad',
    'Visión Computacional', 'Criptografía Aplicada', 'Lógica Computacional', 'Ingeniería de Software', 'Procesamiento de Lenguaje Natural',
]

CALIFICACIONES = [Decimal(x) for x in ('9.5', '8.8', '9.0', '7.5', '10', '8.2', '6.5', '9.3', '8.0', '9.8')]


def _password(prefijo, n):
    return f'Cinv{prefijo}{n}#2026'


def _pdf_demo():
    contenido = b'BT /F1 18 Tf 72 720 Td (Documento de prueba SINAC NEXT) Tj ET'
    objetos = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length ' + str(len(contenido)).encode() + b' >>\nstream\n' + contenido + b'\nendstream',
    ]
    salida = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for numero, objeto in enumerate(objetos, 1):
        offsets.append(len(salida))
        salida.extend(f'{numero} 0 obj\n'.encode() + objeto + b'\nendobj\n')
    xref = len(salida)
    salida.extend(f'xref\n0 {len(objetos) + 1}\n'.encode() + b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        salida.extend(f'{offset:010d} 00000 n \n'.encode())
    salida.extend(
        f'trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    )
    return bytes(salida)


class Command(BaseCommand):
    help = 'Carga datos demo para probar de forma integral los paneles y flujos de SINAC NEXT.'

    def _persona(self, usuario, nombre, rol, numero, password, programa, **extra):
        datos = {
            'correo': f'{usuario.replace(".", "_")}@demo.sinac.mx',
            'nombre': nombre,
            'curp': f'DEMO{numero:02d}0101HDFXXX{numero:02d}',
            'telefono': f'55{numero:08d}',
            'nacimiento': date(1995, 1, 1) + timedelta(days=37 * numero),
            'estado_actual': 'Ciudad de México', 'municipio_actual': 'Gustavo A. Madero', 'direccion_actual': f'Calle Demo {numero}, Col. Centro',
            'estado_permanente': 'Ciudad de México', 'municipio_permanente': 'Gustavo A. Madero', 'direccion_permanente': f'Calle Demo {numero}, Col. Centro',
            'nombre_familiar': f'Familiar de {nombre.split()[0]}', 'parentesco': 'Madre', 'telefono_familiar': f'56{numero:08d}',
            'ultimo_grado': 'Licenciatura en Ingeniería en Computación', 'institucion': 'Instituto Politécnico Nacional',
            'promedio': Decimal('8.50') + Decimal(numero % 10) / 10,
            'unidad': 'Zacatenco', 'departamento': 'Computación', 'seccion': 'Computación',
            'programa': programa, 'modalidad': 'Presencial',
            'business_key': f'DEMO-{usuario}', 'rol': rol, 'is_active': True,
        }
        datos.update(extra)
        persona, _ = Aspirante.objects.get_or_create(usuario=usuario, defaults=datos)
        for campo, valor in datos.items():
            setattr(persona, campo, valor)
        if password:
            persona.set_password(password)
        else:
            persona.set_unusable_password()
        persona.save()
        return persona

    @transaction.atomic
    def handle(self, *args, **options):
        credenciales = []
        ahora = timezone.now()

        directores = []
        for i, nombre in enumerate(DIRECTORES, 1):
            usuario, clave = f'dir.demo{i}', _password('Dir', i)
            directores.append(self._persona(usuario, nombre, 'director', 10 + i, clave, 'Investigación Cinvestav', proceso_estado='aceptado'))
            credenciales.append(('Director', usuario, clave, nombre))

        docentes = []
        for i, nombre in enumerate(DOCENTES, 1):
            usuario, clave = f'doc.demo{i}', _password('Doc', i)
            docentes.append(self._persona(usuario, nombre, 'docente', 20 + i, clave, 'Docencia Cinvestav', proceso_estado='aceptado'))
            credenciales.append(('Docente', usuario, clave, nombre))

        administrador = self._persona(
            'admin.demo', 'Administrador Demo', 'admin', 72, _password('Admin', 1),
            'Administración SINAC', proceso_estado='aceptado', is_staff=True, is_superuser=True,
        )
        credenciales.append(('Admin', administrador.usuario, _password('Admin', 1), administrador.nombre))
        coordinacion = self._persona(
            'coord.demo', 'Coordinación Académica Demo', 'coordinacion', 70, _password('Coord', 1),
            'Administración académica', proceso_estado='aceptado', is_staff=True,
        )
        credenciales.append(('Coordinación', coordinacion.usuario, _password('Coord', 1), coordinacion.nombre))
        servicios = self._persona(
            'serv.demo', 'Servicios Escolares Demo', 'servicios', 71, _password('Serv', 1),
            'Servicios Escolares', proceso_estado='aceptado', is_staff=True,
        )
        credenciales.append(('Servicios', servicios.usuario, _password('Serv', 1), servicios.nombre))

        aspirantes = []
        estados_aspirante = ['pendiente', 'iniciado', 'revision', 'aceptado', 'rechazado']
        tipos_documento = ['cv', 'titulo', 'carta_motivacion', 'carta_recomendacion']
        pdf_demo = _pdf_demo()
        for i, nombre in enumerate(ASPIRANTES, 1):
            usuario, clave = f'asp.demo{i}', _password('Asp', i)
            aspirante = self._persona(
                usuario, nombre, 'aspirante', 30 + i, clave, PROGRAMAS[i - 1],
                proceso_estado=estados_aspirante[i - 1],
                fecha_examen_admision=ahora + timedelta(days=i) if i in (1, 4) else None,
                fecha_entrevista=ahora + timedelta(days=i + 2) if i in (2, 4) else None,
                fecha_inicio_curso_propedeutico=ahora - timedelta(days=30) if i == 4 else None,
                curso_propedeutico_nota=Decimal('8.7') if i == 4 else None,
                curso_propedeutico_aprobado=i == 4,
            )
            aspirantes.append(aspirante)
            credenciales.append(('Aspirante', usuario, clave, nombre))
            for tipo in tipos_documento:
                documento, _ = DocumentoAspirante.objects.get_or_create(
                    aspirante=aspirante,
                    tipo=tipo,
                    defaults={
                        'nombre_original': f'{tipo}_demo_{i}.pdf',
                        'tamano': len(pdf_demo),
                        'lida_notificado': True,
                    },
                )
                if not documento.archivo:
                    documento.archivo.save(
                        f'{tipo}_demo_{i}.pdf', ContentFile(pdf_demo), save=False,
                    )
                documento.nombre_original = f'{tipo}_demo_{i}.pdf'
                documento.tamano = len(pdf_demo)
                documento.lida_notificado = True
                documento.revisado = i >= 3
                documento.revisado_en = ahora if documento.revisado else None
                documento.save()
            SeguimientoSolicitud.objects.get_or_create(
                aspirante=aspirante,
                estado=aspirante.proceso_estado,
                origen='Coordinación Académica Demo',
                detalle=f'Registro de prueba en etapa {aspirante.proceso_estado}.',
            )

        previo, _ = PeriodoInscripcion.objects.update_or_create(
            nombre='DEMO 2025-2', defaults={'apertura': ahora - timedelta(days=300), 'cierre': ahora - timedelta(days=200), 'activo': False})
        actual, _ = PeriodoInscripcion.objects.update_or_create(
            nombre='DEMO 2026-1', defaults={'apertura': ahora - timedelta(days=120), 'cierre': ahora - timedelta(days=20), 'activo': False})

        materias = []
        for i, nombre in enumerate(MATERIAS):
            materia, _ = Materia.objects.update_or_create(
                clave=f'DEMO-{i + 1:02d}',
                defaults={'nombre': nombre, 'categoria': 'formativo', 'creditos': (4, 5, 7)[i % 3], 'profesor': docentes[i // 2].nombre,
                          'horario': ('Lun y Mié 10:00-12:00', 'Mar y Jue 12:00-14:00')[i % 2], 'salon': 'salon_1', 'capacidad': 42})
            materias.append(materia)
        seminario, _ = Materia.objects.update_or_create(
            clave='DEMO-SEM',
            defaults={
                'nombre': 'Seminario de tesis (Demostración)',
                'categoria': 'seminario',
                'creditos': 5,
                'profesor': directores[3].nombre,
                'horario': 'Vie 10:00-12:00',
                'salon': 'sala_juntas',
                'capacidad': 20,
            },
        )

        for programa in PROGRAMAS:
            grado = 'doctorado' if programa.startswith('Doctorado') else 'maestria'
            duracion = 4 if grado == 'doctorado' else 2
            configuracion, _ = ConfiguracionPrograma.objects.update_or_create(
                programa=programa,
                defaults={
                    'grado': grado,
                    'periodicidad': 'semestral',
                    'periodos_requeridos': duracion * 2,
                    'creditos_requeridos': 20,
                    'activo': True,
                },
            )
            for index, materia in enumerate(materias):
                PlanEstudioMateria.objects.update_or_create(
                    configuracion=configuracion,
                    materia=materia,
                    defaults={
                        'periodo_sugerido': index % configuracion.periodos_requeridos + 1,
                        'obligatoria': True,
                    },
                )
            PlanEstudioMateria.objects.update_or_create(
                configuracion=configuracion,
                materia=seminario,
                defaults={'periodo_sugerido': 3, 'obligatoria': True},
            )

        def inscribir(alumno, offset, periodo, ciclo):
            for k in range(4):
                materia = materias[(offset + k) % len(materias)]
                cal = CALIFICACIONES[(offset + k + ciclo) % len(CALIFICACIONES)]
                p1, p2 = min(cal + Decimal('0.3'), Decimal(10)), max(cal - Decimal('0.4'), Decimal(5))
                Inscripcion.objects.update_or_create(
                    aspirante=alumno, materia=materia, periodo_inscripcion=periodo,
                    defaults={'estado': 'aprobada' if cal >= 7 else 'reprobada', 'validacion_servicios': 'validada', 'calificacion': cal,
                              'parcial_1': p1, 'parcial_2': p2, 'parcial_3': cal, 'horario': materia.horario})

        def tesis(alumno, director, titulo, estado):
            ProyectoTesis.objects.update_or_create(
                alumno=alumno, titulo=titulo,
                defaults={'director': director, 'resumen': f'Proyecto de investigación: {titulo}.', 'linea_investigacion': 'Ciencias de la Computación',
                          'objetivos': 'Definir, implementar y evaluar la propuesta.', 'metodologia': 'Revisión de literatura, diseño experimental y validación.',
                          'estado': estado, 'fecha_presentacion': ahora - timedelta(days=60)})

        alumnos = []
        for i, nombre in enumerate(ALUMNOS, 1):
            usuario, clave = f'alu.demo{i}', _password('Alu', i)
            alumno = self._persona(usuario, nombre, 'alumno', 40 + i, clave, PROGRAMAS[i - 1], proceso_estado='aceptado',
                                   matricula=f'DEMO-A{i:03d}', numero_periodo_actual=(1, 2, 3, 3, 4)[i - 1], director_tesis=directores[i - 1], tutor_propuesto=directores[i - 1].nombre)
            inscribir(alumno, i - 1, previo, 0)
            inscribir(alumno, i + 1, actual, 1)
            tesis(alumno, directores[i - 1], TESIS[i - 1], ('borrador', 'en_revision', 'observado', 'aprobado', 'en_revision')[i - 1])
            alumnos.append(alumno)
            credenciales.append(('Alumno', usuario, clave, f'{nombre} · {alumno.programa}'))

        for i, aspirante in enumerate(aspirantes, 1):
            estados_examen = ('programado', 'programado', 'completado', 'aprobado', 'reprobado')
            examen, _ = ExamenEnLinea.objects.update_or_create(
                business_key=f'DEMO-EXAMEN-{aspirante.usuario}',
                defaults={
                    'aspirante': aspirante,
                    'tipo': 'admision',
                    'titulo': 'Examen de admisión (Demostración)',
                    'descripcion': 'Evaluación de muestra para probar el flujo de exámenes.',
                    'fecha_programada': ahora + timedelta(days=i) if i < 3 else ahora - timedelta(days=i),
                    'fecha_inicio': ahora - timedelta(days=i) if i >= 3 else None,
                    'fecha_fin': ahora - timedelta(days=i) if i >= 3 else None,
                    'duracion_minutos': 60,
                    'estado': estados_examen[i - 1],
                    'calificacion': Decimal('8.7') if i == 4 else Decimal('6.2') if i == 5 else None,
                    'intentos': 1 if i >= 3 else 0,
                    'max_intentos': 2,
                    'retroalimentacion': 'Resultado de demostración.' if i >= 3 else '',
                },
            )
            preguntas = []
            for orden, texto, opciones, respuesta in (
                (1, '¿Cuál es el resultado de 2 + 2?', ['3', '4', '5'], '4'),
                (2, '¿Qué estructura organiza datos en pares clave-valor?', ['Pila', 'Diccionario', 'Cola'], 'Diccionario'),
            ):
                pregunta, _ = PreguntaExamen.objects.get_or_create(
                    examen=examen,
                    orden=orden,
                    defaults={'texto': texto, 'opciones': opciones, 'respuesta_correcta': respuesta},
                )
                preguntas.append(pregunta)
            if examen.estado in ('completado', 'aprobado', 'reprobado'):
                for pregunta in preguntas:
                    RespuestaExamen.objects.get_or_create(
                        examen=examen,
                        pregunta=pregunta,
                        aspirante=aspirante,
                        defaults={
                            'respuesta': pregunta.respuesta_correcta,
                            'es_correcta': True,
                        },
                    )

            EntrevistaVirtual.objects.update_or_create(
                jitsi_room_id=f'demo-entrevista-{aspirante.usuario}',
                defaults={
                    'aspirante': aspirante,
                    'proposito': 'admision',
                    'titulo': 'Entrevista de admisión (Demostración)',
                    'descripcion': 'Entrevista de muestra para probar el seguimiento del aspirante.',
                    'fecha_programada': ahora + timedelta(days=i + 2) if i < 3 else ahora - timedelta(days=i),
                    'fecha_inicio': ahora - timedelta(days=i) if i >= 3 else None,
                    'fecha_fin': ahora - timedelta(days=i) if i >= 3 else None,
                    'duracion_minutos': 30,
                    'jitsi_room_link': f'https://meet.jit.si/sinac-demo-{aspirante.usuario}',
                    'estado': 'programada' if i < 3 else 'completada',
                    'notas_docente': 'Registro de entrevista de demostración.' if i >= 3 else '',
                    'retroalimentacion': 'Seguimiento de muestra.' if i >= 3 else '',
                },
            )
            EvaluacionColegio.objects.update_or_create(
                aspirante=aspirante,
                defaults={
                    'evaluador': docentes[(i - 1) % len(docentes)],
                    'estado': ('pendiente', 'en_revision', 'en_revision', 'favorable', 'no_favorable')[i - 1],
                    'dictamen': 'Dictamen de demostración para validar la vista de evaluación.',
                    'fecha_evaluacion': ahora - timedelta(days=i) if i >= 3 else None,
                },
            )

        for alumno, director, estado, alumno_acepto, director_acepto in (
            (alumnos[2], directores[2], 'pendiente_director', True, False),
            (alumnos[3], directores[3], 'aprobada', True, True),
        ):
            SolicitudDireccionTesis.objects.update_or_create(
                alumno=alumno,
                defaults={
                    'director_sugerido': director,
                    'director_asignado': director if director_acepto else None,
                    'alumno_acepto_director': alumno_acepto,
                    'director_acepto': director_acepto,
                    'linea_investigacion': 'Ciencias de la Computación',
                    'justificacion': 'Solicitud de dirección de tesis para demostración del flujo.',
                    'estado': estado,
                    'observaciones': '',
                    'revisado_por': coordinacion if director_acepto else None,
                },
            )
        Inscripcion.objects.update_or_create(
            aspirante=alumnos[3],
            materia=seminario,
            periodo_inscripcion=actual,
            defaults={
                'estado': 'cursando',
                'validacion_servicios': 'validada',
                'horario': seminario.horario,
                'registrada_por': servicios,
            },
        )

        for alumno, tipo, estado, comentario in (
            (alumnos[0], 'historial', 'pendiente', 'Solicito una constancia de historial académico (Demostración).'),
            (alumnos[1], 'ajuste_materias', 'aceptado', 'Solicito revisar mi carga académica (Demostración).'),
            (alumnos[2], 'reinscripcion', 'rechazado', 'Solicitud de reinscripción para mostrar una resolución (Demostración).'),
        ):
            SolicitudAcademica.objects.get_or_create(
                aspirante=alumno,
                tipo=tipo,
                comentario=comentario,
                defaults={
                    'estado': estado,
                    'respuesta_revision': 'Resolución de ejemplo.' if estado != 'pendiente' else '',
                    'resuelta_por': coordinacion if estado != 'pendiente' else None,
                },
            )

        SolicitudInscripcionExtemporanea.objects.get_or_create(
            alumno=alumnos[0],
            periodo_inscripcion=previo,
            defaults={
                'solicitante': alumnos[0],
                'estado': 'pendiente',
                'motivo': 'Solicitud de demostración para probar el flujo de inscripción extemporánea.',
            },
        )

        egresados = []
        for i, nombre in enumerate(EGRESADOS, 1):
            usuario, clave = f'egr.demo{i}', None
            egresado = self._persona(usuario, nombre, 'alumno', 50 + i, clave, PROGRAMAS[(i + 1) % len(PROGRAMAS)], proceso_estado='egresado',
                                     matricula=f'DEMO-E{i:03d}', numero_periodo_actual=4, director_tesis=directores[i - 1], tutor_propuesto=directores[i - 1].nombre)
            inscribir(egresado, i + 3, previo, 2)
            inscribir(egresado, i + 5, actual, 3)
            tesis(egresado, directores[i - 1], TESIS[4 + i], 'concluido')
            egresados.append(egresado)
            EgresoAlumno.objects.update_or_create(
                alumno=egresado,
                defaults={'fecha_egreso': date(2026, 6, 15) + timedelta(days=i), 'generacion': f'{2024 + (i % 2)}-{2026}',
                          'promedio_final': Decimal('8.6') + Decimal(i) / 10, 'titulo_tesis': TESIS[4 + i],
                          'observaciones': 'Registro de datos de prueba.', 'excepcion_motivo': 'Datos de prueba (carga demo).'})
            ExpedienteDigital.objects.get_or_create(aspirante=egresado, defaults={'folio': f'EXP-DEMO-{egresado.pk:06d}'})
            credenciales.append(('Egresado', usuario, '(sin acceso)', f'{nombre} · {egresado.programa}'))

        proyecto_concluido = ProyectoTesis.objects.filter(alumno__in=egresados, estado='concluido').first()
        if proyecto_concluido:
            DefensaTesis.objects.update_or_create(
                proyecto=proyecto_concluido,
                defaults={
                    'fecha': ahora - timedelta(days=14),
                    'lugar': 'Sala de Juntas (Demostración)',
                    'modalidad': 'presencial',
                    'estado': 'realizada',
                    'observaciones': 'Defensa de demostración.',
                    'calificacion_final': Decimal('9.2'),
                },
            )
            for orden, rol, docente in zip((1, 2, 3), ('presidente', 'secretario', 'vocal'), docentes[:3]):
                JuradoProyecto.objects.update_or_create(
                    proyecto=proyecto_concluido,
                    rol=rol,
                    defaults={
                        'jurado': docente,
                        'orden': orden,
                        'estado': 'confirmado',
                        'observaciones': 'Participación de demostración.',
                        'fecha_confirmacion': ahora - timedelta(days=20),
                    },
                )

        self.stdout.write(self.style.SUCCESS(
            f'Datos demo cargados: {len(credenciales) - len(EGRESADOS)} cuentas con acceso, '
            f'{len(EGRESADOS)} egresados sin acceso y {len(materias) + 1} materias demo.'
        ))
        for rol, usuario, clave, detalle in credenciales:
            self.stdout.write(f'{rol:10} | {usuario:12} | {clave:16} | {detalle}')
