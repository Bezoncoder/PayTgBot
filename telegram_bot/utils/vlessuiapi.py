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

import re


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
                 token: str = None,
                 sub_path: str = ":2096/1AWEJRPGmKLSZojNjB",
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
        self.token = token
        self.two_factor = two_factor
        self.verify_ssl = verify_ssl
        self.sub_path = sub_path
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
            # 'Authorization': f'Bearer {token}'

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
        print(url)
        logger.info(url)
        try:
            logger.debug(f"Запрос: {method} {endpoint}")
            # print(url)
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

    def login(self, username: str = None, password: str = None, two_factor: str = None, token: str = None) -> bool:
        """Авторизация в 3X-UI"""
        username = username or self.username
        password = password or self.password
        token  = token or self.token
        if not username or not password:
            logger.error("❌ Username/password не указаны!")
            return False

        url = f"{self.base_url}/login"
        # url = "https://quantumturbovpn.ddns.net:49699/login/"
        print(url)
        data = {
            'username': username,
            'password': password
        }

        payload_new = json.dumps({
            "username": username,
            "password": password

        })
        # headers = {
        #     'Content-Type': 'application/json',
        #     'Accept': 'application/json',
        #     'Authorization': f'Bearer {token}'
        # }
        print(payload_new)
        # print(headers)
        # response = requests.request("POST", url, headers=headers, data=payload)


        if two_factor:
            data['twoFactorCode'] = two_factor

        try:
            logger.info(f"Попытка авторизации для пользователя: {username}")
            print("LOGIN")
            # response = self.session.post(url, data=payload, timeout=30)
            # print(response)
            # result = response.json()
            # print(result)

            # base_url = "https://quantumturbovpn.ddns.net:49699/9RWEJRPGmKLSZojNjB/panel/"

            # Шаг 1: GET на /login — получаем страницу И cookie
            login_page_test = self.session.get(f"{base_url}/panel/", verify=True, allow_redirects=True)
            # "CSRF token: BiZMKckz4oSuUzYlWunL1W2VBaErZqyNAaqGlOge1F4"
            # 9_Vrh_FPCHTkv_ZIMUaHoTaSWOYC_l0DV7SmjqWLZAo
            print(f"Status GET: {login_page_test.status_code}")
            print(f"Content-Type: {login_page_test.headers.get('Content-Type')}")
            print(f"Cookies: {self.session.cookies.get_dict()}")

            # Шаг 2: Ищем CSRF-токен в разных местах
            csrf_token_find = None

            # Вариант А: meta-тег
            match_crf = re.search(r'meta name="csrf-token" content="([^"]+)"', login_page_test.text)
            if match_crf:
                csrf_token_find = match_crf.group(1)
                print(f"Found in meta tag: {csrf_token_find}")
                print("Вариант А: meta-тег")

            url_login = f"https://quantumturbovpn.ddns.net:49699/9RWEJRPGmKLSZojNjB/login"

            payload_new = json.dumps({
                "username": username,
                "password": password
            })

            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'x-csrf-token': csrf_token_find
            }


            response_login = self.session.post(url_login, headers=headers, data=payload_new, verify=True, allow_redirects=True)
            print(f"\nStatus POST: {response_login.status_code}")
            print(f"Response: {response_login.text}")
            print(f"Cookies после логина: {self.session.cookies.get_dict()}")
            result = response_login.json()
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
                   total_gb: float = 0, limit_ip: int = 2, enable: bool = True, sub_id: str = None,
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
            "subId": sub_id or f"sub-{int(time.time())}",
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
            new_base_url_list = str(self.base_url).split(":")
            # sub_path: str = ":2096/1AWEJRPGmKLSZojNjB",
            new_result["subscription_link"] = (new_base_url_list[0]+":"
                                               +new_base_url_list[1]+self.sub_path
                                               +"/"+str(client_data.get("subId")))
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
        rez = self._make_request(f"inbounds/{inbound_id}/delClient/{client_id}", data=data)

        if rez:
            status=dict(client_id=client_id,
                        status=rez)
        else:
            status = {}

        return status

    def update_client(self, inbound_id: str, client_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновить клиента"""
        logger.info(f"Обновление клиента в inbound {inbound_id}")
        settings = json.dumps({"clients": [client_data]})
        data = {'id': inbound_id, 'settings': settings}
        return self._make_request("inbounds/updateClient", data=data)

    def get_client_traffic_by_id(self, client_uuid: str):
        # panel / api / inbounds / getClientTrafficsById / {uuid}
        endpoint = f"inbounds/getClientTrafficsById/{client_uuid}"
        # "https://quantumturbovpn.ddns.net:49699/9RWEJRPGmKLSZojNjB/panel/api/inbounds/getClientTrafficsById/63130ad0-c089-4b5a-a7e4-33bb1e671c24"
        payload = {}
        headers = {
            'Accept': 'application/json'
        }

        return self._make_request(endpoint=endpoint, data=payload, method="GET")

    def get_list_inbounds(self) -> Optional[Dict[str, Any]]:
        """Список всех inbounds"""
        logger.info("Получение списка inbounds")
        return self._make_request("inbounds/list", method="GET")

    def get_inbound(self, inbound_id: int) -> Optional[Dict[str, Any]]:
        """Информация об inbound"""
        logger.info(f"Получение inbound {inbound_id}")
        data = {}
        # https://illiriaakva.ru:28001/ylzqeXtdnca0tHr2ng/panel/api/inbounds/get/1
        # https://illiriaakva.ru:28001/ylzqeXtdnca0tHr2ng/panel/inbounds
        # https://155.212.228.65:49699/IIVMNd0IoCAcUBOuKK/panel/api/inbounds/get/1
        # http: // localhost: 2053 / randompath / panel / api / inbounds / get / {inboundId}
        # url = f"{self.base_url}/panel/api/{endpoint}"
        # inbounds / get / {inboundId}
        # / panel / api / inbounds

        return self._make_request(endpoint=f"inbounds/get/{inbound_id}", method="GET", data=data)

    def logout(self) -> bool:
        """Выход из системы"""
        self.is_authenticated = False
        self.session.cookies.clear()
        logger.info("👋 Сессия закрыта")
        return True

    def get_client_ips(self, inbound_id: str, email: str) -> Optional[Dict[str, Any]]:
        """GET /panel/api/inbounds/1/clientIps/TEST_ODIN_SUKANAHUI"""
        # url = f"{self.base_url}/panel/api/inbounds/{inbound_id}/clientIps/{email}"
        # /clientIps/:email

        # url = "http://localhost:2053/randompath/panel/api/inbounds/clientIps/s729v2km"
        #
        # payload = {}
        # headers = {
        #     'Accept': 'application/json'
        # }
        #
        # response = requests.request("POST", url, headers=headers, data=payload)
        return self._make_request(method="POST", endpoint=f"inbounds/clientIps/{email}")



if __name__ == "__main__":

    # url = "https://quantumturbovpn.ddns.net:49699/9RWEJRPGmKLSZojNjB"
    # # url = "https://quantumturbovpn.ddns.net:49699/9RWEJRPGmKLSZojNjB/panel/login"
    #945960

    # payload = json.dumps({
    #     "username": "sBcdl7KQt9",
    #     "password": "8Dgwr0u6Cw",
    #     "twoFactorCode": "274817"
    # })
    # headers = {
    #     'Content-Type': 'application/json',
    #     'Accept': 'application/json'
    #     # 'Authorization': 'Bearer 2FC9ZcLPIJiRpHNeMDzCvwQiTKwcw5JZt6trDSd21kpuG1iG'
    # }
    #
    #
    #
    # response = requests.request("POST", url, headers=headers, data=payload)
    # print(response.status_code)
    # print(response.text)
    #
    # import requests
    # import json
    # import re
    #
    # session = requests.Session()
    #
    # base_url = "https://quantumturbovpn.ddns.net:49699/9RWEJRPGmKLSZojNjB/panel/"
    #
    # # Шаг 1: GET на /login — получаем страницу И cookie
    # login_page = session.get(f"{base_url}", verify=True, allow_redirects=True)
    # # "CSRF token: BiZMKckz4oSuUzYlWunL1W2VBaErZqyNAaqGlOge1F4"
    # # 9_Vrh_FPCHTkv_ZIMUaHoTaSWOYC_l0DV7SmjqWLZAo
    # print(f"Status GET: {login_page.status_code}")
    # print(f"Content-Type: {login_page.headers.get('Content-Type')}")
    # print(f"Cookies: {session.cookies.get_dict()}")
    #
    # # Шаг 2: Ищем CSRF-токен в разных местах
    # csrf_token = None
    #
    # # Вариант А: meta-тег
    # match = re.search(r'meta name="csrf-token" content="([^"]+)"', login_page.text)
    # if match:
    #     csrf_token = match.group(1)
    #     print(f"Found in meta tag: {csrf_token}")
    #     print( "Вариант А: meta-тег")
    #
    # url = f"https://quantumturbovpn.ddns.net:49699/9RWEJRPGmKLSZojNjB/login"
    #
    # payload = json.dumps({
    #     "username": "sBcdl7KQt9",
    #     "password": "8Dgwr0u6Cw"
    # })
    #
    # response = session.post(url, headers=headers, data=payload, verify=True, allow_redirects=True)
    # print(f"\nStatus POST: {response.status_code}")
    # print(f"Response: {response.text}")
    # print(f"Cookies после логина: {session.cookies.get_dict()}")


    # # Вариант Б: hidden input с name="csrf-token" или name="_csrf"
    # if not csrf_token:
    #     match = re.search(r'name=["\']csrf-token["\']\s+value=["\']([^"\']+)["\']', login_page.text)
    #     if match:
    #         csrf_token = match.group(1)
    #         print(f"Found in input (csrf-token): {csrf_token}")
    #
    # if not csrf_token:
    #     match = re.search(r'name=["\']_csrf["\']\s+value=["\']([^"\']+)["\']', login_page.text)
    #     if match:
    #         csrf_token = match.group(1)
    #         print(f"Found in input (_csrf): {csrf_token}")
    #
    # # Вариант В: CSRF из cookie (csrftoken, XSRF-TOKEN, csrf)
    # if not csrf_token:
    #     csrf_token = session.cookies.get('csrftoken') or session.cookies.get('csrf') or session.cookies.get(
    #         'XSRF-TOKEN')
    #     if csrf_token:
    #         print(f"Found in cookie: {csrf_token}")
    #
    # # Если токен всё равно не найден — пробуем без CSRF
    # if not csrf_token:
    #     print("CSRF token не найден, пробуем без него!")
    #     headers = {
    #         'Content-Type': 'application/json',
    #         'Accept': 'application/json'
    #     }
    # else:
    #     print(f"CSRF token: {csrf_token}")
    #     headers = {
    #         'Content-Type': 'application/json',
    #         'Accept': 'application/json',
    #         'x-csrf-token': csrf_token
    #     }
    # headers = {
    #     'Content-Type': 'application/json',
    #     'Accept': 'application/json',
    #     'x-csrf-token': csrf_token
    # }
    # # Шаг 3: POST на /login
    # url = f"https://quantumturbovpn.ddns.net:49699/9RWEJRPGmKLSZojNjB/login"
    #
    # payload = json.dumps({
    #     "username": "sBcdl7KQt9",
    #     "password": "8Dgwr0u6Cw"
    # })
    #
    # response = session.post(url, headers=headers, data=payload, verify=True, allow_redirects=True)
    # print(f"\nStatus POST: {response.status_code}")
    # print(f"Response: {response.text}")
    # print(f"Cookies после логина: {session.cookies.get_dict()}")

    # Если ответ 200 — проверяем, вошли ли мы
    # if response.status_code == 200:
    #     try:
    #         data = response.json()
    #         print(f"JSON: {data}")
    #     except:
    #         print("Ответ не JSON, текст:", response.text)




    base_url = "https://quantumturbovpn.ddns.net:49699/9RWEJRPGmKLSZojNjB"

    expire_time = 86400
    USER = "sBcdl7KQt9"
    PASSWORD = "8Dgwr0u6Cw"
    # SEERVER PARAMS
    PUBLIC_KEY = "QZ63wahdkxh_n8HoY6M10zcGuT6Ig6-PDZh-sFBhAWo"

    # vless_user_name = "8edc1e1a-5673-4fad-a5b3-43f13966d66f"
    # TOKEN_NEW = "2FC9ZcLPIJiRpHNeMDzCvwQiTKwcw5JZt6trDSd21kpuG1iG"
    # SID = "482faa37e9"

    # "vless_link': 'vless://a400fbb6-fa9b-447c-8575-a4a1828425cf@illiriaakva.ru:443?type=tcp&encryption=none&security=tls&fp=chrome&alpn=http%2F1.1&flow=xtls-rprx-vision#aaaaff111fkkkk"
    # "https://illiriaakva.ru:49699/9RWEJRPGmKLSZojNjB"
    # "https://illiriaakva.ru:2096/9RWEJRPGmKLSZojNjB/sub-1775848081"



    client_mew = XUIClient(base_url_from_panel=base_url,
                           username=USER,
                           password=PASSWORD)
    # pprint(client_mew.add_client(email="NEW_TEST0999007TestT").get("subscription_link"))
    # pprint(client_mew.get_list_inbounds())
    pprint(client_mew.get_inbound(inbound_id=1))
    # uuid = '8edc1e1a-5673-4fad-a5b3-43f13966d66f'
    # print(client_mew.get_list_inbounds())
    # print(client_mew.get_client_ips(inbound_id="1", email="8edc1e1a-5673-4fad-a5b3-43f13966d66f"))
    # pprint(client_mew.remove_client(client_id="8edc1e1a-5673-4fad-a5b3-43f13966d66f"))

    # # {'msg': '', 'obj': [], 'success': True}
    # obj = client_mew.get_client_traffic_by_id(client_uuid=uuid).get("obj")
    #
    # if isinstance(obj, list) and not obj:
    #     print("Вернулся пустой список")
    # else:
    #     print("Это не пустой список")
    #     pprint(obj)


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
    # vless://8edc1e1a-5673-4fad-a5b3-43f13966d66f@quantumturbovpn.ddns.net:443?type=tcp&encryption=none&security=tls&fp=chrome&alpn=http%2F1.1&sni=google.com&flow=xtls-rprx-vision#litva1-911699354_8edc1e1a-5673-4fad-a5b3-43f13966d66f
    # print(vless_client.get_client_ips(inbound_id="1",email="litva1-911699354_8edc1e1a-5673-4fad-a5b3-43f13966d66f"))
    # print(vless_client.add_client(client_uuid="smndas,mnc,ansc",
    #                                        flow="xtls-rprx-vision",
    #                                         limit_ip=1,
    #                                        inbound_id="1",
    #                                        email=f"TEST_ODIN_SUKA_ODIN").get('vless_link'))
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







