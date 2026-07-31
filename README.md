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
