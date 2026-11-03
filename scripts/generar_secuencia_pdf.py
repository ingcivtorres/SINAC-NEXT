"""Genera el documento de diagramas de secuencia por actor de SINAC NEXT."""
import os

from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, Spacer
from reportlab.platypus.tableofcontents import TableOfContents

from plantilla_cinvestav import (
    ANCHO_UTIL, GRIS, RAIZ, VERDE_CLARO, VERDE_OSCURO,
    DiagramaAjustado, Documento, canvas_numerado, cuerpo, envolver, h1, h2, h3, pie_fig,
    portada, tabla, titulo, toc_estilos, vineta,
)

TITULO = 'Diagramas de Secuencia por Actor'
SALIDA = os.path.join(RAIZ, 'docs', 'SINAC_NEXT_Diagramas_de_Secuencia.pdf')

PARTICIPANTES = {
    'actor': (None, None),
    'ui': ('Panel React', '«boundary»'),
    'api': ('API REST Django', '«control»'),
    'bd': ('PostgreSQL', '«entity»'),
    'media': ('Almacenamiento de medios', '«sistema»'),
    'lida': ('Motor LIDA (Camunda)', '«sistema»'),
    'correo': ('Servidor de correo', '«sistema»'),
    'jitsi': ('Jitsi Meet', '«sistema»'),
}

AZUL_FRAG = colors.HexColor('#5B6B7A')
FONDO_ACT = colors.HexColor('#CFEDE6')
TAM_MSG = 7
LINEA_MSG = 8.4
CABECERA = 50


def m(a, b, t):
    return ('m', a, b, t)


def r(a, b, t):
    return ('r', a, b, t)


def asin(a, b, t):
    return ('a', a, b, t)


def s(p, t):
    return ('s', p, t)


def alt(c):
    return ('frag', 'alt', c)


def opt(c):
    return ('frag', 'opt', c)


def loop(c):
    return ('frag', 'loop', c)


def sino(c):
    return ('else', c)


def fin():
    return ('fin',)


class Secuencia:
    """Motor de dibujo de diagramas de secuencia UML con coordenadas de arriba hacia abajo."""

    def __init__(self, actor, pasos, ancho=ANCHO_UTIL):
        self.actor, self.pasos, self.W = actor, pasos, ancho
        usados = {'actor', 'ui'}
        for p in pasos:
            if p[0] in ('m', 'r', 'a'):
                usados.update(p[1:3])
            elif p[0] == 's':
                usados.add(p[1])
        self.orden = [k for k in PARTICIPANTES if k in usados]
        n = len(self.orden)
        margen = 44
        paso_x = (ancho - 2 * margen) / (n - 1)
        self.x = {k: margen + i * paso_x for i, k in enumerate(self.orden)}
        self.paso_x = paso_x
        self.capas = {'fragmentos': [], 'vidas': [], 'activaciones': [], 'mensajes': []}
        self.pila = {k: [] for k in self.orden}
        self.t = CABECERA + 14
        self.numero = 0

    # Primitivas en coordenadas t (desde arriba); se convierten al final.
    def linea(self, capa, x1, t1, x2, t2, color=colors.black, ancho=0.8, guiones=None):
        self.capas[capa].append(('linea', x1, t1, x2, t2, color, ancho, guiones))

    def rect(self, capa, x, t, w, h, relleno=None, borde=colors.black, ancho=0.7, opacidad=None, radio=0):
        self.capas[capa].append(('rect', x, t, w, h, relleno, borde, ancho, opacidad, radio))

    def texto(self, capa, x, t, cadena, fuente='Arial', tam=TAM_MSG, color=colors.black, ancla='start'):
        self.capas[capa].append(('texto', x, t, cadena, fuente, tam, color, ancla))

    def poligono(self, capa, puntos, relleno, borde=colors.black):
        self.capas[capa].append(('poli', puntos, relleno, borde))

    def borde_x(self, p, hacia_derecha):
        prof = len(self.pila[p])
        if not prof:
            return self.x[p]
        desp = (prof - 1) * 4
        return self.x[p] + desp + (4 if hacia_derecha else -4)

    def etiqueta(self, x_ini, x_fin, cadena):
        limite = max(abs(x_fin - x_ini) - 10, 175)
        lineas = envolver(cadena, 'Arial', TAM_MSG, limite)
        ancho = max(stringWidth(l, 'Arial', TAM_MSG) for l in lineas)
        xa = min(x_ini, x_fin) + 5
        if xa + ancho > self.W - 3:
            xa = self.W - 3 - ancho
        alto = len(lineas) * LINEA_MSG
        self.rect('mensajes', xa - 1.5, self.t - 1, ancho + 3, alto + 1, relleno=colors.white, borde=None, opacidad=0.88)
        for i, l in enumerate(lineas):
            self.texto('mensajes', xa, self.t + (i + 1) * LINEA_MSG - 2, l)
        self.t += alto + 3

    def flecha(self, x1, x2, t, tipo):
        guiones = (3, 2) if tipo == 'r' else None
        self.linea('mensajes', x1, t, x2, t, ancho=0.8, guiones=guiones)
        d = 1 if x2 > x1 else -1
        if tipo == 'm':
            self.poligono('mensajes', [(x2, t), (x2 - 6 * d, t - 2.6), (x2 - 6 * d, t + 2.6)], colors.black)
        else:
            self.linea('mensajes', x2, t, x2 - 6 * d, t - 2.8, ancho=0.8)
            self.linea('mensajes', x2, t, x2 - 6 * d, t + 2.8, ancho=0.8)

    def activar(self, p, t):
        self.pila[p].append(t)

    def desactivar(self, p, t):
        if not self.pila[p]:
            return
        inicio = self.pila[p].pop()
        desp = len(self.pila[p]) * 4
        self.rect('activaciones', self.x[p] - 4 + desp, inicio, 8, max(t - inicio, 6), relleno=FONDO_ACT, borde=VERDE_OSCURO, ancho=0.6)

    def mensaje(self, tipo, a, b, cadena):
        if tipo != 'r':
            self.numero += 1
            cadena = f'{self.numero}: {cadena}'
        derecha = self.x[b] > self.x[a]
        x1 = self.borde_x(a, derecha)
        self.etiqueta(self.x[a], self.x[b], cadena)
        t = self.t
        if tipo == 'm':
            if b != 'actor':
                self.activar(b, t)
            x2 = self.borde_x(b, not derecha)
        elif tipo == 'r':
            self.desactivar(a, t)
            x2 = self.borde_x(b, not derecha)
        else:
            x2 = self.x[b] + (-4 if derecha else 4)
            self.rect('activaciones', self.x[b] - 4, t, 8, 10, relleno=FONDO_ACT, borde=VERDE_OSCURO, ancho=0.6)
        self.flecha(x1, x2, t, tipo)
        self.t += 8 if tipo != 'a' else 12

    def propio(self, p, cadena):
        self.numero += 1
        cadena = f'{self.numero}: {cadena}'
        x0 = self.borde_x(p, True)
        lineas = envolver(cadena, 'Arial', TAM_MSG, 170)
        ancho = max(stringWidth(l, 'Arial', TAM_MSG) for l in lineas)
        xa = x0 + 26
        if xa + ancho > self.W - 3:
            xa = self.W - 3 - ancho
        alto = len(lineas) * LINEA_MSG
        t_ini = self.t + 2
        t_fin = t_ini + max(14, alto + 2)
        prof = len(self.pila[p])
        xb = self.x[p] - 4 + prof * 4
        self.rect('activaciones', xb, t_ini + 4, 8, t_fin - t_ini + 2, relleno=FONDO_ACT, borde=VERDE_OSCURO, ancho=0.6)
        self.linea('mensajes', x0, t_ini, x0 + 20, t_ini)
        self.linea('mensajes', x0 + 20, t_ini, x0 + 20, t_fin)
        self.linea('mensajes', x0 + 20, t_fin, xb + 8, t_fin)
        self.poligono('mensajes', [(xb + 8, t_fin), (xb + 14, t_fin - 2.6), (xb + 14, t_fin + 2.6)], colors.black)
        self.rect('mensajes', xa - 1.5, t_ini - 1, ancho + 3, alto + 1, relleno=colors.white, borde=None, opacidad=0.88)
        for i, l in enumerate(lineas):
            self.texto('mensajes', xa, t_ini + (i + 1) * LINEA_MSG - 2, l)
        self.t = t_fin + 10

    def construir(self):
        fragmentos = []
        for paso in self.pasos:
            tipo = paso[0]
            if tipo in ('m', 'r', 'a'):
                self.mensaje(tipo, paso[1], paso[2], paso[3])
            elif tipo == 's':
                self.propio(paso[1], paso[2])
            elif tipo == 'frag':
                self.t += 2
                foto = {k: len(v) for k, v in self.pila.items()}
                fragmentos.append({'tipo': paso[1], 't': self.t, 'guardas': [(self.t, paso[2])], 'foto': foto})
                self.t += 20
            elif tipo == 'else':
                frag = fragmentos[-1]
                self.t += 2
                frag['guardas'].append((self.t, paso[1]))
                for k, n in frag['foto'].items():
                    while len(self.pila[k]) < n:
                        self.activar(k, self.t)
                self.t += 18
            elif tipo == 'fin':
                frag = fragmentos.pop()
                self.t += 4
                self.dibujar_fragmento(frag, len(fragmentos))
                self.t += 8
        t_fin = self.t + 4
        for k in self.orden:
            while self.pila[k]:
                self.desactivar(k, t_fin)
        self.dibujar_cabeceras(t_fin + 6)
        return self.dibujo(t_fin + 14)

    def dibujar_fragmento(self, frag, prof):
        izq = 8 + prof * 5
        der = self.W - 8 - prof * 5
        t0 = frag['t']
        self.rect('fragmentos', izq, t0, der - izq, self.t - t0, borde=AZUL_FRAG, ancho=0.8)
        etiqueta = frag['tipo']
        ancho = stringWidth(etiqueta, 'Arial-Bold', 7.5) + 12
        self.poligono('fragmentos', [(izq, t0), (izq + ancho, t0), (izq + ancho, t0 + 7), (izq + ancho - 5, t0 + 12), (izq, t0 + 12)],
                      colors.HexColor('#E8EDF1'), AZUL_FRAG)
        self.texto('fragmentos', izq + 4, t0 + 9, etiqueta, 'Arial-Bold', 7.5, AZUL_FRAG)
        for i, (tg, guarda) in enumerate(frag['guardas']):
            if i == 0:
                self.texto('fragmentos', izq + ancho + 6, t0 + 9, guarda, 'Arial-Italic', 7.2, AZUL_FRAG)
            else:
                self.linea('fragmentos', izq, tg, der, tg, AZUL_FRAG, 0.8, (4, 3))
                self.texto('fragmentos', izq + 6, tg + 10, guarda, 'Arial-Italic', 7.2, AZUL_FRAG)

    def dibujar_cabeceras(self, t_fin):
        ancho_caja = min(self.paso_x - 8, 98)
        for k in self.orden:
            x = self.x[k]
            self.linea('vidas', x, CABECERA - 2, x, t_fin, colors.HexColor('#8A97A3'), 0.7, (3, 3))
            if k == 'actor':
                self.capas['vidas'].append(('circulo', x, 8, 4.8))
                self.linea('vidas', x, 12.8, x, 24, ancho=1)
                self.linea('vidas', x - 7, 17, x + 7, 17, ancho=1)
                self.linea('vidas', x, 24, x - 6, 32, ancho=1)
                self.linea('vidas', x, 24, x + 6, 32, ancho=1)
                lineas = envolver(self.actor, 'Arial-Bold', 7.5, max(self.paso_x - 4, 70))
                for i, l in enumerate(lineas):
                    self.texto('vidas', x, 40 + i * 8.5, l, 'Arial-Bold', 7.5, VERDE_OSCURO, 'middle')
            else:
                nombre, estereotipo = PARTICIPANTES[k]
                self.rect('vidas', x - ancho_caja / 2, 4, ancho_caja, CABECERA - 6, relleno=VERDE_CLARO, borde=VERDE_OSCURO, ancho=0.9, radio=3)
                self.texto('vidas', x, 14, estereotipo, 'Arial-Italic', 6.5, GRIS, 'middle')
                lineas = envolver(nombre, 'Arial-Bold', 7.3, ancho_caja - 6)
                for i, l in enumerate(lineas):
                    self.texto('vidas', x, 25 + i * 8.5, l, 'Arial-Bold', 7.3, VERDE_OSCURO, 'middle')

    def dibujo(self, alto):
        d = Drawing(self.W, alto)
        Y = lambda t: alto - t
        for capa in ('fragmentos', 'vidas', 'activaciones', 'mensajes'):
            for e in self.capas[capa]:
                if e[0] == 'linea':
                    _, x1, t1, x2, t2, color, ancho, guiones = e
                    d.add(Line(x1, Y(t1), x2, Y(t2), strokeColor=color, strokeWidth=ancho, strokeDashArray=guiones))
                elif e[0] == 'rect':
                    _, x, t, w, h, relleno, borde, ancho, opacidad, radio = e
                    rc = Rect(x, Y(t + h), w, h, fillColor=relleno, strokeColor=borde, strokeWidth=ancho, rx=radio, ry=radio)
                    if opacidad is not None:
                        rc.fillOpacity = opacidad
                    d.add(rc)
                elif e[0] == 'texto':
                    _, x, t, cadena, fuente, tam, color, ancla = e
                    d.add(String(x, Y(t), cadena, fontName=fuente, fontSize=tam, fillColor=color, textAnchor=ancla))
                elif e[0] == 'poli':
                    _, puntos, relleno, borde = e
                    plano = []
                    for px, pt in puntos:
                        plano += [px, Y(pt)]
                    d.add(Polygon(plano, fillColor=relleno, strokeColor=borde, strokeWidth=0.6))
                elif e[0] == 'circulo':
                    _, x, t, radio = e
                    d.add(Circle(x, Y(t), radio, fillColor=colors.white, strokeColor=colors.black, strokeWidth=1))
        return d


