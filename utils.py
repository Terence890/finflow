"""
Utility helpers for PinkLedger (Finflow).

Focus:
- Robust, human-friendly parsing of monetary amounts into Decimal.
- Simple, deterministic date parsing into datetime.date.
- Small formatting helpers for display.

Design principles:
- Clear function names and docstrings.
- Defensive input handling and helpful error messages.
- No external dependencies so the module is portable.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Optional, Sequence, Tuple, Union

__all__ = [
    "parse_amount",
    "parse_amount_or_zero",
    "format_amount",
    "parse_date",
    "parse_date_or_today",
    "month_range",
]

Numeric = Union[int, float, Decimal]
AmountInput = Union[str, Numeric, None]
DateInput = Union[str, date, datetime, None]

# Regex to strip currency symbols and whitespace
_CURRENCY_RE = re.compile(r"[^\d\-\.\,()]+", flags=re.UNICODE)


def _normalize_numeric_string(s: str) -> str:
    """
    Convert a human-entered numeric string to a canonical form suitable for Decimal().

    - Removes currency symbols and letters.
    - Handles parentheses as negation: "(1,234.56)" -> "-1234.56"
    - Removes thousands separators (commas)
    - Leaves the decimal point as '.'.
    - Attempts to handle simple European notation like "1.234,56" -> "1234.56"

    Returns a string that Decimal() can parse, or raises ValueError.
    """
    if not isinstance(s, str):
        raise TypeError("_normalize_numeric_string expects a string")

    orig = s.strip()
    if orig == "":
        raise ValueError("empty numeric string")

    # Remove currency letters/symbols but keep digits, commas, dots, parentheses and minus
    cleaned = _CURRENCY_RE.sub("", orig)

    # Detect parentheses -> negative
    is_negative = False
    if "(" in cleaned and ")" in cleaned:
        is_negative = True
        cleaned = cleaned.replace("(", "").replace(")", "")

    cleaned = cleaned.strip()
    if cleaned == "":
        raise ValueError(f"no numeric content in '{orig}'")

    # If the string contains both '.' and ',' attempt to infer format:
    # - If '.' is before ',' (e.g. "1.234,56"), assume European: '.' thousands, ',' decimal
    # - Else assume standard: ',' thousands, '.' decimal (e.g. "1,234.56")
    if "." in cleaned and "," in cleaned:
        first_dot = cleaned.find(".")
        first_comma = cleaned.find(",")
        if first_dot < first_comma:
            # European style
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # US style but with both present (rare) -> remove commas
            cleaned = cleaned.replace(",", "")
    else:
        # Only commas or only dots
        # If there are commas and no dots, remove commas (they're thousands separators)
        if "," in cleaned and "." not in cleaned:
            cleaned = cleaned.replace(",", "")
        # If only dots are present, keep as-is (decimal point)

    # Trim any remaining stray characters
    cleaned = cleaned.strip()
    if cleaned in {"", ".", "-"}:
        raise ValueError(f"cannot parse numeric value from '{orig}'")

    if is_negative and not cleaned.startswith("-"):
        cleaned = "-" + cleaned

    return cleaned


def parse_amount(value: AmountInput) -> Decimal:
    """
    Parse a user-provided amount into Decimal.

    Accepts strings like:
      "$1,234.56", "1.234,56" (European), "(1234.56)", "-1234.56", "1234"

    Accepts int/float/Decimal as well.

    Raises:
      - TypeError if the type is not supported
      - ValueError if parsing fails

    Example:
      parse_amount("$1,234.50") -> Decimal('1234.50')
      parse_amount("(1,000)") -> Decimal('-1000')
    """
    if value is None:
        raise ValueError("amount is None")

    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"))

    if isinstance(value, (int,)):
        return Decimal(value).quantize(Decimal("0.01"))

    if isinstance(value, float):
        # Convert via string to avoid binary float issues
        try:
            return Decimal(str(value)).quantize(Decimal("0.01"))
        except InvalidOperation as e:
            raise ValueError(f"invalid float amount: {value}") from e

    if isinstance(value, str):
        s = value.strip()
        if s == "":
            raise ValueError("empty amount string")
        cleaned = _normalize_numeric_string(s)
        try:
            dec = Decimal(cleaned)
            # Round to 2 decimal places (common for currencies)
            return dec.quantize(Decimal("0.01"))
        except InvalidOperation as e:
            raise ValueError(f"could not convert '{value}' to Decimal") from e

    raise TypeError(f"unsupported amount type: {type(value).__name__}")


def parse_amount_or_zero(value: AmountInput) -> Decimal:
    """
    Convenience wrapper: attempts to parse amount, returns Decimal('0.00') on falsy/invalid input.

    Use this when you want a safe fallback instead of handling exceptions.
    """
    try:
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return Decimal("0.00")
        return parse_amount(value)
    except (ValueError, TypeError):
        return Decimal("0.00")


def format_amount(
    amount: Union[Decimal, Numeric], currency: str = "", thousands_sep: str = ","
) -> str:
    """
    Format a Decimal or numeric value into a human-friendly string.

    - By default does not add a currency symbol. Pass e.g. '₱' or '$' for display.
    - Uses comma as thousands separator and dot as decimal separator.
    - Ensures two decimal places.

    Example:
      format_amount(Decimal('1234.5'), '$') -> '$1,234.50'
    """
    if not isinstance(amount, Decimal):
        try:
            amount = Decimal(str(amount))
        except Exception:
            raise TypeError("amount must be numeric or Decimal")

    sign = "-" if amount < 0 else ""
    amt = abs(amount).quantize(Decimal("0.01"))
    # Split into integer and fractional parts
    int_part, frac_part = divmod(amt, 1)
    int_part = int(int_part)
    frac_str = f"{frac_part:.2f}"[2:]  # get fractional digits

    # Format integer with thousands separator
    int_str = f"{int_part:,}".replace(",", thousands_sep)
    return f"{sign}{currency}{int_str}.{frac_str}"


# Common date formats to try in order
_COMMON_DATE_FORMATS: Sequence[str] = (
    "%Y-%m-%d",  # ISO
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
    "%d %b %Y",  # 01 Jan 2022
    "%d %B %Y",  # 01 January 2022
    "%b %d, %Y",  # Jan 1, 2022
    "%B %d, %Y",  # January 1, 2022
)


def parse_date(value: DateInput, try_formats: Optional[Sequence[str]] = None) -> date:
    """
    Parse a value into a datetime.date.

    Accepts:
      - date or datetime -> returns the date portion
      - ISO-like / common human formats as strings

    If parsing fails, raises ValueError.

    Examples:
      parse_date("2023-02-15") -> date(2023,2,15)
      parse_date(datetime.utcnow()) -> today's date
    """
    if value is None:
        raise ValueError("date value is None")

    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    if isinstance(value, datetime):
        return value.date()

    if not isinstance(value, str):
        raise TypeError("parse_date expects a string, date or datetime")

    s = value.strip()
    if s == "":
        raise ValueError("empty date string")

    # Try python's fromisoformat first (fast for ISO)
    try:
        # datetime.fromisoformat can parse YYYY-MM-DD and some variants
        dt = datetime.fromisoformat(s)
        return dt.date()
    except Exception:
        # Not ISO or not precise enough - fall back to known formats
        pass

    formats = list(try_formats or _COMMON_DATE_FORMATS)
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue

    # As a last attempt, handle simple numeric timestamps (seconds since epoch)
    if s.isdigit():
        try:
            ts = int(s)
            return datetime.utcfromtimestamp(ts).date()
        except Exception:
            pass

    # Failed all attempts
    raise ValueError(f"unrecognized date format: '{value}'")


def parse_date_or_today(value: DateInput) -> date:
    """
    Parse date and fall back to today's date if parsing fails or input is falsy.
    """
    try:
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return date.today()
        return parse_date(value)
    except Exception:
        return date.today()


def month_range(month: str) -> Tuple[date, date]:
    """
    Given a month string 'YYYY-MM' or 'YYYY/MM', return (start_date, end_date)
    where end_date is inclusive.

    Example:
      month_range('2023-02') -> (date(2023,2,1), date(2023,2,28))
    """
    if not isinstance(month, str):
        raise TypeError("month must be a string in 'YYYY-MM' format")

    m = month.strip().replace("/", "-")
    parts = m.split("-")
    if len(parts) < 2:
        raise ValueError("month must be 'YYYY-MM'")

    year = int(parts[0])
    mon = int(parts[1])

    start = date(year, mon, 1)
    # Compute next month start then subtract one day
    if mon == 12:
        next_start = date(year + 1, 1, 1)
    else:
        next_start = date(year, mon + 1, 1)
    end_inclusive = next_start - timedelta(days=1)
    return start, end_inclusive


# Example quick internal tests when module run directly
if __name__ == "__main__":  # pragma: no cover - quick manual checks
    samples = [
        "$1,234.56",
        "1.234,56",  # european
        "(1,234.56)",
        "-1234.5",
        "  1000 ",
    ]
    for s in samples:
        print(s, "->", parse_amount_or_zero(s))

    dates = ["2023-02-15", "15/02/2023", "Feb 1, 2023", "1672531200"]
    for d in dates:
        print(d, "->", parse_date_or_today(d))
