"""Genera el documento de diagramas de arquitectura de SINAC NEXT."""
import os

from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, Spacer
from reportlab.platypus.tableofcontents import TableOfContents

from plantilla_cinvestav import (
    ANCHO_UTIL, GRIS, GRIS_CLARO, RAIZ, VERDE, VERDE_CLARO, VERDE_OSCURO,
    Documento, canvas_numerado, envolver, h1, h2, portada, texto_centrado, titulo, toc_estilos,
)
from generar_manual_tecnico_pdf import (
    caja, componentes_frontend, diagrama_capas, diagrama_despliegue, diagrama_peticion, flecha, nota, p,
    rutas_api, tabla_peq, vinetas,
)
from generar_manual_tecnico_pdf import figura as figura_base
from reportlab.pdfbase.pdfmetrics import stringWidth

TITULO = 'Diagramas de Arquitectura'
SALIDA = os.path.join(RAIZ, 'docs', 'SINAC_NEXT_Diagramas_de_Arquitectura.pdf')
EXTERNO = dict(relleno=colors.white, borde=GRIS, titulo_color=GRIS, discontinua=True)


# --------------------------------------------------------------------------------------------
# Primitivas
# --------------------------------------------------------------------------------------------

def actor(d, x, y, nombre):
    """Figura de actor UML con los pies en (x, y) y el nombre debajo."""
    trazo = dict(strokeColor=VERDE_OSCURO, strokeWidth=1.3)
    d.add(Circle(x, y + 31, 5.5, fillColor=VERDE_CLARO, **trazo))
    d.add(Line(x, y + 25.5, x, y + 11, **trazo))
    d.add(Line(x - 9, y + 20, x + 9, y + 20, **trazo))
    d.add(Line(x, y + 11, x - 7, y, **trazo))
    d.add(Line(x, y + 11, x + 7, y, **trazo))
    for i, linea in enumerate(envolver(nombre, 'Arial-Bold', 7.4, 78)):
        d.add(String(x, y - 10 - i * 9, linea, fontName='Arial-Bold', fontSize=7.4, fillColor=VERDE_OSCURO, textAnchor='middle'))


def etiqueta(d, x, y, texto, tam=6.8):
    lineas = texto.split('\n')
    alto = tam + 1.7
    ancho = max(stringWidth(t, 'Arial-Italic', tam) for t in lineas) + 4
    d.add(Rect(x - ancho / 2, y - (len(lineas) - 1) * alto - 2.5, ancho, len(lineas) * alto + 1,
               fillColor=colors.white, strokeColor=None))
    for i, linea in enumerate(lineas):
        d.add(String(x, y - i * alto, linea, fontName='Arial-Italic', fontSize=tam, fillColor=GRIS, textAnchor='middle'))


def escalar(dibujo, factor):
    dibujo.scale(factor, factor)
    dibujo.width *= factor
    dibujo.height *= factor
    return dibujo


def figura(dibujo, pie):
    elementos = figura_base(dibujo, pie, alto_maximo=560)
    elementos[0].hAlign = 'CENTER'
    return elementos


def marco(d, x, y, w, h, nombre, discontinuo=True, color=VERDE, relleno=colors.HexColor('#FAFCFB')):
    r = Rect(x, y, w, h, rx=8, ry=8, fillColor=relleno, strokeColor=color, strokeWidth=1.1)
    if discontinuo:
        r.strokeDashArray = [5, 3]
    d.add(r)
    d.add(String(x + w / 2, y + h - 12, nombre, fontName='Arial-Bold', fontSize=8.2, fillColor=VERDE_OSCURO, textAnchor='middle'))


# --------------------------------------------------------------------------------------------
# Diagramas
# --------------------------------------------------------------------------------------------

def diagrama_contexto():
    d = Drawing(490, 385)
    caja(d, 168, 175, 154, 86, ['SINAC NEXT', 'Sistema de información académica', 'del Cinvestav', '(SPA + API REST + LIDA)'], tam=8.2)
    izquierda = [
        (330, 'Aspirante', 'preregistro, documentos,\nexamen y entrevista', 245),
        (245, 'Alumno', 'inscripción, horario,\ntesis y solicitudes', 228),
        (160, 'Docente / Investigador', 'calificaciones, actas\ny evaluaciones', 210),
        (75, 'Director de tesis', 'seguimiento de\ntesistas y jurados', 192),
    ]
    for y, nombre, texto, destino in izquierda:
        actor(d, 42, y, nombre)
        flecha(d, [(62, y + 18), (168, destino)], doble=True)
        etiqueta(d, 112, (y + 18 + destino) / 2 + 14, texto, 7.8)
    derecha = [
        (318, 'Coordinación Académica', 'admisión, cargas y\noperación académica', 245),
        (208, 'Servicios Escolares', 'expedientes, validación\ny trámites', 218),
        (98, 'Administrador', 'usuarios, catálogos\ny configuración', 192),
    ]
    for y, nombre, texto, destino in derecha:
        actor(d, 448, y, nombre)
        flecha(d, [(428, y + 18), (322, destino)], doble=True)
        etiqueta(d, 378, (y + 18 + destino) / 2 + 14, texto, 7.8)
    caja(d, 130, 10, 100, 48, ['Jitsi Meet', 'videollamadas', '(externo)'], **EXTERNO)
    caja(d, 260, 10, 100, 48, ['Servidor SMTP', 'correo institucional', '(externo)'], **EXTERNO)
    flecha(d, [(220, 175), (185, 58)])
    etiqueta(d, 176, 124, 'genera enlaces\nde entrevista', 7.8)
    flecha(d, [(270, 175), (305, 58)])
    etiqueta(d, 318, 124, 'envía\nnotificaciones', 7.8)
    return d