def diagrama_secuencia(actor, pasos):
    return Secuencia(actor, pasos).construir()


# --------------------------------------------------------------------------------------------
# Contenido
# --------------------------------------------------------------------------------------------

def ds(id_, nombre, cu, descripcion, pasos):
    return {'id': id_, 'nombre': nombre, 'cu': cu, 'descripcion': descripcion, 'pasos': pasos}


COMUNES = [
    ds('DS-GEN-01', 'Autenticarse en el sistema', 'Autenticarse en el sistema (incluido por todos los casos de uso generales)',
       'El usuario envía sus credenciales al endpoint de inicio de sesión. La API aplica limitación de peticiones, '
       'verifica el bloqueo temporal por intentos fallidos y, si las credenciales son correctas, emite el par de tokens JWT '
       'con el rol del usuario. Para no revelar información, una cuenta bloqueada responde con el mismo mensaje genérico '
       'que una contraseña incorrecta.',
       [m('actor', 'ui', 'Captura usuario (o correo) y contraseña'),
        m('ui', 'api', 'POST /api/auth/login/ {usuario, password}'),
        s('api', 'Aplicar límite de peticiones (throttling)'),
        m('api', 'bd', 'SELECT ... FOR UPDATE usuario, intentos y bloqueo'),
        r('bd', 'api', 'Registro del usuario'),
        alt('[usuario inactivo o cuenta bloqueada]'),
        r('api', 'ui', '401 Credenciales inválidas'),
        r('ui', 'actor', 'Muestra mensaje genérico de error'),
        sino('[contraseña incorrecta]'),
        m('api', 'bd', 'Incrementar login_failed_attempts; fijar login_locked_until al llegar al límite'),
        r('bd', 'api', 'Actualizado'),
        r('api', 'ui', '401 Credenciales inválidas'),
        r('ui', 'actor', 'Muestra mensaje genérico de error'),
        sino('[credenciales válidas]'),
        m('api', 'bd', 'Reiniciar intentos fallidos y bloqueo'),
        r('bd', 'api', 'Actualizado'),
        s('api', 'Generar tokens JWT (access y refresh) con el rol'),
        r('api', 'ui', '200 {access, refresh, rol}'),
        s('ui', 'Guardar sesión y redirigir según el rol'),
        r('ui', 'actor', 'Muestra el panel correspondiente'),
        fin()]),
    ds('DS-GEN-02', 'Renovar la sesión', 'Autenticarse en el sistema',
       'Cuando el token de acceso caduca, el Panel React solicita uno nuevo con el token de renovación y reintenta '
       'la petición original de forma transparente. Si el token de renovación también expiró, se cierra la sesión.',
       [m('actor', 'ui', 'Realiza una acción en el panel'),
        m('ui', 'api', 'Petición con Authorization: Bearer <access>'),
        s('api', 'Validar firma y vigencia del token'),
        r('api', 'ui', '401 Token expirado'),
        m('ui', 'api', 'POST /api/auth/refresh/ {refresh}'),
        s('api', 'Validar el token de renovación'),
        alt('[refresh válido]'),
        r('api', 'ui', '200 {access}'),
        m('ui', 'api', 'Reintentar la petición original con el nuevo access'),
        r('api', 'ui', '200 Datos solicitados'),
        r('ui', 'actor', 'Muestra la información'),
        sino('[refresh inválido o expirado]'),
        r('api', 'ui', '401 Sesión expirada'),
        s('ui', 'Eliminar los tokens almacenados'),
        r('ui', 'actor', 'Redirige al inicio de sesión'),
        fin()]),
    ds('DS-GEN-03', 'Consultar un archivo protegido', 'Revisar documentos / Consultar expediente',
       'Los archivos cargados (documentos, fotografías, tesis) no se publican directamente: la API entrega una URL '
       'firmada con caducidad y la vista de medios valida la firma antes de leer el archivo del almacenamiento.',
       [m('actor', 'ui', 'Selecciona "Ver documento"'),
        m('ui', 'api', 'GET /api/preregistro/documentos/{id}/'),
        s('api', 'Verificar JWT y que el usuario pueda ver el archivo'),
        m('api', 'bd', 'Consultar documento y propietario'),
        r('bd', 'api', 'Documento'),
        s('api', 'Firmar la URL /media/<ruta> con caducidad'),
        r('api', 'ui', '200 {url firmada}'),
        m('ui', 'api', 'GET /media/<ruta>?firma&expira'),
        s('api', 'Validar firma y vigencia'),
        alt('[firma válida y vigente]'),
        m('api', 'media', 'Leer archivo'),
        r('media', 'api', 'Contenido'),
        r('api', 'ui', '200 Archivo'),
        r('ui', 'actor', 'Muestra o descarga el documento'),
        sino('[firma inválida o expirada]'),
        r('api', 'ui', '403 Enlace no válido'),
        r('ui', 'actor', 'Solicita volver a abrir el documento'),
        fin()]),
]

