# DeforestWatch — start here

An AI-based deforestation alert system. It watches the Hasdeo Aranya forest in Chhattisgarh with free Sentinel-2 satellite imagery, finds newly cleared forest with a U-Net deep-learning model, and sends SMS and email alerts to forest officers within 48 hours — instead of the weeks or months that current monitoring takes.

Minor Project, VII semester, B.Tech CSE, BPIT, Group G1.

---

## Which document do I open?

**Four documents. You almost certainly need two of them, not four.**

| If you are… | Read | Ignore |
|---|---|---|
| Building the **server**, model and pipeline | `02-BACKEND-SPEC.md` + `01-API-CONTRACT.md` | the frontend spec |
| Building the **dashboard** | `03-FRONTEND-SPEC.md` + `01-API-CONTRACT.md` | the backend spec |
| Writing the **report** or presenting | `02-BACKEND-SPEC.md` §1–§3 and Appendices F–H | the phase plans |

```
docs/
├─ 00-README.md          you are here
├─ 01-API-CONTRACT.md    THE SEAM — both developers read this one
├─ 02-BACKEND-SPEC.md    Python, Earth Engine, U-Net, PostGIS, alerts, scheduler
└─ 03-FRONTEND-SPEC.md   React, Leaflet, Chart.js, the six screens
```

## Why it is split this way

The two halves are built **in parallel and never block each other**.

The frontend developer runs the whole dashboard against a mock server from day one — no Python, no database, no Earth Engine account. The backend developer builds against `curl` and `pytest` — no browser. They meet once, at the end, for about half a day, and the only realistic failure is a field name that drifted.

That works only because `01-API-CONTRACT.md` is frozen. Both sides implement it exactly. If something is missing from it, add it there first and tell the other person — do not invent a field on one side.

Two files in the repo are already written and are part of that contract:

- `frontend/src/api/types.ts` — every API response shape, in TypeScript
- `frontend/src/mocks/fixtures.ts` — seed data at realistic magnitudes for the study region

## Handing this to an AI coding agent

Upload **one** spec plus the API contract, not the whole folder. Then:

```text
You are implementing the DeforestWatch <backend|frontend>. The specification is in
docs/02-BACKEND-SPEC.md (or docs/03-FRONTEND-SPEC.md) and the API contract is in
docs/01-API-CONTRACT.md. Read both in full before writing code.

Execute ONLY Phase <N>. Rules:
1. Follow every name in the spec exactly — modules, tables, endpoints, env vars, props.
2. The API contract is frozen: paths, field names, status codes and enum strings are
   normative. If you think something is missing, stop and say so; do not invent a field.
3. Use only the frozen stack. Do not add libraries that are not listed.
4. Write the tests the phase lists and make them pass.
5. When done, run the phase's "Done when" block, paste the output, list any deviation
   with a one-line reason, and STOP. Do not start the next phase.
6. If a step needs a human (an API key, an account, a dataset download, manual
   labelling), stop and say exactly what to do and where to put the result.
```

Phases are sized at one to three days each. Do them in order and do not start the next one until the current "Done when" block passes.

## The shape of the system

```
Sentinel-2 / Landsat 8          Google Earth Engine
        │
        ▼
  ingest → preprocess → detect → alert         PostgreSQL + PostGIS
  (GeoTIFF)  (NDVI,     (U-Net)  (Twilio SMS,        │
             256px chips)         SMTP email)        │
        │                                            │
        └──────────────► FastAPI :8000 ◄─────────────┘
                              │
                     01-API-CONTRACT.md
                              │
                    React + Leaflet :3000
```

Five layers, four of them server-side. The dashboard is the fifth and talks to the other four only through the API.

## What has to happen before any code

Three accounts, and one of them can take hours to approve — start it today:

1. **Google Earth Engine** — free non-commercial signup, a Google Cloud project, the Earth Engine API enabled, a service account with the *Earth Engine Resource Writer* role, and its JSON key saved to `secrets/`. Approval is not instant.
2. **Twilio** — trial account for SMS. Trial accounts only send to numbers you have verified, so verify the team's phones early.
3. **Gmail app password** — for SMTP email.

Full list with where each result goes: `02-BACKEND-SPEC.md` §0.3.

## Two things to verify before quoting them in the report

1. **The `hasdeo-pekb` bounding box.** Corrected in v1.3 after the original estimate was found to miss the mine by about 14 km; it is now centred on the published PEKB coordinates. Still a desk correction from a secondary source — confirm it on a satellite basemap before the first real run. `02-BACKEND-SPEC.md` §3.1 and risk R13.
2. **The 1,013 ha published figure**, which the headline validation compares against. It is a manually digitised research estimate — its own author calls it that, and it was drawn partly from imagery finer than our 10 m Sentinel-2. Never call the comparison "accuracy". §1.4 and risk R14.
