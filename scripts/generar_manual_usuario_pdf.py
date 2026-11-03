"""Genera el manual de usuario de SINAC NEXT con capturas reales del sistema.

Las capturas se obtienen con scripts/capturar_manual.py.
"""
import io
import json
import os
import re
import sys

from PIL import Image as PILImage
from reportlab.lib.units import cm
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents

from plantilla_cinvestav import (
    ANCHO_UTIL, BORDE, RAIZ, VERDE, VERDE_CLARO,
    Documento, canvas_numerado, celda, cuerpo, h1, h2, h3, pie_fig, portada, tabla, titulo,
    toc_estilos, vineta,
)

TITULO = 'Manual de Usuario'
SALIDA = os.path.join(RAIZ, 'docs', 'SINAC_NEXT_Manual_de_Usuario.pdf')
CAPTURAS = os.path.join(RAIZ, 'docs', 'assets', 'manual')

nota_estilo = celda.clone('nota', fontSize=9.5, leading=13)


class Figuras:
    n = 0


def limpiar(etiqueta):
    texto = re.sub(r'^[^\wÁÉÍÓÚÑáéíóúñ]+', '', etiqueta).strip()
    return re.sub(r'[\s\d+−\-]+$', '', texto).strip()


def imagen(ruta, ancho=ANCHO_UTIL - 0.4 * cm):
    with PILImage.open(os.path.join(RAIZ, ruta)) as im:
        im = im.convert('RGB')
        im.thumbnail((1500, 1500))
        alto = ancho * im.height / im.width
        buffer = io.BytesIO()
        im.save(buffer, 'JPEG', quality=82, optimize=True)
    buffer.seek(0)
    return Image(buffer, ancho, alto)


def figura(ruta, pie, escala=0.7):
    Figuras.n += 1
    ancho = ANCHO_UTIL * escala
    marco = Table([[imagen(ruta, ancho - 0.4 * cm)]], colWidths=[ancho - 0.2 * cm])
    marco.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.6, BORDE),
        ('LEFTPADDING', (0, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    return [marco, Paragraph(f'Figura {Figuras.n}. {pie}', pie_fig)]


def nota(texto, etiqueta='Nota'):
    t = Table([[Paragraph(f'<b>{etiqueta}:</b> {texto}', nota_estilo)]], colWidths=[ANCHO_UTIL])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), VERDE_CLARO),
        ('LINEBEFORE', (0, 0), (0, -1), 3, VERDE),
        ('LEFTPADDING', (0, 0), (-1, -1), 9), ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return [t, Spacer(1, 8)]


def pasos(lista):
    return [Paragraph(p, vineta, bulletText=f'{i}.') for i, p in enumerate(lista, 1)]


def vinetas(lista):
    return [Paragraph(p, vineta, bulletText='•') for p in lista]


# --------------------------------------------------------------------------------------------
# Contenido por rol: nombre de la sección del menú -> (descripción, pasos, nota)
# --------------------------------------------------------------------------------------------

def sec(desc, pasos_=None, nota_=None):
    return {'desc': desc, 'pasos': pasos_ or [], 'nota': nota_}


