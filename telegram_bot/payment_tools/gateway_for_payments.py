from typing import Any, Dict, List, Optional
import json
import logging
import requests


class TochkaAPIError(Exception):
    """
    Исключение для ошибок Точка.API.
    Ожидаемый формат JSON:
    {
        "code": "400",
        "id": "...",
        "message": "Что-то пошло не так",
        "Errors": [
            {
                "errorCode": "Validation Error",
                "message": "Field operation_id ...",
                "url": "https://developers.tochka.com/"
            },
            ...
        ]
    }
    """

    def __init__(self, response: requests.Response):
        self.status_code: Optional[int] = response.status_code
        self.raw_body: str = response.text

        try:
            data: Dict[str, Any] = response.json()
        except ValueError:
            # если пришло не JSON
            self.code = None
            self.id = None
            self.message = response.text[:500]
            self.errors: List[Dict[str, Any]] = []
            super().__init__(
                f"[TochkaAPI] status={self.status_code} msg={self.message}"
            )
            return

        # Верхнеуровневые поля
        self.code: Optional[str] = data.get("code")
        self.id: Optional[str] = data.get("id")
        self.message: str = data.get("message") or "Tochka API error"

        # Массив ошибок
        self.errors: List[Dict[str, Any]] = data.get("Errors") or []

        # Для удобства достанем первую ошибку (чаще всего достаточно её)
        self.first_error_code: Optional[str] = None
        self.first_error_message: Optional[str] = None
        self.first_error_url: Optional[str] = None

        if self.errors:
            first = self.errors[0]
            self.first_error_code = first.get("errorCode")
            self.first_error_message = first.get("message")
            self.first_error_url = first.get("url")

        # Формируем читабельное сообщение
        parts = [
            f"status={self.status_code}",
            f"code={self.code}" if self.code else None,
            f"id={self.id}" if self.id else None,
            f"msg={self.message}",
        ]

        if self.first_error_code:
            parts.append(f"detailCode={self.first_error_code}")
        if self.first_error_message:
            parts.append(f"detailMsg={self.first_error_message}")
        if self.first_error_url:
            parts.append(f"doc={self.first_error_url}")

        text = "[TochkaAPI] " + " | ".join(p for p in parts if p)
        super().__init__(text)


