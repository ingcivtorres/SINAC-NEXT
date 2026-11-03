from django.http import JsonResponse
from django.shortcuts import render

ERRORES = {
    400: ('Solicitud no válida', 'La información enviada no tiene el formato esperado. Revisa los datos e inténtalo de nuevo.'),
    403: ('Acceso restringido', 'No tienes permisos para consultar este recurso. Si crees que es un error, solicita acceso a tu coordinación.'),
    404: ('Página no encontrada', 'El recurso que buscas no existe, cambió de dirección o ya no está disponible.'),
    500: ('Error interno del sistema', 'Ocurrió un problema inesperado. Intenta nuevamente en unos momentos.'),
}


def _quiere_json(request):
    return request.path.startswith('/api/') or 'application/json' in request.headers.get('Accept', '')


def _respuesta(request, codigo):
    titulo, mensaje = ERRORES[codigo]
    if _quiere_json(request):
        return JsonResponse({'detail': mensaje, 'error': titulo, 'codigo': codigo}, status=codigo)
    contexto = {'codigo': codigo, 'titulo': titulo, 'mensaje': mensaje, 'ruta': request.path}
    return render(request, 'errors/error.html', contexto, status=codigo)


def error_400(request, exception=None):
    return _respuesta(request, 400)


def error_403(request, exception=None):
    return _respuesta(request, 403)


def error_404(request, exception=None):
    return _respuesta(request, 404)


def error_500(request):
    return _respuesta(request, 500)
