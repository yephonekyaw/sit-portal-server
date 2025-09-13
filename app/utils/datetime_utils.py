from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def utc_now() -> datetime:
    """
    Get current UTC datetime as a timezone-aware datetime.

    Returns:
        datetime: Current UTC datetime with timezone info
    """
    return datetime.now(timezone.utc)


def naive_utc_now() -> datetime:
    """
    Get current UTC datetime as a naive datetime (no timezone info).
    This is useful for storing in DATETIME2 fields which don't store timezone info.

    Returns:
        datetime: Current UTC datetime without timezone info
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_utc(dt: datetime) -> datetime:
    """
    Convert a datetime object to UTC timezone-aware datetime.

    Args:
        dt: Datetime object to convert

    Returns:
        datetime: UTC timezone-aware datetime
    """
    if dt.tzinfo is None:
        # Assume naive datetime is in UTC
        return dt.replace(tzinfo=timezone.utc)
    else:
        # Convert to UTC
        return dt.astimezone(timezone.utc)


def to_naive_utc(dt: datetime) -> datetime:
    """
    Convert a datetime object to naive UTC (no timezone info).
    This is useful for storing in DATETIME2 fields which don't store timezone info.

    Args:
        dt: Datetime object to convert

    Returns:
        datetime: Naive UTC datetime
    """
    if dt.tzinfo is None:
        # Already naive, assume it's UTC
        return dt
    else:
        # Convert to UTC and remove timezone info
        utc_dt = dt.astimezone(timezone.utc)
        return utc_dt.replace(tzinfo=None)


def from_naive_utc(dt: datetime, zone: ZoneInfo = ZoneInfo("UTC")) -> datetime:
    """
    Convert a naive UTC datetime (no timezone info) to a timezone-aware datetime.

    Args:
        dt: Naive UTC datetime to convert
        zone: Timezone to use for the conversion (default: UTC)

    Returns:
        datetime: Timezone-aware datetime
    """
    if dt.tzinfo is not None:
        raise ValueError("Input datetime must be naive (no timezone info)")
    return dt.replace(tzinfo=timezone.utc).astimezone(zone)


def from_bangkok_to_naive_utc(dt: datetime) -> datetime:
    """
    Convert a Bangkok timezone-aware datetime to naive UTC (no timezone info).

    Args:
        dt: Bangkok timezone-aware datetime to convert
    Returns:
        datetime: Naive UTC datetime
    """
    bangkok_tz = ZoneInfo("Asia/Bangkok")
    dt = dt.replace(tzinfo=bangkok_tz)
    return to_naive_utc(dt)


def format_utc_datetime(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a UTC datetime object into a string.

    Args:
        dt: Datetime object to format
        fmt: Format string (default: "%Y-%m-%d %H:%M:%S")

    Returns:
        str: Formatted datetime string
    """
    utc_dt = utc_now()
    return utc_dt.strftime(fmt)
