from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('preregistro', '0034_materia_capacidad_materia_salon'),
    ]

    operations = [
        migrations.AddField(
            model_name='aspirante',
            name='numero_periodo_actual',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]