from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static


def health(request):
    return JsonResponse({"status": "ok", "service": "sinac-backend"})

urlpatterns = [
    path('admin/',    admin.site.urls),
    path('health/',   health),
    path('api/',      include('preregistro.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
