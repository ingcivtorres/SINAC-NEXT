from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies=[('preregistro','0020_periodoinscripcion')]
    operations=[migrations.AddField(model_name='inscripcion',name='parcial_1',field=models.DecimalField(blank=True,decimal_places=2,max_digits=4,null=True)),migrations.AddField(model_name='inscripcion',name='parcial_2',field=models.DecimalField(blank=True,decimal_places=2,max_digits=4,null=True)),migrations.AddField(model_name='inscripcion',name='parcial_3',field=models.DecimalField(blank=True,decimal_places=2,max_digits=4,null=True))]
