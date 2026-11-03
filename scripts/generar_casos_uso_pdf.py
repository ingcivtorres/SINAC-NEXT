"""Genera docs/SINAC_NEXT_Casos_de_Uso.pdf con los casos de uso general y específicos."""
import math
import os

from reportlab.graphics.shapes import Circle, Drawing, Ellipse, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents

from plantilla_cinvestav import (
    ANCHO_UTIL, BORDE, GRIS, GRIS_CLARO, RAIZ, VERDE, VERDE_CLARO, VERDE_OSCURO, Documento,
    borde_elipse, canvas_numerado, celda, celda_cab, celda_neg, cuerpo, envolver, h1, h2, h3,
    pie_fig, portada, tabla, texto_centrado, titulo, toc_estilos, vineta,
)

SALIDA = os.path.join(RAIZ, 'docs', 'SINAC_NEXT_Casos_de_Uso.pdf')
TITULO = 'Casos de Uso general y específicos'

# ---------------------------------------------------------------------------
# Contenido: actores y casos de uso
# ---------------------------------------------------------------------------
ACTORES = [
    ('Aspirante', 'Persona externa que solicita su admisión a un programa de posgrado. Se registra, carga documentos, presenta exámenes y entrevistas y da seguimiento a su solicitud.'),
    ('Alumno', 'Estudiante inscrito en un programa. Realiza su inscripción, consulta calificaciones, horario y avance, gestiona su proyecto de tesis y solicita trámites.'),
    ('Docente', 'Profesor investigador que imparte materias, captura calificaciones, aplica exámenes en línea, conduce entrevistas y participa en el Colegio de Profesores y en jurados.'),
    ('Director de tesis', 'Docente que dirige proyectos de tesis. Acepta solicitudes de dirección, da seguimiento a avances, integra el jurado y programa el examen predoctoral y la defensa.'),
    ('Coordinación Académica', 'Responsable de la operación académica del programa: admisión de aspirantes, cargas académicas, inscripciones, asignación de directores y notificaciones.'),
    ('Servicios Escolares', 'Área responsable del control escolar: expedientes, planes, periodos, validación de inscripciones, historial, constancias, egreso y reportes institucionales.'),
    ('Administrador', 'Responsable técnico del sistema: usuarios, roles, catálogos, periodos, seguridad, auditoría, mantenimiento y configuración general.'),
    ('Motor LIDA (Camunda)', 'Actor de sistema. Ejecuta los procesos modelados con el lenguaje iconográfico LIDA (BPMN) y coordina las tareas de admisión y cargas académicas.'),
    ('Servidor de correo', 'Actor de sistema. Entrega las notificaciones y avisos generados por el sistema a los usuarios.'),
]

AUTENTICARSE = 'Autenticarse en el sistema'

# Casos de uso generales por actor: (nombre, descripción, casos específicos que agrupa)
GENERALES = {
    'COO': [
        ('Gestionar admisión de aspirantes', 'Revisa solicitudes y documentos, registra el dictamen del Colegio, resuelve el estado y convierte aspirantes en alumnos.', ['CU-COO-02', 'CU-COO-03', 'CU-COO-04', 'CU-COO-05', 'CU-COO-06']),
        ('Gestionar operación académica', 'Administra periodos, cargas académicas, inscripciones y solicitudes académicas del programa.', ['CU-COO-07', 'CU-COO-08', 'CU-COO-09']),
        ('Gestionar seguimiento de tesis', 'Asigna directores de tesis y supervisa proyectos y exámenes predoctorales.', ['CU-COO-10', 'CU-COO-11']),
        ('Gestionar exámenes en línea', 'Consulta y administra los exámenes en línea del programa.', ['CU-COO-12']),
        ('Comunicar y generar reportes', 'Consulta indicadores, envía notificaciones masivas y obtiene reportes e histórico.', ['CU-COO-01', 'CU-COO-13', 'CU-COO-14']),
    ],
    'SE': [
        ('Gestionar expedientes de alumnos y docentes', 'Consulta indicadores, administra alumnos y consulta el directorio de docentes.', ['CU-SE-01', 'CU-SE-02', 'CU-SE-03']),
        ('Gestionar control académico', 'Administra planes y periodos, valida cargas, inscripciones y calificaciones y atiende solicitudes.', ['CU-SE-04', 'CU-SE-05', 'CU-SE-06', 'CU-SE-08', 'CU-SE-11']),
        ('Emitir documentos oficiales', 'Genera historiales académicos y constancias.', ['CU-SE-07', 'CU-SE-09']),
        ('Gestionar egreso', 'Registra el egreso y consulta egresados e histórico.', ['CU-SE-10', 'CU-SE-12']),
        ('Generar reportes institucionales', 'Descarga reportes de control escolar.', ['CU-SE-13']),
    ],
    'ASP': [
        ('Registrarse en el proceso de admisión', 'Crea su cuenta e inicia el proceso de admisión LIDA.', ['CU-ASP-01']),
        ('Integrar expediente de admisión', 'Carga sus documentos y mantiene actualizado su perfil.', ['CU-ASP-03', 'CU-ASP-08']),
        ('Presentar evaluaciones de admisión', 'Presenta exámenes en línea y entrevistas virtuales.', ['CU-ASP-04', 'CU-ASP-05']),
        ('Dar seguimiento a la solicitud', 'Consulta el avance del proceso, el dictamen y sus notificaciones.', ['CU-ASP-02', 'CU-ASP-06']),
        ('Solicitar apoyo económico', 'Registra su solicitud de apoyo con datos bancarios.', ['CU-ASP-07']),
    ],
    'ALU': [
        ('Consultar situación académica', 'Consulta avance, calificaciones y horario.', ['CU-ALU-01', 'CU-ALU-03']),
        ('Gestionar inscripción', 'Inscribe materias en el periodo vigente o de forma extemporánea.', ['CU-ALU-02']),
        ('Presentar evaluaciones', 'Presenta exámenes en línea y consulta su examen predoctoral.', ['CU-ALU-04', 'CU-ALU-08']),
        ('Gestionar tesis', 'Solicita director y da seguimiento a su proyecto de tesis.', ['CU-ALU-06', 'CU-ALU-07']),
        ('Realizar trámites', 'Envía solicitudes académicas, obtiene documentos y su diploma digital.', ['CU-ALU-05', 'CU-ALU-09', 'CU-ALU-10']),
    ],
    'DOC': [
        ('Gestionar cursos', 'Consulta su panel, cursos asignados y estudiantes.', ['CU-DOC-01', 'CU-DOC-02']),
        ('Evaluar estudiantes', 'Captura calificaciones, gestiona exámenes en línea y genera reportes.', ['CU-DOC-03', 'CU-DOC-04', 'CU-DOC-07']),
        ('Participar en la admisión', 'Conduce entrevistas y evalúa aspirantes en el Colegio de Profesores.', ['CU-DOC-05', 'CU-DOC-06']),
        ('Gestionar perfil académico', 'Mantiene actualizados sus datos.', ['CU-DOC-08']),
    ],
    'DIR': [
        ('Supervisar tesistas', 'Consulta analítica, tesistas y sus expedientes.', ['CU-DIR-01', 'CU-DIR-03']),
        ('Dirigir proyecto de tesis', 'Acepta la dirección, da seguimiento a avances y registra la revisión antiplagio.', ['CU-DIR-02', 'CU-DIR-04', 'CU-DIR-07']),
        ('Gestionar evaluaciones de grado', 'Programa el predoctoral, integra el jurado y registra la defensa.', ['CU-DIR-05', 'CU-DIR-06', 'CU-DIR-08']),
    ],
    'ADM': [
        ('Administrar usuarios', 'Gestiona usuarios, roles, alumnos y docentes.', ['CU-ADM-02', 'CU-ADM-03']),
        ('Administrar catálogos y periodos', 'Mantiene catálogos institucionales y periodos.', ['CU-ADM-04', 'CU-ADM-05']),
        ('Supervisar la operación', 'Consulta indicadores, solicitudes, reportes y auditoría.', ['CU-ADM-01', 'CU-ADM-06', 'CU-ADM-07', 'CU-ADM-08']),
        ('Configurar el sistema', 'Ajusta seguridad, mantenimiento y parámetros generales.', ['CU-ADM-09']),
    ],
}


def cu(id_, nombre, descripcion, pre, flujo, alternos, post, secundarios=(), relaciones=()):
    return {
        'id': id_, 'nombre': nombre, 'descripcion': descripcion, 'pre': pre, 'flujo': flujo,
        'alternos': alternos, 'post': post, 'secundarios': list(secundarios), 'relaciones': list(relaciones),
    }


PRE_SESION = 'El usuario inició sesión con una cuenta activa del rol correspondiente.'

