"""Registro automático del histórico de alumnos, docentes y directores de tesis."""
from contextvars import ContextVar
from datetime import datetime

from django.db.models import QuerySet
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import (
    Aspirante, CargaAcademicaMateria, DefensaTesis, DocumentoAspirante, EgresoAlumno, HistorialPersona,
    Inscripcion, JuradoProyecto, ProyectoTesis, RevisionAntiplagio, SolicitudAcademica,
    SolicitudDireccionTesis, SolicitudInscripcionExtemporanea,
)

ROLES_HISTORIAL = {'alumno', 'docente', 'director'}
CAMPOS = {
    'rol': 'Rol',
    'proceso_estado': 'Estado',
    'is_active': 'Cuenta activa',
    'programa': 'Programa',
    'departamento': 'Departamento',
    'unidad': 'Unidad',
    'modalidad': 'Modalidad',
    'matricula': 'Matrícula',
    'numero_periodo_actual': 'Periodo actual',
    'director_tesis_id': 'Director de tesis',
    'nombre': 'Nombre',
    'correo': 'Correo',
}

_actor = ContextVar('historial_actor', default=None)


class HistorialJWTAuthentication(JWTAuthentication):
    """Igual que JWTAuthentication, pero recuerda quién hace la petición."""

    def authenticate(self, request):
        resultado = super().authenticate(request)
        if resultado:
            _actor.set(resultado[0])
        return resultado


def limpiar_actor_middleware(get_response):
    def middleware(request):
        _actor.set(None)
        try:
            return get_response(request)
        finally:
            _actor.set(None)
    return middleware


def _texto(valor):
    return '' if valor is None else str(valor)[:255]


def _director(valor):
    if valor in (None, ''):
        return ''
    persona = Aspirante.objects.filter(pk=valor).only('nombre').first()
    return persona.nombre if persona else str(valor)


def _registrar(persona, evento, campo='', anterior='', nuevo='', categoria='cuenta', detalle=''):
    actor = _actor.get()
    HistorialPersona.objects.create(
        persona=persona, rol=persona.rol, categoria=categoria, evento=evento, campo=campo[:60],
        valor_anterior=_texto(anterior), valor_nuevo=_texto(nuevo), detalle=_texto(detalle),
        realizado_por=actor if actor and actor.pk else None,
        realizado_por_nombre=(actor.nombre if actor and actor.pk else 'Sistema'),
    )


@receiver(pre_save, sender=Aspirante)
def _capturar_estado_previo(sender, instance, **kwargs):
    instance._historial_previo = None
    if instance.pk:
        instance._historial_previo = Aspirante.objects.filter(pk=instance.pk).values(*CAMPOS).first()


@receiver(post_save, sender=Aspirante)
def _registrar_cambios(sender, instance, created, **kwargs):
    if kwargs.get('raw'):
        return
    previo = getattr(instance, '_historial_previo', None)
    if created:
        if instance.rol in ROLES_HISTORIAL:
            _registrar(instance, 'alta', 'rol', '', instance.rol)
        return
    if not previo:
        return
    rol_relevante = instance.rol in ROLES_HISTORIAL or previo['rol'] in ROLES_HISTORIAL
    if not rol_relevante:
        return
    for campo, etiqueta in CAMPOS.items():
        anterior, nuevo = previo[campo], getattr(instance, campo)
        if anterior == nuevo:
            continue
        if campo == 'director_tesis_id':
            _avisar_directores(instance, anterior, nuevo)
            anterior, nuevo = _director(anterior), _director(nuevo)
        _registrar(instance, 'cambio', etiqueta, _texto(anterior), _texto(nuevo))


def _avisar_directores(alumno, anterior_id, nuevo_id):
    for director_id, evento in ((anterior_id, 'baja'), (nuevo_id, 'alta')):
        director = Aspirante.objects.filter(pk=director_id).first() if director_id else None
        if director and director.rol in ROLES_HISTORIAL:
            _registrar(director, evento, 'Tesista', categoria='tesis', detalle=alumno.nombre,
                       nuevo=alumno.nombre if evento == 'alta' else '',
                       anterior=alumno.nombre if evento == 'baja' else '')


