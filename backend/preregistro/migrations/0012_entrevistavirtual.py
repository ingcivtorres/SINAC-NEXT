from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('preregistro', '0011_aspirante_profile_photo')]

    operations = [
        migrations.CreateModel(
            name='EntrevistaVirtual',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('proposito', models.CharField(choices=[('admision', 'Entrevista de Admisión'), ('seguimiento', 'Seguimiento de progreso'), ('tutoria', 'Tutoría académica'), ('orientacion', 'Orientación vocacional'), ('otro', 'Otro')], max_length=20)),
                ('titulo', models.CharField(default='Entrevista virtual', max_length=255)),
                ('descripcion', models.TextField(blank=True)),
                ('fecha_programada', models.DateTimeField(blank=True, null=True)),
                ('fecha_inicio', models.DateTimeField(blank=True, null=True)),
                ('fecha_fin', models.DateTimeField(blank=True, null=True)),
                ('duracion_minutos', models.PositiveIntegerField(default=30)),
                ('jitsi_room_id', models.CharField(blank=True, max_length=120, unique=True)),
                ('jitsi_room_link', models.URLField(blank=True)),
                ('estado', models.CharField(choices=[('programada', 'Programada'), ('iniciada', 'Iniciada'), ('completada', 'Completada'), ('cancelada', 'Cancelada')], default='programada', max_length=20)),
                ('recording_link', models.URLField(blank=True, help_text='URL de la grabación si está disponible')),
                ('notas_docente', models.TextField(blank=True, help_text='Notas del docente durante la entrevista')),
                ('retroalimentacion', models.TextField(blank=True, help_text='Retroalimentación para el estudiante')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('aspirante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entrevistas_virtuales', to='preregistro.aspirante')),
            ],
            options={'verbose_name': 'Entrevista virtual', 'verbose_name_plural': 'Entrevistas virtuales', 'ordering': ['-fecha_programada']},
        ),
    ]
