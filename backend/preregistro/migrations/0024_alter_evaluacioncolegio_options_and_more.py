from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('preregistro', '0023_auditoria_configuracion')]

    operations = [
        migrations.AlterModelOptions(
            name='evaluacioncolegio',
            options={'ordering': ['-created_at']},
        ),
        migrations.AlterModelOptions(
            name='preguntaexamen',
            options={'ordering': ['orden', 'id']},
        ),
    ]
