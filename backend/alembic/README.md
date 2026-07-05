# Alembic Migrations

This directory is reserved for database migrations.

Initialize Alembic here when the database model layer is ready:

```powershell
cd backend
python -m alembic init alembic
```

Migration versions should live in `backend/alembic/versions/`.
