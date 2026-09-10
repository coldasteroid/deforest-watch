# DeforestWatch backend

## Run locally

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn deforestwatch.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` to try the API. `POST /api/compare` accepts two same-sized RGB images or four-band satellite GeoTIFFs. For GeoTIFFs, bands are expected in `red, green, blue, nir` order; the API computes NDVI. RGB images use an excess-green index fallback.

Example with curl:

```powershell
curl.exe -X POST http://localhost:8000/api/compare -F before=@before.tif -F after=@after.tif -F threshold=0.2
```

The response includes a loss summary and GeoJSON polygons. The red overlay is available at the returned `overlay_url`.
