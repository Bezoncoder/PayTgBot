import requests
import json

def create_payment(token, amount, client_name, client_email, client_phone):
    url = "https://enter.tochka.com/uapi/acquiring/v1.0/payments_with_receipt"
    payload = {
        "Data": {
            "customerCode": "300000092",
            "amount": amount,
            "purpose": "Перевод за оказанные услуги",
            "redirectUrl": "https://example.com",
            "failRedirectUrl": "https://example.com/fail",
            "paymentMode": ["sbp", "card", "tinkoff", "dolyame"],
            "saveCard": True,
            "consumerId": "fedac807-078d-45ac-a43b-5c01c57edbf8",
            "merchantId": "200000000001056",
            "preAuthorization": True,
            "ttl": 10080,
            "paymentLinkId": "string",
            "taxSystemCode": "osn",
            "Client": {
                "name": client_name,
                "email": client_email,
                "phone": client_phone
            },
            "Items": [
                {
                    "vatType": "none",
                    "name": "Услуга",
                    "amount": amount,
                    "quantity": 1,
                    "paymentMethod": "full_payment",
                    "paymentObject": "service",
                    "measure": "шт.",
                    "Supplier": {
                        "phone": "+7999999999",
                        "name": "ООО Альтер",
                        "taxCode": "660000000000"
                    }
                }
            ],
            "Supplier": {
                "phone": "+7999999999",
                "name": "ООО Альтер",
                "taxCode": "660000000000"
            }
        }
    }

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    response = requests.post(url, headers=headers, json=payload)
    return response.json()

import json
import logging
import requests


class TochkaAPI:
    def __init__(self, token: str):
        if not token:
            raise ValueError("API token must be provided")
        self.token = token

    def _request(self, method: str, endpoint: str, data=None) -> dict:
        base_url = "https://enter.tochka.com/uapi/acquiring/v1.0"
        full_url = f"{base_url}{endpoint}"
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.token}'
        }
        if method.upper() == "POST":
            headers['Content-Type'] = 'application/json'
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

    def create_payment_operation_with_receipt(self, *args, **kwargs) -> dict:
        """
        Expects parameters as kwargs:
        customer_code, payment_link_id, product_name, amount=0, purpose, quantity=1, client_name, email
        """
        customer_code = kwargs.get('customer_code')
        payment_link_id = kwargs.get('payment_link_id')
        product_name = kwargs.get('product_name')
        amount = kwargs.get('amount', 0)
        purpose = kwargs.get('purpose', "Назначение Платежа")
        quantity = kwargs.get('quantity', 1)
        client_name = kwargs.get('client_name', "Нет Данных ФИО")
        email = kwargs.get('email', "ivanov@mail.com")

        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        if quantity < 1:
            raise ValueError("Quantity must be at least 1")

        endpoint = "/payments_with_receipt"
        payload = {
            "Data": {
                "customerCode": str(customer_code),
                "amount": str(amount),
                "purpose": purpose,
                "paymentMode": ["sbp", "dolyame"],
                "paymentLinkId": payment_link_id,
                "taxSystemCode": "osn",
                "Client": {
                    "name": str(client_name),
                    "email": email
                },
                "Items": [
                    {
                        "name": product_name,
                        "amount": str(amount),
                        "quantity": str(quantity)
                    }
                ]
            }
        }
        try:
            data = self._request("POST", endpoint=endpoint, data=json.dumps(payload))
        except TochkaAPIError as e:
            print(f"TochkaAPI said: {e.message}")
            print(f"status = {e.code}")
            print(f"id = {e.id}")
            print(f"Ошибка: {e.first_error_code}")
            print(f"Расшифровка: {e.first_error_message}")
            print(f"Узнать подробности можно по ссылке: {e.first_error_url}")
            logging.error(e)
            return {}
        return data

    def get_payment_operation_info(self, *args, **kwargs) -> dict:
        """
        Expects 'operation_id' in kwargs or as the first positional argument
        """
        operation_id = kwargs.get('operation_id') if 'operation_id' in kwargs else (args[0] if args else None)
        if not operation_id:
            raise ValueError("operation_id must be provided")

        endpoint = f"/payments/{operation_id}"
        try:
            data = self._request("GET", endpoint=endpoint)
        except TochkaAPIError as e:
            print(f"TochkaAPI said: {e.message}")
            print(f"status = {e.code}")
            print(f"id = {e.id}")
            print(f"Ошибка: {e.first_error_code}")
            print(f"Расшифровка: {e.first_error_message}")
            print(f"Узнать подробности можно по ссылке: {e.first_error_url}")
            logging.error(e)
            return {}
        return data

    def get_balance_info(self, *args, **kwargs) -> dict:
        """
        Expects 'account_id' in kwargs or as the first positional argument
        """
        account_id = kwargs.get('account_id') if 'account_id' in kwargs else (args[0] if args else None)
        if not account_id:
            raise ValueError("account_id must be provided")

        endpoint = f"/accounts/{account_id}/balances"
        try:
            data = self._request("GET", endpoint=endpoint)
        except TochkaAPIError as e:
            print(f"TochkaAPI said: {e.message}")
            print(f"status = {e.code}")
            print(f"id = {e.id}")
            print(f"Ошибка: {e.first_error_code}")
            print(f"Расшифровка: {e.first_error_message}")
            print(f"Узнать подробности можно по ссылке: {e.first_error_url}")
            logging.error(e)
            return {}
        return data

    def get_customer_list(self, *args, **kwargs) -> dict:
        endpoint = "/customers"
        return self._request("GET", endpoint=endpoint)

    def get_business_customer_codes(self, *args, **kwargs) -> dict:
        customers = self.get_customer_list()
        if not customers or 'Data' not in customers:
            return {}

        business_codes = {}
        customers_data = customers.get("Data", [])
        for customer in customers_data.get('Customer', []):
            if customer.get("customerType") == "Business":
                try:
                    business_codes[f"{customer['customerType']} customer_code"] = int(customer.get("customerCode"))
                except (TypeError, ValueError):
                    continue
        return business_codes


# Пример вызова:
if __name__ == "__main__":
    token = "<token>"
    amount = "1234.00"
    client_name = "Иванов Иван Иванович"
    client_email = "ivanov@mail.com"
    client_phone = "+7999999999"

    result = create_payment(token, amount, client_name, client_email, client_phone)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # Так вы передаёте только токен, сумму и данные клиента, а все остальное — фиксированные значения внутри функции. При необходимости их можно легко поменять в теле метода.