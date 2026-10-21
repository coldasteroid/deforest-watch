"""Persist one completed pipeline execution into the operational database."""

from __future__ import annotations

from datetime import datetime, timezone

from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape
from sqlalchemy.orm import Session

from ..alert.dedupe import overlaps
from ..alert.notify import publish_alert_created
from ..db.models import Alert, AlertStatus, AlertTier, Detection, Run, RunStatus
from .run import PipelineExecution


def persist_execution(session: Session, run: Run, execution: PipelineExecution) -> dict:
    result = execution.detection
    now = datetime.now(timezone.utc)
    run.status = RunStatus.succeeded
    run.model_version = result.model_version
    run.chips_total = result.chips_total
    run.chips_gated_in = result.chips_gated_in
    run.detections_count = len(result.detections)
    run.alerts_created = 0
    run.alerts_deduped = 0
    run.overlay_path = str(result.overlay_png)
    run.loss_mask_path = str(result.loss_mask_tif)
    run.ndvi_diff_path = str(execution.preprocessed.ndvi_diff_tif)
    run.overlay_bounds = result.overlay_bounds
    run.finished_at = now
    run.duration_s = (now - (run.started_at or now)).total_seconds()

    existing = session.query(Alert).filter_by(aoi_id=run.aoi_id).all()
    created = 0
    deduped = 0
    created_alerts = []
    for item in result.detections:
        geometry = shape(item.geometry)
        centroid = geometry.centroid
        detection = Detection(
            run_id=run.id, aoi_id=run.aoi_id, geom=from_shape(geometry, srid=4326),
            area_ha=item.area_ha, confidence=item.confidence,
            ndvi_drop_mean=item.ndvi_drop_mean, centroid=from_shape(centroid, srid=4326),
            tier=AlertTier(item.tier), chip_ids=item.chip_ids,
        )
        session.add(detection)
        if item.tier == "watch":
            continue
        duplicate = next((alert for alert in existing
                          if overlaps(to_shape(alert.geom), geometry)), None)
        if duplicate is not None:
            duplicate.last_seen_run_id = run.id
            duplicate.times_seen += 1
            duplicate.confidence = max(duplicate.confidence, item.confidence)
            deduped += 1
            continue
        alert = Alert(
            aoi_id=run.aoi_id, first_run_id=run.id, last_seen_run_id=run.id,
            geom=from_shape(geometry, srid=4326), centroid=from_shape(centroid, srid=4326),
            area_ha=item.area_ha, confidence=item.confidence, ndvi_drop_mean=item.ndvi_drop_mean,
            tier=AlertTier(item.tier), status=AlertStatus.new, times_seen=1,
            detected_at=now,
        )
        session.add(alert)
        existing.append(alert)
        created_alerts.append(alert)
        created += 1
    if created_alerts:
        session.flush()
        for alert in created_alerts:
            publish_alert_created(session, str(alert.id), str(alert.aoi_id), alert.tier.value)
    run.alerts_created = created
    run.alerts_deduped = deduped
    return {"detections": len(result.detections), "alerts_created": created, "alerts_deduped": deduped}
