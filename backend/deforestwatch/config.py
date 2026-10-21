from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://dw:dw@localhost:5432/deforestwatch"
    data_dir: Path = Path("./data")
    models_dir: Path = Path("./models")
    model_path: Path = Path("./models/unet_v1.pt")
    detect_mode: str = "bitemporal"
    include_ndvi_diff_channel: bool = False
    ingest_backend: str = "gee"
    demo_data_dir: Path = Path("./data/demo")
    allow_synthetic: bool = False
    gee_service_account_email: str | None = None
    gee_key_file: Path = Path("./secrets/gee-service-account.json")
    gee_project: str | None = None
    max_scene_cloud_pct: float = 20.0
    s2_cloud_prob_max: float = 40.0
    current_window_days: int = 15
    baseline_months_back: int = 4
    use_seasonal_baseline: bool = True
    ndvi_drop_threshold: float = 0.20
    gate_min_pixels: int = 50
    forest_ndvi_min: float = 0.50
    forest_seasons_required: int = 2
    forest_buffer_m: float = 100.0
    chip_size: int = 256
    chip_overlap: int = 32
    epochs: int = 60
    prob_threshold: float = 0.5
    min_component_px: int = 10
    min_patch_ha: float = 1.0
    watch_patch_ha: float = 0.5
    critical_patch_ha: float = 10.0
    min_patch_ha_l8: float = 4.0
    fire_season_hold: bool = True
    fire_season_window: str = "03-01,05-31"
    dedupe_days: int = 90
    alert_on_watch_tier: bool = False
    carbon_stock_tc_per_ha: float = 60.0
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    notifications_enabled: bool = False
    frontend_url: str = "http://localhost:3000"
    admin_api_key: str | None = None
    earthdata_user: str | None = None
    earthdata_password: str | None = None
    worker_concurrency: int = 1
    retry_after_hours: int = 48
    chip_retention_days: int = 30
    download_tile_px: int = 2048
    max_direct_download_km2: float = 3000.0
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
