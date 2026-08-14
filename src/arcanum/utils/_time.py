import re
from datetime import UTC, datetime, timedelta

from arcanum.typing import TimezoneT


def get_timezone(*, utc: bool = False) -> TimezoneT:
    """Return the local timezone, defaulting to UTC if forced or if the local timezone is unable to be detected.

    Parameters
    ----------
    utc : bool, optional
        If `True`, force the returned timezone to be UTC, by default False

    Returns
    -------
    TimezoneT
        The datetime-aware/non-naive local or UTC timezone.
        This is a union of types `datetime.timezone` and `datetime.tzinfo`.
    """

    if utc is True:
        return UTC

    _tzinfo = datetime.now().astimezone().tzinfo
    return _tzinfo if (_tzinfo is not None) else UTC


def to_iso_time(dt: datetime | None = None, *, timezone: TimezoneT | None = None) -> str:
    """Convert a `datetime` object to ISO 8601 formatted string.

    Parameters
    ----------
    dt : datetime, optional
        `datetime` object to be formatted. Defaults to current time if `None`
    timezone : TimezoneT, optional
        Timezone to be used. Defaults to UTC if `None`

    Returns
    -------
    str
        ISO 8601 formatted date/time string with microsecond precision.
    """
    if dt is None:
        dt = datetime.now(timezone if timezone is not None else UTC)
    elif timezone is not None and dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt.isoformat()


def from_iso_time(iso_str: str, *, timezone: TimezoneT | None = None) -> datetime:
    """Parse ISO 8601 formatted string into datetime object.

    Parameters
    ----------
    iso_str : str
        ISO 8601 formatted datetime string.
    timezone : TimezoneT, optional
        Timezone to be used if string has no timezone information.

    Returns
    -------
    datetime
        `datetime` object parsed from ISO string.
    """
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None and timezone is not None:
        dt = dt.replace(tzinfo=timezone)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def to_unix_time(dt: datetime | None = None) -> float:
    """Convert `datetime` to Unix timestamp (seconds since epoch).

    Parameters
    ----------
    dt : datetime, optional
        `datetime` object to be converted. Defaults to current time if `None`.

    Returns
    -------
    float
        Unix timestamp in seconds with microsecond precision.
    """
    if dt is None:
        dt = datetime.now(UTC)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt.timestamp()


def from_unix_time(timestamp: float, *, timezone: TimezoneT | None = None) -> datetime:
    """Convert Unix timestamp to `datetime` object.

    Parameters
    ----------
    timestamp : float
        Unix timestamp in seconds.
    timezone : TimezoneT, optional
        Timezone for resulting datetime, defaults to UTC if `None`.

    Returns
    -------
    datetime
        `datetime` object corresponding to Unix timestamp.
    """
    dt = datetime.fromtimestamp(timestamp, UTC)
    if timezone is not None and timezone is not UTC:
        dt = dt.astimezone(timezone)
    return dt


def get_time(*, timezone: TimezoneT | None = None) -> datetime:
    """Get current datetime with specified timezone.

    Parameters
    ----------
    timezone : TimezoneT, optional
        Timezone to be used, defaults to UTC if `None`.

    Returns
    -------
    datetime
        Current datetime with specified timezone.
    """
    return datetime.now(timezone if timezone is not None else UTC)


def is_older_than(dt: datetime, duration: timedelta | float) -> bool:
    """Check if datetime is older than specified duration from current time.

    Parameters
    ----------
    dt : datetime
        `datetime` to be checked.
    duration : timedelta | int | float
        Duration against which to compare, either as a `datetime.timedelta` object or `float` seconds.

    Returns
    -------
    bool
        `True` if datetime is older than specified duration, `False` otherwise.
    """

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    if isinstance(duration, (int, float)):
        duration = timedelta(seconds=duration)

    return (get_time() - dt) > duration


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string.

    Parameters
    ----------
    seconds : int | float
        Duration in seconds.

    Returns
    -------
    str
        Human-readable duration string, formatted as `'Xd Xh Xm Xs'`.
    """

    result = []
    remainder = int(seconds)
    intervals = [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]

    for unit, count in intervals:
        value, remainder = divmod(remainder, count)
        if value > 0:
            result.append(f'{value}{unit}')

    return ' '.join(result) if result else '0s'


def parse_duration(duration_str: str) -> float:
    """Parse human-readable duration string into seconds.

    Parameters
    ----------
    duration_str : str
        Duration string (e.g., `'1d 2h 3m 4s'` or `'1h30m'`).

    Returns
    -------
    float
        Total duration in seconds.
    """

    total_seconds = 0.0
    mappings = {'d': 86400, 'h': 3600, 'm': 60, 's': 1}
    parts = re.findall(r'(\d+\.?\d*)([dhms])', duration_str)

    for value, unit in parts:
        total_seconds += float(value) * mappings[unit]

    return total_seconds
