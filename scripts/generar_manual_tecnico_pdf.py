"""Genera el manual técnico de SINAC NEXT.

Las tablas de rutas de la API, módulos y componentes se obtienen del código fuente al momento de generar el documento.
"""
import ast
import json
import math
import os
import re
import sys

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import PageBreak, Paragraph, Preformatted, Spacer, Table, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import ParagraphStyle

from plantilla_cinvestav import (
    ANCHO_UTIL, BORDE, GRIS, GRIS_CLARO, RAIZ, VERDE, VERDE_CLARO, VERDE_OSCURO,
    DiagramaAjustado, Documento, canvas_numerado, celda, cuerpo, envolver, h1, h2, pie_fig,
    portada, tabla, texto_centrado, titulo, toc_estilos, vineta,
)

TITULO = 'Manual Técnico'
SALIDA = os.path.join(RAIZ, 'docs', 'SINAC_NEXT_Manual_Tecnico.pdf')
BACKEND = os.path.join(RAIZ, 'backend')
APP = os.path.join(BACKEND, 'preregistro')
COMPONENTES = os.path.join(RAIZ, 'frontend', 'src', 'components')

nota_estilo = celda.clone('nota', fontSize=9.5, leading=13)
codigo_estilo = ParagraphStyle('codigo', fontName='Courier', fontSize=8.3, leading=10.8, textColor=colors.HexColor('#1F2A33'))
celda_peq = celda.clone('celda_peq', fontSize=8, leading=10.2)
celda_peq_cab = celda_peq.clone('celda_peq_cab', fontName='Arial-Bold', textColor=colors.white)


class Contador:
    figura = 0


# --------------------------------------------------------------------------------------------
# Utilidades de maquetación
# --------------------------------------------------------------------------------------------

def p(texto):
    return Paragraph(texto, cuerpo)


def vinetas(lista):
    return [Paragraph(x, vineta, bulletText='•') for x in lista]


def pasos(lista):
    return [Paragraph(x, vineta, bulletText=f'{i}.') for i, x in enumerate(lista, 1)]


def nota(texto, etiqueta='Nota'):
    t = Table([[Paragraph(f'<b>{etiqueta}:</b> {texto}', nota_estilo)]], colWidths=[ANCHO_UTIL])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), VERDE_CLARO),
        ('LINEBEFORE', (0, 0), (0, -1), 3, VERDE),
        ('LEFTPADDING', (0, 0), (-1, -1), 9), ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return [t, Spacer(1, 8)]


def codigo(texto):
    t = Table([[Preformatted(texto.strip('\n'), codigo_estilo)]], colWidths=[ANCHO_UTIL])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), GRIS_CLARO),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDE),
        ('LEFTPADDING', (0, 0), (-1, -1), 8), ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return [t, Spacer(1, 8)]


def tabla_peq(datos, anchos):
    t = tabla(datos, anchos, estilo_celda=celda_peq)
    t._cellvalues[0] = [Paragraph(c.text if hasattr(c, 'text') else str(c), celda_peq_cab) for c in t._cellvalues[0]]
    return t


def figura(dibujo, pie, alto_maximo=None):
    Contador.figura += 1
    return [DiagramaAjustado(dibujo, alto_maximo=alto_maximo), Paragraph(f'Figura {Contador.figura}. {pie}', pie_fig)]


def ruta_rel(ruta):
    return os.path.relpath(ruta, RAIZ).replace('\\', '/')


def lineas(ruta):
    with open(ruta, encoding='utf-8', errors='ignore') as f:
        return sum(1 for _ in f)


# --------------------------------------------------------------------------------------------
# Extracción de información del código fuente
# --------------------------------------------------------------------------------------------

METODOS_HTTP = ('get', 'post', 'put', 'patch', 'delete')
METODOS_GENERICOS = {
    'ListAPIView': ['GET'], 'CreateAPIView': ['POST'], 'ListCreateAPIView': ['GET', 'POST'],
    'RetrieveAPIView': ['GET'], 'RetrieveUpdateAPIView': ['GET', 'PUT', 'PATCH'],
    'RetrieveUpdateDestroyAPIView': ['GET', 'PUT', 'PATCH', 'DELETE'], 'TokenRefreshView': ['POST'],
    'TokenObtainPairView': ['POST'],
}


def vistas_backend():
    vistas = {}
    for nombre in sorted(os.listdir(APP)):
        if not nombre.endswith('.py'):
            continue
        with open(os.path.join(APP, nombre), encoding='utf-8') as f:
            arbol = ast.parse(f.read())
        for nodo in arbol.body:
            if not isinstance(nodo, ast.ClassDef):
                continue
            metodos = [n.name.upper() for n in nodo.body if isinstance(n, ast.FunctionDef) and n.name in METODOS_HTTP]
            bases = [b.attr if isinstance(b, ast.Attribute) else getattr(b, 'id', '') for b in nodo.bases]
            for base in bases:
                metodos += [m for m in METODOS_GENERICOS.get(base, []) if m not in metodos]
            vistas[nodo.name] = {'modulo': nombre, 'metodos': metodos, 'bases': bases}
    for nombre, datos in vistas.items():
        if not datos['metodos']:
            for base in datos['bases']:
                if base in vistas and vistas[base]['metodos']:
                    datos['metodos'] = vistas[base]['metodos']
    return vistas


def rutas_api():
    with open(os.path.join(APP, 'urls.py'), encoding='utf-8') as f:
        texto = f.read()
    vistas = vistas_backend()
    orden = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
    rutas = []
    for ruta, vista in re.findall(r"path\(\s*'([^']*)'\s*,\s*(\w+)\.as_view\(", texto):
        info = vistas.get(vista, {'modulo': '?', 'metodos': []})
        metodos = sorted(set(info['metodos']), key=orden.index)
        rutas.append({'ruta': '/api/' + ruta, 'vista': vista, 'modulo': info['modulo'], 'metodos': metodos})
    return rutas


def componentes_frontend():
    return sorted(n for n in os.listdir(COMPONENTES) if n.endswith('.js'))


# --------------------------------------------------------------------------------------------
# Diagramas
# --------------------------------------------------------------------------------------------

def caja(d, x, y, w, h, lineas_txt, relleno=VERDE_CLARO, borde=VERDE_OSCURO, titulo_color=VERDE_OSCURO, tam=7.6, discontinua=False):
    r = Rect(x, y, w, h, rx=5, ry=5, fillColor=relleno, strokeColor=borde, strokeWidth=1)
    if discontinua:
        r.strokeDashArray = [4, 3]
    d.add(r)
    alto = tam + 2
    total = len(lineas_txt) * alto
    inicio = y + h / 2 + total / 2 - tam
    for i, linea in enumerate(lineas_txt):
        fuente = 'Arial-Bold' if i == 0 else 'Arial'
        color = titulo_color if i == 0 else colors.HexColor('#1F2A33')
        d.add(String(x + w / 2, inicio - i * alto, linea, fontName=fuente, fontSize=tam if i else tam + 0.4,
                     fillColor=color, textAnchor='middle'))


def flecha(d, puntos, etiqueta=None, pos_etiqueta=None, doble=False, color=GRIS):
    for (x1, y1), (x2, y2) in zip(puntos, puntos[1:]):
        d.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=1))

    def punta(a, b):
        (x1, y1), (x2, y2) = a, b
        ang = math.atan2(y2 - y1, x2 - x1)
        largo, abre = 6, 0.42
        d.add(Polygon([x2, y2,
                       x2 - largo * math.cos(ang - abre), y2 - largo * math.sin(ang - abre),
                       x2 - largo * math.cos(ang + abre), y2 - largo * math.sin(ang + abre)],
                      fillColor=color, strokeColor=color, strokeWidth=0.5))

    punta(puntos[-2], puntos[-1])
    if doble:
        punta(puntos[1], puntos[0])
    if etiqueta:
        x, y = pos_etiqueta
        for i, linea in enumerate(etiqueta.split('\n')):
            d.add(String(x, y - i * 8.5, linea, fontName='Arial-Italic', fontSize=6.8, fillColor=GRIS, textAnchor='middle'))


