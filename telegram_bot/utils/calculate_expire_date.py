from datetime import date, datetime
from typing import Union
import logging


def get_expire_time_sec(expire_date: Union[str, date, datetime]) -> int:
    """
    Принимает дату/строку → возвращает timestamp миллисекунды для 3X-UI

    Args:
        expire_date: '2026-04-04', date(2026,4,4) или datetime

    Returns:
        int: 1772620800000 (13 цифр)
    """
    # Конвертируем в datetime
    if isinstance(expire_date, str):
        dt = datetime.strptime(expire_date, "%Y-%m-%d")
    elif isinstance(expire_date, date):
        dt = datetime.combine(expire_date, datetime.min.time())
    elif isinstance(expire_date, datetime):
        dt = expire_date
    else:
        raise ValueError(f"Неверный тип: {type(expire_date)}")

    # → timestamp миллисекунды
    return int(dt.timestamp() * 1000)


if __name__ == "__main__":
    expiretime = get_expire_time_sec(expire_date="2026-04-07")
    print(expiretime)