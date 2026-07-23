# ScanX Billing Service

Milestone 1 foundation for institutional referral invoicing.

## Included

- FastAPI application skeleton
- Environment-based configuration
- JSON structured logging
- SQLAlchemy 2.0
- Cloud SQL Python Connector using `pg8000`
- Alembic migrations
- Existing `organization_invoices` model
- Unique one-invoice-per-referral migration
- `/health` and `/health/ready`
- Dockerfile and starter test

## Local setup

```cmd
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Update `.env` with the real Cloud SQL credentials.

Authenticate Application Default Credentials:

```cmd
gcloud auth application-default login
gcloud config set project vernal-maker-473121-k4
```

Start locally:

```cmd
uvicorn app.main:app --reload
```

Check:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/health/ready
```

## Migration safety check

Before applying the unique index, confirm no duplicate invoice rows already exist:

```sql
SELECT appointment_referral_id, COUNT(*)
FROM organization_invoices
GROUP BY appointment_referral_id
HAVING COUNT(*) > 1;
```

If the query returns no rows:

```cmd
alembic upgrade head
```

Inspect migration state:

```cmd
alembic current
alembic history
```

## Tests

```cmd
pytest -q
```

## Notes

- The invoice table already exists; this project maps it and adds only the missing unique safeguard.
- Do not run `Base.metadata.create_all()` against production.
- Alembic is the only supported path for schema changes.
