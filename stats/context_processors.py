from django.conf import settings

from .secrets import riot_api_key_status


def application_settings(_request):
    status = riot_api_key_status()
    return {
        "dps_threshold": settings.DPS_THREAT_THRESHOLD,
        "riot_configured": status.configured,
        "public_requests_enabled": settings.RIOT_PUBLIC_REQUESTS_ENABLED,
        "riot_match_count": settings.RIOT_MATCH_COUNT,
    }
