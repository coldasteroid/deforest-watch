"""Database notification helper for post-commit WebSocket fan-out."""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


def publish_alert_created(session: Session, alert_id: str, aoi_id: str, tier: str) -> bool:
    """Queue an alert-created event on PostgreSQL's ``dw_alerts`` channel.

    PostgreSQL delivers NOTIFY events only after the surrounding transaction
    commits. Other database backends or unavailable databases fail closed.
    """
    payload = json.dumps({"type": "alert.created", "payload": {"alert_id": str(alert_id), "aoi_id": str(aoi_id), "tier": tier}}, separators=(",", ":"))
    try:
        session.execute(text("SELECT pg_notify(:channel, :payload)"), {"channel": "dw_alerts", "payload": payload})
        return True
    except SQLAlchemyError:
        return False