def diagrama_produccion():
    d = Drawing(490, 400)
    caja(d, 4, 300, 82, 52, ['Usuarios', 'navegador web', '(HTTPS)'], relleno=colors.white)
    caja(d, 106, 300, 84, 52, ['Proxy inverso TLS', 'HTTPS :443', '(institucional)'], **EXTERNO)
    caja(d, 4, 40, 82, 52, ['Administrador TI', 'SSH / túnel', 'a 127.0.0.1'], relleno=colors.white)
    marco(d, 200, 14, 286, 372, 'Servidor Linux · Docker Engine', discontinuo=False)
    marco(d, 210, 116, 266, 246, 'Red interna Docker (<proyecto>_default)')
    caja(d, 220, 270, 115, 60, ['sinac-frontend', 'nginx :80', 'publicado en :3000'])
    caja(d, 220, 188, 115, 60, ['sinac-backend', 'Gunicorn :8000', '127.0.0.1:8000'])
    caja(d, 250, 126, 85, 44, ['sinac-alertas', 'ciclo de 3600 s'])
    caja(d, 352, 270, 115, 60, ['camunda', 'Tomcat :8080', '127.0.0.1:8081'])
    caja(d, 352, 188, 115, 60, ['camunda-postgres', 'PostgreSQL :5432', '127.0.0.1:5433'])
    caja(d, 220, 32, 115, 50, ['documentos_media', 'volumen nombrado', '/app/media'], relleno=GRIS_CLARO, borde=GRIS, titulo_color=GRIS)
    caja(d, 352, 32, 115, 50, ['postgres_data', 'volumen nombrado', '/var/lib/postgresql/data'], relleno=GRIS_CLARO, borde=GRIS, titulo_color=GRIS)

    flecha(d, [(86, 326), (106, 326)])
    etiqueta(d, 96, 362, 'HTTPS')
    flecha(d, [(190, 318), (220, 304)])
    etiqueta(d, 196, 300, ':3000')
    flecha(d, [(277, 270), (277, 248)])
    etiqueta(d, 302, 262, '/api/ · /media/')
    flecha(d, [(335, 218), (352, 218)])
    flecha(d, [(335, 240), (362, 270)])
    flecha(d, [(409, 270), (409, 248)])
    etiqueta(d, 424, 262, 'JDBC')
    flecha(d, [(335, 152), (372, 188)])
    etiqueta(d, 362, 160, 'SQL')
    flecha(d, [(232, 188), (232, 82)])
    flecha(d, [(409, 188), (409, 82)])
    flecha(d, [(86, 66), (200, 66)])
    etiqueta(d, 143, 80, 'SSH (consola\nCamunda y BD)')
    return d


def diagrama_dominios_backend():
    d = Drawing(490, 372)
    caja(d, 4, 336, 482, 30, ['preregistro/urls.py · enrutamiento de la API REST', ''], tam=8)
    dominios = [
        ('Acceso y perfil', ['views.py', 'auth/login · auth/refresh', 'preregistro · perfil', 'notificaciones']),
        ('Admisión', ['views.py (coordinación)', 'examenes_gestion_views.py', 'docente_views.py', '(entrevistas y exámenes)']),
        ('Operación académica', ['views.py (inscripciones,', 'cargas, horarios, boletas)', 'docente_views.py', '(calificaciones y actas)']),
        ('Tesis y posgrado', ['tesis_views · tesis_flujo_views', 'jurado_views · director_views', 'antiplagio_views', 'predoctoral_views']),
        ('Servicios Escolares', ['servicios_views.py', 'expediente_central_views.py', 'egresados · docentes_views', 'diploma_views.py']),
        ('Administración', ['admin_views.py', 'historico_views.py', 'auditoría y catálogos', 'configuración del sistema']),
    ]
    w, h = 154, 100
    for i, (nombre, items) in enumerate(dominios):
        fila, col = divmod(i, 3)
        x = 4 + col * (w + 10)
        y = 216 - fila * (h + 14)
        d.add(Rect(x, y, w, h, rx=6, ry=6, fillColor=VERDE_CLARO, strokeColor=VERDE_OSCURO, strokeWidth=1))
        d.add(Rect(x, y + h - 20, w, 20, rx=6, ry=6, fillColor=VERDE, strokeColor=VERDE_OSCURO, strokeWidth=1))
        d.add(String(x + w / 2, y + h - 14, nombre, fontName='Arial-Bold', fontSize=8.2, fillColor=colors.white, textAnchor='middle'))
        for j, item in enumerate(items):
            d.add(String(x + w / 2, y + h - 36 - j * 14, item, fontName='Arial', fontSize=7.4, fillColor=colors.HexColor('#1F2A33'), textAnchor='middle'))
        if fila == 0:
            flecha(d, [(x + w / 2, 336), (x + w / 2, y + h)], color=VERDE_OSCURO)
    d.add(Rect(4, 8, 482, 76, rx=6, ry=6, fillColor=colors.HexColor('#FAFCFB'), strokeColor=GRIS, strokeWidth=1))
    d.add(String(245, 70, 'Núcleo compartido', fontName='Arial-Bold', fontSize=8.2, fillColor=GRIS, textAnchor='middle'))
    nucleo = ['models.py (29 modelos)', 'serializers.py', 'seguridad.py', 'historial.py', 'configuracion_sistema.py', 'alertas.py']
    wn = (482 - 12 - 5 * 6) / 6
    for i, item in enumerate(nucleo):
        x = 10 + i * (wn + 6)
        d.add(Rect(x, 18, wn, 40, rx=3, ry=3, fillColor=GRIS_CLARO, strokeColor=GRIS, strokeWidth=0.6))
        texto_centrado(d, x + wn / 2, 38, envolver(item, 'Arial', 7.2, wn - 6), 'Arial', 7.2)
    for col in range(3):
        x = 4 + col * (w + 10) + w / 2
        flecha(d, [(x, 102), (x, 84)], color=GRIS)
    return d


