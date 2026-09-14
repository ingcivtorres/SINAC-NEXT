from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('preregistro', '0014_evaluacioncolegio')]
    operations = [
        migrations.CreateModel(name='PreguntaExamen', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('texto', models.TextField()), ('opciones', models.JSONField(default=list)), ('respuesta_correcta', models.CharField(max_length=255)), ('orden', models.PositiveIntegerField(default=1)), ('examen', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='preguntas', to='preregistro.examenenlinea'))]),
        migrations.CreateModel(name='RespuestaExamen', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('respuesta', models.CharField(max_length=255)), ('es_correcta', models.BooleanField(default=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('aspirante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='respuestas_examen', to='preregistro.aspirante')), ('examen', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='respuestas', to='preregistro.examenenlinea')), ('pregunta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='respuestas', to='preregistro.preguntaexamen'))]),
        migrations.AlterUniqueTogether(name='respuestaexamen', unique_together={('pregunta', 'aspirante')})]
