from django.db import migrations, models
import django.db.models.deletion
class Migration(migrations.Migration):
    dependencies=[('preregistro','0018_firmaelectronica')]
    operations=[migrations.CreateModel(name='CargaAcademica',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('estado',models.CharField(choices=[('borrador','Borrador'),('en_revision','En revisión'),('aprobada','Aprobada'),('publicada','Publicada'),('rechazada','Rechazada')],default='borrador',max_length=20)),('periodo',models.CharField(blank=True,max_length=30)),('camunda_instance_id',models.CharField(blank=True,max_length=80)),('comentario',models.TextField(blank=True)),('created_at',models.DateTimeField(auto_now_add=True)),('updated_at',models.DateTimeField(auto_now=True)),('creador',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='cargas_creadas',to='preregistro.aspirante'))],)]
