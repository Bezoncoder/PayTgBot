# pip install pyopenssl

import os
import random
import uuid
import json
from OpenSSL import crypto
import datetime as DT

"""

get_signed_cert(cert_dir:str, user_id:int, expiretime:int, filename: str | None = None)->str

Генерирует сертификат <filename>.ovpn и возвращает полный путь до файла.

"""


DEFAULT_REMOTE_HOST = "5.188.158.179"
DEFAULT_REMOTE_PORT = 1194
DEFAULT_PROTO = "tcp"


def _load_cert_profile(cert_dir: str) -> dict:
    """Load per-product VPN profile from config.json if present."""

    config_path = os.path.join(os.path.abspath(cert_dir), "config.json")
    if not os.path.exists(config_path):
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        # Ignore malformed config and fall back to defaults
        return {}


def _read_tls_auth_key(cert_dir: str, config: dict) -> str:
    """Return tls-auth key string either from file or config override."""

    key_file = config.get("tls_auth_key_file")
    if key_file:
        path = os.path.join(os.path.abspath(cert_dir), key_file)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()

    key_value = config.get("tls_auth_key")
    if isinstance(key_value, str) and key_value.strip():
        return key_value.strip()

    return DEFAULT_TLS_AUTH_KEY.strip()


# Default tls-auth key (InfraSharing)
DEFAULT_TLS_AUTH_KEY = """
bb88b164babea978608d6002e3eac394
b3eae11e24ac7408a2f0a1f18a2a2fff
43209ad31012a54abf2b55475dd2e6a0
50a239ebddb56722257ac5079313a3e1
f24dacc135fb0733b4e0cb318b87a756
e1f559161877cc10cc9a1065390935e4
97ee1f069ec9385005b6888c571114e6
46bf642fa312bd23a133b7a097022dcd
54bfb5c2b6c3068df0f234b5b5a29b15
57135955038d6cd9ca92bdbe1c8b2c07
b4478343a86c7ebe8e2d248e62c1b2db
c00aeae50738b09070cdc2e56a394b55
7d4514310eaf5cace68ff21082017d32
95e2659f121a822f97c24b0bb5f01cfb
42f8f36e6538a6f770fd633ed05f52f6
80bc2f9e71a728934634ec5f797f0ae4
"""


def get_signed_cert(
    cert_dir: str,
    user_id: int,
    expiretime: int,
    filename: str | None = None,
) -> str:

    # Profile controls remote/proto/tls-auth key per product
    profile = _load_cert_profile(cert_dir)

    CA_CRT = os.path.abspath(f"{cert_dir}/ca.pem").replace("utils", "")
    CA_KEY = os.path.abspath(f"{cert_dir}/ca.key").replace("utils", "")

    #  Загружаем промежуточный сертификат для подписи
    with open(CA_CRT) as ca_file:
        ca_pem = ca_file.read().strip()
        ca_cert = crypto.load_certificate(crypto.FILETYPE_PEM, ca_pem)

    #  Загружаем промежуточный ключ, последний параметр пароль
    with open(CA_KEY) as ca_key_file:
        ca_key = crypto.load_privatekey(
            crypto.FILETYPE_PEM, ca_key_file.read(), "".encode("utf-8")
        )

    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 2048)  # размер может быть 2048, 4196

    cert = crypto.X509()
    cert.get_subject().C = "RU"  #  указываем свои данные
    cert.get_subject().ST = "Moscow"  #  указываем свои данные
    cert.get_subject().L = "Moscow"  #  указываем свои данные
    cert.get_subject().O = "infrasharing.ru"  #  указываем свои данные
    cert.get_subject().OU = "infrasharing"  #  указываем свои данные
    cert.get_subject().CN = (
        f"user-{uuid.uuid4().hex[:8]}.infrasharing.local"  #  указываем свои данные
    )
    cert.set_serial_number(random.getrandbits(64))
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(expiretime)  #  срок "жизни" сертификата в секундах
    cert.set_issuer(ca_cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(ca_key, "sha256")

    abs_path = os.path.abspath(f"{cert_dir}").replace("utils", "")
    name = filename or f"InfraSharing_DE_{user_id}.ovpn"
    if not name.endswith(".ovpn"):
        name = f"{name}.ovpn"
    path_to_cert = os.path.join(abs_path, name)

    remote_host = profile.get("remote_host", DEFAULT_REMOTE_HOST)
    remote_port = int(profile.get("remote_port", DEFAULT_REMOTE_PORT))
    proto = profile.get("proto", DEFAULT_PROTO)

    tls_auth_key = _read_tls_auth_key(cert_dir, profile)

    with open(path_to_cert, "w") as f:
        f.write(
            f"""client
resolv-retry infinite
nobind
remote {remote_host} {remote_port}
proto {proto}
dev tun
comp-lzo
tls-client
float
keepalive 10 120
persist-key
persist-tun
tun-mtu 1450
mssfix 1410
cipher AES-256-GCM
verb 3
route 172.24.0.1 255.255.255.255
dhcp-option DOMAIN local
dhcp-option ADAPTER_DOMAIN_SUFFIX local
dhcp-option DOMAIN infrasharing.ru
dhcp-option ADAPTER_DOMAIN_SUFFIX infrasharing.ru

<ca>
{ca_pem}
</ca>

<cert>
{crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode('utf-8')}
</cert>
<key>
{crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode('utf-8')}
</key>
<tls-auth>
#
# 2048 bit OpenVPN static key
#
-----BEGIN OpenVPN Static key V1-----
{tls_auth_key}
-----END OpenVPN Static key V1-----
</tls-auth>

key-direction 1

#up /etc/openvpn/update-resolv-conf
#down /etc/openvpn/update-resolv-conf
"""
        )
        return path_to_cert


if __name__ == "__main__":
    current_directory = "source/certs/infrasharing"
    path = get_signed_cert(
        cert_dir=current_directory, user_id=11115555, expiretime=60 * 60 * 24 * 365 * 1
    )
    print(path)
