"""Genera la ficha técnica del Sistema SINAC NEXT en formato Word."""

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from datetime import datetime

OUTPUT = "Ficha_Tecnica_Sistema_SINAC_NEXT.docx"


def set_heading_style(paragraph, level=1):
    sizes = {1: 18, 2: 14, 3: 12}
    paragraph.runs[0].font.size = Pt(sizes.get(level, 12))
    paragraph.runs[0].font.bold = True
    if level == 1:
        paragraph.runs[0].font.color.rgb = RGBColor(0x00, 0x3D, 0x7A)


def add_table(doc, headers, rows):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
        for p in hdr[i].paragraphs:
            for r in p.runs:
                r.font.bold = True
    for ri, row in enumerate(rows):
        cells = table.rows[ri + 1].cells
        for ci, val in enumerate(row):
            cells[ci].text = str(val)
    doc.add_paragraph()


def build():
    doc = Document()

    # Portada
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("FICHA TÉCNICA\n\nSistema SINAC NEXT")
    run.font.size = Pt(24)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x00, 0x3D, 0x7A)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_run = subtitle.add_run(
        "Sistema Integral de Administración y Control\n"
        "Centro de Investigación y de Estudios Avanzados (Cinvestav)\n\n"
        f"Versión 1.0 — {datetime.now().strftime('%d de %B de %Y')}"
    )
    sub_run.font.size = Pt(12)

    doc.add_page_break()

    # 1. Descripción general
    h = doc.add_heading("1. Descripción General", level=1)
    set_heading_style(h, 1)
    doc.add_paragraph(
        "SINAC NEXT es una plataforma web integral diseñada para la gestión del ciclo de vida "
        "académico de aspirantes, alumnos y docentes del Cinvestav. El sistema cubre desde el "
        "pre-registro de aspirantes hasta la administración académica, incluyendo gestión de "
        "documentos, seguimiento de solicitudes, solicitud de apoyos económicos, inscripción a "
        "materias y coordinación administrativa."
    )
    doc.add_paragraph(
        "La arquitectura es híbrida: combina un backend REST en Django, un frontend SPA en React, "
        "un motor de procesos BPMN con Camunda (LIDA) y PostgreSQL como base de datos relacional. "
        "Todo el ecosistema se despliega mediante contenedores Docker orquestados con Docker Compose."
    )

    # 2. Objetivos
    h = doc.add_heading("2. Objetivos del Sistema", level=1)
    set_heading_style(h, 1)
    objetivos = [
        "Digitalizar y automatizar el proceso de pre-registro de aspirantes al Cinvestav.",
        "Proporcionar trazabilidad completa del flujo de admisión mediante integración con Camunda (LIDA).",
        "Centralizar la gestión documental de aspirantes (CV, título, carta de motivos, carta de recomendación).",
        "Facilitar la coordinación académica con paneles diferenciados por rol (administrador, coordinación, docente, alumno, aspirante).",
        "Gestionar solicitudes de apoyo económico con datos bancarios y autorización.",
        "Administrar inscripciones, calificaciones y solicitudes académicas (historial, reinscripción, ajuste de materias).",
        "Notificar a los usuarios sobre cambios de estado en su solicitud mediante seguimiento y correo electrónico.",
    ]
    for obj in objetivos:
        doc.add_paragraph(obj, style="List Bullet")

    # 3. Arquitectura
    h = doc.add_heading("3. Arquitectura del Sistema", level=1)
    set_heading_style(h, 1)

    h2 = doc.add_heading("3.1 Diagrama de componentes", level=2)
    set_heading_style(h2, 2)
    doc.add_paragraph(
        "┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐\n"
        "│   Frontend      │────▶│   Backend       │────▶│   PostgreSQL    │\n"
        "│   React + Nginx │     │   Django REST   │     │   (Base datos)  │\n"
        "│   Puerto 3000   │     │   Puerto 8000   │     │   Puerto 5433   │\n"
        "└─────────────────┘     └────────┬────────┘     └─────────────────┘\n"
        "                                   │\n"
        "                                   ▼\n"
        "                          ┌─────────────────┐\n"
        "                          │   Camunda BPM   │\n"
        "                          │   (Motor LIDA)  │\n"
        "                          │   Puerto 8081   │\n"
        "                          └─────────────────┘"
    )

    h2 = doc.add_heading("3.2 Patrón arquitectónico", level=2)
    set_heading_style(h2, 2)
    doc.add_paragraph(
        "Arquitectura de tres capas con separación frontend/backend (SPA + API REST). "
        "El backend actúa como orquestador entre la interfaz de usuario, la base de datos "
        "y el motor de procesos Camunda. La autenticación se basa en tokens JWT (JSON Web Tokens)."
    )

    # 4. Stack tecnológico
    h = doc.add_heading("4. Stack Tecnológico", level=1)
    set_heading_style(h, 1)

    add_table(doc,
        ["Componente", "Tecnología", "Versión"],
        [
            ["Backend", "Python + Django", "Python 3.12 / Django 5.0.6"],
            ["API REST", "Django REST Framework", "3.15.2"],
            ["Autenticación", "Simple JWT", "5.3.1"],
            ["Frontend", "React", "18.3.1"],
            ["Build Frontend", "Create React App (react-scripts)", "5.0.1"],
            ["Servidor Web Frontend", "Nginx (Alpine)", "Latest"],
            ["Base de datos", "PostgreSQL", "15"],
            ["Motor de procesos", "Camunda BPM Platform", "Latest"],
            ["Conectividad BD", "psycopg (binary)", "3.2.1"],
            ["CORS", "django-cors-headers", "4.4.0"],
            ["Contenedores", "Docker + Docker Compose", "—"],
            ["Node.js (build)", "Node Alpine", "20"],
        ],
    )

    # 5. Servicios e infraestructura
    h = doc.add_heading("5. Servicios e Infraestructura", level=1)
    set_heading_style(h, 1)

    add_table(doc,
        ["Servicio", "Contenedor", "Puerto", "Descripción"],
        [
            ["Frontend", "sinac-frontend", "3000 → 80", "Interfaz web React servida por Nginx"],
            ["Backend", "sinac-backend", "8000", "API REST Django con JWT"],
            ["PostgreSQL", "camunda-postgres", "5433 → 5432", "Base de datos relacional compartida"],
            ["Camunda", "camunda", "8081 → 8080", "Motor BPMN para procesos LIDA"],
        ],
    )

    doc.add_paragraph("Volúmenes persistentes:")
    doc.add_paragraph("postgres_data — Datos de PostgreSQL", style="List Bullet")
    doc.add_paragraph("documentos_media — Archivos subidos por aspirantes", style="List Bullet")

    doc.add_paragraph("Comando de despliegue:")
    p = doc.add_paragraph("docker compose up --build -d")
    p.runs[0].font.name = "Consolas"
    p.runs[0].font.size = Pt(10)

    # 6. Roles de usuario
    h = doc.add_heading("6. Roles de Usuario", level=1)
    set_heading_style(h, 1)

    add_table(doc,
        ["Rol", "Descripción", "Panel / Vista"],
        [
            ["Aspirante", "Usuario en proceso de admisión", "Panel Aspirante — pre-registro, documentos, seguimiento, apoyo"],
            ["Alumno", "Aspirante aceptado y matriculado", "Panel Alumno — materias, inscripciones, solicitudes académicas"],
            ["Docente", "Profesor del programa", "Panel Docente — consulta de información académica"],
            ["Coordinación", "Personal de coordinación académica (is_staff)", "Panel Coordinación — gestión de aspirantes, materias, cargas, calificaciones"],
            ["Administrador", "Superusuario del sistema (is_superuser)", "Panel Administrador — vista global de aspirantes y estadísticas"],
        ],
    )

    # 7. Modelo de datos
    h = doc.add_heading("7. Modelo de Datos", level=1)
    set_heading_style(h, 1)

    h2 = doc.add_heading("7.1 Aspirante (modelo principal de usuario)", level=2)
    set_heading_style(h2, 2)
    doc.add_paragraph(
        "Extiende AbstractBaseUser y PermissionsMixin. Campos organizados en 11 secciones: "
        "datos generales, domicilio actual, domicilio permanente, familiar, escolaridad, "
        "idiomas/publicaciones/apoyos/experiencia (opcionales), datos Cinvestav, adscripción, "
        "fechas de proceso (examen, entrevista, curso propedéutico), apoyo económico, "
        "integración LIDA/Camunda (business_key, camunda_instance_id, proceso_estado) y rol."
    )

    add_table(doc,
        ["Entidad", "Descripción", "Relaciones"],
        [
            ["Aspirante", "Usuario principal del sistema", "1:N DocumentoAspirante, SeguimientoSolicitud, Inscripcion, SolicitudAcademica"],
            ["DocumentoAspirante", "Archivos del aspirante (CV, título, carta motivos, recomendación)", "N:1 Aspirante"],
            ["SeguimientoSolicitud", "Historial de estados y notificaciones", "N:1 Aspirante"],
            ["Materia", "Catálogo de materias del programa", "1:N Inscripcion"],
            ["Inscripcion", "Inscripción de alumno a materia con calificación", "N:1 Aspirante, N:1 Materia"],
            ["SolicitudAcademica", "Solicitudes de historial, reinscripción o ajuste de materias", "N:1 Aspirante"],
        ],
    )

    h2 = doc.add_heading("7.2 Tipos de documento admitidos", level=2)
    set_heading_style(h2, 2)
    add_table(doc,
        ["Tipo", "Descripción", "Restricción"],
        [
            ["cv", "Currículum vitae", "Uno por aspirante"],
            ["titulo", "Título o comprobante de estudios", "Uno por aspirante"],
            ["carta_motivacion", "Carta de motivos", "Uno por aspirante"],
            ["carta_recomendacion", "Carta de recomendación", "Uno por aspirante"],
        ],
    )
    doc.add_paragraph("Tamaño máximo por archivo: 10 MB.")

    # 8. API REST
    h = doc.add_heading("8. Endpoints de la API REST", level=1)
    set_heading_style(h, 1)
    doc.add_paragraph("Base URL: http://localhost:8000/api/")

    add_table(doc,
        ["Endpoint", "Método", "Autenticación", "Descripción"],
        [
            ["/health/", "GET", "Pública", "Verificación de estado del backend"],
            ["/api/auth/login/", "POST", "Pública", "Inicio de sesión (JWT access + refresh)"],
            ["/api/auth/refresh/", "POST", "Refresh token", "Renovación de token de acceso"],
            ["/api/preregistro/", "POST", "Pública", "Creación de pre-registro de aspirante"],
            ["/api/preregistro/me/", "GET/PATCH", "JWT", "Consulta y actualización del perfil"],
            ["/api/preregistro/seguimiento/", "GET", "JWT", "Historial de seguimiento de solicitud"],
            ["/api/preregistro/documentos/", "GET/POST", "JWT", "Listado y carga de documentos"],
            ["/api/preregistro/documentos/{id}/", "DELETE", "JWT", "Eliminación de documento"],
            ["/api/preregistro/documentos/{id}/descarga/", "GET", "JWT", "Descarga de documento"],
            ["/api/preregistro/apoyo/solicitar/", "POST", "JWT", "Solicitud de apoyo económico"],
            ["/api/preregistro/notificaciones/marcar-leidas/", "POST", "JWT", "Marcar notificaciones como leídas"],
            ["/api/preregistro/convertir-misma-cuenta/", "POST", "JWT", "Conversión de aspirante a alumno (misma cuenta)"],
            ["/api/administracion/panel/", "GET", "JWT (admin)", "Panel de administración"],
            ["/api/coordinacion/panel/", "GET", "JWT (staff)", "Panel de coordinación"],
            ["/api/coordinacion/aspirantes/{id}/", "GET", "JWT (staff)", "Detalle de aspirante"],
            ["/api/coordinacion/aspirantes/{id}/estado/", "PATCH", "JWT (staff)", "Actualizar estado de aspirante"],
            ["/api/coordinacion/aspirantes/{id}/convertir/", "POST/PATCH", "JWT (staff)", "Convertir aspirante a alumno"],
            ["/api/coordinacion/aspirantes/{id}/dar_baja/", "POST", "JWT (staff)", "Dar de baja a aspirante/alumno"],
            ["/api/coordinacion/aspirantes/{id}/calificaciones/", "GET", "JWT (staff)", "Descarga de calificaciones"],
            ["/api/coordinacion/aspirantes/{id}/adscripcion/download/", "GET", "JWT (staff)", "Descarga de adscripción"],
            ["/api/coordinacion/materias/", "GET", "JWT (staff)", "Listado de materias"],
            ["/api/coordinacion/cursos/upload/", "POST", "JWT (staff)", "Carga masiva de cursos (CSV)"],
            ["/api/coordinacion/cargas/generar/", "POST", "JWT (staff)", "Generación de cargas académicas"],
        ],
    )

    # 9. Integración Camunda / LIDA
    h = doc.add_heading("9. Integración con Camunda (LIDA)", level=1)
    set_heading_style(h, 1)
    doc.add_paragraph(
        "Al completar un pre-registro, el backend dispara automáticamente el proceso BPMN "
        "'sinac_preregistro_v1' en Camunda mediante la REST API (engine-rest). Se envían "
        "variables de proceso: aspiranteId, correo, unidad, programa y lidaSource."
    )
    doc.add_paragraph(
        "Cuando un aspirante carga un documento, se envía un mensaje 'DocumentoCargado' al "
        "proceso Camunda asociado mediante business_key, incluyendo tipoDocumento, nombreArchivo "
        "y documentoId. La integración es tolerante a fallos: si Camunda no está disponible, "
        "el sistema continúa operando normalmente."
    )

    add_table(doc,
        ["Evento", "Acción Camunda", "Endpoint"],
        [
            ["Pre-registro completado", "Iniciar proceso sinac_preregistro_v1", "POST /process-definition/key/sinac_preregistro_v1/start"],
            ["Documento cargado", "Enviar mensaje DocumentoCargado", "POST /message"],
        ],
    )

    # 10. Seguridad
    h = doc.add_heading("10. Seguridad y Autenticación", level=1)
    set_heading_style(h, 1)
    seguridad = [
        "Autenticación basada en JWT (JSON Web Tokens) con Simple JWT.",
        "Token de acceso: vigencia de 8 horas.",
        "Token de refresco: vigencia de 7 días.",
        "Endpoints protegidos con IsAuthenticated por defecto; pre-registro y login son públicos.",
        "Control de acceso por rol: admin (is_superuser), coordinación (is_staff), aspirante/alumno/docente (campo rol).",
        "CORS configurado para localhost:3000 y 127.0.0.1:3000.",
        "Sesión del frontend con timeout de inactividad de 60 minutos.",
        "Limpieza de tokens al cerrar pestaña o cambiar visibilidad del navegador.",
        "Restricción de tamaño de archivos subidos (máx. 10 MB).",
        "Constraint de unicidad: un documento por tipo por aspirante.",
    ]
    for s in seguridad:
        doc.add_paragraph(s, style="List Bullet")

    # 11. Módulos frontend
    h = doc.add_heading("11. Módulos del Frontend", level=1)
    set_heading_style(h, 1)

    add_table(doc,
        ["Componente", "Función"],
        [
            ["HomePage", "Página de inicio con carrusel, misión y visión"],
            ["AspirantRegistration", "Formulario de pre-registro (11 secciones)"],
            ["LoginView", "Inicio de sesión con JWT"],
            ["PanelAspirante", "Panel del aspirante: perfil, documentos, seguimiento, apoyo"],
            ["PanelAlumno", "Panel del alumno: materias, inscripciones, solicitudes académicas"],
            ["PanelDocente", "Panel del docente"],
            ["PanelCoordinacion", "Panel de coordinación: gestión de aspirantes y materias"],
            ["PanelAdministrador", "Panel de administración global"],
            ["DocumentosAspirante", "Carga y gestión de documentos"],
            ["SeguimientoSolicitud", "Timeline de seguimiento de la solicitud"],
            ["SolicitudApoyo", "Formulario de solicitud de apoyo económico"],
            ["Navbar / Footer", "Navegación y pie de página"],
            ["LoadingScreen", "Pantalla de carga inicial"],
        ],
    )

    # 12. Comandos de gestión
    h = doc.add_heading("12. Comandos de Gestión (Django)", level=1)
    set_heading_style(h, 1)

    add_table(doc,
        ["Comando", "Descripción"],
        [
            ["crear_admin_sinac", "Crea un usuario administrador del sistema"],
            ["crear_alumno_sinac", "Crea un usuario alumno de prueba"],
            ["crear_docente_sinac", "Crea un usuario docente de prueba"],
        ],
    )

    # 13. Configuración regional
    h = doc.add_heading("13. Configuración Regional", level=1)
    set_heading_style(h, 1)
    add_table(doc,
        ["Parámetro", "Valor"],
        [
            ["Idioma", "es-mx (Español México)"],
            ["Zona horaria", "America/Mexico_City"],
            ["Formato de fechas", "ISO 8601 con soporte de zona horaria"],
        ],
    )

    # 14. Requisitos del sistema
    h = doc.add_heading("14. Requisitos del Sistema", level=1)
    set_heading_style(h, 1)

    h2 = doc.add_heading("14.1 Requisitos de hardware (mínimos para desarrollo)", level=2)
    set_heading_style(h2, 2)
    add_table(doc,
        ["Recurso", "Mínimo"],
        [
            ["Procesador", "2 núcleos"],
            ["Memoria RAM", "4 GB"],
            ["Almacenamiento", "10 GB libres"],
            ["Red", "Conexión a Internet (para build de contenedores)"],
        ],
    )

    h2 = doc.add_heading("14.2 Requisitos de software", level=2)
    set_heading_style(h2, 2)
    add_table(doc,
        ["Software", "Versión"],
        [
            ["Docker Desktop", "Latest"],
            ["Docker Compose", "v2+"],
            ["Navegador web", "Chrome, Firefox o Edge (última versión)"],
        ],
    )

    # 15. Flujo de proceso de admisión
    h = doc.add_heading("15. Flujo del Proceso de Admisión", level=1)
    set_heading_style(h, 1)
    flujo = [
        "1. El aspirante completa el formulario de pre-registro en el portal web.",
        "2. El sistema crea la cuenta, genera un business_key y registra el seguimiento inicial.",
        "3. Se dispara el proceso BPMN en Camunda (si está disponible).",
        "4. El aspirante inicia sesión y carga sus documentos requeridos.",
        "5. Cada documento cargado notifica al proceso LIDA en Camunda.",
        "6. Coordinación revisa el expediente, actualiza estados y programa fechas (examen, entrevista, curso propedéutico).",
        "7. El aspirante puede solicitar apoyo económico con datos bancarios.",
        "8. Coordinación autoriza o rechaza el apoyo y convierte al aspirante en alumno.",
        "9. El alumno accede a inscripción de materias, solicitudes académicas y descarga de documentos.",
    ]
    for paso in flujo:
        doc.add_paragraph(paso, style="List Number")

    # 16. Historial de migraciones
    h = doc.add_heading("16. Evolución del Sistema (Migraciones)", level=1)
    set_heading_style(h, 1)
    add_table(doc,
        ["Migración", "Cambio"],
        [
            ["0001_initial", "Modelo Aspirante inicial"],
            ["0002_documentoaspirante", "Gestión de documentos"],
            ["0003_seguimiento_solicitud", "Seguimiento de solicitudes"],
            ["0004_aspirante_rol", "Campo de rol de usuario"],
            ["0005_alter_aspirante_rol", "Ajuste de choices de rol"],
            ["0006_aspirante_apoyo_autorizado_and_more", "Apoyo económico y fechas de proceso"],
            ["0007_add_leido_field", "Campo leído en notificaciones"],
            ["0008_datos_bancarios_apoyo", "Datos bancarios para apoyo"],
            ["0009_create_materia", "Materias, inscripciones y solicitudes académicas"],
        ],
    )

    # Pie de documento
    doc.add_paragraph()
    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = footer.add_run(
        f"\n— Documento generado automáticamente —\n"
        f"Sistema SINAC NEXT v1.0 | Cinvestav | {datetime.now().strftime('%Y-%m-%d')}"
    )
    fr.font.size = Pt(9)
    fr.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    doc.save(OUTPUT)
    print(f"Documento generado: {OUTPUT}")


if __name__ == "__main__":
    build()
