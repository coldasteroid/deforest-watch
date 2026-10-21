from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..config import get_settings
from ..contracts import DetectRequest, DetectionResult, FetchRequest, PreprocessRequest, RunSummary
from ..detect.baseline_ndvi import detect as baseline_detect
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
        detect_request.model_path = model_path
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
