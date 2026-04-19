from settings.config import MERCHANT_ID, PLATEGA_SECRET_KEY

import requests
import time
import logging
import json
import uuid
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

# Настройка логирования
# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

HTTP_STATUS_EMOJIS = {
    200: "✅", 201: "✨", 204: "📥",
    301: "➡️", 302: "➡️", 304: "🔄",
    400: "❌", 401: "🔐", 403: "🚫", 404: "❓",
    500: "🟥", 502: "🔥", 503: "🔥", 504: "💥"
}

class PlategaAPIError(Exception):
    """Базовый класс исключений для Platega API"""

    def __init__(self, message: str, status_code: Optional[int] = None,
                 response_data: Optional[Dict[str, Any]] = None):
        self.status_code = status_code
        self.response_data = response_data

        # 🔥 ПРОВЕРКА АВТОРИЗАЦИИ (401)
        if status_code == 401:
            self._is_auth_error = True
            auth_codes = ['Auth:SIGN_1001', 'AUTH_INVALID', 'SIGNATURE_INVALID']
            if response_data and 'code' in response_data and response_data['code'] in auth_codes:
                auth_message = response_data.get('message', 'Неверные учетные данные')
                message = f"🔐 АВТОРИЗАЦИЯ: {auth_message}"
            else:
                message = "🔐 АВТОРИЗАЦИЯ: Неверный Merchant ID или Secret ключ"
        else:
            self._is_auth_error = False

        super().__init__(f"Platega API Error {status_code}: {message}")

    @property
    def is_auth_error(self) -> bool:
        """Проверяет, является ли ошибка проблемой авторизации"""
        return getattr(self, '_is_auth_error', False)


class ValidationError(PlategaAPIError):
    """Ошибки валидации параметров (короткий merchant_id, api_secret и т.д.)"""

    def __init__(self, message: str):
        super().__init__(message, status_code=None, response_data=None)
        self._is_auth_error = False
        self._is_validation_error = True

    @property
    def is_validation_error(self) -> bool:
        return getattr(self, '_is_validation_error', False)


class PaymentStatus(Enum):
    PENDING = "pending"
    CANCELED = "canceled"
    CONFIRMED = "confirmed"
    CHARGEBACKED = "chargebacked"


class PaymentMethod(Enum):
    SBP_QR = 2
    CARD_ACQUIRING = 11
    CRYPTOCURRENCY = 13


@dataclass
class Payment:
    payment_method: PaymentMethod
    transaction_id: str
    redirect: str
    return_url: str
    payment_details: str
    status: PaymentStatus
    expires_in: str
    merchant_id: str
    usdt_rate: float


