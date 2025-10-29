from datetime import UTC, datetime


def get_today_date() -> str:
    """Get today's date as a string in YYYY-MM-DD format using UTC now."""
    return datetime.now(UTC).date().isoformat()
