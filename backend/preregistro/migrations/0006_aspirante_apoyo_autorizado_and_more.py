from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('preregistro', '0005_alter_aspirante_rol'),
    ]

    operations = [
        migrations.AddField(
            model_name='aspirante',
            name='fecha_examen_admision',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='aspirante',
            name='fecha_entrevista',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='aspirante',
            name='fecha_inicio_curso_propedeutico',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='aspirante',
            name='curso_propedeutico_nota',
            field=models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='aspirante',
            name='curso_propedeutico_aprobado',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='aspirante',
            name='apoyo_solicitado',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='aspirante',
            name='apoyo_autorizado',
            field=models.BooleanField(default=False),
        ),
    ]
