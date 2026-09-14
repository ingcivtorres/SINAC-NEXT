from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('preregistro', '0024_alter_evaluacioncolegio_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='aspirante',
            name='director_tesis',
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={'rol': 'director'},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='tesistas_asignados',
                to='preregistro.aspirante',
            ),
        ),
    ]
