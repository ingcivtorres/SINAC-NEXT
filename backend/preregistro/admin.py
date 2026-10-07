from django.contrib import admin
from .models import Aspirante, ExpedienteDigital, AuditoriaSistema, ConfiguracionSistema, Materia, PeriodoInscripcion, ProyectoTesis, ConfiguracionPrograma, PlanEstudioMateria, SolicitudDireccionTesis


@admin.register(Aspirante)
class AspiranteAdmin(admin.ModelAdmin):
    list_display  = ('usuario', 'nombre', 'curp', 'correo', 'unidad', 'proceso_estado', 'created_at')
    list_filter   = ('unidad', 'proceso_estado', 'modalidad')
    search_fields = ('usuario', 'nombre', 'curp', 'correo')
    readonly_fields = ('business_key', 'created_at', 'updated_at')


@admin.register(ExpedienteDigital)
class ExpedienteDigitalAdmin(admin.ModelAdmin):
    list_display = ('folio', 'aspirante', 'estado', 'fecha_creacion')
    list_filter = ('estado',)
    search_fields = ('folio', 'aspirante__usuario', 'aspirante__nombre')
    readonly_fields = ('folio', 'fecha_creacion')


@admin.register(AuditoriaSistema)
class AuditoriaSistemaAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'actor', 'accion', 'modelo', 'objeto_id', 'ip')
    list_filter = ('accion', 'modelo', 'created_at')
    search_fields = ('actor__usuario', 'accion', 'modelo', 'objeto_id')
    readonly_fields = ('created_at',)


@admin.register(ConfiguracionSistema)
class ConfiguracionSistemaAdmin(admin.ModelAdmin):
    list_display = ('clave', 'valor', 'actualizado_por', 'updated_at')
    search_fields = ('clave', 'valor')
    readonly_fields = ('updated_at',)


@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ('clave', 'nombre', 'categoria', 'creditos', 'profesor', 'horario')
    list_filter = ('categoria',)
    search_fields = ('clave', 'nombre', 'profesor')


@admin.register(PeriodoInscripcion)
class PeriodoInscripcionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apertura', 'cierre', 'activo')
    list_filter = ('activo',)


@admin.register(ProyectoTesis)
class ProyectoTesisAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'alumno', 'director', 'estado', 'updated_at')
    list_filter = ('estado', 'director')
    search_fields = ('titulo', 'alumno__nombre', 'alumno__matricula', 'director__nombre')
    readonly_fields = ('created_at', 'updated_at')


class PlanEstudioMateriaInline(admin.TabularInline):
    model = PlanEstudioMateria
    extra = 1


@admin.register(ConfiguracionPrograma)
class ConfiguracionProgramaAdmin(admin.ModelAdmin):
    list_display = ('programa', 'grado', 'periodicidad', 'duracion_anios', 'periodos_requeridos', 'creditos_requeridos', 'activo')
    list_filter = ('grado', 'periodicidad', 'activo')
    search_fields = ('programa',)
    inlines = [PlanEstudioMateriaInline]


@admin.register(SolicitudDireccionTesis)
class SolicitudDireccionTesisAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'director_sugerido', 'director_asignado', 'estado', 'updated_at')
    list_filter = ('estado',)
    search_fields = ('alumno__nombre', 'alumno__matricula', 'director_asignado__nombre')
    readonly_fields = ('created_at', 'updated_at')
