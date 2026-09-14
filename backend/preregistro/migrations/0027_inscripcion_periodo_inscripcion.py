import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('preregistro', '0026_backfill_director_tesis'),
    ]

    operations = [
        migrations.AddField(
            model_name='inscripcion',
            name='periodo_inscripcion',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='inscripciones',
                to='preregistro.periodoinscripcion',
            ),
        ),
    ]