ROLES = [
    {
        'nombre': 'Coordinación Académica',
        'actor': 'Coordinación Académica',
        'sigla': 'COO',
        'intro': ('La Coordinación Académica conduce el proceso de admisión y la operación académica del programa. '
                  'Desde su panel revisa la bandeja de aspirantes, valida documentos, registra la evaluación del Colegio de Profesores, '
                  'resuelve el estado de cada solicitud, gestiona periodos y cargas académicas apoyadas en el motor LIDA (Camunda), '
                  'atiende inscripciones y solicitudes académicas, asigna directores de tesis y envía notificaciones masivas.'),
        'casos': [
            cu('CU-COO-01', 'Consultar resumen de coordinación',
               'Muestra indicadores de aspirantes por estado, alumnos activos, pendientes de revisión y accesos rápidos.',
               [PRE_SESION],
               ['El actor abre el panel de Coordinación.', 'El sistema calcula y presenta los indicadores del programa.', 'El actor selecciona un indicador para ir a la sección relacionada.'],
               ['Si no hay registros, el sistema muestra los indicadores en cero con un mensaje informativo.'],
               ['El actor conoce el estado general del programa.']),
            cu('CU-COO-02', 'Revisar bandeja de aspirantes',
               'Permite buscar, filtrar y abrir el detalle de las solicitudes de admisión recibidas.',
               [PRE_SESION, 'Existen aspirantes con preregistro concluido.'],
               ['El actor abre la bandeja de aspirantes.', 'El sistema lista solicitudes con paginación, búsqueda y filtros por estado y programa.', 'El actor selecciona un aspirante.', 'El sistema muestra datos personales, documentos, exámenes, entrevistas y seguimiento LIDA.'],
               ['Si la búsqueda no tiene coincidencias, se muestra un estado vacío.'],
               ['El detalle del aspirante queda disponible para su revisión.'],
               relaciones=[('include', 'Consultar expediente del aspirante')]),
            cu('CU-COO-03', 'Revisar documentos del aspirante',
               'Valida cada documento cargado por el aspirante y registra observaciones.',
               [PRE_SESION, 'El aspirante cargó al menos un documento.'],
               ['El actor abre el detalle del aspirante.', 'El sistema muestra la lista de documentos con enlace firmado y caducable.', 'El actor visualiza el documento y lo marca como revisado o agrega una observación.', 'El sistema guarda la revisión y la registra en el histórico.'],
               ['Si el enlace expiró, el sistema genera uno nuevo al volver a solicitarlo.', 'Si el documento es ilegible, el actor registra una observación para que el aspirante lo reemplace.'],
               ['El documento queda marcado como revisado u observado.']),
            cu('CU-COO-04', 'Resolver estado del aspirante',
               'Cambia el estado de la solicitud (en revisión, aceptado, rechazado, baja) y notifica al aspirante.',
               [PRE_SESION, 'Los documentos obligatorios fueron revisados.'],
               ['El actor selecciona el nuevo estado de la solicitud.', 'El sistema valida que la transición sea permitida.', 'El sistema actualiza el estado, avanza la tarea correspondiente en el motor LIDA y notifica al aspirante.', 'El sistema registra el movimiento en el histórico.'],
               ['Si faltan documentos por revisar, el sistema impide la aceptación y lo indica.', 'Si el motor LIDA no responde, se conserva el estado y se informa el error para reintentar.'],
               ['La solicitud queda resuelta y el aspirante ya no puede modificar sus documentos.'],
               secundarios=['Motor LIDA (Camunda)', 'Servidor de correo'],
               relaciones=[('include', 'Notificar al aspirante')]),
            cu('CU-COO-05', 'Registrar evaluación del Colegio de Profesores',
               'Captura el dictamen colegiado sobre el aspirante a partir de exámenes y entrevistas.',
               [PRE_SESION, 'El aspirante presentó exámenes y entrevista.'],
               ['El actor abre la sección Colegio.', 'El sistema muestra los resultados de exámenes y entrevistas del aspirante.', 'El actor registra el dictamen y sus observaciones.', 'El sistema guarda la evaluación y la hace visible en el seguimiento del aspirante.'],
               ['Si ya existe una evaluación, el actor puede actualizarla antes de resolver la solicitud.'],
               ['El dictamen queda registrado y disponible para resolver la solicitud.'],
               secundarios=['Docente']),
            cu('CU-COO-06', 'Convertir aspirante en alumno',
               'Genera la cuenta de alumno a partir de un aspirante aceptado o lo da de baja.',
               [PRE_SESION, 'El aspirante tiene estado aceptado.'],
               ['El actor selecciona al aspirante aceptado.', 'El actor elige la opción "Convertir en alumno".', 'El sistema asigna matrícula, programa y periodo de ingreso y cambia el rol a alumno.', 'El sistema registra el alta en el histórico y notifica al usuario.'],
               ['Si el aspirante no está aceptado, la acción no se habilita.', 'El actor puede dar de baja la solicitud indicando el motivo.'],
               ['La persona accede al sistema con el panel de Alumno.'],
               secundarios=['Servidor de correo']),
            cu('CU-COO-07', 'Gestionar periodos y cargas académicas',
               'Define periodos y asigna materias a docentes mediante el proceso LIDA de cargas académicas.',
               [PRE_SESION, 'Existen materias y docentes registrados.'],
               ['El actor abre la sección de cargas académicas.', 'El sistema muestra las materias disponibles del periodo.', 'El actor asigna materias a los docentes y envía la carga.', 'El sistema inicia o avanza la instancia del proceso en el motor LIDA.', 'El sistema confirma el registro de la carga.'],
               ['Si una materia ya está asignada en el periodo, el sistema lo advierte.', 'El actor puede importar materias desde un archivo CSV validado.'],
               ['La carga académica queda registrada y visible para el docente.'],
               secundarios=['Motor LIDA (Camunda)'],
               relaciones=[('extend', 'Importar materias desde CSV')]),
            cu('CU-COO-08', 'Gestionar inscripciones regulares y extemporáneas',
               'Revisa inscripciones de alumnos y resuelve solicitudes de inscripción extemporánea.',
               [PRE_SESION, 'Existe un periodo de inscripción configurado.'],
               ['El actor abre la sección de inscripciones.', 'El sistema lista inscripciones y solicitudes extemporáneas con filtros.', 'El actor revisa la solicitud y la aprueba o rechaza con comentario.', 'El sistema actualiza el estado y notifica al alumno.'],
               ['Si la solicitud extemporánea carece de justificación, el actor la rechaza.'],
               ['La inscripción queda resuelta y registrada en el histórico.'],
               secundarios=['Alumno']),
            cu('CU-COO-09', 'Atender solicitudes académicas',
               'Revisa y responde solicitudes académicas enviadas por los alumnos.',
               [PRE_SESION, 'Existen solicitudes pendientes.'],
               ['El actor abre la sección de solicitudes académicas.', 'El sistema muestra las solicitudes con su tipo y estado.', 'El actor responde y cambia el estado.', 'El sistema notifica al alumno.'],
               ['Si la solicitud corresponde a otra área, el actor la deriva con un comentario.'],
               ['La solicitud queda atendida.'],
               secundarios=['Alumno']),
            cu('CU-COO-10', 'Asignar director de tesis',
               'Revisa la solicitud de dirección y asigna o confirma al director de tesis del alumno.',
               [PRE_SESION, 'El alumno envió una solicitud de dirección de tesis.'],
               ['El actor abre la sección de asignaciones.', 'El sistema muestra la línea de investigación, el director sugerido y el estado.', 'El actor asigna al director.', 'El sistema vincula al director con el alumno y registra el evento para ambos.'],
               ['Si el director sugerido no está disponible, el actor elige otro docente.'],
               ['El alumno queda vinculado a su director de tesis.'],
               secundarios=['Director de tesis']),
            cu('CU-COO-11', 'Revisar proyectos de tesis y predoctoral',
               'Supervisa los proyectos de tesis registrados y los exámenes predoctorales.',
               [PRE_SESION],
               ['El actor abre la sección de tesis o predoctoral.', 'El sistema lista proyectos o exámenes con su estado.', 'El actor registra una revisión con comentario.', 'El sistema actualiza el estado.'],
               ['Si el proyecto requiere cambios, se devuelve al alumno con observaciones.'],
               ['El proyecto o examen queda con su estado actualizado.']),
            cu('CU-COO-12', 'Gestionar exámenes en línea',
               'Consulta y administra los exámenes en línea del proceso de admisión y del programa.',
               [PRE_SESION],
               ['El actor abre la sección de exámenes.', 'El sistema lista exámenes con fechas, intentos y resultados.', 'El actor consulta resultados o ajusta la disponibilidad.'],
               ['Si el examen ya tiene intentos registrados, ciertas ediciones se bloquean.'],
               ['La información de exámenes queda actualizada.']),
            cu('CU-COO-13', 'Enviar notificaciones masivas',
               'Envía avisos a grupos de aspirantes o alumnos filtrados.',
               [PRE_SESION],
               ['El actor redacta el aviso y selecciona destinatarios por filtro.', 'El sistema muestra el número de destinatarios.', 'El actor confirma el envío.', 'El sistema crea las notificaciones internas y envía los correos.'],
               ['Si no hay destinatarios para el filtro, el envío no se habilita.'],
               ['Los destinatarios reciben la notificación.'],
               secundarios=['Servidor de correo']),
            cu('CU-COO-14', 'Consultar egresados, histórico y reportes',
               'Consulta el directorio de egresados, la línea de tiempo histórica por persona y descarga reportes.',
               [PRE_SESION],
               ['El actor abre la sección de histórico, egresados o reportes.', 'El sistema muestra el resumen, los filtros y los eventos.', 'El actor filtra por categoría, programa, responsable o fechas, o abre la línea de tiempo de una persona.', 'El actor descarga el reporte en XLSX o PDF.'],
               ['Si el resultado excede el límite, el sistema indica que la lista está truncada.'],
               ['El actor obtiene la información requerida.'],
               relaciones=[('extend', 'Descargar reporte XLSX/PDF')]),
        ],
    },
    {
        'nombre': 'Servicios Escolares',
        'actor': 'Servicios Escolares',
        'sigla': 'SE',
        'intro': ('Servicios Escolares mantiene el control escolar institucional. Administra los expedientes de alumnos y el '
                  'directorio de docentes, los planes de estudio y periodos, valida inscripciones y calificaciones, emite historiales '
                  'y constancias, registra el egreso y genera reportes institucionales.'),
        'casos': [
            cu('CU-SE-01', 'Consultar resumen escolar',
               'Presenta indicadores de alumnos por estatus, inscripciones pendientes y trámites.',
               [PRE_SESION],
               ['El actor abre el panel de Servicios Escolares.', 'El sistema calcula y muestra los indicadores.', 'El actor navega a la sección deseada.'],
               ['Sin datos, el sistema muestra indicadores en cero.'],
               ['El actor conoce el estado del control escolar.']),
            cu('CU-SE-02', 'Gestionar alumnos',
               'Da de alta, edita y cambia el estatus (activo, baja, reingreso, egresado) de los alumnos.',
               [PRE_SESION],
               ['El actor abre la sección de alumnos.', 'El sistema lista alumnos con búsqueda, filtros y paginación.', 'El actor registra un alumno nuevo o edita uno existente.', 'El sistema valida CURP, correo, matrícula y programa y guarda los cambios.', 'El sistema registra el movimiento en el histórico.'],
               ['Si la CURP, el usuario o la matrícula ya existen, se muestra el error en el campo.', 'Al cambiar a baja, el sistema solicita el motivo.'],
               ['El expediente del alumno queda actualizado.'],
               relaciones=[('include', 'Consultar expediente del alumno')]),
            cu('CU-SE-03', 'Consultar directorio de docentes',
               'Consulta los docentes, su departamento y la carga académica asignada.',
               [PRE_SESION],
               ['El actor abre el directorio de docentes.', 'El sistema muestra la tabla con búsqueda y filtros.', 'El actor consulta el detalle de un docente.'],
               ['Sin coincidencias, se muestra un estado vacío.'],
               ['El actor obtiene la información del docente.']),
            cu('CU-SE-04', 'Gestionar planes de estudio y periodos',
               'Administra planes de estudio y periodos escolares con sus fechas de inscripción.',
               [PRE_SESION],
               ['El actor abre planes o periodos.', 'El sistema muestra los registros vigentes.', 'El actor crea o modifica un periodo indicando fechas.', 'El sistema valida que las fechas sean coherentes y guarda.'],
               ['Si las fechas se traslapan con otro periodo, el sistema rechaza el registro.'],
               ['El periodo queda disponible para inscripciones.']),
            cu('CU-SE-05', 'Validar cargas y solicitudes extemporáneas',
               'Consulta cargas académicas y valida las solicitudes de inscripción extemporánea.',
               [PRE_SESION, 'Existen cargas o solicitudes registradas.'],
               ['El actor abre la sección correspondiente.', 'El sistema lista las solicitudes con su justificación.', 'El actor valida u observa la solicitud.', 'El sistema notifica al alumno y actualiza el estado.'],
               ['El actor puede generar el oficio de autorización en PDF.'],
               ['La solicitud queda validada u observada.'],
               secundarios=['Alumno'], relaciones=[('extend', 'Generar oficio PDF')]),
            cu('CU-SE-06', 'Validar inscripciones',
               'Revisa la inscripción de materias del alumno y la valida u observa.',
               [PRE_SESION, 'El alumno envió su inscripción.'],
               ['El actor abre la sección de inscripciones.', 'El sistema muestra las materias inscritas por alumno.', 'El actor valida u observa la inscripción.', 'El sistema actualiza el estado y lo registra en el histórico.'],
               ['Si la inscripción incumple el mínimo de materias, el actor la observa.'],
               ['La inscripción queda validada u observada.'],
               secundarios=['Alumno']),
            cu('CU-SE-07', 'Generar historial académico',
               'Genera el historial académico oficial del alumno en PDF.',
               [PRE_SESION, 'El alumno tiene calificaciones registradas.'],
               ['El actor busca al alumno.', 'El sistema muestra materias, calificaciones y promedio.', 'El actor solicita el historial.', 'El sistema genera el PDF con los datos institucionales.'],
               ['Sin calificaciones, el sistema informa que no hay información para el historial.'],
               ['Se obtiene el historial en PDF.']),
            cu('CU-SE-08', 'Consultar calificaciones',
               'Consulta y supervisa las calificaciones capturadas por los docentes.',
               [PRE_SESION],
               ['El actor abre la sección de calificaciones.', 'El sistema muestra calificaciones por periodo, materia y alumno.', 'El actor filtra y exporta la información.'],
               ['Sin capturas en el periodo, se muestra un estado vacío.'],
               ['El actor conoce el estado de las calificaciones.']),
            cu('CU-SE-09', 'Emitir constancias y documentos',
               'Emite constancias de estudios y documentos oficiales del alumno.',
               [PRE_SESION, 'El alumno está activo o egresado.'],
               ['El actor selecciona al alumno y el tipo de constancia.', 'El sistema valida el estatus del alumno.', 'El sistema genera el documento en PDF.', 'El documento queda disponible para el alumno.'],
               ['Si el alumno está dado de baja, el sistema restringe el tipo de constancia.'],
               ['La constancia queda emitida.'],
               secundarios=['Alumno']),
            cu('CU-SE-10', 'Registrar egreso',
               'Registra el egreso del alumno y habilita su diploma digital.',
               [PRE_SESION, 'El alumno concluyó créditos y aprobó su defensa.'],
               ['El actor selecciona al alumno.', 'El sistema verifica créditos y defensa aprobada.', 'El actor confirma el egreso.', 'El sistema cambia el estatus a egresado, lo registra en el histórico y habilita el diploma digital.'],
               ['Si no cumple requisitos, el sistema indica los faltantes.'],
               ['El alumno queda como egresado.'],
               relaciones=[('include', 'Verificar requisitos de egreso')]),
            cu('CU-SE-11', 'Atender solicitudes académicas',
               'Atiende las solicitudes académicas de alumnos que corresponden a control escolar.',
               [PRE_SESION],
               ['El actor abre las solicitudes académicas.', 'El sistema lista solicitudes pendientes.', 'El actor responde y cambia el estado.', 'El sistema notifica al alumno.'],
               ['Si corresponde a Coordinación, el actor la deriva.'],
               ['La solicitud queda atendida.'],
               secundarios=['Alumno']),
            cu('CU-SE-12', 'Consultar egresados e histórico',
               'Consulta el directorio de egresados y la bitácora histórica de movimientos.',
               [PRE_SESION],
               ['El actor abre egresados o histórico.', 'El sistema muestra el resumen, la actividad mensual y los eventos.', 'El actor filtra o abre la línea de tiempo de una persona.'],
               ['Sin eventos, se muestra un estado vacío.'],
               ['El actor obtiene la trazabilidad requerida.']),
            cu('CU-SE-13', 'Generar reportes institucionales',
               'Descarga reportes de alumnos, inscripciones y egresados.',
               [PRE_SESION],
               ['El actor abre la sección de reportes.', 'El actor elige el reporte y el formato.', 'El sistema genera el archivo con valores protegidos contra inyección de fórmulas.', 'El actor descarga el archivo.'],
               ['Si el reporte no tiene datos, se informa antes de descargar.'],
               ['El reporte queda descargado.'],
               relaciones=[('extend', 'Descargar reporte XLSX/PDF')]),
        ],
    },
    {
        'nombre': 'Aspirante',
        'actor': 'Aspirante',
        'sigla': 'ASP',
        'intro': ('El Aspirante interactúa con el sistema desde el preregistro hasta la resolución de su solicitud. Su panel '
                  'muestra el seguimiento del proceso LIDA, la carga de documentos, los exámenes en línea, las entrevistas '
                  'virtuales, las notificaciones y la solicitud de apoyo económico.'),
        'casos': [
            cu('CU-ASP-01', 'Registrar preregistro',
               'Crea la cuenta de aspirante e inicia el proceso de admisión en el motor LIDA.',
               ['La convocatoria del programa está vigente.'],
               ['El actor abre el formulario de preregistro.', 'El actor captura datos personales, CURP, correo, programa y contraseña y acepta el aviso de privacidad.', 'El sistema valida formato y unicidad de CURP, usuario y correo y la robustez de la contraseña.', 'El sistema crea la cuenta con rol aspirante e inicia la instancia del proceso LIDA.', 'El sistema confirma el registro.'],
               ['Si algún dato ya existe o es inválido, el sistema marca el campo con el error.', 'Si el registro excede el límite de intentos, se solicita esperar.'],
               ['El aspirante puede iniciar sesión y continuar su proceso.'],
               secundarios=['Motor LIDA (Camunda)'], relaciones=[('include', 'Validar datos del registro')]),
            cu('CU-ASP-02', 'Consultar seguimiento de la solicitud',
               'Consulta las etapas del proceso de admisión y el dictamen del Colegio.',
               [PRE_SESION],
               ['El actor abre la sección de proceso LIDA.', 'El sistema obtiene el estado del proceso y muestra las etapas completadas y pendientes.', 'El sistema muestra el dictamen del Colegio cuando existe.'],
               ['Si el motor LIDA no responde, se muestra el último estado conocido.'],
               ['El actor conoce el avance de su solicitud.'],
               secundarios=['Motor LIDA (Camunda)']),
            cu('CU-ASP-03', 'Cargar documentos de admisión',
               'Sube los documentos requeridos (CV, título, cartas) para su revisión.',
               [PRE_SESION, 'La solicitud no ha sido resuelta.'],
               ['El actor abre la sección de documentos.', 'El sistema muestra la lista de documentos requeridos y su estado.', 'El actor selecciona un archivo PDF y lo sube.', 'El sistema valida tipo real, extensión y tamaño y almacena el archivo.', 'El sistema marca el documento como pendiente de revisión.'],
               ['Si el archivo no es válido, el sistema muestra el motivo.', 'Si la solicitud ya fue resuelta, los documentos quedan en solo lectura.'],
               ['El documento queda disponible para la Coordinación.'],
               secundarios=['Coordinación Académica'], relaciones=[('extend', 'Reemplazar documento')]),
            cu('CU-ASP-04', 'Presentar examen en línea',
               'Resuelve los exámenes de admisión dentro de su ventana de disponibilidad.',
               [PRE_SESION, 'Hay un examen disponible con intentos restantes.'],
               ['El actor abre la sección de exámenes.', 'El sistema muestra exámenes, fechas e intentos.', 'El actor inicia el examen y responde; el sistema guarda el avance localmente.', 'El actor envía sus respuestas.', 'El sistema califica y registra el intento.'],
               ['Si el tiempo termina, el sistema envía automáticamente las respuestas.', 'Si falla el envío, el actor puede reintentar sin perder respuestas.'],
               ['El intento queda registrado.'],
               relaciones=[('include', 'Enviar respuestas')]),
            cu('CU-ASP-05', 'Consultar entrevistas virtuales',
               'Consulta la fecha, hora y estado de sus entrevistas y se une a la sesión.',
               [PRE_SESION, 'Un docente programó una entrevista.'],
               ['El actor abre la sección de entrevistas.', 'El sistema muestra las entrevistas sin las notas privadas del docente.', 'Cuando la entrevista está iniciada, el actor se une mediante el enlace seguro.'],
               ['Si la entrevista no ha iniciado, el enlace no se habilita.'],
               ['El actor participa en la entrevista.'],
               secundarios=['Docente'], relaciones=[('extend', 'Unirse a videollamada')]),
            cu('CU-ASP-06', 'Consultar notificaciones',
               'Revisa avisos del proceso y los marca como leídos.',
               [PRE_SESION],
               ['El sistema muestra el contador de notificaciones no leídas.', 'El actor abre la sección de notificaciones.', 'El actor marca una notificación como leída.', 'El sistema actualiza el contador.'],
               ['Sin notificaciones, se muestra un estado vacío.'],
               ['Las notificaciones quedan leídas.']),
            cu('CU-ASP-07', 'Solicitar apoyo económico',
               'Registra la solicitud de apoyo con sus datos bancarios.',
               [PRE_SESION, 'El apoyo aún no está autorizado.'],
               ['El actor abre la solicitud de apoyo.', 'El actor captura banco y CLABE.', 'El sistema valida los 18 dígitos y el dígito verificador de la CLABE.', 'El sistema guarda la solicitud.'],
               ['Si la CLABE es inválida, se informa el error.', 'Si el apoyo ya fue autorizado, los datos no pueden modificarse.'],
               ['La solicitud de apoyo queda registrada.'],
               relaciones=[('include', 'Validar CLABE')]),
            cu('CU-ASP-08', 'Actualizar perfil',
               'Actualiza teléfono, datos de contacto y fotografía.',
               [PRE_SESION],
               ['El actor abre su perfil.', 'El actor modifica teléfono o fotografía.', 'El sistema valida el formato del teléfono y la imagen.', 'El sistema guarda los cambios.'],
               ['Si un campo es inválido, se marca el error; la matrícula es de solo lectura.'],
               ['El perfil queda actualizado.']),
        ],
    },
    {
        'nombre': 'Alumno',
        'actor': 'Alumno',
        'sigla': 'ALU',
        'intro': ('El Alumno utiliza el sistema durante toda su trayectoria académica: inscripción de materias, consulta de '
                  'calificaciones, avance y horario, exámenes en línea, solicitudes académicas, proyecto de tesis, examen '
                  'predoctoral, documentos y trámites, hasta la obtención de su diploma digital.'),
        'casos': [
            cu('CU-ALU-01', 'Consultar resumen y avance académico',
               'Consulta créditos cursados, promedio, materias en curso y estado de su tesis.',
               [PRE_SESION],
               ['El actor abre su panel.', 'El sistema calcula avance de créditos y promedio.', 'El sistema muestra materias en curso, avisos y estado de tesis.'],
               ['Sin calificaciones, el avance se muestra en cero.'],
               ['El actor conoce su situación académica.']),
            cu('CU-ALU-02', 'Inscribir materias del periodo',
               'Selecciona y envía las materias a cursar en el periodo vigente.',
               [PRE_SESION, 'Existe un periodo de inscripción abierto.'],
               ['El actor abre la sección de materias e inscripciones.', 'El sistema muestra la oferta del periodo.', 'El actor selecciona las materias y envía la inscripción.', 'El sistema valida periodo, cupo y número mínimo de materias.', 'El sistema registra la inscripción pendiente de validación.'],
               ['Si el periodo está cerrado, el actor puede solicitar inscripción extemporánea con justificación.', 'Si no cumple el mínimo de materias, el sistema lo indica.'],
               ['La inscripción queda enviada a Servicios Escolares.'],
               secundarios=['Servicios Escolares'],
               relaciones=[('include', 'Validar periodo y cupo'), ('extend', 'Solicitar inscripción extemporánea')]),
            cu('CU-ALU-03', 'Consultar calificaciones y horario',
               'Consulta calificaciones por periodo y su horario de clases.',
               [PRE_SESION],
               ['El actor abre calificaciones o horario.', 'El sistema muestra calificaciones por materia y el horario semanal.', 'El actor descarga la información.'],
               ['Sin capturas, se muestra un estado vacío.'],
               ['El actor consulta su información académica.']),
            cu('CU-ALU-04', 'Presentar examen en línea',
               'Resuelve los exámenes asignados por sus docentes.',
               [PRE_SESION, 'Hay un examen disponible.'],
               ['El actor inicia el examen.', 'El actor responde y envía.', 'El sistema califica y registra el intento.'],
               ['Al terminar el tiempo, se envía automáticamente.'],
               ['El intento queda registrado.'],
               secundarios=['Docente']),
            cu('CU-ALU-05', 'Enviar solicitud académica',
               'Envía solicitudes (baja de materia, cambio, revisión) y consulta su respuesta.',
               [PRE_SESION],
               ['El actor abre solicitudes académicas.', 'El actor elige el tipo y describe la solicitud.', 'El sistema registra la solicitud y notifica al área responsable.', 'El actor consulta la respuesta.'],
               ['Si faltan datos obligatorios, el sistema lo indica.'],
               ['La solicitud queda registrada.'],
               secundarios=['Coordinación Académica']),
            cu('CU-ALU-06', 'Solicitar director de tesis',
               'Propone una línea de investigación y un director sugerido.',
               [PRE_SESION, 'El alumno no tiene director asignado.'],
               ['El actor abre proyecto de tesis.', 'El actor captura la línea de investigación y sugiere un director.', 'El sistema registra la solicitud.', 'El director y la Coordinación reciben la solicitud.'],
               ['Si ya existe una solicitud pendiente, el sistema impide duplicarla.'],
               ['La solicitud de dirección queda en revisión.'],
               secundarios=['Director de tesis', 'Coordinación Académica']),
            cu('CU-ALU-07', 'Gestionar proyecto de tesis',
               'Registra el proyecto, consulta avances, jurado, revisión antiplagio y defensa.',
               [PRE_SESION, 'El alumno tiene director asignado.'],
               ['El actor registra título y resumen del proyecto.', 'El sistema lo envía a revisión del director.', 'El actor consulta el porcentaje de avance, el jurado y el resultado antiplagio.', 'El actor consulta la fecha y el resultado de su defensa.'],
               ['Si el director observa el proyecto, el actor lo corrige y reenvía.'],
               ['El proyecto queda actualizado.'],
               secundarios=['Director de tesis']),
            cu('CU-ALU-08', 'Consultar examen predoctoral',
               'Consulta la programación y el resultado del examen predoctoral.',
               [PRE_SESION, 'El director programó el examen.'],
               ['El actor abre la sección de predoctoral.', 'El sistema muestra fecha, sinodales y resultado.'],
               ['Si no está programado, se informa.'],
               ['El actor conoce el estado de su predoctoral.']),
            cu('CU-ALU-09', 'Gestionar documentos y trámites',
               'Solicita y descarga constancias y documentos oficiales.',
               [PRE_SESION],
               ['El actor abre documentos y trámites.', 'El actor solicita una constancia.', 'El sistema registra el trámite.', 'El actor descarga el documento emitido.'],
               ['Si el documento aún no se emite, se muestra en proceso.'],
               ['El actor obtiene su documento.'],
               secundarios=['Servicios Escolares']),
            cu('CU-ALU-10', 'Descargar diploma digital',
               'Descarga el diploma digital una vez registrado su egreso.',
               [PRE_SESION, 'El alumno está registrado como egresado.'],
               ['El actor abre diploma digital.', 'El sistema verifica el egreso.', 'El actor descarga el diploma.'],
               ['Si no ha egresado, la opción aparece deshabilitada.'],
               ['El diploma queda descargado.'],
               relaciones=[('include', 'Verificar egreso')]),
        ],
    },
    {
        'nombre': 'Docente',
        'actor': 'Docente',
        'sigla': 'DOC',
        'intro': ('El Docente gestiona sus cursos asignados y la evaluación de sus estudiantes. Además crea y califica exámenes '
                  'en línea, conduce entrevistas virtuales a aspirantes, participa en el Colegio de Profesores y genera reportes.'),
        'casos': [
            cu('CU-DOC-01', 'Consultar panel docente',
               'Consulta indicadores de cursos, estudiantes y pendientes de evaluación.',
               [PRE_SESION],
               ['El actor abre su panel.', 'El sistema muestra cursos, estudiantes y pendientes.'],
               ['Sin cursos asignados, se informa.'],
               ['El actor conoce su carga de trabajo.']),
            cu('CU-DOC-02', 'Consultar cursos y estudiantes',
               'Consulta las materias asignadas en su carga académica y sus estudiantes inscritos.',
               [PRE_SESION, 'Tiene carga académica asignada.'],
               ['El actor abre cursos.', 'El sistema muestra materias por periodo.', 'El actor selecciona un curso.', 'El sistema muestra la lista de estudiantes.'],
               ['Si el curso no tiene inscritos, se informa.'],
               ['El actor consulta su grupo.']),
            cu('CU-DOC-03', 'Capturar calificaciones',
               'Registra calificaciones de sus estudiantes en el periodo.',
               [PRE_SESION, 'El periodo de captura está abierto.'],
               ['El actor selecciona curso y estudiante.', 'El actor captura la calificación.', 'El sistema valida el rango permitido.', 'El sistema guarda y registra el movimiento en el histórico.'],
               ['Si el valor está fuera de rango, se rechaza.', 'Si el periodo está cerrado, la captura se bloquea.'],
               ['La calificación queda registrada.'],
               secundarios=['Servicios Escolares'], relaciones=[('include', 'Validar rango de calificación')]),
            cu('CU-DOC-04', 'Gestionar exámenes en línea',
               'Crea exámenes, agrega preguntas, define ventana e intentos y revisa resultados.',
               [PRE_SESION],
               ['El actor crea el examen con fechas, duración e intentos.', 'El actor agrega preguntas y respuestas.', 'El actor publica el examen.', 'El sistema califica intentos y muestra resultados.'],
               ['Con intentos registrados, se restringe la edición de preguntas.'],
               ['El examen queda disponible para los evaluados.'],
               secundarios=['Aspirante', 'Alumno']),
            cu('CU-DOC-05', 'Conducir entrevista virtual',
               'Programa e inicia entrevistas con aspirantes y registra notas privadas.',
               [PRE_SESION, 'Tiene aspirantes asignados para entrevista.'],
               ['El actor programa fecha y hora.', 'El sistema notifica al aspirante.', 'El actor inicia la entrevista y habilita el enlace.', 'El actor registra notas y evaluación al finalizar.'],
               ['Si el aspirante no se conecta, el actor reprograma.'],
               ['La entrevista queda registrada; las notas no son visibles al aspirante.'],
               secundarios=['Aspirante'], relaciones=[('extend', 'Registrar notas privadas')]),
            cu('CU-DOC-06', 'Evaluar aspirante en Colegio',
               'Emite su evaluación como integrante del Colegio de Profesores.',
               [PRE_SESION, 'Es miembro del Colegio.'],
               ['El actor consulta el expediente del aspirante.', 'El actor registra su evaluación.', 'El sistema la integra al dictamen colegiado.'],
               ['Si ya evaluó, puede actualizar su evaluación antes de la resolución.'],
               ['La evaluación queda registrada.'],
               secundarios=['Coordinación Académica']),
            cu('CU-DOC-07', 'Generar reportes docentes',
               'Descarga listas y actas de calificaciones de sus cursos.',
               [PRE_SESION],
               ['El actor abre reportes.', 'El actor selecciona curso y formato.', 'El sistema genera el archivo.'],
               ['Sin datos, se informa.'],
               ['El reporte queda descargado.']),
            cu('CU-DOC-08', 'Actualizar perfil académico',
               'Actualiza datos de contacto, departamento y fotografía.',
               [PRE_SESION],
               ['El actor abre su perfil.', 'El actor modifica sus datos.', 'El sistema valida y guarda.'],
               ['Si un campo es inválido, se marca el error.'],
               ['El perfil queda actualizado.']),
        ],
    },
    {
        'nombre': 'Director de tesis',
        'actor': 'Director de tesis',
        'sigla': 'DIR',
        'intro': ('El Director de tesis da seguimiento a sus tesistas desde la solicitud de dirección hasta la defensa. Su panel '
                  'incluye analítica, tesistas, avances, examen predoctoral, evaluaciones, integración de jurado, expedientes y proyectos.'),
        'casos': [
            cu('CU-DIR-01', 'Consultar resumen y analítica',
               'Consulta indicadores de tesistas, avances y próximos eventos.',
               [PRE_SESION, 'El usuario tiene rol de director.'],
               ['El actor abre su panel.', 'El sistema muestra indicadores y gráficas de avance.'],
               ['Sin tesistas, se informa.'],
               ['El actor conoce el estado de sus tesistas.']),
            cu('CU-DIR-02', 'Responder solicitud de dirección',
               'Acepta o rechaza la solicitud de dirección de tesis de un alumno.',
               [PRE_SESION, 'Existe una solicitud dirigida al actor.'],
               ['El actor abre la solicitud.', 'El sistema muestra datos del alumno y línea de investigación.', 'El actor acepta o rechaza con comentario.', 'El sistema notifica al alumno y a la Coordinación y registra el evento.'],
               ['Si rechaza, la Coordinación puede asignar otro director.'],
               ['La solicitud queda resuelta.'],
               secundarios=['Alumno', 'Coordinación Académica']),
            cu('CU-DIR-03', 'Consultar tesistas y expedientes',
               'Consulta la lista de tesistas y el expediente de cada uno.',
               [PRE_SESION, 'Tiene tesistas asignados.'],
               ['El actor abre tesistas.', 'El sistema lista tesistas con su programa y avance.', 'El actor abre el expediente de un tesista.'],
               ['Sin tesistas, se muestra un estado vacío.'],
               ['El actor consulta la información del tesista.'],
               relaciones=[('include', 'Consultar expediente del tesista')]),
            cu('CU-DIR-04', 'Dar seguimiento a avances',
               'Revisa el proyecto, registra porcentaje de avance y observaciones.',
               [PRE_SESION, 'El tesista registró su proyecto.'],
               ['El actor abre avances o proyectos.', 'El actor revisa el proyecto.', 'El actor registra avance, observaciones o dictamen.', 'El sistema notifica al tesista.'],
               ['Si el proyecto requiere cambios, se devuelve con observaciones.'],
               ['El avance queda registrado.'],
               secundarios=['Alumno']),
            cu('CU-DIR-05', 'Programar examen predoctoral',
               'Programa el examen predoctoral y registra su resultado.',
               [PRE_SESION, 'El tesista cumple los requisitos.'],
               ['El actor programa fecha y sinodales.', 'El sistema notifica al alumno y a la Coordinación.', 'El actor registra el resultado.'],
               ['Si la fecha cambia, el actor reprograma.'],
               ['El predoctoral queda registrado.'],
               secundarios=['Alumno', 'Coordinación Académica']),
            cu('CU-DIR-06', 'Integrar jurado de defensa',
               'Selecciona a los integrantes del jurado de tesis.',
               [PRE_SESION, 'El proyecto está aprobado.'],
               ['El actor abre jurado.', 'El actor selecciona docentes e investigadores y su función.', 'El sistema valida que no haya duplicados.', 'El sistema registra el jurado y notifica a los integrantes.'],
               ['Si un integrante ya está en el jurado, el sistema lo rechaza.'],
               ['El jurado queda integrado.'],
               secundarios=['Docente'], relaciones=[('include', 'Validar integrantes')]),
            cu('CU-DIR-07', 'Registrar revisión antiplagio',
               'Carga la tesis para revisión antiplagio y registra el porcentaje de similitud.',
               [PRE_SESION, 'Existe documento final de tesis.'],
               ['El actor carga el PDF.', 'El sistema valida el archivo.', 'El actor registra el resultado de similitud.'],
               ['Si el archivo no es válido, se rechaza.'],
               ['La revisión queda registrada.']),
            cu('CU-DIR-08', 'Programar defensa y registrar resultado',
               'Programa la defensa de tesis y registra su resultado.',
               [PRE_SESION, 'Jurado integrado y antiplagio aprobado.'],
               ['El actor programa la defensa.', 'El sistema notifica a alumno y jurado.', 'El actor registra el resultado.', 'El sistema habilita el proceso de egreso.'],
               ['Si se pospone, el actor reprograma.'],
               ['La defensa queda registrada.'],
               secundarios=['Alumno', 'Docente'], relaciones=[('extend', 'Habilitar egreso')]),
        ],
    },
    {
        'nombre': 'Administrador',
        'actor': 'Administrador',
        'sigla': 'ADM',
        'intro': ('El Administrador mantiene la plataforma. Gestiona usuarios y roles, alumnos y docentes, catálogos y periodos, '
                  'revisa solicitudes, genera reportes, consulta la auditoría y configura la seguridad, el mantenimiento y los parámetros del sistema.'),
        'casos': [
            cu('CU-ADM-01', 'Consultar panorama del sistema',
               'Consulta indicadores globales de usuarios, actividad y estado del sistema.',
               [PRE_SESION],
               ['El actor abre su panel.', 'El sistema muestra indicadores globales.'],
               ['Sin datos, se informa.'],
               ['El actor conoce el estado del sistema.']),
            cu('CU-ADM-02', 'Gestionar usuarios y roles',
               'Crea, edita, activa o desactiva usuarios y asigna su rol.',
               [PRE_SESION],
               ['El actor abre usuarios.', 'El sistema lista usuarios con filtros.', 'El actor crea o edita un usuario y asigna el rol.', 'El sistema valida unicidad y guarda.', 'El sistema registra la acción en auditoría.'],
               ['Si el usuario existe, se informa.', 'El actor puede desbloquear una cuenta bloqueada por intentos fallidos.'],
               ['El usuario queda actualizado.'],
               relaciones=[('include', 'Registrar en auditoría'), ('extend', 'Desbloquear cuenta')]),
            cu('CU-ADM-03', 'Gestionar alumnos y docentes',
               'Consulta y corrige la información de alumnos y docentes.',
               [PRE_SESION],
               ['El actor abre alumnos o docentes.', 'El actor edita la información.', 'El sistema valida y guarda.'],
               ['Datos inválidos se marcan en el campo.'],
               ['El registro queda actualizado.']),
            cu('CU-ADM-04', 'Gestionar catálogos',
               'Administra catálogos de programas, materias, departamentos y líneas de investigación.',
               [PRE_SESION],
               ['El actor abre catálogos.', 'El actor crea, edita o desactiva elementos.', 'El sistema valida y guarda.'],
               ['Elementos en uso no pueden eliminarse, solo desactivarse.'],
               ['El catálogo queda actualizado.']),
            cu('CU-ADM-05', 'Gestionar periodos',
               'Configura periodos y ventanas de inscripción.',
               [PRE_SESION],
               ['El actor abre periodos.', 'El actor define fechas.', 'El sistema valida y guarda.'],
               ['Fechas traslapadas se rechazan.'],
               ['El periodo queda configurado.']),
            cu('CU-ADM-06', 'Revisar solicitudes',
               'Consulta solicitudes del sistema y su estado.',
               [PRE_SESION],
               ['El actor abre solicitudes.', 'El sistema lista solicitudes.', 'El actor revisa y actúa.'],
               ['Sin solicitudes, estado vacío.'],
               ['Las solicitudes quedan revisadas.']),
            cu('CU-ADM-07', 'Generar reportes',
               'Descarga reportes globales del sistema.',
               [PRE_SESION],
               ['El actor elige reporte y formato.', 'El sistema genera el archivo.'],
               ['Sin datos, se informa.'],
               ['El reporte queda descargado.']),
            cu('CU-ADM-08', 'Consultar auditoría',
               'Consulta la bitácora de accesos y acciones sensibles.',
               [PRE_SESION],
               ['El actor abre auditoría.', 'El sistema lista eventos con usuario, acción, IP y fecha.', 'El actor filtra los eventos.'],
               ['Sin eventos en el rango, estado vacío.'],
               ['El actor obtiene la trazabilidad.']),
            cu('CU-ADM-09', 'Configurar seguridad y sistema',
               'Ajusta políticas de seguridad, mantenimiento y parámetros generales.',
               [PRE_SESION],
               ['El actor abre seguridad, mantenimiento o configuración.', 'El actor modifica parámetros.', 'El sistema valida y aplica los cambios.', 'El sistema registra la acción en auditoría.'],
               ['Valores fuera de rango se rechazan.'],
               ['La configuración queda aplicada.'],
               relaciones=[('include', 'Registrar en auditoría')]),
        ],
    },
]

