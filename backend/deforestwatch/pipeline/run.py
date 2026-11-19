from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..config import get_settings
from ..contracts import DetectRequest, DetectionResult, FetchRequest, PreprocessRequest, RunSummary
from ..detect.baseline_ndvi import detect as baseline_detect
from ..detect.runner import checkpoint_threshold
from ..ingest import fetch_imagery
from ..preprocess.run import preprocess


@dataclass
class PipelineRequest:
    fetch: FetchRequest
    aoi_slug: str | None = None
    model_path: Path | None = None


@dataclass
class PipelineExecution:
    fetched: object
    preprocessed: object
    detection: DetectionResult


def execute_pipeline(request: PipelineRequest) -> PipelineExecution:
    fetched = fetch_imagery(request.fetch)
    pre = preprocess(PreprocessRequest(run_id=request.fetch.run_id, fetch=fetched, aoi_slug=request.aoi_slug))
    model_path = request.model_path or get_settings().model_path
    detect_request = DetectRequest(run_id=request.fetch.run_id, pre=pre)
    if model_path.is_file():
        # Apply the checkpoint at the operating point it was selected at. The
        # scheduled path used to leave prob_threshold at the contract default
        # of 0.5 while the checkpoint records 0.99, so every alert the worker
        # raised came from a threshold the model was never chosen for. `dw
        # detect` already did this; the worker did not.
        update: dict = {"model_path": model_path}
        stored = checkpoint_threshold(model_path)
        if stored is not None:
            update["prob_threshold"] = stored
        detect_request = detect_request.model_copy(update=update)
    detection = baseline_detect(detect_request)
    return PipelineExecution(fetched=fetched, preprocessed=pre, detection=detection)


def run_pipeline(request: PipelineRequest) -> RunSummary:
    started = datetime.now(timezone.utc)
    try:
        execution = execute_pipeline(request)
        detection = execution.detection
        duration = (datetime.now(timezone.utc) - started).total_seconds()
        return RunSummary(run_id=request.fetch.run_id, status="succeeded", detections=len(detection.detections),
                          hectares_detected=sum(item.area_ha for item in detection.detections),
                          alerts_created=sum(item.tier in {"alert", "critical"} for item in detection.detections),
                          duration_s=duration)
    except Exception as exc:
        duration = (datetime.now(timezone.utc) - started).total_seconds()
        return RunSummary(run_id=request.fetch.run_id, status="failed", detections=0,
                          alerts_created=0, duration_s=duration, error=str(exc))
