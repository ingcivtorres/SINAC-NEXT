"""Genera docs/SINAC_NEXT_Base_de_Datos.pdf: diagrama de clases, diagrama entidad-relación y diccionario de datos.

La estructura se toma de docs/assets/modelo_datos.json, generado con scripts/extraer_modelo_datos.py.
"""
import json
import math
import os
from collections import defaultdict

from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, PolyLine, Rect, String
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import KeepTogether, NextPageTemplate, PageBreak, Paragraph, Spacer
from reportlab.platypus.tableofcontents import TableOfContents

from plantilla_cinvestav import (
    ANCHO_UTIL, GRIS, RAIZ, VERDE_OSCURO, DiagramaAjustado, Documento, canvas_numerado, celda,
    cuerpo, h1, h2, h3, pie_fig, portada, tabla, titulo, toc_estilos, vineta,
)

SALIDA = os.path.join(RAIZ, 'docs', 'SINAC_NEXT_Base_de_Datos.pdf')
TITULO = 'Documento de Base de Datos'

with open(os.path.join(RAIZ, 'docs', 'assets', 'modelo_datos.json'), encoding='utf-8') as archivo:
    MODELOS = {m['modelo']: m for m in json.load(archivo)}

PREFIJO = 'preregistro_'
LINEA = colors.HexColor('#3F4A54')

# ---------------------------------------------------------------------------
# Contenido descriptivo
# ---------------------------------------------------------------------------
MODULOS = [
    {
        'clave': 'usuarios', 'nombre': 'Usuarios, admisión y expediente', 'color': '#00957A',
        'modelos': ['Aspirante', 'DocumentoAspirante', 'SeguimientoSolicitud', 'EvaluacionColegio', 'ExpedienteDigital', 'FirmaElectronica'],
        'descripcion': ('Concentra la cuenta única de cada persona (aspirante, alumno, docente, director, coordinación, servicios escolares '
                        'o administrador), los documentos de admisión, el seguimiento de la solicitud, el dictamen del Colegio de '
                        'Profesores y el expediente digital con sus firmas electrónicas.'),
    },
    {
        'clave': 'planes', 'nombre': 'Planes de estudio y cargas académicas', 'color': '#2F6DB5',
        'modelos': ['ConfiguracionPrograma', 'PlanEstudioMateria', 'Materia', 'CargaAcademicaMateria', 'CargaAcademica', 'PeriodoInscripcion'],
        'descripcion': ('Define el catálogo de materias, las reglas de cada programa y su plan de estudios, los periodos de inscripción '
                        'y las cargas académicas que asignan grupos, horarios, salones y docentes por periodo.'),
    },
    {
        'clave': 'inscripciones', 'nombre': 'Inscripciones y solicitudes académicas', 'color': '#1F7A8C',
        'modelos': ['Inscripcion', 'SolicitudAcademica', 'SolicitudInscripcionExtemporanea', 'SolicitudInscripcionExtemporaneaMateria'],
        'referencias': ['PeriodoInscripcion', 'Materia', 'CargaAcademicaMateria'],
        'descripcion': ('Registra la inscripción de los alumnos a materias con sus calificaciones parciales y finales, las solicitudes de '
                        'inscripción extemporánea con las materias pedidas y las solicitudes académicas (historial, reinscripción, ajustes).'),
    },
    {
        'clave': 'tesis', 'nombre': 'Tesis y egreso', 'color': '#7A3FA0',
        'modelos': ['JuradoProyecto', 'DefensaTesis', 'ProyectoTesis', 'RevisionAntiplagio', 'SolicitudDireccionTesis', 'EgresoAlumno'],
        'descripcion': ('Da soporte al proceso de titulación: solicitud y asignación de director, proyecto de tesis con su avance, jurado, '
                        'revisiones antiplagio, defensa y registro formal del egreso.'),
    },
    {
        'clave': 'evaluacion', 'nombre': 'Evaluación en línea', 'color': '#B5642F',
        'modelos': ['EntrevistaVirtual', 'ExamenEnLinea', 'PreguntaExamen', 'RespuestaExamen'],
        'descripcion': ('Almacena los exámenes en línea con sus preguntas y las respuestas de cada evaluado, así como las entrevistas '
                        'virtuales realizadas por videoconferencia.'),
    },
    {
        'clave': 'auditoria', 'nombre': 'Auditoría y configuración', 'color': '#5D6D7E',
        'modelos': ['HistorialPersona', 'AuditoriaSistema', 'ConfiguracionSistema'],
        'descripcion': ('Mantiene la trazabilidad del sistema: la bitácora histórica por persona, la auditoría de acciones administrativas '
                        'y los parámetros institucionales configurables.'),
    },
]

# Distribución en columnas de cada diagrama por módulo (la clase Aspirante se dibuja como barra superior).
DISTRIBUCION = {
    'usuarios': [['DocumentoAspirante'], ['SeguimientoSolicitud'], ['EvaluacionColegio'], ['ExpedienteDigital', 'FirmaElectronica']],
    'planes': [['ConfiguracionPrograma', 'PlanEstudioMateria'], ['Materia'], ['CargaAcademicaMateria'], ['CargaAcademica', 'PeriodoInscripcion']],
    'inscripciones': [['Inscripcion'], ['PeriodoInscripcion', 'Materia', 'SolicitudAcademica'], ['SolicitudInscripcionExtemporanea'],
                      ['SolicitudInscripcionExtemporaneaMateria', 'CargaAcademicaMateria']],
    'tesis': [['JuradoProyecto', 'DefensaTesis'], ['ProyectoTesis'], ['RevisionAntiplagio', 'SolicitudDireccionTesis'], ['EgresoAlumno']],
    'evaluacion': [['EntrevistaVirtual'], ['ExamenEnLinea'], ['PreguntaExamen', 'RespuestaExamen']],
    'auditoria': [['HistorialPersona'], ['AuditoriaSistema'], ['ConfiguracionSistema']],
}

DESCRIPCION_TABLA = {
    'Aspirante': 'Tabla de usuarios del sistema (modelo de autenticación de Django). Una misma cuenta evoluciona de aspirante a alumno y almacena también al personal (docentes, directores, coordinación, servicios escolares y administración) mediante la columna rol.',
    'DocumentoAspirante': 'Documentos de admisión cargados por el aspirante (CV, título, cartas). Solo puede existir un documento por tipo y aspirante.',
    'ExpedienteDigital': 'Expediente digital creado automáticamente al aceptar una solicitud; relación uno a uno con la persona.',
    'FirmaElectronica': 'Firmas electrónicas aplicadas sobre un expediente digital, con huella única de verificación.',
    'ProyectoTesis': 'Registro institucional del proyecto de tesis del alumno, su director, avance y dictamen académico.',
    'JuradoProyecto': 'Integrantes del jurado de un proyecto de tesis con su función y estado de confirmación.',
    'DefensaTesis': 'Programación y resultado de la defensa pública de un proyecto de tesis (uno a uno con el proyecto).',
    'RevisionAntiplagio': 'Resultados de las revisiones de similitud realizadas sobre el documento de tesis.',
    'CargaAcademica': 'Encabezado de la carga académica de un periodo; su aprobación se coordina con el proceso LIDA en Camunda.',
    'CargaAcademicaMateria': 'Grupos de la carga académica: materia, docente, horario, salón, capacidad y modalidad.',
    'SeguimientoSolicitud': 'Eventos y notificaciones del proceso de admisión mostrados al aspirante.',
    'HistorialPersona': 'Bitácora histórica de cambios de cuentas, actividad académica, tesis, documentos y egreso por persona.',
    'EgresoAlumno': 'Registro formal del egreso de un alumno (uno a uno), con promedio final y tesis.',
    'Materia': 'Catálogo institucional de materias con su clave, categoría, créditos y datos de impartición por defecto.',
    'ConfiguracionPrograma': 'Reglas académicas de cada programa: grado, periodicidad, duración y créditos requeridos.',
    'PlanEstudioMateria': 'Materias que integran el plan de estudios de un programa y el periodo sugerido para cursarlas.',
    'SolicitudDireccionTesis': 'Solicitud del alumno para la asignación de director de tesis y su flujo de aceptación.',
    'PeriodoInscripcion': 'Periodos con ventana de apertura y cierre para inscripciones.',
    'AuditoriaSistema': 'Bitácora de acciones administrativas con los datos anteriores y nuevos y la dirección IP.',
    'ConfiguracionSistema': 'Parámetros institucionales en formato clave-valor editables por el administrador.',
    'Inscripcion': 'Inscripción de un alumno a una materia en un periodo, con calificaciones parciales, final y validación de Servicios Escolares.',
    'SolicitudInscripcionExtemporanea': 'Solicitud de inscripción fuera de la ventana del periodo; solo puede haber una pendiente por alumno y periodo.',
    'SolicitudInscripcionExtemporaneaMateria': 'Grupos de la carga académica solicitados dentro de una solicitud extemporánea.',
    'SolicitudAcademica': 'Solicitudes académicas de los alumnos (historial, reinscripción, ajuste de materias) y su resolución.',
    'ExamenEnLinea': 'Examen en línea asignado a un aspirante o alumno, con ventana, intentos, calificación y vínculo con LIDA.',
    'PreguntaExamen': 'Preguntas de opción múltiple de un examen en línea.',
    'RespuestaExamen': 'Respuesta de un evaluado a una pregunta; una respuesta por pregunta y evaluado.',
    'EntrevistaVirtual': 'Entrevistas por videoconferencia (Jitsi) entre un docente y un aspirante o alumno.',
    'EvaluacionColegio': 'Evaluación y dictamen del Colegio de Profesores sobre un aspirante.',
}

