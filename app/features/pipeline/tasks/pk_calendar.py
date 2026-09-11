"""
Pakistani Bank Holiday and Date Sanity Calendar.
Sources: State Bank of Pakistan (SBP) Circular Letters + `holidays` library (country="PK").

Pakistan's current banking week: Monday–Friday working, Saturday–Sunday off.
(Prior to 2007, Pakistan used Thursday–Friday off. Set PK_WEEKEND_FRIDAY=true
 in env to use that legacy schedule for old statements.)
"""
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
import logging
import os
import re
from typing import Any, Optional

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

# ─────────────────────────────────────────────────────────────────────────────
# Built-in SBP Holiday & Bank Closing Dates (2020–2027)
# Ensures 100% deterministic precision offline or when 'holidays' pkg is absent.
# ─────────────────────────────────────────────────────────────────────────────
_SBP_FIXED_HOLIDAYS = {
    (2, 5): "Kashmir Solidarity Day",
    (3, 23): "Pakistan Day",
    (5, 1): "Labour Day",
    (8, 14): "Independence Day",
    (9, 6): "Defence of Pakistan Day",
    (11, 9): "Iqbal Day",
    (12, 25): "Quaid-e-Azam Day / Christmas",
}

# SBP Annual Accounts Closing Days: Banks are strictly closed for public dealings / OTC
_SBP_BANK_CLOSING_DAYS = {
    (1, 1): "SBP Annual Accounts Closing",
    (7, 1): "SBP Half-Yearly Accounts Closing",
}

