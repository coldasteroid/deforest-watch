from collections.abc import Generator

from fastapi import Header, HTTPException

from ..config import get_settings
from ..db.base import SessionLocal


def db_session() -> Generator:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def require_admin(x_api_key: str | None = Header(default=None)) -> None:
    configured = get_settings().admin_api_key
    if not configured or x_api_key != configured:
        raise HTTPException(status_code=401, detail="Missing or invalid API key")
