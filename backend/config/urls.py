from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health(request):
    return JsonResponse({"status": "ok", "service": "sinac-backend"})

urlpatterns = [
    path('admin/',    admin.site.urls),
    path('health/',   health),
    path('api/',      include('preregistro.urls')),
]