# SBP Gazetted Islamic Lunar Holidays (exact gazetted notification dates 2020–2027)
_SBP_LUNAR_GAZETTED_HOLIDAYS = {
    # 2020
    date(2020, 5, 24): "Eid-ul-Fitr", date(2020, 5, 25): "Eid-ul-Fitr", date(2020, 5, 26): "Eid-ul-Fitr",
    date(2020, 7, 31): "Eid-ul-Adha", date(2020, 8, 1): "Eid-ul-Adha", date(2020, 8, 2): "Eid-ul-Adha",
    date(2020, 8, 29): "Ashura (9 Muharram)", date(2020, 8, 30): "Ashura (10 Muharram)",
    date(2020, 10, 30): "Eid Milad-un-Nabi",
    # 2021
    date(2021, 5, 13): "Eid-ul-Fitr", date(2021, 5, 14): "Eid-ul-Fitr", date(2021, 5, 15): "Eid-ul-Fitr",
    date(2021, 7, 20): "Eid-ul-Adha", date(2021, 7, 21): "Eid-ul-Adha", date(2021, 7, 22): "Eid-ul-Adha",
    date(2021, 8, 18): "Ashura (9 Muharram)", date(2021, 8, 19): "Ashura (10 Muharram)",
    date(2021, 10, 19): "Eid Milad-un-Nabi",
    # 2022
    date(2022, 5, 2): "Eid-ul-Fitr", date(2022, 5, 3): "Eid-ul-Fitr", date(2022, 5, 4): "Eid-ul-Fitr", date(2022, 5, 5): "Eid-ul-Fitr",
    date(2022, 7, 10): "Eid-ul-Adha", date(2022, 7, 11): "Eid-ul-Adha", date(2022, 7, 12): "Eid-ul-Adha",
    date(2022, 8, 7): "Ashura (9 Muharram)", date(2022, 8, 8): "Ashura (10 Muharram)",
    date(2022, 10, 9): "Eid Milad-un-Nabi",
    # 2023
    date(2023, 4, 21): "Eid-ul-Fitr", date(2023, 4, 22): "Eid-ul-Fitr", date(2023, 4, 23): "Eid-ul-Fitr", date(2023, 4, 24): "Eid-ul-Fitr",
    date(2023, 6, 28): "Eid-ul-Adha", date(2023, 6, 29): "Eid-ul-Adha", date(2023, 6, 30): "Eid-ul-Adha", date(2023, 7, 1): "Eid-ul-Adha",
    date(2023, 7, 28): "Ashura (9 Muharram)", date(2023, 7, 29): "Ashura (10 Muharram)",
    date(2023, 9, 29): "Eid Milad-un-Nabi",
    # 2024
    date(2024, 4, 10): "Eid-ul-Fitr", date(2024, 4, 11): "Eid-ul-Fitr", date(2024, 4, 12): "Eid-ul-Fitr", date(2024, 4, 13): "Eid-ul-Fitr",
    date(2024, 6, 17): "Eid-ul-Adha", date(2024, 6, 18): "Eid-ul-Adha", date(2024, 6, 19): "Eid-ul-Adha",
    date(2024, 7, 16): "Ashura (9 Muharram)", date(2024, 7, 17): "Ashura (10 Muharram)",
    date(2024, 9, 17): "Eid Milad-un-Nabi",
    # 2025
    date(2025, 3, 30): "Eid-ul-Fitr", date(2025, 3, 31): "Eid-ul-Fitr", date(2025, 4, 1): "Eid-ul-Fitr", date(2025, 4, 2): "Eid-ul-Fitr",
    date(2025, 6, 6): "Eid-ul-Adha", date(2025, 6, 7): "Eid-ul-Adha", date(2025, 6, 8): "Eid-ul-Adha",
    date(2025, 7, 5): "Ashura (9 Muharram)", date(2025, 7, 6): "Ashura (10 Muharram)",
    date(2025, 9, 5): "Eid Milad-un-Nabi",
    # 2026
    date(2026, 3, 20): "Eid-ul-Fitr", date(2026, 3, 21): "Eid-ul-Fitr", date(2026, 3, 22): "Eid-ul-Fitr",
    date(2026, 5, 27): "Eid-ul-Adha", date(2026, 5, 28): "Eid-ul-Adha", date(2026, 5, 29): "Eid-ul-Adha",
    date(2026, 6, 24): "Ashura (9 Muharram)", date(2026, 6, 25): "Ashura (10 Muharram)",
    date(2026, 8, 25): "Eid Milad-un-Nabi",
    # 2027
    date(2027, 3, 9): "Eid-ul-Fitr", date(2027, 3, 10): "Eid-ul-Fitr", date(2027, 3, 11): "Eid-ul-Fitr",
    date(2027, 5, 16): "Eid-ul-Adha", date(2027, 5, 17): "Eid-ul-Adha", date(2027, 5, 18): "Eid-ul-Adha",
    date(2027, 6, 14): "Ashura (9 Muharram)", date(2027, 6, 15): "Ashura (10 Muharram)",
    date(2027, 8, 14): "Eid Milad-un-Nabi",
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
    Combines built-in SBP gazetted dataset with the `holidays` library dataset.
    """
    holidays_set = set()

    # Built-in fixed solar holidays
    for (m, d) in _SBP_FIXED_HOLIDAYS:
        try:
            holidays_set.add(date(year, m, d))
        except ValueError:
            pass

    # Built-in lunar Islamic holidays for this year
    for dt in _SBP_LUNAR_GAZETTED_HOLIDAYS:
        if dt.year == year:
            holidays_set.add(dt)

    # Union with Python holidays package if installed
    try:
        import holidays as _holidays
        pk = _holidays.Pakistan(years=year)
        holidays_set.update(pk.keys())
    except ImportError:
        logger.debug("pk_calendar: 'holidays' package not installed — using built-in SBP dataset.")
    except Exception as exc:
        logger.debug("pk_calendar: Failed to load PK holidays for %d: %s", year, exc)

    return frozenset(holidays_set)


def is_sbp_bank_closing_day(d: date) -> bool:
    """
    Return True if the date is an SBP mandated Accounts Closing Bank Holiday (Jan 1 or July 1),
    on which all commercial bank branches are strictly closed for public dealings.
    """
    return (d.month, d.day) in _SBP_BANK_CLOSING_DAYS


def is_gazetted_holiday(d: date) -> bool:
    """
    Return True only if the date is a gazetted Pakistani national public holiday
    (e.g. Independence Day, Pakistan Day, Eid) excluding regular weekends.
    """
    if (d.month, d.day) in _SBP_FIXED_HOLIDAYS:
        return True
    if d in _SBP_LUNAR_GAZETTED_HOLIDAYS:
        return True
    pk_holidays = get_pk_holidays(d.year)
    return d in pk_holidays


def is_bank_holiday(d: date) -> bool:
    """
    Return True if the date falls on a Pakistani banking non-working day:
      - Saturday or Sunday (current SBP schedule, post-2007)
      - OR Thursday or Friday when PK_WEEKEND_FRIDAY=true (pre-2007 legacy)
      - OR SBP Annual Accounts Closing Days (1 Jan, 1 Jul)
      - OR a national public holiday in the SBP / holidays dataset.
    """
    if _PK_WEEKEND_FRIDAY:
        if d.weekday() in (3, 4):
            return True
    else:
        if d.weekday() in (5, 6):
            return True

    if is_sbp_bank_closing_day(d):
        return True

    return is_gazetted_holiday(d)


def is_future_date(d: date, reference: Optional[date] = None) -> bool:
    """
    Return True if `d` is strictly after `reference`.
    `reference` defaults to today's date (UTC).
    """
    ref = reference if reference is not None else date.today()
    return d > ref


class ChannelType:
    DIGITAL = "DIGITAL"
    OTC_CLEARING = "OTC_CLEARING"
    GENERIC = "GENERIC"


is_sbp_closing_day = is_sbp_bank_closing_day


def classify_transaction_channel(narration: str) -> str:
    """
    Classify transaction narration into channel types:
      - 'DIGITAL': Automated 24/7/365 electronic channels (Raast, ATM, IBFT, POS, Cards, Fees).
      - 'OTC_CLEARING': In-branch over-the-counter & clearing operations (Cheque, NIFT, Teller, Deposit Slip).
      - 'GENERIC': Unclassified narration.
    """
    if not narration:
        return ChannelType.GENERIC
    low = narration.lower()

    # In-branch Over-the-Counter & NIFT Clearing (Checked first to avoid 'ft' substring matching inside 'nift')
    if any(k in low for k in [
        "cheque", "chq", "clearing", "nift", "clg", "counter", "teller",
        "cash deposit", "cash withdrawal", "pay order", "banker's cheque",
        "bankers cheque", "demand draft", "branch", "over the counter", "otc",
    ]):
        return ChannelType.OTC_CLEARING

    # Digital 24/7 channels
    if any(k in low for k in [
        "raast", "atm", "ibft", "online", "pos", "card", "1link",
        "p2p", "digital", "interbank", "paypak",
        "visa", "mastercard", "fee", "tax", "wht", "fed", "sms",
        "profit", "withholding", "excise", "mobile banking", "internet banking",
    ]) or re.search(r"\bft\b|\bft[/\s-]", low):
        return ChannelType.DIGITAL

    return ChannelType.GENERIC


def evaluate_transaction_date(
    d: date,
    narration: str = "",
    reference_date: Optional[date] = None,
    statement_period_end: Optional[date] = None,
) -> Optional[dict[str, Any]]:
    """
    Perform rigorous chronological and SBP calendar sanity evaluation on a transaction date.
    Returns None if date is fully valid, or an anomaly dictionary with rule metadata.
    """
    # 1. Impossible Future Date Check
    # A transaction date is impossible if:
    #   a) It exceeds the statement period end / generation date, OR
    #   b) It exceeds the current calendar date (today).
    if statement_period_end and d > statement_period_end:
        return {
            "rule_id": "RULE_PK_FUTURE_DATE_TRANSACTION",
            "category": "DATE_SEQUENCE_VIOLATION",
            "severity": "CRITICAL",
            "risk_points": 35,
            "title": f"Impossible Future Date Transaction ({d.strftime('%d-%b-%Y')})",
            "description": (
                f"Transaction date '{d.strftime('%d-%b-%Y')}' occurs after the stated statement "
                f"period end date ({statement_period_end.strftime('%d-%b-%Y')}). Bank statements cannot "
                "record transactions occurring after their statement generation cutoff."
            ),
            "expected_value": f"<= {statement_period_end.strftime('%d-%b-%Y')}",
            "actual_value": d.strftime('%d-%b-%Y'),
            "discrepancy": f"{ (d - statement_period_end).days } days in future",
            "is_future": True,
            "channel": classify_transaction_channel(narration),
        }

    if is_future_date(d, reference=reference_date):
        ref = reference_date or date.today()
        return {
            "rule_id": "RULE_PK_FUTURE_DATE_TRANSACTION",
            "category": "DATE_SEQUENCE_VIOLATION",
            "severity": "CRITICAL",
            "risk_points": 35,
            "title": f"Impossible Future Date Transaction ({d.strftime('%d-%b-%Y')})",
            "description": (
                f"Transaction date '{d.strftime('%d-%b-%Y')}' is in the future relative to "
                f"current date ({ref.strftime('%d-%b-%Y')}). No legitimate bank can post a transaction "
                "to a future settlement date. This indicates chronological fabrication."
            ),
            "expected_value": f"<= {ref.strftime('%d-%b-%Y')}",
            "actual_value": d.strftime('%d-%b-%Y'),
            "discrepancy": f"{ (d - ref).days } days in future",
            "is_future": True,
            "channel": classify_transaction_channel(narration),
        }

    # 2. National Bank Holiday & SBP Closing Check
    channel = classify_transaction_channel(narration)
    _is_gazetted = is_gazetted_holiday(d)
    _is_bank_closing = is_sbp_bank_closing_day(d)

    holiday_name = None
    if (d.month, d.day) in _SBP_FIXED_HOLIDAYS:
        holiday_name = _SBP_FIXED_HOLIDAYS[(d.month, d.day)]
    elif (d.month, d.day) in _SBP_BANK_CLOSING_DAYS:
        holiday_name = _SBP_BANK_CLOSING_DAYS[(d.month, d.day)]
    elif d in _SBP_LUNAR_GAZETTED_HOLIDAYS:
        holiday_name = _SBP_LUNAR_GAZETTED_HOLIDAYS[d]

    if _is_bank_closing:
        # On Jan 1 and Jul 1, banks are officially closed for public transactions.
        # Electronic 24/7 channels continue, but OTC/cheque clearing cannot occur.
        if channel == ChannelType.OTC_CLEARING:
            return {
                "rule_id": "RULE_PK_HOLIDAY_TRANSACTION",
                "category": "DATE_SEQUENCE_VIOLATION",
                "severity": "CRITICAL",
                "risk_points": 35,
                "title": f"In-Branch Transaction on SBP Bank Closing Day ({d.strftime('%d-%b-%Y')})",
                "description": (
                    f"Transaction '{narration[:60]}' is dated '{d.strftime('%d-%b-%Y')}' ({holiday_name}). "
                    "Commercial bank branches and NIFT clearing are officially closed to the public on this SBP bank holiday. "
                    "Over-the-counter or clearing transactions cannot be settled on this date."
                ),
                "expected_value": "Banking Business Day",
                "actual_value": f"{holiday_name} (Banks Closed)",
                "discrepancy": "OTC Transaction on SBP Accounts Closing Day",
                "is_future": False,
                "channel": channel,
            }

    if _is_gazetted:
        # Gazetted national public holiday (Independence Day, Eid, Ashura, Pakistan Day)
        if channel == ChannelType.OTC_CLEARING:
            return {
                "rule_id": "RULE_PK_HOLIDAY_TRANSACTION",
                "category": "DATE_SEQUENCE_VIOLATION",
                "severity": "CRITICAL",
                "risk_points": 30,
                "title": f"Clearing/OTC Transaction on Gazetted Public Holiday ({d.strftime('%d-%b-%Y')})",
                "description": (
                    f"Transaction '{narration[:60]}' is recorded on '{d.strftime('%d-%b-%Y')}' ({holiday_name or 'National Holiday'}). "
                    "State Bank of Pakistan regulations mandate that all retail bank branches and NIFT clearing houses remain "
                    "closed on gazetted national public holidays."
                ),
                "expected_value": "Banking Business Day",
                "actual_value": f"{holiday_name or 'Gazetted Public Holiday'} (Closed)",
                "discrepancy": "Clearing/OTC Transaction on Gazetted Holiday",
                "is_future": False,
                "channel": channel,
            }
        elif channel == ChannelType.GENERIC:
            return {
                "rule_id": "RULE_PK_HOLIDAY_TRANSACTION",
                "category": "DATE_SEQUENCE_VIOLATION",
                "severity": "HIGH",
                "risk_points": 25,
                "title": f"Transaction on Gazetted National Holiday ({d.strftime('%d-%b-%Y')})",
                "description": (
                    f"Transaction row carries date '{d.strftime('%d-%b-%Y')}', which is an official gazetted public holiday "
                    f"({holiday_name or 'National Holiday'}). Bank branches and clearing settlements are closed on this date."
                ),
                "expected_value": "Banking Business Day",
                "actual_value": f"{holiday_name or 'National Holiday'} (Closed)",
                "discrepancy": "Transaction on Gazetted Public Holiday",
                "is_future": False,
                "channel": channel,
            }
        # Automated 24/7 electronic transactions (Raast, ATM, IBFT) on gazetted holidays are standard;
        # they are not flagged to avoid false positives.

    # 3. Weekend Cheque Clearing / Branch Operation Check
    is_weekend = (d.weekday() in (5, 6)) if not _PK_WEEKEND_FRIDAY else (d.weekday() in (3, 4))
    if is_weekend and channel == ChannelType.OTC_CLEARING and d.weekday() == 6:  # Sunday
        return {
            "rule_id": "RULE_PK_WEEKEND_CLEARING_ANOMALY",
            "category": "DATE_SEQUENCE_VIOLATION",
            "severity": "MEDIUM",
            "risk_points": 15,
            "title": f"Cheque Clearing / Branch Transaction on Sunday ({d.strftime('%d-%b-%Y')})",
            "description": (
                f"Transaction '{narration[:60]}' indicates cheque clearing or branch counter operation "
                f"on Sunday ({d.strftime('%d-%b-%Y')}). NIFT interbank clearing does not operate on Sundays."
            ),
            "expected_value": "Weekday Clearing Settlement",
            "actual_value": "Sunday Settlement",
            "discrepancy": "Weekend Clearing Anomaly",
            "is_future": False,
            "channel": channel,
        }

    return None
