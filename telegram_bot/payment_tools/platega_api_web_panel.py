import logging
from datetime import datetime, date, time, timezone, timedelta
from gettext import find
from pprint import pprint
from time import sleep
from typing import Optional, Any, List
from uuid import UUID

import requests
from pydantic import BaseModel

# from settings.config import LOGIN_WEB_PLATEGA, PASSWORD_WEB_PLATEGA

logger = logging.getLogger(__name__)


class PlategaRateLimitError(RuntimeError):
    def __init__(
        self,
        retry_after_seconds: Optional[int] = None,
        trace_id: Optional[str] = None,
    ):
        self.retry_after_seconds = retry_after_seconds
        self.trace_id = trace_id

        message = "Platega временно ограничила количество запросов"
        if retry_after_seconds is not None:
            message += f". Повторите через {retry_after_seconds} сек."
        if trace_id:
            message += f" traceId={trace_id}"

        super().__init__(message)


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
        self.login_blocked_until: Optional[datetime] = None

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64; rv:154.0) "
                "Gecko/20100101 Firefox/154.0"
            ),
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://my.platega.io",
            "Referer": "https://my.platega.io/",
            "X-Merchant-Portal-CSRF": "1",
        })

        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"
        else:
            token = self._get_authorisation()
            if token:
                self._update_token(token)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        self.session.close()

    def _update_token(self, token: str):
        self.token = token
        self.session.headers["Authorization"] = f"Bearer {token}"

    @staticmethod
    def _get_retry_after_seconds(response: requests.Response) -> Optional[int]:
        try:
            payload = response.json()
        except ValueError:
            return None

        for item in payload.get("data", []):
            if item.get("key") == "retryAfterSeconds":
                try:
                    return int(item.get("message"))
                except (TypeError, ValueError):
                    return None

        return None

    @staticmethod
    def _get_trace_id(response: requests.Response) -> Optional[str]:
        try:
            payload = response.json()
        except ValueError:
            return None

        trace_id = payload.get("traceId")
        return str(trace_id) if trace_id else None

    def _get_authorisation(self) -> Optional[str]:
        now = datetime.now(timezone.utc)

        if (
            self.login_blocked_until is not None
            and now < self.login_blocked_until
        ):
            retry_after = max(
                1,
                int((self.login_blocked_until - now).total_seconds()),
            )
            raise PlategaRateLimitError(retry_after_seconds=retry_after)

        url = "https://app.platega.io/merchant-portal/v1/auth/login"

        headers = {
            "Content-Type": "application/json",
        }

        payload = {
            "login": self.login,
            "password": self.password,
        }

        response = self.session.post(
            url,
            headers=headers,
            json=payload,
            timeout=30,
        )

        if response.status_code == 429:
            retry_after = self._get_retry_after_seconds(response) or 120
            trace_id = self._get_trace_id(response)

            self.login_blocked_until = (
                datetime.now(timezone.utc)
                + timedelta(seconds=retry_after)
            )

            logger.warning(
                "Platega web login rate limited: retry_after=%s trace_id=%s",
                retry_after,
                trace_id,
            )

            raise PlategaRateLimitError(
                retry_after_seconds=retry_after,
                trace_id=trace_id,
            )

        if not response.ok:
            logger.error(
                "Platega web login failed: status=%s body=%r",
                response.status_code,
                response.text[:1000],
            )
            response.raise_for_status()

        if not response.content:
            logger.info(
                "Platega web login successful: "
                "no response body, cookies=%s",
                [cookie.name for cookie in self.session.cookies],
            )
            return None

        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError(
                "Platega login вернул не-JSON при успешном HTTP-ответе"
            ) from exc

        logger.debug(
            "Platega web login successful: response_keys=%s cookies=%s",
            list(data.keys()),
            [cookie.name for cookie in self.session.cookies],
        )

        return (
            data.get("accessToken")
            or data.get("accesToken")
            or data.get("token")
        )

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        logger.debug("Request: %s %s", method, url)

        response = self.session.request(method, url, timeout=30, **kwargs)

        logger.debug(
            "Response: status=%s url=%s body=%r",
            response.status_code,
            url,
            response.text[:1000],
        )

        if response.status_code == 429:
            retry_after = self._get_retry_after_seconds(response)
            trace_id = self._get_trace_id(response)

            logger.warning(
                "Platega request rate limited: url=%s retry_after=%s trace_id=%s",
                url,
                retry_after,
                trace_id,
            )

            raise PlategaRateLimitError(
                retry_after_seconds=retry_after,
                trace_id=trace_id,
            )

        response.raise_for_status()
        return response

    def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> Optional[requests.Response]:
        try:
            return self._make_request(method, url, **kwargs)

        except PlategaRateLimitError:
            # Никаких мгновенных повторов: Platega явно сообщила cooldown.
            raise

        except requests.exceptions.HTTPError as error:
            response = error.response

            if response is None or response.status_code != 401:
                logger.error("HTTP error for %s: %s", url, error)
                return None

            logger.warning(
                "Platega request returned 401 for %s. "
                "Refreshing web session once.",
                url,
            )

            try:
                token = self._get_authorisation()
                if token:
                    self._update_token(token)

                return self._make_request(method, url, **kwargs)

            except PlategaRateLimitError:
                raise

            except requests.exceptions.HTTPError as refresh_error:
                refresh_response = refresh_error.response

                logger.error(
                    "Platega web login refresh failed: status=%s body=%r",
                    (
                        refresh_response.status_code
                        if refresh_response is not None
                        else None
                    ),
                    (
                        refresh_response.text[:1000]
                        if refresh_response is not None
                        else None
                    ),
                )
                return None

            except Exception:
                logger.exception(
                    "Unexpected error while refreshing Platega web session"
                )
                return None

        except requests.exceptions.RequestException as error:
            logger.error("Request error for %s: %s", url, error)
            return None

        except Exception:
            logger.exception("Unexpected error while requesting %s", url)
            return None

    def get_transactions(
        self,
        page: int = 1,
        size: int = 10,
        direction: int = 0,
    ) -> Optional[TransactionsResponse]:
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

    # def get_balance(
    #     self,
    #     currencycode: str = "RUB",
    # ) -> Optional[BalanceResponse]:
    #     url = "https://app.platega.io/balance"
    #     params = {"CurrencyCode": currencycode}
    #
    #     response = self._request_with_retry("GET", url, params=params)
    #     if response is None:
    #         return None
    #
    #     return BalanceResponse.model_validate(response.json())

    def get_balance(
            self,
            currencycode: str = "RUB",
    ) -> Optional[BalanceResponse]:
        url = "https://app.platega.io/merchant-portal/v1/balances"

        response = self._request_with_retry(
            "GET",
            url,
            params={"currencyCode": currencycode},
        )

        if response is None:
            return None

        data = response.json()

        if isinstance(data, list):
            if not data:
                return None
            data = data[0]

        elif isinstance(data, dict) and isinstance(data.get("balances"), list):
            balances = data["balances"]

            if not balances:
                return None

            data = balances[0]

        return BalanceResponse.model_validate(data)

    def get_statistics_by_currency(
            self,
            date_start: str,
            date_end: str,
            currency_code: str = "RUB",
    ) -> Optional[StatisticsByCurrencyResponse]:
        url = (
            "https://app.platega.io/"
            "merchant-portal/v1/analytics/by-currency"
        )

        start_date = date.fromisoformat(date_start)
        end_date = date.fromisoformat(date_end) + timedelta(days=1)

        dt_start = datetime.combine(
            start_date,
            time.min,
            tzinfo=timezone.utc,
        )
        dt_end = datetime.combine(
            end_date,
            time.min,
            tzinfo=timezone.utc,
        )

        response = self._request_with_retry(
            "GET",
            url,
            params={
                "dateStart": (
                    dt_start.isoformat(timespec="milliseconds")
                    .replace("+00:00", "Z")
                ),
                "dateEnd": (
                    dt_end.isoformat(timespec="milliseconds")
                    .replace("+00:00", "Z")
                ),
                "currencyCode": currency_code,
                "timezoneId": "UTC",
            },
        )

        if response is None:
            return None

        return StatisticsByCurrencyResponse.model_validate(response.json())

if __name__ == "__main__":

    # platega_client = PlategaWebClient(login=LOGIN_WEB_PLATEGA,
    #                                   password=PASSWORD_WEB_PLATEGA)

    platega_client = PlategaWebClient(login="",
                                      password="")
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
    statistic = platega_client.get_statistics_by_currency(date_start=date_str, date_end=date_str)
    print(statistic)

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

# try:
#     balance = await asyncio.to_thread(platega_client.get_balance)
# except PlategaRateLimitError as exc:
#     logger.warning("Platega rate limit: %s", exc)
#
#     wait_text = (
#         f"примерно через {exc.retry_after_seconds} секунд"
#         if exc.retry_after_seconds
#         else "чуть позже"
#     )
#
#     await message.answer(
#         "Платёжный сервис временно ограничил частоту запросов. "
#         f"Повторите попытку {wait_text}."
#     )
#     return
# except Exception:
#     logger.exception("Ошибка при работе с Platega")
#     await message.answer(
#         "Не удалось выполнить платёжную операцию. Попробуйте позже."
#     )
#     return