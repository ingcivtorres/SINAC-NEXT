from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('preregistro', '0035_aspirante_numero_periodo_actual'),
    ]

    operations = [
        migrations.AddField(
            model_name='inscripcion',
            name='validacion_servicios',
            field=models.CharField(choices=[('pendiente', 'Pendiente'), ('validada', 'Validada'), ('observada', 'Observada')], default='pendiente', max_length=12),
        ),
    ]