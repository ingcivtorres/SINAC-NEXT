import os

from django.core.management.base import BaseCommand, CommandError

from preregistro.models import Aspirante


class Command(BaseCommand):
    help = 'Crea o actualiza una cuenta docente para SINAC NEXT.'

    def handle(self, *args, **options):
        password = os.environ.get('SINAC_DOCENTE_PASSWORD')
        if not password:
            raise CommandError('Define la variable de entorno SINAC_DOCENTE_PASSWORD.')

        usuario = os.environ.get('SINAC_DOCENTE_USUARIO', 'docente')
        correo = os.environ.get('SINAC_DOCENTE_CORREO', 'docente@sinac.local')

        user, created = Aspirante.objects.get_or_create(
            usuario=usuario,
            defaults={
                'correo': correo,
                'nombre': 'Docente SINAC',
                'curp': 'DOCT000000HDF00001',
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
                'ultimo_grado': 'Doctorado',
                'institucion': 'Cinvestav',
                'unidad': 'Investigación',
                'departamento': 'Docencia',
                'seccion': 'Docencia',
                'programa': 'SINAC NEXT',
                'business_key': 'DOCENTE-SINAC',
                'rol': 'docente',
            },
        )

        user.correo = correo
        user.rol = 'docente'
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        user.set_password(password)
        user.save()

        verb = 'creada' if created else 'actualizada'
        self.stdout.write(self.style.SUCCESS(f'Cuenta docente {verb}: {usuario} / {correo}'))
