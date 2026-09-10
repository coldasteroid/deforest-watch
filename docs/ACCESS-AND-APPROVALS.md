# DeforestWatch — Accounts, APIs and Approvals

Every credential the project needs, ordered by lead time rather than by phase. Only one item can make you wait; everything else is instant or optional.

**Total cost: zero.** Every service below is used on a free tier. That is success criterion S5, and it is why the stack looks the way it does.

---

## At a glance

| # | Service | Needed for | Phase | Lead time | Cost |
|---|---------|-----------|-------|-----------|------|
| 1 | **Google Earth Engine** | all satellite imagery | 2 | **hours to days** | free (non-commercial) |
| 2 | Twilio | SMS alerts | 7 | instant | free trial credit |
| 3 | Gmail app password | email alerts | 7 | instant | free (~500/day) |
| 4 | NASA Earthdata Login | Phase 10 comparison | 10 | instant | free |
| 5 | Kaggle | optional pretraining | 4 | instant | free |
| 6 | Copernicus Data Space | optional; real imagery before GEE clears | — | instant | free |
| — | ~~Google Maps Platform~~ | **rejected** — see below | — | — | — |
| — | ~~Render / Railway~~ | **dropped** — localhost only | — | — | — |

**Do item 1 today.** Do the rest when you reach the phase.

---

## 1. Google Earth Engine — the only blocking item

**What it gives you.** Every satellite image the project uses: Sentinel-2 at 10 m on a 5-day revisit, Landsat 8 for the 2013–2016 backfill, and the Hansen Global Forest Change layer for weak training labels. There is no local substitute at this scale.

**Steps**

1. Sign up at `earthengine.google.com` and register for **non-commercial** use.
2. Create a Google Cloud project. Billing is **not** required for non-commercial Earth Engine.
3. Enable the **Earth Engine API** on that project.
4. Register the project for Earth Engine use.
5. Create a **service account** under IAM → Service Accounts.
6. Grant it the **Earth Engine Resource Writer** role.
7. Create a JSON key and download it.

**Where the credentials go**

```
secrets/gee-service-account.json      the downloaded key (git-ignored)
.env    GEE_SERVICE_ACCOUNT_EMAIL     the service account address
        GEE_PROJECT                   the Cloud project id
        GEE_KEY_FILE                  ./secrets/gee-service-account.json
```

**Do not wait for approval to start building.** Layer 1 has a second implementation behind the same contract:

```bash
python scripts/make_demo_data.py
# then in .env:
INGEST_BACKEND=fixture
DEMO_DATA_DIR=data/demo
```

Phases 3, 6, 7, 8 and 9 all work on synthetic imagery. Nothing downstream knows the difference, and switching to real data later is one line in `.env`. See §4.5b of the backend spec.

---

## 2. Twilio — SMS

**What it gives you.** SMS delivery to forest officers and community leaders. The trial tier covers the whole project.

**Steps**

1. Create a trial account at `twilio.com`.
2. From the console dashboard, copy the **Account SID** and **Auth Token**.
3. Claim a trial phone number — this becomes your sender.
4. Under **Verified Caller IDs**, verify every number that should receive an alert.

**Where the credentials go**

```
.env    TWILIO_ACCOUNT_SID
        TWILIO_AUTH_TOKEN
        TWILIO_FROM_NUMBER            your trial number, E.164 format
```

> **The one that catches people.** A trial account sends **only** to numbers you have explicitly verified, and Twilio prefixes every message with a trial notice. Verify the whole team's phones well before demo day — otherwise the code runs, logs success, and nobody receives anything.

---

## 3. Gmail app password — email

**What it gives you.** Email alerts over SMTP. Twilio's SMS product does not send email, so email goes through Gmail instead.

**Steps**

1. Enable **2-Step Verification** on the Google account. App passwords do not exist without it.
2. Go to Google Account → Security → **App passwords**.
3. Generate one for "Mail" and copy the 16 characters.
4. Use it as `SMTP_PASSWORD` — never the account's own password.

**Where the credentials go**

```
.env    SMTP_HOST=smtp.gmail.com
        SMTP_PORT=587
        SMTP_USER                     the Gmail address
        SMTP_PASSWORD                 the 16-character app password
        SMTP_FROM                     sender shown to recipients
```

> The app-passwords page is hidden until 2-Step Verification is on. If you cannot find it, that is why.

---

## 4. NASA Earthdata Login — Phase 10 only

**What it gives you.** Access to OPERA DIST-ALERT from the LP DAAC, used in Phase 10 to compare our detections against an independent near-real-time product.

**Steps**

1. Register at `urs.earthdata.nasa.gov`.
2. Confirm the email verification link.
3. Accept the LP DAAC data-use agreement on first download.

**Where the credentials go**

```
.env    EARTHDATA_USER
        EARTHDATA_PASSWORD
# or a ~/.netrc entry for urs.earthdata.nasa.gov
```

> Check first whether DIST-ALERT is mirrored as a Google Earth Engine asset. If it is, the service account already reaches it and you can skip this entirely.

---

## 5. Kaggle — optional

