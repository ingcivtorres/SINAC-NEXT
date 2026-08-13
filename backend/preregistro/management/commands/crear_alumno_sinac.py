import os

from django.core.management.base import BaseCommand, CommandError

from preregistro.models import Aspirante


class Command(BaseCommand):
    help = 'Crea o actualiza una cuenta de alumno para SINAC NEXT.'

    def handle(self, *args, **options):
        password = os.environ.get('SINAC_ALUMNO_PASSWORD')
        if not password:
            raise CommandError('Define la variable de entorno SINAC_ALUMNO_PASSWORD.')

        usuario = os.environ.get('SINAC_ALUMNO_USUARIO', 'alumno')
        correo = os.environ.get('SINAC_ALUMNO_CORREO', 'alumno@sinac.local')

        user, created = Aspirante.objects.get_or_create(
            usuario=usuario,
            defaults={
                'correo': correo,
                'nombre': 'Alumno SINAC',
                'curp': 'ALUM000000HDF00001',
                'telefono': '0000000000',
                'estado_actual': 'Ciudad de México',
                'municipio_actual': 'Coyoacán',
                'direccion_actual': 'Cinvestav',
                'estado_permanente': 'Ciudad de México',
                'municipio_permanente': 'Coyoacán',
                'direccion_permanente': 'Cinvestav',
                'nombre_familiar': 'No aplica',
                'parentesco': 'No aplica',
                'telefono_familiar': '0000000000',
                'ultimo_grado': 'Licenciatura',
                'institucion': 'Cinvestav',
                'unidad': 'Estudios',
                'departamento': 'Académico',
                'seccion': 'Alumno',
                'programa': 'SINAC NEXT',
                'business_key': 'ALUMNO-SINAC',
                'rol': 'alumno',
            },
        )

        user.correo = correo
        user.rol = 'alumno'
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        user.set_password(password)
        user.save()

        verb = 'creada' if created else 'actualizada'
        self.stdout.write(self.style.SUCCESS(f'Cuenta alumno {verb}: {usuario} / {correo}'))
