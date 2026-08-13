from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('preregistro', '0007_add_leido_field')]

    operations = [
        migrations.AddField(model_name='aspirante', name='banco_apoyo', field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name='aspirante', name='clabe_interbancaria', field=models.CharField(blank=True, max_length=18)),
        migrations.AddField(model_name='aspirante', name='solicitud_apoyo_fecha', field=models.DateTimeField(blank=True, null=True)),
    ]