DESC_COMUN = {
    'id': 'Identificador único autoincremental.',
    'created_at': 'Fecha y hora de creación del registro.',
    'updated_at': 'Fecha y hora de la última modificación.',
    'estado': 'Estado actual del registro.',
    'observaciones': 'Observaciones registradas.',
    'comentario': 'Comentario libre.',
    'descripcion': 'Descripción.',
    'titulo': 'Título.',
    'nombre': 'Nombre.',
    'archivo': 'Ruta relativa del archivo en el almacenamiento de medios.',
    'nombre_original': 'Nombre original del archivo cargado.',
    'tamano': 'Tamaño del archivo en bytes.',
    'business_key': 'Clave de negocio que vincula el registro con su instancia de proceso LIDA.',
    'camunda_instance_id': 'Identificador de la instancia de proceso en el motor Camunda.',
    'horario': 'Horario de impartición.',
    'salon': 'Salón asignado.',
    'capacidad': 'Cupo máximo de alumnos.',
    'modalidad': 'Modalidad de impartición o realización.',
    'aspirante': 'Persona (aspirante o alumno) a la que pertenece el registro.',
    'alumno': 'Alumno al que pertenece el registro.',
    'docente': 'Docente asignado.',
    'director': 'Director de tesis.',
    'evaluador': 'Persona que evalúa.',
    'revisado_por': 'Usuario que revisó el registro.',
    'resuelta_por': 'Usuario que resolvió la solicitud.',
    'registrado_por': 'Usuario que registró la información.',
    'registrada_por': 'Usuario que registró la inscripción extemporánea.',
    'realizado_por': 'Usuario que realizó el cambio.',
    'actualizado_por': 'Usuario que actualizó el parámetro.',
    'proyecto': 'Proyecto de tesis relacionado.',
    'materia': 'Materia relacionada.',
    'periodo_inscripcion': 'Periodo de inscripción relacionado.',
    'fecha_programada': 'Fecha y hora programada.',
    'fecha_inicio': 'Fecha y hora de inicio.',
    'fecha_fin': 'Fecha y hora de término.',
    'duracion_minutos': 'Duración en minutos.',
    'calificacion': 'Calificación obtenida (escala 0 a 10).',
    'retroalimentacion': 'Retroalimentación para el evaluado.',
    'orden': 'Posición para el ordenamiento.',
    'linea_investigacion': 'Línea de investigación.',
    'justificacion': 'Justificación de la solicitud.',
    'motivo': 'Motivo de la solicitud.',
    'tipo': 'Tipo de registro.',
    'activo': 'Indica si el registro está vigente.',
    'clave': 'Clave única.',
    'valor': 'Valor del parámetro.',
    'programa': 'Programa de posgrado.',
    'periodo': 'Periodo académico en texto.',
    'rol': 'Rol de la persona.',
    'leido': 'Indica si el aspirante ya leyó la notificación.',
}

