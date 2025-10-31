from datetime import UTC, datetime, timedelta


def get_yesterday_date() -> str:
    """Get yesterday's date as a string in YYYY-MM-DD format using UTC now."""
    yesterday = datetime.now(UTC).date() - timedelta(days=1)
    return yesterday.isoformat()


def get_today_date() -> str:
    """Get today's date as a string in YYYY-MM-DD format using UTC now."""
    return datetime.now(UTC).date().isoformat()