# ---------------------------------------------------------------------------
# Diagramas UML
# ---------------------------------------------------------------------------

def actor(d, x, y, nombre, sistema=False):
    if sistema:
        d.add(Rect(x - 30, y - 14, 60, 28, fillColor=GRIS_CLARO, strokeColor=GRIS, strokeWidth=0.8))
        d.add(String(x, y + 4, '«sistema»', fontName='Arial-Italic', fontSize=6, textAnchor='middle', fillColor=GRIS))
        texto_centrado(d, x, y - 5, envolver(nombre, 'Arial-Bold', 6.3, 56)[:2], 'Arial-Bold', 6.3)
        return
    d.add(Circle(x, y + 16, 5.5, fillColor=colors.white, strokeColor=VERDE_OSCURO, strokeWidth=1.1))
    d.add(Line(x, y + 10.5, x, y - 4, strokeColor=VERDE_OSCURO, strokeWidth=1.1))
    d.add(Line(x - 9, y + 5, x + 9, y + 5, strokeColor=VERDE_OSCURO, strokeWidth=1.1))
    d.add(Line(x, y - 4, x - 7, y - 15, strokeColor=VERDE_OSCURO, strokeWidth=1.1))
    d.add(Line(x, y - 4, x + 7, y - 15, strokeColor=VERDE_OSCURO, strokeWidth=1.1))
    for i, linea in enumerate(envolver(nombre, 'Arial-Bold', 6.8, 70)[:2]):
        d.add(String(x, y - 24 - i * 8, linea, fontName='Arial-Bold', fontSize=6.8, textAnchor='middle'))