ROLES = [
    {
        'nombre': 'Coordinación Académica', 'sigla': 'COO',
        'intro': 'La Coordinación Académica conduce la admisión y la operación académica. Sus secuencias principales '
                 'involucran la revisión del expediente del aspirante, la resolución de la solicitud con avance del proceso '
                 'LIDA, la conversión a alumno, las cargas académicas orquestadas por Camunda y las notificaciones masivas.',
        'diagramas': [
            ds('DS-COO-01', 'Revisar documentos del aspirante', 'CU-COO-03 Revisar documentos del aspirante',
               'El actor abre el detalle del aspirante, consulta sus documentos mediante enlaces firmados y registra la '
               'revisión u observación de cada uno.',
               [m('actor', 'ui', 'Abre el detalle del aspirante'),
                m('ui', 'api', 'GET /api/coordinacion/aspirantes/{id}/'),
                s('api', 'Verificar JWT y rol de Coordinación'),
                m('api', 'bd', 'Consultar aspirante, documentos y seguimiento'),
                r('bd', 'api', 'Datos del expediente'),
                s('api', 'Firmar URL de cada documento'),
                r('api', 'ui', '200 Aspirante con documentos'),
                r('ui', 'actor', 'Muestra la lista de documentos'),
                m('actor', 'ui', 'Marca el documento como revisado u observado'),
                m('ui', 'api', 'PATCH /api/coordinacion/documentos/{id}/revision/ {revisado, observaciones}'),
                m('api', 'bd', 'Consultar documento'),
                r('bd', 'api', 'Documento'),
                alt('[documento inexistente]'),
                r('api', 'ui', '404 No encontrado'),
                r('ui', 'actor', 'Muestra el error'),
                sino('[revisión válida]'),
                m('api', 'bd', 'Actualizar revisado, observaciones y fecha de revisión'),
                r('bd', 'api', 'Documento actualizado'),
                r('api', 'ui', '200 Documento revisado'),
                r('ui', 'actor', 'Actualiza el estado del documento'),
                fin()]),
            ds('DS-COO-02', 'Resolver estado del aspirante', 'CU-COO-04 Resolver estado del aspirante',
               'El actor cambia la solicitud a revisión, aceptado o rechazado. La API impide aceptar si hay documentos sin '
               'revisar, crea el expediente digital al aceptar, registra el seguimiento y notifica al aspirante.',
               [m('actor', 'ui', 'Selecciona el nuevo estado'),
                m('ui', 'api', 'PATCH /api/coordinacion/aspirantes/{id}/estado/ {proceso_estado}'),
                s('api', 'Validar estado permitido (revisión, aceptado, rechazado)'),
                m('api', 'bd', 'Consultar aspirante y documentos'),
                r('bd', 'api', 'Aspirante y documentos'),
                alt('[aceptado con documentos ausentes o sin revisar]'),
                r('api', 'ui', '409 documentos_pendientes'),
                r('ui', 'actor', 'Indica los documentos pendientes'),
                sino('[transición válida]'),
                m('api', 'bd', 'Actualizar proceso_estado'),
                r('bd', 'api', 'Actualizado'),
                opt('[estado = aceptado]'),
                m('api', 'bd', 'Crear expediente digital con folio'),
                r('bd', 'api', 'Expediente'),
                fin(),
                m('api', 'bd', 'Registrar seguimiento de la solicitud'),
                r('bd', 'api', 'Seguimiento registrado'),
                asin('api', 'lida', 'Notificar avance del proceso (engine-rest)'),
                asin('api', 'correo', 'Enviar correo de notificación al aspirante'),
                r('api', 'ui', '200 Aspirante (+ expediente digital)'),
                r('ui', 'actor', 'Muestra el nuevo estado'),
                fin()]),
            ds('DS-COO-03', 'Convertir aspirante en alumno', 'CU-COO-06 Convertir aspirante en alumno',
               'A partir de un aspirante aceptado se asigna matrícula, programa y rol de alumno, se registra el alta en el '
               'histórico y se notifica a la persona.',
               [m('actor', 'ui', 'Elige "Convertir en alumno"'),
                m('ui', 'api', 'POST /api/coordinacion/aspirantes/{id}/convertir/ {matrícula, programa, periodo}'),
                s('api', 'Verificar JWT y rol de Coordinación'),
                m('api', 'bd', 'Consultar aspirante'),
                r('bd', 'api', 'Aspirante'),
                alt('[no está aceptado o matrícula duplicada]'),
                r('api', 'ui', '400 Motivo del rechazo'),
                r('ui', 'actor', 'Muestra el motivo'),
                sino('[aceptado]'),
                m('api', 'bd', 'Asignar matrícula, programa y rol alumno'),
                r('bd', 'api', 'Alumno'),
                m('api', 'bd', 'Registrar alta en el histórico'),
                r('bd', 'api', 'Evento registrado'),
                asin('api', 'correo', 'Notificar el alta como alumno'),
                r('api', 'ui', '200 Alumno'),
                r('ui', 'actor', 'Confirma la conversión'),
                fin()]),
            ds('DS-COO-04', 'Gestionar cargas académicas con LIDA', 'CU-COO-07 Gestionar periodos y cargas académicas',
               'La carga se crea en borrador; al enviarla a revisión se inicia el proceso BPMN carga_academica en Camunda y '
               'las aprobaciones posteriores completan las tareas de usuario correspondientes.',
               [m('actor', 'ui', 'Asigna materias a docentes y guarda'),
                m('ui', 'api', 'POST /api/cargas-academicas/ {periodo, materias}'),
                m('api', 'bd', 'Crear carga en estado borrador'),
                r('bd', 'api', 'Carga'),
                r('api', 'ui', '201 Carga (borrador)'),
                r('ui', 'actor', 'Muestra la carga'),
                m('actor', 'ui', 'Envía la carga a revisión'),
                m('ui', 'api', 'PATCH /api/cargas-academicas/{id}/ {estado: en_revision}'),
                opt('[la carga no tiene instancia LIDA]'),
                m('api', 'lida', 'POST /process-definition/key/carga_academica/start'),
                r('lida', 'api', '200 {id de instancia}'),
                fin(),
                m('api', 'bd', 'Guardar estado y camunda_instance_id'),
                r('bd', 'api', 'Actualizado'),
                r('api', 'ui', '200 Carga {camunda}'),
                r('ui', 'actor', 'Muestra la carga en revisión'),
                m('actor', 'ui', 'Aprueba o publica la carga'),
                m('ui', 'api', 'PATCH /api/cargas-academicas/{id}/ {estado: aprobada | publicada}'),
                m('api', 'lida', 'GET /task?processInstanceId&taskDefinitionKey'),
                r('lida', 'api', 'Tarea activa'),
                m('api', 'lida', 'POST /task/{id}/complete {aprobada | publicada}'),
                r('lida', 'api', '204 Tarea completada'),
                m('api', 'bd', 'Actualizar estado de la carga'),
                r('bd', 'api', 'Actualizado'),
                r('api', 'ui', '200 Carga actualizada'),
                r('ui', 'actor', 'Muestra la carga aprobada o publicada')]),
            ds('DS-COO-05', 'Enviar notificaciones masivas', 'CU-COO-13 Enviar notificaciones masivas',
               'El actor redacta un aviso para un grupo filtrado; la API crea la notificación interna de cada destinatario '
               'y envía el correo correspondiente.',
               [m('actor', 'ui', 'Redacta el aviso y elige el grupo'),
                m('ui', 'api', 'POST /api/coordinacion/notificaciones-masivas/ {grupo, asunto, mensaje}'),
                m('api', 'bd', 'Filtrar destinatarios por grupo'),
                r('bd', 'api', 'Destinatarios'),
                alt('[sin destinatarios]'),
                r('api', 'ui', '400 No hay destinatarios'),
                r('ui', 'actor', 'Muestra el aviso'),
                sino('[con destinatarios]'),
                loop('[por cada destinatario]'),
                m('api', 'bd', 'Crear notificación interna'),
                r('bd', 'api', 'Registrada'),
                asin('api', 'correo', 'send_mail(asunto, mensaje)'),
                fin(),
                r('api', 'ui', '200 {enviados, fallidos}'),
                r('ui', 'actor', 'Muestra el resumen del envío'),
                fin()]),
        ],
    },
    {
        'nombre': 'Servicios Escolares', 'sigla': 'SE',
        'intro': 'Servicios Escolares mantiene el control escolar. Sus secuencias muestran la actualización del expediente '
                 'del alumno, la validación de inscripciones y de solicitudes extemporáneas, el registro del egreso y la '
                 'generación de reportes institucionales.',
        'diagramas': [
            ds('DS-SE-01', 'Gestionar alumnos', 'CU-SE-02 Gestionar alumnos',
               'El actor edita los datos o el estatus de un alumno. La API valida unicidad y formato y registra el '
               'movimiento en el histórico.',
               [m('actor', 'ui', 'Edita los datos o el estatus del alumno'),
                m('ui', 'api', 'PATCH /api/servicios-escolares/alumnos/{id}/ {datos, estatus}'),
                s('api', 'Verificar JWT y rol de Servicios Escolares'),
                s('api', 'Validar CURP, correo, matrícula y programa'),
                alt('[datos inválidos o duplicados]'),
                r('api', 'ui', '400 Errores por campo'),
                r('ui', 'actor', 'Marca los campos con error'),
                sino('[datos válidos]'),
                m('api', 'bd', 'Actualizar alumno'),
                r('bd', 'api', 'Alumno actualizado'),
                m('api', 'bd', 'Registrar movimiento en el histórico'),
                r('bd', 'api', 'Evento registrado'),
                r('api', 'ui', '200 Alumno'),
                r('ui', 'actor', 'Muestra el expediente actualizado'),
                fin()]),
            ds('DS-SE-02', 'Validar inscripciones', 'CU-SE-06 Validar inscripciones',
               'El actor consulta las materias inscritas por el alumno y valida u observa la inscripción.',
               [m('actor', 'ui', 'Abre las inscripciones del alumno'),
                m('ui', 'api', 'GET /api/servicios-escolares/alumnos/{id}/'),
                m('api', 'bd', 'Consultar alumno e inscripciones del periodo'),
                r('bd', 'api', 'Inscripciones'),
                r('api', 'ui', '200 Alumno con inscripciones'),
                r('ui', 'actor', 'Muestra las materias inscritas'),
                m('actor', 'ui', 'Valida u observa la inscripción'),
                m('ui', 'api', 'POST /api/servicios-escolares/alumnos/{id}/validar-inscripcion/ {estado, observaciones}'),
                alt('[sin inscripciones por validar]'),
                r('api', 'ui', '400 No hay inscripciones pendientes'),
                r('ui', 'actor', 'Muestra el aviso'),
                sino('[inscripciones pendientes]'),
                m('api', 'bd', 'Actualizar estado de las inscripciones'),
                r('bd', 'api', 'Actualizadas'),
                m('api', 'bd', 'Registrar en el histórico'),
                r('bd', 'api', 'Evento registrado'),
                r('api', 'ui', '200 Inscripción validada u observada'),
                r('ui', 'actor', 'Actualiza el estado'),
                fin()]),
            ds('DS-SE-03', 'Validar solicitudes extemporáneas', 'CU-SE-05 Validar cargas y solicitudes extemporáneas',
               'El actor resuelve la solicitud de inscripción extemporánea; si la aprueba se crean las inscripciones y, '
               'opcionalmente, genera el oficio de autorización en PDF.',
               [m('actor', 'ui', 'Abre las solicitudes extemporáneas'),
                m('ui', 'api', 'GET /api/servicios-escolares/solicitudes-extemporaneas/'),
                m('api', 'bd', 'Consultar solicitudes y justificación'),
                r('bd', 'api', 'Solicitudes'),
                r('api', 'ui', '200 Lista'),
                r('ui', 'actor', 'Muestra las solicitudes'),
                m('actor', 'ui', 'Valida u observa la solicitud'),
                m('ui', 'api', 'PATCH /api/servicios-escolares/solicitudes-extemporaneas/{id}/ {estado, comentario}'),
                m('api', 'bd', 'Actualizar estado de la solicitud'),
                r('bd', 'api', 'Actualizada'),
                opt('[estado = aprobada]'),
                m('api', 'bd', 'Crear inscripciones extemporáneas'),
                r('bd', 'api', 'Inscripciones'),
                fin(),
                m('api', 'bd', 'Registrar notificación al alumno'),
                r('bd', 'api', 'Registrada'),
                r('api', 'ui', '200 Solicitud'),
                r('ui', 'actor', 'Muestra el nuevo estado'),
                opt('[generar oficio]'),
                m('actor', 'ui', 'Solicita el oficio de autorización'),
                m('ui', 'api', 'GET /api/servicios-escolares/solicitudes-extemporaneas/{id}/oficio/'),
                s('api', 'Generar el oficio en PDF'),
                r('api', 'ui', '200 application/pdf'),
                r('ui', 'actor', 'Descarga el oficio'),
                fin()]),
            ds('DS-SE-04', 'Registrar egreso', 'CU-SE-10 Registrar egreso',
               'La API verifica créditos y defensa aprobada antes de registrar el egreso, cambiar el estatus y habilitar el '
               'diploma digital.',
               [m('actor', 'ui', 'Selecciona al alumno y confirma el egreso'),
                m('ui', 'api', 'POST /api/egresados/ {alumno, fecha_egreso}'),
                m('api', 'bd', 'Consultar créditos y resultado de la defensa'),
                r('bd', 'api', 'Situación académica'),
                s('api', 'Verificar requisitos de egreso'),
                alt('[requisitos incompletos]'),
                r('api', 'ui', '400 {faltantes}'),
                r('ui', 'actor', 'Muestra los requisitos faltantes'),
                sino('[requisitos cumplidos]'),
                m('api', 'bd', 'Registrar egreso y estatus egresado'),
                r('bd', 'api', 'Egreso'),
                m('api', 'bd', 'Registrar evento en el histórico'),
                r('bd', 'api', 'Evento registrado'),
                r('api', 'ui', '201 Egreso (diploma habilitado)'),
                r('ui', 'actor', 'Confirma el egreso'),
                fin()]),
            ds('DS-SE-05', 'Generar reportes institucionales', 'CU-SE-13 Generar reportes institucionales',
               'El reporte se genera en XLSX o PDF; los valores se neutralizan para evitar la inyección de fórmulas.',
               [m('actor', 'ui', 'Elige el reporte y el formato'),
                m('ui', 'api', 'GET /api/servicios-escolares/reportes/?tipo&formato'),
                s('api', 'Verificar JWT y rol de Servicios Escolares'),
                m('api', 'bd', 'Consultar los datos del reporte'),
                r('bd', 'api', 'Registros'),
                alt('[sin registros]'),
                r('api', 'ui', 'Respuesta sin datos'),
                r('ui', 'actor', 'Informa que no hay información'),
                sino('[con registros]'),
                s('api', 'Neutralizar fórmulas y generar XLSX o PDF'),
                r('api', 'ui', '200 Archivo del reporte'),
                r('ui', 'actor', 'Descarga el archivo'),
                fin()]),
        ],
    },
    {
        'nombre': 'Aspirante', 'sigla': 'ASP',
        'intro': 'El Aspirante recorre el proceso de admisión. Sus secuencias abarcan el preregistro con inicio del proceso '
                 'LIDA, la carga validada de documentos, la presentación de exámenes en línea, la solicitud de apoyo '
                 'económico y la consulta periódica del seguimiento y las notificaciones.',
        'diagramas': [
            ds('DS-ASP-01', 'Registrar preregistro', 'CU-ASP-01 Registrar preregistro',
               'El registro público crea la cuenta con rol aspirante e inicia la instancia del proceso BPMN '
               'sinac_preregistro_v1 en Camunda. Si el motor no responde, la cuenta se conserva y el proceso puede '
               'iniciarse después.',
               [m('actor', 'ui', 'Captura datos personales, CURP, programa y contraseña'),
                s('ui', 'Validar formato en el formulario'),
                m('ui', 'api', 'POST /api/preregistro/ {datos del aspirante}'),
                s('api', 'Aplicar throttling de registro'),
                s('api', 'Validar CURP, correo, usuario y robustez de la contraseña'),
                alt('[datos inválidos o duplicados]'),
                r('api', 'ui', '400 Errores por campo'),
                r('ui', 'actor', 'Marca los campos con error'),
                sino('[datos válidos]'),
                m('api', 'bd', 'Crear Aspirante con rol aspirante'),
                r('bd', 'api', 'Aspirante (business_key)'),
                m('api', 'lida', 'POST /process-definition/key/sinac_preregistro_v1/start'),
                r('lida', 'api', '200 {id de instancia}'),
                m('api', 'bd', 'Guardar camunda_instance_id y proceso_estado'),
                r('bd', 'api', 'Actualizado'),
                r('api', 'ui', '201 {aspirante, camunda_id}'),
                r('ui', 'actor', 'Confirma el registro'),
                fin()]),
            ds('DS-ASP-02', 'Cargar documentos de admisión', 'CU-ASP-03 Cargar documentos de admisión',
               'El archivo se valida por contenido real, extensión y tamaño; se almacena, se registra pendiente de revisión '
               'y se notifica al flujo BPMN con el mensaje DocumentoCargado.',
               [m('actor', 'ui', 'Selecciona el PDF y lo sube'),
                m('ui', 'api', 'POST /api/preregistro/documentos/ (multipart: tipo, archivo)'),
                m('api', 'bd', 'Consultar estado de la solicitud'),
                r('bd', 'api', 'Estado'),
                s('api', 'Validar tipo real, extensión y tamaño'),
                alt('[solicitud resuelta]'),
                r('api', 'ui', '409 Documentos en solo lectura'),
                r('ui', 'actor', 'Muestra el aviso'),
                sino('[archivo inválido]'),
                r('api', 'ui', '400 Archivo no permitido'),
                r('ui', 'actor', 'Muestra el motivo'),
                sino('[archivo válido]'),
                m('api', 'media', 'Guardar archivo en aspirantes/AAAA/MM/'),
                r('media', 'api', 'Ruta del archivo'),
                m('api', 'bd', 'Crear o reemplazar DocumentoAspirante'),
                r('bd', 'api', 'Documento pendiente de revisión'),
                asin('api', 'lida', 'POST /message DocumentoCargado'),
                r('api', 'ui', '201 Documento'),
                r('ui', 'actor', 'Muestra el documento pendiente de revisión'),
                fin()]),
            ds('DS-ASP-03', 'Presentar examen en línea', 'CU-ASP-04 Presentar examen en línea',
               'El avance se guarda localmente mientras el aspirante responde; al enviar, la API verifica ventana e intentos, '
               'califica y registra el intento.',
               [m('actor', 'ui', 'Abre la sección de exámenes'),
                m('ui', 'api', 'GET /api/preregistro/examenes/'),
                m('api', 'bd', 'Consultar exámenes asignados e intentos'),
                r('bd', 'api', 'Exámenes'),
                r('api', 'ui', '200 Exámenes (sin respuestas correctas)'),
                r('ui', 'actor', 'Muestra los exámenes disponibles'),
                m('actor', 'ui', 'Inicia el examen'),
                s('ui', 'Iniciar temporizador'),
                r('ui', 'actor', 'Muestra las preguntas'),
                loop('[por cada pregunta]'),
                m('actor', 'ui', 'Selecciona una respuesta'),
                s('ui', 'Guardar avance localmente'),
                r('ui', 'actor', 'Marca la pregunta como respondida'),
                fin(),
                m('actor', 'ui', 'Envía respuestas (o se agota el tiempo)'),
                m('ui', 'api', 'POST /api/preregistro/examenes/ {examen, respuestas}'),
                m('api', 'bd', 'Consultar ventana e intentos'),
                r('bd', 'api', 'Examen'),
                alt('[fuera de ventana o sin intentos]'),
                r('api', 'ui', '400 Examen no disponible'),
                r('ui', 'actor', 'Muestra el motivo y conserva respuestas'),
                sino('[envío válido]'),
                s('api', 'Calificar respuestas'),
                m('api', 'bd', 'Registrar intento y puntaje'),
                r('bd', 'api', 'Intento'),
                r('api', 'ui', '201 Resultado'),
                s('ui', 'Limpiar el avance local'),
                r('ui', 'actor', 'Muestra el resultado'),
                fin()]),
            ds('DS-ASP-04', 'Solicitar apoyo económico', 'CU-ASP-07 Solicitar apoyo económico',
               'La CLABE se valida en longitud y dígito verificador; un apoyo ya autorizado no admite cambios.',
               [m('actor', 'ui', 'Captura banco y CLABE'),
                m('ui', 'api', 'POST /api/preregistro/apoyo/solicitar/ {banco, clabe}'),
                m('api', 'bd', 'Consultar estado del apoyo'),
                r('bd', 'api', 'Estado del apoyo'),
                s('api', 'Validar 18 dígitos y dígito verificador'),
                alt('[apoyo ya autorizado]'),
                r('api', 'ui', '409 Datos no modificables'),
                r('ui', 'actor', 'Muestra el aviso'),
                sino('[CLABE inválida]'),
                r('api', 'ui', '400 CLABE inválida'),
                r('ui', 'actor', 'Marca el campo con error'),
                sino('[datos válidos]'),
                m('api', 'bd', 'Guardar solicitud de apoyo'),
                r('bd', 'api', 'Solicitud registrada'),
                r('api', 'ui', '200 Solicitud de apoyo'),
                r('ui', 'actor', 'Confirma la solicitud'),
                fin()]),
            ds('DS-ASP-05', 'Consultar seguimiento y notificaciones', 'CU-ASP-02 y CU-ASP-06',
               'El panel consulta periódicamente el seguimiento para actualizar etapas y el contador de notificaciones; el '
               'aspirante puede marcarlas como leídas.',
               [m('actor', 'ui', 'Abre la sección Proceso LIDA'),
                loop('[cada 30 s mientras la sesión está activa]'),
                m('ui', 'api', 'GET /api/preregistro/seguimiento/'),
                m('api', 'bd', 'Consultar seguimiento, dictamen y notificaciones'),
                r('bd', 'api', 'Eventos'),
                r('api', 'ui', '200 Etapas y no leídas'),
                s('ui', 'Actualizar etapas y contador'),
                fin(),
                r('ui', 'actor', 'Muestra etapas y dictamen'),
                m('actor', 'ui', 'Marca las notificaciones como leídas'),
                m('ui', 'api', 'POST /api/preregistro/notificaciones/marcar-leidas/ {ids}'),
                m('api', 'bd', 'Marcar notificaciones como leídas'),
                r('bd', 'api', 'Actualizadas'),
                r('api', 'ui', '200 {no_leidas}'),
                r('ui', 'actor', 'Actualiza el contador')]),
        ],
    },
    {
        'nombre': 'Alumno', 'sigla': 'ALU',
        'intro': 'El Alumno utiliza el sistema durante su trayectoria académica. Sus secuencias cubren la inscripción de '
                 'materias, las solicitudes académicas, la solicitud de director de tesis, la gestión del proyecto de tesis '
                 'y la descarga del diploma digital.',
        'diagramas': [
            ds('DS-ALU-01', 'Inscribir materias del periodo', 'CU-ALU-02 Inscribir materias del periodo',
               'La API valida periodo abierto, cupo y número mínimo de materias; las inscripciones quedan pendientes de '
               'validación por Servicios Escolares.',
               [m('actor', 'ui', 'Abre materias e inscripciones'),
                m('ui', 'api', 'GET /api/preregistro/materias/'),
                m('api', 'bd', 'Consultar periodo activo y oferta publicada'),
                r('bd', 'api', 'Materias con cupo'),
                r('api', 'ui', '200 Oferta del periodo'),
                r('ui', 'actor', 'Muestra la oferta'),
                m('actor', 'ui', 'Selecciona materias y envía'),
                m('ui', 'api', 'POST /api/preregistro/inscripciones/ {materias}'),
                s('api', 'Validar periodo abierto, cupo y mínimo de materias'),
                alt('[periodo cerrado o reglas incumplidas]'),
                r('api', 'ui', '400 Motivo del rechazo'),
                r('ui', 'actor', 'Ofrece solicitar inscripción extemporánea'),
                sino('[inscripción válida]'),
                loop('[por cada materia]'),
                m('api', 'bd', 'Crear inscripción pendiente de validación'),
                r('bd', 'api', 'Inscripción'),
                fin(),
                m('api', 'bd', 'Registrar evento en el histórico'),
                r('bd', 'api', 'Evento registrado'),
                r('api', 'ui', '201 Inscripciones'),
                r('ui', 'actor', 'Muestra la inscripción enviada'),
                fin(),
                opt('[descargar boleta]'),
                m('actor', 'ui', 'Descarga la boleta de inscripción'),
                m('ui', 'api', 'GET /api/preregistro/boleta-inscripcion/download/'),
                s('api', 'Generar la boleta en PDF'),
                r('api', 'ui', '200 application/pdf'),
                r('ui', 'actor', 'Descarga el archivo'),
                fin()]),
            ds('DS-ALU-02', 'Enviar solicitud académica', 'CU-ALU-05 Enviar solicitud académica',
               'La solicitud se registra pendiente y se notifica al área responsable; el alumno consulta después la respuesta.',
               [m('actor', 'ui', 'Elige el tipo y describe la solicitud'),
                m('ui', 'api', 'POST /api/preregistro/solicitudes-academicas/ {tipo, descripcion}'),
                s('api', 'Validar campos obligatorios'),
                alt('[datos incompletos]'),
                r('api', 'ui', '400 Errores por campo'),
                r('ui', 'actor', 'Marca los campos con error'),
                sino('[datos completos]'),
                m('api', 'bd', 'Registrar solicitud pendiente'),
                r('bd', 'api', 'Solicitud'),
                m('api', 'bd', 'Notificar al área responsable'),
                r('bd', 'api', 'Notificación registrada'),
                r('api', 'ui', '201 Solicitud'),
                r('ui', 'actor', 'Muestra la solicitud registrada'),
                fin(),
                m('actor', 'ui', 'Consulta la respuesta'),
                m('ui', 'api', 'GET /api/preregistro/solicitudes-academicas/'),
                m('api', 'bd', 'Consultar solicitudes del alumno'),
                r('bd', 'api', 'Solicitudes'),
                r('api', 'ui', '200 Solicitudes con respuesta'),
                r('ui', 'actor', 'Muestra estado y respuesta')]),
            ds('DS-ALU-03', 'Solicitar director de tesis', 'CU-ALU-06 Solicitar director de tesis',
               'La API impide duplicar solicitudes pendientes y notifica al director sugerido y a la Coordinación.',
               [m('actor', 'ui', 'Captura línea de investigación y director sugerido'),
                m('ui', 'api', 'POST /api/tesis/flujo/ {linea, director}'),
                m('api', 'bd', 'Buscar solicitud pendiente del alumno'),
                r('bd', 'api', 'Resultado'),
                alt('[ya existe una solicitud pendiente]'),
                r('api', 'ui', '400 Solicitud en revisión'),
                r('ui', 'actor', 'Muestra el aviso'),
                sino('[sin solicitud pendiente]'),
                m('api', 'bd', 'Crear solicitud de dirección (pendiente)'),
                r('bd', 'api', 'Solicitud'),
                m('api', 'bd', 'Notificar al director y a Coordinación'),
                r('bd', 'api', 'Notificaciones registradas'),
                r('api', 'ui', '201 Solicitud'),
                r('ui', 'actor', 'Muestra la solicitud en revisión'),
                fin()]),
            ds('DS-ALU-04', 'Gestionar proyecto de tesis', 'CU-ALU-07 Gestionar proyecto de tesis',
               'El alumno con director asignado registra su proyecto y consulta su avance, jurado, revisión antiplagio y defensa.',
               [m('actor', 'ui', 'Registra título y resumen del proyecto'),
                m('ui', 'api', 'POST /api/proyectos-tesis/ {titulo, resumen}'),
                m('api', 'bd', 'Verificar director asignado'),
                r('bd', 'api', 'Director'),
                alt('[sin director asignado]'),
                r('api', 'ui', '400 Requiere director de tesis'),
                r('ui', 'actor', 'Muestra el aviso'),
                sino('[con director]'),
                m('api', 'bd', 'Crear proyecto en revisión'),
                r('bd', 'api', 'Proyecto'),
                r('api', 'ui', '201 Proyecto'),
                r('ui', 'actor', 'Muestra el proyecto'),
                fin(),
                m('actor', 'ui', 'Consulta avance, jurado y antiplagio'),
                m('ui', 'api', 'GET /api/proyectos-tesis/{id}/'),
                m('api', 'bd', 'Consultar proyecto, jurado, revisiones y defensa'),
                r('bd', 'api', 'Detalle'),
                r('api', 'ui', '200 Detalle del proyecto'),
                r('ui', 'actor', 'Muestra el avance')]),
            ds('DS-ALU-05', 'Descargar diploma digital', 'CU-ALU-10 Descargar diploma digital',
               'El diploma solo se genera si el egreso está registrado.',
               [m('actor', 'ui', 'Selecciona "Descargar diploma"'),
                m('ui', 'api', 'GET /api/proyectos-tesis/{id}/diploma/'),
                m('api', 'bd', 'Verificar egreso y defensa aprobada'),
                r('bd', 'api', 'Situación'),
                alt('[sin egreso registrado]'),
                r('api', 'ui', '403 Diploma no disponible'),
                r('ui', 'actor', 'Muestra la opción deshabilitada'),
                sino('[egresado]'),
                s('api', 'Generar diploma digital en PDF'),
                r('api', 'ui', '200 application/pdf'),
                r('ui', 'actor', 'Descarga el diploma'),
                fin()]),
        ],
    },
    {
        'nombre': 'Docente', 'sigla': 'DOC',
        'intro': 'El Docente evalúa a sus estudiantes y participa en la admisión. Sus secuencias describen la captura de '
                 'calificaciones, la gestión de exámenes en línea, la conducción de entrevistas virtuales con Jitsi y LIDA '
                 'y la evaluación en el Colegio de Profesores.',
        'diagramas': [
            ds('DS-DOC-01', 'Capturar calificaciones', 'CU-DOC-03 Capturar calificaciones',
               'La API comprueba que la materia pertenece al docente, valida el rango y el periodo de captura y registra el '
               'movimiento en el histórico.',
               [m('actor', 'ui', 'Abre el curso'),
                m('ui', 'api', 'GET /api/docente/materias/{id}/'),
                s('api', 'Verificar que la materia pertenece al docente'),
                m('api', 'bd', 'Consultar estudiantes inscritos'),
                r('bd', 'api', 'Estudiantes'),
                r('api', 'ui', '200 Curso y estudiantes'),
                r('ui', 'actor', 'Muestra la lista'),
                m('actor', 'ui', 'Captura la calificación'),
                m('ui', 'api', 'POST /api/docente/calificaciones/ {inscripcion, calificacion}'),
                s('api', 'Validar rango y periodo de captura'),
                alt('[fuera de rango o periodo cerrado]'),
                r('api', 'ui', '400 Motivo del rechazo'),
                r('ui', 'actor', 'Marca el campo con error'),
                sino('[calificación válida]'),
                m('api', 'bd', 'Guardar calificación'),
                r('bd', 'api', 'Calificación'),
                m('api', 'bd', 'Registrar movimiento en el histórico'),
                r('bd', 'api', 'Evento registrado'),
                r('api', 'ui', '201 Calificación'),
                r('ui', 'actor', 'Muestra la calificación guardada'),
                fin(),
                opt('[generar acta]'),
                m('actor', 'ui', 'Descarga el acta del curso'),
                m('ui', 'api', 'GET /api/docente/actas/{materia_id}/'),
                s('api', 'Generar el acta en PDF'),
                r('api', 'ui', '200 application/pdf'),
                r('ui', 'actor', 'Descarga el acta'),
                fin()]),
            ds('DS-DOC-02', 'Gestionar exámenes en línea', 'CU-DOC-04 Gestionar exámenes en línea',
               'El docente crea el examen, agrega preguntas y lo publica. Si ya existen intentos, la edición de preguntas se bloquea.',
               [m('actor', 'ui', 'Crea el examen con fechas, duración e intentos'),
                m('ui', 'api', 'POST /api/examenes-gestion/ {titulo, ventana, intentos, evaluados}'),
                m('api', 'bd', 'Crear examen'),
                r('bd', 'api', 'Examen'),
                r('api', 'ui', '201 Examen'),
                r('ui', 'actor', 'Muestra el examen en borrador'),
                m('actor', 'ui', 'Agrega preguntas y publica'),
                m('ui', 'api', 'PUT /api/docente/examenes/{id}/ {preguntas, publicado}'),
                m('api', 'bd', 'Consultar intentos registrados'),
                r('bd', 'api', 'Intentos'),
                alt('[existen intentos]'),
                r('api', 'ui', '409 Edición de preguntas bloqueada'),
                r('ui', 'actor', 'Muestra el aviso'),
                sino('[sin intentos]'),
                m('api', 'bd', 'Guardar preguntas y publicar'),
                r('bd', 'api', 'Examen publicado'),
                r('api', 'ui', '200 Examen'),
                r('ui', 'actor', 'Confirma la publicación'),
                fin(),
                m('actor', 'ui', 'Consulta resultados'),
                m('ui', 'api', 'GET /api/docente/examenes/{id}/'),
                m('api', 'bd', 'Consultar intentos y puntajes'),
                r('bd', 'api', 'Resultados'),
                r('api', 'ui', '200 Resultados'),
                r('ui', 'actor', 'Muestra los resultados')]),
            ds('DS-DOC-03', 'Conducir entrevista virtual', 'CU-DOC-05 Conducir entrevista virtual',
               'La entrevista se programa e inicia el proceso BPMN sinac_entrevista_v1. Al iniciarla se habilita el enlace '
               'seguro de Jitsi y al terminar se registran notas privadas no visibles para el aspirante.',
               [m('actor', 'ui', 'Programa fecha y hora para el aspirante'),
                m('ui', 'api', 'POST /api/docente/entrevistas/ {aspirante, fecha}'),
                m('api', 'bd', 'Crear entrevista programada con sala'),
                r('bd', 'api', 'Entrevista'),
                opt('[motor LIDA configurado]'),
                m('api', 'lida', 'POST /process-definition/key/sinac_entrevista_v1/start'),
                r('lida', 'api', '200 {id de instancia}'),
                m('api', 'bd', 'Guardar camunda_instance_id'),
                r('bd', 'api', 'Actualizado'),
                fin(),
                r('api', 'ui', '201 Entrevista'),
                r('ui', 'actor', 'Muestra la entrevista programada'),
                m('actor', 'ui', 'Inicia la entrevista'),
                m('ui', 'api', 'PUT /api/docente/entrevistas/{id}/ {estado: iniciada}'),
                m('api', 'bd', 'Actualizar estado y habilitar enlace'),
                r('bd', 'api', 'Actualizado'),
                r('api', 'ui', '200 {enlace seguro}'),
                m('ui', 'jitsi', 'Abrir sala de videollamada'),
                r('jitsi', 'ui', 'Sesión activa'),
                r('ui', 'actor', 'Muestra la videollamada'),
                m('actor', 'ui', 'Registra notas privadas y evaluación'),
                m('ui', 'api', 'PUT /api/docente/entrevistas/{id}/ {estado: completada, notas}'),
                m('api', 'bd', 'Guardar notas privadas y resultado'),
                r('bd', 'api', 'Actualizado'),
                r('api', 'ui', '200 Entrevista completada'),
                r('ui', 'actor', 'Confirma el registro')]),
            ds('DS-DOC-04', 'Evaluar aspirante en Colegio', 'CU-DOC-06 Evaluar aspirante en Colegio',
               'El docente consulta los resultados del aspirante y registra o actualiza su evaluación, que se integra al '
               'dictamen colegiado.',
               [m('actor', 'ui', 'Consulta el expediente del aspirante'),
                m('ui', 'api', 'GET /api/preregistro/evaluaciones-colegio/?aspirante={id}'),
                m('api', 'bd', 'Consultar exámenes, entrevistas y evaluaciones'),
                r('bd', 'api', 'Resultados'),
                r('api', 'ui', '200 Expediente de evaluación'),
                r('ui', 'actor', 'Muestra los resultados'),
                m('actor', 'ui', 'Registra su evaluación'),
                alt('[sin evaluación previa]'),
                m('ui', 'api', 'POST /api/preregistro/evaluaciones-colegio/ {aspirante, dictamen, observaciones}'),
                m('api', 'bd', 'Crear evaluación'),
                r('bd', 'api', 'Evaluación'),
                r('api', 'ui', '201 Evaluación'),
                sino('[evaluación existente]'),
                m('ui', 'api', 'PATCH /api/preregistro/evaluaciones-colegio/{id}/ {dictamen, observaciones}'),
                m('api', 'bd', 'Actualizar evaluación'),
                r('bd', 'api', 'Evaluación'),
                r('api', 'ui', '200 Evaluación'),
                fin(),
                r('ui', 'actor', 'Muestra la evaluación integrada al dictamen')]),
        ],
    },
    {
        'nombre': 'Director de tesis', 'sigla': 'DIR',
        'intro': 'El Director de tesis acompaña a sus tesistas desde la solicitud de dirección hasta la defensa. Sus '
                 'secuencias incluyen la respuesta a la solicitud, el examen predoctoral, la integración del jurado, la '
                 'revisión antiplagio y la programación y resultado de la defensa.',
        'diagramas': [
            ds('DS-DIR-01', 'Responder solicitud de dirección', 'CU-DIR-02 Responder solicitud de dirección',
               'Al aceptar, el director queda vinculado al alumno y el evento se registra para ambos; en cualquier caso se '
               'notifica al alumno y a la Coordinación.',
               [m('actor', 'ui', 'Abre su panel'),
                m('ui', 'api', 'GET /api/director/panel/'),
                m('api', 'bd', 'Consultar solicitudes dirigidas al director'),
                r('bd', 'api', 'Solicitudes'),
                r('api', 'ui', '200 Panel con solicitudes'),
                r('ui', 'actor', 'Muestra alumno y línea de investigación'),
                m('actor', 'ui', 'Acepta o rechaza con comentario'),
                m('ui', 'api', 'PATCH /api/tesis/solicitudes/{id}/ {accion, comentario}'),
                s('api', 'Verificar que la solicitud pertenece al director'),
                alt('[aceptar]'),
                m('api', 'bd', 'Marcar aceptada y asignar director al alumno'),
                r('bd', 'api', 'Actualizado'),
                m('api', 'bd', 'Registrar evento para alumno y director'),
                r('bd', 'api', 'Eventos registrados'),
                sino('[rechazar]'),
                m('api', 'bd', 'Marcar rechazada con comentario'),
                r('bd', 'api', 'Actualizado'),
                fin(),
                m('api', 'bd', 'Notificar al alumno y a Coordinación'),
                r('bd', 'api', 'Notificaciones registradas'),
                r('api', 'ui', '200 Solicitud resuelta'),
                r('ui', 'actor', 'Actualiza la bandeja')]),
            ds('DS-DIR-02', 'Programar examen predoctoral', 'CU-DIR-05 Programar examen predoctoral',
               'El director programa el examen de su tesista con fecha y sinodales y después registra el resultado.',
               [m('actor', 'ui', 'Programa fecha y sinodales'),
                m('ui', 'api', 'POST /api/predoctoral/examenes/ {alumno, fecha, sinodales}'),
                s('api', 'Validar que el alumno es tesista del director'),
                alt('[datos inválidos]'),
                r('api', 'ui', '400 Errores por campo'),
                r('ui', 'actor', 'Marca los campos con error'),
                sino('[datos válidos]'),
                m('api', 'bd', 'Crear examen predoctoral programado'),
                r('bd', 'api', 'Examen'),
                m('api', 'bd', 'Notificar al alumno y a Coordinación'),
                r('bd', 'api', 'Notificaciones registradas'),
                r('api', 'ui', '201 Examen predoctoral'),
                r('ui', 'actor', 'Muestra la programación'),
                fin(),
                m('actor', 'ui', 'Registra el resultado'),
                m('ui', 'api', 'PATCH /api/predoctoral/examenes/{id}/ {resultado, observaciones}'),
                m('api', 'bd', 'Guardar resultado'),
                r('bd', 'api', 'Actualizado'),
                r('api', 'ui', '200 Examen con resultado'),
                r('ui', 'actor', 'Muestra el resultado')]),
            ds('DS-DIR-03', 'Integrar jurado de defensa', 'CU-DIR-06 Integrar jurado de defensa',
               'Los integrantes se eligen de los docentes disponibles; la API rechaza duplicados y proyectos no aprobados.',
               [m('actor', 'ui', 'Abre la integración de jurado'),
                m('ui', 'api', 'GET /api/jurados-disponibles/'),
                m('api', 'bd', 'Consultar docentes e investigadores activos'),
                r('bd', 'api', 'Candidatos'),
                r('api', 'ui', '200 Candidatos'),
                r('ui', 'actor', 'Muestra los candidatos'),
                m('actor', 'ui', 'Selecciona integrante y función'),
                m('ui', 'api', 'POST /api/proyectos-tesis/{id}/jurado/ {docente, rol}'),
                m('api', 'bd', 'Verificar proyecto aprobado e integrantes actuales'),
                r('bd', 'api', 'Jurado actual'),
                alt('[integrante duplicado o proyecto no aprobado]'),
                r('api', 'ui', '400 Motivo del rechazo'),
                r('ui', 'actor', 'Muestra el motivo'),
                sino('[integrante válido]'),
                m('api', 'bd', 'Registrar integrante del jurado'),
                r('bd', 'api', 'Integrante'),
                m('api', 'bd', 'Notificar al integrante'),
                r('bd', 'api', 'Notificación registrada'),
                r('api', 'ui', '201 Integrante agregado'),
                r('ui', 'actor', 'Actualiza el jurado'),
                fin()]),
            ds('DS-DIR-04', 'Registrar revisión antiplagio', 'CU-DIR-07 Registrar revisión antiplagio',
               'La tesis se valida como PDF real antes de almacenarse; se registra el porcentaje de similitud.',
               [m('actor', 'ui', 'Carga la tesis en PDF y el porcentaje de similitud'),
                m('ui', 'api', 'POST /api/proyectos-tesis/{id}/revision-antiplagio/ (multipart)'),
                s('api', 'Validar tipo real, extensión y tamaño'),
                alt('[archivo inválido]'),
                r('api', 'ui', '400 Archivo no permitido'),
                r('ui', 'actor', 'Muestra el motivo'),
                sino('[archivo válido]'),
                m('api', 'media', 'Guardar archivo en antiplagio/AAAA/MM/'),
                r('media', 'api', 'Ruta del archivo'),
                m('api', 'bd', 'Registrar revisión y similitud'),
                r('bd', 'api', 'Revisión'),
                r('api', 'ui', '201 Revisión registrada'),
                r('ui', 'actor', 'Muestra el resultado'),
                fin()]),
            ds('DS-DIR-05', 'Programar defensa y registrar resultado', 'CU-DIR-08 Programar defensa y registrar resultado',
               'La defensa requiere jurado integrado y antiplagio aprobado; el resultado aprobatorio habilita el egreso.',
               [m('actor', 'ui', 'Programa la defensa'),
                m('ui', 'api', 'POST /api/proyectos-tesis/{id}/defensa/ {fecha, sede}'),
                m('api', 'bd', 'Verificar jurado integrado y antiplagio aprobado'),
                r('bd', 'api', 'Requisitos'),
                alt('[requisitos pendientes]'),
                r('api', 'ui', '400 Requisitos pendientes'),
                r('ui', 'actor', 'Muestra los pendientes'),
                sino('[requisitos cumplidos]'),
                m('api', 'bd', 'Registrar defensa programada'),
                r('bd', 'api', 'Defensa'),
                m('api', 'bd', 'Notificar al alumno y al jurado'),
                r('bd', 'api', 'Notificaciones registradas'),
                r('api', 'ui', '201 Defensa programada'),
                r('ui', 'actor', 'Muestra la fecha'),
                fin(),
                m('actor', 'ui', 'Registra el resultado'),
                m('ui', 'api', 'PATCH /api/proyectos-tesis/{id}/defensa/ {resultado, acta}'),
                m('api', 'bd', 'Guardar resultado y concluir proyecto'),
                r('bd', 'api', 'Actualizado'),
                r('api', 'ui', '200 Defensa con resultado'),
                r('ui', 'actor', 'Indica que el egreso está habilitado')]),
        ],
    },
    {
        'nombre': 'Administrador', 'sigla': 'ADM',
        'intro': 'El Administrador mantiene la plataforma. Sus secuencias muestran la gestión de usuarios con desbloqueo de '
                 'cuentas, la administración de catálogos, la consulta de la auditoría y la configuración de seguridad; '
                 'toda acción de escritura queda registrada en la bitácora de auditoría.',
        'diagramas': [
            ds('DS-ADM-01', 'Gestionar usuarios y roles', 'CU-ADM-02 Gestionar usuarios y roles',
               'El administrador crea usuarios con su rol y puede desbloquear cuentas bloqueadas por intentos fallidos; cada '
               'acción se audita.',
               [m('actor', 'ui', 'Crea un usuario y asigna el rol'),
                m('ui', 'api', 'POST /api/administracion/usuarios/ {datos, rol}'),
                s('api', 'Verificar JWT y rol administrador'),
                m('api', 'bd', 'Verificar unicidad de usuario, correo y CURP'),
                r('bd', 'api', 'Resultado'),
                alt('[usuario existente]'),
                r('api', 'ui', '400 Usuario existente'),
                r('ui', 'actor', 'Marca el campo con error'),
                sino('[datos únicos]'),
                m('api', 'bd', 'Crear usuario con contraseña cifrada'),
                r('bd', 'api', 'Usuario'),
                m('api', 'bd', 'Registrar acción en auditoría'),
                r('bd', 'api', 'Registrada'),
                r('api', 'ui', '201 Usuario'),
                r('ui', 'actor', 'Muestra el usuario creado'),
                fin(),
                opt('[desbloquear cuenta]'),
                m('actor', 'ui', 'Selecciona "Desbloquear"'),
                m('ui', 'api', 'PATCH /api/administracion/usuarios/{id}/ {desbloquear}'),
                m('api', 'bd', 'Reiniciar intentos y login_locked_until'),
                r('bd', 'api', 'Actualizado'),
                m('api', 'bd', 'Registrar acción en auditoría'),
                r('bd', 'api', 'Registrada'),
                r('api', 'ui', '200 Usuario desbloqueado'),
                r('ui', 'actor', 'Actualiza el estado de la cuenta'),
                fin()]),
            ds('DS-ADM-02', 'Gestionar catálogos', 'CU-ADM-04 Gestionar catálogos',
               'Los elementos de catálogo se validan contra duplicados antes de guardarse y auditarse.',
               [m('actor', 'ui', 'Abre catálogos'),
                m('ui', 'api', 'GET /api/administracion/catalogos/'),
                m('api', 'bd', 'Consultar catálogos'),
                r('bd', 'api', 'Catálogos'),
                r('api', 'ui', '200 Catálogos'),
                r('ui', 'actor', 'Muestra los catálogos'),
                m('actor', 'ui', 'Agrega o modifica un elemento'),
                m('ui', 'api', 'POST /api/administracion/catalogos/ {catalogo, valor}'),
                s('api', 'Validar datos y duplicados'),
                alt('[dato inválido o duplicado]'),
                r('api', 'ui', '400 Errores por campo'),
                r('ui', 'actor', 'Marca el campo con error'),
                sino('[dato válido]'),
                m('api', 'bd', 'Guardar elemento'),
                r('bd', 'api', 'Elemento'),
                m('api', 'bd', 'Registrar acción en auditoría'),
                r('bd', 'api', 'Registrada'),
                r('api', 'ui', '201 Elemento'),
                r('ui', 'actor', 'Actualiza el catálogo'),
                fin()]),
            ds('DS-ADM-03', 'Consultar auditoría', 'CU-ADM-08 Consultar auditoría',
               'La bitácora se consulta con filtros y paginación.',
               [m('actor', 'ui', 'Aplica filtros (usuario, acción, fechas)'),
                m('ui', 'api', 'GET /api/administracion/auditoria/?filtros&pagina'),
                s('api', 'Verificar JWT y rol administrador'),
                m('api', 'bd', 'Consultar bitácora paginada'),
                r('bd', 'api', 'Eventos'),
                alt('[sin coincidencias]'),
                r('api', 'ui', '200 Lista vacía'),
                r('ui', 'actor', 'Muestra estado vacío'),
                sino('[con eventos]'),
                r('api', 'ui', '200 Eventos de auditoría'),
                r('ui', 'actor', 'Muestra la bitácora'),
                fin()]),
            ds('DS-ADM-04', 'Configurar seguridad y sistema', 'CU-ADM-09 Configurar seguridad y sistema',
               'Los parámetros de seguridad (intentos antes del bloqueo, mantenimiento, etc.) se validan por rango antes de '
               'guardarse y auditarse.',
               [m('actor', 'ui', 'Abre la configuración'),
                m('ui', 'api', 'GET /api/administracion/configuracion/'),
                m('api', 'bd', 'Consultar configuración del sistema'),
                r('bd', 'api', 'Parámetros'),
                r('api', 'ui', '200 Parámetros'),
                r('ui', 'actor', 'Muestra los parámetros'),
                m('actor', 'ui', 'Modifica intentos de bloqueo y mantenimiento'),
                m('ui', 'api', 'PUT /api/administracion/configuracion/ {parámetros}'),
                s('api', 'Validar rangos permitidos'),
                alt('[valores fuera de rango]'),
                r('api', 'ui', '400 Errores por campo'),
                r('ui', 'actor', 'Marca los campos con error'),
                sino('[valores válidos]'),
                m('api', 'bd', 'Guardar configuración'),
                r('bd', 'api', 'Actualizada'),
                m('api', 'bd', 'Registrar acción en auditoría'),
                r('bd', 'api', 'Registrada'),
                r('api', 'ui', '200 Configuración'),
                r('ui', 'actor', 'Confirma los cambios'),
                fin()]),
        ],
    },
]


