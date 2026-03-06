from os import name
from pprint import pprint
from urllib.parse import urlparse
from types import new_class

import requests
import json
import time
import logging
import uuid
from typing import Dict, Any, Optional
import pandas as pd
import json

# Настройка логирования
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.StreamHandler(),
#         logging.FileHandler('xui_client.log')
#     ]
# )
logger = logging.getLogger(__name__)


class XUIClient:
    def __init__(self, base_url_from_panel: str = None,
                 public_inbound_key: str = None, sid: str = None, sni: str = "ya.ru",
                 username: str = None, password: str = None, two_factor: str = None,
                 verify_ssl: bool = False, auto_login: bool = True):

        # 🔍 ПАРСИМ base_url → host, port, web_path, protocol
        parsed = urlparse(base_url_from_panel.rstrip('/'))


        # Серверные параметры (из 3X-UI Reality)
        self.server_params = {
            'pbk': public_inbound_key,
            'sid': sid,
            'sni': sni
        }

        self.base_url = base_url_from_panel
        self.host = parsed.hostname
        self.port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        self.web_path = parsed.path.rstrip('/') if parsed.path else ''
        self.use_https = parsed.scheme == 'https'
        self.username = username
        self.password = password
        self.two_factor = two_factor
        self.verify_ssl = verify_ssl

        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        # Отключение SSL проверки для самоподписанных сертификатов
        self.session.verify = verify_ssl

        self.is_authenticated = False

        logger.info(f"XUIClient инициализирован: {self.base_url}")

        # Автоматический логин
        if auto_login and username and password:
            self._auto_login()

    def _make_request(self, endpoint: str, method: str = "POST", **kwargs) -> Optional[Dict[str, Any]]:
        """Базовый API запрос"""
        if not self.is_authenticated:
            logger.warning("⚠️ Не авторизован!")
            return None

        url = f"{self.base_url}/panel/api/{endpoint}"
        logger.info(url)
        try:
            logger.debug(f"Запрос: {method} {endpoint}")
            response = self.session.request(method, url, timeout=30, **kwargs)

            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.debug(f"Успешный ответ: {endpoint}")
                    return result
                except:
                    logger.debug(f"Raw ответ: {response.text}")
                    return {"success": True, "raw": response.text}
            else:
                logger.error(f"❌ HTTP {response.status_code}: {response.text}")
                return None

        except requests.RequestException as e:
            logger.error(f"❌ API Error {endpoint}: {e}")
            return None

    def _auto_login(self) -> bool:
        """Внутренний метод автоматической авторизации"""
        return self.login(self.username, self.password, self.two_factor)

    @staticmethod
    def _generate_client_uuid() -> str:
        """Генерация уникального UUID для клиента"""
        return str(uuid.uuid4())

    def _generate_vless_link(self, client_uuid: str,
                             profile_name: str,
                             host: str,
                             vless_port: int = 443) -> str:
        """
        Генератор VLESS Reality ссылок для 3X-UI

        ОБЯЗАТЕЛЬНЫЕ ПАРАМЕТРЫ и ГДЕ ИХ БРАТЬ:

        ╔══════════════════════════════════════════════════════════════╗
        ║ 1. uuid                   │ 3X-UI → Inbounds → Клиенты → ID  ║
        ║                           │ remark: "678efafd-36c5-..."       ║
        ╚══════════════════════════════════════════════════════════════╝

        ╔══════════════════════════════════════════════════════════════╗
        ║ 2. host                   │ IP сервера (155.212.228.65)       ║
        ║                           │ Где угодно (известно заранее)     ║
        ╚══════════════════════════════════════════════════════════════╝

        ╔══════════════════════════════════════════════════════════════╗
        ║ 3. port                   │ 3X-UI → Inbounds → Port (6443)    ║
        ║                           │ Настройки подключения             ║
        ╚══════════════════════════════════════════════════════════════╝

        ╔══════════════════════════════════════════════════════════════╗
        ║ 4. public_inbound_key     │ 3X-UI → Inbounds → Reality        ║
        ║     (pbk)                 │    → Public Key                   ║
        ║                           │ "lFJfqBItMEQ_cRFJxCsWor..."       ║
        ╚══════════════════════════════════════════════════════════════╝

        ╔══════════════════════════════════════════════════════════════╗
        ║ 5. sid (Short ID)         │ 3X-UI → Inbounds → Reality        ║
        ║     ★ОБЯЗАТЕЛЬНО★        │    → Short ID (d35ff639)          ║
        ║                           │ БЕЗ него Reality НЕ РАБОТАЕТ!     ║
        ╚══════════════════════════════════════════════════════════════╝

        ╔══════════════════════════════════════════════════════════════╗
        ║ 6. sni (Dest/Target)      │ 3X-UI → Inbounds → Reality        ║
        ║     ★ОБЯЗАТЕЛЬНО★        │    → Dest (ya.ru)                 ║
        ║                           │ БЕЗ него Reality НЕ РАБОТАЕТ!     ║
        ╚══════════════════════════════════════════════════════════════╝

        ╔══════════════════════════════════════════════════════════════╗
        ║ 7. profile_name           │ Email клиента из 3X-UI            ║
        ║                           │ "litva1-halltape"                 ║
        ╚══════════════════════════════════════════════════════════════╝
        ╚══════════════════════════════════════════════════════════════╝
        """

        # Фиксированные параметры (не меняются)
        # self.fixed_params = {
        #     'type': 'tcp',
        #     'encryption': 'none',
        #     'security': 'reality',
        #     'fp': 'chrome',
        #     'spx': '/',
        #     'flow': 'xtls-rprx-vision'
        # }

        server_params = self.server_params

        # ✅ НОВЫЙ ПОРЯДОК как в твоём примере (TLS вместо Reality):
        params_order = {
            'type': 'tcp',
            'encryption': 'none',
            'security': 'tls',  # Изменено с 'reality'
            'fp': 'chrome',
            'alpn': 'http%2F1.1',  # Добавлен новый параметр
            'flow': 'xtls-rprx-vision'
        }

        params_str = '&'.join(f"{k}={v}" for k, v in params_order.items())

        return f"vless://{client_uuid}@{host}:{vless_port}?{params_str}#{profile_name}"

    def login(self, username: str = None, password: str = None, two_factor: str = "") -> bool:
        """Авторизация в 3X-UI"""
        username = username or self.username
        password = password or self.password

        if not username or not password:
            logger.error("❌ Username/password не указаны!")
            return False

        url = f"{self.base_url}/login/"
        data = {
            'username': username,
            'password': password
        }
        if two_factor:
            data['twoFactorCode'] = two_factor

        try:
            logger.info(f"Попытка авторизации для пользователя: {username}")
            response = self.session.post(url, data=data, timeout=30)
            result = response.json()

            if result.get('success'):
                self.is_authenticated = True
                self.username = username
                self.password = password
                logger.info("✅ Авторизация успешна!")
                return True
            else:
                logger.error(f"❌ Ошибка авторизации: {result.get('msg', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            return False

    def add_client(self, inbound_id: str = "1", client_uuid: str = None, email: str = "",
                   total_gb: float = 0, limit_ip: int = 2, enable: bool = True,
                   comment: str = "", expiry_time: int = 0, flow: str = "xtls-rprx-vision") -> Optional[Dict[str, Any]]:
        """Добавить клиента"""
        final_id = client_uuid if client_uuid else self._generate_client_uuid()

        client_data = {
            "id": final_id,
            "flow": flow,
            "email": email or f"user_{inbound_id}_{int(time.time())}@example.com",
            "limitIp": limit_ip,
            "totalGB": total_gb,
            "expiryTime": expiry_time,
            "enable": enable,
            "tgId": "",
            "subId": f"sub-{int(time.time())}",
            "comment": comment,
            "reset": 0
        }

        logger.info(f"Добавление клиента {final_id[:8]}... в inbound {inbound_id}: {client_data['email']}")
        settings = json.dumps({"clients": [client_data]})
        data = {'id': inbound_id, 'settings': settings}
        result = self._make_request("inbounds/addClient", data=data)
        success = result.get('success', False)
        if success is True:
            new_result = result
            vless_link = self._generate_vless_link(client_uuid=final_id,
                                                   host=self.host,
                                                   profile_name=email)
            new_result["vless_link"] = vless_link
        else:
            new_result = result
            raise ValueError(new_result.get('msg'))

        return new_result

    def remove_client(self, client_id: str, inbound_id: str= "1") -> Optional[Dict[str, Any]]:
        """Удалить клиента из inbound"""
        logger.info(f"Удаление клиента {client_id[:8]}... из inbound {inbound_id}")
        settings = json.dumps({"clients": [{"id": client_id}]})
        data = {'id': inbound_id, 'settings': settings}
        # http: // localhost: 2053 / randompath / panel / api / inbounds / {inboundId} / delClient / {uuid}
        return self._make_request(f"inbounds/{inbound_id}/delClient/{client_id}", data=data)

    def update_client(self, inbound_id: str, client_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновить клиента"""
        logger.info(f"Обновление клиента в inbound {inbound_id}")
        settings = json.dumps({"clients": [client_data]})
        data = {'id': inbound_id, 'settings': settings}
        return self._make_request("inbounds/updateClient", data=data)

    def get_list_inbounds(self) -> Optional[Dict[str, Any]]:
        """Список всех inbounds"""
        logger.info("Получение списка inbounds")
        return self._make_request("inbounds/list", method="GET")

    def get_inbound(self, inbound_id: str) -> Optional[Dict[str, Any]]:
        """Информация об inbound"""
        logger.info(f"Получение inbound {inbound_id}")
        data = {'id': inbound_id}
        # https://illiriaakva.ru:28001/ylzqeXtdnca0tHr2ng/panel/api/inbounds/get/1
        # https://illiriaakva.ru:28001/ylzqeXtdnca0tHr2ng/panel/inbounds
        # https://155.212.228.65:49699/IIVMNd0IoCAcUBOuKK/panel/api/inbounds/get/1
        # http: // localhost: 2053 / randompath / panel / api / inbounds / get / {inboundId}
        return self._make_request(endpoint=f"inbounds/get/{inbound_id}", method="POST", data=data)

    def logout(self) -> bool:
        """Выход из системы"""
        self.is_authenticated = False
        self.session.cookies.clear()
        logger.info("👋 Сессия закрыта")
        return True



if __name__ == "__main__":
    base_url = "https://155.212.228.65:49699/9RWEJRPGmKLSZojNjB"
    expire_time = 86400
    USER = "sBcdl7KQt9"
    PASSWORD = "8Dgwr0u6Cw"
    # SEERVER PARAMS
    PUBLIC_KEY = "QZ63wahdkxh_n8HoY6M10zcGuT6Ig6-PDZh-sFBhAWo"

    SID = "482faa37e9"

    # port = int(base_url.split(":")[2].split("/")[0] )
    # print(port)
    # vless_client = XUIClient(base_url_from_panel=base_url,
    #                          username=USER,
    #                          password=PASSWORD,
    #                          verify_ssl = True,
    #                          public_inbound_key=PUBLIC_KEY,
    #                          sid=SID)

    # print(vless_client.add_client(email="NEW_TEST_USER",
    #                               inbound_id="1",
    #                               flow="xtls-rprx-vision",
    #                               expiry_time=1775505600000))

    # print(vless_client.add_client(email="Shu", inbound_id="1", flow="xtls-rprx-vision"))
    # pprint(vless_client.get_list_inbounds())

    # print(vless_client.add_client(email="TEST_SUKA_NAHUI_NEW",
    #                               expiry_time=1775505600000,
    #                               inbound_id="2").get('vless_link',"None"))

    # 🎯 ПРИМЕР использования:
    # link = generate_vless_link(
    #     uuid="678efafd-36c5-4263-9da7-995a9e44f621",
    #     profile_name="litva1-halltape",
    #     host="155.212.228.65",
    #     port=6443,
    #     public_inbound_key="lFJfqBItMEQ_cRFJxCsWor-oaUsPRBOBQPq24vCfojI",
    #     sid="d35ff639",
    #     sni="ya.ru"
    # )

