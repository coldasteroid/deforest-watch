# Nepal disaster-monitoring case study

## Scope boundary

DeforestWatch remains a Hasdeo Aranya forest-loss system. The Nepal case is a
separate satellite-change demonstration for disaster response. Landslide,
debris-flow, flood and avalanche scars from Nepal must never be counted as
Hasdeo deforestation or used as positive U-Net clearing labels.

## Event record

The tracked event is the 26 August 2026 Rasuwa / Bhote Koshi ice-rock avalanche
and cascading debris-flood event. NSET describes the upstream event as a major
ice-rock avalanche that transformed into a debris-flow and flood emergency;
WHO and ICIMOD describe the downstream flash-flood impacts and treat the exact
trigger as preliminary rather than fully settled. The initial marker is stored in
`data/validation/nepal_bhotekoshi_2026.geojson` as approximate only. The event
affected a downstream corridor rather than one compact polygon, so the final
validation geometry should be a set of verified source and impact polygons.
An inactive approximate envelope is also present in
`data/aoi/seed_aois.geojson` so the case can be displayed without entering
operational Hasdeo runs.

## Planned satellite demonstration

1. Verify the source and downstream impact polygons against official or
   independently documented satellite interpretation.
2. Fetch cloud-minimised pre-event imagery and the first usable post-event
   imagery around 26 August 2026.
3. Produce a separate debris/flood change overlay and affected-area estimate.
4. Report it as disaster-change detection, with cloud, shadow, water and
   mountain-topography limitations; do not compare it with Hasdeo hectares.

## Sources checked

- NSET, [Rasuwa Debris Flash Flood 2026](https://nset.org.np/disaster/rasuwa-flood/)
- WHO Nepal, [2026 Rasuwa flash floods](https://www.who.int/nepal/emergencies/2026-rasuwa-flash-floods)
- ICIMOD, [Rasuwa flash-flood advisory](https://www.icimod.org/press-release/major-flash-flood-sweeps-through-nepals-rasuwa-district-raising-fears-of-further-downstream-flooding/)
