from datetime import datetime
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")


def eastern_now():
    """Current time as a naive datetime in Eastern time (handles DST automatically)."""
    return datetime.now(EASTERN).replace(tzinfo=None)
