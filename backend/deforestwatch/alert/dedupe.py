from dataclasses import dataclass
from datetime import datetime

from shapely.geometry.base import BaseGeometry


@dataclass
class AlertCandidate:
    geometry: BaseGeometry
    area_ha: float
    confidence: float
    ndvi_drop_mean: float
    detected_at: datetime
    tier: str


def tier_for(area_ha: float, min_patch_ha: float = 1.0, critical_patch_ha: float = 10.0, watch_patch_ha: float = 0.5) -> str:
    return "critical" if area_ha >= critical_patch_ha else ("alert" if area_ha >= min_patch_ha else "watch")


def overlaps(existing: BaseGeometry, candidate: BaseGeometry, minimum_fraction: float = 0.5) -> bool:
    if candidate.is_empty or existing.is_empty or not existing.intersects(candidate):
        return False
    return existing.intersection(candidate).area / max(candidate.area, 1e-12) > minimum_fraction


def dedupe(candidates: list[AlertCandidate], existing: list[AlertCandidate], dedupe_days: int = 90) -> tuple[list[AlertCandidate], int]:
    accepted, deduped = [], 0
    for candidate in candidates:
        duplicate = any((candidate.detected_at - old.detected_at).days <= dedupe_days and overlaps(old.geometry, candidate.geometry) for old in existing)
        if duplicate:
            deduped += 1
        else:
            accepted.append(candidate)
    return accepted, deduped
