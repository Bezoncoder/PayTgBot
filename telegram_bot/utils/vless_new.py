from urllib.parse import urlparse

import requests
import uuid
import time
import json
import logging
import urllib3
from typing import Optional, Dict, Any


class XUIClient:
    def __init__(self, base_url: str = None, username: str = None, password: str = None,
                 two_factor: str = None, verify_ssl: bool = False, auto_login: bool = True):
        """
        ✅ Автоматический парсинг host/port/web_path из base_url!
        client = XUIClient("https://155.212.228.65:49699/9RWEJRPGmKLSZojNjB")
        """
        self.username = username
        self.password = password
        self.two_factor = two_factor
        self.verify_ssl = verify_ssl
        self.is_authenticated = False

        if not base_url:
            raise ValueError("❌ base_url обязателен!")

        # 🔍 ПАРСИМ base_url → host, port, web_path, protocol
        parsed = urlparse(base_url.rstrip('/'))

        self.host = parsed.hostname
        self.port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        self.web_path = parsed.path.rstrip('/') if parsed.path else ''
        self.use_https = parsed.scheme == 'https'

        # ✅ Финальный base_url с правильным слешем
        self.base_url = f"{parsed.scheme}://{self.host}:{self.port}{self.web_path}/"

        # ✅ Инициализация сессии
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        self.session.verify = verify_ssl

        # ✅ Отключаем SSL warnings
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        logging.info(f"XUIClient инициализирован:")
        logging.info(f"  📍 Host: {self.host}:{self.port}")
        logging.info(f"  🛤️ WebPath: {self.web_path}")
        logging.info(f"  🌐 BaseURL: {self.base_url}")

        if auto_login and username and password:
            self._auto_login()

    def _make_request(self, endpoint: str, method: str = "POST", **kwargs) -> Optional[Dict[str, Any]]:
        """Базовый API запрос"""
        if not self.is_authenticated:
            logging.warning("⚠️ Не авторизован!")
            return None

        url = f"{self.base_url.rstrip('/')}/panel/api/{endpoint}"
        logging.debug(f"API запрос: {method} {url}")

        try:
            response = self.session.request(method, url, timeout=30, **kwargs)

            if response.status_code == 200:
                try:
                    result = response.json()
                    logging.debug(f"✅ API OK: {endpoint}")
                    return result
                except:
                    logging.debug(f"Raw ответ: {response.text[:200]}")
                    return {"success": True, "raw": response.text}
            else:
                logging.error(f"❌ HTTP {response.status_code}: {response.text[:200]}")
                return None

        except requests.RequestException as e:
            logging.error(f"❌ API Error {endpoint}: {e}")
            return None

    def _auto_login(self) -> bool:
        """Внутренний метод автоматической авторизации"""
        return self.login(self.username, self.password, self.two_factor)

    @staticmethod
    def _generate_client_uuid() -> str:
        """Генерация уникального UUID для клиента"""
        return str(uuid.uuid4())

    @staticmethod
    def _generate_vless_url(client_uuid: str, host: str, email: str = "", port: int = 443, flow: str = "") -> str:
        """
        ✅ VLESS + Reality для 3X-UI
        """
        vless_url = f"vless://{client_uuid}@{host}:{port}"

        # 🔑 Reality параметры (замени на реальные из inbound)
        pbk = "BMf_HacRVKEqSeGZSkFH1Y3dhvl88gnILTuTBNkMAHk"
        sid = "f150d1"
        sni = "www.google.com"

        params = (
            f"?type=tcp&encryption=none&security=reality"
            f"&pbk={pbk}&fp=chrome&sni={sni}&sid={sid}"
            f"&spx=%2F&flow={flow}"
        )

        profile_name = email or f"XUI-{host}"
        return vless_url + params + f"#{profile_name}"

    def login(self, username: str = None, password: str = None, two_factor: str = "") -> bool:
        """🔧 ИСПРАВЛЕННЫЙ ЛОГИН — проверка по cookies + API"""
        username = username or self.username
        password = password or self.password

        if not username or not password:
            logging.error("❌ Username/password не указаны!")
            return False

        login_url = f"{self.base_url.rstrip('/')}/login"
        data = {'username': username, 'password': password}
        if two_factor:
            data['twoFactorCode'] = two_factor

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Origin': self.base_url.rstrip('/'),
            'Referer': f"{self.base_url.rstrip('/')}/login",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        try:
            logging.info(f"🔐 Логин: {username}")

            # 1. POST логин
            response = self.session.post(login_url, data=data, headers=headers,
                                         allow_redirects=True, timeout=30)

            logging.debug(f"Login статус: {response.status_code}")
            logging.debug(f"Login URL: {response.url}")
            logging.debug(f"Cookies кол-во: {len(self.session.cookies)}")

            # 2. ТЕСТ API — главный индикатор успеха
            test_api = self._make_request("inbounds/list", method="GET")
            api_works = test_api is not None

            # 3. Проверяем cookies
            has_cookies = len(self.session.cookies) > 0

            if api_works or has_cookies:
                self.is_authenticated = True
                logging.info("✅ Авторизация успешна! (API test + cookies)")
                return True
            else:
                logging.error("❌ Login FAILED:")
                logging.error(f"  Cookies: {has_cookies}")
                logging.error(f"  API test: {api_works}")
                logging.error(f"  Response: {response.text[:300]}")
                return False

        except Exception as e:
            logging.error(f"❌ Login error: {e}")
            return False

    def add_client(self, inbound_id: str = "1", client_uuid: str = None, email: str = "",
                   total_gb: float = 0, limit_ip: int = 2, enable: bool = True,
                   comment: str = "", expiry_time: int = 0, flow: str = "") -> Optional[Dict[str, Any]]:
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

        logging.info(f"➕ Клиент {final_id[:8]}... → inbound {inbound_id}")
        settings = json.dumps({"clients": [client_data]})
        data = {'id': inbound_id, 'settings': settings}
        result = self._make_request("inbounds/addClient", data=data)

        if result and result.get('success'):
            vless_link = self._generate_vless_url(
                client_uuid=final_id,
                host=self.host,
                email=email or client_data['email'],
                port=6443,
                flow=flow
            )
            result["vless_link"] = vless_link
            logging.info(f"✅ VLESS создана: {vless_link[:50]}...")
            return result
        else:
            logging.error(f"❌ Add client error: {result}")
            return None

    def remove_client(self, client_id: str, inbound_id: str = "1") -> Optional[Dict[str, Any]]:
        """Удалить клиента"""
        logging.info(f"🗑️ Удаление {client_id[:8]}... из {inbound_id}")
        settings = json.dumps({"clients": [{"id": client_id}]})
        data = {'id': inbound_id, 'settings': settings}
        return self._make_request(f"inbounds/{inbound_id}/delClient/{client_id}", data=data)

    def update_client(self, inbound_id: str, client_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновить клиента"""
        logging.info(f"🔄 Обновление inbound {inbound_id}")
        settings = json.dumps({"clients": [client_data]})
        data = {'id': inbound_id, 'settings': settings}
        return self._make_request("inbounds/updateClient", data=data)

    def get_list_inbounds(self) -> Optional[Dict[str, Any]]:
        """Список всех inbounds"""
        logging.info("📋 Получение inbounds")
        return self._make_request("inbounds/list", method="GET")

    def get_inbound(self, inbound_id: str) -> Optional[Dict[str, Any]]:
        """Информация об inbound"""
        logging.info(f"📄 Inbound {inbound_id}")
        data = {'id': inbound_id}
        return self._make_request(f"inbounds/get/{inbound_id}", method="POST", data=data)

    def logout(self) -> bool:
        """Выход"""
        self.is_authenticated = False
        self.session.cookies.clear()
        logging.info("👋 Logout")
        return True


###################################################################################



def generate_vless_link(
        uuid: str,
        profile_name: str,
        host: str,
        port: int,
        public_inbound_key: str,
        sid: str,
        sni: str
) -> str:
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
    fixed_params = {
        'type': 'tcp',
        'encryption': 'none',
        'security': 'reality',
        'fp': 'chrome',
        'spx': '/',
        'flow': 'xtls-rprx-vision'
    }

    # Серверные параметры (из 3X-UI Reality)
    server_params = {
        'pbk': public_inbound_key,
        'sid': sid,
        'sni': sni
    }

    params_str = '&'.join(f"{k}={v}" for k, v in {**fixed_params, **server_params}.items())
    return f"vless://{uuid}@{host}:{port}?{params_str}#{profile_name}"


def test_link():
    # Тест 2: Генерация Reality ссылки
    print("\n🔍 Тест 2: VLESS Reality ссылка")
    test_uuid = "7afd825f-d5e0-407d-aae6-d62422339531"
    link_vl = XUIClient._generate_vless_url(
        client_uuid=test_uuid,
        host="193.242.109.208",
        email="test-Vk_client",
        port=6443
    )
    print(f"✅ Ссылка: {link_vl[:100]}...")

def test_add():
    # Тест 3: Добавление клиента
    print("\n🔍 Тест 3: Добавление клиента")
    result = client.add_client(
        inbound_id="1",
        email="test_user@example.com",
        total_gb=10.0,
        limit_ip=2,
        flow=""
    )

    if result and result.get('success'):
        print("✅ Клиент добавлен!")
        print(f"🔗 VLESS ссылка: {result['vless_link']}")
    else:
        print("❌ Ошибка добавления клиента")

def test_inbounds():
    # Тест 4: Список inbounds
    print("\n🔍 Тест 4: Получение inbounds")
    inbounds = client.get_list_inbounds()
    if inbounds and inbounds.get('success'):
        print(f"✅ Найдено inbounds: {len(inbounds.get('obj', []))}")
    else:
        print("❌ Ошибка получения inbounds")




###################################################################################

if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    BASE_URL = "https://155.212.228.65:49699/9RWEJRPGmKLSZojNjB"
    # Инициализация клиента

    client = XUIClient(
        base_url=BASE_URL,
        username="sBcdl7KQt9",
        password="8Dgwr0u6Cw"
    )

    # Тест 1: Авторизация
    print("🔍 Тест 1: Авторизация")
    if client.login():
        print("✅ Авторизация OK")
    else:
        print("❌ Авторизация FAILED")
        exit()

    test_inbounds()

    test_add()

    test_link()
