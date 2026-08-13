from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('preregistro', '0006_aspirante_apoyo_autorizado_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='seguimientosolicitud',
            name='leido',
            field=models.BooleanField(default=False),
        ),
    ]
