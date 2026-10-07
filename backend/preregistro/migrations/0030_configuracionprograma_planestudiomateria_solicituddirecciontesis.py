from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('preregistro', '0029_examenenlinea_predoctoral')]

    operations = [
        migrations.CreateModel(
            name='ConfiguracionPrograma',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('programa', models.CharField(max_length=180, unique=True)),
                ('grado', models.CharField(choices=[('maestria', 'Maestría'), ('doctorado', 'Doctorado')], max_length=20)),
                ('periodicidad', models.CharField(choices=[('semestral', 'Semestral'), ('cuatrimestral', 'Cuatrimestral')], default='semestral', max_length=20)),
                ('duracion_anios', models.PositiveSmallIntegerField(default=2)),
                ('periodos_requeridos', models.PositiveSmallIntegerField(default=4)),
                ('creditos_requeridos', models.PositiveSmallIntegerField(default=0)),
                ('activo', models.BooleanField(default=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'Configuración de programa', 'verbose_name_plural': 'Configuraciones de programas', 'ordering': ['programa']},
        ),
        migrations.CreateModel(
            name='PlanEstudioMateria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('periodo_sugerido', models.PositiveSmallIntegerField(default=1)),
                ('obligatoria', models.BooleanField(default=True)),
                ('configuracion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='materias_plan', to='preregistro.configuracionprograma')),
                ('materia', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='planes_estudio', to='preregistro.materia')),
            ],
            options={'ordering': ['periodo_sugerido', 'materia__clave'], 'unique_together': {('configuracion', 'materia')}},
        ),
        migrations.CreateModel(
            name='SolicitudDireccionTesis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('linea_investigacion', models.CharField(blank=True, max_length=180)),
                ('justificacion', models.TextField(blank=True)),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente de revisión'), ('aprobada', 'Director asignado'), ('rechazada', 'Rechazada'), ('cancelada', 'Cancelada')], default='pendiente', max_length=20)),
                ('observaciones', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('alumno', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='solicitudes_direccion_tesis', to='preregistro.aspirante')),
                ('director_asignado', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='asignaciones_direccion_tesis', to='preregistro.aspirante')),
                ('director_sugerido', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='solicitudes_sugeridas', to='preregistro.aspirante')),
                ('revisado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='solicitudes_tesis_revisadas', to='preregistro.aspirante')),
            ],
            options={'ordering': ['-updated_at']},
        ),
    ]
