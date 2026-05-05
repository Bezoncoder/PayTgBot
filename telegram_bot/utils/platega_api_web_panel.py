import logging
from datetime import datetime, date, time, timezone
from gettext import find
from pprint import pprint
from time import sleep
from typing import Optional, Any, List
from uuid import UUID

import requests
from pydantic import BaseModel

from settings.config import LOGIN_WEB_PLATEGA, PASSWORD_WEB_PLATEGA

logger = logging.getLogger(__name__)


class Transaction(BaseModel):
    recordId: str
    status: int
    paymentMethod: Optional[int] = None
    amount: float
    currencyCode: str
    merchantId: str
    merchantName: str
    usdtAmount: float
    createdAt: datetime
    payload: Optional[Any] = None
    description: str
    fee: Optional[float] = None
    usdtFee: float
    qrId: Optional[str] = None


class TransactionsResponse(BaseModel):
    transactions: List[Transaction]
    totalCount: int
    page: int
    pageSize: int
    totalPages: int


class BalanceResponse(BaseModel):
    amount: float
    currency: str
    id: UUID
    merchantId: UUID
    isMainAccount: bool
    isActive: bool
    frozenBalance: float


class StatsByCurrencyItem(BaseModel):
    currency: str
    turnover: float
    netProfit: float
    successTransactionsCount: int
    failedTransactionsCount: int
    chargebackTransactionsCount: int
    allTransactionsCount: int
    averageTransactionValue: float
    conversionRate: float
    chargebackAmount: float


class StatisticsByCurrencyResponse(BaseModel):
    statsByCurrency: List[StatsByCurrencyItem]


class PlategaWebClient:
    def __init__(self, login: str, password: str, token: str | None = None):
        self.login = login
        self.password = password
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://my.platega.io",
            "Referer": "https://my.platega.io/",
        })
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"
        else:
            self.token = self._get_authorisation()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        self.session.close()

    def _update_token(self, token: str):
        self.token = token
        self.session.headers["Authorization"] = f"Bearer {token}"

    def _get_authorisation(self) -> str:
        url = "https://app.platega.io/user/login"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Content-Type": "application/json",
            "Origin": "https://my.platega.io",
            "Referer": "https://my.platega.io/",
        }
        payload = {
            "Login": self.login,
            "Password": self.password,
        }

        response = self.session.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()
        token = data.get("accesToken")
        if not token:
            raise RuntimeError(f"Токен не найден в ответе: {data}")

        return token

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        logger.debug(f"Request: {method} {url} kwargs={kwargs}")

        # url = "https://app.platega.io/user/statistics/by-currency"
        # url = "https://app.platega.io/balance"
        # url = "https://app.platega.io/transaction/search"


        response = self.session.request(method, url, timeout=30, **kwargs)
        logger.debug(f"Response: {response.status_code} {response.text}")
        response.raise_for_status()
        return response

    def _request_with_retry(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        last_error = None

        for attempt in range(1, 4):
            try:
                return self._make_request(method, url, **kwargs)

            except requests.exceptions.HTTPError as e:
                last_error = e
                response = e.response

                if response is not None and response.status_code == 401:
                    logger.debug(f"401 Unauthorized on attempt {attempt}/3 for {url}. Refreshing token...")
                    try:
                        new_token = self._get_authorisation()
                        self._update_token(new_token)
                        continue
                    except Exception as refresh_error:
                        last_error = refresh_error
                        logger.debug(f"Token refresh failed on attempt {attempt}: {refresh_error}")
                        continue

                logger.debug(f"HTTP error on attempt {attempt}: {e}")
                break

            except Exception as e:
                last_error = e
                logger.debug(f"Unexpected error on attempt {attempt}: {e}")
                break

        logger.error(f"Request failed after 3 attempts: {last_error}")
        return None

    def get_transactions(self, page: int = 1, size: int = 10,
                         direction: int = 0) -> Optional[TransactionsResponse]:
        url = "https://app.platega.io/transaction/search"
        params = {
            "Page": page,
            "Size": size,
            "Direction": direction,
        }

        response = self._request_with_retry("GET", url, params=params)
        if response is None:
            return None

        return TransactionsResponse.model_validate(response.json())

    def get_balance(self, currencycode: str = "RUB") -> Optional[BalanceResponse]:
        url = "https://app.platega.io/balance"
        params = {"CurrencyCode": currencycode}

        response = self._request_with_retry("GET", url, params=params)
        if response is None:
            return None

        return BalanceResponse.model_validate(response.json())

    def get_statistics_by_currency(self, date_start: str,
                                   date_end: str,
                                   currency_code: str = "RUB") -> Optional[StatisticsByCurrencyResponse]:

        url = "https://app.platega.io/user/statistics/by-currency"

        start_date = date.fromisoformat(date_start)
        end_date = date.fromisoformat(date_end)

        dt_start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        dt_end = datetime.combine(end_date, time.max, tzinfo=timezone.utc)

        params = {
            "DateStart": dt_start.isoformat().replace("+00:00", "Z"),
            "DateEnd": dt_end.isoformat().replace("+00:00", "Z"),
            "CurrencyCode": currency_code,
            "timezoneId": "UTC",
        }

        response = self._request_with_retry("GET", url, params=params)
        if response is None:
            return None

        return StatisticsByCurrencyResponse.model_validate(response.json())




if __name__ == "__main__":

    platega_client = PlategaWebClient(login=LOGIN_WEB_PLATEGA,
                                      password=PASSWORD_WEB_PLATEGA)

    # transaction_list = platega_client.get_transactions()
    # # datetime
    # date_str = "2026-04-29"
    # # find_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    # find_date = datetime.now().date()
    #
    # for transaction in transaction_list.transactions:
    #     if transaction.createdAt.date() == find_date:
    #         print(transaction)
    #     print()

    # date_str = "2026-04-28"
    date_str = datetime.now().date().isoformat()
    print(date_str)
    print(str(date_str))
    # find_date = datetime.strptime(date_str, "YYYY-MM-DD")
    # date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # statistics = platega_client.get_statistics_by_currency(date_start=date_str, date_end=date_str)
    # print(statistics.statsByCurrency == [])

    #
    Balance = platega_client.get_balance()
    print(Balance)

    # Litva1 - beget - ssh root@155.212.228.65     %rx%ko%h8H&h

    date_start_stat = datetime.now().replace(day=1).date().isoformat()

    # month_to_date_stat = platega_client.get_statistics_by_currency(date_start=date_start_stat,
    #                                                                    date_end=today__date_iso)

    # if not month_to_date_stat.statsByCurrency:
    #     month_to_now_date = 0
    # else:
    #     month_to_now_date = statistics_today.statsByCurrency[0].turnover
    #
    # print()

