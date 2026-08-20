import random
from pprint import pprint
from urllib.parse import urlparse
import requests
import json
import time
import logging
import uuid
from typing import Dict, Any, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


class XUIClient:
    def __init__(self, base_url_from_panel: str = None,
                 public_inbound_key: str = None, sid: str = None, sni: str = "ya.ru",
                 username: str = None, password: str = None, two_factor: str = None,
                 api_token: str = None,
                 sub_path: str = ":2096/1AWEJRPGmKLSZojNjB",
                 verify_ssl: bool = False, auto_login: bool = True):

        if not base_url_from_panel:
            raise ValueError("base_url_from_panel is required")

        parsed = urlparse(base_url_from_panel.rstrip('/'))

        self.server_params = {
            'pbk': public_inbound_key,
            'sid': sid,
            'sni': sni
        }

        self.base_url = base_url_from_panel.rstrip('/')
        self.host = parsed.hostname
        self.port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        self.web_path = parsed.path.rstrip('/') if parsed.path else ''
        self.use_https = parsed.scheme == 'https'
        self.verify_ssl = verify_ssl
        self.sub_path = sub_path

        self.username = username
        self.password = password
        self.two_factor = two_factor

        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
        })
        self.session.verify = verify_ssl

        self.is_authenticated = False

        if api_token:
            self.login(api_token=api_token)

    def login(self, username: str = None, password: str = None, two_factor: str = "", api_token: str = None) -> bool:
        if api_token:
            self.api_token = api_token
            self.session.headers.update({
                "Authorization": f"Bearer {api_token}"
            })
            self.is_authenticated = True
            logger.info("✅ Авторизация по API token успешна!")
            return True

        logger.error("❌ Для этой версии клиента используется только api_token")
        return False

    def logout(self) -> bool:
        self.is_authenticated = False
        self.session.cookies.clear()
        self.session.headers.pop("Authorization", None)
        logger.info("👋 Сессия закрыта")
        return True

    def _make_request(self, endpoint: str, method: str = "POST", **kwargs) -> Optional[Dict[str, Any]]:
        if not self.is_authenticated:
            logger.warning("⚠️ Не авторизован!")
            return None

        url = f"{self.base_url}/panel/api/{endpoint.lstrip('/')}"
        logger.info(url)

        try:
            response = self.session.request(method.upper(), url, timeout=30, **kwargs)

            if response.status_code == 200:
                try:
                    return response.json()
                except Exception:
                    return {"success": True, "raw": response.text}

            logger.error(f"❌ HTTP {response.status_code}: {response.text}")
            return None

        except requests.RequestException as e:
            logger.error(f"❌ API Error {endpoint}: {e}")
            return None

    @staticmethod
    def _generate_client_uuid() -> str:
        return str(uuid.uuid4())

    def _generate_vless_link(self, client_uuid: str,
                             profile_name: str,
                             host: str,
                             vless_port: int = 443) -> str:
        params_order = {
            'type': 'tcp',
            'encryption': 'none',
            'security': 'tls',
            'fp': 'chrome',
            'alpn': 'http%2F1.1',
            'flow': 'xtls-rprx-vision'
        }
        params_str = '&'.join(f"{k}={v}" for k, v in params_order.items())
        return f"vless://{client_uuid}@{host}:{vless_port}?{params_str}#{profile_name}"

    def add_client(self, inbound_id: str = "1", client_uuid: str = None, email: str = "",
                   total_gb: float = 0, limit_ip: int = 3, enable: bool = True, sub_id: str = None,
                   comment: str = "", expiry_time: int = 0, flow: str = "xtls-rprx-vision") -> Optional[Dict[str, Any]]:
        final_id = client_uuid if client_uuid else self._generate_client_uuid()
        final_email = email or f"user_{inbound_id}_{int(time.time())}@example.com"
        # final_sub_id = sub_id or f"sub-{int(time.time()) + random.randint(1, 100)}"

        client_data = {
            "id": final_id,
            "email": final_email,
            "totalGB": int(total_gb)*(1024 ** 3),
            "expiryTime": expiry_time,
            "tgId": 0,
            "limitIp": limit_ip,
            "enable": enable,
            "subId": sub_id or "",
            "comment": comment,
            "flow": flow,
        }

        payload = {
            "client": client_data,
            "inboundIds": [int(inbound_id)]
        }

        logging.info(f"Добавление клиента {final_id[:8]}... в inbound {inbound_id}: {final_email}")

        result = self._make_request("clients/add", method="POST", json=payload)
        success = result.get('success', False)

        # if success is True:
        #     new_result = result
        #     vless_link = self._generate_vless_link(client_uuid=final_id,
        #                                            host=self.host,
        #                                            profile_name=email)
        #     new_result["vless_link"] = vless_link
        #     new_base_url_list = str(self.base_url).split(":")
        #     # sub_path: str = ":2096/1AWEJRPGmKLSZojNjB",
        #     new_result["subscription_link"] = (new_base_url_list[0]+":"
        #                                        +new_base_url_list[1]+self.sub_path
        #                                        +"/"+str(client_data.get("subId")))
        if success is True:
            new_result = result

            panel_client = self.get_client(final_email)

            # print(panel_client)

            if not panel_client:
                raise RuntimeError(
                    f"Клиент {final_email!r} создан, "
                    "но не удалось получить его данные из панели"
                )

            panel_sub_id = panel_client.get("subId")

            if not panel_sub_id:
                raise RuntimeError(
                    f"Панель не вернула subId для клиента {final_email!r}"
                )

            new_result["subId"] = panel_sub_id

            new_result["vless_link"] = self._generate_vless_link(
                client_uuid=panel_client.get("id", final_id),
                host=self.host,
                profile_name=final_email,
            )

            # sub_path: str = ":2096/1AWEJRPGmKLSZojNjB"
            # new_base_url_list = str(self.base_url).split(":")
            # new_result["subscription_link"] = (new_base_url_list[0]+":"
            #                                    +new_base_url_list[1]+self.sub_path
            #                                    +"/"+str(panel_sub_id))
            new_result["subscription_link"] = (
                f"{self.base_url.split(':', 1)[0]}:"
                f"{self.base_url.split(':', 2)[1]}"
                f"{self.sub_path}/{panel_sub_id}"
            )
        else:
            new_result = result
            raise ValueError(new_result.get('msg'))

        # raise ValueError(result.get("msg", "Unknown error"))

        return new_result

    def remove_client(self, client_id: str, inbound_id: str = "1") -> Optional[Dict[str, Any]]:
        logger.info(f"Удаление клиента {client_id[:8]}... из inbound {inbound_id}")
        # data = {'id': inbound_id, 'clientId': client_id}
        # //panel/api/clients/del/:email?keepTraffic=5404
        # return self._make_request(f"inbounds/{inbound_id}/delClient/{client_id}", method="POST", data=data)
        return self._make_request(endpoint=f"clients/del/{client_id}?keepTraffic=5404", method="POST")

    def update_client(self, inbound_id: str, client_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        logger.info(f"Обновление клиента в inbound {inbound_id}")
        payload = {
            "id": int(inbound_id),
            "client": client_data
        }
        return self._make_request("clients/update", method="POST", json=payload)

    def add_client_external_links(self, email: str, subscriptions_links: list[str]) -> Optional[Dict[str, Any]]:
        """
        Добавляет клиенту несколько внешних ссылок (подписок) одним запросом.

        :param email: email (имя) клиента
        :param subscriptions: список подписок, каждая — dict с полями:
            {
                "kind": "subscription",
                "value": "https://домен:порт/путь",
                "remark": ""  # опционально
            }

        :return: JSON-ответ от сервера (dict) или None при ошибке
        """
        subscriptions=[]
        for subscription_link in subscriptions_links:
            subscriptions.append(dict(kind="subscription",
                                      value=subscription_link,
                                      remark=""))
        # subscription_links = [
        #     {
        #         "kind": "subscription",
        #         "value": "https://origin.illiriaakva.online:2096/1AWEJRPGmKLSZojNjB/a3pk3drwrluo6q6d",
        #         "remark": "",
        #     },
        #     {
        #         "kind": "subscription",
        #         "value": "https://другой-домен:порт/путь",
        #         "remark": "backup",
        #     },
        # ]


        # logger.info(f"Добавление {len(subscriptions)} внешних ссылок для клиента {email}")
        logging.info(f"Добавление {len(subscriptions)} внешних ссылок для клиента {email}")
        payload = {
            "externalLinks": subscriptions
        }

        return self._make_request(endpoint=f"clients/{email}/externalLinks", method="POST", json=payload)

    def get_client(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Получает данные клиента 3X-UI по email.

        Возвращает именно объект клиента:
        {
            "id": 99,
            "email": "...",
            "subId": "...",
            "uuid": "...",
            ...
        }
        """
        email_encoded = quote(email, safe="")

        logger.info("Получение клиента по email: %s", email)

        response = self._make_request(
            endpoint=f"clients/get/{email_encoded}",
            method="GET",
        )

        if not response:
            return None

        if not response.get("success"):
            logger.warning(
                "Клиент %r не найден: %s",
                email,
                response.get("msg", "Unknown error"),
            )
            return None

        obj = response.get("obj")

        if not obj:
            logger.warning("3X-UI вернул пустой obj для %r", email)
            return None

        client = obj.get("client", obj)

        if not client:
            logger.warning("3X-UI не вернул данные клиента для %r", email)
            return None

        return client


    def get_client_traffic_by_id(self, client_uuid: str):
        # //panel/api/clients/get/:email
        endpoint = f"clients/get/{client_uuid}"

        # {'success': False, 'msg': ' (record not found)', 'obj': None}
        response = self._make_request(endpoint=endpoint, method="GET")
        sucsess = response.get('success', None)
        if sucsess:
            client_traffic_info = dict(obj=response.get("obj"))
        else:
            client_traffic_info = dict(obj=[])

        return client_traffic_info

    def get_list_inbounds(self) -> Optional[Dict[str, Any]]:
        logger.info("Получение списка inbounds")
        return self._make_request("inbounds/list", method="GET")

    def get_inbound(self, inbound_id: int) -> Optional[Dict[str, Any]]:
        logger.info(f"Получение inbound {inbound_id}")
        return self._make_request(endpoint=f"inbounds/get/{inbound_id}", method="GET")

    def get_client_ips(self, inbound_id: str, email: str) -> Optional[Dict[str, Any]]:
        logger.info(f"Получение clientIps для inbound {inbound_id}, email={email}")
        return self._make_request(method="POST", endpoint=f"inbounds/clientIps/{email}")

    def get_server(self) -> Optional[Dict[str, Any]]:
        logger.info("Получение server info")
        return self._make_request("server", method="GET")

    def get_nodes(self) -> Optional[Dict[str, Any]]:
        logger.info("Получение nodes")
        return self._make_request("nodes", method="GET")

    def get_custom_geo(self) -> Optional[Dict[str, Any]]:
        logger.info("Получение custom geo")
        return self._make_request("custom-geo", method="GET")

    def backup_to_tgbot(self) -> Optional[Dict[str, Any]]:
        logger.info("Отправка бэкапа в Telegram bot")
        return self._make_request("backuptotgbot", method="POST")







if __name__=="__main__":
    API_VLESS_TOKEN = "KAuYWOt5neJjJZIuPnbryp4x15MrDmEHYcihBDHFaVRdVlL2"

    BASE_URL = "https://connect.quantumturbovpn.com:49699/9RWEJRPGmKLSZojNjB"
    # "https://quantumturbovpn.ddns.net:49699/9RWEJRPGmKLSZojNjB"
    # client = XUIClient(
    #     base_url_from_panel="https://origin.illiriaakva.online:49699/9RWEJRPGmKLSZojNjB",
    #     api_token=API_VLESS_TOKEN,
    #     verify_ssl=True
    # )
    #


    client = XUIClient(
        base_url_from_panel=BASE_URL,
        api_token=API_VLESS_TOKEN,
        verify_ssl=True,

    )

    test_email = "SUKA__ZAEBALA_TRI_RAZA_TVAR100"

    result = client.add_client(
        inbound_id="2",
        email=test_email,
        total_gb=50,
        limit_ip=1,
        expiry_time=0,
    )

    pprint(result)

    # print(client.get_list_inbounds())

    # result = client.add_client(
    #     inbound_id="2",
    #     email="SUKA",
    #     total_gb=50 * 1024 * 1024 * 1024,
    #     limit_ip=1,
    #     expiry_time=1816239600000
    # )
    #
    # print(result)
    # print(result["vless_link"])
    # print(result["subscription_link"])
    # remove_client(self, client_id: str, inbound_id: str = "1")

    # print(client.remove_client(client_id="SUKA_TEST", inbound_id="2"))

    # print(client.get_client_traffic_by_id(client_uuid="SUKA_TEST"))
    #

    # link = client.add_client(client_uuid=client._generate_client_uuid(),
    #                                flow="xtls-rprx-vision",
    #                                inbound_id="2",
    #                                expiry_time=1816239600000,
    #                                email=f"SUKA_TEST").get('subscription_link')
    # print(link)


    # 'https://connect.quantumturbovpn.com:49699/9RWEJRPGmKLSZojNjB/f691370e-2335-4a7a-b194-b403d276b75f' GOVNO
    #
    # 'https://connect.quantumturbovpn.com:2096/1AWEJRPGmKLSZojNjB/f691370e-2335-4a7a-b194-b403d276b75f'
    #
    # 'https://connect.quantumturbovpn.com:2096/9RWEJRPGmKLSZojNjB/f691370e-2335-4a7a-b194-b403d276b75f'
    #
    # '/1AWEJRPGmKLSZojNjB/'