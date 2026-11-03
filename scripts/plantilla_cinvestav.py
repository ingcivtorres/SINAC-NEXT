"""Formato institucional compartido por los documentos PDF de SINAC NEXT."""
import math
import os

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, Image, NextPageTemplate, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO = os.path.join(RAIZ, 'docs', 'assets', 'logo_cinvestav.png')

FUENTES = r'C:\Windows\Fonts'
pdfmetrics.registerFont(TTFont('Arial', os.path.join(FUENTES, 'arial.ttf')))
pdfmetrics.registerFont(TTFont('Arial-Bold', os.path.join(FUENTES, 'arialbd.ttf')))
pdfmetrics.registerFont(TTFont('Arial-Italic', os.path.join(FUENTES, 'ariali.ttf')))
pdfmetrics.registerFont(TTFont('Arial-BoldItalic', os.path.join(FUENTES, 'arialbi.ttf')))
pdfmetrics.registerFontFamily('Arial', normal='Arial', bold='Arial-Bold', italic='Arial-Italic', boldItalic='Arial-BoldItalic')

VERDE = colors.HexColor('#00957A')
VERDE_OSCURO = colors.HexColor('#00634F')
VERDE_CLARO = colors.HexColor('#E6F4F1')
GRIS = colors.HexColor('#4A5560')
GRIS_CLARO = colors.HexColor('#F3F5F7')
BORDE = colors.HexColor('#B9C4CC')

RESIDENTE = 'Equipo de Desarrollo'
PROYECTO = ('SINAC NEXT: DESARROLLO DE UN SISTEMA DE INFORMACIÓN ACADÉMICA BASADO EN EL '
            'LENGUAJE ICONOGRÁFICO (LIDA) PARA EL CINVESTAV')
CARRERA = 'Ingeniería en Sistemas Computacionales'
INSTITUCION = 'Centro de Investigación y de Estudios Avanzados'
FECHA = 'Noviembre de 2026'

MARGEN_X = 2.2 * cm
MARGEN_SUP = 3.1 * cm
MARGEN_INF = 2.2 * cm
ANCHO_UTIL = letter[0] - 2 * MARGEN_X

base = ParagraphStyle('base', fontName='Arial', fontSize=10.5, leading=14.5, alignment=TA_JUSTIFY, textColor=colors.HexColor('#1F2A33'))
cuerpo = ParagraphStyle('cuerpo', parent=base, spaceAfter=7)
vineta = ParagraphStyle('vineta', parent=cuerpo, leftIndent=14, bulletIndent=3, spaceAfter=3)
h1 = ParagraphStyle('h1', parent=base, fontName='Arial-Bold', fontSize=17, leading=21, textColor=VERDE_OSCURO, spaceBefore=4, spaceAfter=12, alignment=0)
h2 = ParagraphStyle('h2', parent=base, fontName='Arial-Bold', fontSize=13.5, leading=17, textColor=VERDE_OSCURO, spaceBefore=12, spaceAfter=8, alignment=0, keepWithNext=1)
h3 = ParagraphStyle('h3', parent=base, fontName='Arial-Bold', fontSize=11.5, leading=15, textColor=GRIS, spaceBefore=10, spaceAfter=6, alignment=0, keepWithNext=1)
celda = ParagraphStyle('celda', parent=base, fontSize=9, leading=12, alignment=0)
celda_neg = ParagraphStyle('celda_neg', parent=celda, fontName='Arial-Bold', textColor=VERDE_OSCURO)
celda_cab = ParagraphStyle('celda_cab', parent=celda, fontName='Arial-Bold', textColor=colors.white)
pie_fig = ParagraphStyle('pie_fig', parent=base, fontName='Arial-Italic', fontSize=9, alignment=TA_CENTER, textColor=GRIS, spaceBefore=4, spaceAfter=12)

toc_estilos = [
    ParagraphStyle('toc0', fontName='Arial-Bold', fontSize=11, leading=16, leftIndent=0, textColor=VERDE_OSCURO, spaceBefore=5),
    ParagraphStyle('toc1', fontName='Arial', fontSize=10, leading=14, leftIndent=16),
    ParagraphStyle('toc2', fontName='Arial', fontSize=9.5, leading=13, leftIndent=32),
    ParagraphStyle('toc3', fontName='Arial', fontSize=8.5, leading=11.5, leftIndent=48, textColor=GRIS),
]