DESC_CAMPO = {
    ('Aspirante', 'password'): 'Hash de la contraseña (PBKDF2 de Django).',
    ('Aspirante', 'last_login'): 'Fecha y hora del último inicio de sesión.',
    ('Aspirante', 'is_superuser'): 'Indica si tiene todos los permisos.',
    ('Aspirante', 'usuario'): 'Nombre de usuario para iniciar sesión.',
    ('Aspirante', 'matricula'): 'Matrícula institucional asignada al convertirse en alumno.',
    ('Aspirante', 'numero_periodo_actual'): 'Periodo que cursa actualmente el alumno.',
    ('Aspirante', 'nombre'): 'Nombre completo.',
    ('Aspirante', 'curp'): 'Clave Única de Registro de Población.',
    ('Aspirante', 'correo'): 'Correo electrónico de contacto.',
    ('Aspirante', 'telefono'): 'Teléfono de contacto.',
    ('Aspirante', 'nacimiento'): 'Fecha de nacimiento.',
    ('Aspirante', 'estado_actual'): 'Entidad federativa del domicilio actual.',
    ('Aspirante', 'municipio_actual'): 'Municipio del domicilio actual.',
    ('Aspirante', 'direccion_actual'): 'Dirección del domicilio actual.',
    ('Aspirante', 'estado_permanente'): 'Entidad federativa del domicilio permanente.',
    ('Aspirante', 'municipio_permanente'): 'Municipio del domicilio permanente.',
    ('Aspirante', 'direccion_permanente'): 'Dirección del domicilio permanente.',
    ('Aspirante', 'nombre_familiar'): 'Nombre del familiar de contacto.',
    ('Aspirante', 'parentesco'): 'Parentesco del familiar de contacto.',
    ('Aspirante', 'telefono_familiar'): 'Teléfono del familiar de contacto.',
    ('Aspirante', 'ultimo_grado'): 'Último grado de estudios.',
    ('Aspirante', 'institucion'): 'Institución de procedencia.',
    ('Aspirante', 'promedio'): 'Promedio del último grado.',
    ('Aspirante', 'idiomas'): 'Idiomas que domina.',
    ('Aspirante', 'publicaciones'): 'Publicaciones.',
    ('Aspirante', 'apoyos'): 'Apoyos o becas recibidos.',
    ('Aspirante', 'experiencia'): 'Experiencia profesional o de investigación.',
    ('Aspirante', 'sni_nivel'): 'Nivel en el Sistema Nacional de Investigadores (personal académico).',
    ('Aspirante', 'orcid'): 'Identificador ORCID del investigador.',
    ('Aspirante', 'especialidad'): 'Especialidad académica.',
    ('Aspirante', 'lineas_declaradas'): 'Líneas de investigación declaradas.',
    ('Aspirante', 'unidad'): 'Unidad del Cinvestav.',
    ('Aspirante', 'departamento'): 'Departamento de adscripción.',
    ('Aspirante', 'seccion'): 'Sección de adscripción.',
    ('Aspirante', 'tutor_propuesto'): 'Tutor propuesto por el aspirante.',
    ('Aspirante', 'director_tesis'): 'Director de tesis asignado (autorreferencia).',
    ('Aspirante', 'comentarios'): 'Comentarios del aspirante.',
    ('Aspirante', 'fecha_examen_admision'): 'Fecha del examen de admisión.',
    ('Aspirante', 'fecha_entrevista'): 'Fecha de la entrevista.',
    ('Aspirante', 'fecha_inicio_curso_propedeutico'): 'Inicio del curso propedéutico.',
    ('Aspirante', 'curso_propedeutico_nota'): 'Calificación del curso propedéutico.',
    ('Aspirante', 'curso_propedeutico_aprobado'): 'Indica si aprobó el curso propedéutico.',
    ('Aspirante', 'apoyo_solicitado'): 'Indica si solicitó apoyo económico.',
    ('Aspirante', 'apoyo_autorizado'): 'Indica si el apoyo económico fue autorizado.',
    ('Aspirante', 'banco_apoyo'): 'Banco para el depósito del apoyo.',
    ('Aspirante', 'clabe_interbancaria'): 'CLABE interbancaria (18 dígitos con dígito verificador).',
    ('Aspirante', 'solicitud_apoyo_fecha'): 'Fecha de la solicitud de apoyo.',
    ('Aspirante', 'proceso_estado'): 'Estado del proceso de admisión.',
    ('Aspirante', 'rol'): 'Rol de la cuenta. En uso: aspirante, alumno, docente, director, coordinacion, servicios y admin.',
    ('Aspirante', 'profile_photo'): 'Ruta de la fotografía de perfil.',
    ('Aspirante', 'is_active'): 'Indica si la cuenta está activa.',
    ('Aspirante', 'is_staff'): 'Indica acceso de personal administrativo.',
    ('Aspirante', 'login_failed_attempts'): 'Intentos fallidos de inicio de sesión consecutivos.',
    ('Aspirante', 'login_locked_until'): 'Fecha hasta la que la cuenta permanece bloqueada.',
    ('DocumentoAspirante', 'lida_notificado'): 'Indica si la carga se notificó al proceso LIDA.',
    ('DocumentoAspirante', 'revisado'): 'Indica si la Coordinación revisó el documento.',
    ('DocumentoAspirante', 'revisado_en'): 'Fecha de revisión del documento.',
    ('ExpedienteDigital', 'folio'): 'Folio único del expediente.',
    ('ExpedienteDigital', 'fecha_creacion'): 'Fecha de creación del expediente.',
    ('FirmaElectronica', 'expediente'): 'Expediente firmado.',
    ('FirmaElectronica', 'firmante'): 'Persona que firma.',
    ('FirmaElectronica', 'rol_firmante'): 'Rol con el que se firma.',
    ('FirmaElectronica', 'huella'): 'Huella SHA-256 que garantiza la integridad de la firma.',
    ('FirmaElectronica', 'firmado_at'): 'Fecha y hora de la firma.',
    ('ProyectoTesis', 'resumen'): 'Resumen del proyecto.',
    ('ProyectoTesis', 'objetivos'): 'Objetivos del proyecto.',
    ('ProyectoTesis', 'metodologia'): 'Metodología del proyecto.',
    ('ProyectoTesis', 'comentarios_revision'): 'Comentarios de revisión del director o la coordinación.',
    ('ProyectoTesis', 'avance_porcentaje'): 'Porcentaje de avance (0 a 100).',
    ('ProyectoTesis', 'fecha_presentacion'): 'Fecha de presentación del proyecto.',
    ('JuradoProyecto', 'jurado'): 'Docente o investigador integrante del jurado.',
    ('JuradoProyecto', 'rol'): 'Función dentro del jurado.',
    ('JuradoProyecto', 'fecha_confirmacion'): 'Fecha de confirmación de participación.',
    ('DefensaTesis', 'fecha'): 'Fecha y hora de la defensa.',
    ('DefensaTesis', 'lugar'): 'Lugar de la defensa.',
    ('DefensaTesis', 'enlace_virtual'): 'Enlace de videoconferencia.',
    ('DefensaTesis', 'calificacion_final'): 'Calificación final de la defensa.',
    ('DefensaTesis', 'acta_url'): 'Enlace al acta de examen.',
    ('RevisionAntiplagio', 'proveedor'): 'Servicio utilizado para la revisión.',
    ('RevisionAntiplagio', 'porcentaje_similitud'): 'Porcentaje de similitud detectado.',
    ('RevisionAntiplagio', 'resultados'): 'Detalle de resultados en formato JSON.',
    ('CargaAcademica', 'creador'): 'Usuario que elaboró la carga académica.',
    ('CargaAcademicaMateria', 'carga'): 'Carga académica a la que pertenece el grupo.',
    ('SeguimientoSolicitud', 'detalle'): 'Descripción del evento.',
    ('SeguimientoSolicitud', 'origen'): 'Área o proceso que generó el evento.',
    ('HistorialPersona', 'persona'): 'Persona a la que se refiere el evento.',
    ('HistorialPersona', 'rol'): 'Rol de la persona al momento del evento.',
    ('HistorialPersona', 'categoria'): 'Categoría del evento.',
    ('HistorialPersona', 'evento'): 'Tipo de evento (alta, baja, cambio, etc.).',
    ('HistorialPersona', 'campo'): 'Campo modificado.',
    ('HistorialPersona', 'detalle'): 'Descripción del evento.',
    ('HistorialPersona', 'valor_anterior'): 'Valor previo al cambio.',
    ('HistorialPersona', 'valor_nuevo'): 'Valor posterior al cambio.',
    ('HistorialPersona', 'realizado_por_nombre'): 'Nombre del responsable, conservado aunque se elimine su cuenta.',
    ('EgresoAlumno', 'fecha_egreso'): 'Fecha de egreso.',
    ('EgresoAlumno', 'generacion'): 'Generación del alumno.',
    ('EgresoAlumno', 'promedio_final'): 'Promedio final.',
    ('EgresoAlumno', 'titulo_tesis'): 'Título de la tesis.',
    ('EgresoAlumno', 'excepcion_motivo'): 'Motivo cuando el egreso se registra por excepción.',
    ('Materia', 'categoria'): 'Categoría curricular.',
    ('Materia', 'lgacs'): 'Líneas de generación y aplicación del conocimiento (lista JSON).',
    ('Materia', 'creditos'): 'Créditos oficiales de la materia.',
    ('Materia', 'profesor'): 'Profesor por defecto.',
    ('ConfiguracionPrograma', 'grado'): 'Grado académico.',
    ('ConfiguracionPrograma', 'periodicidad'): 'Periodicidad de los ciclos.',
    ('ConfiguracionPrograma', 'duracion_anios'): 'Duración en años (2 maestría, 4 doctorado).',
    ('ConfiguracionPrograma', 'periodos_requeridos'): 'Periodos requeridos para iniciar tesis.',
    ('ConfiguracionPrograma', 'creditos_requeridos'): 'Créditos requeridos.',
    ('PlanEstudioMateria', 'configuracion'): 'Programa al que pertenece el plan.',
    ('PlanEstudioMateria', 'periodo_sugerido'): 'Periodo sugerido para cursar la materia.',
    ('PlanEstudioMateria', 'obligatoria'): 'Indica si la materia es obligatoria.',
    ('SolicitudDireccionTesis', 'director_sugerido'): 'Director propuesto por el alumno.',
    ('SolicitudDireccionTesis', 'director_asignado'): 'Director asignado.',
    ('SolicitudDireccionTesis', 'alumno_acepto_director'): 'Indica si el alumno confirmó al director.',
    ('SolicitudDireccionTesis', 'director_acepto'): 'Indica si el director aceptó la dirección.',
    ('PeriodoInscripcion', 'nombre'): 'Nombre único del periodo.',
    ('PeriodoInscripcion', 'apertura'): 'Inicio de la ventana de inscripción.',
    ('PeriodoInscripcion', 'cierre'): 'Fin de la ventana de inscripción.',
    ('PeriodoInscripcion', 'activo'): 'Indica si es el periodo vigente.',
    ('AuditoriaSistema', 'actor'): 'Usuario que realizó la acción.',
    ('AuditoriaSistema', 'accion'): 'Acción realizada.',
    ('AuditoriaSistema', 'modelo'): 'Entidad afectada.',
    ('AuditoriaSistema', 'objeto_id'): 'Identificador del registro afectado.',
    ('AuditoriaSistema', 'datos_anteriores'): 'Datos previos en formato JSON.',
    ('AuditoriaSistema', 'datos_nuevos'): 'Datos nuevos en formato JSON.',
    ('AuditoriaSistema', 'ip'): 'Dirección IP de origen.',
    ('ConfiguracionSistema', 'descripcion'): 'Descripción del parámetro.',
    ('Inscripcion', 'validacion_servicios'): 'Validación de Servicios Escolares.',
    ('Inscripcion', 'parcial_1'): 'Calificación del primer parcial.',
    ('Inscripcion', 'parcial_2'): 'Calificación del segundo parcial.',
    ('Inscripcion', 'parcial_3'): 'Calificación del tercer parcial.',
    ('Inscripcion', 'extemporanea'): 'Indica si la inscripción fue extemporánea.',
    ('Inscripcion', 'motivo_extemporanea'): 'Motivo de la inscripción extemporánea.',
    ('SolicitudInscripcionExtemporanea', 'solicitante'): 'Usuario que envió la solicitud.',
    ('SolicitudInscripcionExtemporanea', 'comentario_revision'): 'Comentario de la revisión.',
    ('SolicitudInscripcionExtemporaneaMateria', 'solicitud'): 'Solicitud extemporánea a la que pertenece.',
    ('SolicitudInscripcionExtemporaneaMateria', 'carga_materia'): 'Grupo de la carga académica solicitado.',
    ('SolicitudAcademica', 'respuesta_revision'): 'Respuesta del área que resolvió.',
    ('ExamenEnLinea', 'intentos'): 'Intentos realizados.',
    ('ExamenEnLinea', 'max_intentos'): 'Intentos permitidos.',
    ('PreguntaExamen', 'examen'): 'Examen al que pertenece la pregunta.',
    ('PreguntaExamen', 'texto'): 'Enunciado de la pregunta.',
    ('PreguntaExamen', 'opciones'): 'Opciones de respuesta (lista JSON).',
    ('PreguntaExamen', 'respuesta_correcta'): 'Opción correcta.',
    ('RespuestaExamen', 'examen'): 'Examen respondido.',
    ('RespuestaExamen', 'pregunta'): 'Pregunta respondida.',
    ('RespuestaExamen', 'respuesta'): 'Opción elegida.',
    ('RespuestaExamen', 'es_correcta'): 'Indica si la respuesta es correcta.',
    ('EntrevistaVirtual', 'proposito'): 'Propósito de la entrevista.',
    ('EntrevistaVirtual', 'jitsi_room_id'): 'Identificador único de la sala de videoconferencia.',
    ('EntrevistaVirtual', 'jitsi_room_link'): 'Enlace a la sala de videoconferencia.',
    ('EntrevistaVirtual', 'recording_link'): 'Enlace a la grabación.',
    ('EntrevistaVirtual', 'notas_docente'): 'Notas privadas del docente (no visibles al aspirante).',
    ('EvaluacionColegio', 'dictamen'): 'Dictamen del Colegio de Profesores.',
    ('EvaluacionColegio', 'fecha_evaluacion'): 'Fecha de la evaluación.',
}

