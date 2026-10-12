from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from preregistro.models import (
    Aspirante, EgresoAlumno, ExpedienteDigital, Inscripcion, Materia, PeriodoInscripcion, ProyectoTesis,
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


class Command(BaseCommand):
    help = 'Carga de forma idempotente usuarios de prueba. Los egresados son registros sin acceso al sistema.'

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

        for i, nombre in enumerate(ASPIRANTES, 1):
            usuario, clave = f'asp.demo{i}', _password('Asp', i)
            self._persona(usuario, nombre, 'aspirante', 30 + i, clave, PROGRAMAS[i - 1], proceso_estado='pendiente')
            credenciales.append(('Aspirante', usuario, clave, nombre))

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
                                   matricula=f'DEMO-A{i:03d}', numero_periodo_actual=2, director_tesis=directores[i - 1], tutor_propuesto=directores[i - 1].nombre)
            inscribir(alumno, i - 1, previo, 0)
            inscribir(alumno, i + 1, actual, 1)
            tesis(alumno, directores[i - 1], TESIS[i - 1], ('borrador', 'en_revision', 'observado', 'aprobado', 'en_revision')[i - 1])
            alumnos.append(alumno)
            credenciales.append(('Alumno', usuario, clave, f'{nombre} · {alumno.programa}'))

        for i, nombre in enumerate(EGRESADOS, 1):
            usuario, clave = f'egr.demo{i}', None
            egresado = self._persona(usuario, nombre, 'alumno', 50 + i, clave, PROGRAMAS[(i + 1) % len(PROGRAMAS)], proceso_estado='egresado',
                                     matricula=f'DEMO-E{i:03d}', numero_periodo_actual=4, director_tesis=directores[i - 1], tutor_propuesto=directores[i - 1].nombre)
            inscribir(egresado, i + 3, previo, 2)
            inscribir(egresado, i + 5, actual, 3)
            tesis(egresado, directores[i - 1], TESIS[4 + i], 'concluido')
            EgresoAlumno.objects.update_or_create(
                alumno=egresado,
                defaults={'fecha_egreso': date(2026, 6, 15) + timedelta(days=i), 'generacion': f'{2024 + (i % 2)}-{2026}',
                          'promedio_final': Decimal('8.6') + Decimal(i) / 10, 'titulo_tesis': TESIS[4 + i],
                          'observaciones': 'Registro de datos de prueba.', 'excepcion_motivo': 'Datos de prueba (carga demo).'})
            ExpedienteDigital.objects.get_or_create(aspirante=egresado, defaults={'folio': f'EXP-DEMO-{egresado.pk:06d}'})
            credenciales.append(('Egresado', usuario, '(sin acceso)', f'{nombre} · {egresado.programa}'))

        self.stdout.write(self.style.SUCCESS('Datos de prueba cargados.'))
        for rol, usuario, clave, detalle in credenciales:
            self.stdout.write(f'{rol:10} | {usuario:12} | {clave:16} | {detalle}')
