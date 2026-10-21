from pathlib import Path

from deforestwatch.config import Settings


def test_settings_have_safe_defaults(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("INGEST_BACKEND", raising=False)
    settings = Settings(_env_file=None)
    assert settings.ingest_backend == "gee"
    assert settings.database_url.startswith("postgresql+")
    assert settings.gee_key_file == Path("secrets/gee-service-account.json")