TABLAS_FRAMEWORK = [
    ('preregistro_aspirante_groups', 'Relación muchos a muchos entre usuarios y grupos de permisos (PermissionsMixin).'),
    ('preregistro_aspirante_user_permissions', 'Relación muchos a muchos entre usuarios y permisos individuales (PermissionsMixin).'),
    ('auth_group', 'Grupos de permisos de Django.'),
    ('auth_permission', 'Permisos por modelo generados por Django.'),
    ('auth_group_permissions', 'Relación entre grupos y permisos.'),
    ('django_content_type', 'Registro de los modelos instalados, usado por permisos y auditoría del administrador.'),
    ('django_admin_log', 'Bitácora de acciones realizadas desde el sitio de administración de Django.'),
    ('django_session', 'Sesiones del sitio de administración de Django.'),
    ('django_migrations', 'Control de las migraciones aplicadas al esquema.'),
]

# ---------------------------------------------------------------------------
# Utilidades de datos
# ---------------------------------------------------------------------------

def tabla_corta(modelo):
    return MODELOS[modelo]['tabla'].replace(PREFIJO, '')


def tipo_bd(campo):
    tipo = campo['tipo_bd'] or ''
    return tipo.replace('timestamp with time zone', 'timestamptz').replace('numeric(', 'numeric(').replace(', ', ',')


def tipo_django(campo):
    tipo = campo['tipo']
    if 'relacion' in campo:
        return campo['relacion']['modelo']
    if campo['max_length'] and tipo in ('CharField', 'EmailField', 'URLField'):
        return f'{tipo}({campo["max_length"]})'
    if tipo == 'DecimalField':
        return f'Decimal({campo["max_digits"]},{campo["decimal_places"]})'
    return tipo.replace('Field', '') if tipo not in ('ForeignKey', 'OneToOneField') else tipo


def relaciones():
    salida = []
    for modelo in MODELOS.values():
        for campo in modelo['campos']:
            if 'relacion' in campo:
                r = campo['relacion']
                salida.append({
                    'hijo': modelo['modelo'], 'campo': campo['nombre'], 'columna': campo['columna'],
                    'padre': r['modelo'], 'uno_a_uno': r['tipo'] == 'OneToOne', 'on_delete': r['on_delete'],
                    'nulo': campo['nulo'], 'related_name': r['related_name'],
                })
    return salida


RELACIONES = relaciones()


def llave(campo):
    marcas = []
    if campo['pk']:
        marcas.append('PK')
    if 'relacion' in campo:
        marcas.append('FK')
    if campo['unico'] and not campo['pk']:
        marcas.append('UQ')
    return marcas


def predeterminado(campo):
    if campo['auto_now_add']:
        return 'now() al crear'
    if campo['auto_now']:
        return 'now() al guardar'
    if campo['pk']:
        return 'identity'
    valor = campo['default']
    if valor is None:
        return '—'
    if valor == 'dict()':
        return '{}'
    if valor == 'list()':
        return '[]'
    if isinstance(valor, bool):
        return 'true' if valor else 'false'
    if valor == '':
        return "'' (vacío)"
    return str(valor)


def humanizar(nombre):
    texto = nombre.replace('_', ' ').strip()
    return texto[:1].upper() + texto[1:] + '.'


def describir(modelo, campo):
    nombre = campo['nombre']
    especifica = DESC_CAMPO.get((modelo, nombre))
    texto = especifica or DESC_COMUN.get(nombre) or humanizar(nombre)
    if campo['ayuda'] and not especifica:
        texto += f' {campo["ayuda"].rstrip(".")}.'
    if 'relacion' in campo:
        r = campo['relacion']
        texto += f' Referencia a <b>{MODELOS[r["modelo"]]["tabla"]}</b>(id), ON DELETE {r["on_delete"]}.'
    if campo['choices'] and not (modelo == 'Aspirante' and nombre == 'rol'):
        texto += ' Valores: ' + ', '.join(campo['choices']) + '.'
    return texto


# ---------------------------------------------------------------------------
# Motor de diagramas por módulo (clases y entidad-relación)
# ---------------------------------------------------------------------------
COL_W = 168
GAP = 34
FILA = 9.2
CABECERA = 17
TAM = 6.6
ASPIRANTE_CLAVE = ['id', 'usuario', 'nombre', 'correo', 'curp', 'matricula', 'rol', 'programa', 'director_tesis']


def ajustar_fuente(texto, fuente, tam, ancho):
    while tam > 5 and stringWidth(texto, fuente, tam) > ancho:
        tam -= 0.2
    return tam


def filas_entidad(modelo, modo, estilo):
    campos = MODELOS[modelo]['campos']
    if modo == 'compacto':
        campos = [c for c in campos if c['nombre'] in ASPIRANTE_CLAVE]
    elif modo == 'referencia':
        campos = [c for c in campos if c['pk'] or c['unico'] or c['nombre'] in ('nombre', 'clave')][:3]
    filas = []
    for c in campos:
        if estilo == 'er':
            filas.append({'campo': c['nombre'], 'marca': '/'.join(llave(c)), 'texto': c['columna'], 'tipo': tipo_bd(c)})
        else:
            filas.append({'campo': c['nombre'], 'marca': '+', 'texto': c['nombre'], 'tipo': tipo_django(c)})
    total = len(MODELOS[modelo]['campos'])
    if modo in ('compacto', 'referencia') and total > len(filas):
        filas.append({'campo': None, 'marca': '', 'texto': f'… {total - len(filas)} atributos más', 'tipo': '', 'nota': True})
    return filas


def metodos_clase(modelo):
    salida = []
    for m in MODELOS[modelo]['metodos']:
        if m['tipo'] == 'metodo':
            retorno = ': str' if m['nombre'] == '__str__' else ''
            salida.append(f'+ {m["nombre"]}{m.get("firma", "()")}{retorno}')
        else:
            salida.append(f'+ «{m["tipo"].replace("cached_", "")}» {m["nombre"]}')
    if modelo == 'Aspirante':
        salida += ['+ set_password(raw)', '+ check_password(raw): bool']
    return salida


class Caja:
    def __init__(self, modelo, x, y_top, ancho, filas, columnas, estilo, color, modo, metodos=()):
        self.modelo, self.x, self.y_top, self.ancho = modelo, x, y_top, ancho
        self.filas, self.columnas, self.estilo, self.color, self.modo = filas, columnas, estilo, color, modo
        self.metodos = list(metodos)
        self.filas_por_col = math.ceil(len(filas) / columnas)
        self.alto_attr = self.filas_por_col * FILA + 4
        self.alto_met = (len(self.metodos) * FILA + 4) if estilo == 'clase' and self.metodos else (6 if estilo == 'clase' else 0)
        cab = CABECERA + (7 if estilo == 'clase' else 0)
        self.cab = cab
        self.alto = cab + self.alto_attr + self.alto_met
        self.y_fila = {}

    @property
    def derecha(self):
        return self.x + self.ancho

    @property
    def base(self):
        return self.y_top - self.alto

    def y_campo(self, campo):
        return self.y_fila.get(campo, self.y_top - self.cab - FILA * 0.6)

    def dibujar(self, d):
        color = colors.HexColor(self.color)
        punteada = self.modo == 'referencia'
        d.add(Rect(self.x, self.base, self.ancho, self.alto, fillColor=colors.white, strokeColor=color,
                   strokeWidth=1, strokeDashArray=[3, 2] if punteada else None))
        relleno = colors.HexColor('#FFFFFF') if punteada else color
        d.add(Rect(self.x, self.y_top - self.cab, self.ancho, self.cab, fillColor=relleno, strokeColor=color, strokeWidth=1,
                   strokeDashArray=[3, 2] if punteada else None))
        texto_cab = colors.HexColor(self.color) if punteada else colors.white
        if self.estilo == 'clase':
            d.add(String(self.x + self.ancho / 2, self.y_top - 8, '«Model»' if self.modo != 'referencia' else '«Model» (referencia)',
                         fontName='Arial-Italic', fontSize=5.8, fillColor=texto_cab, textAnchor='middle'))
            nombre = self.modelo
            tam = ajustar_fuente(nombre, 'Arial-Bold', 8, self.ancho - 8)
            d.add(String(self.x + self.ancho / 2, self.y_top - self.cab + 5, nombre, fontName='Arial-Bold', fontSize=tam,
                         fillColor=texto_cab, textAnchor='middle'))
        else:
            nombre = tabla_corta(self.modelo)
            tam = ajustar_fuente(nombre, 'Arial-Bold', 7.6, self.ancho - 8)
            d.add(String(self.x + self.ancho / 2, self.y_top - self.cab + 5.5, nombre, fontName='Arial-Bold', fontSize=tam,
                         fillColor=texto_cab, textAnchor='middle'))
        ancho_col = self.ancho / self.columnas
        for i, fila in enumerate(self.filas):
            col, pos = divmod(i, self.filas_por_col)
            x0 = self.x + col * ancho_col
            y = self.y_top - self.cab - 2 - (pos + 1) * FILA + 2.4
            if fila.get('campo'):
                self.y_fila[fila['campo']] = y + 2.2
            if pos % 2 == 1:
                d.add(Rect(x0 + 0.5, y - 2.4, ancho_col - 1, FILA, fillColor=colors.HexColor('#F5F7F9'), strokeColor=None))
            if fila.get('nota'):
                d.add(String(x0 + 5, y, fila['texto'], fontName='Arial-Italic', fontSize=TAM - 0.4, fillColor=GRIS))
                continue
            marca = fila['marca']
            color_marca = colors.HexColor('#B5642F') if 'PK' in marca else colors.HexColor('#2F6DB5') if 'FK' in marca else GRIS
            d.add(String(x0 + 3, y, marca, fontName='Arial-Bold', fontSize=TAM - 1.2, fillColor=color_marca))
            sangria = 22 if self.estilo == 'er' else 9
            tipo_tam = TAM - 0.6
            ancho_tipo = stringWidth(fila['tipo'], 'Arial', tipo_tam)
            disponible = ancho_col - sangria - ancho_tipo - 8
            texto = fila['texto'] if self.estilo == 'er' else f'{fila["texto"]}:'
            tam = ajustar_fuente(texto, 'Arial', TAM, disponible)
            negrita = 'PK' in marca
            d.add(String(x0 + sangria, y, texto, fontName='Arial-Bold' if negrita else 'Arial', fontSize=tam))
            d.add(String(x0 + ancho_col - 4, y, fila['tipo'], fontName='Arial', fontSize=tipo_tam, fillColor=GRIS, textAnchor='end'))
            if col > 0 and pos == 0:
                d.add(Line(x0, self.y_top - self.cab, x0, self.y_top - self.cab - self.alto_attr, strokeColor=colors.HexColor('#DDE3E8'), strokeWidth=0.5))
        if self.estilo == 'clase':
            y_sep = self.y_top - self.cab - self.alto_attr
            d.add(Line(self.x, y_sep, self.derecha, y_sep, strokeColor=colors.HexColor(self.color), strokeWidth=0.8))
            for i, metodo in enumerate(self.metodos):
                d.add(String(self.x + 5, y_sep - (i + 1) * FILA + 2.2, metodo, fontName='Arial', fontSize=TAM - 0.3,
                             fillColor=colors.HexColor('#1F2A33')))


