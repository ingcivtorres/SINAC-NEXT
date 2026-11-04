import mimetypes
import os
from pathlib import Path

from django.conf import settings
from django.core import signing
from django.http import FileResponse, Http404
from django.utils._os import safe_join
from django.utils.text import get_valid_filename
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_IMAGEN_BYTES = 5 * 1024 * 1024
MAX_CSV_BYTES = 2 * 1024 * 1024
FORMATOS_IMAGEN = {'JPEG': ('.jpg', '.jpeg'), 'PNG': ('.png',), 'WEBP': ('.webp',)}
MEDIA_FIRMA_SALT = 'sinac.media'
MEDIA_FIRMA_SEGUNDOS = 12 * 60 * 60


def _tamano(archivo):
    size = getattr(archivo, 'size', None)
    if size is None:
        posicion = archivo.tell()
        archivo.seek(0, os.SEEK_END)
        size = archivo.tell()
        archivo.seek(posicion)
    return int(size or 0)


def nombre_archivo_seguro(nombre, por_defecto='archivo'):
    base = os.path.basename(str(nombre or '').replace('\\', '/')).strip()
    raiz, extension = os.path.splitext(base)
    limpio = get_valid_filename(raiz[:120]) if raiz else ''
    return f'{limpio or por_defecto}{extension.lower()[:10]}'


def validar_pdf(archivo, max_bytes=MAX_PDF_BYTES):
    """Devuelve un mensaje de error o None si el archivo es un PDF real dentro del límite."""
    if not archivo:
        return 'Selecciona un archivo PDF.'
    if not str(archivo.name or '').lower().endswith('.pdf'):
        return 'Solo se permiten archivos PDF.'
    tamano = _tamano(archivo)
    if tamano <= 0:
        return 'El archivo adjunto está vacío.'
    if tamano > max_bytes:
        return f'El archivo no debe exceder {max_bytes // (1024 * 1024)} MB.'
    posicion = archivo.tell()
    archivo.seek(0)
    cabecera = archivo.read(1024)
    archivo.seek(posicion)
    if b'%PDF-' not in cabecera:
        return 'El archivo no es un PDF válido.'
    return None


def validar_imagen(archivo, max_bytes=MAX_IMAGEN_BYTES):
    """Devuelve un mensaje de error o None si el archivo es una imagen JPG, PNG o WEBP real."""
    if not archivo:
        return None
    if _tamano(archivo) > max_bytes:
        return f'La imagen no debe superar {max_bytes // (1024 * 1024)} MB.'
    extension = Path(str(archivo.name or '')).suffix.lower()
    posicion = archivo.tell()
    try:
        archivo.seek(0)
        with Image.open(archivo, formats=list(FORMATOS_IMAGEN)) as imagen:
            formato = imagen.format
            imagen.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        return 'El archivo no es una imagen válida.'
    finally:
        archivo.seek(posicion)
    if formato not in FORMATOS_IMAGEN or extension not in FORMATOS_IMAGEN[formato]:
        return 'Solo se permiten imágenes JPG, PNG o WEBP.'
    return None


def validar_csv(archivo, max_bytes=MAX_CSV_BYTES):
    if not archivo:
        return 'Selecciona un archivo CSV.'
    if not str(archivo.name or '').lower().endswith('.csv'):
        return 'Solo se permiten archivos CSV.'
    if _tamano(archivo) > max_bytes:
        return f'El archivo no debe exceder {max_bytes // (1024 * 1024)} MB.'
    return None


def celda_segura(valor):
    """Neutraliza fórmulas en celdas exportadas a hojas de cálculo (CSV/XLSX injection)."""
    if isinstance(valor, str) and valor[:1] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + valor
    return valor


def url_media(archivo):
    """URL temporal y firmada para un archivo almacenado en MEDIA_ROOT."""
    if not archivo:
        return None
    nombre = str(getattr(archivo, 'name', archivo) or '').lstrip('/')
    if not nombre:
        return None
    firmado = signing.TimestampSigner(salt=MEDIA_FIRMA_SALT).sign(nombre)
    return f"{settings.MEDIA_URL}{nombre}?firma={firmado[len(nombre) + 1:]}"


class ImagenFirmadaField(serializers.ImageField):
    def to_internal_value(self, data):
        error = validar_imagen(data)
        if error:
            raise serializers.ValidationError(error)
        return super().to_internal_value(data)

    def to_representation(self, value):
        return url_media(value)


def servir_media(request, ruta):
    firma = request.GET.get('firma', '')
    try:
        signing.TimestampSigner(salt=MEDIA_FIRMA_SALT).unsign(f'{ruta}:{firma}', max_age=MEDIA_FIRMA_SEGUNDOS)
    except signing.BadSignature:
        raise Http404
    try:
        absoluta = safe_join(settings.MEDIA_ROOT, ruta)
    except Exception:
        raise Http404
    if not os.path.isfile(absoluta):
        raise Http404
    tipo, _ = mimetypes.guess_type(absoluta)
    respuesta = FileResponse(open(absoluta, 'rb'), content_type=tipo or 'application/octet-stream')
    respuesta['X-Content-Type-Options'] = 'nosniff'
    if tipo != 'application/pdf':
        respuesta['Content-Security-Policy'] = "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; sandbox"
    respuesta['Cache-Control'] = 'private, max-age=3600'
    respuesta['Referrer-Policy'] = 'no-referrer'
    return respuesta
