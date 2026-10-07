import hashlib
import re
import unicodedata

from django.core.management.base import BaseCommand
from django.db import transaction

from preregistro.models import ConfiguracionPrograma, Materia, PlanEstudioMateria


NUCLEO_MAESTRIA = [
    'Arquitectura de Computadoras',
    'Diseño y Análisis de Algoritmos',
    'Teoría de la Computación',
    'Programación Avanzada',
]

LGAC = {
    'Teoría de la Computación': {
        'formativos': [
            'Teoría de la Computación', 'Matemáticas Discretas', 'Aritmética Computacional',
            'Códigos y Criptografía', 'Geometría Computacional', 'Lógica Matemática',
        ],
        'topicos': [
            'Optimización en Ingeniería', 'Optimización Numérica', 'Computabilidad y Complejidad',
            'Teoría de Códigos', 'Códigos Lineales', 'Computación Científica I',
            'Algoritmos en Gráficas', 'Tópicos Selectos de Complejidad Computacional',
            'Tópicos Selectos de Criptografía', 'Tópicos Selectos de Criptografía Asimétrica',
        ],
    },
    'Inteligencia Artificial': {
        'formativos': [
            'Inteligencia Artificial', 'Procesamiento de Lenguaje Natural',
            'Introducción a la Computación Evolutiva', 'Visión', 'Aprendizaje Automático',
        ],
        'topicos': [
            'Sistemas de Agentes y Multiagentes', 'Teoría de Juegos',
            'Introducción a la Optimización Evolutiva Multiobjetivo',
            'Redes Complejas y Aprendizaje Computacional', 'Redes Neuronales Artificiales',
            'Aprendizaje Profundo',
            'Tópicos Selectos de Inteligencia Artificial: Agentes y Multiagentes',
            'Tópicos Selectos de Inteligencia Artificial: Teoría de Juegos',
            'Tópicos Selectos de Inteligencia Artificial: Redes Complejas y Aprendizaje Computacional',
            'Tópicos Selectos de Inteligencia Artificial Generativa',
        ],
    },
    'Sistemas de Cómputo': {
        'formativos': [
            'Arquitectura de Computadoras', 'Programación Avanzada',
            'Programación Orientada a Objetos', 'Cómputo Móvil', 'Computación Paralela',
            'Sistemas Distribuidos', 'Sistemas Operativos', 'Programación Concurrente',
            'Sistemas de Tiempo Real', 'Redes de Computadoras',
        ],
        'topicos': [
            'Diseño de Herramientas para Desarrollo de Sistemas Distribuidos', 'Cómputo Ubicuo',
            'Introducción al Cómputo Reconfigurable', 'Sistemas Operativos de Tiempo Real',
            'Cómputo de Alto Rendimiento I', 'Cómputo de Alto Rendimiento II',
            'Cómputo de Alto Rendimiento III', 'Programación de Dispositivos Móviles',
            'Tópicos Selectos en Cómputo Móvil', 'Tópicos Selectos en Sistemas Distribuidos: eLearning',
            'Tópicos Selectos de Sistemas Distribuidos Móviles y Ubicuos',
            'Tópicos Selectos de Sistemas Distribuidos: Computación en Internet',
            'Redes de Petri', 'Tópicos Selectos de Ingeniería: Virtualización',
        ],
    },
    'Sistemas de Información': {
        'formativos': [
            'Base de Datos', 'Lógica y Base de Datos', 'Graficación', 'Ingeniería de Software',
            'Minería de Datos', 'Lenguajes de Programación',
        ],
        'topicos': [
            'Seguridad en Sistemas de Información', 'Pruebas de Confiabilidad de Software',
            'Sistemas Colaborativos Distribuidos', 'Sistemas Distribuidos: eLearning',
            'Interacción Hombre-Máquina', 'Minería de Datos Avanzada',
            'Sistemas de Soporte a la Toma de Decisiones', 'Análisis Estadístico de Datos',
            'Visualización', 'Tópicos Selectos en Seguridad de Redes y Computación',
            'Tópicos Selectos en Interacción Hombre-Máquina',
            'Tópicos Selectos en Minería de Datos Avanzada', 'Tópicos Selectos en Sistemas Colaborativos',
        ],
    },
}

ADICIONALES = [
    'Tópicos Selectos: Sistemas de Agentes', 'Tópicos Selectos de Computación Científica I',
    'Tópicos Selectos de Computación Científica II', 'Tópicos Selectos en Cómputo Móvil',
    'Tópicos Selectos en Criptografía', 'Tópicos Selectos en Criptografía Asimétrica',
    'Tópicos Selectos en Inteligencia Artificial: Agentes y Multiagentes',
    'Tópicos Selectos en Inteligencia Artificial: Introducción a la Optimización Evolutiva Multiobjetivo',
    'Tópicos Selectos en Inteligencia Artificial: Lenguajes Formales y Máquinas de Estado',
    'Tópicos Selectos en Inteligencia Artificial: Redes Complejas y Aprendizaje Computacional',
    'Tópicos Selectos en Inteligencia Artificial: Sistemas de Soporte a la Toma de Decisiones',
    'Tópicos Selectos en Inteligencia Artificial: Teoría de Juegos',
    'Tópicos Selectos en Interacción Hombre-Máquina', 'Tópicos Selectos en Minería de Datos Avanzada',
    'Tópicos Selectos en Redes Neuronales Artificiales', 'Tópicos Selectos en Robótica Móvil',
    'Tópicos Selectos en Seguridad de Redes y Computación',
    'Tópicos Selectos en Sistemas Distribuidos: eLearning',
    'Tópicos Selectos en Sistemas Operativos de Tiempo Real', 'Tópicos Selectos en Teoría de Códigos',
    'Tópicos Selectos en Visualización', 'Visión', 'Redes de Petri',
]

