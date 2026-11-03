from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('preregistro', '0051_examen_evaluador_entrevista_docente'),
    ]

    operations = [
        migrations.AddField(
            model_name='historialpersona',
            name='categoria',
            field=models.CharField(
                choices=[
                    ('cuenta', 'Cuenta y datos'),
                    ('academico', 'Académico'),
                    ('tesis', 'Tesis'),
                    ('documentos', 'Documentos'),
                    ('egreso', 'Egreso'),
                ],
                db_index=True,
                default='cuenta',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='historialpersona',
            name='detalle',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
