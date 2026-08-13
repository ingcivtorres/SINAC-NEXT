from django.db import migrations, models
import django.db.models.deletion


def crear_eventos_iniciales(apps, schema_editor):
    Aspirante = apps.get_model('preregistro', 'Aspirante')
    SeguimientoSolicitud = apps.get_model('preregistro', 'SeguimientoSolicitud')
    for aspirante in Aspirante.objects.filter(is_staff=False):
        SeguimientoSolicitud.objects.create(
            aspirante_id=aspirante.pk,
            estado=aspirante.proceso_estado,
            detalle='Estado inicial recuperado para el seguimiento de solicitud.',
            origen='Sistema SINAC NEXT',
        )


class Migration(migrations.Migration):
    dependencies = [('preregistro', '0002_documentoaspirante')]

    operations = [
        migrations.AddField(
            model_name='aspirante',
            name='camunda_instance_id',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.CreateModel(
            name='SeguimientoSolicitud',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado', models.CharField(max_length=40)),
                ('detalle', models.CharField(max_length=255)),
                ('origen', models.CharField(max_length=80)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('aspirante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='seguimientos', to='preregistro.aspirante')),
            ],
            options={'verbose_name': 'Seguimiento de solicitud', 'verbose_name_plural': 'Seguimientos de solicitudes', 'ordering': ['-created_at']},
        ),
        migrations.RunPython(crear_eventos_iniciales, migrations.RunPython.noop),
    ]