def caso(d, x, y, ancho, alto, texto, relleno=VERDE_CLARO):
    d.add(Ellipse(x, y, ancho / 2, alto / 2, fillColor=relleno, strokeColor=VERDE_OSCURO, strokeWidth=0.9))
    texto_centrado(d, x, y, envolver(texto, 'Arial', 7.2, ancho * 0.78)[:3], tam=7.2)


def flecha_punteada(d, x1, y1, x2, y2, etiqueta):
    d.add(Line(x1, y1, x2, y2, strokeColor=GRIS, strokeWidth=0.8, strokeDashArray=[3, 2]))
    ang = math.atan2(y2 - y1, x2 - x1)
    for delta in (0.45, -0.45):
        d.add(Line(x2, y2, x2 - 6 * math.cos(ang + delta), y2 - 6 * math.sin(ang + delta), strokeColor=GRIS, strokeWidth=0.8))
    t = 0.5 if etiqueta == 'extend' else 0.3
    mx, my = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
    d.add(String(mx, my + 3, f'«{etiqueta}»', fontName='Arial-Italic', fontSize=6.3, textAnchor='middle', fillColor=GRIS))


SISTEMAS = {'Motor LIDA (Camunda)', 'Servidor de correo'}


def diagrama_casos(rol, casos, parte=None, etiqueta=None):
    ancho = ANCHO_UTIL
    secundarios = []
    for c in casos:
        for s in c['secundarios']:
            if s not in secundarios:
                secundarios.append(s)
    relaciones = [(c['id'], tipo, destino) for c in casos for tipo, destino in c['relaciones']]
    con_b = bool(relaciones)
    alto = max(42 + len(casos) * 44 + 14, len(secundarios) * 66 + 40)
    paso = (alto - 56) / len(casos)
    x0 = 86
    x1 = ancho - (88 if secundarios else 14)
    if con_b:
        ax, aw = x0 + 82, 152
        bx, bw = x1 - 62, 112
    else:
        ax, aw = (x0 + x1) / 2, 210
    ah = 32
    d = Drawing(ancho, alto)
    titulo = f'SINAC NEXT · {etiqueta or rol["nombre"]}' + (f' ({parte})' if parte else '')
    d.add(Rect(x0, 6, x1 - x0, alto - 12, fillColor=None, strokeColor=VERDE_OSCURO, strokeWidth=1.2))
    d.add(String(x0 + 8, alto - 20, titulo, fontName='Arial-Bold', fontSize=8.5, fillColor=VERDE_OSCURO))

    pos_a = {}
    for i, c in enumerate(casos):
        pos_a[c['id']] = (ax, alto - 46 - i * paso)
    pos_b, ocupados = {}, []
    for origen, tipo, destino in relaciones:
        if destino in pos_b:
            continue
        propios = [d for o, _, d in relaciones if o == origen]
        origenes = [pos_a[o][1] for o, _, d in relaciones if d == destino]
        if len(origenes) > 1:
            y = sum(origenes) / len(origenes)
        else:
            y = pos_a[origen][1] + ((len(propios) - 1) / 2 - propios.index(destino)) * 44
        while any(abs(y - o) < 38 for o in ocupados):
            y -= 38
        y = max(min(y, alto - 46), 28)
        ocupados.append(y)
        pos_b[destino] = (bx, y)

    ay_centro = alto / 2
    actor_x = 44
    for c in casos:
        cx, cy = pos_a[c['id']]
        ex, ey = borde_elipse(cx, cy, aw / 2, ah / 2, actor_x, ay_centro + 4)
        d.add(Line(actor_x + 10, ay_centro + 4, ex, ey, strokeColor=colors.HexColor('#5B6B75'), strokeWidth=0.7))

    sec_x = ancho - 40
    deseado = {}
    for s in secundarios:
        ys = [pos_a[c['id']][1] for c in casos if s in c['secundarios']]
        deseado[s] = sum(ys) / len(ys)
    sec_pos, previo = {}, None
    for s in sorted(secundarios, key=lambda n: -deseado[n]):
        y = min(deseado[s], alto - 30)
        if previo is not None:
            y = min(y, previo - 66)
        sec_pos[s] = previo = y
    if sec_pos and min(sec_pos.values()) < 40:
        desfase = 40 - min(sec_pos.values())
        sec_pos = {s: y + desfase for s, y in sec_pos.items()}
    for c in casos:
        for s in c['secundarios']:
            cx, cy = pos_a[c['id']]
            ex, ey = borde_elipse(cx, cy, aw / 2, ah / 2, sec_x, sec_pos[s])
            d.add(Line(sec_x - 12, sec_pos[s] + 4, ex, ey, strokeColor=colors.HexColor('#9AA7B0'), strokeWidth=0.6))

    for origen, tipo, destino in relaciones:
        ox, oy = pos_a[origen]
        dx, dy = pos_b[destino]
        p_a = borde_elipse(ox, oy, aw / 2, ah / 2, dx, dy)
        p_b = borde_elipse(dx, dy, bw / 2, ah / 2, ox, oy)
        if tipo == 'include':
            flecha_punteada(d, p_a[0], p_a[1], p_b[0], p_b[1], 'include')
        else:
            flecha_punteada(d, p_b[0], p_b[1], p_a[0], p_a[1], 'extend')

    for c in casos:
        cx, cy = pos_a[c['id']]
        caso(d, cx, cy, aw, ah, f'{c["id"]} {c["nombre"]}')
    for destino, (dx, dy) in pos_b.items():
        caso(d, dx, dy, bw, ah, destino, relleno=colors.white)

    actor(d, actor_x, ay_centro, rol['actor'])
    for s, y in sec_pos.items():
        actor(d, sec_x, y, s, sistema=s in SISTEMAS)
    return d


