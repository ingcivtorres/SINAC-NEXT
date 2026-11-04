from django.db import migrations, models
from django.db.models.functions import Replace


def corregir_cuentas(apps, schema_editor):
    Aspirante = apps.get_model('preregistro', 'Aspirante')
    EntrevistaVirtual = apps.get_model('preregistro', 'EntrevistaVirtual')
    Aspirante.objects.filter(is_superuser=True, rol='aspirante').update(rol='admin')
    Aspirante.objects.filter(
        is_staff=True, is_superuser=False,
        rol__in=['servicios', 'servicios_escolares', 'servicios escolares'],
    ).update(is_staff=False)
    EntrevistaVirtual.objects.filter(jitsi_room_link__contains='meet.jitsi.si').update(
        jitsi_room_link=Replace('jitsi_room_link', models.Value('meet.jitsi.si'), models.Value('meet.jit.si'))
    )


class Migration(migrations.Migration):

    dependencies = [
        ('preregistro', '0052_historialpersona_categoria_detalle'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aspirante',
            name='rol',
            field=models.CharField(
                choices=[
                    ('aspirante', 'Aspirante'),
                    ('alumno', 'Alumno'),
                    ('docente', 'Docente'),
                    ('director', 'Director de tesis'),
                    ('investigador', 'Investigador'),
                    ('coordinacion', 'Coordinación'),
                    ('servicios', 'Servicios Escolares'),
                    ('admin', 'Administrador'),
                ],
                default='aspirante',
                max_length=20,
            ),
        ),
        migrations.RunPython(corregir_cuentas, migrations.RunPython.noop),
    ]