def _formatear(modelo, campo, valor):
    """Convierte el valor guardado en texto legible (choices, relaciones, fechas, booleanos)."""
    if valor in (None, ''):
        return ''
    campo_modelo = modelo._meta.get_field(campo[:-3] if campo.endswith('_id') else campo)
    if campo_modelo.is_relation:
        objeto = campo_modelo.related_model.objects.filter(pk=valor).first()
        return getattr(objeto, 'nombre', None) or str(objeto or valor)
    if campo_modelo.choices:
        return str(dict(campo_modelo.flatchoices).get(valor, valor))
    if isinstance(valor, bool):
        return 'Sí' if valor else 'No'
    if isinstance(valor, datetime):
        return timezone.localtime(valor).strftime('%Y-%m-%d %H:%M') if timezone.is_aware(valor) else valor.strftime('%Y-%m-%d %H:%M')
    return str(valor)


class Seguimiento:
    """Lleva al histórico las altas, cambios y bajas de un modelo relacionado con personas.

    ``personas`` devuelve las personas afectadas; ``campos`` relaciona campo → etiqueta;
    ``alta`` es (etiqueta, campo cuyo valor se muestra al crear).
    """

    def __init__(self, modelo, categoria, personas, detalle, campos, alta, baja=None):
        self.modelo, self.categoria, self.personas, self.detalle = modelo, categoria, personas, detalle
        self.campos, self.alta, self.baja = campos, alta, baja
        uid = f'historial-{modelo.__name__}'
        pre_save.connect(self._previo, sender=modelo, dispatch_uid=f'{uid}-pre', weak=False)
        post_save.connect(self._guardado, sender=modelo, dispatch_uid=f'{uid}-post', weak=False)
        if baja:
            post_delete.connect(self._borrado, sender=modelo, dispatch_uid=f'{uid}-del', weak=False)

    def _relevantes(self, instancia):
        return [p for p in self.personas(instancia) if p is not None and p.rol in ROLES_HISTORIAL]

    def _previo(self, sender, instance, **kwargs):
        instance._historial_previo = None
        if instance.pk and not kwargs.get('raw'):
            instance._historial_previo = sender.objects.filter(pk=instance.pk).values(*self.campos).first()

    def _guardado(self, sender, instance, created, **kwargs):
        if kwargs.get('raw'):
            return
        personas = self._relevantes(instance)
        if not personas:
            return
        detalle = self.detalle(instance)
        if created:
            etiqueta, campo = self.alta
            nuevo = _formatear(sender, campo, getattr(instance, campo)) if campo else ''
            for persona in personas:
                _registrar(persona, 'alta', etiqueta, '', nuevo, self.categoria, detalle)
            return
        previo = getattr(instance, '_historial_previo', None)
        if not previo:
            return
        for campo, etiqueta in self.campos.items():
            anterior, nuevo = previo[campo], getattr(instance, campo)
            if anterior == nuevo:
                continue
            anterior, nuevo = _formatear(sender, campo, anterior), _formatear(sender, campo, nuevo)
            if anterior == nuevo:
                continue
            for persona in personas:
                _registrar(persona, 'cambio', etiqueta, anterior, nuevo, self.categoria, detalle)

    def _borrado(self, sender, instance, **kwargs):
        origen = kwargs.get('origin')
        directo = origen is None or isinstance(origen, sender) or (isinstance(origen, QuerySet) and origen.model is sender)
        if not directo:
            return
        detalle = self.detalle(instance)
        for persona in self._relevantes(instance):
            _registrar(persona, 'baja', self.baja, detalle, '', self.categoria, detalle)


def _materia(m):
    return f'{m.clave} · {m.nombre}'


def _con_periodo(texto, periodo):
    return f'{texto} ({periodo.nombre})' if periodo else texto


