# Presentation demo

## Focus

Present one solution only: timely deforestation detection from before/after
multispectral imagery.

## Compare demonstration

Open `http://127.0.0.1:3000/compare` and upload, in this order:

1. `data/demo/presentation/before_forest_synthetic.tif`
2. `data/demo/presentation/after_deforestation_synthetic.tif`

Use threshold `0.20` and pixel size `10 m`, then click **Detect deforestation**.
The result is a deliberately synthetic demonstration with two large clearing
patches. The PNG files in the same folder are preview-only.

## What is live and what is demo

- The `/api/compare` upload and comparison endpoint are live local backend
  code and produce the overlay and measurements from the uploaded files.
- Google Earth Engine authentication and real Sentinel-2 ingestion have been
  verified in the backend pipeline.
- The dashboard map, alerts, and latest-run cards use MSW fixture data while
  `VITE_ENABLE_MSW=true`; they are not live Earth Engine measurements.
- The synthetic TIFFs are presentation inputs, not real satellite imagery and
  must be described that way.

## Suggested explanation

"The system compares a current image with a historical image, computes the
vegetation-index drop, groups connected changed pixels into patches, and
returns their area and severity. In the operational version, the images are
retrieved from Google Earth Engine; this presentation uses a labelled synthetic
pair so the comparison is deterministic."
