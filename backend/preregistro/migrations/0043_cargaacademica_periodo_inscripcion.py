import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('preregistro', '0042_cargaacademicamateria'),
    ]

    operations = [
        migrations.AddField(
            model_name='cargaacademica',
            name='periodo_inscripcion',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='cargas_academicas',
                to='preregistro.periodoinscripcion',
            ),
        ),
    ]
