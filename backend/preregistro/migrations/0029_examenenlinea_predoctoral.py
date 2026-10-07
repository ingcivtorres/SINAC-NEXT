from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('preregistro', '0028_proyectotesis'),
    ]

    operations = [
        migrations.AlterField(
            model_name='examenenlinea',
            name='tipo',
            field=models.CharField(
                choices=[
                    ('admision', 'Examen de Admisión'),
                    ('seleccion', 'Examen de Selección'),
                    ('diagnostico', 'Examen de Diagnóstico'),
                    ('predoctoral', 'Examen predoctoral'),
                    ('otro', 'Otro'),
                ],
                max_length=20,
            ),
        ),
    ]
