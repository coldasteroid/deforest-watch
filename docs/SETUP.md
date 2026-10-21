# DeforestWatch setup and cold-start rehearsal

The repository supports a fixture-only development path and a live path. The
fixture path never requires Earth Engine credentials or a database; live AOI,
run, alert, and subscriber routes require PostgreSQL/PostGIS.

## 1. Verify prerequisites

From the repository root:

```powershell
python scripts\environment_check.py
python scripts\database_check.py
python scripts\verify_contract.py
# After configuring credentials, use: python scripts\environment_check.py --live
python scripts\phase_gate.py
```

The environment report must not print secret contents. An approximate Nepal
event marker is expected until the event impact polygons are independently
verified.

## 2. Fixture smoke path

```powershell
python -m pip install -r requirements.txt
$env:INGEST_BACKEND = 'fixture'
python scripts\backfill_runs.py --aoi hasdeo-pekb --start 2013 --end 2025
Remove-Item Env:INGEST_BACKEND
python -m pytest backend/tests -q
Push-Location frontend
npm ci
npm test -- --run
npm run build
Pop-Location
```

The fixture backfill writes regenerable output under `data/backfill/`; it does
not represent independent field validation.

## 3. Live backend path

1. Copy `.env.example` to `.env` and set `DATABASE_URL`, `ADMIN_API_KEY`, and
   `GEE_PROJECT`.
2. Put the Earth Engine service-account JSON at
   `secrets/gee-service-account.json`. Never commit or print it.
3. Start PostGIS using `infra/docker-compose.yml`, verify it with
   `python scripts\database_check.py`, then run:

```powershell
Push-Location backend
$env:PYTHONPATH = '.'
alembic upgrade head
python scripts\seed_aois.py
$env:TEAM_EMAIL = 'operator@example.org'
python scripts\seed_subscribers.py
Remove-Item Env:TEAM_EMAIL
python -m deforestwatch.ingest.check
uvicorn deforestwatch.api.main:app --reload --port 8000
Pop-Location
```

The ingestion check must report `gee_initialized: True` before claiming a
real imagery fetch. The API health route must report `db: true`; otherwise the
live gate remains open.

## 4. Dashboard

```powershell
Push-Location frontend
npm ci
npm run dev
Pop-Location
```

Set `VITE_API_URL` to the live API when integrating. With no live backend, the
MSW fixture handlers exercise the dashboard contract and the UI must continue
to show a degraded/live-updates-unavailable state rather than fabricate live
results.
