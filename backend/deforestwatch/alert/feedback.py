"""Retraining-feedback export kept separate from database persistence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID


def append_feedback_export(path: str | Path, alert_id: UUID | str, verdict: str,
                           note: str | None, author: str, created_at: datetime | None = None) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "alert_id": str(alert_id), "verdict": verdict, "note": note,
        "author": author, "created_at": (created_at or datetime.now(timezone.utc)).isoformat(),
    }
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, separators=(",", ":")) + "\n")
