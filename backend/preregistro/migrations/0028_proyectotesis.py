import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('preregistro', '0027_inscripcion_periodo_inscripcion'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProyectoTesis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=255)),
                ('resumen', models.TextField()),
                ('linea_investigacion', models.CharField(blank=True, max_length=180)),
                ('objetivos', models.TextField(blank=True)),
                ('metodologia', models.TextField(blank=True)),
                ('comentarios_revision', models.TextField(blank=True)),
                ('estado', models.CharField(choices=[('borrador', 'Borrador'), ('en_revision', 'En revisión'), ('observado', 'Con observaciones'), ('aprobado', 'Aprobado'), ('rechazado', 'Rechazado'), ('concluido', 'Concluido')], default='borrador', max_length=20)),
                ('fecha_presentacion', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('alumno', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='proyectos_tesis', to='preregistro.aspirante')),
                ('director', models.ForeignKey(blank=True, limit_choices_to={'rol': 'director'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='proyectos_dirigidos', to='preregistro.aspirante')),
            ],
            options={
                'verbose_name': 'Proyecto de tesis',
                'verbose_name_plural': 'Proyectos de tesis',
                'ordering': ['-updated_at'],
            },
        ),
    ]
