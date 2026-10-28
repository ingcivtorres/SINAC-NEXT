# SINAC-NEXT

## Arquitectura propuesta

Esta carpeta está preparada para una arquitectura híbrida con:

- Backend en Python + Django
- Frontend en React
- Camunda como motor de procesos
- PostgreSQL como base de datos
- Docker Compose para orquestación

## Servicios

- Frontend: http://localhost:3000
- Backend: http://localhost:8000/health
- Camunda: http://localhost:8081
- PostgreSQL: localhost:5433

## Ejecutar

```powershell
docker compose up --build -d
```

## Configuración de seguridad

En producción, configura `DJANGO_SECRET_KEY` con una clave aleatoria y establece
`DJANGO_DEBUG=False`. El backend no inicia en modo de producción si falta la clave.
No guardes la clave en el repositorio. Por ejemplo, en PowerShell puedes generar
una para la sesión actual con:

```powershell
$env:DJANGO_SECRET_KEY = (& .\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
$env:DJANGO_DEBUG = "False"
```

Al usar Docker Compose, proporciona esas variables al proceso que ejecuta
`docker compose up`; la clave no debe incluirse en el archivo Compose.
