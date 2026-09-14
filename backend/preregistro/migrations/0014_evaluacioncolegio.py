from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('preregistro', '0013_repair_examenenlinea_table')]
    operations = [migrations.CreateModel(name='EvaluacionColegio', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('estado', models.CharField(choices=[('pendiente','Pendiente'),('en_revision','En revisión'),('favorable','Favorable'),('no_favorable','No favorable')], default='pendiente', max_length=20)), ('dictamen', models.TextField(blank=True)), ('fecha_evaluacion', models.DateTimeField(blank=True, null=True)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)), ('aspirante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evaluaciones_colegio', to='preregistro.aspirante')), ('evaluador', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='evaluaciones_realizadas', to='preregistro.aspirante'))])]