ROLES = [
    {
        'clave': 'coordinacion', 'nombre': 'Coordinación Académica', 'usuario': 'coordinacion',
        'intro': 'El panel de Coordinación Académica concentra la gestión de la admisión y de la operación académica: '
                 'revisión de expedientes de aspirantes, materias y cargas académicas, inscripciones, solicitudes, tesis, '
                 'exámenes, Colegio de Profesores, histórico y reportes. El menú lateral agrupa las secciones en Panorama, '
                 'Gestión académica, Investigación, Comunidad y Análisis.',
        'secciones': {
            'Resumen': sec('Muestra el tablero analítico de la coordinación: solicitudes por estado (pendiente, en revisión, '
                           'aceptado, rechazado), la composición del sistema (aspirantes, alumnos y personal académico) y '
                           'botones de exportación rápida de expedientes y listados en XLSX o PDF.'),
            'Bandeja de solicitudes': sec(
                'Lista las solicitudes de admisión con búsqueda, filtros por estado y programa, y paginación. El contador del '
                'menú indica cuántas solicitudes requieren atención. En la parte superior se encuentra el formulario de '
                'notificaciones masivas para enviar avisos a un grupo de aspirantes.',
                ['Escriba en el buscador el nombre, CURP o folio del aspirante, o aplique un filtro de estado.',
                 'Seleccione la solicitud para abrir su <b>Detalle de expediente</b>.',
                 'Para un aviso masivo, elija el grupo de destinatarios, redacte el mensaje y pulse <b>Enviar notificación</b>; '
                 'cada destinatario lo recibe en su panel y por correo.']),
            'Detalle de expediente': sec(
                'Presenta el expediente completo del aspirante seleccionado: datos personales, programa, adscripción, '
                'escolaridad, documentos cargados, fechas del curso propedéutico, exámenes, entrevistas y seguimiento. Desde '
                'aquí se revisan los documentos y se resuelve la solicitud.',
                ['Abra cada documento; el enlace es seguro y caduca después de un tiempo.',
                 'Marque el documento como revisado o registre una observación para que el aspirante lo reemplace.',
                 'Registre, si aplica, las fechas y la aprobación del curso propedéutico y pulse <b>Guardar cambios</b>.',
                 'Resuelva la solicitud con <b>Marcar en revisión</b>, <b>Aceptar</b> o <b>Rechazar</b>. El sistema notifica '
                 'al aspirante por correo y en su panel.',
                 'Con el aspirante aceptado, pulse <b>Convertir a alumno</b> para darlo de alta en el panel de Alumno.'],
                'No es posible aceptar a un aspirante mientras tenga documentos sin revisar. Al aceptarlo se crea su '
                'expediente digital con folio. Desde esta vista también se descargan el historial de calificaciones y el '
                'formato de adscripción, y se puede <b>Dar de baja</b> a un alumno.'),
            'Materias y cursos': sec(
                'Consulta el catálogo de materias publicado por Servicios Escolares, con clave, nombre, créditos, profesor y '
                'horario, y filtros por créditos y profesor. La carga y actualización del catálogo corresponden a Servicios '
                'Escolares.'),
            'Preparar carga académica': sec(
                'Prepara los borradores de carga académica (materias y docentes por periodo) y los envía a Servicios Escolares '
                'para su revisión y publicación. El flujo de aprobación es orquestado por el motor LIDA y la tabla muestra el '
                'estado de cada carga (borrador, en revisión, aprobada, publicada).',
                ['Escriba el periodo escolar (por ejemplo, 2026-1).',
                 'Pulse <b>Agregar materia</b> por cada materia de la carga y asígnele docente.',
                 'Pulse <b>Guardar borrador</b>.',
                 'Cuando la carga esté completa, envíela a revisión desde las acciones de la tabla y dé seguimiento a su estado.']),
            'Solicitudes académicas': sec(
                'Muestra las solicitudes asignadas al área (por ejemplo, ajuste de materias), con filtros por estado y tipo. '
                'Cada resolución requiere una respuesta para que el alumno conozca el resultado.',
                ['Localice la solicitud con el buscador o los filtros.',
                 'Lea la solicitud del alumno y escriba la respuesta.',
                 'Acepte o rechace la solicitud; el alumno recibe la notificación.']),
            'Inscripciones regulares': sec(
                'Permite consultar y gestionar las materias inscritas por cada alumno en el periodo vigente y descargar su '
                'boleta de inscripción.'),
            'Inscripción extemporánea': sec(
                'Registra solicitudes de inscripción fuera del periodo ordinario para un alumno, con el motivo correspondiente. '
                'Servicios Escolares revisa la solicitud y, al aprobarla, se inscriben las materias.'),
            'Exámenes en línea': sec(
                'Crea exámenes de admisión, selección o diagnóstico, los asigna a aspirantes y revisa sus resultados. Los '
                'indicadores superiores muestran cuántos exámenes están programados, en curso, completados, aprobados, '
                'reprobados o cancelados.',
                ['Pulse <b>Nuevo examen</b>.',
                 'Defina tipo, título, fecha programada, duración, preguntas, aspirante y docente evaluador.',
                 'Guarde. El examen aparece como programado en la tabla.',
                 'Use <b>Ver</b> para consultar el detalle, el estado y la calificación.']),
            'Proyectos de tesis': sec(
                'Supervisa los proyectos de tesis registrados, su director, porcentaje de avance, jurado, revisión antiplagio '
                'y defensa.'),
            'Asignación de directores': sec(
                'Atiende las solicitudes de dirección de tesis. El alumno sugiere un director y la Coordinación confirma la '
                'asignación formal. La tabla muestra alumno, línea de investigación, director sugerido, director asignado y '
                'estado (por ejemplo, aprobada o pendiente del director).',
                ['Filtre por estado, programa o línea de investigación.',
                 'En la columna <b>Director asignado</b>, elija al director sugerido o a otro docente disponible.',
                 'Confirme la asignación; el alumno y el director reciben la notificación.']),
            'Examen predoctoral': sec('Consulta la programación, los sinodales y el resultado de los exámenes predoctorales.'),
            'Colegio de Profesores': sec(
                'Integra las evaluaciones de los docentes del Colegio y permite registrar el dictamen colegiado de cada '
                'aspirante a partir de sus exámenes y entrevistas.'),
            'Alumnos': sec('Directorio de alumnos con búsqueda y filtros por programa, semestre y estatus; permite abrir el '
                           'expediente, consultar calificaciones y descargar la constancia de adscripción.'),
            'Aspirantes': sec('Directorio de aspirantes con nombre, usuario, correo, programa y estado de admisión (pendiente, '
                              'iniciado, en revisión, aceptado o rechazado). Permite buscar, filtrar por programa y estado, '
                              'y descargar el listado en XLSX o PDF.'),
            'Egresados': sec('Directorio de egresados con filtros por programa y generación.'),
            'Histórico': sec(
                'Bitácora histórica del sistema: resumen, actividad mensual y eventos por categoría (admisión, inscripción, '
                'calificaciones, tesis, egreso, etc.). Permite abrir la línea de tiempo de una persona y exportar el resultado.',
                ['Filtre por categoría, programa, responsable o rango de fechas.',
                 'Pulse sobre una persona para ver su línea de tiempo completa.',
                 'Descargue el resultado en XLSX o PDF si lo requiere.']),
            'Docentes y Directores': sec('Directorio del personal académico con su departamento, carga académica y tesistas.'),
            'Reportes': sec('Genera reportes institucionales (aspirantes, alumnos, inscripciones, tesis) en XLSX o PDF.'),
            'Mi perfil': sec('Muestra y permite actualizar los datos de contacto de la cuenta de coordinación.'),
        },
    },
    {
        'clave': 'servicios', 'nombre': 'Servicios Escolares', 'usuario': 'servicios',
        'intro': 'El panel de Servicios Escolares mantiene el control escolar institucional: expedientes de alumnos, '
                 'directorio docente, planes de estudio, periodos, validación de inscripciones y calificaciones, historiales, '
                 'constancias, egreso y reportes. Las secciones se agrupan en Panorama, Control académico y Documentación y cierre.',
        'secciones': {
            'Resumen': sec('Indicadores de control escolar: alumnos por estatus, inscripciones pendientes de validar y '
                           'trámites en curso.'),
            'Alumnos': sec(
                'Lista oficial de alumnos con matrícula, programa, departamento y estatus, con búsqueda y filtros por programa, '
                'departamento y estatus. Permite registrar alumnos, editar sus datos y cambiar su estatus (activo, baja, '
                'reingreso, egresado).',
                ['Pulse <b>+ Registrado</b> para dar de alta un alumno, o <b>Consultar expediente</b> en uno existente.',
                 'Capture o corrija CURP, correo, matrícula, programa y semestre.',
                 'Si cambia el estatus a baja, indique el motivo.',
                 'Guarde. Los errores (por ejemplo, CURP duplicada) se marcan junto al campo correspondiente.'],
                'Cada cambio queda registrado en el histórico del alumno.'),
            'Directorio de docentes': sec('Consulta de docentes con su departamento y la carga académica asignada.'),
            'Planes de estudio': sec('Administra los planes de estudio y las materias que los integran por semestre.'),
            'Periodos de inscripción': sec(
                'Define cuándo pueden realizarse las inscripciones y reinscripciones de los alumnos.',
                ['Pulse <b>Nuevo periodo</b>, o elija uno en <b>Selecciona un periodo para editar</b>.',
                 'Capture el nombre del periodo y las fechas y horas de <b>Apertura</b> y <b>Cierre</b>.',
                 'Indique si el periodo está <b>Habilitado</b>.',
                 'Pulse <b>Actualizar periodo</b> (o guarde el nuevo). El sistema rechaza fechas incoherentes.']),
            'Revisión de cargas académicas': sec('Consulta las cargas académicas enviadas por Coordinación y su estado en el '
                                                 'flujo de aprobación.'),
            'Solicitudes extemporáneas': sec(
                'Revisa las solicitudes de inscripción extemporánea enviadas por Coordinación. Cada tarjeta muestra alumno, '
                'folio, periodo, programa y motivo. Las materias se inscriben solo después de aprobar la solicitud.',
                ['Filtre por estatus, periodo o programa.', 'Lea el motivo y escriba el <b>Comentario de revisión</b>.',
                 'Pulse <b>Aprobar solicitud</b> o <b>Rechazar solicitud</b>.']),
            'Solicitudes académicas': sec('Atiende las solicitudes de alumnos que corresponden a control escolar o las deriva '
                                          'a Coordinación.'),
            'Inscripciones': sec(
                'Lista de alumnos registrados para validar sus inscripciones, reinscripciones y requisitos administrativos.',
                ['Localice al alumno y pulse <b>Consultar expediente</b>.', 'Revise las materias inscritas en el periodo.',
                 'Valide u observe la inscripción; el alumno ve el resultado en su panel.']),
            'Historial académico': sec('Genera el historial académico oficial del alumno en PDF con materias, calificaciones '
                                       'y promedio.'),
            'Calificaciones': sec('Supervisa las calificaciones capturadas por los docentes, por periodo, materia y alumno.'),
            'Exámenes en línea': sec('Consulta de los exámenes en línea y sus resultados.'),
            'Constancias y documentos': sec('Emite constancias de estudios y documentos oficiales del alumno; el tipo de '
                                            'constancia disponible depende de su estatus.'),
            'Egreso': sec(
                'Registra el egreso de los alumnos que concluyeron créditos y aprobaron su defensa, y habilita su diploma digital.',
                ['Localice al alumno y pulse <b>Consultar expediente</b> para revisar la prevalidación académica.',
                 'Verifique créditos y defensa aprobada.',
                 'Confirme el egreso. Si faltan requisitos, el sistema los enumera.']),
            'Egresados': sec('Directorio de egresados con filtros por programa y generación.'),
            'Histórico': sec('Bitácora histórica con resumen, actividad mensual, eventos filtrables y línea de tiempo por persona.'),
            'Reportes': sec('Descarga reportes de alumnos, inscripciones y egresados en XLSX o PDF.'),
        },
    },
    {
        'clave': 'aspirante', 'nombre': 'Aspirante', 'usuario': 'aspirante',
        'intro': 'El panel del Aspirante acompaña el proceso de admisión después del preregistro. Su encabezado muestra el '
                 'nombre, el programa, la unidad y el estado actual de la solicitud. Las secciones se abren y cierran como '
                 'apartados desplegables en la columna izquierda.',
        'secciones': {
            'Notificaciones': sec('Lista los avisos del proceso (cambios de estado, entrevistas programadas, observaciones a '
                                  'documentos). El número indica cuántos avisos no se han leído; pueden marcarse como leídos.'),
            'Mi perfil': sec('Permite actualizar el teléfono, los datos de contacto y la fotografía. La CURP y el correo son de '
                             'solo lectura.'),
            'Inicio': sec('Resumen de la solicitud: etapas del proceso (preregistro recibido, proceso iniciado, en revisión, '
                          'aceptado), etapa actual, accesos rápidos y el estado de la solicitud de apoyo económico.',
                          nota_='La solicitud de apoyo se habilita cuando Coordinación registra la aprobación del curso '
                                'propedéutico; requiere banco y una CLABE válida de 18 dígitos.'),
            'Expediente': sec('Muestra los datos capturados en el preregistro: datos personales, domicilios, escolaridad y '
                              'adscripción.'),
            'Seguimiento LIDA': sec('Presenta el avance del proceso de admisión en el motor LIDA, con las etapas completadas y '
                                    'pendientes y, cuando existe, el dictamen del Colegio de Profesores.'),
            'Documentos': sec(
                'Carga de los documentos requeridos: currículum vitae, título o comprobante de estudios, carta de motivos y '
                'carta de recomendación.',
                ['Pulse <b>Cargar</b> en el documento correspondiente.', 'Seleccione un archivo PDF de hasta 10 MB.',
                 'Espere la confirmación; el documento queda <b>Pendiente de revisión</b>.',
                 'Si Coordinación registra una observación, use <b>Reemplazar</b> para subir la versión corregida.'],
                'Cuando la solicitud se resuelve (aceptada o rechazada) los documentos quedan en solo lectura.'),
            'Entrevistas': sec('Muestra fecha, hora y estado de las entrevistas virtuales. Cuando el docente inicia la '
                               'entrevista se habilita el botón para unirse a la videollamada.'),
            'Exámenes en línea': sec(
                'Lista los exámenes de admisión disponibles con su ventana de fechas e intentos.',
                ['Pulse <b>Iniciar</b> dentro de la ventana de disponibilidad.',
                 'Responda las preguntas; el avance se guarda en el navegador.',
                 'Pulse <b>Enviar respuestas</b>. Si el tiempo termina, las respuestas se envían automáticamente.'],
                'Si el envío falla por la conexión, puede reintentar sin perder las respuestas.'),
        },
    },
    {
        'clave': 'alumno', 'nombre': 'Alumno', 'usuario': 'alumno',
        'intro': 'El panel del Alumno reúne la trayectoria académica: inscripción de materias, calificaciones, horario, '
                 'exámenes, solicitudes, entrevistas, proyecto de tesis, diploma digital y trámites.',
        'secciones': {
            'Resumen': sec('Muestra créditos cursados, promedio, materias en curso, avisos y el estado del proyecto de tesis.'),
            'Mi perfil': sec('Datos personales y de contacto; permite actualizar teléfono y fotografía. La matrícula es de solo lectura.'),
            'Materias e inscripciones': sec(
                'Muestra la oferta de materias del periodo, el número de materias requeridas y las materias ya inscritas '
                'con su estado de validación.',
                ['Verifique que el periodo de inscripción esté abierto (se muestra con sus fechas).',
                 'Seleccione las materias a cursar y pulse <b>Enviar inscripción</b>.',
                 'Espere la validación de Servicios Escolares; el estado se muestra en cada materia.',
                 'Descargue la boleta de inscripción cuando lo requiera.'],
                'Si el periodo está cerrado, puede solicitar una inscripción extemporánea con una justificación.'),
            'Calificaciones y avance': sec('Calificaciones parciales y finales por materia y periodo, promedio y avance de créditos.'),
            'Horario': sec('Horario semanal de clases del periodo, con opción de descarga.'),
            'Exámenes en línea': sec('Exámenes asignados por Coordinación Académica, con ventana de disponibilidad, intentos y resultados.'),
            'Solicitudes académicas': sec(
                'Envío y seguimiento de solicitudes (baja de materia, cambios, revisiones).',
                ['Pulse <b>Nueva solicitud</b> y elija el tipo.', 'Describa la solicitud y envíela.',
                 'Consulte la respuesta y el estado en la misma sección.']),
            'Entrevistas virtuales': sec('Entrevistas programadas con fecha, hora y enlace de acceso.'),
            'Proyecto de tesis': sec(
                'Permite solicitar director de tesis, registrar la propuesta de proyecto y consultar su dictamen, la revisión '
                'antiplagio, el jurado y la defensa. Coordinación Académica y el director dan seguimiento al dictamen.',
                ['Si aún no tiene director, capture la línea de investigación y el director sugerido y envíe la solicitud.',
                 'Con director asignado, capture título y resumen de la propuesta y envíela a revisión.',
                 'Mientras el proyecto esté en borrador o con observaciones puede corregirlo con <b>Editar</b>.',
                 'Consulte más abajo la revisión antiplagio, el jurado y la defensa.']),
            'Diploma digital': sec('Permite descargar el diploma digital una vez que Servicios Escolares registra el egreso; '
                                   'antes de eso la opción aparece deshabilitada.'),
            'Documentos y trámites': sec('Solicitud y descarga de constancias y documentos oficiales.'),
        },
    },
    {
        'clave': 'docente', 'nombre': 'Docente', 'usuario': 'docente',
        'intro': 'El panel del Docente permite gestionar los cursos asignados, evaluar a los estudiantes, calificar exámenes en '
                 'línea, conducir entrevistas virtuales a aspirantes y generar reportes.',
        'secciones': {
            'Resumen': sec('Indicadores de cursos, estudiantes y pendientes de evaluación.'),
            'Mis cursos': sec('Materias asignadas en la carga académica publicada, por periodo.'),
            'Estudiantes': sec('Lista de estudiantes inscritos en los cursos del docente.'),
            'Calificaciones': sec(
                'Captura de calificaciones de los estudiantes de sus cursos.',
                ['Pulse <b>+ Registrar calificación</b> (botón superior del panel).',
                 'Seleccione el curso y el estudiante y capture la calificación (rango de 0 a 10).',
                 'Guarde. Si el valor está fuera de rango o el periodo de captura está cerrado, el sistema lo rechaza.',
                 'Descargue el acta del curso en PDF desde <b>Reportes</b> cuando termine la captura.']),
            'Exámenes': sec(
                'Lista los exámenes en línea en los que Coordinación Académica asignó al docente como evaluador, con '
                'estudiante, tipo, fecha programada, estado, calificación e intentos.',
                ['Filtre por estudiante, tipo o estado.',
                 'Abra el examen desde la columna de acciones para revisar las respuestas.',
                 'Registre la calificación cuando el examen requiera evaluación del docente.'],
                'Los exámenes los crea y asigna Coordinación Académica; el docente participa como evaluador.'),
            'Entrevistas': sec(
                'Programación y conducción de entrevistas virtuales con aspirantes mediante Jitsi. La tabla muestra estudiante, '
                'propósito, fecha, estado, enlace de videollamada y notas.',
                ['Pulse <b>+ Programar entrevista</b> y elija aspirante, propósito, fecha y hora.',
                 'El día de la entrevista iníciela desde las acciones; se habilita el enlace de videollamada para el aspirante.',
                 'Al terminar registre las notas y la evaluación. Las notas son privadas y el aspirante no las ve.']),
            'Reportes': sec('Descarga de listas de estudiantes y actas de calificaciones de sus cursos.'),
            'Mi perfil': sec('Datos de contacto, departamento y fotografía del docente.'),
        },
    },
    {
        'clave': 'director', 'nombre': 'Director de tesis', 'usuario': 'director',
        'intro': 'El panel del Director de tesis da seguimiento a los tesistas desde la solicitud de dirección hasta la defensa. '
                 'Un director también puede abrir el panel docente desde el menú superior (≡) para gestionar sus cursos.',
        'secciones': {
            'Resumen': sec('Indicadores de acompañamiento: tesistas asignados, expedientes activos, proyectos y avances por revisar.'),
            'Dashboard analítico': sec('Métricas de tesistas asignados, expedientes activos, proyectos y promedio general, con la '
                                       'distribución de materias aprobadas, en curso y reprobadas y los proyectos en revisión.'),
            'Mis tesistas': sec('Tabla de tesistas asignados con matrícula, programa, materias cursadas, materias aprobadas y '
                                'promedio, con búsqueda y filtro por programa.'),
            'Avances de tesis': sec('Avance académico de cada tesista: materias, aprobadas, reprobadas, créditos y promedio.'),
            'Examen predoctoral': sec(
                'Programación del examen predoctoral de los tesistas y registro de su resultado.',
                ['Programe el examen eligiendo al tesista, la fecha y los sinodales.',
                 'Después del examen, registre el resultado y las observaciones.']),
            'Evaluaciones': sec('Trayectoria académica de los tesistas por materia: calificaciones parciales, calificación final '
                                'y estado, con filtros por tesista y estado.'),
            'Jurado y defensa': sec(
                'Integración del jurado y programación de la defensa de los proyectos aprobados.',
                ['Seleccione el proyecto aprobado.',
                 'Agregue a los integrantes del jurado con su función (presidente, secretario, vocal).',
                 'Registre la revisión antiplagio (PDF y porcentaje de similitud).',
                 'Programe la defensa y, al concluir, registre el resultado.'],
                'Esta sección se habilita cuando el director aprueba el proyecto de tesis.'),
            'Expedientes digitales': sec('Expedientes digitales de los tesistas con fecha de creación, estado y firma electrónica '
                                         'del director. Los expedientes pendientes se firman desde la columna de acciones.'),
            'Proyectos de tesis': sec('Proyectos registrados por los tesistas con título, resumen, línea, porcentaje de avance y '
                                      'estado. Desde aquí el director revisa la propuesta, registra el avance y la aprueba o la '
                                      'devuelve con observaciones.'),
            'Mi perfil': sec('Datos de contacto y líneas de investigación del director.'),
        },
    },
    {
        'clave': 'admin', 'nombre': 'Administrador', 'usuario': 'administrador',
        'intro': 'El panel de Administración controla la plataforma: usuarios y roles, alumnos y docentes, catálogos, periodos, '
                 'solicitudes, reportes, auditoría, seguridad, mantenimiento y configuración. Los botones superiores permiten '
                 'exportar en XLSX o PDF y agregar usuarios desde cualquier sección.',
        'secciones': {
            'Resumen': sec('Panorama global: usuarios por rol, actividad reciente y estado general del sistema.'),
            'Usuarios': sec(
                'Alta, edición, activación y desactivación de usuarios y asignación de su rol.',
                ['Pulse <b>+ Agregar usuario</b>.', 'Capture nombre, usuario, correo, rol, área y contraseña inicial.',
                 'Guarde. Si el usuario o el correo ya existen, el sistema lo indica.',
                 'Use <b>Editar</b> para modificar datos o rol, <b>Restablecer</b> para restablecer el acceso de una cuenta '
                 '(por ejemplo, tras un bloqueo por intentos fallidos) y <b>Desactivar</b> para impedir el inicio de sesión.'],
                'Todas las acciones administrativas quedan registradas en la auditoría.'),
            'Alumnos': sec('Consulta y corrección de la información de los alumnos.'),
            'Docentes y directores': sec('Consulta y corrección de la información del personal académico.'),
            'Catálogos': sec('Administración de los catálogos del sistema (programas, unidades, departamentos y otros valores '
                             'de selección).'),
            'Periodos académicos': sec('Consulta y gestión de los periodos académicos del sistema.'),
            'Solicitudes': sec('Revisión global de las solicitudes registradas en el sistema.'),
            'Reportes': sec('Reportes generales del sistema en XLSX o PDF.'),
            'Auditoría': sec('Bitácora de acciones administrativas con filtros por usuario, acción y fechas.'),
            'Seguridad': sec('Resumen de los controles de acceso y del estado de las cuentas: activas, inactivas o bloqueadas '
                             'y bloqueos temporales vigentes.'),
            'Mantenimiento': sec('Estado de los servicios del sistema y lineamientos de respaldo. Las operaciones de respaldo y '
                                 'restauración se realizan desde la infraestructura autorizada, no desde el panel.'),
            'Configuración': sec('Parámetros generales del sistema, como el número de intentos fallidos antes del bloqueo '
                                 'temporal y los avisos por correo.'),
        },
    },
]