def lista_numerada(pasos):
    return '<br/>'.join(f'{i}. {p}' for i, p in enumerate(pasos, 1))


def lista_vinetas(items):
    return '<br/>'.join(f'• {p}' for p in items)


def ficha(rol, c):
    secundarios = ', '.join(c['secundarios']) or 'Ninguno'
    relaciones = '<br/>'.join(f'«{t}» {d}' for t, d in c['relaciones']) or 'Ninguna'
    filas = [
        [Paragraph(f'{c["id"]} · {c["nombre"]}', celda_cab), ''],
        [Paragraph('Actor principal', celda_neg), Paragraph(rol['actor'], celda)],
        [Paragraph('Actores secundarios', celda_neg), Paragraph(secundarios, celda)],
        [Paragraph('Descripción', celda_neg), Paragraph(c['descripcion'], celda)],
        [Paragraph('Precondiciones', celda_neg), Paragraph(lista_vinetas(c['pre']), celda)],
        [Paragraph('Flujo principal', celda_neg), Paragraph(lista_numerada(c['flujo']), celda)],
        [Paragraph('Flujos alternos', celda_neg), Paragraph(lista_vinetas(c['alternos']), celda)],
        [Paragraph('Postcondiciones', celda_neg), Paragraph(lista_vinetas(c['post']), celda)],
        [Paragraph('Relaciones', celda_neg), Paragraph(relaciones, celda)],
    ]
    t = Table(filas, colWidths=[3.6 * cm, ANCHO_UTIL - 3.6 * cm])
    t.setStyle(TableStyle([
        ('SPAN', (0, 0), (1, 0)),
        ('BACKGROUND', (0, 0), (1, 0), VERDE),
        ('BACKGROUND', (0, 1), (0, -1), VERDE_CLARO),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return t


def introduccion():
    h = []
    h.append(titulo('1. Introducción', h1, 0))
    h.append(titulo('1.1 Propósito', h2, 1))
    h.append(Paragraph(
        'Este documento describe los casos de uso del sistema <b>SINAC NEXT</b>, el sistema de información académica '
        'desarrollado para el Centro de Investigación y de Estudios Avanzados (Cinvestav). Su propósito es especificar, '
        'mediante la notación de casos de uso de UML, las funciones que el sistema ofrece a cada uno de sus actores y la '
        'forma en que estos interactúan con él, sirviendo como referencia para el diseño, la implementación, las pruebas y '
        'la validación con los usuarios.', cuerpo))
    h.append(titulo('1.2 Alcance', h2, 1))
    h.append(Paragraph(
        'El documento comprende un caso de uso general y los casos de uso específicos de cada uno de los siete actores '
        'humanos que operan la plataforma:', cuerpo))
    for r in ('Coordinación Académica', 'Servicios Escolares', 'Aspirante', 'Alumno', 'Docente', 'Director de tesis', 'Administrador'):
        h.append(Paragraph(r, vineta, bulletText='•'))
    h.append(Paragraph(
        'Para cada actor se presenta primero su caso de uso general, con su diagrama y la relación de casos específicos que '
        'agrupa cada función, y después sus casos de uso específicos con su diagrama, una tabla resumen y la especificación '
        'detallada de cada caso (actores, precondiciones, flujo principal, flujos alternos, postcondiciones y relaciones).', cuerpo))
    h.append(titulo('1.3 Descripción general del sistema', h2, 1))
    h.append(Paragraph(
        'SINAC NEXT integra en una sola plataforma web el ciclo académico completo de los programas de posgrado: admisión de '
        'aspirantes, inscripciones, cargas académicas, evaluación, seguimiento de tesis, egreso y emisión de documentos. Los '
        'procesos institucionales se modelan con el <b>Lenguaje Iconográfico (LIDA)</b> y se ejecutan en el motor de procesos '
        'BPMN Camunda, lo que permite visualizar y controlar cada etapa del flujo.', cuerpo))
    h.append(Paragraph(
        'La arquitectura se compone de una aplicación web de una sola página desarrollada en React, una API REST construida con '
        'Django y Django REST Framework con autenticación mediante tokens JWT, una base de datos PostgreSQL, el motor Camunda '
        'para los procesos LIDA y un proxy inverso nginx, todo desplegado con contenedores Docker. Cada usuario accede a un '
        'panel específico según su rol, con control de permisos en el servidor.', cuerpo))
    h.append(titulo('1.4 Actores del sistema', h2, 1))
    h.append(tabla([['Actor', 'Descripción']] + [[a, d] for a, d in ACTORES], [4.2 * cm, ANCHO_UTIL - 4.2 * cm]))
    h.append(titulo('1.5 Notación utilizada', h2, 1))
    h.append(tabla([
        ['Elemento', 'Representación y significado'],
        ['Actor', 'Figura humana. Representa un rol que interactúa con el sistema. Los actores de sistema se muestran como rectángulos con el estereotipo «sistema».'],
        ['Caso de uso', 'Elipse verde con identificador y nombre. Representa una función que aporta un resultado observable al actor.'],
        ['Caso incluido o extendido', 'Elipse blanca. Comportamiento reutilizado u opcional asociado a un caso de uso principal.'],
        ['Límite del sistema', 'Rectángulo que agrupa los casos de uso del sistema SINAC NEXT.'],
        ['Asociación', 'Línea continua entre actor y caso de uso; indica participación del actor.'],
        ['«include»', 'Flecha punteada del caso base al caso incluido; el comportamiento incluido siempre se ejecuta.'],
        ['«extend»', 'Flecha punteada del caso extendido al caso base; el comportamiento se ejecuta solo bajo cierta condición.'],
    ], [4.2 * cm, ANCHO_UTIL - 4.2 * cm]))
    h.append(Spacer(1, 8))
    h.append(titulo('1.6 Convención de identificadores', h2, 1))
    h.append(Paragraph(
        'Los casos de uso generales se identifican con el prefijo <b>CUG</b> y los específicos con <b>CU</b>, seguidos de la '
        'sigla del actor y un número consecutivo (por ejemplo, CUG-ASP-01 y CU-ASP-01). Las siglas son: COO (Coordinación '
        'Académica), SE (Servicios Escolares), ASP (Aspirante), ALU (Alumno), DOC (Docente), DIR (Director de tesis) y '
        'ADM (Administrador).', cuerpo))
    h.append(PageBreak())
    return h


def casos_generales(rol):
    por_id = {c['id']: c for c in rol['casos']}
    generales = []
    for i, (nombre, descripcion, ids) in enumerate(GENERALES[rol['sigla']], 1):
        secundarios = []
        for id_ in ids:
            for s in por_id[id_]['secundarios']:
                if s not in secundarios:
                    secundarios.append(s)
        relaciones = [] if 'CU-ASP-01' in ids else [('include', AUTENTICARSE)]
        generales.append({'id': f'CUG-{rol["sigla"]}-{i:02d}', 'nombre': nombre, 'descripcion': descripcion,
                          'especificos': ids, 'secundarios': secundarios, 'relaciones': relaciones})
    return generales


def desarrollo():
    h = [titulo('2. Desarrollo', h1, 0)]
    h.append(Paragraph(
        'A continuación se presenta, para cada actor, su caso de uso general y sus casos de uso específicos. El caso de uso '
        'general muestra las grandes funciones que el actor realiza en SINAC NEXT; cada una de ellas agrupa varios casos de uso '
        'específicos, que se detallan después mediante su diagrama, una tabla resumen y la especificación de cada caso.', cuerpo))
    figura = 1
    for n, rol in enumerate(ROLES, 1):
        if n > 1:
            h.append(PageBreak())
        h.append(titulo(f'2.{n} {rol["nombre"]}', h2, 1))
        h.append(Paragraph(rol['intro'], cuerpo))

        generales = casos_generales(rol)
        por_id = {c['id']: c for c in rol['casos']}
        h.append(titulo(f'2.{n}.1 Caso de uso general: {rol["nombre"]}', h3, 2))
        leyenda = f'Figura {figura}. Diagrama de caso de uso general de {rol["nombre"]}.'
        h.append(KeepTogether([diagrama_casos(rol, generales, etiqueta=f'{rol["nombre"]} (general)'), Paragraph(leyenda, pie_fig)]))
        figura += 1
        h.append(tabla([['ID', 'Caso de uso general', 'Descripción', 'Casos específicos']] + [
            [g['id'], g['nombre'], g['descripcion'], '<br/>'.join(f'{i} {por_id[i]["nombre"]}' for i in g['especificos'])]
            for g in generales
        ], [2.5 * cm, 3.4 * cm, 4.3 * cm, ANCHO_UTIL - 10.2 * cm]))

        h.append(PageBreak())
        h.append(titulo(f'2.{n}.2 Casos de uso específicos: {rol["nombre"]}', h3, 2))
        casos = rol['casos']
        bloques = [casos] if len(casos) <= 9 else [casos[:len(casos) // 2 + len(casos) % 2], casos[len(casos) // 2 + len(casos) % 2:]]
        for i, bloque in enumerate(bloques):
            parte = f'parte {i + 1} de {len(bloques)}' if len(bloques) > 1 else None
            leyenda = f'Figura {figura}. Diagrama de casos de uso de {rol["nombre"]}' + (f' ({parte})' if parte else '') + '.'
            h.append(KeepTogether([diagrama_casos(rol, bloque, parte), Paragraph(leyenda, pie_fig)]))
            figura += 1
        h.append(Paragraph(f'<b>Resumen de casos de uso de {rol["nombre"]}</b>', h3))
        h.append(tabla([['ID', 'Caso de uso', 'Descripción']] + [[c['id'], c['nombre'], c['descripcion']] for c in casos],
                       [2.1 * cm, 5.0 * cm, ANCHO_UTIL - 7.1 * cm]))
        h.append(Paragraph(f'<b>Especificación de casos de uso de {rol["nombre"]}</b>', h3))
        for c in casos:
            encabezado = titulo(f'{c["id"]} {c["nombre"]}', ParagraphStyle('oculto', parent=celda, fontSize=0.1, leading=0.1, textColor=colors.white), 3)
            h.append(KeepTogether([encabezado, ficha(rol, c), Spacer(1, 10)]))
    return h


def conclusiones():
    total = sum(len(r['casos']) for r in ROLES)
    generales = sum(len(v) for v in GENERALES.values())
    return [
        PageBreak(),
        titulo('3. Conclusiones', h1, 0),
        Paragraph(
            f'Se documentó un caso de uso general por cada uno de los siete actores de SINAC NEXT, con {generales} funciones '
            f'generales que agrupan {total} casos de uso específicos. El modelo permite identificar con claridad las responsabilidades de cada actor, las '
            'dependencias entre áreas (por ejemplo, la relación entre la Coordinación Académica, el Director de tesis y el Alumno '
            'en el proceso de titulación) y los puntos donde intervienen los actores de sistema, como el motor LIDA y el servidor de correo.', cuerpo),
        Paragraph(
            'Estos casos de uso constituyen la base para la trazabilidad de requerimientos, el diseño de pruebas funcionales y la '
            'validación del sistema con los usuarios del Cinvestav, y deberán actualizarse conforme evolucionen los procesos institucionales.', cuerpo),
    ]


def construir():
    doc = Documento(SALIDA, TITULO)
    indice = TableOfContents()
    indice.levelStyles = toc_estilos
    indice.dotsMinLevel = 0
    historia = portada(TITULO)
    historia.append(Paragraph('Índice', h1))
    historia.append(indice)
    historia.append(PageBreak())
    historia += introduccion()
    historia += desarrollo()
    historia += conclusiones()
    doc.multiBuild(historia, canvasmaker=canvas_numerado(TITULO))
    print(SALIDA)


if __name__ == '__main__':
    construir()
