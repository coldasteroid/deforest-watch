def render_sms(aoi_name: str, area_ha: float, tier: str, dashboard_url: str) -> str:
    message = f"DeforestWatch {tier.upper()}: {area_ha:.1f} ha detected in {aoi_name}. Review: {dashboard_url}"
    return message[:160]


def render_email_subject(aoi_name: str, tier: str) -> str:
    return f"DeforestWatch {tier.upper()} — {aoi_name}"
