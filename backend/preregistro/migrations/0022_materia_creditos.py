from random import Random

from django.db import migrations, models


def asignar_creditos_iniciales(apps, schema_editor):
    Materia = apps.get_model('preregistro', 'Materia')
    generador = Random(20260910)
    opciones = (4, 5, 7)
    for materia in Materia.objects.order_by('id').iterator():
        materia.creditos = generador.choice(opciones)
        materia.save(update_fields=['creditos'])


class Migration(migrations.Migration):
    dependencies = [('preregistro', '0021_inscripcion_parciales')]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        'ALTER TABLE "preregistro_materia" '
                        'ADD COLUMN IF NOT EXISTS "creditos" smallint DEFAULT 4 NOT NULL;'
                    ),
                    reverse_sql=(
                        'ALTER TABLE "preregistro_materia" '
                        'DROP COLUMN IF EXISTS "creditos";'
                    ),
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='materia',
                    name='creditos',
                    field=models.PositiveSmallIntegerField(
                        choices=[(4, '4 cr\u00e9ditos'), (5, '5 cr\u00e9ditos'), (7, '7 cr\u00e9ditos')],
                        default=4,
                    ),
                ),
            ],
        ),
        migrations.RunPython(asignar_creditos_iniciales, migrations.RunPython.noop),
    ]