def diagrama_despliegue():
    d = Drawing(490, 360)
    # Servidor Docker
    host = Rect(112, 30, 290, 300, rx=8, ry=8, fillColor=colors.HexColor('#FAFCFB'), strokeColor=VERDE, strokeWidth=1.2)
    host.strokeDashArray = [5, 3]
    d.add(host)
    d.add(String(257, 318, 'Servidor de aplicación · Docker Compose', fontName='Arial-Bold', fontSize=8.5,
                 fillColor=VERDE_OSCURO, textAnchor='middle'))

    caja(d, 6, 196, 84, 58, ['Navegador web', 'SPA React', '(usuarios por rol)'], relleno=colors.white)
    caja(d, 126, 242, 112, 62, ['sinac-frontend', 'nginx (alpine)', 'build de React', ':80 → host :3000'])
    caja(d, 126, 140, 112, 64, ['sinac-backend', 'Django 5 + DRF', 'Gunicorn / runserver', '127.0.0.1:8000'])
    caja(d, 126, 44, 112, 50, ['sinac-alertas', 'generar_alertas_', 'automatizadas (cada hora)'])
    caja(d, 274, 242, 116, 62, ['camunda (LIDA)', 'Camunda BPM Platform', 'REST /engine-rest', '127.0.0.1:8081'])
    caja(d, 274, 140, 116, 64, ['camunda-postgres', 'PostgreSQL 15', 'volumen postgres_data', '127.0.0.1:5433'])
    caja(d, 274, 44, 116, 50, ['documentos_media', 'volumen Docker', '/app/media (expedientes)'], relleno=GRIS_CLARO, borde=GRIS, titulo_color=GRIS)
    caja(d, 414, 222, 72, 52, ['Jitsi Meet', 'meet.jit.si', '(externo)'], relleno=colors.white, borde=GRIS, titulo_color=GRIS, discontinua=True)
    caja(d, 414, 44, 72, 50, ['Servidor', 'SMTP', '(externo)'], relleno=colors.white, borde=GRIS, titulo_color=GRIS, discontinua=True)

    flecha(d, [(90, 236), (126, 268)], 'HTTP(S)\n:3000', (70, 270))
    flecha(d, [(182, 242), (182, 204)], '/api/ · /media/\nproxy_pass', (214, 228))
    flecha(d, [(238, 166), (274, 166)], 'SQL', (256, 170))
    flecha(d, [(238, 192), (274, 258)], 'REST', (250, 230))
    flecha(d, [(332, 242), (332, 204)], 'JDBC', (346, 222))
    flecha(d, [(238, 76), (256, 76), (256, 150), (274, 150)], 'SQL', (247, 80))
    flecha(d, [(220, 140), (300, 94)], 'archivos', (282, 120))
    flecha(d, [(160, 140), (160, 118), (450, 118), (450, 94)], 'correo (send_mail)', (420, 122))
    flecha(d, [(48, 254), (48, 344), (450, 344), (450, 274)], 'videollamada (enlace generado por el backend)', (250, 348))
    return d