**What it gives you.** The Planet "Understanding the Amazon from Space" dataset — 40,000 labelled chips used to pretrain the U-Net encoder before training on Hasdeo data.

**Steps**

1. Create a Kaggle account.
2. Settings → API → **Create New Token**. This downloads `kaggle.json`.
3. Accept the rules of the competition. The download fails silently until you do.

**Where the credential goes**

```
%USERPROFILE%\.kaggle\kaggle.json
```

> Pretraining is a nice-to-have. If time is short, skip it and say so in the report. Tile-level tags are not segmentation masks anyway, and the spec only uses them to initialise the encoder.

---

## 6. Copernicus Data Space — optional, but useful while you wait

**What it gives you.** Real Sentinel-2 imagery over the PEKB block, downloaded by hand. Registration is instant, with no approval queue — so this is how you get genuine before/after imagery before Earth Engine clears.

**Steps**

1. Register at `dataspace.copernicus.eu`.
2. Open the Browser and navigate to the PEKB block at **22.838 N, 82.814 E**.
3. Download two low-cloud scenes roughly a year apart, from the November–February window.
4. Convert to the 4-band R/G/B/NIR layout and drop them into `DEMO_DATA_DIR`.

The fixture ingest backend reads them exactly as it reads synthetic files.

> This gives a real before/after demonstration in an afternoon. It does **not** replace Earth Engine — manual downloads cannot support a 5-day cadence or a 13-year backfill.

---

## Evaluated and rejected

Recorded so the decision does not get made twice.

### Google Maps Platform — not usable

Its Environment APIs are Air Quality, Pollen, Solar and Weather. No vegetation, no land cover, no near-infrared band, no NDVI. Google Maps Platform is a mapping, routing and places product — not an Earth-observation archive.

The confusion is worth naming: the Google product that *does* serve satellite data is **Google Earth Engine**, a separate service with separate credentials, and it is already the ingestion layer. The imagery need is met.

Not recommended as a basemap either: it needs a billing-enabled key, its terms restrict deriving from or analysing the imagery, and adding it would falsify the "100% free and open-source stack" claim in the submitted synopsis. OpenStreetMap and Esri World Imagery are already specified, cost nothing, and need no key.

### Render / Railway — dropped

The project runs on localhost only. No hosting account, no public URL, no deployment step. Cloud deployment is explicitly out of scope; nothing in the design blocks it later if it is ever wanted.

---

## Where every credential lands

One `.env` at the repository root. It is in `.gitignore` — never commit it, and never commit `secrets/`.

| Variable | From | Value |
|---|---|---|
| `GEE_SERVICE_ACCOUNT_EMAIL` | Earth Engine | service account address from the JSON key |
| `GEE_PROJECT` | Earth Engine | Cloud project id registered for Earth Engine |
| `GEE_KEY_FILE` | Earth Engine | `./secrets/gee-service-account.json` |
| `TWILIO_ACCOUNT_SID` | Twilio | console dashboard |
| `TWILIO_AUTH_TOKEN` | Twilio | console dashboard |
| `TWILIO_FROM_NUMBER` | Twilio | trial number, E.164 format |
| `SMTP_HOST` / `SMTP_PORT` | Gmail | `smtp.gmail.com` / `587` |
| `SMTP_USER` / `SMTP_PASSWORD` | Gmail | address, and the 16-character app password |
| `SMTP_FROM` | Gmail | sender shown to recipients |
| `EARTHDATA_USER` / `EARTHDATA_PASSWORD` | NASA | Phase 10 DIST-ALERT comparison only |
| `ADMIN_API_KEY` | you choose | any random string; guards the API's write routes |
| `NOTIFICATIONS_ENABLED` | you choose | keep `false` until Phase 7 — dry-run logs instead of sending |
| `INGEST_BACKEND` | you choose | `gee`, or `fixture` while waiting on approval |
| `DEMO_DATA_DIR` | you choose | `data/demo` |
| `ALLOW_SYNTHETIC` | you choose | must be `true` before alerts can be raised from synthetic imagery |

---

## One prerequisite that is not an account

Before Phase 3, open `data/aoi/seed_aois.geojson` on a satellite basemap — drag it onto **geojson.io** and switch to satellite view — and confirm the PEKB mine pit sits inside the `hasdeo-pekb` box with forest on every side.

The coordinates were wrong once already: an earlier estimate missed the mine by about 14 km, which would have produced a pipeline that ran perfectly and detected nothing. Every hectare figure the project reports depends on this box. Two minutes, and it is a blocker for Phase 3. See §3.1 of the backend spec and risk R13.

---

## Order of operations

1. **Today** — start the Earth Engine signup (steps 1–4 at minimum, so the clock is running).
2. **Today** — verify the bounding box at geojson.io. Two minutes, no account needed.
3. **While waiting** — generate synthetic data, set `INGEST_BACKEND=fixture`, and build Phases 0, 1, 3.
4. **When GEE clears** — finish steps 5–7, do Phase 2, flip `INGEST_BACKEND=gee`.
5. **Before Phase 7** — Twilio and the Gmail app password. Verify the team's phone numbers.
6. **Before Phase 10** — NASA Earthdata, if DIST-ALERT is not available through GEE.
