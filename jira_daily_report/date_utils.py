from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class MonthWindow:
    start: date
    end: date


class MonthParseError(ValueError):
    pass


def parse_month(month_str: str) -> MonthWindow:
    try:
        year, month = month_str.split("-")
        year_i = int(year)
        month_i = int(month)
    except (ValueError, AttributeError) as exc:
        raise MonthParseError("Month must be in YYYY-MM format") from exc

    if not (1 <= month_i <= 12):
        raise MonthParseError("Month must be in YYYY-MM format")

    last_day = monthrange(year_i, month_i)[1]
    return MonthWindow(start=date(year_i, month_i, 1), end=date(year_i, month_i, last_day))


def as_local_date(dt_str: str, timezone: str) -> date:
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    return dt.astimezone(ZoneInfo(timezone)).date()