# --------------------------------------------------------------------------------------------
# Capítulos
# --------------------------------------------------------------------------------------------

def introduccion():
    h = [titulo('1. Introducción', h1, 0)]
    h.append(titulo('1.1 Propósito del manual', h2, 1))
    h.append(Paragraph(
        'Este manual explica cómo utilizar SINAC NEXT, el sistema de información académica del Cinvestav basado en el '
        'lenguaje iconográfico LIDA. Describe el acceso al sistema, los elementos comunes de la interfaz y, para cada '
        'perfil de usuario, las secciones de su panel y los procedimientos para realizar las tareas más frecuentes. Todas '
        'las pantallas son capturas reales del sistema con datos de demostración.', cuerpo))
    h.append(titulo('1.2 A quién va dirigido', h2, 1))
    h.append(Paragraph('El manual está dirigido a todas las personas que utilizan el sistema según su perfil:', cuerpo))
    h.append(tabla([
        ['Perfil', 'Descripción', 'Capítulo'],
        ['Aspirante', 'Persona en proceso de admisión a un programa de posgrado.', '6'],
        ['Alumno', 'Estudiante inscrito en un programa.', '7'],
        ['Docente', 'Profesor o investigador que imparte cursos y evalúa.', '8'],
        ['Director de tesis', 'Docente que dirige proyectos de tesis.', '9'],
        ['Coordinación Académica', 'Personal que conduce la admisión y la operación académica.', '4'],
        ['Servicios Escolares', 'Personal de control escolar institucional.', '5'],
        ['Administrador', 'Responsable de usuarios, seguridad y configuración de la plataforma.', '10'],
    ], [4.2 * cm, ANCHO_UTIL - 6.2 * cm, 2 * cm]))
    h.append(Spacer(1, 8))
    h.append(titulo('1.3 Convenciones', h2, 1))
    h += vinetas([
        'Los nombres de botones, opciones y secciones aparecen en <b>negritas</b>, por ejemplo <b>Iniciar sesión</b>.',
        'Los procedimientos se presentan como pasos numerados que deben seguirse en orden.',
        'Los recuadros verdes marcados como <b>Nota</b> contienen reglas o advertencias importantes.',
        'Los números que aparecen junto a una opción del menú lateral indican elementos pendientes o registros disponibles.',
    ])
    h.append(titulo('1.4 Requisitos', h2, 1))
    h += vinetas([
        'Navegador web actualizado: Microsoft Edge, Google Chrome, Mozilla Firefox o Safari.',
        'Conexión a internet estable. Para entrevistas virtuales se requieren cámara, micrófono y permisos del navegador.',
        'Resolución recomendada de 1280 × 720 píxeles o superior; la interfaz se adapta a tabletas y teléfonos.',
        'Cuenta proporcionada por el Cinvestav o creada mediante el preregistro (aspirantes); documentos en PDF de hasta 10 MB.',
    ])
    h.append(PageBreak())
    return h


