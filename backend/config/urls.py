from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

from preregistro.seguridad import servir_media


def health(request):
    return JsonResponse({"status": "ok", "service": "sinac-backend"})

urlpatterns = [
    path('admin/',    admin.site.urls),
    path('health/',   health),
    path('api/',      include('preregistro.urls')),
    path('media/<path:ruta>', servir_media, name='media-firmada'),
]

handler400 = 'config.errores.error_400'
handler403 = 'config.errores.error_403'
handler404 = 'config.errores.error_404'
handler500 = 'config.errores.error_500'
