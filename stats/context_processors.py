from django.conf import settings

from .secrets import riot_api_key_status


def application_settings(_request):
    status = riot_api_key_status()
    return {
        "dps_threshold": settings.DPS_THREAT_THRESHOLD,
        "riot_configured": status.configured,
    }