def interfaz_general(indice):
    h = [titulo('2. Elementos generales de la interfaz', h1, 0)]
    h.append(Paragraph('Todas las pantallas de SINAC NEXT comparten la misma estructura, de modo que lo aprendido en un panel '
                       'se aplica en los demás.', cuerpo))
    h.append(titulo('2.1 Barra superior', h2, 1))
    h += vinetas([
        '<b>Logotipos</b> del Cinvestav y de SINAC NEXT a la izquierda.',
        '<b>Selector de tema</b>: alterna entre modo claro y modo oscuro.',
        '<b>Selector de idioma</b>: cambia el idioma de la interfaz (por ejemplo, Español o English).',
        '<b>Menú ≡</b>: da acceso a Inicio, Portal de aspirantes, Iniciar sesión o al panel del usuario, Contacto y Cerrar sesión.',
    ])
    h.append(titulo('2.2 Panel de trabajo', h2, 1))
    h += vinetas([
        '<b>Encabezado del panel</b>: indica el perfil, el título de la sección y acciones generales como <b>Actualizar '
        'información</b> o <b>Cerrar sesión</b>.',
        '<b>Menú lateral</b>: lista las secciones disponibles para el perfil, agrupadas por tema. La sección activa aparece resaltada.',
        '<b>Área de contenido</b>: muestra la información de la sección elegida en tarjetas, tablas y formularios.',
        '<b>Tablas</b>: incluyen buscador, filtros, ordenamiento y paginación; muchas permiten exportar a XLSX o PDF.',
        '<b>Campana de notificaciones</b>: el botón flotante de la esquina inferior derecha muestra los avisos recientes y '
        'su número de no leídos.',
    ])
    h.append(titulo('2.3 Cierre de sesión y expiración', h2, 1))
    h.append(Paragraph(
        'Para salir, pulse <b>Cerrar sesión</b> en el encabezado o en el menú lateral y confirme en el cuadro de diálogo. Por '
        'seguridad, la sesión se cierra automáticamente después de una hora de inactividad; en ese caso aparece un aviso y '
        'basta con iniciar sesión de nuevo.', cuerpo))
    cierre = next((s for s in indice.get('servicios', []) if limpiar(s['seccion']) == 'Cerrar sesión'), None)
    if cierre:
        h.append(KeepTogether(figura(cierre['imagen'], 'Confirmación de cierre de sesión.')))
    h.append(titulo('2.4 Mensajes del sistema', h2, 1))
    h.append(tabla([
        ['Tipo de mensaje', 'Significado y acción recomendada'],
        ['Error en un campo', 'El dato es inválido o ya existe (por ejemplo, CURP duplicada). Corrija el campo marcado en rojo.'],
        ['Confirmación', 'La operación se realizó correctamente.'],
        ['Acceso denegado (403)', 'La sección no corresponde a su perfil. Regrese a su panel desde el menú ≡.'],
        ['Página no encontrada (404)', 'La dirección no existe. Use el botón <b>Ir al inicio</b>.'],
        ['Servicio no disponible', 'El servidor no responde temporalmente. Espere unos minutos e intente de nuevo.'],
        ['Demasiadas solicitudes', 'Se excedió el límite de intentos en poco tiempo. Espere antes de volver a intentar.'],
    ], [4.4 * cm, ANCHO_UTIL - 4.4 * cm]))
    h.append(PageBreak())
    return h