class PlategaAPI:
    BASE_URL = "https://app.platega.io"
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    MIN_CREDENTIALS_LENGTH = 10

    def __init__(self, merchant_id: str, api_secret: str):
        """
        Инициализация клиента Platega API

        :param merchant_id: Ваш MerchantId
        :param api_secret: Ваш API ключ (X-Secret)
        """
        if not merchant_id or not merchant_id.strip():
            raise ValidationError("❌ merchant_id не может быть пустым")
        if len(merchant_id.strip()) < self.MIN_CREDENTIALS_LENGTH:
            raise ValidationError(f"❌ merchant_id слишком короткий (минимум {self.MIN_CREDENTIALS_LENGTH} символов)")

        if not api_secret or not api_secret.strip():
            raise ValidationError("❌ api_secret не может быть пустым")
        if len(api_secret.strip()) < self.MIN_CREDENTIALS_LENGTH:
            raise ValidationError(f"❌ api_secret слишком короткий (минимум {self.MIN_CREDENTIALS_LENGTH} символов)")

        # 🔥 ПРИВАТНЫЕ АТРИБУТЫ - НЕДОСТУПНЫ СНАРУЖИ
        self._merchant_id = merchant_id.strip()
        self._api_secret = api_secret.strip()
        self.base_url = self.BASE_URL.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'X-MerchantId': self._merchant_id,
            'X-Secret': self._api_secret,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        logger.info(f"⚙️ PlategaAPI инициализирован: merchant_id={self._merchant_id[:8]}...")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def _validate_url(self, url: str) -> bool:
        if not url:
            return True
        try:
            result = urlparse(url)
            return all([result.scheme in ('http', 'https'), result.netloc])
        except:
            return False

    def _request(self, method: str, endpoint: str,
                 data: Optional[Dict[str, Any]] = None,
                 params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        logger.info(f"🌐 {method.upper()} {url}")
        if data:
            logger.debug(f"📤 Body: {json.dumps(data, indent=2, ensure_ascii=False)}")
        if params:
            logger.debug(f"📋 Params: {params}")
        logger.debug(f"🔑 MerchantId: {self._merchant_id[:8]}...")

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.request(
                    method=method.upper(),
                    url=url,
                    json=data,
                    params=params,
                    timeout=30
                )
                status = HTTP_STATUS_EMOJIS.get(response.status_code, '')
                logger.debug(f"{status} Status: {response.status_code}")

                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        logger.error(f"💥 API Error: {error_data}")
                    except:
                        logger.error(f"💥 Raw response: {response.text[:500]}")

                response.raise_for_status()
                logger.info(f"{status} Успех: {method} {endpoint}")
                return response.json()

            except requests.exceptions.Timeout as e:
                logger.warning(f"⏰ Таймаут (попытка {attempt + 1}/{self.MAX_RETRIES})")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (2 ** attempt))
                    continue
                raise PlategaAPIError("Request timeout после всех попыток", status_code=408) from e

            except requests.exceptions.ConnectionError as e:
                logger.warning(f"🔌 Ошибка соединения (попытка {attempt + 1}/{self.MAX_RETRIES})")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (2 ** attempt))
                    continue
                raise PlategaAPIError("Ошибка соединения после всех попыток", status_code=None) from e

            except requests.exceptions.HTTPError as e:
                status_code = getattr(e.response, 'status_code', None)
                response_data = None
                if e.response:
                    try:
                        response_data = e.response.json()
                    except:
                        response_data = {"raw": e.response.text[:1000]}

                if status_code and status_code >= 500 and attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"🚫 Серверная ошибка {status_code}")
                    time.sleep(self.RETRY_DELAY * (2 ** attempt))
                    continue

                raise PlategaAPIError(
                    message=str(e),
                    status_code=status_code,
                    response_data=response_data
                ) from e

        raise PlategaAPIError("Сервер недоступен после всех попыток", status_code=None)

    def create_payment(self, amount: float, description: str,
                       currency: str = 'RUB', success_url: str = '',
                       fail_url: str = '', payload: str = '',
                       payment_method: int = 2) -> Dict[str, Any]:
        """
        Создает транзакцию с правильной структурой для Platega API
        """
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValidationError(f"❌ Сумма должна быть положительным числом, получено: {amount}")
        if amount < 0.01:
            raise ValidationError("❌ Минимальная сумма платежа: 0.01")

        if not isinstance(description, str):
            raise ValidationError("❌ description должен быть строкой")
        if len(description.strip()) > 255:
            raise ValidationError("❌ description не должен превышать 255 символов")

        allowed_currencies = ['RUB', 'USDT']
        if currency not in allowed_currencies:
            raise ValidationError(f"❌ Валюта должна быть одной из: {allowed_currencies}")

        if not self._validate_url(success_url):
            raise ValidationError("❌ success_url должен быть пустым или валидным URL")
        if not self._validate_url(fail_url):
            raise ValidationError("❌ fail_url должен быть пустым или валидным URL")

        if payload and len(payload) > 1000:
            raise ValidationError("❌ payload не должен превышать 1000 символов")

        payment_uuid = str(uuid.uuid4())

        payload_data = {
            "command": "create",
            "id": payment_uuid,
            "paymentMethod": int(payment_method),
            "paymentDetails": {
                "amount": round(amount, 2),
                "currency": currency
            },
            "description": description.strip(),
            "returnUrl": success_url or None,
            "failedUrl": fail_url or None,
            "payload": payload or None
        }

        logger.info(f"💳 Создание платежа: amount={amount}, uuid={payment_uuid[:8]}...")
        response_data = self._request('POST', 'transaction/process', data=payload_data)
        return response_data

    def get_payment_status(self, transaction_id: str) -> Dict[str, Any]:
        if not isinstance(transaction_id, str):
            raise ValidationError("❌ transaction_id должен быть строкой")
        if not transaction_id.strip():
            raise ValidationError("❌ transaction_id не может быть пустым")
        if len(transaction_id) < 10:
            raise ValidationError("❌ transaction_id слишком короткий для UUID")

        logger.info(f"🔍 Проверка статуса: {transaction_id[:8]}...")
        response_data = self._request('GET', f'transaction/{transaction_id}')
        return response_data

    def get_payment_method_rate(self, payment_method: PaymentMethod,
                                currency_from: str = None, currency_to: str = None) -> Dict[str, Any]:
        if not isinstance(payment_method, PaymentMethod):
            raise ValidationError(f"❌ payment_method должен быть PaymentMethod, получено: {payment_method}")

        # allowed_currencies = ['RUB', 'USDT', 'USD', 'EUR']
        # if currency_from not in allowed_currencies:
        #     raise ValidationError(f"❌ currency_from должен быть из: {allowed_currencies}")
        # if currency_to not in allowed_currencies:
        #     raise ValidationError(f"❌ currency_to должен быть из: {allowed_currencies}")

        params = {
            'merchantId': self._merchant_id,
            'paymentMethod': payment_method.value,
            'currencyFrom': currency_from,
            'currencyTo': currency_to
        }

        response_data = self._request('GET', 'rates/payment_method_rate', params=params)
        return response_data

    def get_balance_unlock_operations(self, from_date: str, to_date: str,
                                      page: int = 1, size: int = 20) -> Dict[str, Any]:
        def validate_iso_date(date_str: str) -> bool:
            if not isinstance(date_str, str):
                return False
            try:
                time.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
                return True
            except ValueError:
                return False

        if not validate_iso_date(from_date):
            raise ValidationError("❌ from_date должен быть в формате ISO 8601 (2025-01-01T00:00:00Z)")
        if not validate_iso_date(to_date):
            raise ValidationError("❌ to_date должен быть в формате ISO 8601 (2025-01-01T23:59:59Z)")

        if page < 1:
            raise ValidationError("❌ page должен быть >= 1")
        if size < 1 or size > 100:
            raise ValidationError("❌ size должен быть от 1 до 100")

        params = {
            'from': from_date,
            'to': to_date,
            'page': str(page),
            'size': str(size)
        }

        response_data = self._request('GET', 'transaction/balance-unlock-operations', params=params)
        return response_data


# Тестовый блок
if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    # SBP_QR = 2
    #
    # CARD_ACQUIRING = 11
    #
    # CRYPTOCURRENCY = 13
    MERCHANT_ID_test = "a8e1a6ed-c586-478b-ac3d-81ac1eb70cf5"
    PLATEGA_SECRET_KEY_test = "9kx7SgS9BYfP07Pq0ExsVqExYZHXGLvGKVEhMLXx5kzgVmTGLFqC53NkgOaB3UdNhturqAwumz3D1kjPWpOMJYuS1TDBDhwOVStk"
    gd = PaymentMethod

    try:
        a=PlategaAPI(MERCHANT_ID_test, PLATEGA_SECRET_KEY_test)
        link = a.create_payment(payment_method=gd.CARD_ACQUIRING.value, amount=10, description='test')
        # link = a.get_payment_method_rate( payment_method=gd.SBP_QR)
        print(f"link = {link}")
    except Exception as e:
        print(e)
