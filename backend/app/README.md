# Sprint 1 – Usuarios, sesiones y permisos (JWT + RBAC)

## Requisitos
- Python 3.11+
- Postgres local con DB `multimedia` (ajusta `.env`)
- `pip install -r requirements.txt`

## Configuración
1) Copia `.env.example` a `.env` y ajusta `DATABASE_URL` y `JWT_SECRET`.
2) Crea la base de datos en Postgres:
   ```sql
   CREATE DATABASE multimedia;