def diagrama_capas(capas, ancho=490, titulo_ancho=96, alto_item=22, por_fila=4, lateral=None, flechas=True):
    """Bandas horizontales con los módulos de cada capa; la primera capa queda arriba."""
    ancho_items = ancho - titulo_ancho - 14 - (110 if lateral else 0)
    filas_por_capa = [max(1, -(-len(items) // por_fila)) for _, items in capas]
    sep = 12
    alto_capas = [f * (alto_item + 6) + 8 for f in filas_por_capa]
    alto_total = sum(alto_capas) + sep * (len(capas) - 1) + 10
    d = Drawing(ancho, alto_total)
    y = alto_total - 5
    centros = []
    for (nombre, items), alto in zip(capas, alto_capas):
        y -= alto
        d.add(Rect(0, y, ancho - (110 if lateral else 0), alto, rx=6, ry=6, fillColor=colors.HexColor('#FAFCFB'), strokeColor=BORDE, strokeWidth=0.8))
        d.add(Rect(0, y, titulo_ancho, alto, rx=6, ry=6, fillColor=VERDE, strokeColor=VERDE, strokeWidth=0.8))
        texto_centrado(d, titulo_ancho / 2, y + alto / 2, envolver(nombre, 'Arial-Bold', 8, titulo_ancho - 10), 'Arial-Bold', 8, colors.white)
        w_item = (ancho_items - (por_fila - 1) * 6) / por_fila
        for i, item in enumerate(items):
            fila, col = divmod(i, por_fila)
            x = titulo_ancho + 8 + col * (w_item + 6)
            yi = y + alto - 6 - (fila + 1) * (alto_item + 6) + 6
            d.add(Rect(x, yi, w_item, alto_item, rx=3, ry=3, fillColor=VERDE_CLARO, strokeColor=VERDE_OSCURO, strokeWidth=0.6))
            tam = 7.2
            while max(stringWidth(t, 'Arial', tam) for t in envolver(item, 'Arial', tam, w_item - 6)) > w_item - 6:
                tam -= 0.2
            texto_centrado(d, x + w_item / 2, yi + alto_item / 2, envolver(item, 'Arial', tam, w_item - 6)[:2], 'Arial', tam)
        centros.append(y + alto / 2)
        y -= sep
    for i in range(len(capas) - 1 if flechas else 0):
        ya = centros[i] - alto_capas[i] / 2
        flecha(d, [(titulo_ancho / 2, ya), (titulo_ancho / 2, ya - sep)], color=VERDE_OSCURO)
    if lateral:
        nombre, items = lateral
        x0 = ancho - 102
        d.add(Rect(x0, 5, 102, alto_total - 10, rx=6, ry=6, fillColor=colors.white, strokeColor=GRIS, strokeWidth=0.8))
        d.add(String(x0 + 51, alto_total - 22, nombre, fontName='Arial-Bold', fontSize=8, fillColor=GRIS, textAnchor='middle'))
        paso = (alto_total - 50) / len(items)
        for i, item in enumerate(items):
            yi = alto_total - 40 - (i + 1) * paso + paso / 2 - 12
            d.add(Rect(x0 + 6, yi, 90, 26, rx=3, ry=3, fillColor=GRIS_CLARO, strokeColor=GRIS, strokeWidth=0.6))
            texto_centrado(d, x0 + 51, yi + 13, envolver(item, 'Arial', 7, 84)[:2], 'Arial', 7)
    return d


def diagrama_peticion():
    d = Drawing(490, 98)
    etapas = [
        ['Navegador', 'fetch() con', 'Authorization: Bearer'],
        ['nginx', 'cabeceras, límite', 'de peticiones, proxy'],
        ['Django', 'middleware de', 'seguridad y sesión'],
        ['DRF', 'JWT + throttling', '+ permisos por rol'],
        ['Vista APIView', 'reglas de negocio', 'y serializador'],
        ['ORM / LIDA', 'PostgreSQL y', 'Camunda REST'],
    ]
    w, sep = 70, 13.5
    for i, etapa in enumerate(etapas):
        x = 4 + i * (w + sep)
        caja(d, x, 30, w, 62, etapa, tam=7)
        if i:
            flecha(d, [(x - sep, 61), (x, 61)], color=VERDE_OSCURO)
    d.add(String(245, 10, 'La respuesta JSON recorre el camino inverso; los errores se devuelven con {"detail": ...} y código HTTP.',
                 fontName='Arial-Italic', fontSize=7.4, fillColor=GRIS, textAnchor='middle'))
    return d


# --------------------------------------------------------------------------------------------
# Contenido
# --------------------------------------------------------------------------------------------

DESCRIPCION_MODULOS = {
    'views.py': 'Vistas principales: preregistro, inicio de sesión, perfil, documentos, coordinación, inscripciones, cargas académicas y descargas PDF.',
    'servicios_views.py': 'API de Servicios Escolares: alumnos, validación de inscripción, expedientes, solicitudes extemporáneas, oficios y reportes.',
    'models.py': 'Modelo de datos (29 modelos), incluido el usuario personalizado Aspirante.',
    'admin_views.py': 'API del Administrador: usuarios, catálogos, alumnos, docentes, reportes, auditoría y configuración.',
    'serializers.py': 'Serializadores DRF y validaciones de entrada.',
    'docente_views.py': 'API del Docente: materias, calificaciones, actas, exámenes y entrevistas.',
    'tesis_flujo_views.py': 'Flujo de tesis y solicitudes de dirección de tesis.',
    'expediente_central_views.py': 'Expediente centralizado del alumno y su exportación a PDF.',
    'examenes_gestion_views.py': 'Gestión de exámenes de admisión en línea por Coordinación.',
    'historial.py': 'Autenticación JWT con registro de actor y señales que alimentan el historial de cada persona.',
    'jurado_views.py': 'Jurados de proyecto y programación de defensas de tesis.',
    'docentes_views.py': 'Directorio de docentes para Servicios Escolares.',
    'egresados_views.py': 'Registro y consulta de egresados.',
    'predoctoral_views.py': 'Exámenes predoctorales.',
    'tesis_views.py': 'Proyectos de tesis del alumno.',
    'antiplagio_views.py': 'Revisión antiplagio de documentos de tesis.',
    'historico_views.py': 'Consulta del histórico de personas.',
    'director_views.py': 'Panel del Director de tesis.',
    'seguridad.py': 'Validación de archivos, nombres seguros, URLs firmadas de /media/ y neutralización de fórmulas.',
    'urls.py': 'Tabla de rutas de la API REST.',
    'diploma_views.py': 'Generación del diploma digital.',
    'alertas.py': 'Generación idempotente de alertas automatizadas.',
    'admin.py': 'Registro de modelos en el sitio de administración de Django.',
    'configuracion_sistema.py': 'Parámetros configurables (política de contraseñas, bloqueo, notificaciones).',
    'tests.py': 'Pruebas funcionales de la API.',
    'tests_seguridad.py': 'Pruebas de los controles de seguridad.',
    'apps.py': 'Configuración de la aplicación Django.',
    'camunda.py': 'Cliente REST del motor de procesos.',
}

VARIABLES = [
    ['DJANGO_DEBUG', 'false', 'Modo de depuración. En producción debe ser false (usa Gunicorn).'],
    ['DJANGO_SECRET_KEY', '—', 'Clave criptográfica. Obligatoria con DEBUG=false; mínimo 50 caracteres.'],
    ['DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,backend', 'Dominios aceptados por Django, separados por comas.'],
    ['DJANGO_CORS_ORIGINS', 'http://localhost:3000', 'Orígenes autorizados para CORS.'],
    ['DJANGO_CSRF_TRUSTED_ORIGINS', 'igual a CORS', 'Orígenes de confianza para CSRF.'],
    ['DJANGO_HTTPS', 'false', 'Activa cookies seguras, HSTS y redirección cuando hay TLS delante de nginx.'],
    ['DJANGO_SSL_REDIRECT / DJANGO_HSTS_SECONDS / DJANGO_HSTS_SUBDOMAINS', 'derivados de DJANGO_HTTPS', 'Ajuste fino de la redirección HTTPS y de HSTS.'],
    ['DJANGO_NUM_PROXIES', '1', 'Número de proxies inversos para calcular la IP real del cliente.'],
    ['DJANGO_LOG_LEVEL', 'INFO', 'Nivel de los registros enviados a la consola.'],
    ['DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD', 'postgres / 5432 / camunda', 'Conexión de Django con PostgreSQL.'],
    ['POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD', 'camunda', 'Credenciales con las que se inicializa el contenedor de PostgreSQL.'],
    ['CAMUNDA_URL / CAMUNDA_REST_URL', 'http://camunda:8080', 'Dirección del motor de procesos LIDA (Camunda).'],
    ['THROTTLE_ANON / THROTTLE_USER', '120/min · 1200/min', 'Límite de peticiones anónimas y autenticadas.'],
    ['THROTTLE_LOGIN / THROTTLE_REGISTRO / THROTTLE_REFRESH', '10/min · 5/hora · 30/min', 'Límites específicos de inicio de sesión, registro y renovación de token.'],
    ['JWT_ACCESS_MINUTES / JWT_REFRESH_HOURS', '120 / 24', 'Vigencia de los tokens de acceso y renovación.'],
    ['GUNICORN_WORKERS', '3', 'Procesos de Gunicorn en producción.'],
    ['SINAC_ADMIN_PASSWORD', '—', 'Contraseña usada por crear_admin_sinac (solo al ejecutar el comando).'],
    ['SINAC_ALUMNO_PASSWORD / SINAC_DOCENTE_PASSWORD', '—', 'Contraseñas usadas por crear_alumno_sinac y crear_docente_sinac.'],
]

COMANDOS = [
    ['migrate', 'Aplica las migraciones (se ejecuta automáticamente al iniciar el contenedor backend).'],
    ['crear_admin_sinac', 'Crea o actualiza la cuenta «admin». Requiere SINAC_ADMIN_PASSWORD.'],
    ['crear_alumno_sinac / crear_docente_sinac', 'Crea o actualiza cuentas individuales de alumno o docente.'],
    ['cargar_plan_computacion', 'Carga de forma idempotente el catálogo de materias y los planes de Computación.'],
    ['cargar_datos_prueba', 'Carga datos de demostración para todos los paneles. Solo para ambientes de prueba.'],
    ['generar_alertas_automatizadas', 'Genera alertas de bajas, vencimientos, apertura de inscripciones y becas (lo ejecuta el servicio alertas).'],
    ['test preregistro', 'Ejecuta la suite de pruebas automatizadas.'],
]

PROCESOS_BPMN = [
    ['sinac_preregistro_v1', 'sinac_preregistro_v1.bpmn', 'Inicio «Aspirante registrado» → tarea de usuario «Revisión» (grupo coordinacion) → fin.', 'Al crear el preregistro (business key del aspirante).'],
    ['sinac_documentos_v1', 'sinac_documentos_v1.bpmn', 'Validar documentos → compuerta «¿válido?» → aceptado o corrección.', 'Modelo de la revisión documental; desplegado, aún no se inicia desde el backend.'],
    ['sinac_entrevista_v1', 'sinac_entrevista_v1.bpmn', 'Tarea de servicio «Crear sala» → tarea de usuario «Entrevista».', 'Programación de entrevistas virtuales.'],
    ['sinac_examen_v1', 'sinac_examen_v1.bpmn', 'Presentar examen (grupo aspirantes) → tarea de servicio «Evaluar».', 'Modelo del examen en línea; desplegado, aún no se inicia desde el backend.'],
    ['carga_academica', 'carga_academica.bpmn', 'Revisión → compuerta → publicación o «Rechazada».', 'Flujo de aprobación de cargas académicas.'],
]

SEGURIDAD = [
    ['Autenticación', 'JWT (SimpleJWT) con tokens de acceso de 120 min y renovación de 24 h; bloqueo de cuenta tras N intentos fallidos (configurable, 15 min).'],
    ['Autorización', 'Cada vista valida el rol del usuario (campo rol); el frontend además restringe vistas con ROLE_VIEW_ACCESS.'],
    ['Contraseñas', 'Validadores de Django más la política institucional configurable (longitud, mayúscula, minúscula, número).'],
    ['Límite de peticiones', 'DRF throttling por usuario/IP y nginx limit_req (10 r/min en login y registro, 20 r/s en la API) y limit_conn (40).'],
    ['Archivos', 'Se verifica el contenido real (firma %PDF, Pillow para imágenes), la extensión y el tamaño (PDF 10 MB, imagen 5 MB, CSV 2 MB); los nombres se normalizan.'],
    ['Archivos privados', '/media/ solo se sirve con una firma temporal (12 h) generada por url_media(); sin firma la respuesta es 404.'],
    ['Exportaciones', 'celda_segura() antepone un apóstrofo a los valores que inician con = + - @ para evitar inyección de fórmulas en CSV/XLSX.'],
    ['Cabeceras HTTP', 'CSP, X-Frame-Options DENY, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, COOP; HSTS cuando DJANGO_HTTPS=true.'],
    ['Errores', 'Manejadores 400/403/404/500 propios (config/errores.py) que no exponen trazas; nginx entrega páginas y JSON de servicio no disponible.'],
    ['Red', 'PostgreSQL, Camunda y el backend se publican solo en 127.0.0.1; únicamente el frontend (puerto 3000) queda expuesto.'],
    ['Auditoría', 'AuditoriaSistema registra acciones administrativas; HistorialPersona registra cambios por persona con el actor que los realizó.'],
]

PROBLEMAS = [
    ['Todas las peticiones a /api/ devuelven 503 o 502 tras reiniciar el backend.', 'nginx conserva la IP anterior del contenedor backend.', 'docker compose restart frontend'],
    ['El backend no inicia: «DJANGO_SECRET_KEY debe configurarse con al menos 50 caracteres…».', 'DEBUG=false sin clave o con menos de 50 caracteres.', 'Definir DJANGO_SECRET_KEY en el entorno o en .env y volver a levantar el servicio.'],
    ['Error 400 «Bad Request» al acceder por dominio.', 'El dominio no está en DJANGO_ALLOWED_HOSTS.', 'Agregar el dominio a DJANGO_ALLOWED_HOSTS y a DJANGO_CORS_ORIGINS.'],
    ['Respuesta 429 «Too Many Requests».', 'Se alcanzó el límite de peticiones de DRF o de nginx.', 'Esperar el periodo indicado o ajustar THROTTLE_* en un ambiente controlado.'],
    ['El usuario no puede iniciar sesión aunque la contraseña sea correcta.', 'La cuenta está bloqueada por intentos fallidos o inactiva.', 'Esperar 15 min o desbloquear/activar la cuenta desde el panel de Administración.'],
    ['Los enlaces a documentos responden 404.', 'La URL firmada caducó (12 h) o el archivo no existe en el volumen.', 'Volver a abrir el documento desde el panel para obtener una URL nueva.'],
    ['El registro funciona pero aparece un aviso de LIDA en los registros.', 'Camunda no está disponible o el proceso no está desplegado.', 'Verificar docker compose ps, la consola en :8081 y los archivos de camunda/.'],
    ['El puerto 3000, 8000, 5433 u 8081 está ocupado.', 'Otro proceso usa el puerto.', 'Detener el proceso o cambiar el puerto publicado en docker-compose.yml.'],
    ['Error «relation … does not exist».', 'Migraciones pendientes.', 'docker compose exec backend python manage.py migrate'],
    ['No llegan correos.', 'No se configuró un servidor SMTP.', 'Definir EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD y DEFAULT_FROM_EMAIL (sección 11.6).'],
]


def construir():
    rutas = rutas_api()
    componentes = componentes_frontend()
    with open(os.path.join(RAIZ, 'docs', 'assets', 'modelo_datos.json'), encoding='utf-8') as f:
        modelos = json.load(f)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from generar_base_datos_pdf import DESCRIPCION_TABLA

    with open(os.path.join(APP, 'tests.py'), encoding='utf-8') as f:
        n_tests = len(re.findall(r'^\s+def test_', f.read(), re.M))
    with open(os.path.join(APP, 'tests_seguridad.py'), encoding='utf-8') as f:
        n_tests_seg = len(re.findall(r'^\s+def test_', f.read(), re.M))

    H = []

    # 1. Introducción ------------------------------------------------------------------------
    H += [titulo('1. Introducción', h1, 0)]
    H += [p('El presente manual técnico describe la arquitectura, los componentes, la configuración, la instalación y el '
            'mantenimiento de <b>SINAC NEXT</b>, el sistema de información académica del Cinvestav que integra la admisión de '
            'aspirantes, la vida académica de los alumnos, el trabajo docente, la dirección de tesis y los servicios escolares, '
            'con procesos orquestados mediante el Lenguaje Iconográfico (LIDA) implementado sobre Camunda BPM.')]
    H += [titulo('1.1 Objetivo', h2, 1),
          p('Proporcionar al personal técnico la información necesaria para instalar, configurar, operar, respaldar, '
            'diagnosticar y extender el sistema de forma segura y reproducible.')]
    H += [titulo('1.2 Alcance', h2, 1),
          p('El documento cubre los cinco servicios de la solución (frontend, backend, servicio de alertas, base de datos y motor de '
            'procesos), su despliegue con Docker Compose, la API REST, el modelo de datos, la integración con LIDA, los controles '
            'de seguridad, las pruebas automatizadas y los procedimientos de mantenimiento.')]
    H += [titulo('1.3 Audiencia', h2, 1)]
    H += vinetas([
        '<b>Administradores de infraestructura</b>: instalación, variables de entorno, respaldos y monitoreo.',
        '<b>Desarrolladores</b>: estructura del código, API, modelo de datos y convenciones para extender el sistema.',
        '<b>Personal de soporte</b>: solución de problemas frecuentes y comandos de operación.',
    ])
    H += [titulo('1.4 Documentos relacionados', h2, 1)]
    H += [tabla([
        ['Documento', 'Contenido'],
        ['SINAC_NEXT_Casos_de_Uso.pdf', 'Casos de uso generales y específicos por actor.'],
        ['SINAC_NEXT_Base_de_Datos.pdf', 'Diagrama de clases, diagrama entidad-relación y diccionario de datos.'],
        ['SINAC_NEXT_Diagramas_de_Secuencia.pdf', 'Interacción entre usuario, interfaz, API, base de datos y servicios externos.'],
        ['SINAC_NEXT_Manual_de_Usuario.pdf', 'Operación del sistema por cada rol con capturas de pantalla.'],
    ], [6.2 * cm, ANCHO_UTIL - 6.2 * cm]), Spacer(1, 6)]
    H += [titulo('1.5 Convenciones', h2, 1)]
    H += vinetas([
        'Los comandos se muestran en <font face="Courier">fuente monoespaciada</font> y se ejecutan desde la carpeta raíz del proyecto.',
        'Las rutas de la API son relativas al dominio del sistema; todas comienzan con <font face="Courier">/api/</font>.',
        'Los valores entre ángulos, por ejemplo <font face="Courier">&lt;archivo&gt;</font>, deben sustituirse por el valor real.',
    ])
    H += [PageBreak()]

    # 2. Arquitectura -------------------------------------------------------------------------
    H += [titulo('2. Arquitectura del sistema', h1, 0)]
    H += [p('SINAC NEXT sigue una arquitectura cliente-servidor de tres capas desplegada en contenedores. La interfaz es una '
            'aplicación de una sola página (SPA) en React que se comunica exclusivamente con una API REST construida en Django '
            'REST Framework. La API persiste la información en PostgreSQL y delega la orquestación de procesos institucionales '
            'al motor Camunda (LIDA). Un servicio independiente genera alertas periódicas.')]
    H += [titulo('2.1 Diagrama de despliegue', h2, 1)]
    H += figura(diagrama_despliegue(), 'Diagrama de despliegue de SINAC NEXT con Docker Compose.')
    H += [titulo('2.2 Servicios', h2, 1)]
    H += [tabla_peq([
        ['Servicio', 'Contenedor', 'Imagen', 'Puerto', 'Responsabilidad'],
        ['frontend', 'sinac-frontend', 'node:20-alpine → nginx:alpine', '3000 → 80', 'Sirve la SPA compilada y actúa como proxy inverso de /api/ y /media/.'],
        ['backend', 'sinac-backend', 'python:3.12-slim', '127.0.0.1:8000', 'API REST, reglas de negocio, generación de PDF/XLSX y archivos privados.'],
        ['alertas', 'sinac-alertas', 'misma del backend', '—', 'Ejecuta generar_alertas_automatizadas cada 3600 s.'],
        ['postgres', 'camunda-postgres', 'postgres:15', '127.0.0.1:5433', 'Base de datos de SINAC NEXT y de Camunda.'],
        ['camunda', 'camunda', 'camunda-bpm-platform', '127.0.0.1:8081', 'Motor de procesos BPMN (LIDA) y su consola web.'],
    ], [1.7 * cm, 2.5 * cm, 3.4 * cm, 2.4 * cm, ANCHO_UTIL - 10 * cm]), Spacer(1, 6)]
    H += [titulo('2.3 Arquitectura lógica del backend', h2, 1)]
    H += [p('El backend se organiza en capas. Cada petición atraviesa el enrutamiento, la autenticación y los permisos antes de '
            'llegar a la vista, que aplica las reglas de negocio apoyándose en serializadores, validaciones y el ORM de Django.')]
    H += figura(diagrama_capas([
        ('Enrutamiento', ['config/urls.py', 'preregistro/urls.py', f'{len(rutas)} rutas REST', 'servir_media (firmado)']),
        ('Autenticación y control', ['HistorialJWT Authentication', 'Throttling DRF', 'Validación de rol', 'Bloqueo por intentos']),
        ('Vistas (APIView)', ['views.py', 'servicios_views.py', 'docente_views.py', 'admin_views.py', 'director / tesis / jurado',
                              'exámenes y entrevistas', 'egresados / histórico', 'expediente central']),
        ('Validación y serialización', ['serializers.py', 'seguridad.py', 'configuracion_ sistema.py']),
        ('Dominio y persistencia', ['models.py (29 modelos)', 'historial.py (señales)', 'alertas.py', 'migraciones']),
    ], lateral=('Integraciones', ['Camunda REST (LIDA)', 'SMTP (send_mail)', 'reportlab (PDF)', 'openpyxl (XLSX)', 'Jitsi (enlaces)'])),
        'Arquitectura lógica en capas del backend.')
    H += [titulo('2.4 Flujo de una petición', h2, 1)]
    H += figura(diagrama_peticion(), 'Recorrido de una petición autenticada desde el navegador hasta la base de datos.')
    H += [titulo('2.5 Tecnologías y versiones', h2, 1)]
    H += [tabla([
        ['Capa', 'Tecnología', 'Versión', 'Uso'],
        ['Frontend', 'React / react-dom', '18.3.1', 'Interfaz de usuario SPA.'],
        ['Frontend', 'react-scripts (Create React App)', '5.0.1', 'Compilación y servidor de desarrollo.'],
        ['Frontend', 'Node.js', '20 (alpine)', 'Etapa de compilación de la imagen.'],
        ['Servidor web', 'nginx', 'alpine', 'Archivos estáticos, proxy inverso, cabeceras y límites.'],
        ['Backend', 'Python', '3.12', 'Lenguaje del backend.'],
        ['Backend', 'Django', '5.0.6', 'Framework web, ORM y migraciones.'],
        ['Backend', 'Django REST Framework', '3.15.2', 'API REST, serialización y throttling.'],
        ['Backend', 'djangorestframework-simplejwt', '5.3.1', 'Autenticación con JSON Web Tokens.'],
        ['Backend', 'django-cors-headers', '4.4.0', 'Política CORS.'],
        ['Backend', 'psycopg', '3.2.13', 'Controlador de PostgreSQL.'],
        ['Backend', 'reportlab / openpyxl / Pillow', '4.2.2 / 3.1.5 / 11.3.0', 'PDF, hojas de cálculo e imágenes.'],
        ['Backend', 'requests', '—', 'Cliente HTTP hacia Camunda.'],
        ['Backend', 'Gunicorn', '23.0.0', 'Servidor WSGI de producción.'],
        ['Datos', 'PostgreSQL', '15', 'Base de datos relacional.'],
        ['Procesos', 'Camunda BPM Platform', 'latest', 'Motor BPMN que implementa LIDA.'],
        ['Infraestructura', 'Docker / Docker Compose', 'Compose v2', 'Contenedores y orquestación.'],
    ], [2.5 * cm, 5.2 * cm, 3.3 * cm, ANCHO_UTIL - 11 * cm]), Spacer(1, 6)]
    H += [PageBreak()]

    # 3. Estructura -------------------------------------------------------------------------
    H += [titulo('3. Estructura del proyecto', h1, 0)]
    H += [titulo('3.1 Árbol de directorios', h2, 1)]
    H += codigo('''
Sistema SINAC NEXT/
├── docker-compose.yml        Orquestación de los cinco servicios
├── .env.example              Plantilla de variables de entorno
├── backend/
│   ├── Dockerfile            Imagen python:3.12-slim
│   ├── requirements.txt      Dependencias de Python
│   ├── manage.py
│   ├── config/               Proyecto Django (settings, urls, wsgi, errores)
│   ├── preregistro/          Aplicación principal: modelos, vistas, API, pruebas
│   │   ├── management/commands/   Comandos de administración
│   │   └── migrations/            Migraciones del esquema
│   └── templates/errors/     Plantilla HTML de errores
├── frontend/
│   ├── Dockerfile            Compilación con Node 20 y despliegue en nginx
│   ├── nginx.conf            Servidor web y proxy inverso
│   ├── sinac-proxy.inc       Parámetros comunes de proxy
│   ├── public/               index.html y página de servicio no disponible
│   └── src/
│       ├── App.js            Navegación por estado, sesión y roles
│       ├── translations.js   Textos generales en cinco idiomas
│       └── components/       Paneles por rol y componentes compartidos
├── camunda/                  Procesos BPMN (LIDA)
├── tests/smoke_test.py       Prueba de humo de los servicios
├── scripts/                  Generadores de la documentación PDF
└── docs/                     Documentación del proyecto
''')
    H += [titulo('3.2 Módulos del backend', h2, 1)]
    H += [p('La lógica del sistema reside en la aplicación Django <font face="Courier">preregistro</font>. La siguiente tabla '
            'resume sus módulos y su tamaño aproximado en líneas de código.')]
    filas = [['Módulo', 'Líneas', 'Responsabilidad']]
    for nombre in sorted((n for n in os.listdir(APP) if n.endswith('.py') and n != '__init__.py'),
                         key=lambda n: -lineas(os.path.join(APP, n))):
        filas.append([nombre, str(lineas(os.path.join(APP, nombre))), DESCRIPCION_MODULOS.get(nombre, '—')])
    H += [tabla_peq(filas, [4.3 * cm, 1.4 * cm, ANCHO_UTIL - 5.7 * cm]), Spacer(1, 6)]
    H += [p('El proyecto <font face="Courier">config</font> contiene <font face="Courier">settings.py</font> (configuración '
            'leída de variables de entorno), <font face="Courier">urls.py</font> (rutas raíz: <font face="Courier">admin/</font>, '
            '<font face="Courier">health/</font>, <font face="Courier">api/</font> y <font face="Courier">media/</font>), '
            '<font face="Courier">errores.py</font> (manejadores 400, 403, 404 y 500) y <font face="Courier">wsgi.py</font>.')]
    H += [titulo('3.3 Componentes del frontend', h2, 1)]
    H += [p(f'La carpeta <font face="Courier">frontend/src/components</font> contiene {len(componentes)} módulos JavaScript. '
            'Se agrupan de la siguiente forma:')]
    paneles = [c for c in componentes if c.startswith('Panel')]
    traducciones = [c for c in componentes if 'Translations' in c]
    otros = [c for c in componentes if c not in paneles and c not in traducciones]
    H += [tabla_peq([
        ['Grupo', 'Archivos'],
        ['Paneles por rol', ', '.join(c[:-3] for c in paneles)],
        ['Traducciones por panel', ', '.join(c[:-3] for c in traducciones)],
        ['Componentes compartidos y vistas públicas', ', '.join(c[:-3] for c in otros)],
    ], [4.2 * cm, ANCHO_UTIL - 4.2 * cm]), Spacer(1, 6)]
    H += [PageBreak()]

    # 4. Instalación ---------------------------------------------------------------------------
    H += [titulo('4. Instalación y despliegue', h1, 0)]
    H += [titulo('4.1 Requisitos', h2, 1)]
    H += [tabla([
        ['Recurso', 'Mínimo recomendado'],
        ['Sistema operativo', 'Linux (Ubuntu 22.04 o superior) o Windows 10/11 con Docker Desktop (WSL 2).'],
        ['Software', 'Docker Engine 24 o superior y Docker Compose v2; Git para obtener el código.'],
        ['Hardware', '4 núcleos, 8 GB de RAM (Camunda requiere ~1 GB) y 20 GB de disco libres.'],
        ['Red', 'Puerto 3000 (o 80/443 si se coloca un proxy TLS delante) accesible para los usuarios; salida a Internet para Jitsi y SMTP.'],
    ], [3.5 * cm, ANCHO_UTIL - 3.5 * cm]), Spacer(1, 6)]
    H += [titulo('4.2 Instalación en ambiente de desarrollo', h2, 1)]
    H += pasos([
        'Obtener el código fuente y ubicarse en la carpeta raíz del proyecto.',
        'Copiar <font face="Courier">.env.example</font> como <font face="Courier">.env</font> y, para desarrollo, '
        'establecer <font face="Courier">DJANGO_DEBUG=true</font> y una contraseña para PostgreSQL.',
        'Construir y levantar los servicios.',
        'Crear la cuenta administradora y, opcionalmente, cargar el plan de estudios y los datos de demostración.',
        'Abrir <font face="Courier">http://localhost:3000</font> e iniciar sesión.',
    ])
    H += codigo('''
docker compose up -d --build
docker compose ps
docker compose exec -e SINAC_ADMIN_PASSWORD=<contraseña> backend python manage.py crear_admin_sinac
docker compose exec backend python manage.py cargar_plan_computacion
docker compose exec backend python manage.py cargar_datos_prueba      # solo pruebas
''')
    H += nota('Las migraciones se aplican automáticamente cada vez que inicia el contenedor backend. Con '
              '<font face="Courier">DJANGO_DEBUG=true</font> el backend usa el servidor de desarrollo de Django; con '
              '<font face="Courier">false</font> usa Gunicorn.')
    H += [titulo('4.3 Ejecución sin Docker (desarrollo local)', h2, 1)]
    H += [p('Para depurar el código puede ejecutarse cada parte por separado, conservando PostgreSQL y Camunda en contenedores.')]
    H += codigo('''
docker compose up -d postgres camunda
cd backend
python -m venv .venv && .venv\\Scripts\\activate        # Linux: source .venv/bin/activate
pip install -r requirements.txt
set DJANGO_DEBUG=true & set DB_HOST=localhost & set DB_PORT=5433
python manage.py migrate
python manage.py runserver 8000
cd ..\\frontend
npm install
npm start          # http://localhost:3000, con proxy a http://localhost:8000
''')
    H += [titulo('4.4 Despliegue en producción', h2, 1)]
    H += [p('En producción se recomienda colocar un proxy con certificado TLS (por ejemplo, nginx o el balanceador institucional) '
            'delante del puerto 3000 y aplicar la siguiente lista de verificación:')]
    H += vinetas([
        '<font face="Courier">DJANGO_DEBUG=false</font> y <font face="Courier">DJANGO_SECRET_KEY</font> aleatoria de al menos 50 caracteres: '
        '<font face="Courier">python -c "import secrets; print(secrets.token_urlsafe(64))"</font>.',
        '<font face="Courier">DJANGO_ALLOWED_HOSTS</font>, <font face="Courier">DJANGO_CORS_ORIGINS</font> y '
        '<font face="Courier">DJANGO_CSRF_TRUSTED_ORIGINS</font> con el dominio institucional.',
        '<font face="Courier">DJANGO_HTTPS=true</font> para activar cookies seguras, redirección a HTTPS y HSTS.',
        'Contraseña robusta en <font face="Courier">POSTGRES_PASSWORD</font> antes del primer arranque (el volumen conserva la contraseña inicial).',
        'Ajustar <font face="Courier">GUNICORN_WORKERS</font> (regla práctica: 2 × núcleos + 1).',
        'Fijar una versión concreta de la imagen de Camunda en lugar de <font face="Courier">latest</font>.',
        'No ejecutar <font face="Courier">cargar_datos_prueba</font> y programar respaldos (capítulo 10).',
    ])
    H += nota('El archivo <font face="Courier">.env</font> contiene secretos: no debe incluirse en el repositorio ni compartirse. '
              'Está excluido mediante <font face="Courier">.gitignore</font>.', 'Importante')
    H += [titulo('4.5 Verificación de la instalación', h2, 1)]
    H += codigo('''
curl http://localhost:8000/health/          # {"status": "ok", ...}
python tests/smoke_test.py                   # backend, frontend y Camunda
docker compose logs -f backend               # registros en tiempo real
''')
    H += [PageBreak()]

    # 5. Configuración -----------------------------------------------------------------------------
    H += [titulo('5. Configuración', h1, 0)]
    H += [p('Toda la configuración se toma de variables de entorno, que Docker Compose obtiene del archivo '
            '<font face="Courier">.env</font> o del entorno del proceso. El bloque <font face="Courier">x-backend-env</font> de '
            '<font face="Courier">docker-compose.yml</font> comparte las mismas variables entre los servicios backend y alertas.')]
    H += [titulo('5.1 Variables de entorno', h2, 1)]
    H += [tabla_peq([['Variable', 'Valor por defecto', 'Descripción']] + VARIABLES,
                    [5.8 * cm, 3.6 * cm, ANCHO_UTIL - 9.4 * cm]), Spacer(1, 6)]
    H += [titulo('5.2 Parámetros relevantes de settings.py', h2, 1)]
    H += [tabla([
        ['Parámetro', 'Valor'],
        ['AUTH_USER_MODEL', 'preregistro.Aspirante (usuario único para todos los roles, distinguidos por el campo rol).'],
        ['Idioma y zona horaria', 'es-mx, America/Mexico_City.'],
        ['Sesión de Django', '8 horas; cookies HttpOnly y SameSite=Lax (Secure con HTTPS).'],
        ['Carga de archivos', 'Hasta 5 MB en memoria; permisos de archivo 0640; nginx acepta cuerpos de hasta 10 MB.'],
        ['DRF', 'Autenticación HistorialJWTAuthentication, permiso por defecto IsAuthenticated y throttling por ámbito.'],
        ['Registros (logging)', 'Salida a consola con nivel DJANGO_LOG_LEVEL; se consultan con docker compose logs.'],
        ['Middleware propio', 'preregistro.historial.limpiar_actor_middleware (limpia el actor de la petición para el historial).'],
    ], [4.2 * cm, ANCHO_UTIL - 4.2 * cm]), Spacer(1, 6)]
    H += [titulo('5.3 Configuración funcional desde la aplicación', h2, 1)]
    H += [p('Algunos parámetros se almacenan en la tabla ConfiguracionSistema y se modifican desde el panel de Administración, '
            'sin reiniciar servicios. Si no existe un valor guardado se usa el valor por defecto:')]
    H += [tabla([
        ['Clave', 'Valor por defecto', 'Efecto'],
        ['politica_password', '8 caracteres, mayúscula, minúscula y número', 'Reglas aplicadas al crear o cambiar contraseñas.'],
        ['bloqueo_intentos', '5', 'Intentos fallidos antes de bloquear la cuenta 15 minutos (1 a 20).'],
        ['notificaciones_activas', 'true', 'Habilita el envío de correos de notificación.'],
        ['nombre_sistema / campus / correo_soporte / zona_horaria', 'SINAC NEXT / Unidad Zacatenco / …', 'Datos institucionales mostrados en la interfaz.'],
    ], [4.6 * cm, 4.8 * cm, ANCHO_UTIL - 9.4 * cm]), Spacer(1, 6)]
    H += [PageBreak()]

    # 6. Backend ---------------------------------------------------------------------------------
    H += [titulo('6. Backend', h1, 0)]
    H += [titulo('6.1 Modelo de datos', h2, 1)]
    H += [p(f'El esquema está compuesto por {len(modelos)} modelos de Django gestionados mediante migraciones. El detalle de '
            'atributos, relaciones y restricciones se encuentra en el documento de Base de Datos; aquí se presenta un resumen.')]
    H += [p('Todas las tablas llevan el prefijo <font face="Courier">preregistro_</font>, que se omite en la columna «Tabla».')]
    filas = [['Modelo', 'Tabla', 'Campos', 'Descripción']]
    for m in modelos:
        desc = DESCRIPCION_TABLA.get(m['modelo'], m.get('descripcion') or '')
        desc = desc.split('. ')[0].rstrip('.') + '.'
        filas.append([m['modelo'], m['tabla'].replace('preregistro_', '', 1), str(len(m['campos'])), desc])
    H += [tabla_peq(filas, [4 * cm, 4.6 * cm, 1.4 * cm, ANCHO_UTIL - 10 * cm]), Spacer(1, 6)]
    H += [titulo('6.2 Autenticación y roles', h2, 1)]
    H += vinetas([
        '<b>Inicio de sesión</b>: <font face="Courier">POST /api/auth/login/</font> recibe usuario o correo y contraseña y devuelve '
        '<font face="Courier">access</font>, <font face="Courier">refresh</font> y <font face="Courier">rol</font>. Los intentos '
        'fallidos se cuentan por cuenta y la bloquean al alcanzar el límite configurado.',
        '<b>Renovación</b>: <font face="Courier">POST /api/auth/refresh/</font> emite un nuevo token de acceso.',
        '<b>Peticiones</b>: el cliente envía <font face="Courier">Authorization: Bearer &lt;access&gt;</font>. '
        '<font face="Courier">HistorialJWTAuthentication</font> valida el token y registra al usuario como actor de los cambios.',
        '<b>Roles</b>: aspirante, alumno, docente, investigador, director, coordinacion, servicios y admin. Cada vista verifica el '
        'rol requerido y responde 403 si no corresponde.',
        '<b>Registro público</b>: <font face="Courier">POST /api/preregistro/</font> crea siempre cuentas con rol aspirante; los '
        'campos de rol y privilegios se ignoran.',
    ])
    H += [titulo('6.3 Servicios transversales', h2, 1)]
    H += [tabla([
        ['Servicio', 'Implementación'],
        ['Historial por persona', 'historial.py conecta señales pre_save/post_save/post_delete a los modelos relevantes y guarda en HistorialPersona el campo, valor anterior, valor nuevo, categoría y actor.'],
        ['Auditoría', 'AuditoriaSistema registra acciones administrativas (altas, bajas, cambios de configuración) consultables en el panel de Administración.'],
        ['Notificaciones', 'SeguimientoSolicitud almacena avisos por persona; la campana del frontend los consulta y marca como leídos. Los correos usan send_mail.'],
        ['Documentos PDF', 'reportlab genera horarios, boletas, oficios, actas, expediente centralizado y diploma digital.'],
        ['Hojas de cálculo', 'openpyxl y csv exportan reportes; los valores pasan por celda_segura().'],
        ['Archivos privados', 'Los serializadores devuelven URLs firmadas con url_media(); servir_media() valida la firma y la ruta con safe_join.'],
        ['Alertas', 'alertas.py crea avisos idempotentes de baja, vencimiento y apertura de inscripción y estado de becas.'],
        ['Errores', 'config/errores.py devuelve JSON para /api/ y la plantilla errors/error.html para el resto, sin trazas internas.'],
    ], [3.6 * cm, ANCHO_UTIL - 3.6 * cm]), Spacer(1, 6)]
    H += [titulo('6.4 API REST', h2, 1)]
    H += [p(f'La API expone {len(rutas)} rutas bajo <font face="Courier">/api/</font>. Todas requieren token salvo el inicio de '
            'sesión, la renovación y el preregistro. Las respuestas son JSON salvo las descargas (PDF, XLSX, CSV). Además existe '
            '<font face="Courier">GET /health/</font> para el monitoreo.')]
    grupos = {}
    for r in rutas:
        grupo = r['ruta'].split('/')[2] or 'raíz'
        grupos.setdefault(grupo, []).append(r)
    filas = [['Ruta', 'Métodos', 'Vista', 'Módulo']]
    estilos_grupo = []
    for grupo in sorted(grupos):
        filas.append([f'<b>{grupo}</b>', '', '', ''])
        estilos_grupo.append(len(filas) - 1)
        for r in grupos[grupo]:
            ruta = r['ruta'].replace('<', '&lt;').replace('>', '&gt;')
            filas.append([f'<font face="Courier" size="7.2">{ruta}</font>', ', '.join(r['metodos']) or '—', r['vista'], r['modulo']])
    t = tabla_peq(filas, [7.4 * cm, 2.3 * cm, 4.6 * cm, ANCHO_UTIL - 14.3 * cm])
    t.setStyle(TableStyle([cmd for i in estilos_grupo for cmd in (
        ('SPAN', (0, i), (-1, i)), ('BACKGROUND', (0, i), (-1, i), VERDE_CLARO))]))
    H += [t, Spacer(1, 6)]
    H += [titulo('6.5 Convenciones para extender la API', h2, 1)]
    H += pasos([
        'Definir o ajustar el modelo en <font face="Courier">models.py</font> y generar la migración con '
        '<font face="Courier">python manage.py makemigrations preregistro</font>.',
        'Crear el serializador y validar archivos con las funciones de <font face="Courier">seguridad.py</font>.',
        'Implementar la vista como <font face="Courier">APIView</font>, verificando el rol al inicio de cada método.',
        'Registrar la ruta en <font face="Courier">preregistro/urls.py</font>.',
        'Agregar pruebas en <font face="Courier">tests.py</font> y ejecutar la suite completa.',
        'Consumir el endpoint desde el panel correspondiente y agregar los textos en su archivo de traducciones.',
    ])
    H += [PageBreak()]

    # 7. LIDA ----------------------------------------------------------------------------------------
    H += [titulo('7. Integración con LIDA (Camunda)', h1, 0)]
    H += [p('Los procesos institucionales se modelan en BPMN 2.0 con el Lenguaje Iconográfico (LIDA) y se ejecutan en Camunda BPM. '
            'La carpeta <font face="Courier">camunda/</font> se monta en <font face="Courier">/camunda/configuration/resources</font>, '
            'por lo que Camunda despliega automáticamente los archivos .bpmn al iniciar.')]
    H += [titulo('7.1 Procesos desplegados', h2, 1)]
    H += [tabla_peq([['Clave del proceso', 'Archivo', 'Flujo', 'Uso en SINAC NEXT']] + PROCESOS_BPMN,
                    [3.3 * cm, 3.6 * cm, 5.4 * cm, ANCHO_UTIL - 12.3 * cm]), Spacer(1, 6)]
    H += [titulo('7.2 Comunicación', h2, 1)]
    H += [p('El backend usa la API REST de Camunda (<font face="Courier">&lt;CAMUNDA_REST_URL&gt;/engine-rest</font>; la función '
            '<font face="Courier">_camunda_rest_url()</font> acepta la URL con o sin ese sufijo) mediante la biblioteca requests, '
            'con tiempos de espera de 4 a 8 segundos:')]
    H += [tabla([
        ['Operación', 'Petición', 'Origen'],
        ['Iniciar preregistro', 'POST /process-definition/key/sinac_preregistro_v1/start', 'views.py, al registrar un aspirante.'],
        ['Notificar documento', 'POST /message (DocumentoCargado)', 'views.py, al cargar un documento.'],
        ['Iniciar carga académica', 'POST /process-definition/key/carga_academica/start', 'views.py, flujo de cargas académicas.'],
        ['Completar revisión', 'GET /task y POST /task/{id}/complete', 'views.py, aprobación o rechazo de la carga.'],
        ['Iniciar entrevista', 'POST /process-definition/key/sinac_entrevista_v1/start', 'docente_views.py, al programar una entrevista.'],
    ], [3.6 * cm, 7.4 * cm, ANCHO_UTIL - 11 * cm], estilo_celda=celda_peq), Spacer(1, 6)]
    H += [p('Si Camunda no responde, la operación académica no se interrumpe: el backend registra una advertencia y continúa, '
            'de modo que la información queda guardada en PostgreSQL.')]
    H += [titulo('7.3 Administración de procesos', h2, 1)]
    H += vinetas([
        'La consola web (Cockpit y Tasklist) está disponible en <font face="Courier">http://127.0.0.1:8081/camunda</font> desde el servidor.',
        'Para modificar un proceso, editar el archivo .bpmn con Camunda Modeler conservando la clave del proceso, copiarlo a '
        '<font face="Courier">camunda/</font> y ejecutar <font face="Courier">docker compose restart camunda</font>; se creará una '
        'nueva versión y las instancias en curso continúan en la versión anterior.',
    ])
    H += nota('El proceso <font face="Courier">sinac_preregistro_v1</font> no define un evento de captura para el mensaje '
              '<font face="Courier">DocumentoCargado</font>; cuando el backend lo envía, Camunda lo rechaza y solo se registra '
              'una advertencia. Si se desea reflejar la carga documental en el proceso, debe agregarse dicho evento.', 'Observación')
    H += [PageBreak()]

    # 8. Frontend ---------------------------------------------------------------------------------------
    H += [titulo('8. Frontend', h1, 0)]
    H += [titulo('8.1 Organización', h2, 1)]
    H += [p('El frontend es una SPA creada con Create React App. No usa un enrutador: <font face="Courier">App.js</font> mantiene '
            'la vista activa en el estado y la cambia con <font face="Courier">handleNavigate()</font>, que valida el acceso por '
            'rol antes de mostrar cada panel.')]
    H += figura(diagrama_capas([
        ('Aplicación', ['App.js (vista y sesión)', 'Navbar', 'ErrorBoundary', 'LoadingScreen']),
        ('Vistas públicas', ['HomePage', 'AspirantRegistration', 'LoginView', 'ContactPage / Aviso de privacidad']),
        ('Paneles por rol', ['PanelAspirante', 'PanelAlumno', 'PanelDocente', 'PanelDirector', 'PanelCoordinacion',
                             'PanelServiciosEscolares', 'PanelAdministrador']),
        ('Componentes compartidos', ['TablaControles', 'DashboardAnalitico', 'NotificationBell', 'HistoricoPanel',
                                     'ExamenesEnLinea', 'ErrorPage', 'ExpedienteCentralizado', 'DocumentosAspirante']),
        ('Servicios', ['fetch + JWT', 'translations.js', '*Translations.js', 'styles.css / CSS por panel']),
    ]), 'Organización de componentes del frontend.')
    H += [titulo('8.2 Navegación y control de acceso', h2, 1)]
    H += [tabla([
        ['Rol', 'Vista inicial'],
        ['aspirante', 'panel'], ['alumno', 'alumno-panel'], ['docente, investigador', 'docente-panel'],
        ['director', 'director-panel (también puede abrir docente-panel)'], ['coordinacion', 'coordinacion-panel'],
        ['servicios', 'servicios-panel'], ['admin', 'admin-panel'],
    ], [5 * cm, ANCHO_UTIL - 5 * cm]), Spacer(1, 6)]
    H += [p('Si un usuario intenta abrir una vista que no corresponde a su rol se muestra la página 403; las rutas desconocidas '
            'muestran la página 404. La autorización definitiva siempre la realiza el backend.')]
    H += [titulo('8.3 Sesión', h2, 1)]
    H += vinetas([
        'Los tokens se guardan en <font face="Courier">localStorage</font> (opción «Recordarme») o en '
        '<font face="Courier">sessionStorage</font> con las claves <font face="Courier">sinac_access</font>, '
        '<font face="Courier">sinac_refresh</font> y <font face="Courier">sinac_role</font>.',
        'La sesión del cliente se cierra automáticamente 60 minutos después de iniciarla y al recibir respuestas 401.',
        'Al cerrar sesión se eliminan las tres claves de ambos almacenamientos.',
    ])
    H += [titulo('8.4 Internacionalización', h2, 1)]
    H += [p('La interfaz está disponible en español, inglés, alemán, chino y portugués. Los textos generales están en '
            '<font face="Courier">translations.js</font> y los de cada panel en su archivo <font face="Courier">*Translations.js</font>. '
            'Para agregar un texto se debe incluir la misma clave en los cinco idiomas.')]
    H += [titulo('8.5 Compilación y servidor web', h2, 1)]
    H += vinetas([
        'En desarrollo, <font face="Courier">npm start</font> levanta el servidor en el puerto 3000 y <font face="Courier">setupProxy.js</font> '
        '(http-proxy-middleware) redirige /api al backend en <font face="Courier">http://localhost:8000</font>.',
        'En la imagen Docker, la etapa node:20-alpine ejecuta <font face="Courier">npm run build</font> y la etapa nginx:alpine '
        'sirve la carpeta build con <font face="Courier">try_files</font> hacia index.html.',
        'nginx agrega cabeceras de seguridad, evita el almacenamiento en caché de index.html y de las respuestas de la API, y '
        'muestra <font face="Courier">error-servicio.html</font> (o JSON en /api/) cuando el backend no está disponible.',
    ])
    H += [PageBreak()]

    # 9. Seguridad ----------------------------------------------------------------------------------------
    H += [titulo('9. Seguridad', h1, 0)]
    H += [p('SINAC NEXT maneja datos personales y académicos, por lo que aplica controles en varias capas. La siguiente tabla '
            'resume los mecanismos implementados.')]
    H += [tabla([['Control', 'Implementación']] + SEGURIDAD, [3.4 * cm, ANCHO_UTIL - 3.4 * cm]), Spacer(1, 6)]
    H += [titulo('9.1 Recomendaciones de operación', h2, 1)]
    H += vinetas([
        'Rotar <font face="Courier">DJANGO_SECRET_KEY</font> invalida todas las sesiones y URLs firmadas vigentes; hacerlo en una ventana de mantenimiento.',
        'Mantener actualizadas las imágenes base y las dependencias, revisando los avisos de seguridad de Django y React.',
        'Restringir el acceso a la consola de Camunda y a PostgreSQL a la red de administración.',
        'Revisar periódicamente la auditoría y las cuentas bloqueadas desde el panel de Administración.',
    ])

    # 10. Pruebas -----------------------------------------------------------------------------------------
    H += [titulo('10. Pruebas', h1, 0)]
    H += [tabla([
        ['Conjunto', 'Pruebas', 'Cobertura'],
        ['preregistro/tests.py', str(n_tests), 'Registro, inicio de sesión, perfiles, documentos, coordinación, inscripciones, servicios escolares, docentes, tesis, jurados, exámenes, egresados, histórico y administración.'],
        ['preregistro/tests_seguridad.py', str(n_tests_seg), 'Escalada de privilegios, validación de archivos, URLs firmadas, cabeceras y neutralización de fórmulas.'],
        ['tests/smoke_test.py', '3', 'Disponibilidad del backend (/health/), del frontend y, opcionalmente, de Camunda.'],
    ], [4.6 * cm, 1.7 * cm, ANCHO_UTIL - 6.3 * cm]), Spacer(1, 6)]
    H += codigo('''
docker compose exec backend python manage.py test preregistro           # suite completa
docker compose exec backend python manage.py test preregistro.tests_seguridad
python tests/smoke_test.py
cd frontend && npm run build                                            # verificación de compilación
''')
    H += nota('Django crea una base de datos temporal para las pruebas, por lo que la información real no se modifica. '
              'El usuario de PostgreSQL debe tener permiso para crear bases de datos.')
    H += [PageBreak()]

    # 11. Operación y mantenimiento ----------------------------------------------------------------------------
    H += [titulo('11. Operación y mantenimiento', h1, 0)]
    H += [titulo('11.1 Comandos de administración', h2, 1)]
    H += [p('Se ejecutan con <font face="Courier">docker compose exec backend python manage.py &lt;comando&gt;</font>.')]
    H += [tabla([['Comando', 'Descripción']] + COMANDOS, [5.4 * cm, ANCHO_UTIL - 5.4 * cm]), Spacer(1, 6)]
    H += [titulo('11.2 Operación de los contenedores', h2, 1)]
    H += codigo('''
docker compose ps                         # estado y healthcheck
docker compose logs -f --tail=200 backend # registros del backend
docker compose restart backend            # reinicio de un servicio
docker compose down                       # detener (conserva los volúmenes)
docker compose up -d --build              # reconstruir tras actualizar el código
''')
    H += [titulo('11.3 Respaldos y restauración', h2, 1)]
    H += [p('La información persistente está en dos volúmenes: <font face="Courier">postgres_data</font> (base de datos) y '
            '<font face="Courier">documentos_media</font> (documentos cargados). Ambos deben respaldarse juntos.')]
    H += codigo('''
# Respaldo
docker compose exec -T postgres pg_dump -U <usuario> -Fc <base> > sinac_AAAAMMDD.dump
docker run --rm -v sistemasinacnext_documentos_media:/datos -v %cd%:/respaldo alpine \\
    tar czf /respaldo/media_AAAAMMDD.tar.gz -C /datos .

# Restauración
docker compose exec -T postgres pg_restore -U <usuario> -d <base> --clean < sinac_AAAAMMDD.dump
docker run --rm -v sistemasinacnext_documentos_media:/datos -v %cd%:/respaldo alpine \\
    tar xzf /respaldo/media_AAAAMMDD.tar.gz -C /datos
''')
    H += nota('El nombre real del volumen lleva como prefijo el nombre del proyecto de Compose; se consulta con '
              '<font face="Courier">docker volume ls</font>. En Linux sustituir <font face="Courier">%cd%</font> por '
              '<font face="Courier">$(pwd)</font>. Se recomienda un respaldo diario y conservar copias fuera del servidor.')
    H += [titulo('11.4 Actualización del sistema', h2, 1)]
    H += pasos([
        'Realizar un respaldo de la base de datos y de los documentos.',
        'Obtener la nueva versión del código (<font face="Courier">git pull</font>).',
        'Reconstruir y levantar: <font face="Courier">docker compose up -d --build</font> (las migraciones se aplican solas).',
        'Ejecutar la prueba de humo y revisar los registros del backend.',
    ])
    H += [titulo('11.5 Servicio de alertas', h2, 1)]
    H += [p('El contenedor <font face="Courier">sinac-alertas</font> ejecuta <font face="Courier">generar_alertas_automatizadas</font> '
            'cada hora (reintenta a los 60 segundos si falla) con la zona horaria America/Mexico_City. El proceso es idempotente: '
            'antes de crear una alerta comprueba si ya existe una equivalente, por lo que puede ejecutarse manualmente sin duplicar avisos. '
            'Los días de anticipación para avisar el cierre de inscripción se definen en <font face="Courier">ALERTA_DIAS_VENCIMIENTO</font> (7).')]
    H += [titulo('11.6 Correo electrónico', h2, 1)]
    H += [p('El envío de correos usa <font face="Courier">django.core.mail.send_mail</font> con el remitente '
            '<font face="Courier">DEFAULT_FROM_EMAIL</font> (por defecto no-reply@sinac.local). <font face="Courier">settings.py</font> '
            'no define todavía un servidor SMTP, por lo que Django usa sus valores por defecto (localhost:25). Para producción se deben '
            'agregar <font face="Courier">EMAIL_HOST</font>, <font face="Courier">EMAIL_PORT</font>, <font face="Courier">EMAIL_USE_TLS</font>, '
            '<font face="Courier">EMAIL_HOST_USER</font>, <font face="Courier">EMAIL_HOST_PASSWORD</font> y '
            '<font face="Courier">DEFAULT_FROM_EMAIL</font>, leídos desde variables de entorno.')]
    H += [PageBreak()]

    # 12. Solución de problemas ---------------------------------------------------------------------------------
    H += [titulo('12. Solución de problemas', h1, 0)]
    H += [tabla_peq([['Síntoma', 'Causa probable', 'Solución']] + PROBLEMAS,
                    [5.3 * cm, 4.8 * cm, ANCHO_UTIL - 10.1 * cm]), Spacer(1, 6)]
    H += [titulo('12.1 Observaciones técnicas pendientes', h2, 1)]
    H += [p('Durante la elaboración de este manual se identificaron los siguientes puntos de mejora, que no impiden la operación '
            'del sistema:')]
    H += vinetas([
        'Configurar el servidor SMTP en <font face="Courier">settings.py</font> mediante variables de entorno (sección 11.6).',
        'En <font face="Courier">docente_views.py</font> el enlace de entrevista se genera con el dominio '
        '<font face="Courier">meet.jitsi.si</font>; el resto del sistema usa <font face="Courier">meet.jit.si</font>, que es el correcto.',
        'Agregar al proceso <font face="Courier">sinac_preregistro_v1</font> el evento de mensaje <font face="Courier">DocumentoCargado</font>.',
        'Fijar la versión de la imagen <font face="Courier">camunda/camunda-bpm-platform</font> y ejecutar el backend con un usuario no root.',
        'El panel del Director importa el componente de solicitudes de dirección de tesis, pero aún no lo muestra.',
    ])

    # 13. Conclusiones ---------------------------------------------------------------------------------
    H += [PageBreak(), titulo('13. Conclusiones', h1, 0)]
    H += [p('SINAC NEXT integra en una sola plataforma los procesos académicos del Cinvestav, desde el preregistro de aspirantes '
            'hasta el egreso, apoyándose en una arquitectura de contenedores sencilla de desplegar y respaldar. La separación entre '
            'la SPA en React, la API REST en Django y el motor de procesos LIDA permite evolucionar cada parte de forma independiente, '
            'mientras que la configuración por variables de entorno facilita trasladar el sistema entre ambientes.')]
    H += [p('Los controles de seguridad en nginx, Django y la propia aplicación, junto con más de doscientas pruebas automatizadas, '
            'ofrecen una base confiable para la operación. Siguiendo los procedimientos de este manual, el personal técnico puede '
            'instalar, mantener y extender el sistema, y atender las observaciones pendientes como parte de su mejora continua.')]
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