class TochkaAPI:
    def __init__(self, token: str):
        if not token:
            raise ValueError("API token must be provided")
        self.token = token

    def _request(self, method: str, endpoint: str, data=None) -> dict:
        base_url = "https://enter.tochka.com/uapi/acquiring/v1.0"  # Базовый URL
        full_url = f"{base_url}{endpoint}"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
        if method.upper() == "POST":
            headers["Content-Type"] = "application/json"
            response = requests.post(url=full_url, headers=headers, data=data)
        elif method.upper() == "GET":
            response = requests.get(url=full_url, headers=headers, params=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        try:
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            logging.error(e)
            raise TochkaAPIError(response)

    def create_payment_operation_with_receipt(
        self,
        customer_code: int,
        payment_link_id: str,
        product_name: str,
        amount: float = 0,
        purpose: str = "Назначение Платежа",
        quantity: int = 1,
        client_name: str = "Нет Данных ФИО",
        email: str = "ivanov@mail.com",
    ) -> dict:
        """
        Create Payment Operation With Receipt

        Метод для создания ссылки на оплату и отправки чека


        :param customer_code: можно получить из метода self.get_business_customer_codes()
        :param payment_link_id: уникальный идентификатор "string"
        :param product_name: название продукта
        :param amount: цена за единицу
        :param purpose: "Перевод за оказанные услуги"
        :param quantity: колличество
        :param client_name: ФИО покупателя
        :return: dict инфо о платеже

        {'Data': {'purpose': 'Назначение Платежа',
                'status': 'CREATED',
                'amount': 1.0,
                'operationId': 'e4d4b392-c4fe-4b27-b77c-93ef95140a8b',
                'paymentLink': 'https://merch.tochka.com/order',
                'consumerId': 'ac01a1a3-7b6e-456d-a527-298bfb943d30',
                'ttl': 10080,
                'paymentLinkId':
                'tyesst2',
                'paymentMode': ['sbp', 'dolyame'],
                ...
                }
        }

        """

        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        if quantity < 1:
            raise ValueError("Quantity must be at least 1")

        endpoint = "/payments_with_receipt"
        payload = {
            "Data": {
                # "paymentMode": ["sbp", "card", "tinkoff", "dolyame"],
                "customerCode": str(customer_code),
                "amount": str(amount),
                "purpose": purpose,
                "paymentMode": ["sbp", "dolyame"],
                "paymentLinkId": payment_link_id,
                "taxSystemCode": "osn",
                "Client": {"name": str(client_name), "email": email},
                "Items": [
                    {
                        "name": product_name,
                        "amount": str(amount),
                        "quantity": str(quantity),
                    }
                ],
            }
        }
        try:
            data = self._request("POST", endpoint=endpoint, data=json.dumps(payload))
        except TochkaAPIError as e:
            print(f"TochkaAPI said: {e.message}")  # "Что-то пошло не так"
            print(f"status = {e.code}")  # "400"
            print(f"id = {e.id}")  # "9269395f-a03f-4ab7-9575-c9bba412b516"
            print(f"Ошибка: {e.first_error_code}")  # "Validation Error"
            print(
                f"Расшифровка: {e.first_error_message}"
            )  # "Field operation_id : String should have at most 36 characters; "
            print(
                f"Узнать подробности можно по ссылке: {e.first_error_url}"
            )  # "https://developers.tochka.com/"
            logging.error(e)
            return {}
        # pprint(data)
        return data

    def get_payment_operation_info(self, operation_id: str) -> dict:
        endpoint = f"/payments/{operation_id}"
        try:
            data = self._request("GET", endpoint=endpoint)
        except TochkaAPIError as e:
            print(f"TochkaAPI said: {e.message}")  # "Что-то пошло не так"
            print(f"status = {e.code}")  # "400"
            print(f"id = {e.id}")  # "9269395f-a03f-4ab7-9575-c9bba412b516"
            print(f"Ошибка: {e.first_error_code}")  # "Validation Error"
            print(
                f"Расшифровка: {e.first_error_message}"
            )  # "Field operation_id : String should have at most 36 characters; "
            print(
                f"Узнать подробности можно по ссылке: {e.first_error_url}"
            )  # "https://developers.tochka.com/"
            logging.error(e)
            return {}
        # pprint(data)
        return data

    def get_balance_info(self, account_id: str) -> dict:
        """
        Get Balance Info

        Метод для получения информации о балансе конкретного счёта

        :param account_id: номер расчётного счёта и БИК Точки, разделённые через / слеш
        :return: account_info

        """
        endpoint = f"/accounts/{account_id}/balances"

        try:
            data = self._request("GET", endpoint=endpoint)
        except TochkaAPIError as e:
            print(f"TochkaAPI said: {e.message}")  # "Что-то пошло не так"
            print(f"status = {e.code}")  # "400"
            print(f"id = {e.id}")  # "9269395f-a03f-4ab7-9575-c9bba412b516"
            print(f"Ошибка: {e.first_error_code}")  # "Validation Error"
            print(
                f"Расшифровка: {e.first_error_message}"
            )  # "Field operation_id : String should have at most 36 characters; "
            print(
                f"Узнать подробности можно по ссылке: {e.first_error_url}"
            )  # "https://developers.tochka.com/"
            logging.error(e)
            return {}
        return data

    def get_customer_list(self) -> dict:
        endpoint = "/customers"
        return self._request("GET", endpoint=endpoint)

    def get_business_customer_codes(self) -> dict[Any, Any] | list[Any]:
        """
        Extracts customerCode values where customerType is 'Business' from customer list.
        """
        customers = self.get_customer_list()
        if not customers or "Data" not in customers:
            return {}

        business_codes = {}
        customers = customers.get("Data", [])
        for customer in customers["Customer"]:
            if customer["customerType"] == "Business":
                try:
                    business_codes[f"{customer['customerType']} customer_code"] = int(
                        customer.get("customerCode")
                    )
                except (TypeError, ValueError):
                    continue
        return business_codes


if __name__ == "__main__":
    TOCHKA_BANK_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI3MzVlNDczM2E2MTAzMTkzODE2MjAzMGYwNWNmZTI2OSIsInN1YiI6IjFlZTZiOThjLWQ5N2QtNDQwZC1hNjhjLWRiN2E2MWZmNWIwOSIsImN1c3RvbWVyX2NvZGUiOiIzMDUzNTY3NjUifQ.PD5VKjXkTQZGTlfAUVZdu2D3ny6P2l0r1FBANCXgxaFr3DcLN2pOMYfpMnXTpdDWF6OrAn2hwDN76-ZEB8k3sUajIBB4iSEmXJWGLIJscK7xMRPymIOUipT3vnq_G_rkbeFgVd7sRclSoxHXMjoqKD58CGzt9tuWBlHUHLj9PaYfBXGUenpTR5E5IbrFikcLyYzqNOvikLlovdkiLQU5NNwgtsdKsaOqztNW4zxhmWoNNH4EGjFD8qDM0ucHDoHT4_EiVgRBAn5uHOG1TPP02DQuJA0gBv8PRWfR6h4h9h3tRv9DTVXSutXNEHXFMvvjdTUZrUQTeLHlu6Ki0lKQJIiYnmTjjRV2LIhJGQefsW_W_7hqHOXwptfYrBhTafDHflZzz1ilaHkv0RbidhdrK5h3V7iZQjQRBJP0L305-QTqSw5lm6KfkY0YS8UCf8TRb0wC3dfRzcqXPHG1r6JPDZASLqAHDS9u_2fa6ZUIV2miSxhfT8Hp2J9X1ymgo12Y"
    TOCHKA_BANK_CUSTOMER_CODE = 305352162
    TOCHKA_BANK_ACCOUNT_ID = "40802810220000801577/044525104"
    TOCHKA_BANK_REDIRECT_URL = "https://vk.com/roadmappers"

    tochka = TochkaAPI(token=TOCHKA_BANK_TOKEN)
    # 'operationId': 'd437ae74-385c-4233-bf92-3863e6a1c5d0'
    # print(tochka.get_balance_info(account_id=ACCOUNT_ID))
    # print(tochka.get_payment_link(customer_code=customer_сode, payment_link_id='qwerty', product_name='TEST', amount=1))
    # print(tochka.get_business_customer_codes())
    print(
        tochka.create_payment_operation_with_receipt(
            customer_code=TOCHKA_BANK_CUSTOMER_CODE,
            payment_link_id="tyesst4",
            product_name="Laga",
            amount=1,
        )
    )
    # print(tochka.get_payment_operation_info(operation_id='d437ae74-385c-4233-bf92-3863e6a1c5d0'))