def diagrama_frontend():
    return diagrama_capas([
        ('Aplicación', ['App.js (vista y sesión)', 'Navbar', 'ErrorBoundary', 'LoadingScreen']),
        ('Vistas públicas', ['HomePage', 'AspirantRegistration', 'LoginView', 'ContactPage / Aviso de privacidad']),
        ('Paneles por rol', ['PanelAspirante', 'PanelAlumno', 'PanelDocente', 'PanelDirector', 'PanelCoordinacion',
                             'PanelServiciosEscolares', 'PanelAdministrador']),
        ('Componentes compartidos', ['TablaControles', 'DashboardAnalitico', 'NotificationBell', 'HistoricoPanel',
                                     'ExamenesEnLinea', 'ErrorPage', 'ExpedienteCentralizado', 'DocumentosAspirante']),
        ('Servicios del cliente', ['fetch + JWT', 'translations.js', '*Translations.js', 'styles.css / CSS por panel']),
    ], lateral=('Backend', ['/api/auth/*', '/api/<rol>/*', '/media/ (firmado)', 'Respuestas JSON', 'PDF / XLSX']))


def diagrama_datos():
    return diagrama_capas([
        ('Identidad y control', ['Aspirante (usuario)', 'ConfiguracionSistema', 'AuditoriaSistema', 'HistorialPersona']),
        ('Admisión', ['DocumentoAspirante', 'ExpedienteDigital', 'FirmaElectronica', 'SeguimientoSolicitud', 'EntrevistaVirtual',
                      'ExamenEnLinea', 'PreguntaExamen', 'RespuestaExamen', 'EvaluacionColegio']),
        ('Operación académica', ['Materia', 'ConfiguracionPrograma', 'PlanEstudioMateria', 'PeriodoInscripcion', 'Inscripcion',
                                 'CargaAcademica', 'CargaAcademicaMateria', 'SolicitudInscripcion Extemporanea',
                                 'SolicitudInscripcion ExtemporaneaMateria', 'SolicitudAcademica']),
        ('Tesis', ['ProyectoTesis', 'SolicitudDireccionTesis', 'JuradoProyecto', 'DefensaTesis', 'RevisionAntiplagio']),
        ('Egreso', ['EgresoAlumno']),
    ], flechas=False, titulo_ancho=104)


def diagrama_lida():
    d = Drawing(490, 300)
    disparadores = [
        (238, ['views.py', 'registro de aspirante'], 'start'),
        (180, ['views.py', 'carga de documento'], 'message'),
        (122, ['views.py', 'cargas académicas'], 'start · task'),
        (64, ['docente_views.py', 'programar entrevista'], 'start'),
    ]
    for y, texto, op in disparadores:
        caja(d, 4, y, 120, 42, texto)
        flecha(d, [(124, y + 21), (178, y + 21)])
        etiqueta(d, 151, y + 26, op)
    caja(d, 178, 64, 124, 216, ['Camunda REST', '/engine-rest', '', 'POST /process-definition/', 'key/{clave}/start', '',
                                'POST /message', '', 'GET /task', 'POST /task/{id}/complete'], relleno=colors.white, tam=7.2)
    caja(d, 178, 6, 124, 38, ['PostgreSQL', 'tablas ACT_* de Camunda'], relleno=GRIS_CLARO, borde=GRIS, titulo_color=GRIS)
    flecha(d, [(240, 64), (240, 44)])
    procesos = [
        (246, ['sinac_preregistro_v1', 'Revisión por Coordinación'], True),
        (196, ['sinac_documentos_v1', 'desplegado, sin invocación'], False),
        (146, ['sinac_entrevista_v1', 'Crear sala → Entrevista'], True),
        (96, ['sinac_examen_v1', 'desplegado, sin invocación'], False),
        (46, ['carga_academica', 'Revisión → Publicación'], True),
    ]
    for y, texto, activo in procesos:
        if activo:
            caja(d, 346, y, 140, 38, texto)
            flecha(d, [(302, min(max(y + 19, 70), 274)), (346, y + 19)], color=VERDE_OSCURO)
        else:
            caja(d, 346, y, 140, 38, texto, **EXTERNO)
    etiqueta(d, 416, 292, 'Procesos BPMN (carpeta camunda/)')
    return d