class Documento(BaseDocTemplate):
    """Plantilla con encabezado institucional, páginas verticales y horizontales e índice."""

    def __init__(self, archivo, titulo, **kw):
        super().__init__(archivo, pagesize=letter, leftMargin=MARGEN_X, rightMargin=MARGEN_X,
                         topMargin=MARGEN_SUP, bottomMargin=MARGEN_INF, title=titulo, author=RESIDENTE,
                         subject=PROYECTO, **kw)
        vertical = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='vertical')
        ancho_h, alto_h = landscape(letter)
        horizontal = Frame(MARGEN_X, MARGEN_INF, ancho_h - 2 * MARGEN_X, alto_h - MARGEN_SUP - MARGEN_INF, id='horizontal')
        self.addPageTemplates([
            PageTemplate(id='portada', frames=[vertical], onPage=self.encabezado, pagesize=letter),
            PageTemplate(id='normal', frames=[vertical], onPage=self.encabezado, pagesize=letter),
            PageTemplate(id='horizontal', frames=[horizontal], onPage=self.encabezado, pagesize=landscape(letter)),
        ])

    def encabezado(self, c, doc):
        c.saveState()
        ancho, alto = c._pagesize
        logo_h = 1.25 * cm
        logo_w = logo_h * 927 / 282
        y = alto - 1.0 * cm - logo_h
        c.drawImage(LOGO, MARGEN_X, y, logo_w, logo_h, mask='auto')
        c.setFont('Arial-Bold', 12)
        c.setFillColor(VERDE_OSCURO)
        c.drawString(MARGEN_X + logo_w + 0.4 * cm, y + logo_h / 2 - 4, INSTITUCION)
        c.setStrokeColor(VERDE)
        c.setLineWidth(1.4)
        c.line(MARGEN_X, y - 0.25 * cm, ancho - MARGEN_X, y - 0.25 * cm)
        c.restoreState()

    def afterFlowable(self, flowable):
        nivel = getattr(flowable, 'nivel_indice', None)
        if nivel is not None:
            texto = flowable.getPlainText()
            clave = f'sec{self.seq.nextf("sec")}'
            self.canv.bookmarkPage(clave)
            self.canv.addOutlineEntry(texto, clave, level=nivel, closed=nivel > 0)
            self.notify('TOCEntry', (nivel, texto, self.page, clave))


def canvas_numerado(titulo_documento):
    class CanvasNumerado(rl_canvas.Canvas):
        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)
            self._paginas = []

        def showPage(self):
            self._paginas.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._paginas)
            for estado in self._paginas:
                self.__dict__.update(estado)
                if self._pageNumber > 1:
                    ancho = self._pagesize[0]
                    self.setFont('Arial', 9)
                    self.setFillColor(GRIS)
                    self.setStrokeColor(BORDE)
                    self.setLineWidth(0.6)
                    self.line(MARGEN_X, 1.5 * cm, ancho - MARGEN_X, 1.5 * cm)
                    self.drawString(MARGEN_X, 1.0 * cm, 'SINAC NEXT · ' + titulo_documento)
                    self.drawRightString(ancho - MARGEN_X, 1.0 * cm, f'Página {self._pageNumber} de {total}')
                super().showPage()
            super().save()

    return CanvasNumerado


class DiagramaAjustado(Flowable):
    """Dibuja un Drawing escalado para que quepa en el marco disponible."""

    def __init__(self, dibujo, alto_maximo=None, reserva=0):
        super().__init__()
        self.dibujo = dibujo
        self.alto_maximo = alto_maximo
        self.reserva = reserva
        self.escala = 1

    def wrap(self, ancho_disp, alto_disp):
        d = self.dibujo
        alto_disp -= self.reserva
        por_ancho = min(1, ancho_disp / d.width)
        escala = min(por_ancho, alto_disp / d.height)
        if escala < 0.8 * por_ancho and self.alto_maximo:
            escala = min(por_ancho, self.alto_maximo / d.height)
        self.escala = escala
        self.width, self.height = d.width * escala, d.height * escala
        return self.width, self.height

    def draw(self):
        self.canv.saveState()
        self.canv.scale(self.escala, self.escala)
        renderPDF.draw(self.dibujo, self.canv, 0, 0)
        self.canv.restoreState()


