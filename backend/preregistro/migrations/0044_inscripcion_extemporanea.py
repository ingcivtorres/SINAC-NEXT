from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('preregistro', '0043_cargaacademica_periodo_inscripcion'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='inscripcion',
            name='extemporanea',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='inscripcion',
            name='motivo_extemporanea',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='inscripcion',
            name='registrada_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='inscripciones_extemporaneas_registradas',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