def acceso(indice):
    pub = {s['seccion']: s['imagen'] for s in indice.get('publico', [])}
    h = [titulo('3. Acceso al sistema', h1, 0)]
    h.append(titulo('3.1 Página de inicio', h2, 1))
    h.append(Paragraph('Al abrir la dirección del sistema se muestra la página de inicio con información de las unidades del '
                       'Cinvestav, la misión y la visión. Desde el menú ≡ se accede al portal de aspirantes y al inicio de sesión.', cuerpo))
    if 'Inicio' in pub:
        h.append(KeepTogether(figura(pub['Inicio'], 'Página de inicio de SINAC NEXT.')))
    h.append(titulo('3.2 Preregistro de aspirantes', h2, 1))
    h.append(Paragraph('Las personas interesadas en ingresar a un programa crean su cuenta en el Portal de aspirantes.', cuerpo))
    h += pasos([
        'Abra el menú ≡ y elija <b>Portal Aspirantes</b>.',
        'Lea el aviso y pulse <b>Aceptar y continuar</b>. El Aviso de privacidad está disponible en el pie de página.',
        'Complete las secciones del menú izquierdo: Datos generales, Domicilio actual, Domicilio permanente, Datos de un '
        'familiar, Escolaridad, Idiomas, Publicaciones, Apoyos, Experiencia profesional, Cinvestav y Adscripción. La barra '
        'superior muestra el porcentaje de avance y cada sección indica cuántos campos obligatorios faltan.',
        'Defina usuario y contraseña. La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula y un número.',
        'Envíe el preregistro. Si algún dato es inválido o ya existe (CURP, usuario o correo), el campo se marca con el error.',
        'Al confirmarse el registro, inicie sesión con su usuario y contraseña para continuar en el panel del Aspirante.',
    ])
    for clave, pie in (('Portal de aspirantes', 'Aviso previo al preregistro.'),
                       ('Formulario de preregistro', 'Formulario de preregistro con avance por secciones.')):
        if clave in pub:
            h.append(KeepTogether(figura(pub[clave], pie)))
    h.append(titulo('3.3 Iniciar sesión', h2, 1))
    h.append(Paragraph('Todos los perfiles usan la misma pantalla de acceso; el sistema identifica el perfil a partir de las '
                       'credenciales y abre el panel correspondiente.', cuerpo))
    h += pasos([
        'Abra el menú ≡ y elija <b>Iniciar sesión</b>.',
        'Escriba su <b>usuario o correo institucional</b> y su <b>contraseña</b>. Puede usar <b>Mostrar</b> para verificarla.',
        'Marque <b>Recuérdame en este dispositivo</b> solo si usa un equipo personal.',
        'Pulse <b>Inicia sesión</b>. Se abrirá el panel de su perfil.',
    ])
    if 'Iniciar sesión' in pub:
        h.append(KeepTogether(figura(pub['Iniciar sesión'], 'Pantalla de inicio de sesión.')))
    h += nota('Después de varios intentos fallidos consecutivos la cuenta se bloquea temporalmente. Por seguridad, el mensaje '
              'es siempre «Credenciales inválidas», sin indicar si el usuario existe. Si olvidó su contraseña o su cuenta '
              'quedó bloqueada, solicite apoyo al Administrador del sistema.', 'Importante')
    if 'Error de credenciales' in pub:
        h.append(KeepTogether(figura(pub['Error de credenciales'], 'Mensaje de credenciales inválidas.')))
    h.append(PageBreak())
    return h


