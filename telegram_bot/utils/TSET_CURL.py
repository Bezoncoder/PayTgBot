import asyncio
import logging
from datetime import datetime, date, time, timezone
from typing import Optional, Any, List
from uuid import UUID

import httpx
import requests
from pydantic import BaseModel

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


class PlategaAsyncClient:
    def __init__(self, login: str, password: str, token: str | None = None):
        self.login = login
        self.password = password
        self.token = token
        self.client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0",
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://my.platega.io",
                "Referer": "https://my.platega.io/",
            },
        )
        if self.token:
            self.client.headers["Authorization"] = f"Bearer {self.token}"
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client is not None:
            await self.client.aclose()
            self.client = None

    def _update_token(self, token: str):
        self.token = token
        if self.client is not None:
            self.client.headers["Authorization"] = f"Bearer {token}"

    async def get_authorisation(self) -> str:
        if self.client is None:
            raise RuntimeError("Client is not initialized. Use 'async with'.")

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

        response = await self.client.post(url, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        token = data.get("accesToken")
        if not token:
            raise RuntimeError(f"Токен не найден в ответе: {data}")

        return token

    async def _make_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        if self.client is None:
            raise RuntimeError("Client is not initialized. Use 'async with'.")

        logger.debug(f"Request: {method} {url} kwargs={kwargs}")
        response = await self.client.request(method, url, **kwargs)
        logger.debug(f"Response: {response.status_code} {response.text}")
        response.raise_for_status()
        return response

    async def _request_with_retry(self, method: str, url: str, **kwargs) -> Optional[httpx.Response]:
        last_error = None

        for attempt in range(1, 4):
            try:
                return await self._make_request(method, url, **kwargs)

            except httpx.HTTPStatusError as e:
                last_error = e

                if e.response.status_code == 401:
                    logger.debug(f"401 Unauthorized on attempt {attempt}/3 for {url}. Refreshing token...")
                    try:
                        new_token = await self.get_authorisation()
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

    async def get_transactions(
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

        response = await self._request_with_retry("GET", url, params=params)
        if response is None:
            return None

        return TransactionsResponse.model_validate(response.json())

    async def get_balance(self, currencycode: str = "RUB") -> Optional[BalanceResponse]:
        url = "https://app.platega.io/balance"
        params = {"CurrencyCode": currencycode}

        response = await self._request_with_retry("GET", url, params=params)
        if response is None:
            return None

        return BalanceResponse.model_validate(response.json())

#
# class Transaction(BaseModel):
#     recordId: str
#     status: int
#     paymentMethod: Optional[int] = None
#     amount: float
#     currencyCode: str
#     merchantId: str
#     merchantName: str
#     usdtAmount: float
#     createdAt: datetime
#     payload: Optional[Any] = None
#     description: str
#     fee: Optional[float] = None
#     usdtFee: float
#     qrId: Optional[str] = None
#
#
# class TransactionsResponse(BaseModel):
#     transactions: List[Transaction]
#     totalCount: int
#     page: int
#     pageSize: int
#     totalPages: int
#
def get_authorisation(login: str, password: str):

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
        "Login": login,
        "Password": password
    }

    # response = requests.post(url, headers=headers, json=payload)
    # print(response.status_code)
    # print(response.text)
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        pprint(response.text)
        print()
        data = response.json()
        token = data.get("accesToken")

        if token:
            result = token
            return result
        else:
            result = f"Токен не найден в ответе:\n{data}"
            return result


    except requests.exceptions.Timeout:
        print("Ошибка: таймаут запроса")
    except requests.exceptions.ConnectionError:
        print("Ошибка: проблема соединения")
    except requests.exceptions.HTTPError as e:
        print("HTTP ошибка:", e)
        try:
            print("Ответ сервера:", e.response.json())
        except Exception:
            print("Ответ сервера:", e.response.text)
    except requests.exceptions.RequestException as e:
        print("Ошибка requests:", e)
    except ValueError:
        print("Ошибка: сервер вернул невалидный JSON")


def get_balance(token:str, currencycode: str = "RUB"):
    url = "https://app.platega.io/balance"
    params = {"CurrencyCode": currencycode}

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Authorization": "Bearer "+token,
        "Origin": "https://my.platega.io",
        "Referer": "https://my.platega.io/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "TE": "trailers",
    }

    # response = requests.get(url, params=params, headers=headers)
    # print(response.status_code)
    # print(response.text)
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()

        data = response.json()
        print(data)
        amount = data.get("amount")


        if amount:
            result = f"{amount} {currencycode}"
            return result
        else:
            result = f"Баланс не найден в ответе:\n{data}"
            return result


    except requests.exceptions.Timeout:
        print("Ошибка: таймаут запроса")
    except requests.exceptions.ConnectionError:
        print("Ошибка: проблема соединения")
    except requests.exceptions.HTTPError as e:
        print("HTTP ошибка:", e)
        try:
            print("Ответ сервера:", e.response.json())
        except Exception:
            print("Ответ сервера:", e.response.text)
    except requests.exceptions.RequestException as e:
        print("Ошибка requests:", e)
    except ValueError:
        print("Ошибка: сервер вернул невалидный JSON")



