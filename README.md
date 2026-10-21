# DeforestWatch

DeforestWatch monitors forest clearing in the Hasdeo Aranya / PEKB region of
Chhattisgarh using Sentinel-2/Landsat imagery, an NDVI baseline, and a U-Net
detector. The repository also contains a separate disaster-change case study
for the 26 August 2026 Rasuwa / Bhote Koshi ice-rock avalanche and debris-flood
cascade in Nepal. Nepal event change is never counted as Hasdeo deforestation.

## Quick start

```powershell
python scripts\environment_check.py
python scripts\phase_gate.py
$env:INGEST_BACKEND = 'fixture'
python scripts\backfill_runs.py --aoi hasdeo-pekb --start 2013 --end 2025
python -m pytest backend/tests -q
Push-Location frontend
npm ci
npm run dev
Pop-Location
```

The fixture path is reproducible and needs no Earth Engine account or database.
For live operation, follow [docs/SETUP.md](docs/SETUP.md), configure PostGIS
and Earth Engine, then run `python scripts\environment_check.py --live`.

## Project map

- [Implementation plan](docs/IMPLEMENTATION-PLAN.md)
- [Phase status and gates](docs/PHASE-STATUS.md)
- [API contract](docs/01-API-CONTRACT.md)
- [Backend specification](docs/02-BACKEND-SPEC.md)
- [Frontend specification](docs/03-FRONTEND-SPEC.md)
- [Nepal case study](docs/NEPAL-CASE-STUDY.md)
- [Setup](docs/SETUP.md)
- [Demo script](docs/DEMO.md)

Synthetic fixture output is clearly labelled and is not production accuracy
evidence. Production claims require reviewed Hasdeo labels, live imagery, and
independent validation references.
