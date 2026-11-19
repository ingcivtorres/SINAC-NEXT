from django.db import migrations


def retirar_is_staff(apps, schema_editor):
    Aspirante = apps.get_model('preregistro', 'Aspirante')
    Aspirante.objects.filter(is_staff=True, is_superuser=False).exclude(
        rol__in=['admin', 'coordinacion'],
    ).update(is_staff=False)


class Migration(migrations.Migration):

    dependencies = [
        ('preregistro', '0053_roles_y_privilegios'),
    ]

    operations = [
        migrations.RunPython(retirar_is_staff, migrations.RunPython.noop),
    ]