Seguimiento(
    Inscripcion, 'academico',
    personas=lambda i: [i.aspirante],
    detalle=lambda i: _con_periodo(_materia(i.materia), i.periodo_inscripcion),
    campos={'estado': 'Estado de la materia', 'calificacion': 'Calificación', 'validacion_servicios': 'Validación de Servicios Escolares'},
    alta=('Inscripción a materia', 'estado'), baja='Baja de materia',
)
Seguimiento(
    SolicitudInscripcionExtemporanea, 'academico',
    personas=lambda s: [s.alumno],
    detalle=lambda s: f'Inscripción extemporánea · {s.periodo_inscripcion.nombre}',
    campos={'estado': 'Solicitud extemporánea'},
    alta=('Solicitud extemporánea', 'estado'),
)
Seguimiento(
    SolicitudAcademica, 'academico',
    personas=lambda s: [s.aspirante],
    detalle=lambda s: s.get_tipo_display(),
    campos={'estado': 'Solicitud académica'},
    alta=('Solicitud académica', 'estado'),
)
Seguimiento(
    CargaAcademicaMateria, 'academico',
    personas=lambda c: [c.docente],
    detalle=lambda c: _con_periodo(_materia(c.materia), c.carga.periodo_inscripcion),
    campos={'horario': 'Horario', 'salon': 'Salón', 'modalidad': 'Modalidad'},
    alta=('Materia asignada', 'horario'), baja='Materia retirada',
)
Seguimiento(
    SolicitudDireccionTesis, 'tesis',
    personas=lambda s: [s.alumno],
    detalle=lambda s: s.linea_investigacion or 'Solicitud de director de tesis',
    campos={'estado': 'Solicitud de director', 'director_asignado_id': 'Director propuesto'},
    alta=('Solicitud de director', 'estado'),
)
Seguimiento(
    ProyectoTesis, 'tesis',
    personas=lambda p: [p.alumno],
    detalle=lambda p: p.titulo,
    campos={'estado': 'Estado del proyecto', 'titulo': 'Título', 'director_id': 'Director del proyecto', 'avance_porcentaje': 'Avance (%)'},
    alta=('Proyecto de tesis registrado', 'estado'),
)
Seguimiento(
    JuradoProyecto, 'tesis',
    personas=lambda j: [j.proyecto.alumno, j.jurado],
    detalle=lambda j: f'{j.jurado.nombre} · {j.get_rol_display()} · {j.proyecto.titulo}',
    campos={'estado': 'Estado del jurado', 'rol': 'Rol en el jurado'},
    alta=('Jurado asignado', 'rol'), baja='Jurado retirado',
)
Seguimiento(
    DefensaTesis, 'tesis',
    personas=lambda d: [d.proyecto.alumno],
    detalle=lambda d: d.proyecto.titulo,
    campos={'estado': 'Estado de la defensa', 'fecha': 'Fecha de defensa', 'calificacion_final': 'Calificación de defensa'},
    alta=('Defensa programada', 'fecha'),
)
Seguimiento(
    RevisionAntiplagio, 'tesis',
    personas=lambda r: [r.proyecto.alumno],
    detalle=lambda r: f'{r.get_proveedor_display()} · {r.proyecto.titulo}',
    campos={'estado': 'Revisión antiplagio', 'porcentaje_similitud': 'Similitud (%)'},
    alta=('Revisión antiplagio enviada', 'porcentaje_similitud'),
)
Seguimiento(
    DocumentoAspirante, 'documentos',
    personas=lambda d: [d.aspirante],
    detalle=lambda d: d.get_tipo_display(),
    campos={'nombre_original': 'Archivo', 'revisado': 'Revisado'},
    alta=('Documento cargado', 'nombre_original'), baja='Documento eliminado',
)
Seguimiento(
    EgresoAlumno, 'egreso',
    personas=lambda e: [e.alumno],
    detalle=lambda e: e.generacion or 'Egreso',
    campos={'fecha_egreso': 'Fecha de egreso', 'promedio_final': 'Promedio final', 'titulo_tesis': 'Título de tesis'},
    alta=('Egreso registrado', 'fecha_egreso'), baja='Egreso anulado',
)
