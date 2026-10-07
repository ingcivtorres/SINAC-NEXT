from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('preregistro', '0037_inscripcion_unica_por_periodo'),
    ]

    operations = [
        migrations.AddField(
            model_name='materia',
            name='categoria',
            field=models.CharField(
                choices=[
                    ('nucleo', 'Núcleo'),
                    ('formativo', 'Formativo'),
                    ('especializacion', 'Especialización / tópico'),
                    ('adicional', 'Curso adicional'),
                    ('seminario', 'Seminario'),
                    ('tesis', 'Trabajo de tesis'),
                ],
                default='formativo',
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name='materia',
            name='lgacs',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
