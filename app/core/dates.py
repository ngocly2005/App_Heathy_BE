"""One business timezone for teacher/student clients and server defaults."""
from datetime import datetime
from zoneinfo import ZoneInfo
from app.core.config import get_settings


def today():
    return datetime.now(ZoneInfo(get_settings().time_zone)).date()
