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

## Detect clearing in a region

With Earth Engine configured, run the detector over a real AOI and a real
date. The checkpoint's own decision threshold is read from the file, so the
model is applied at the operating point it was selected at:

```powershell
$env:PYTHONPATH = 'backend'
$env:INGEST_BACKEND = 'gee'
python -m deforestwatch.cli detect --aoi hasdeo-pekb --date 2026-11-15 `
  --model models\weak-label-unet-7region.pt
```

It writes a detection count, a `loss_mask.tif` and an RGBA `overlay.png`
under `data/overlays/<run-id>/`. The comparison is the AOI's current window
against the same window a year earlier, so it answers "what has been cleared
since last year" rather than "what changed this fortnight".

For annual polygons and the comparisons that consume them:

```powershell
python scripts\export_annual_detections.py --aoi hasdeo-pekb --years 2024 2025 `
  --model models\weak-label-unet-7region.pt --threshold 0.99
python scripts\export_hansen_reference.py --region hasdeo-pekb --years 2024 2025
python scripts\compare_hansen.py --aoi hasdeo-pekb --years 2024 2025
```

Measured output on `hasdeo-pekb`, against the published PEKB increments:

| window | detected | published |
|---|---:|---:|
| 2024 | 134.45 ha | 150 ha |
| 2025 | 70.48 ha | 133 ha |
| 2019 | 12.69 ha | 81 ha |

The 2019 figure is the honest shape of the current model's limits: it is
trained on 2024-25 Hansen weak labels and tracks those years far better than
earlier ones. Read [docs/MODEL-CARD.md](docs/MODEL-CARD.md) before quoting any
of these: they measure agreement with Hansen, not field accuracy.

Scheduled monitoring is a different question from the above. `dw detect`
compares against last year; the worker compares the last three weeks against
the preceding three and the same period a year back, so it alerts on change
that is *recent*, which is what the 48-hour target means:

```powershell
python -m deforestwatch.worker --once
```

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
