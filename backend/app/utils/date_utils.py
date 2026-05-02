from datetime import datetime, timedelta


def get_now_str() -> str:
    """Returns the current UTC time as an ISO 8601 string."""
    return datetime.utcnow().isoformat()


def days_ago(n: int) -> datetime:
    """Returns the datetime N days before now (UTC)."""
    return datetime.utcnow() - timedelta(days=n)


def to_unix_timestamp(dt: datetime) -> int:
    """Converts a datetime object to a UNIX timestamp (integer seconds)."""
    return int(dt.timestamp())


def parse_newsapi_datetime(dt_str: str) -> datetime:
    """
    Parses a NewsAPI publishedAt string (e.g. '2024-01-15T12:00:00Z')
    into a naive UTC datetime. Falls back to utcnow() on failure.
    """
    if not dt_str:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, AttributeError):
        return datetime.utcnow()


def parse_finnhub_timestamp(ts: int) -> datetime:
    """Converts a Finnhub UNIX timestamp (int) to a Python datetime."""
    try:
        return datetime.fromtimestamp(int(ts))
    except (ValueError, OSError, OverflowError, TypeError):
        return datetime.utcnow()
