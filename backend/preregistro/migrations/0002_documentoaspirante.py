# Generated manually for document upload support.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('preregistro', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='DocumentoAspirante',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('cv', 'Currículum vitae'), ('titulo', 'Título o comprobante de estudios'), ('carta_motivacion', 'Carta de motivos'), ('carta_recomendacion', 'Carta de recomendación')], max_length=30)),
                ('archivo', models.FileField(upload_to='aspirantes/%Y/%m/')),
                ('nombre_original', models.CharField(max_length=255)),
                ('tamano', models.PositiveIntegerField()),
                ('lida_notificado', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('aspirante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documentos', to='preregistro.aspirante')),
            ],
            options={'verbose_name': 'Documento de aspirante', 'verbose_name_plural': 'Documentos de aspirantes'},
        ),
        migrations.AddConstraint(model_name='documentoaspirante', constraint=models.UniqueConstraint(fields=('aspirante', 'tipo'), name='documento_unico_por_tipo')),
    ]
