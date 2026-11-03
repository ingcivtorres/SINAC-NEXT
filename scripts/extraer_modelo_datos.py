"""Exporta a JSON la estructura de los modelos de Django.

Uso (desde la raíz del repositorio):
    Get-Content scripts/extraer_modelo_datos.py | docker compose run --rm --no-deps -T backend python manage.py shell > docs/assets/modelo_datos.json
"""
import inspect
import json

from django.apps import apps
from django.db import connection, models

ON_DELETE = {
    models.CASCADE: 'CASCADE', models.PROTECT: 'PROTECT', models.SET_NULL: 'SET_NULL',
    models.SET_DEFAULT: 'SET_DEFAULT', models.DO_NOTHING: 'DO_NOTHING', models.RESTRICT: 'RESTRICT',
}


def valor_defecto(campo):
    if not campo.has_default():
        return None
    valor = campo.default
    if callable(valor):
        return f'{valor.__name__}()'
    return valor


def campo_a_dict(campo):
    datos = {
        'nombre': campo.name,
        'columna': campo.column,
        'tipo': campo.get_internal_type(),
        'tipo_bd': campo.db_type(connection),
        'pk': campo.primary_key,
        'nulo': campo.null,
        'blank': campo.blank,
        'unico': campo.unique,
        'indice': campo.db_index,
        'max_length': campo.max_length,
        'default': valor_defecto(campo),
        'choices': [str(c[0]) for c in campo.choices] if campo.choices else [],
        'auto_now': getattr(campo, 'auto_now', False),
        'auto_now_add': getattr(campo, 'auto_now_add', False),
        'max_digits': getattr(campo, 'max_digits', None),
        'decimal_places': getattr(campo, 'decimal_places', None),
        'ayuda': str(campo.help_text or ''),
    }
    if campo.is_relation and campo.related_model:
        datos['relacion'] = {
            'tipo': 'OneToOne' if campo.one_to_one else 'ForeignKey',
            'modelo': campo.related_model.__name__,
            'on_delete': ON_DELETE.get(campo.remote_field.on_delete, campo.remote_field.on_delete.__name__),
            'related_name': campo.remote_field.related_name or '',
            'limit_choices_to': {k: str(v) for k, v in (campo.remote_field.limit_choices_to or {}).items()},
        }
    return datos


def metodos(modelo):
    salida = []
    for nombre, valor in modelo.__dict__.items():
        if nombre.startswith('_') and nombre not in ('__str__',):
            continue
        if isinstance(valor, property):
            salida.append({'nombre': nombre, 'tipo': 'property'})
        elif type(valor).__name__ == 'cached_property':
            salida.append({'nombre': nombre, 'tipo': 'cached_property'})
        elif inspect.isfunction(valor):
            firma = str(inspect.signature(valor)).replace('self, ', '').replace('(self)', '()')
            salida.append({'nombre': nombre, 'tipo': 'metodo', 'firma': firma})
    return salida


resultado = []
for modelo in apps.get_app_config('preregistro').get_models():
    meta = modelo._meta
    doc = (modelo.__doc__ or '').strip()
    if doc.startswith(f'{modelo.__name__}('):
        doc = ''
    resultado.append({
        'modelo': modelo.__name__,
        'tabla': meta.db_table,
        'verbose_name': str(meta.verbose_name),
        'descripcion': doc,
        'bases': [b.__name__ for b in modelo.__bases__],
        'campos': [campo_a_dict(c) for c in meta.local_fields],
        'muchos_a_muchos': [
            {'nombre': c.name, 'modelo': c.related_model.__name__, 'tabla': c.m2m_db_table()}
            for c in meta.local_many_to_many
        ],
        'unique_together': [list(g) for g in meta.unique_together],
        'restricciones': [
            {'nombre': r.name, 'campos': list(getattr(r, 'fields', []) or []),
             'condicion': str(r.condition) if getattr(r, 'condition', None) else ''}
            for r in meta.constraints
        ],
        'ordering': list(meta.ordering or []),
        'metodos': metodos(modelo),
    })

print('@@JSON@@' + json.dumps(resultado, ensure_ascii=False, default=str))
