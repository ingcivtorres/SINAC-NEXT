from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('preregistro', '0016_aspirante_matricula')]

    operations = [
        migrations.CreateModel(
            name='ExpedienteDigital',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('folio', models.CharField(max_length=40, unique=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('estado', models.CharField(default='activo', max_length=20)),
                ('aspirante', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='expediente_digital', to='preregistro.aspirante')),
            ],
            options={'verbose_name': 'Expediente digital', 'verbose_name_plural': 'Expedientes digitales'},
        ),
    ]