def titulo(texto, estilo, nivel):
    p = Paragraph(texto, estilo)
    p.nivel_indice = nivel
    return p


def tabla(datos, anchos, cabecera=True, estilo_celda=None):
    estilo_celda = estilo_celda or celda
    filas = []
    for i, fila in enumerate(datos):
        estilo = celda_cab if cabecera and i == 0 else estilo_celda
        filas.append([c if not isinstance(c, str) else Paragraph(c, estilo) for c in fila])
    t = Table(filas, colWidths=anchos, repeatRows=1 if cabecera else 0)
    comandos = [
        ('GRID', (0, 0), (-1, -1), 0.5, BORDE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]
    if cabecera:
        comandos += [('BACKGROUND', (0, 0), (-1, 0), VERDE)]
        comandos += [('BACKGROUND', (0, i), (-1, i), GRIS_CLARO) for i in range(2, len(filas), 2)]
    t.setStyle(TableStyle(comandos))
    return t


def portada(titulo_documento):
    titulo_p = ParagraphStyle('tp', parent=base, fontName='Arial-Bold', fontSize=24, leading=30, alignment=TA_CENTER, textColor=VERDE_OSCURO)
    proyecto_p = ParagraphStyle('pp', parent=base, fontName='Arial-Bold', fontSize=12.5, leading=17, alignment=TA_CENTER, textColor=GRIS)
    etiqueta = ParagraphStyle('et', parent=base, fontName='Arial-Bold', fontSize=11, textColor=VERDE_OSCURO, alignment=0)
    valor = ParagraphStyle('va', parent=base, fontSize=11, leading=15, alignment=0)
    logo_w = 9 * cm
    datos = Table([
        [Paragraph('Residente:', etiqueta), Paragraph(RESIDENTE, valor)],
        [Paragraph('Carrera:', etiqueta), Paragraph(CARRERA, valor)],
        [Paragraph('Institución:', etiqueta), Paragraph(INSTITUCION + ' (Cinvestav)', valor)],
        [Paragraph('Fecha:', etiqueta), Paragraph(FECHA, valor)],
    ], colWidths=[3.4 * cm, ANCHO_UTIL - 5.4 * cm])
    datos.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, BORDE),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    contenedor = Table([[datos]], colWidths=[ANCHO_UTIL - 2 * cm])
    contenedor.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, VERDE),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FAFCFB')),
        ('LEFTPADDING', (0, 0), (-1, -1), 14),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    return [
        Spacer(1, 1.2 * cm),
        Image(LOGO, logo_w, logo_w * 282 / 927),
        Spacer(1, 1.4 * cm),
        Paragraph(titulo_documento, titulo_p),
        Spacer(1, 0.5 * cm),
        Table([['']], colWidths=[6 * cm], style=[('LINEABOVE', (0, 0), (-1, -1), 2, VERDE)]),
        Spacer(1, 0.6 * cm),
        Paragraph('Proyecto', ParagraphStyle('pl', parent=etiqueta, alignment=TA_CENTER)),
        Spacer(1, 0.15 * cm),
        Paragraph(PROYECTO, proyecto_p),
        Spacer(1, 1.6 * cm),
        contenedor,
        NextPageTemplate('normal'),
        PageBreak(),
    ]


def envolver(texto, fuente, tam, ancho):
    lineas, actual = [], ''
    for palabra in texto.split():
        prueba = f'{actual} {palabra}'.strip()
        if stringWidth(prueba, fuente, tam) <= ancho:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def texto_centrado(d, x, y, lineas, fuente='Arial', tam=7.5, color=colors.black):
    alto = tam + 1.5
    inicio = y + (len(lineas) - 1) * alto / 2 - tam * 0.35
    for i, linea in enumerate(lineas):
        d.add(String(x, inicio - i * alto, linea, fontName=fuente, fontSize=tam, fillColor=color, textAnchor='middle'))


def borde_elipse(cx, cy, rx, ry, px, py):
    ang = math.atan2(py - cy, px - cx)
    return cx + rx * math.cos(ang), cy + ry * math.sin(ang)