def capitulo_rol(numero, rol, indice):
    capturas = indice.get(rol['clave'], [])
    h = [titulo(f'{numero}. Panel de {rol["nombre"]}', h1, 0)]
    h.append(Paragraph(rol['intro'], cuerpo))
    vistas = []
    for c in capturas:
        nombre = limpiar(c['seccion'])
        if nombre == 'Cerrar sesión' or nombre in [v[0] for v in vistas]:
            continue
        vistas.append((nombre, c['imagen']))
    faltantes = [n for n, _ in vistas if n not in rol['secciones']]
    if faltantes:
        print(f'  Aviso: sin descripción en {rol["clave"]}: {faltantes}', file=sys.stderr)
    filas = [['Sección', 'Para qué sirve']]
    for nombre, _ in vistas:
        desc = rol['secciones'].get(nombre, {}).get('desc', '')
        filas.append([nombre, desc.split('. ')[0].rstrip('.') + '.'])
    h.append(titulo(f'{numero}.1 Secciones del panel', h2, 1))
    h.append(tabla(filas, [4.6 * cm, ANCHO_UTIL - 4.6 * cm]))
    h.append(titulo(f'{numero}.2 Uso de cada sección', h2, 1))
    for i, (nombre, ruta) in enumerate(vistas, 1):
        info = rol['secciones'].get(nombre, sec('Sección del panel.'))
        cabecera = [titulo(f'{numero}.2.{i} {nombre}', h3, 2), Paragraph(info['desc'], cuerpo)]
        h.append(KeepTogether(cabecera + figura(ruta, f'{rol["nombre"]}: sección {nombre}.')))
        if info['pasos']:
            h.append(Paragraph('<b>Procedimiento:</b>', cuerpo))
            h += pasos(info['pasos'])
            h.append(Spacer(1, 4))
        if info['nota']:
            h += nota(info['nota'])
    h.append(PageBreak())
    return h