def get_statistics_by_currency(token: str, date_start: str, date_end: str, currency_code: str = "RUB"):
    start_date = date.fromisoformat(date_start)
    end_date = date.fromisoformat(date_end)

    dt_start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    dt_end = datetime.combine(end_date, time.max, tzinfo=timezone.utc)

    url = "https://app.platega.io/user/statistics/by-currency"
    params = {
        "DateStart": dt_start.isoformat().replace("+00:00", "Z"),
        "DateEnd": dt_end.isoformat().replace("+00:00", "Z"),
        "CurrencyCode": currency_code,
        "timezoneId": "UTC",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0",
        "Accept": "application/json, text/plain, */*",
        "Authorization": f"Bearer {token}",
        "Origin": "https://my.platega.io",
        "Referer": "https://my.platega.io/",
    }

    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()

def search_transactions(token: str, page: int = 1, size: int = 10, direction: int = 0):
    url = "https://app.platega.io/transaction/search"
    params = {
        "Page": page,
        "Size": size,
        "Direction": direction,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Authorization": f"Bearer {token}",
        "Origin": "https://my.platega.io",
        "Referer": "https://my.platega.io/",
    }

    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()





async def main():
    async with PlategaAsyncClient(login="mylogin@gmail.com", password="mypassword") as client:
        balance = await client.get_balance()
        print(balance)

if __name__ == "__main__":
    TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI2NTJkN2QyNS1jMzJiLTQ0MjQtOGM2ZC0xMzYxNzAxMzUzYjkiLCJyb2xlIjoiTWVyY2hhbnRVc2VyIiwibG9naW4iOiJjaGlrc2xlYWRtb2RlbHNAZ21haWwuY29tIiwibWVyY2hhbnRJZCI6ImE4ZTFhNmVkLWM1ODYtNDc4Yi1hYzNkLTgxYWMxZWI3MGNmNSIsImVtYWlsIjoiY2hpa3NsZWFkbW9kZWxzQGdtYWlsLmNvbSIsIm5iZiI6MTc3NzUyODQ3NiwiZXhwIjoxNzc3NTg2MDc2LCJpYXQiOjE3Nzc1Mjg0NzZ9.HyyPTAFIzIza0SgSkNfULPuoLzTAUSH0hQLgr2q-L0Y"

    LOGIN = "chiksleadmodels@gmail.com"
    PASSWORD = "Bezoncoder_1986"



    # print(asyncio.run(platga_client.get_balance()))


    # asyncio.run(main())

    print(search_transactions(token=TOKEN).get('transactions')[0])
    # print(get_statistics_by_currency(token=TOKEN, date_start="2026-04-28", date_end="2026-04-28"))
    # {'statsByCurrency': [{'currency': 'RUB',
    #                       'turnover': 460.0,
    #                       'netProfit': 409.4,
    #                       'successTransactionsCount': 2,
    #                       'failedTransactionsCount': 5,
    #                       'chargebackTransactionsCount': 0,
    #                       'allTransactionsCount': 7,
    #                       'averageTransactionValue': 230.0,
    #                       'conversionRate': 28.57,
    #                       'chargebackAmount': 0}]}
    # print(get_authorisation(login=LOGIN, password=PASSWORD))

    # print(get_balance(token=TOKEN, currencycode="RUB"))
    # test = asyncio.run(check_and_ban())
    # print(test)

# curl 'https://app.platega.io/user/login' \
#   -X POST \
#   -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0' \
#   -H 'Accept: application/json, text/plain, */*' \
#   -H 'Accept-Language: ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7' \
#   -H 'Accept-Encoding: gzip, deflate, br, zstd' \
#   -H 'Content-Type: application/json' \
#   -H 'Origin: https://my.platega.io' \
#   -H 'Connection: keep-alive' \
#   -H 'Referer: https://my.platega.io/' \
#   -H 'Sec-Fetch-Dest: empty' \
#   -H 'Sec-Fetch-Mode: cors' \
#   -H 'Sec-Fetch-Site: same-site' \
#   -H 'Priority: u=0' \
#   -H 'TE: trailers' \
#   --data-raw '{"login":"mylogin@gmail.com","password":"mypassword"}'


#   --data-raw '{"login":"chiksleadmodels@gmail.com","password":"Bezoncoder_1986"}'



# curl 'https://app.platega.io/balance?CurrencyCode=RUB' \
#   -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0' \
#   -H 'Accept: application/json, text/plain, */*' \
#   -H 'Accept-Language: ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7' \
#   -H 'Accept-Encoding: gzip, deflate, br, zstd' \
#   -H 'Authorization: Bearer ' \
#   -H 'Origin: https://my.platega.io' \
#   -H 'Connection: keep-alive' \
#   -H 'Referer: https://my.platega.io/' \
#   -H 'Sec-Fetch-Dest: empty' \
#   -H 'Sec-Fetch-Mode: cors' \
#   -H 'Sec-Fetch-Site: same-site' \
#   -H 'TE: trailers'