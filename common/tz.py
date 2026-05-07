"""School wall-clock timezone (IANA). Stored datetimes remain UTC-aware via ``USE_TZ``."""

from __future__ import annotations

from zoneinfo import ZoneInfo

from django.conf import settings


def school_timezone() -> ZoneInfo:
    """IANA zone used when combining date + time into an instant (e.g. due_at)."""
    return ZoneInfo(str(settings.TIME_ZONE))
