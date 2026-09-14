from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('preregistro', '0017_expedientedigital')]
    operations = [migrations.CreateModel(
        name='FirmaElectronica',
        fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('rol_firmante', models.CharField(default='director', max_length=40)),
            ('huella', models.CharField(max_length=64, unique=True)),
            ('firmado_at', models.DateTimeField(auto_now_add=True)),
            ('expediente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='firmas', to='preregistro.expedientedigital')),
            ('firmante', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='firmas_realizadas', to='preregistro.aspirante')),
        ],
        options={'unique_together': {('expediente', 'firmante', 'rol_firmante')}},
    )]
