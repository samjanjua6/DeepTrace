"""
Pakistani Bank Holiday and Date Sanity Calendar.
Sources: SBP Circular Letters + `holidays` library (country="PK").

Pakistan's current banking week: Monday–Friday working, Saturday–Sunday off.
(Prior to 2007, Pakistan used Thursday–Friday off. Set PK_WEEKEND_FRIDAY=true
 in env to use that legacy schedule for old statements.)
"""
import logging
import os
import re
from datetime import date, datetime
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

# env var: set to "true" for pre-2007 Thursday-Friday weekend
_PK_WEEKEND_FRIDAY = os.environ.get("PK_WEEKEND_FRIDAY", "false").lower() == "true"

# Supported date string formats (mirrors DATE_REGEX groups from stage_6_financial.py)
_DATE_PATTERNS = [
    # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    re.compile(r"^(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})$"),
    # DD/MM/YY or DD-MM-YY
    re.compile(r"^(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2})$"),
    # DD-Mon-YYYY or DD/Mon/YYYY  (e.g. 12-Apr-2024)
    re.compile(
        r"^(\d{1,2})[/\-\. ](Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[/\-\. ](\d{4})$",
        re.IGNORECASE,
    ),
    # DD-Mon-YY  (e.g. 12-Apr-24)
    re.compile(
        r"^(\d{1,2})[/\-\. ](Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[/\-\. ](\d{2})$",
        re.IGNORECASE,
    ),
    # DD Mon YYYY  (e.g. 11 Jun 2026)
    re.compile(
        r"^(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})$",
        re.IGNORECASE,
    ),
]

_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_transaction_date(date_str: str) -> Optional[date]:
    """
    Parse a date string captured by DATE_REGEX into a Python date.
    Supports:
        DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
        DD/MM/YY, DD-MM-YY
        DD-Mon-YYYY, DD/Mon/YYYY, DD Mon YYYY  (e.g. 12-Apr-2024, 11 Jun 2026)
        DD-Mon-YY  (e.g. 12-Apr-24)
    Returns None if the string cannot be parsed or represents an invalid calendar date.
    """
    if not date_str:
        return None
    raw = date_str.strip()

    for pattern in _DATE_PATTERNS:
        m = pattern.match(raw)
        if not m:
            continue
        g1, g2, g3 = m.group(1), m.group(2), m.group(3)
        try:
            day = int(g1)
            # Determine month
            if g2.isdigit():
                month = int(g2)
            else:
                month = _MONTH_MAP.get(g2.lower())
                if month is None:
                    continue
            # Determine year
            year = int(g3)
            if year < 100:
                # Two-digit year: 00–49 → 2000–2049, 50–99 → 1950–1999
                year = (2000 + year) if year < 50 else (1900 + year)
            return date(year, month, day)
        except (ValueError, TypeError):
            continue

    logger.debug("pk_calendar: Could not parse date string '%s'", date_str)
    return None


@lru_cache(maxsize=32)
def get_pk_holidays(year: int) -> frozenset:
    """
    Return a frozenset of Pakistani national public holidays for the given year.
    Falls back to an empty frozenset if the `holidays` package is not installed.
    """
    try:
        import holidays as _holidays  # lazy import to avoid hard dependency
        pk = _holidays.Pakistan(years=year)
        return frozenset(pk.keys())
    except ImportError:
        logger.warning("pk_calendar: 'holidays' package not installed — holiday detection disabled.")
        return frozenset()
    except Exception as exc:
        logger.warning("pk_calendar: Failed to load PK holidays for %d: %s", year, exc)
        return frozenset()


def is_bank_holiday(d: date) -> bool:
    """
    Return True if the date falls on a Pakistani banking non-working day:
      - Saturday or Sunday (current SBP schedule, post-2007)
      - OR Thursday or Friday when PK_WEEKEND_FRIDAY=true (pre-2007 legacy)
      - OR a national public holiday in the `holidays` library dataset.

    Does NOT cover SBP ad-hoc gazette notifications (those require a custom table).
    """
    if _PK_WEEKEND_FRIDAY:
        # Pre-2007: Thursday (3) + Friday (4)
        if d.weekday() in (3, 4):
            return True
    else:
        # Current: Saturday (5) + Sunday (6)
        if d.weekday() in (5, 6):
            return True

    pk_holidays = get_pk_holidays(d.year)
    return d in pk_holidays


def is_future_date(d: date, reference: Optional[date] = None) -> bool:
    """
    Return True if `d` is strictly after `reference`.
    `reference` defaults to today's date (UTC).
    """
    ref = reference if reference is not None else date.today()
    return d > ref


def is_gazetted_holiday(d: date) -> bool:
    """
    Return True only if the date is a gazetted Pakistani national public holiday
    (e.g. Independence Day, Pakistan Day, Eid) excluding regular weekends.
    """
    pk_holidays = get_pk_holidays(d.year)
    return d in pk_holidays

