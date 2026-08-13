from django.db import migrations, models


class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ('preregistro', '0008_datos_bancarios_apoyo'),
    ]

    operations = [
        migrations.CreateModel(
            name='Materia',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('clave', models.CharField(max_length=40, unique=True)),
                ('nombre', models.CharField(max_length=200)),
                ('profesor', models.CharField(blank=True, max_length=180)),
                ('horario', models.CharField(blank=True, max_length=120)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Materia',
                'verbose_name_plural': 'Materias',
            },
        ),
    ]