# --------------------------------------------------------------------------------------------
# Secciones del documento
# --------------------------------------------------------------------------------------------

class Contador:
    figura = 0


def bloque_diagrama(actor, d):
    Contador.figura += 1
    detalle = Paragraph(f'<b>Caso de uso relacionado:</b> {d["cu"]}<br/>{d["descripcion"]}', cuerpo)
    figura = DiagramaAjustado(diagrama_secuencia(actor, d['pasos']), alto_maximo=600, reserva=26)
    pie = Paragraph(f'Figura {Contador.figura}. Diagrama de secuencia {d["id"]}: {d["nombre"]}.', pie_fig)
    return [KeepTogether([titulo(f'{d["id"]} {d["nombre"]}', h3, 2), detalle, figura, pie])]


def introduccion():
    hist = [titulo('1. Introducción', h1, 0)]
    hist.append(titulo('1.1 Propósito', h2, 1))
    hist.append(Paragraph(
        'Este documento presenta los diagramas de secuencia de SINAC NEXT, el sistema de información académica basado en '
        'el lenguaje iconográfico LIDA para el Cinvestav. Para cada actor se describen las interacciones más relevantes '
        'entre el usuario, la interfaz web, la API REST, la base de datos y los servicios externos, en el orden temporal '
        'en que ocurren. Los diagramas complementan los documentos de casos de uso y de base de datos: cada secuencia '
        'detalla el flujo principal y los flujos alternos de un caso de uso específico.', cuerpo))
    hist.append(titulo('1.2 Alcance', h2, 1))
    hist.append(Paragraph(
        'Se modelan tres secuencias comunes a todos los actores (autenticación, renovación de la sesión y consulta de '
        'archivos protegidos) y entre cuatro y cinco secuencias por cada uno de los siete actores: Coordinación Académica, '
        'Servicios Escolares, Aspirante, Alumno, Docente, Director de tesis y Administrador. Los mensajes corresponden a '
        'los endpoints reales de la API (<font face="Arial-Bold">/api/...</font>) y a las llamadas al motor LIDA '
        '(Camunda <font face="Arial-Bold">engine-rest</font>).', cuerpo))
    hist.append(titulo('1.3 Participantes', h2, 1))
    hist.append(Paragraph('Las líneas de vida que aparecen en los diagramas son las siguientes:', cuerpo))
    hist.append(tabla([
        ['Participante', 'Estereotipo', 'Responsabilidad'],
        ['Actor', 'Actor UML', 'Persona que inicia la interacción según su rol.'],
        ['Panel React', '«boundary»', 'Interfaz web (SPA) que captura acciones, conserva la sesión JWT y presenta resultados.'],
        ['API REST Django', '«control»', 'Vistas de Django REST Framework: autenticación, permisos por rol, validación, reglas de negocio y generación de archivos.'],
        ['PostgreSQL', '«entity»', 'Persistencia de usuarios, expedientes, inscripciones, tesis, histórico y auditoría mediante el ORM.'],
        ['Almacenamiento de medios', '«sistema»', 'Archivos cargados (documentos, tesis, fotografías) servidos con URL firmada y caducable.'],
        ['Motor LIDA (Camunda)', '«sistema»', 'Motor BPMN que orquesta los procesos de preregistro, entrevistas y cargas académicas.'],
        ['Servidor de correo', '«sistema»', 'Envío de notificaciones por correo electrónico.'],
        ['Jitsi Meet', '«sistema»', 'Videollamadas para entrevistas virtuales.'],
    ], [3.6 * cm, 2.6 * cm, ANCHO_UTIL - 6.2 * cm]))
    hist.append(Spacer(1, 8))
    hist.append(titulo('1.4 Notación', h2, 1))
    hist.append(Paragraph(
        'Los diagramas siguen la notación UML 2.5 para diagramas de secuencia. Los mensajes se numeran en orden de '
        'ejecución; las respuestas no se numeran y muestran el código HTTP y el contenido principal devuelto.', cuerpo))
    hist.append(tabla([
        ['Elemento', 'Representación', 'Significado'],
        ['Línea de vida', 'Cabecera y línea discontinua vertical', 'Existencia del participante durante la interacción.'],
        ['Barra de activación', 'Rectángulo verde sobre la línea de vida', 'Periodo en que el participante procesa un mensaje.'],
        ['Mensaje síncrono', 'Línea continua con punta rellena', 'Petición que espera respuesta (por ejemplo, una llamada HTTP).'],
        ['Mensaje de respuesta', 'Línea discontinua con punta abierta', 'Resultado devuelto al emisor.'],
        ['Mensaje asíncrono', 'Línea continua con punta abierta', 'Envío que no bloquea el flujo (correo, mensaje BPMN).'],
        ['Automensaje', 'Flecha que regresa a la misma línea de vida', 'Procesamiento interno: validaciones, firmas, generación de PDF.'],
        ['Fragmento alt', 'Marco con guardas separadas por línea discontinua', 'Alternativas mutuamente excluyentes según la condición.'],
        ['Fragmento opt', 'Marco con una guarda', 'Bloque que solo se ejecuta si se cumple la condición.'],
        ['Fragmento loop', 'Marco con guarda de repetición', 'Bloque que se repite mientras se cumple la condición.'],
    ], [3.4 * cm, 5.4 * cm, ANCHO_UTIL - 8.8 * cm]))
    hist.append(Spacer(1, 8))
    ejemplo = [m('actor', 'ui', 'Acción del usuario'),
               m('ui', 'api', 'Petición HTTP síncrona'),
               s('api', 'Procesamiento interno'),
               alt('[condición de error]'),
               r('api', 'ui', 'Respuesta de error'),
               sino('[condición correcta]'),
               m('api', 'bd', 'Consulta o escritura'),
               r('bd', 'api', 'Resultado'),
               asin('api', 'correo', 'Mensaje asíncrono'),
               r('api', 'ui', 'Respuesta correcta'),
               fin(),
               r('ui', 'actor', 'Resultado mostrado')]
    Contador.figura += 1
    hist.append(KeepTogether([
        DiagramaAjustado(diagrama_secuencia('Actor', ejemplo), alto_maximo=420, reserva=26),
        Paragraph(f'Figura {Contador.figura}. Ejemplo de la notación empleada.', pie_fig),
    ]))
    hist.append(titulo('1.5 Consideraciones generales', h2, 1))
    for v in [
        'Toda petición a la API, excepto el inicio de sesión y el preregistro público, incluye el token JWT de acceso; '
        'la API verifica el token y el permiso del rol antes de ejecutar la lógica. Por brevedad, esta verificación se '
        'muestra explícitamente solo en algunos diagramas.',
        'Los errores de validación devuelven 400 con el detalle por campo; los conflictos de estado devuelven 409; la '
        'falta de permisos devuelve 403 y los recursos inexistentes 404. Los mensajes de error no exponen detalles internos.',
        'Las escrituras relevantes generan un evento en el histórico (línea de tiempo por persona) y, en el panel de '
        'administración, un registro en la bitácora de auditoría.',
        'Las llamadas al motor LIDA tienen tiempo de espera corto; si el motor no está disponible, la operación local se '
        'conserva y el error queda registrado para reintentar.',
    ]:
        hist.append(Paragraph(v, vineta, bulletText='•'))
    hist.append(PageBreak())
    return hist


