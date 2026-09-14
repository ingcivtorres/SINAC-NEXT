from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('preregistro', '0015_preguntarespuestaexamen')]
    operations = [migrations.AddField(model_name='aspirante', name='matricula', field=models.CharField(blank=True, max_length=30, null=True, unique=True))]