def simbolo_er(d, x, y, dx, dy, tipo):
    px, py = -dy, dx

    def linea(x1, y1, x2, y2):
        d.add(Line(x1, y1, x2, y2, strokeColor=LINEA, strokeWidth=0.8))

    def barra(t):
        cx, cy = x + dx * t, y + dy * t
        linea(cx + px * 4, cy + py * 4, cx - px * 4, cy - py * 4)

    def circulo(t):
        d.add(Circle(x + dx * t, y + dy * t, 2.6, fillColor=colors.white, strokeColor=LINEA, strokeWidth=0.8))

    if tipo == 'muchos':
        punta = (x + dx * 9, y + dy * 9)
        for k in (-1, 0, 1):
            linea(x + px * 4.5 * k, y + py * 4.5 * k, *punta)
        circulo(13)
    elif tipo == 'uno':
        barra(4)
        barra(8)
    elif tipo == 'uno_opcional':
        barra(4)
        circulo(10)


def simbolo_clase(d, x, y, dx, dy, multiplicidad, composicion):
    px, py = -dy, dx
    if composicion:
        d.add(Polygon([x, y, x + dx * 6 + px * 3.5, y + dy * 6 + py * 3.5, x + dx * 12, y + dy * 12,
                       x + dx * 6 - px * 3.5, y + dy * 6 - py * 3.5], fillColor=LINEA, strokeColor=LINEA, strokeWidth=0.6))
    t = 17 if composicion else 8
    lado = 1 if dy == 0 else 1
    d.add(String(x + dx * t + px * 6 * lado, y + dy * t + py * 6 * lado - 2, multiplicidad, fontName='Arial', fontSize=6,
                 fillColor=colors.HexColor('#1F2A33'), textAnchor='middle'))