def resumen_actor(rol):
    filas = [['Diagrama', 'Nombre', 'Caso de uso', 'Participantes']]
    for d in rol['diagramas']:
        usados = {'actor', 'ui'}
        for p in d['pasos']:
            if p[0] in ('m', 'r', 'a'):
                usados.update(p[1:3])
            elif p[0] == 's':
                usados.add(p[1])
        nombres = [rol['nombre'] if k == 'actor' else PARTICIPANTES[k][0] for k in PARTICIPANTES if k in usados]
        filas.append([d['id'], d['nombre'], d['cu'].split(' ')[0], ', '.join(nombres)])
    return tabla(filas, [2.2 * cm, 4.4 * cm, 2.3 * cm, ANCHO_UTIL - 8.9 * cm])


def desarrollo():
    hist = [titulo('2. Desarrollo', h1, 0)]
    hist.append(Paragraph(
        'En esta sección se presentan los diagramas de secuencia. Primero se describen las secuencias comunes a todos los '
        'actores y después, en un apartado por actor, las secuencias de sus casos de uso específicos más representativos.', cuerpo))
    hist.append(titulo('2.1 Secuencias comunes a todos los actores', h2, 1))
    hist.append(Paragraph(
        'Todos los casos de uso generales incluyen la autenticación. Estas secuencias aplican a cualquier rol y se omiten '
        'en los diagramas específicos.', cuerpo))
    for d in COMUNES:
        hist += bloque_diagrama('Usuario', d)
    for i, rol in enumerate(ROLES, start=2):
        hist.append(PageBreak())
        hist.append(titulo(f'2.{i} Actor: {rol["nombre"]}', h2, 1))
        hist.append(Paragraph(rol['intro'], cuerpo))
        hist.append(resumen_actor(rol))
        hist.append(Spacer(1, 6))
        for d in rol['diagramas']:
            hist += bloque_diagrama(rol['nombre'], d)
    hist.append(PageBreak())
    return hist