SEMINARIOS_MAESTRIA = [
    'Seminario de Tesis de Maestría I', 'Seminario de Tesis de Maestría II',
    'Seminario de Tesis de Maestría III', 'Trabajo de Tesis', 'Seminario de Investigación',
]

DOCTORADO_EXTRA = [
    'Interfaces Conscientes del Contexto', 'Métodos de Evaluación de Interfaces de Usuario',
    'Tópicos Avanzados de IA', 'Tópicos Avanzados relacionados con las LGAC',
    'Seminario de Investigación I', 'Seminario de Investigación II',
    'Seminario de Investigación III', 'Seminario de Investigación IV',
] + [f'Trabajo de Tesis {roman}' for roman in (
    'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII'
)]


def clave_materia(nombre):
    normalizado = unicodedata.normalize('NFKD', nombre).encode('ascii', 'ignore').decode().upper()
    slug = re.sub(r'[^A-Z0-9]+', '-', normalizado).strip('-')
    digest = hashlib.sha1(nombre.encode('utf-8')).hexdigest()[:6].upper()
    return f'CC-{slug[:31]}-{digest}'[:40]


def catalogo_nombres():
    nombres = list(NUCLEO_MAESTRIA)
    for grupos in LGAC.values():
        nombres.extend(grupos['formativos'])
        nombres.extend(grupos['topicos'])
    nombres.extend(ADICIONALES, )
    nombres.extend(SEMINARIOS_MAESTRIA)
    nombres.extend(DOCTORADO_EXTRA)
    return list(dict.fromkeys(nombres))


def catalogo_metadata():
    metadata = {nombre: {'categoria': 'formativo', 'lgacs': []} for nombre in catalogo_nombres()}
    for nombre in NUCLEO_MAESTRIA:
        metadata[nombre] = {'categoria': 'nucleo', 'lgacs': []}
    for lgac, grupos in LGAC.items():
        for nombre in grupos['formativos']:
            if nombre not in NUCLEO_MAESTRIA:
                metadata[nombre]['categoria'] = 'formativo'
            if lgac not in metadata[nombre]['lgacs']:
                metadata[nombre]['lgacs'].append(lgac)
        for nombre in grupos['topicos']:
            metadata[nombre]['categoria'] = 'especializacion'
            if lgac not in metadata[nombre]['lgacs']:
                metadata[nombre]['lgacs'].append(lgac)
    for nombre in ADICIONALES:
        metadata[nombre]['categoria'] = 'adicional'
    for nombre in SEMINARIOS_MAESTRIA + DOCTORADO_EXTRA:
        metadata[nombre]['categoria'] = 'tesis' if nombre.startswith('Trabajo de Tesis') else 'seminario'
    return metadata


class Command(BaseCommand):
    help = 'Carga de forma idempotente el catalogo y los planes de Computacion.'

    @transaction.atomic
    def handle(self, *args, **options):
        materias = {}
        metadata = catalogo_metadata()
        for nombre in catalogo_nombres():
            materia, creada = Materia.objects.get_or_create(
                clave=clave_materia(nombre),
                defaults={'nombre': nombre, 'creditos': 4, **metadata[nombre]},
            )
            if not creada:
                materia.nombre = nombre
                materia.categoria = metadata[nombre]['categoria']
                materia.lgacs = metadata[nombre]['lgacs']
                materia.save(update_fields=['nombre', 'categoria', 'lgacs', 'updated_at'])
            materias[nombre] = materia

        maestria, _ = ConfiguracionPrograma.objects.update_or_create(
            programa='Maestría en Ciencias en Computación',
            defaults={'grado': 'maestria', 'periodicidad': 'semestral', 'periodos_requeridos': 4, 'creditos_requeridos': 16, 'activo': True},
        )
        doctorado, _ = ConfiguracionPrograma.objects.update_or_create(
            programa='Doctorado en Ciencias en Computación',
            defaults={'grado': 'doctorado', 'periodicidad': 'semestral', 'periodos_requeridos': 12, 'creditos_requeridos': 16, 'activo': True},
        )

        for index, nombre in enumerate(catalogo_nombres(), start=1):
            materia = materias[nombre]
            es_nucleo = nombre in NUCLEO_MAESTRIA
            PlanEstudioMateria.objects.update_or_create(
                configuracion=maestria, materia=materia,
                defaults={'periodo_sugerido': 1 if es_nucleo else 2 + ((index - 1) % 3), 'obligatoria': es_nucleo},
            )

        nombres_doctorado = list(dict.fromkeys(
            [nombre for grupos in LGAC.values() for nombre in grupos['topicos']]
            + [nombre for nombre in DOCTORADO_EXTRA]
        ))
        for index, nombre in enumerate(nombres_doctorado, start=1):
            materia = materias[nombre]
            PlanEstudioMateria.objects.update_or_create(
                configuracion=doctorado, materia=materia,
                defaults={'periodo_sugerido': 1 + ((index - 1) % 12), 'obligatoria': True},
            )

        self.stdout.write(self.style.SUCCESS(
            f'Catalogo cargado: {len(materias)} materias, '
            f'{maestria.materias_plan.count()} materias en Maestria y '
            f'{doctorado.materias_plan.count()} materias en Doctorado.'
        ))