class Diagrama:
    def __init__(self, modulo, estilo):
        self.modulo, self.estilo = modulo, estilo
        self.columnas = DISTRIBUCION[modulo['clave']]
        self.ancho = len(self.columnas) * COL_W + (len(self.columnas) + 1) * GAP
        self.uso_gap = defaultdict(int)
        referencias = set(modulo.get('referencias', []))
        completo = modulo['clave'] == 'usuarios'
        self.barra = Caja('Aspirante', 8, 0, self.ancho - 16 - (30 if completo else 0),
                          filas_entidad('Aspirante', 'completo' if completo else 'compacto', estilo),
                          5 if completo else 4, estilo, MODULOS[0]['color'], 'completo' if completo else 'compacto',
                          metodos_clase('Aspirante') if (estilo == 'clase' and completo) else ['+ __str__(): str', '…'] if estilo == 'clase' else [])
        self.cajas = {}
        alturas = []
        for i, col in enumerate(self.columnas):
            total = 0
            for nombre in col:
                modo = 'referencia' if nombre in referencias else 'completo'
                caja = Caja(nombre, GAP + i * (COL_W + GAP), 0, COL_W, filas_entidad(nombre, modo, estilo), 1, estilo,
                            modulo['color'] if modo != 'referencia' else '#7D8A96', modo,
                            metodos_clase(nombre) if estilo == 'clase' else [])
                caja.col = i
                self.cajas[nombre] = caja
                total += caja.alto + 30
            alturas.append(total)
        extra_superior = 70 if (estilo == 'clase' and completo) else 26
        self.alto = extra_superior + self.barra.alto + 48 + max(alturas) + 6
        self.barra.y_top = self.alto - extra_superior
        for i, col in enumerate(self.columnas):
            y = self.barra.base - 48
            for nombre in col:
                self.cajas[nombre].y_top = y
                y -= self.cajas[nombre].alto + 30
        self.d = Drawing(self.ancho, self.alto)

    def gap_x(self, indice):
        k = self.uso_gap[indice]
        self.uso_gap[indice] += 1
        centro = indice * (COL_W + GAP) + GAP / 2
        return centro + ((k + 1) // 2) * 5 * (1 if k % 2 else -1)

    def ruta(self, puntos):
        plano = [v for p in puntos for v in p]
        self.d.add(PolyLine(plano, strokeColor=LINEA, strokeWidth=0.8))

    def extremos(self, rel, hijo_xy, hijo_dir, padre_xy, padre_dir):
        hx, hy = hijo_xy
        px_, py_ = padre_xy
        if self.estilo == 'er':
            simbolo_er(self.d, hx, hy, *hijo_dir, 'uno_opcional' if rel['uno_a_uno'] else 'muchos')
            simbolo_er(self.d, px_, py_, *padre_dir, 'uno_opcional' if rel['nulo'] else 'uno')
        else:
            simbolo_clase(self.d, hx, hy, *hijo_dir, '0..1' if rel['uno_a_uno'] else '0..*', False)
            simbolo_clase(self.d, px_, py_, *padre_dir, '0..1' if rel['nulo'] else '1', rel['on_delete'] == 'CASCADE')

    def dibujar(self):
        d = self.d
        for caja in [self.barra, *self.cajas.values()]:
            caja.dibujar(d)
        presentes = set(self.cajas)
        for rel in RELACIONES:
            hijo, padre = rel['hijo'], rel['padre']
            if hijo not in presentes or self.cajas[hijo].modo == 'referencia':
                continue
            caja = self.cajas[hijo]
            y = caja.y_campo(rel['campo'])
            if padre == 'Aspirante':
                gx = self.gap_x(caja.col)
                self.ruta([(caja.x, y), (gx, y), (gx, self.barra.base)])
                self.extremos(rel, (caja.x, y), (-1, 0), (gx, self.barra.base), (0, -1))
            elif padre in presentes:
                destino = self.cajas[padre]
                yp = destino.y_campo('id')
                if destino.col == caja.col:
                    gx = self.gap_x(caja.col + 1)
                    self.ruta([(caja.derecha, y), (gx, y), (gx, yp), (destino.derecha, yp)])
                    self.extremos(rel, (caja.derecha, y), (1, 0), (destino.derecha, yp), (1, 0))
                elif destino.col > caja.col:
                    gx = self.gap_x(caja.col + 1)
                    self.ruta([(caja.derecha, y), (gx, y), (gx, yp), (destino.x, yp)])
                    self.extremos(rel, (caja.derecha, y), (1, 0), (destino.x, yp), (-1, 0))
                else:
                    gx = self.gap_x(caja.col)
                    self.ruta([(caja.x, y), (gx, y), (gx, yp), (destino.derecha, yp)])
                    self.extremos(rel, (caja.x, y), (-1, 0), (destino.derecha, yp), (1, 0))
        if self.modulo['clave'] == 'usuarios':
            self.autorreferencia()
            if self.estilo == 'clase':
                self.herencia()
        return d

    def autorreferencia(self):
        b = self.barra
        rel = next(r for r in RELACIONES if r['hijo'] == 'Aspirante' and r['campo'] == 'director_tesis')
        y1, y2 = b.y_top - b.alto * 0.35, b.y_top - b.alto * 0.7
        xr = b.derecha + 18
        self.ruta([(b.derecha, y1), (xr, y1), (xr, y2), (b.derecha, y2)])
        self.extremos(rel, (b.derecha, y1), (1, 0), (b.derecha, y2), (1, 0))
        self.d.add(String(xr + 3, (y1 + y2) / 2, 'director_tesis', fontName='Arial-Italic', fontSize=6, fillColor=GRIS))

    def herencia(self):
        d, b = self.d, self.barra
        y_padres = b.y_top + 56
        cajas = [('AbstractBaseUser', '«django.contrib.auth»', b.x + 40), ('PermissionsMixin', '«django.contrib.auth»', b.x + 230)]
        for nombre, estereotipo, x in cajas:
            d.add(Rect(x, y_padres - 26, 150, 26, fillColor=colors.HexColor('#F3F5F7'), strokeColor=GRIS, strokeWidth=0.8))
            d.add(String(x + 75, y_padres - 9, estereotipo, fontName='Arial-Italic', fontSize=5.8, fillColor=GRIS, textAnchor='middle'))
            d.add(String(x + 75, y_padres - 20, nombre, fontName='Arial-Bold', fontSize=7.5, textAnchor='middle'))
            cx = x + 75
            d.add(Line(cx, y_padres - 26, cx, b.y_top + 8, strokeColor=LINEA, strokeWidth=0.8))
            d.add(Polygon([cx, y_padres - 26, cx - 5, y_padres - 35, cx + 5, y_padres - 35], fillColor=colors.white, strokeColor=LINEA, strokeWidth=0.8))
            d.add(Line(cx, y_padres - 35, cx, b.y_top, strokeColor=LINEA, strokeWidth=0.8))
        x = b.x + 440
        d.add(Rect(x, y_padres - 26, 190, 26, fillColor=colors.HexColor('#F3F5F7'), strokeColor=GRIS, strokeWidth=0.8))
        d.add(String(x + 95, y_padres - 9, '«manager» AspiranteManager', fontName='Arial-Bold', fontSize=7, textAnchor='middle'))
        d.add(String(x + 95, y_padres - 20, '+ create_user()  + create_superuser()', fontName='Arial', fontSize=6, textAnchor='middle'))
        d.add(Line(x + 95, y_padres - 26, x + 95, b.y_top, strokeColor=LINEA, strokeWidth=0.8, strokeDashArray=[3, 2]))
        d.add(String(x + 99, b.y_top + 12, 'objects', fontName='Arial-Italic', fontSize=6, fillColor=GRIS))


# ---------------------------------------------------------------------------
# Diagramas generales
# ---------------------------------------------------------------------------
COLUMNAS_GENERAL = {
    'izq_ext': ['PreguntaExamen'],
    'izq': ['DocumentoAspirante', 'SeguimientoSolicitud', 'EvaluacionColegio', 'ExpedienteDigital', 'FirmaElectronica',
            'HistorialPersona', 'AuditoriaSistema', 'ConfiguracionSistema', 'ExamenEnLinea', 'RespuestaExamen', 'EntrevistaVirtual'],
    'der': ['SolicitudDireccionTesis', 'EgresoAlumno', 'JuradoProyecto', 'ProyectoTesis', 'SolicitudAcademica', 'Inscripcion',
            'SolicitudInscripcionExtemporanea', 'CargaAcademica', 'CargaAcademicaMateria'],
    'der_ext': ['DefensaTesis', 'RevisionAntiplagio', 'PeriodoInscripcion', 'SolicitudInscripcionExtemporaneaMateria', 'Materia',
                'PlanEstudioMateria', 'ConfiguracionPrograma'],
}


def color_modulo(modelo):
    for m in MODULOS:
        if modelo in m['modelos']:
            return m['color']
    return '#7D8A96'


def borde_rect(cx, cy, w, h, tx, ty):
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    escala = min((w / 2) / abs(dx) if dx else 1e9, (h / 2) / abs(dy) if dy else 1e9)
    return cx + dx * escala, cy + dy * escala


def diagrama_general(estilo):
    ancho, alto = 940, 460
    d = Drawing(ancho, alto)
    xs = {'izq_ext': 70, 'izq': 270, 'der': 640, 'der_ext': 850}
    pos = {}
    for clave in ('izq', 'der'):
        lista = COLUMNAS_GENERAL[clave]
        paso = (alto - 30) / len(lista)
        for i, nombre in enumerate(lista):
            pos[nombre] = [xs[clave], alto - 20 - paso * (i + 0.5)]
    pos['Aspirante'] = [455, alto / 2]
    for clave in ('izq_ext', 'der_ext'):
        deseados = []
        for nombre in COLUMNAS_GENERAL[clave]:
            ys = [pos[r['padre']][1] for r in RELACIONES if r['hijo'] == nombre and r['padre'] in pos]
            ys += [pos[r['hijo']][1] for r in RELACIONES if r['padre'] == nombre and r['hijo'] in pos]
            deseados.append([nombre, sum(ys) / len(ys) if ys else alto / 2])
        deseados.sort(key=lambda e: -e[1])
        previo = alto - 10
        for nombre, y in deseados:
            y = min(y, previo - 34)
            pos[nombre] = [xs[clave], y]
            previo = y
        minimo = min(pos[n][1] for n, _ in deseados)
        if minimo < 20:
            for n, _ in deseados:
                pos[n][1] += 20 - minimo

    medidas = {}
    for nombre in pos:
        texto = nombre if estilo == 'clase' else tabla_corta(nombre)
        w = stringWidth(texto, 'Arial-Bold', 7) + 14
        h = 20
        if nombre == 'Aspirante':
            w, h = max(w, 110), 40
        medidas[nombre] = (w, h, texto)

    vistos = set()
    columna_de = {n: c for c, lista in COLUMNAS_GENERAL.items() for n in lista}
    for rel in RELACIONES:
        par = (rel['hijo'], rel['padre'])
        if rel['hijo'] == rel['padre'] or par in vistos:
            continue
        vistos.add(par)
        (hx, hy), (px_, py_) = pos[rel['hijo']], pos[rel['padre']]
        hw, hh, _ = medidas[rel['hijo']]
        pw, ph, _ = medidas[rel['padre']]
        misma = columna_de.get(rel['hijo']) and columna_de.get(rel['hijo']) == columna_de.get(rel['padre'])
        if misma:
            lado = -1 if hx < 455 else 1
            ax = hx + lado * hw / 2
            bx = px_ + lado * pw / 2
            gx = (min(ax, bx) if lado < 0 else max(ax, bx)) + lado * 12
            d.add(PolyLine([ax, hy, gx, hy, gx, py_, bx, py_], strokeColor=LINEA, strokeWidth=0.7))
            a, b, da, db = (ax, hy), (bx, py_), (lado, 0), (lado, 0)
        else:
            a = borde_rect(hx, hy, hw, hh, px_, py_)
            b = borde_rect(px_, py_, pw, ph, hx, hy)
            d.add(Line(*a, *b, strokeColor=LINEA, strokeWidth=0.7))
            largo = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
            da = ((b[0] - a[0]) / largo, (b[1] - a[1]) / largo)
            db = (-da[0], -da[1])
        if estilo == 'er':
            simbolo_er(d, *a, *da, 'uno_opcional' if rel['uno_a_uno'] else 'muchos')
            simbolo_er(d, *b, *db, 'uno_opcional' if rel['nulo'] else 'uno')
        elif rel['on_delete'] == 'CASCADE':
            px2, py2 = -db[1], db[0]
            x, y = b
            d.add(Polygon([x, y, x + db[0] * 6 + px2 * 3.5, y + db[1] * 6 + py2 * 3.5, x + db[0] * 12, y + db[1] * 12,
                           x + db[0] * 6 - px2 * 3.5, y + db[1] * 6 - py2 * 3.5], fillColor=LINEA, strokeColor=LINEA, strokeWidth=0.5))

    for nombre, (x, y) in pos.items():
        w, h, texto = medidas[nombre]
        color = colors.HexColor(color_modulo(nombre))
        d.add(Rect(x - w / 2, y - h / 2, w, h, fillColor=colors.white, strokeColor=color, strokeWidth=1.1))
        if nombre == 'Aspirante':
            d.add(Rect(x - w / 2, y + h / 2 - 16, w, 16, fillColor=color, strokeColor=color))
            d.add(String(x, y + h / 2 - 11.5, texto, fontName='Arial-Bold', fontSize=8, fillColor=colors.white, textAnchor='middle'))
            d.add(String(x, y - h / 2 + 8, 'usuarios del sistema', fontName='Arial-Italic', fontSize=6.5, fillColor=GRIS, textAnchor='middle'))
        else:
            d.add(Rect(x - w / 2, y - h / 2, 4, h, fillColor=color, strokeColor=None))
            d.add(String(x + 2, y - 2.5, texto, fontName='Arial-Bold', fontSize=7, textAnchor='middle'))
    leyenda_modulos(d, 8, 10)
    return d


def leyenda_modulos(d, x, y):
    for m in MODULOS:
        d.add(Rect(x, y, 9, 9, fillColor=colors.HexColor(m['color']), strokeColor=None))
        d.add(String(x + 12, y + 1.5, m['nombre'], fontName='Arial', fontSize=6.5))
        x += stringWidth(m['nombre'], 'Arial', 6.5) + 26


def leyenda_er():
    d = Drawing(ANCHO_UTIL, 92)
    ejemplos = [('uno', 'Exactamente uno (1)'), ('uno_opcional', 'Cero o uno (0..1)'), ('muchos', 'Cero o muchos (0..*)')]
    for i, (tipo, texto) in enumerate(ejemplos):
        y = 76 - i * 26
        d.add(Line(20, y, 80, y, strokeColor=LINEA, strokeWidth=0.8))
        simbolo_er(d, 80, y, -1, 0, tipo)
        d.add(Rect(80, y - 8, 14, 16, fillColor=colors.HexColor('#E6F4F1'), strokeColor=VERDE_OSCURO, strokeWidth=0.8))
        d.add(String(104, y - 3, texto, fontName='Arial', fontSize=8.5))
    marcas = [('PK', '#B5642F', 'Llave primaria'), ('FK', '#2F6DB5', 'Llave foránea'), ('UQ', '#4A5560', 'Valor único')]
    for i, (marca, color, texto) in enumerate(marcas):
        y = 73 - i * 26
        d.add(String(270, y, marca, fontName='Arial-Bold', fontSize=8, fillColor=colors.HexColor(color)))
        d.add(String(292, y, texto, fontName='Arial', fontSize=8.5))
    d.add(Rect(350, 58, 40, 22, fillColor=colors.white, strokeColor=GRIS, strokeWidth=0.9, strokeDashArray=[3, 2]))
    d.add(String(396, 70, 'Entidad de referencia', fontName='Arial', fontSize=8.5))
    d.add(String(396, 59, '(se detalla en otro diagrama)', fontName='Arial', fontSize=7.5, fillColor=GRIS))
    return d


def leyenda_clases():
    d = Drawing(ANCHO_UTIL, 70)
    d.add(Line(20, 56, 110, 56, strokeColor=LINEA, strokeWidth=0.8))
    simbolo_clase(d, 110, 56, -1, 0, '1', True)
    d.add(String(122, 53, 'Composición (ON DELETE CASCADE): las partes se eliminan con el todo', fontName='Arial', fontSize=8.5))
    d.add(Line(20, 34, 110, 34, strokeColor=LINEA, strokeWidth=0.8))
    simbolo_clase(d, 110, 34, -1, 0, '0..1', False)
    d.add(String(122, 31, 'Asociación (PROTECT / SET_NULL) con su multiplicidad en cada extremo', fontName='Arial', fontSize=8.5))
    d.add(Line(35, 4, 35, 18, strokeColor=LINEA, strokeWidth=0.8))
    d.add(Polygon([35, 20, 30, 11, 40, 11], fillColor=colors.white, strokeColor=LINEA, strokeWidth=0.8))
    d.add(String(122, 8, 'Herencia (generalización) de clases de Django', fontName='Arial', fontSize=8.5))
    return d


# ---------------------------------------------------------------------------
# Secciones del documento
# ---------------------------------------------------------------------------
pequena = ParagraphStyle('pequena', parent=celda, fontSize=7.6, leading=9.6)


def introduccion():
    total_campos = sum(len(m['campos']) for m in MODELOS.values())
    h = [titulo('1. Introducción', h1, 0)]
    h.append(titulo('1.1 Propósito', h2, 1))
    h.append(Paragraph(
        'Este documento describe el diseño de la base de datos de <b>SINAC NEXT</b>, el sistema de información académica del '
        'Centro de Investigación y de Estudios Avanzados (Cinvestav). Presenta el modelo de clases de la capa de persistencia, el '
        'modelo entidad-relación del esquema físico y el diccionario de datos, con el fin de servir como referencia para el '
        'desarrollo, el mantenimiento, la administración y la auditoría de la información institucional.', cuerpo))
    h.append(titulo('1.2 Alcance', h2, 1))
    h.append(Paragraph(
        f'Se documentan las <b>{len(MODELOS)} tablas</b> del dominio del sistema, con sus <b>{total_campos} columnas</b>, '
        f'<b>{len(RELACIONES)} llaves foráneas</b> y las restricciones de integridad, agrupadas en seis módulos funcionales. Se '
        'incluyen también, de forma resumida, las tablas que Django crea para autenticación, permisos y control de migraciones.', cuerpo))
    h.append(titulo('1.3 Tecnología y gestión del esquema', h2, 1))
    h.append(Paragraph(
        'La base de datos se implementa en <b>PostgreSQL 15</b>, desplegado en un contenedor Docker. El esquema se define mediante '
        'los modelos del ORM de <b>Django 5</b> en la aplicación <i>preregistro</i> y se versiona con migraciones (52 migraciones a la '
        'fecha, la más reciente <i>0052_historialpersona_categoria_detalle</i>). Cada modelo de Django corresponde a una clase del '
        'diagrama de clases y a una tabla del diagrama entidad-relación.', cuerpo))
    h.append(Paragraph(
        'El motor de procesos Camunda, que ejecuta los flujos modelados con el lenguaje iconográfico LIDA, mantiene su propia base '
        'de datos; SINAC NEXT solo guarda las referencias a sus instancias (columnas <i>business_key</i> y <i>camunda_instance_id</i>).', cuerpo))
    h.append(titulo('1.4 Convenciones', h2, 1))
    for texto in [
        'Las tablas usan el prefijo <b>preregistro_</b> seguido del nombre del modelo en minúsculas (por ejemplo, <i>preregistro_inscripcion</i>). En los diagramas entidad-relación se omite el prefijo para mayor legibilidad.',
        'Toda tabla tiene una llave primaria <b>id</b> de tipo <i>bigint</i> autoincremental (identity).',
        'Las llaves foráneas se nombran <b>&lt;relación&gt;_id</b> y referencian siempre la columna <i>id</i> de la tabla padre.',
        'Las columnas <i>created_at</i> y <i>updated_at</i> registran automáticamente la creación y la última modificación.',
        'El tipo <i>timestamptz</i> abrevia <i>timestamp with time zone</i>; las fechas se almacenan en UTC.',
        'Los campos de archivo guardan la ruta relativa del archivo; el contenido se resguarda en el almacenamiento de medios y se sirve mediante URL firmadas y caducables.',
    ]:
        h.append(Paragraph(texto, vineta, bulletText='•'))
    h.append(titulo('1.5 Notación del diagrama entidad-relación', h2, 1))
    h.append(Paragraph(
        'Los diagramas entidad-relación usan la notación de <b>pata de gallo</b> (crow\'s foot). Cada entidad muestra el nombre de la '
        'tabla, sus columnas y su tipo en PostgreSQL. Las líneas parten de la columna de llave foránea y llegan a la llave primaria '
        'de la tabla padre; los símbolos de los extremos indican la cardinalidad.', cuerpo))
    h.append(DiagramaAjustado(leyenda_er()))
    h.append(titulo('1.6 Notación del diagrama de clases', h2, 1))
    h.append(Paragraph(
        'Los diagramas de clases siguen UML. Cada clase muestra el estereotipo «Model», sus atributos con el tipo de campo de '
        'Django (los atributos de relación muestran la clase referenciada) y sus métodos. Las relaciones indican la multiplicidad '
        'en cada extremo; el rombo relleno representa composición, que corresponde a la eliminación en cascada.', cuerpo))
    h.append(DiagramaAjustado(leyenda_clases()))
    h.append(PageBreak())
    return h


def arquitectura():
    h = [titulo('2. Desarrollo', h1, 0), titulo('2.1 Organización de la base de datos', h2, 1)]
    h.append(Paragraph(
        'Las tablas se organizan en seis módulos funcionales. La tabla <i>preregistro_aspirante</i> es el eje del modelo: almacena '
        'a todas las personas del sistema y es referenciada por la mayoría de las tablas, tanto como titular del registro como '
        'responsable de una acción (revisión, registro o evaluación).', cuerpo))
    filas = [['Módulo', 'Descripción', 'Tablas']]
    for m in MODULOS:
        filas.append([f'<b>{m["nombre"]}</b>', m['descripcion'], '<br/>'.join(tabla_corta(n) for n in m['modelos'])])
    h.append(tabla(filas, [3.6 * cm, ANCHO_UTIL - 9.6 * cm, 6 * cm]))
    return h


def seccion_diagramas(numero, estilo, figura):
    nombre = 'Diagrama de clases' if estilo == 'clase' else 'Diagrama entidad-relación'
    h = [NextPageTemplate('horizontal'), PageBreak(), titulo(f'2.{numero} {nombre}', h2, 1)]
    if estilo == 'clase':
        h.append(Paragraph(
            'El diagrama de clases representa los modelos de Django que conforman la capa de persistencia. La vista general muestra '
            'todas las clases y sus asociaciones; después se detalla cada módulo con atributos, métodos y multiplicidades. La clase '
            '<b>Aspirante</b> hereda de <i>AbstractBaseUser</i> y <i>PermissionsMixin</i> y es el modelo de usuario del sistema.', cuerpo))
    else:
        h.append(Paragraph(
            'El diagrama entidad-relación representa el esquema físico en PostgreSQL. La vista general muestra todas las tablas y sus '
            'relaciones; después se detalla cada módulo con columnas, tipos y llaves. Cuando un módulo necesita una tabla de otro módulo, '
            'esta se dibuja con borde punteado como entidad de referencia.', cuerpo))
    h.append(titulo(f'2.{numero}.1 Vista general', h3, 2))
    h.append(DiagramaAjustado(diagrama_general(estilo), alto_maximo=380, reserva=28))
    h.append(Paragraph(f'Figura {figura}. {nombre} general de SINAC NEXT.', pie_fig))
    figura += 1
    for i, modulo in enumerate(MODULOS, 2):
        h.append(PageBreak())
        h.append(titulo(f'2.{numero}.{i} {modulo["nombre"]}', h3, 2))
        h.append(DiagramaAjustado(Diagrama(modulo, estilo).dibujar(), alto_maximo=380, reserva=28))
        h.append(Paragraph(f'Figura {figura}. {nombre}: {modulo["nombre"]}.', pie_fig))
        figura += 1
    h += [NextPageTemplate('normal')]
    return h, figura


def diccionario():
    h = [PageBreak(), titulo('2.4 Diccionario de datos', h2, 1)]
    h.append(Paragraph(
        'Para cada tabla se indica su propósito, sus columnas con el tipo de dato en PostgreSQL, si admiten nulos, su participación '
        'en llaves, el valor predeterminado y una descripción. Al final de cada tabla se listan sus restricciones adicionales.', cuerpo))
    indice = 1
    for modulo in MODULOS:
        for nombre in modulo['modelos']:
            m = MODELOS[nombre]
            bloque = [titulo(f'2.4.{indice} {m["tabla"]}', h3, 2),
                      Paragraph(f'<b>Clase:</b> {nombre} · <b>Módulo:</b> {modulo["nombre"]}', celda),
                      Spacer(1, 3), Paragraph(DESCRIPCION_TABLA[nombre], cuerpo)]
            filas = [['Columna', 'Tipo', 'Nulo', 'Llave', 'Predet.', 'Descripción']]
            for c in m['campos']:
                filas.append([f'<b>{c["columna"]}</b>' if c['pk'] else c['columna'], tipo_bd(c), 'Sí' if c['nulo'] else 'No',
                              ', '.join(llave(c)) or '—', predeterminado(c), describir(nombre, c)])
            t = tabla(filas, [3.3 * cm, 2.3 * cm, 1.15 * cm, 1.35 * cm, 1.9 * cm, ANCHO_UTIL - 10.0 * cm], estilo_celda=pequena)
            reglas = restricciones_tabla(m)
            h.append(KeepTogether(bloque + [t]) if len(filas) < 14 else bloque[0])
            if len(filas) >= 14:
                h += bloque[1:] + [t]
            if reglas:
                h.append(Spacer(1, 4))
                h.append(Paragraph('<b>Restricciones e índices</b>', celda))
                for regla in reglas:
                    h.append(Paragraph(regla, ParagraphStyle('r', parent=vineta, fontSize=9, leading=12), bulletText='•'))
            h.append(Spacer(1, 10))
            indice += 1
    return h


def restricciones_tabla(m):
    reglas = []
    unicos = [c['columna'] for c in m['campos'] if c['unico'] and not c['pk']]
    if unicos:
        reglas.append('UNIQUE en: ' + ', '.join(unicos) + '.')
    for grupo in m['unique_together']:
        columnas = [next(c['columna'] for c in m['campos'] if c['nombre'] == g) for g in grupo]
        reglas.append(f'UNIQUE ({", ".join(columnas)}).')
    for r in m['restricciones']:
        columnas = [next((c['columna'] for c in m['campos'] if c['nombre'] == g), g) for g in r['campos']]
        texto = f'<b>{r["nombre"]}</b>: UNIQUE ({", ".join(columnas)})'
        if r['condicion']:
            texto += f' cuando {condicion_legible(r["condicion"])}'
        reglas.append(texto + '.')
    indices = [c['columna'] for c in m['campos'] if c['indice'] and not c['unico'] and 'relacion' not in c and not c['pk']]
    if indices:
        reglas.append('Índice en: ' + ', '.join(indices) + '.')
    fks = [c['columna'] for c in m['campos'] if 'relacion' in c]
    if fks:
        reglas.append('Índice automático en las llaves foráneas: ' + ', '.join(fks) + '.')
    if m['ordering']:
        reglas.append('Orden predeterminado de consulta: ' + ', '.join(m['ordering']) + '.')
    if m['modelo'] == 'ProyectoTesis':
        reglas.append('Validación: avance_porcentaje entre 0 y 100.')
    return reglas


def condicion_legible(condicion):
    reemplazos = [("(AND: ", ''), (')', ''), ("('", ''), ("',", ' ='), ("'", ''), ('__isnull = False', ' IS NOT NULL'),
                  ('__isnull = True', ' IS NULL'), ('__in =', ' IN'), ('[', '('), (']', ')')]
    texto = condicion
    for a, b in reemplazos:
        texto = texto.replace(a, b)
    return texto.replace('periodo_inscripcion', 'periodo_inscripcion_id').strip()


def integridad():
    h = [PageBreak(), titulo('2.5 Relaciones e integridad referencial', h2, 1)]
    h.append(Paragraph(
        'La siguiente tabla lista todas las llaves foráneas del esquema con su cardinalidad y la acción que PostgreSQL y Django '
        'aplican al eliminar el registro padre: <b>CASCADE</b> elimina los registros dependientes, <b>PROTECT</b> impide eliminar '
        'el padre mientras existan dependientes y <b>SET_NULL</b> conserva el registro dejando la referencia en nulo.', cuerpo))
    filas = [['Tabla hija', 'Columna', 'Tabla padre', 'Cardinalidad', 'Al eliminar']]
    for r in RELACIONES:
        cardinalidad = '1 : 0..1' if r['uno_a_uno'] else ('0..1 : 0..*' if r['nulo'] else '1 : 0..*')
        filas.append([tabla_corta(r['hijo']), r['columna'], tabla_corta(r['padre']), cardinalidad, r['on_delete']])
    h.append(tabla(filas, [5.0 * cm, 3.5 * cm, 3.4 * cm, 2.6 * cm, ANCHO_UTIL - 14.5 * cm], estilo_celda=pequena))
    h.append(titulo('2.6 Reglas de negocio implementadas en el esquema', h2, 1))
    for texto in [
        'Un aspirante solo puede tener un documento por tipo (<i>documento_unico_por_tipo</i>).',
        'Un docente no puede repetirse en el jurado de un mismo proyecto y cada función del jurado es única por proyecto.',
        'Una materia solo aparece una vez por carga académica y una vez por plan de estudios.',
        'Un alumno no puede inscribirse dos veces a la misma materia en el mismo periodo, ni dos veces sin periodo asignado.',
        'Solo puede existir una solicitud de inscripción extemporánea pendiente por alumno y periodo.',
        'Un evaluado responde una sola vez cada pregunta de un examen.',
        'CURP, usuario, correo, matrícula y business_key son únicos por persona.',
        'La firma electrónica es única por expediente, firmante y rol, y su huella no se puede repetir.',
        'El historial y la auditoría conservan el nombre del responsable aunque su cuenta se elimine (SET_NULL).',
    ]:
        h.append(Paragraph(texto, vineta, bulletText='•'))
    h.append(titulo('2.7 Tablas de soporte del framework', h2, 1))
    h.append(Paragraph(
        'Además de las tablas del dominio, Django crea y administra las siguientes tablas. No forman parte del modelo de negocio, '
        'pero son necesarias para la autenticación, los permisos y el control de versiones del esquema.', cuerpo))
    h.append(tabla([['Tabla', 'Propósito']] + [list(t) for t in TABLAS_FRAMEWORK], [6.4 * cm, ANCHO_UTIL - 6.4 * cm]))
    return h


def conclusiones():
    return [
        PageBreak(),
        titulo('3. Conclusiones', h1, 0),
        Paragraph(
            f'La base de datos de SINAC NEXT se compone de {len(MODELOS)} tablas de dominio organizadas en seis módulos, con la tabla '
            'de usuarios como eje central. El uso del ORM de Django garantiza la correspondencia directa entre el diagrama de clases y '
            'el esquema físico, mientras que las restricciones de unicidad, las restricciones condicionales y las reglas de eliminación '
            'protegen la integridad de la información académica.', cuerpo),
        Paragraph(
            'El diseño separa los datos del motor de procesos LIDA (Camunda), conserva la trazabilidad mediante el historial y la '
            'auditoría, y permite evolucionar el esquema de forma controlada por medio de migraciones. Este documento debe '
            'actualizarse regenerando el archivo modelo_datos.json cada vez que se agregue una migración.', cuerpo),
    ]


def construir():
    doc = Documento(SALIDA, TITULO)
    indice = TableOfContents()
    indice.levelStyles = toc_estilos
    indice.dotsMinLevel = 0
    historia = portada(TITULO)
    historia += [Paragraph('Índice', h1), indice, PageBreak()]
    historia += introduccion()
    historia += arquitectura()
    clases, figura = seccion_diagramas(2, 'clase', 1)
    er, figura = seccion_diagramas(3, 'er', figura)
    historia += clases + er
    historia += diccionario()
    historia += integridad()
    historia += conclusiones()
    doc.multiBuild(historia, canvasmaker=canvas_numerado(TITULO))
    print(SALIDA)


if __name__ == '__main__':
    construir()
