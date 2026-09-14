import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from preregistro.models import Aspirante

# Crear usuario docente de prueba
user, created = Aspirante.objects.get_or_create(
    usuario='docente_test',
    defaults={
        'nombre': 'Docente Test',
        'correo': 'docente@test.sinac.edu.mx',
        'curp': 'DOCT850101HDFRNN01',
        'telefono': '5555555555',
        'estado_actual': 'Ciudad de México',
        'municipio_actual': 'Coyoacán',
        'direccion_actual': 'Calle Test',
        'estado_permanente': 'Ciudad de México',
        'municipio_permanente': 'Coyoacán',
        'direccion_permanente': 'Calle Test',
        'nombre_familiar': 'Familiar',
        'parentesco': 'Padre',
        'telefono_familiar': '5555555555',
        'ultimo_grado': 'Licenciatura',
        'institucion': 'Cinvestav',
        'unidad': 'Cinvestav',
        'departamento': 'Academia',
        'seccion': 'Posgrado',
        'programa': 'Ingeniería',
        'rol': 'docente',
        'is_active': True,
        'business_key': 'DOCENTE-TEST-001',
    }
)

if created:
    user.set_password('TestPass123!')
    user.save()
    print(f'✓ Usuario creado: {user.usuario} ({user.correo})')
    print(f'  Contraseña: TestPass123!')
    print(f'  Rol: {user.rol}')
    print(f'  Activo: {user.is_active}')
else:
    print(f'✓ Usuario ya existe: {user.usuario}')
    # Actualizar contraseña
    user.set_password('TestPass123!')
    user.save()
    print(f'  Contraseña actualizada: TestPass123!')
