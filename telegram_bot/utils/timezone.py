import datetime as dt

MOSCOW_TZ = dt.timezone(dt.timedelta(hours=3))


def get_moscow_now() -> dt.datetime:
    """Return current datetime in Moscow timezone."""
    return dt.datetime.now(MOSCOW_TZ)


def get_moscow_today() -> dt.date:
    """Return today's date based on Moscow timezone."""
    return get_moscow_now().date()
