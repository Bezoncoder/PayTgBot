from dateutil.relativedelta import relativedelta
import logging

from utils.timezone import get_moscow_now


# # Calculating the difference between two dates
# date1 = datetime(2022, 1, 15)
# date2 = datetime(2023, 3, 10)
# diff = relativedelta(date2, date1)
# print(f"Difference: {diff}")
# print(f"Years: {diff.years}, Months: {diff.months}, Days: {diff.days}")

def get_expire_time_sec(expire_data) -> int:

    logging.debug("Формируем дату окончания подписки:\nexpire_date = %s", expire_data)

    current_date = get_moscow_now()

    # Полная разница в днях + включаем сам expire_date (последний день доступен).
    expire_days = max((expire_data - current_date.date()).days + 1, 0)

    expire_time = expire_days * 60 * 60 * 24

    logging.info("expire_time = %s", expire_time)
    return expire_time
