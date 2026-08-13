from django.contrib import admin
from .models import Aspirante


@admin.register(Aspirante)
class AspiranteAdmin(admin.ModelAdmin):
    list_display  = ('usuario', 'nombre', 'curp', 'correo', 'unidad', 'proceso_estado', 'created_at')
    list_filter   = ('unidad', 'proceso_estado', 'modalidad')
    search_fields = ('usuario', 'nombre', 'curp', 'correo')
    readonly_fields = ('business_key', 'created_at', 'updated_at')