def cadena(etapas, por_fila=5, ancho=490, alto_caja=50):
    """Secuencia de pasos en zigzag: la primera fila de izquierda a derecha y la siguiente de regreso."""
    filas = -(-len(etapas) // por_fila)
    sep_x, sep_y = 16, 30
    w = (ancho - 8 - (por_fila - 1) * sep_x) / por_fila
    alto = filas * alto_caja + (filas - 1) * sep_y + 8
    d = Drawing(ancho, alto)
    posiciones = []
    for i, etapa in enumerate(etapas):
        fila, col = divmod(i, por_fila)
        if fila % 2:
            col = por_fila - 1 - col
        x = 4 + col * (w + sep_x)
        y = alto - 4 - (fila + 1) * alto_caja - fila * sep_y
        caja(d, x, y, w, alto_caja, [f'{i + 1}. {etapa[0]}'] + envolver(etapa[1], 'Arial', 7, w - 8), tam=7)
        posiciones.append((x, y, fila))
    for (x1, y1, f1), (x2, y2, f2) in zip(posiciones, posiciones[1:]):
        if f1 == f2:
            if x2 > x1:
                flecha(d, [(x1 + w, y1 + alto_caja / 2), (x2, y2 + alto_caja / 2)], color=VERDE_OSCURO)
            else:
                flecha(d, [(x1, y1 + alto_caja / 2), (x2 + w, y2 + alto_caja / 2)], color=VERDE_OSCURO)
        else:
            flecha(d, [(x1 + w / 2, y1), (x2 + w / 2, y2 + alto_caja)], color=VERDE_OSCURO)
    return d


def diagrama_capas_seguridad():
    return diagrama_capas([
        ('Red', ['Proxy TLS (HTTPS)', 'Puertos internos en 127.0.0.1', 'Red Docker aislada', 'Solo :3000 expuesto']),
        ('nginx', ['CSP y cabeceras', 'limit_req / limit_conn', 'client_max_body_size 10 MB', 'Bloqueo de archivos ocultos']),
        ('Django', ['ALLOWED_HOSTS', 'CORS y CSRF', 'SecurityMiddleware / HSTS', 'Errores sin trazas']),
        ('Django REST Framework', ['JWT (SimpleJWT)', 'Throttling por ámbito', 'IsAuthenticated', 'Validación de rol']),
        ('Aplicación', ['Validación real de archivos', 'Política de contraseñas', 'Bloqueo por intentos', 'Registro solo como aspirante']),
        ('Datos', ['URLs firmadas de /media/', 'Permisos de archivo 0640', 'celda_segura() en exportaciones', 'Auditoría e historial']),
    ], titulo_ancho=104)


def diagrama_construccion():
    d = Drawing(490, 170)
    filas = [
        ('Frontend', [['package.json', 'npm install'], ['Código React', 'npm run build'],
                      ['nginx:alpine', 'copia build y nginx.conf'], ['sinac-frontend', 'nginx -g daemon off']], 92),
        ('Backend', [['python:3.12-slim', 'imagen base'], ['requirements.txt', 'pip install'],
                     ['Inicio del contenedor', 'migrate --noinput'], ['sinac-backend', 'Gunicorn o runserver']], 10),
    ]
    for nombre, pasos_, y in filas:
        d.add(Rect(0, y, 80, 62, rx=6, ry=6, fillColor=VERDE, strokeColor=VERDE, strokeWidth=0.8))
        d.add(String(40, y + 28, nombre, fontName='Arial-Bold', fontSize=8.5, fillColor=colors.white, textAnchor='middle'))
        w, sep = 90, 14
        for i, paso in enumerate(pasos_):
            x = 92 + i * (w + sep)
            caja(d, x, y + 6, w, 50, paso, tam=7.2)
            if i:
                flecha(d, [(x - sep, y + 31), (x, y + 31)], color=VERDE_OSCURO)
    d.add(String(245, 160, 'docker compose up -d --build', fontName='Courier-Bold', fontSize=8.5, fillColor=VERDE_OSCURO, textAnchor='middle'))
    return d


def leyenda():
    d = Drawing(490, 90)
    elementos = [
        ('caja', 'Contenedor o componente del sistema'),
        ('externo', 'Sistema externo o elemento opcional'),
        ('volumen', 'Almacenamiento persistente'),
        ('capa', 'Capa o agrupación lógica'),
    ]
    for i, (tipo, texto) in enumerate(elementos):
        x = 4 + (i % 2) * 245
        y = 62 - (i // 2) * 32
        if tipo == 'caja':
            caja(d, x, y, 46, 24, ['  '])
        elif tipo == 'externo':
            caja(d, x, y, 46, 24, ['  '], **EXTERNO)
        elif tipo == 'volumen':
            caja(d, x, y, 46, 24, ['  '], relleno=GRIS_CLARO, borde=GRIS)
        else:
            d.add(Rect(x, y, 46, 24, rx=5, ry=5, fillColor=VERDE, strokeColor=VERDE))
        d.add(String(x + 56, y + 9, texto, fontName='Arial', fontSize=8.5, fillColor=colors.HexColor('#1F2A33')))
    flecha(d, [(4, 6), (50, 6)])
    d.add(String(60, 3, 'Comunicación o dependencia (punta en el destino; doble punta: interacción bidireccional)',
                 fontName='Arial', fontSize=8.5, fillColor=colors.HexColor('#1F2A33')))
    return d


# --------------------------------------------------------------------------------------------
# Contenido
# --------------------------------------------------------------------------------------------

DECISIONES = [
    ['Monolito modular en Django', 'Una sola aplicación (preregistro) con módulos por dominio.', 'Simplifica el despliegue, las transacciones y las pruebas; el equipo es reducido.'],
    ['SPA en React sin enrutador', 'App.js controla la vista activa en el estado.', 'Navegación simple por rol; el control de acceso se valida en un solo punto.'],
    ['API REST con JWT', 'Tokens de acceso y renovación sin sesión en servidor.', 'Desacopla frontend y backend y facilita clientes futuros.'],
    ['Camunda como motor LIDA', 'Procesos BPMN desplegados desde camunda/.', 'Hace visibles y versionables los procesos institucionales.'],
    ['Tolerancia a fallos de LIDA', 'Si Camunda no responde se registra una advertencia y se continúa.', 'La operación académica no depende de la disponibilidad del motor.'],
    ['PostgreSQL compartido', 'Una instancia para SINAC NEXT y Camunda.', 'Menos infraestructura y un único respaldo.'],
    ['Archivos con URL firmada', 'Django sirve /media/ solo con una firma temporal.', 'Protege documentos personales sin un servidor de archivos adicional.'],
    ['Docker Compose', 'Cinco servicios declarados en un archivo.', 'Instalación reproducible en desarrollo y producción.'],
    ['Alertas en contenedor propio', 'Ciclo de ejecución horaria del comando de alertas.', 'Evita depender de cron del servidor y aísla la carga.'],
    ['Configuración por entorno', 'settings.py lee variables de entorno.', 'Mismo código en todos los ambientes y secretos fuera del repositorio.'],
]


def construir():
    rutas = rutas_api()
    componentes = componentes_frontend()
    H = []

    # 1 ---------------------------------------------------------------------------------------------
    H += [titulo('1. Introducción', h1, 0)]
    H += [p('Este documento reúne los diagramas de arquitectura de <b>SINAC NEXT</b>. Cada diagrama muestra el sistema desde '
            'una perspectiva distinta, de lo general a lo particular: el contexto con sus usuarios y sistemas externos, los '
            'contenedores que lo forman, los componentes internos del backend y del frontend, la organización de los datos, la '
            'integración con el motor de procesos LIDA, el comportamiento en tiempo de ejecución, la seguridad y el despliegue.')]
    H += [titulo('1.1 Propósito y alcance', h2, 1)]
    H += [p('Servir como referencia común para el equipo de desarrollo, el personal de infraestructura y los evaluadores del '
            'proyecto. Los diagramas corresponden a la versión actual del código; las tablas de rutas y componentes se obtienen '
            'directamente del código fuente al generar el documento.')]
    H += [titulo('1.2 Notación', h2, 1)]
    H += [p('Los diagramas siguen una notación inspirada en el modelo C4 para las vistas de contexto, contenedores y componentes, '
            'y en los diagramas de despliegue de UML para la vista física. Se usan los siguientes elementos:')]
    H += figura(leyenda(), 'Leyenda de los diagramas.')
    H += [titulo('1.3 Vistas incluidas', h2, 1)]
    H += [tabla_peq([
        ['Vista', 'Pregunta que responde', 'Capítulo'],
        ['Contexto', '¿Quién usa el sistema y con qué sistemas externos se relaciona?', '2'],
        ['Contenedores', '¿Qué aplicaciones y almacenes de datos lo componen y cómo se comunican?', '3'],
        ['Componentes del backend', '¿Cómo se organiza internamente la API?', '4'],
        ['Componentes del frontend', '¿Cómo se organiza la interfaz de usuario?', '5'],
        ['Datos', '¿Cómo se agrupan las entidades por dominio?', '6'],
        ['Integración LIDA', '¿Cómo interactúa el backend con los procesos BPMN?', '7'],
        ['Dinámica', '¿Qué ocurre durante una petición y un inicio de sesión?', '8'],
        ['Seguridad', '¿Qué controles protegen al sistema en cada capa?', '9'],
        ['Despliegue', '¿Dónde y cómo se ejecuta el sistema?', '10'],
    ], [3.8 * cm, ANCHO_UTIL - 5.6 * cm, 1.8 * cm]), Spacer(1, 6)]
    H += [PageBreak()]

    # 2 ---------------------------------------------------------------------------------------------
    H += [titulo('2. Diagrama de contexto', h1, 0)]
    H += [p('El diagrama de contexto presenta a SINAC NEXT como una caja negra, rodeado de los siete tipos de usuario que lo '
            'operan y de los dos servicios externos de los que depende. El motor de procesos LIDA (Camunda) forma parte del '
            'sistema y por ello no aparece como externo.')]
    H += figura(escalar(diagrama_contexto(), 0.78), 'Diagrama de contexto de SINAC NEXT.')
    H += [tabla_peq([
        ['Elemento', 'Tipo', 'Relación con el sistema'],
        ['Aspirante', 'Persona', 'Se preregistra, completa su expediente, presenta el examen en línea y asiste a entrevistas.'],
        ['Alumno', 'Persona', 'Se inscribe, consulta horario y calificaciones, gestiona su tesis y realiza solicitudes académicas.'],
        ['Docente / Investigador', 'Persona', 'Captura calificaciones, firma actas, evalúa exámenes y entrevistas.'],
        ['Director de tesis', 'Persona', 'Da seguimiento a sus tesistas, avances y jurados.'],
        ['Coordinación Académica', 'Persona', 'Gestiona la admisión, las cargas académicas, los periodos y la operación del programa.'],
        ['Servicios Escolares', 'Persona', 'Valida inscripciones, administra expedientes, egresados y trámites oficiales.'],
        ['Administrador', 'Persona', 'Administra usuarios, catálogos, configuración y auditoría.'],
        ['Jitsi Meet', 'Sistema externo', 'Aloja las salas de videollamada cuyos enlaces genera el backend.'],
        ['Servidor SMTP', 'Sistema externo', 'Entrega los correos de notificación enviados por el backend.'],
    ], [3.8 * cm, 2.6 * cm, ANCHO_UTIL - 6.4 * cm])]
    H += [PageBreak()]

    # 3 ---------------------------------------------------------------------------------------------
    H += [titulo('3. Diagrama de contenedores', h1, 0)]
    H += [p('Al abrir la caja de SINAC NEXT aparecen cinco contenedores Docker y dos volúmenes persistentes. El navegador solo '
            'se comunica con nginx, que sirve la aplicación React y reenvía las peticiones de la API y de archivos al backend.')]
    H += figura(escalar(diagrama_despliegue(), 0.9), 'Diagrama de contenedores de SINAC NEXT.')
    H += [tabla_peq([
        ['Contenedor', 'Tecnología', 'Responsabilidad', 'Se comunica con'],
        ['sinac-frontend', 'nginx + React 18', 'Servir la SPA, aplicar cabeceras y límites, proxy de /api/ y /media/.', 'Navegador (HTTP), backend (HTTP).'],
        ['sinac-backend', 'Django 5 + DRF + Gunicorn', 'Reglas de negocio, API REST, documentos PDF/XLSX y archivos privados.', 'PostgreSQL (SQL), Camunda (REST), SMTP.'],
        ['sinac-alertas', 'Django (comando)', 'Generar alertas automatizadas cada hora.', 'PostgreSQL (SQL).'],
        ['camunda', 'Camunda BPM Platform', 'Ejecutar los procesos BPMN de LIDA.', 'PostgreSQL (JDBC).'],
        ['camunda-postgres', 'PostgreSQL 15', 'Persistir los datos del sistema y del motor de procesos.', '—'],
        ['documentos_media', 'Volumen Docker', 'Almacenar documentos, fotografías y archivos generados.', 'Montado en el backend.'],
    ], [3 * cm, 3.4 * cm, 6 * cm, ANCHO_UTIL - 12.4 * cm])]
    H += [PageBreak()]

    # 4 ---------------------------------------------------------------------------------------------
    H += [titulo('4. Componentes del backend', h1, 0)]
    H += [titulo('4.1 Vista por capas', h2, 1)]
    H += [p('Internamente, el backend es un monolito modular. Cada petición atraviesa capas bien definidas: enrutamiento, '
            'autenticación y control, vistas, validación y persistencia; las integraciones se usan desde las vistas.')]
    H += figura(diagrama_capas([
        ('Enrutamiento', ['config/urls.py', 'preregistro/urls.py', f'{len(rutas)} rutas REST', 'servir_media (firmado)']),
        ('Autenticación y control', ['HistorialJWT Authentication', 'Throttling DRF', 'Validación de rol', 'Bloqueo por intentos']),
        ('Vistas (APIView)', ['views.py', 'servicios_views.py', 'docente_views.py', 'admin_views.py', 'director / tesis / jurado',
                              'exámenes y entrevistas', 'egresados / histórico', 'expediente central']),
        ('Validación y serialización', ['serializers.py', 'seguridad.py', 'configuracion_ sistema.py']),
        ('Dominio y persistencia', ['models.py (29 modelos)', 'historial.py (señales)', 'alertas.py', 'migraciones']),
    ], lateral=('Integraciones', ['Camunda REST (LIDA)', 'SMTP (send_mail)', 'reportlab (PDF)', 'openpyxl (XLSX)', 'Jitsi (enlaces)'])),
        'Componentes del backend organizados por capas.')
    H += [PageBreak(), titulo('4.2 Vista por dominios', h2, 1)]
    H += [p('Los módulos de vistas se agrupan en seis dominios funcionales que comparten un núcleo común de modelos, '
            'serializadores y servicios transversales.')]
    H += figura(diagrama_dominios_backend(), 'Componentes del backend agrupados por dominio funcional.')
    conteo = {}
    for r in rutas:
        conteo[r['modulo']] = conteo.get(r['modulo'], 0) + 1
    filas = [['Módulo de vistas', 'Rutas', 'Prefijos principales']]
    for modulo, n in sorted(conteo.items(), key=lambda x: -x[1]):
        prefijos = sorted({r['ruta'].split('/')[2] for r in rutas if r['modulo'] == modulo})
        filas.append([modulo, str(n), ', '.join(prefijos)])
    H += [Paragraph('<b>Distribución de las rutas de la API por módulo</b>', h2.clone('h2b', fontSize=11, spaceBefore=4)),
          tabla_peq(filas, [4.6 * cm, 1.4 * cm, ANCHO_UTIL - 6 * cm])]
    H += [PageBreak()]

    # 5 ---------------------------------------------------------------------------------------------
    H += [titulo('5. Componentes del frontend', h1, 0)]
    H += [p(f'La interfaz es una SPA de React con {len(componentes)} módulos de componentes. <font face="Courier">App.js</font> '
            'decide qué vista mostrar según la sesión y el rol; cada rol tiene su panel, que reutiliza componentes compartidos y '
            'consume la API mediante <font face="Courier">fetch</font> con el token JWT.')]
    H += figura(diagrama_frontend(), 'Componentes del frontend y su relación con el backend.')
    H += [tabla_peq([
        ['Rol', 'Vista', 'Componente principal', 'Prefijo de API'],
        ['aspirante', 'panel', 'PanelAspirante', '/api/preregistro/ (perfil, documentos, exámenes, entrevistas)'],
        ['alumno', 'alumno-panel', 'PanelAlumno', '/api/preregistro/ (materias, inscripciones, horario), /api/tesis/, /api/proyectos-tesis/'],
        ['docente, investigador', 'docente-panel', 'PanelDocente', '/api/docente/'],
        ['director', 'director-panel', 'PanelDirector', '/api/director/, /api/proyectos-tesis/'],
        ['coordinacion', 'coordinacion-panel', 'PanelCoordinacion', '/api/coordinacion/, /api/examenes-gestion/, /api/cargas-academicas/'],
        ['servicios', 'servicios-panel', 'PanelServiciosEscolares', '/api/servicios-escolares/, /api/egresados/, /api/historico/'],
        ['admin', 'admin-panel', 'PanelAdministrador', '/api/administracion/'],
    ], [2.8 * cm, 2.8 * cm, 3.8 * cm, ANCHO_UTIL - 9.4 * cm])]
    H += [PageBreak()]

    # 6 ---------------------------------------------------------------------------------------------
    H += [titulo('6. Arquitectura de datos', h1, 0)]
    H += [p('Los 29 modelos de Django se agrupan en cinco dominios. El modelo <b>Aspirante</b> es el usuario único del sistema: '
            'una misma cuenta evoluciona de aspirante a alumno y egresado, y también representa al personal mediante el campo '
            '<font face="Courier">rol</font>. Todas las demás entidades se relacionan directa o indirectamente con él.')]
    H += figura(escalar(diagrama_datos(), 0.92), 'Agrupación de las entidades de datos por dominio.')
    H += vinetas([
        '<b>Persistencia:</b> PostgreSQL 15 mediante el ORM de Django y migraciones versionadas en '
        '<font face="Courier">preregistro/migrations</font>.',
        '<b>Archivos:</b> los documentos se guardan en el volumen <font face="Courier">documentos_media</font>; la base de datos '
        'almacena solo su ruta.',
        '<b>Trazabilidad:</b> HistorialPersona y AuditoriaSistema registran los cambios y el actor que los realizó.',
        '<b>Procesos:</b> Camunda guarda el estado de las instancias BPMN en sus propias tablas (ACT_*) dentro de la misma base de datos.',
    ])
    H += nota('El detalle de atributos, relaciones, el diagrama de clases y el diagrama entidad-relación se encuentran en el '
              'documento <i>SINAC_NEXT_Base_de_Datos.pdf</i>.')
    H += [PageBreak()]

    # 7 ---------------------------------------------------------------------------------------------
    H += [titulo('7. Arquitectura de integración con LIDA', h1, 0)]
    H += [p('El backend actúa como cliente de la API REST de Camunda. Cuatro puntos del código inician instancias de proceso, '
            'envían mensajes o completan tareas. Dos procesos están desplegados como modelo, pero todavía no se invocan desde el backend.')]
    H += figura(diagrama_lida(), 'Integración entre el backend y los procesos BPMN de LIDA.')
    H += [tabla_peq([
        ['Proceso', 'Iniciado por', 'Business key', 'Estado'],
        ['sinac_preregistro_v1', 'Registro de aspirante (views.py)', 'Clave del aspirante', 'En uso'],
        ['carga_academica', 'Flujo de cargas académicas (views.py)', 'Carga académica', 'En uso (inicio y tareas)'],
        ['sinac_entrevista_v1', 'Programación de entrevista (docente_views.py)', 'entrevista-{id}', 'En uso'],
        ['sinac_documentos_v1', '—', '—', 'Desplegado, sin invocación'],
        ['sinac_examen_v1', '—', '—', 'Desplegado, sin invocación'],
    ], [3.6 * cm, 5.4 * cm, 3.2 * cm, ANCHO_UTIL - 12.2 * cm])]
    H += [Spacer(1, 8)]
    H += vinetas([
        '<b>Tolerancia a fallos:</b> las llamadas usan tiempos de espera de 4 a 8 segundos; si Camunda no responde, el dato se '
        'guarda en PostgreSQL y solo se registra una advertencia.',
        '<b>Despliegue de procesos:</b> los archivos .bpmn de <font face="Courier">camunda/</font> se montan en el contenedor y '
        'Camunda los despliega al iniciar, creando una nueva versión cuando cambian.',
        '<b>Mensaje DocumentoCargado:</b> el proceso de preregistro no define un evento que lo reciba, por lo que Camunda lo rechaza.',
    ])
    H += [PageBreak()]

    # 8 ---------------------------------------------------------------------------------------------
    H += [titulo('8. Vista dinámica', h1, 0)]
    H += [titulo('8.1 Recorrido de una petición', h2, 1)]
    H += [p('Toda petición autenticada sigue el mismo camino a través de las capas del sistema:')]
    H += figura(diagrama_peticion(), 'Recorrido de una petición autenticada.')
    H += [titulo('8.2 Autenticación y ciclo de la sesión', h2, 1)]
    H += [p('El inicio de sesión combina controles en nginx, en Django REST Framework y en la aplicación. El siguiente diagrama '
            'muestra el ciclo completo desde el formulario hasta el cierre de la sesión.')]
    H += figura(cadena([
        ('LoginView', 'usuario o correo y contraseña'),
        ('nginx', 'limit_req: 10 peticiones por minuto'),
        ('Throttling', 'THROTTLE_LOGIN por IP'),
        ('Bloqueo', '¿cuenta bloqueada por intentos fallidos?'),
        ('Contraseña', 'verificación; si falla suma un intento'),
        ('Emisión JWT', 'access 120 min y refresh 24 h'),
        ('Almacenamiento', 'localStorage o sessionStorage'),
        ('Peticiones', 'Authorization: Bearer <access>'),
        ('Validación', 'HistorialJWT Authentication y rol'),
        ('Cierre', 'respuesta 401 o 60 min en el cliente'),
    ]), 'Ciclo de autenticación y sesión.')
    H += [p('Los diagramas de secuencia detallados de cada actor se encuentran en el documento '
            '<i>SINAC_NEXT_Diagramas_de_Secuencia.pdf</i>.')]
    H += [PageBreak()]

    # 9 ---------------------------------------------------------------------------------------------
    H += [titulo('9. Arquitectura de seguridad', h1, 0)]
    H += [p('La seguridad se organiza en defensa en profundidad: cada capa aplica sus propios controles, de modo que la falla de '
            'uno no compromete al sistema completo. El diagrama se lee de afuera (red) hacia adentro (datos).')]
    H += figura(diagrama_capas_seguridad(), 'Capas de seguridad de SINAC NEXT.')
    H += [tabla_peq([
        ['Activo', 'Amenaza', 'Control principal'],
        ['Cuentas de usuario', 'Fuerza bruta y robo de credenciales', 'Límites de peticiones, bloqueo por intentos y política de contraseñas.'],
        ['Privilegios', 'Escalada de rol desde el registro público', 'El registro siempre crea aspirantes; las vistas validan el rol.'],
        ['Documentos personales', 'Acceso directo a /media/', 'URLs firmadas que caducan a las 12 horas.'],
        ['Servidor', 'Carga de archivos maliciosos', 'Verificación del contenido real, extensión y tamaño.'],
        ['Usuarios de reportes', 'Inyección de fórmulas en CSV/XLSX', 'Neutralización con celda_segura().'],
        ['Navegador', 'XSS y clickjacking', 'Content-Security-Policy y X-Frame-Options DENY.'],
        ['Infraestructura', 'Acceso directo a la BD o a Camunda', 'Puertos publicados solo en 127.0.0.1.'],
    ], [3.4 * cm, 5.2 * cm, ANCHO_UTIL - 8.6 * cm])]
    H += [PageBreak()]

    # 10 --------------------------------------------------------------------------------------------
    H += [titulo('10. Arquitectura de despliegue', h1, 0)]
    H += [titulo('10.1 Despliegue en producción', h2, 1)]
    H += [p('En producción, un proxy inverso con certificado TLS recibe el tráfico HTTPS y lo reenvía al puerto 3000 del servidor. '
            'Los demás puertos solo escuchan en la interfaz local, por lo que la administración de Camunda y de la base de datos '
            'se realiza mediante un túnel SSH.')]
    H += figura(diagrama_produccion(), 'Diagrama de despliegue en producción.')
    H += [tabla_peq([
        ['Puerto en el servidor', 'Contenedor', 'Interfaz', 'Uso'],
        ['3000', 'sinac-frontend (80)', 'Todas', 'Acceso de los usuarios (detrás del proxy TLS).'],
        ['8000', 'sinac-backend (8000)', '127.0.0.1', 'Diagnóstico local de la API.'],
        ['8081', 'camunda (8080)', '127.0.0.1', 'Consola Cockpit/Tasklist.'],
        ['5433', 'camunda-postgres (5432)', '127.0.0.1', 'Respaldos y administración de la base de datos.'],
    ], [3.4 * cm, 4.2 * cm, 2.4 * cm, ANCHO_UTIL - 10 * cm])]
    H += [titulo('10.2 Construcción de imágenes', h2, 1)]
    H += [p('Las imágenes se construyen con Docker. El frontend usa una construcción multietapa para que la imagen final '
            'contenga solo nginx y los archivos compilados; el backend aplica las migraciones cada vez que inicia.')]
    H += figura(diagrama_construccion(), 'Construcción de las imágenes del frontend y del backend.')
    H += [PageBreak()]

    # 11 --------------------------------------------------------------------------------------------
    H += [titulo('11. Decisiones de arquitectura', h1, 0)]
    H += [p('La siguiente tabla resume las principales decisiones que dan forma a la arquitectura y su justificación.')]
    H += [tabla_peq([['Decisión', 'Descripción', 'Justificación']] + DECISIONES,
                    [3.8 * cm, 5.6 * cm, ANCHO_UTIL - 9.4 * cm]), Spacer(1, 8)]
    H += [titulo('11.1 Evolución recomendada', h2, 1)]
    H += vinetas([
        'Invocar los procesos <font face="Courier">sinac_documentos_v1</font> y <font face="Courier">sinac_examen_v1</font> o '
        'retirarlos, y agregar el evento de mensaje <font face="Courier">DocumentoCargado</font> al proceso de preregistro.',
        'Configurar el servidor SMTP por variables de entorno.',
        'Fijar la versión de la imagen de Camunda y ejecutar el backend con un usuario sin privilegios.',
        'Si la carga crece, separar la base de datos de Camunda y escalar horizontalmente el backend detrás de nginx.',
    ])

    # 12 --------------------------------------------------------------------------------------------
    H += [PageBreak(), titulo('12. Conclusiones', h1, 0)]
    H += [p('La arquitectura de SINAC NEXT combina una interfaz React desacoplada, una API REST modular en Django y un motor de '
            'procesos LIDA, todo desplegado con Docker Compose. Las vistas presentadas muestran un sistema con responsabilidades '
            'bien separadas, una única fuente de datos y controles de seguridad en cada capa.')]
    H += [p('Esta organización permite incorporar nuevos módulos académicos agregando vistas y componentes por dominio sin '
            'alterar el resto del sistema. También permite trasladar la solución a la infraestructura institucional con cambios '
            'mínimos de configuración.')]
    return H


def main():
    temporal = SALIDA.replace('.pdf', '_tmp.pdf')
    doc = Documento(temporal, TITULO)
    toc = TableOfContents()
    toc.levelStyles = toc_estilos
    toc.dotsMinLevel = 0
    historia = portada(TITULO) + [Paragraph('Índice', h1), toc, PageBreak()] + construir()
    doc.multiBuild(historia, canvasmaker=canvas_numerado(TITULO))
    os.replace(temporal, SALIDA)
    print('Generado:', SALIDA)


if __name__ == '__main__':
    main()
