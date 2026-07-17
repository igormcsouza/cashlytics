"""Pure helpers for projecting a recurring expense onto a given month.

Kept dependency-free (no FastAPI/boto3 imports) so it is trivial to unit test
and reuse from both ``services.py`` and, if ever needed, a background job.
"""

import calendar
import re

MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def is_valid_month(month: str) -> bool:
    """Return True if ``month`` is a well-formed ``YYYY-MM`` string.

    Requires the month component to be a real calendar month (01-12) — not
    just two digits — since callers (``project_deadline`` via
    ``calendar.monthrange``) raise on an out-of-range month, and this is the
    only validation standing between a bad query param and an unhandled
    500 (e.g. ``month=2026-13``).
    """
    return bool(MONTH_RE.match(month))


def home_month(deadline: str) -> str:
    """The ``YYYY-MM`` month an expense's own ``deadline`` falls in."""
    return deadline[:7]


def project_deadline(deadline: str, month: str) -> str:
    """Project a recurring expense's day-of-month onto ``month``.

    The day-of-month is preserved, clamped to the last valid day of the
    target month (e.g. the 31st projected onto February becomes the 28th/29th).
    """
    year, mon = (int(part) for part in month.split("-"))
    day = min(int(deadline[8:10]), calendar.monthrange(year, mon)[1])
    return f"{year:04d}-{mon:02d}-{day:02d}"


def month_status_id(expense_id: str, month: str) -> str:
    """Composite partition key for a per-month paid/due status row."""
    return f"{expense_id}#{month}"
