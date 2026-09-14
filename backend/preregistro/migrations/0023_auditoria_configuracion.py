from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('preregistro', '0022_materia_creditos'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditoriaSistema',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('accion', models.CharField(max_length=80)),
                ('modelo', models.CharField(max_length=80)),
                ('objeto_id', models.CharField(blank=True, max_length=80)),
                ('datos_anteriores', models.JSONField(blank=True, default=dict)),
                ('datos_nuevos', models.JSONField(blank=True, default=dict)),
                ('ip', models.GenericIPAddressField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='auditorias_realizadas', to='preregistro.aspirante')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='ConfiguracionSistema',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('clave', models.CharField(max_length=80, unique=True)),
                ('valor', models.TextField(blank=True)),
                ('descripcion', models.CharField(blank=True, max_length=255)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('actualizado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='configuraciones_actualizadas', to='preregistro.aspirante')),
            ],
        ),
    ]
