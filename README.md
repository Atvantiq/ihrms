# Atvantiq People (iHRMS)

Multi-tenant iHRMS — hire to retire, one platform. Reverse-engineered from the
41-screen prototype; full specification in [`blueprint/`](blueprint/README.md).

## Repository layout (monorepo — one repo, independent apps)

```
blueprint/            Complete implementation blueprint (start at README)
apps/
  web/                Next.js 16 + TypeScript + Tailwind v4 (Prism design tokens)
services/
  api/                FastAPI + SQLAlchemy 2 + Alembic (Python 3.12+)
packages/
  api-client/         TS client generated from the API's OpenAPI spec
  ui/                 (reserved) shared components extracted from apps/web
infra/                (reserved) deploy/infra config
```

## Database — shared with ONAQT (read blueprint doc 24 first)

The dev Supabase Postgres is **shared with the live ONAQT app**:

- `public` schema = ONAQT's tables (employees, job_details, …) — **never modify**
- `ihrms` schema = all iHRMS tables, views, and its own Alembic history
- App code reads employees via `ihrms.v_employee`, never `public.*` directly
- IPv4 networks must use the session pooler host (`aws-1-ap-south-1.pooler.supabase.com`)

## Quick start

### API
```bash
cd services/api
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env            # fill in DATABASE_URL (percent-encode special chars!)
DATABASE_URL=... .venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --port 8000
# http://localhost:8000/docs  ·  /api/v1/health
```

### Web
```bash
cd apps/web
npm install
npm run dev                     # http://localhost:3000
```

### Regenerate the API client (after backend changes)
```bash
npm run generate --workspace packages/api-client   # API must be running
```

## Engineering rules (blueprint doc 17 §17.4)

- Money is `decimal.Decimal` only — `float` is banned in financial code (`app/core/money.py`)
- `mypy --strict`; Pydantic models at every boundary
- All iHRMS migrations create objects in the `ihrms` schema only
- Next.js renders, FastAPI decides — no business logic in the web app
