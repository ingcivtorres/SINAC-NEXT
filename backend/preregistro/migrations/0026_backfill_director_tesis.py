from django.db import migrations


def vincular_directores_existentes(apps, schema_editor):
    Aspirante = apps.get_model('preregistro', 'Aspirante')
    directores = list(Aspirante.objects.filter(rol='director', is_staff=False).only('id', 'nombre', 'usuario'))
    por_nombre = {director.nombre.strip().casefold(): director for director in directores if director.nombre}
    por_usuario = {director.usuario.strip().casefold(): director for director in directores if director.usuario}
    alumnos = Aspirante.objects.filter(director_tesis__isnull=True).exclude(tutor_propuesto='').only('id', 'tutor_propuesto')
    for alumno in alumnos.iterator():
        clave = alumno.tutor_propuesto.strip().casefold()
        director = por_nombre.get(clave) or por_usuario.get(clave)
        if director:
            Aspirante.objects.filter(pk=alumno.pk).update(director_tesis_id=director.pk)


class Migration(migrations.Migration):
    dependencies = [
        ('preregistro', '0025_aspirante_director_tesis'),
    ]

    operations = [migrations.RunPython(vincular_directores_existentes, migrations.RunPython.noop)]
