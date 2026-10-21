from .fixture import fetch_fixture


def fetch_imagery(req):
    """Fetch imagery through the configured backend.

    The fixture backend is intentionally deterministic and is used until the
    Earth Engine account and PostGIS environment pass their live gates.
    """
    from ..config import get_settings

    if get_settings().ingest_backend == "fixture":
        return fetch_fixture(req)
    from .gee_client import fetch_gee

    return fetch_gee(req)


__all__ = ["fetch_imagery"]