def preguntas_frecuentes():
    h = [titulo('11. Preguntas frecuentes y solución de problemas', h1, 0)]
    h.append(tabla([
        ['Situación', 'Solución'],
        ['Olvidé mi contraseña.', 'Solicite al Administrador el restablecimiento. Por seguridad, la recuperación se realiza '
                                  'mediante el Administrador.'],
        ['Mi cuenta aparece bloqueada.', 'Espere a que termine el bloqueo temporal o solicite al Administrador que la desbloquee.'],
        ['No puedo subir un documento.', 'Verifique que sea un PDF real de hasta 10 MB y que su solicitud no haya sido resuelta.'],
        ['No aparecen materias para inscribir.', 'Confirme que el periodo de inscripción esté abierto y que Coordinación le '
                                                 'haya asignado semestre y plan de estudios.'],
        ['El enlace de un documento ya no abre.', 'Los enlaces caducan por seguridad. Vuelva a abrir el documento desde el sistema.'],
        ['No puedo unirme a la entrevista.', 'El enlace se habilita solo cuando el docente inicia la entrevista. Permita el uso '
                                             'de cámara y micrófono en el navegador.'],
        ['El examen se cerró antes de enviar.', 'Al agotarse el tiempo las respuestas se envían automáticamente. Consulte el '
                                                'resultado en la sección de exámenes.'],
        ['Veo «Acceso denegado».', 'La sección no corresponde a su perfil. Use el menú ≡ para volver a su panel.'],
        ['Se cerró mi sesión.', 'La sesión expira tras una hora de inactividad. Inicie sesión de nuevo.'],
        ['El diploma digital está deshabilitado.', 'Se habilita cuando Servicios Escolares registra su egreso.'],
    ], [5.2 * cm, ANCHO_UTIL - 5.2 * cm]))
    h.append(PageBreak())
    h.append(titulo('12. Glosario', h1, 0))
    h.append(tabla([
        ['Término', 'Definición'],
        ['LIDA', 'Lenguaje iconográfico con el que se modelan los procesos académicos del sistema.'],
        ['Motor LIDA (Camunda)', 'Componente que ejecuta los procesos de admisión, entrevistas y cargas académicas.'],
        ['Preregistro', 'Registro inicial del aspirante que crea su cuenta e inicia su proceso de admisión.'],
        ['Expediente digital', 'Conjunto de datos y documentos de una persona; se crea con folio al ser aceptada.'],
        ['Carga académica', 'Asignación de materias a docentes en un periodo.'],
        ['Inscripción extemporánea', 'Inscripción realizada fuera del periodo ordinario con autorización.'],
        ['Colegio de Profesores', 'Cuerpo colegiado que emite el dictamen sobre los aspirantes.'],
        ['Examen predoctoral', 'Evaluación previa a la defensa de tesis doctoral.'],
        ['Histórico', 'Bitácora de eventos académicos por persona (línea de tiempo).'],
        ['Auditoría', 'Registro de las acciones administrativas realizadas en el sistema.'],
        ['CLABE', 'Clave bancaria estandarizada de 18 dígitos para depósitos de apoyo económico.'],
    ], [4.6 * cm, ANCHO_UTIL - 4.6 * cm]))
    return h


def main():
    with open(os.path.join(CAPTURAS, 'indice.json'), encoding='utf-8') as f:
        indice = json.load(f)
    orden = {'coordinacion': 4, 'servicios': 5, 'aspirante': 6, 'alumno': 7, 'docente': 8, 'director': 9, 'admin': 10}
    temporal = SALIDA.replace('.pdf', '_tmp.pdf')
    doc = Documento(temporal, TITULO)
    toc = TableOfContents()
    toc.levelStyles = toc_estilos
    toc.dotsMinLevel = 0
    historia = portada(TITULO) + [Paragraph('Índice', h1), toc, PageBreak()]
    historia += introduccion() + interfaz_general(indice) + acceso(indice)
    for rol in sorted(ROLES, key=lambda r: orden[r['clave']]):
        historia += capitulo_rol(orden[rol['clave']], rol, indice)
    historia += preguntas_frecuentes()
    doc.multiBuild(historia, canvasmaker=canvas_numerado(TITULO))
    os.replace(temporal, SALIDA)
    print('Generado:', SALIDA, f'({Figuras.n} figuras)')


if __name__ == '__main__':
    main()
