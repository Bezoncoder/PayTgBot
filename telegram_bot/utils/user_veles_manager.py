import requests
import time
import logging
from typing import Dict, Any, Optional

# ✅ ГЛОБАЛЬНАЯ НАСТРОЙКА ЛОГИРОВАНИЯ (один раз!)
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[logging.StreamHandler()]
# )


class UserVelesManagerAPI:
    """
    Клиент для работы с User Manager API (213.139.229.165:8000)
    Production-ready с retry логикой и профессиональным логированием
    """

    def __init__(self, base_url: str = "http://213.139.229.165:8000",
                 secret_key: str = "bezoncoder-secure-api-v1-2026-X7K9P2M4"):
        """
        Args:
            base_url: Базовый URL API
            secret_key: Секретный ключ (приватное свойство)
        """
        self.base_url = base_url.rstrip('/')
        self._secret_key = secret_key
        self.logger = logging.getLogger('UserManagerAPI')

    def _request(self, method: str, endpoint: str, payload: Optional[Dict] = None,
                 max_retries: int = 3, timeout: int = 2) -> Dict[str, Any]:
        """
        Внутренний метод HTTP запросов с retry логикой (3 попытки)
        """
        url = f"{self.base_url}{endpoint}"

        for attempt in range(max_retries + 1):
            headers = {
                "secret_key": self._secret_key,
                "Content-Type": "application/json"
            }

            try:
                self.logger.debug(f"🔄 Попытка {attempt + 1}/{max_retries + 1}: {method} {url}")

                if method.upper() == 'GET':
                    response = requests.get(url, headers=headers, timeout=10)
                elif method.upper() == 'POST':
                    response = requests.post(url, headers=headers, json=payload, timeout=10)
                else:
                    response = requests.request(method, url, headers=headers, json=payload, timeout=10)

                # ✅ Успешный ответ (<500)
                if response.status_code < 500:
                    if response.status_code == 200 and response.text.strip():
                        self.logger.info(f"✅ {method} {endpoint}: {response.status_code}")
                        return response.json()
                    else:
                        self.logger.warning(f"⚠️ {method} {endpoint}: HTTP {response.status_code}")
                        return {
                            "status_code": response.status_code,
                            "text": response.text[:200],
                            "success": False,
                            "error": "Empty or invalid response"
                        }

                # 5xx ошибки — retry
                self.logger.warning(f"❌ Серверная ошибка {response.status_code}. Повтор...")

            except requests.exceptions.Timeout:
                self.logger.warning(f"⏰ Timeout. Попытка {attempt + 1}/{max_retries + 1}")
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"🔌 Нет соединения. Попытка {attempt + 1}/{max_retries + 1}")
            except requests.exceptions.RequestException as e:
                self.logger.error(f"🌐 Request error: {str(e)}")

            # Задержка перед повтором
            if attempt < max_retries:
                self.logger.debug(f"💤 Ожидание {timeout}с...")
                time.sleep(timeout)

        self.logger.error(f"💥 Все {max_retries + 1} попытки неудачны: {url}")
        return {"status_code": 0, "success": False, "error": "All retries failed"}

    def add_user(self, username: str):
        """🆕 POST /newuser/ - создание пользователя"""
        self.logger.info(f"🆕 Создание пользователя: {username}")
        data = self._request('POST', '/newuser/', {"user_name": username})

        self.logger.info(f"📊 returncode={data.get('returncode', 'N/A')}, success={data.get('success', False)}")
        if data.get('stdout'):
            self.logger.info(f"📤 STDOUT: {data.get('stdout')}")
        if data.get('stderr'):
            self.logger.error(f"❌ STDERR: {data.get('stderr')}")

        # return data.get('success', False)
        return data.get('stdout')

    def delete_user(self, username: str) -> bool:
        """🗑️ POST /rmuser/ - удаление пользователя"""
        self.logger.info(f"🗑️ Удаление пользователя: {username}")
        data = self._request('POST', '/rmuser/', {"user_name": username})

        self.logger.info(f"📊 returncode={data.get('returncode', 'N/A')}, success={data.get('success', False)}")
        if data.get('stdout'):
            self.logger.info(f"📤 STDOUT: {data.get('stdout')}")
        if data.get('stderr'):
            self.logger.error(f"❌ STDERR: {data.get('stderr')}")

        return data.get('success', False)

    def test_connection(self) -> bool:
        """🔍 GET /test/ - тест подключения"""
        self.logger.info("🔍 Тест подключения...")
        data = self._request('GET', '/test/')

        # ✅ Новый формат ответа сервера
        status = data.get('status', 'ERROR')
        secret_key_verified = data.get('secret_key_verified', False)

        self.logger.info(f"🌐 API status: {status}")
        self.logger.info(f"🔑 Secret key verified: {secret_key_verified}")
        self.logger.info(f"✅ Подключение: {'🟢 OK' if status == 'OK' and secret_key_verified else '🔴 Failed'}")

        return status == "OK" and secret_key_verified




# 🚀 Пример использования
if __name__ == "__main__":
    print("🔥 Запуск UserManagerAPI...\n")

    # ✅ САМЫЙ ПРОСТОЙ запуск!
    labuda = UserVelesManagerAPI()

    # Тест подключения
    if labuda.test_connection():
        print("\n✅ API доступен!")
        test = labuda.add_user("Vasja")
        print(test)
        # test2 = labuda.delete_user(username="Vasja")
        # print(test2)
    else:
        print("❌ API недоступен!")

