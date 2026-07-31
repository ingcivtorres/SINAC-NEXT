from django.http import JsonResponse
from django.conf import settings
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')


def health(request):
    return JsonResponse({"status": "ok", "service": "sinac-backend"})
