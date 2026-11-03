import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('preregistro', '0050_proyectotesis_avance_porcentaje'),
    ]

    operations = [
        migrations.AddField(
            model_name='examenenlinea',
            name='evaluador',
            field=models.ForeignKey(
                blank=True,
                help_text='Docente autorizado para ajustar la calificación del examen.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='examenes_evaluados',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='entrevistavirtual',
            name='docente',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='entrevistas_conducidas',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
