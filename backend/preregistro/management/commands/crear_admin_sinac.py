import os

from django.core.management.base import BaseCommand, CommandError

from preregistro.models import Aspirante


class Command(BaseCommand):
    help = 'Crea o actualiza la cuenta administradora de SINAC NEXT.'

    def handle(self, *args, **options):
        password = os.environ.get('SINAC_ADMIN_PASSWORD')
        if not password:
            raise CommandError('Define la variable de entorno SINAC_ADMIN_PASSWORD.')

        user, created = Aspirante.objects.get_or_create(
            usuario='admin',
            defaults={
                'correo': 'admin@sinac.local',
                'nombre': 'Administrador SINAC',
                'curp': 'ADMS000000HDF00001',
                'telefono': '0000000000',
                'estado_actual': 'Ciudad de México',
                'municipio_actual': 'Gustavo A. Madero',
                'direccion_actual': 'Cinvestav',
                'estado_permanente': 'Ciudad de México',
                'municipio_permanente': 'Gustavo A. Madero',
                'direccion_permanente': 'Cinvestav',
                'nombre_familiar': 'No aplica',
                'parentesco': 'No aplica',
                'telefono_familiar': '0000000000',
                'ultimo_grado': 'No aplica',
                'institucion': 'Cinvestav',
                'unidad': 'Administración',
                'departamento': 'SINAC',
                'seccion': 'Administración',
                'programa': 'SINAC NEXT',
                'business_key': 'ADMIN-SINAC',
            },
        )
        user.correo = 'admin@sinac.local'
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()
        verb = 'creada' if created else 'actualizada'
        self.stdout.write(self.style.SUCCESS(f'Cuenta administradora {verb}.'))