def conclusiones():
    total = len(COMUNES) + sum(len(r['diagramas']) for r in ROLES)
    hist = [titulo('3. Conclusiones', h1, 0)]
    for texto in [
        f'Se documentaron {total} diagramas de secuencia: {len(COMUNES)} comunes y {total - len(COMUNES)} distribuidos entre '
        'los siete actores del sistema. Cada uno se apoya en los endpoints reales de la API y en las reglas de negocio '
        'implementadas, por lo que sirve como referencia para el mantenimiento y las pruebas.',
        'Las secuencias muestran que la API REST concentra la seguridad (JWT, permisos por rol, limitación de peticiones, '
        'validación de archivos y URL firmadas), mientras que el Panel React se limita a la captura y presentación.',
        'La integración con el motor LIDA (Camunda) aparece en el preregistro, la carga de documentos, la resolución de '
        'solicitudes, las entrevistas y las cargas académicas, y se diseñó para no bloquear la operación local cuando el '
        'motor no está disponible.',
        'La trazabilidad queda garantizada por el registro sistemático de eventos en el histórico y en la bitácora de '
        'auditoría, visible en los diagramas como escrituras explícitas en PostgreSQL.',
    ]:
        hist.append(Paragraph(texto, cuerpo))
    return hist


def main():
    temporal = SALIDA.replace('.pdf', '_tmp.pdf')
    doc = Documento(temporal, TITULO)
    indice = TableOfContents()
    indice.levelStyles = toc_estilos
    indice.dotsMinLevel = 0
    historia = portada(TITULO) + [Paragraph('Índice', h1), indice, PageBreak()]
    historia += introduccion() + desarrollo() + conclusiones()
    doc.multiBuild(historia, canvasmaker=canvas_numerado(TITULO))
    os.replace(temporal, SALIDA)
    print('Generado:', SALIDA)


if __name__ == '__main__':
    main()
