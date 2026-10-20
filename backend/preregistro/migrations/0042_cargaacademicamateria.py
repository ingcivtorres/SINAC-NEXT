import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('preregistro', '0041_historialpersona'),
    ]

    operations = [
        migrations.CreateModel(
            name='CargaAcademicaMateria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('horario', models.CharField(blank=True, max_length=120)),
                ('salon', models.CharField(choices=[('salon_1', 'Salón 1'), ('laboratorio_harold', 'Laboratorio Harold V. McIntosh'), ('sala_juntas', 'Sala de Juntas')], default='salon_1', max_length=40)),
                ('capacidad', models.PositiveSmallIntegerField(default=42)),
                ('modalidad', models.CharField(choices=[('presencial', 'Presencial'), ('hibrida', 'Híbrida'), ('virtual', 'Virtual')], default='presencial', max_length=20)),
                ('carga', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='materias', to='preregistro.cargaacademica')),
                ('docente', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='materias_carga_academica', to='preregistro.aspirante')),
                ('materia', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cargas_academicas', to='preregistro.materia')),
            ],
            options={
                'constraints': [
                    models.UniqueConstraint(fields=('carga', 'materia'), name='uniq_materia_por_carga_academica'),
                ],
            },
        ),
    ]
