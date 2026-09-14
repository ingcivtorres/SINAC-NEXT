from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies=[('preregistro','0019_cargaacademica')]
    operations=[migrations.CreateModel(name='PeriodoInscripcion',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('nombre',models.CharField(max_length=40,unique=True)),('apertura',models.DateTimeField()),('cierre',models.DateTimeField()),('activo',models.BooleanField(default=False))])]
