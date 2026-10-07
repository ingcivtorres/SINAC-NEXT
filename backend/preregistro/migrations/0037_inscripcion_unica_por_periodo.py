from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('preregistro', '0036_inscripcion_validacion_servicios'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='inscripcion',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='inscripcion',
            constraint=models.UniqueConstraint(
                condition=models.Q(periodo_inscripcion__isnull=False),
                fields=('aspirante', 'materia', 'periodo_inscripcion'),
                name='unique_inscripcion_por_periodo',
            ),
        ),
        migrations.AddConstraint(
            model_name='inscripcion',
            constraint=models.UniqueConstraint(
                condition=models.Q(periodo_inscripcion__isnull=True),
                fields=('aspirante', 'materia'),
                name='unique_inscripcion_sin_periodo',
            ),
        ),
    ]