from urllib.parse import urlencode, urlunparse

from pprint import pprint
from typing import Optional, Dict, Any, List
from datetime import datetime
import requests
import json

"""
О сервисе.

С помощью API банка вы можете работать с интернет-банком прямо из своего сервиса:

    Получать список счетов, подключённых к аккаунту
    Получать выписки по счёту
    Создавать черновики платёжек на подпись
    Получать вебхуки о входящих и исходящих платежах
    Подписывать платежи из интегрированного сервиса
    Регистрироваться в Системе быстрых платежей (СБП), создавать QR-коды, отслеживать оплаты по ним и делать возвраты
    Получать балансы счетов
    Создавать счета и закрывающие документы
    Создавать платёжные ссылки для приёма оплаты по карте и/или СБП
    
    Авторизация по JWT-токену
    
    JSON web token (JWT) — это уникальный токен с зашифрованной в нём информацией. С помощью него ваше приложение 
        получает доступ к ресурсам интернет-банка по API.
    
    Авторизация с помощью JWT проще, чем по OAuth 2.0: вы просто генерируете токен в интернет-банке, 
        задаёте время его жизни (TTL) и права доступа, а затем используете его в заголовках запросов.
       
       
    Авторизация по OAuth 2.0
    
    get_authorisation(client_id, client_secret) -> access_token
        -> set_consents(access_token) -> consent_id
        -> get_authorisation_link(client_id, consent_id) -> Link
        -> после успешной регистрации по Link выдаст code= в параметрах перехода
        -> get_acses_token(code, client_id, client_secret) -> token
   
"""


class TB:
    def check_payment(self):
        return False


tochka_bank = TB


def get_authorisation(client_id, client_secret):
    url = 'https://enter.tochka.com/connect/token'
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
        'scope': 'accounts balances customers statements sbp payments'
    }

    response = requests.post(url, data=data)
    print(response.status_code)
    print(response.json())

    return


def set_consents(access_token_local):
    headers = {
        'Authorization': f'Bearer {access_token_local}',
        'Content-Type': 'application/json',
    }

    json_data = {
        'Data': {
            'permissions': [
                'ReadAccountsBasic',
                'ReadAccountsDetail',
                'MakeAcquiringOperation',
                'ReadAcquiringData',
                'ReadBalances',
                'ReadStatements',
                'ReadCustomerData',
                'ReadSBPData',
                'EditSBPData',
                'CreatePaymentForSign',
                'CreatePaymentOrder',
                'ManageWebhookData',
                'ManageInvoiceData',
            ],
        },
    }

    response = requests.post('https://enter.tochka.com/uapi/v1.0/consents', headers=headers, json=json_data)
    pprint(response.json())
    return


def get_authorisation_link(client_id_local, consent_id_local):
    base_url = 'https://enter.tochka.com/connect/authorize'

    # client_id — идентификатор клиента;
    # response_type — код авторизации;
    # state — произвольная строка (подойдёт для связи запроса и ответа, то есть идентификации клиента);
    # redirect_uri — URI, предварительно зарегистрированный на авторизационном сервере.
    # На него перенаправим пользователя;
    # scope — accounts balances customers statements sbp payments acquiring то есть запрашиваемая область действия токена доступа;
    # consent_id — id разрешения из ответа с предыдущего шага.

    uri = 'https://vk.com/roadmappers'
    params = {
        'client_id': client_id_local,
        'response_type': 'code',
        'state': 'roadmappers',
        'redirect_uri': uri,
        'scope': 'accounts balances customers statements sbp payments',
        'consent_id': consent_id_local,
    }

    query_string = urlencode(params, safe=' ')

    # urlencode заменит пробелы %20, так что можно оставить safe как пустую строку:
    query_string = urlencode(params)

    url = f"{base_url}?{query_string}"

    print(url)


def get_access_token(code, client_id, client_secret, redirect_uri):
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'authorization_code',
        'scope': 'accounts balances customers statements sbp payments',
        'code': code,
        'redirect_uri': redirect_uri,
    }

    response = requests.post('https://enter.tochka.com/connect/token', data=data)
    pprint(response.json())
    return


def get_token_hybrid(access_token):
    data = {
        'access_token': access_token,
    }

    response = requests.post('https://enter.tochka.com/connect/introspect', data=data)

    pprint(response.json())
    return


def get_payment_link(token: str, customer_code: int, payment_link_id: str, product_name: str,
                     amount: float = 0, purpose: str = "Назначение Платежа", quantity: int = 1) -> dict | Exception:
    """
    Create Payment Operation With Receipt

    https://developers.tochka.com/docs/tochka-api/api/create-payment-operation-with-receipt-acquiring-v-1-0-payments-with-receipt-post

    Метод для создания ссылки на оплату и отправки чека

    :param purpose:
    :param product_name:
    :param amount:
    :param quantity:
    :param payment_link_id:
    :param token:
    :param customer_code:
    :return:

    """


    url = "https://enter.tochka.com/uapi/acquiring/v1.0/payments_with_receipt"

    payload = json.dumps({
        "Data": {
            "customerCode": f"{customer_code}",
            "amount": f"{amount}",
            "purpose": f"{purpose}",
            "paymentMode": [
                "sbp",
                "card",
                "tinkoff",
                "dolyame"
            ],

            "paymentLinkId": f"{payment_link_id}",
            "taxSystemCode": "osn",
            "Client": {
                "name": "Иванов Иван Иванович",
                "email": "ivanov@mail.com"
            },
            "Items": [
                {
                    "name": f"{product_name}",
                    "amount": f"{amount}",
                    "quantity": f"{quantity}"
                }
            ]
        }
    })
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    #
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        response.raise_for_status()
        # print(response.text)
        link = response.json().get("Data")
    except Exception as e:
        return e

    return link


def get_payment_operation_info(token: str, operation_id: str) -> dict:

    """

    Get Payment Operation Info

    Метод для получения информации о конкретной операции

    :param token:
    :param operation_id:
    :return:

    # 'status': 'APPROVED',

    {"Data":
        {"Operation":[{"customerCode":"305352162",
                        "taxSystemCode":"osn",
                        "createdAt":"2025-12-09T19:59:59+05:00",
                        "paymentMode":["sbp","card","tinkoff","dolyame"],
                        "Client":{"name":"Иванов Иван Иванович", "email":"ivanov@mail.com"},
                        "Items":[{"name":"BOOTCAMP","amount":10.0,"quantity":1.0,"measure":"шт."}],
                        "purpose":"Назначение Платежа",
                        "amount":10.0,
                        "status":"CREATED",
                        "operationId":"157b9069-9efb-4e2e-966f-0f56414f1ba5",
                        "paymentLink":"https://merch.tochka.com/order/?uuid=157b9069-9efb-4e2e-966f-0f56414f1ba5",
                        "consumerId":"328656ef-8ea4-4647-8711-45dd6c117a26",
                        "Order":[],
                        "paymentLinkId":"djd2hssdh"
                        }
                        ]
        },
    "Links":{"self":"https://enter.tochka.com/uapi/acquiring/v1.0/payments/157b9069-9efb-4e2e-966f-0f56414f1ba5"},
    "Meta":{"totalPages":1}
    }


    """


    url = f"https://enter.tochka.com/uapi/acquiring/v1.0/payments/{operation_id}"

    payload = {}
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    pprint(response.json())

    return response.json()

def get_balance_info(token, account_id):
    """
    Get Balance Info
    https://developers.tochka.com/docs/tochka-api/api/get-balance-info-open-banking-v-1-0-accounts-account-id-balances-get

    Метод для получения информации о балансе конкретного счёта

    accountId – это номер расчётного счёта и БИК Точки, разделённые через слеш

    :param token:
    :param account_id:
    :return:

    """

    url = f"https://enter.tochka.com/uapi/open-banking/v1.0/accounts/{account_id}/balances"
    payload = {}
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    try:
        response = requests.request("GET", url=url, headers=headers, data=payload)
        balance_info = response.json()
        # print(response.json())
    except Exception as e:
        print(e)
        return e

    return balance_info


def get_customer_list(token):
    """
        Get Customers List

        Метод для получения списка доступных клиентов

        https://developers.tochka.com/docs/tochka-api/api/get-customers-list-open-banking-v-1-0-customers-get

        Необходимо вызвать метод Get Customers List и взять значение customerCode,
        опираясь на customerType: Business, а не Personal.

    """

    url = "https://enter.tochka.com/uapi/open-banking/v1.0/customers"

    payload = {}
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    try:
        response = requests.request("GET", url, headers=headers, data=payload)
        customer_info = response.json()
    except Exception as e:
        print(e)
        return None

    return customer_info



if __name__ == '__main__':

    # code = 'e57e296527b1876262b91bb9fb9995aac41afde0a65fda3c3706296d80c275a3'
    # consentId = '3932ed76-5ccf-4b5f-81dd-37f8a2ce3ad6'
    # uri = 'https://vk.com/roadmappers'
    # access_token_loc = 'NjY4YWExNmYwNzcxNGQ1Njk3NGFmNWRiYjkwNjAxNTQ='
    # client_id = '668aa16f07714d56974af5dbb9060154'
    # client_secret = '6f8eab6007d64d3388d7ee9f2eb00fe7'

    # get_authorisation(client_id=client_id, client_secret=client_secret)
    # {'token_type': 'bearer', 'access_token': 'NjY4YWExNmYwNzcxNGQ1Njk3NGFmNWRiYjkwNjAxNTQ=', 'expires_in': 86400}

    # set_consents(access_token_local=access_token_loc)
    # get_authorisation_link(client_id_local=client_id, consent_id_local=consentId)
    # https://vk.com/roadmappers?code=&application=668aa16f07714d56974af5dbb9060154&state=roadmappers

    # get_acses_token(code=code, client_id=client_id, client_secret=client_secret)

    # {'access_token': 'aac744dc9fb842d5b7110881806298c9',
    #  'expires_in': 86400,
    #  'refresh_token': 'f09277df7f204437a21fb2284d200118',
    #  'state': 'roadmappers',
    #  'token_type': 'bearer',
    #  'user_id': '1ee6b98c-d97d-440d-a68c-db7a61ff5b09'}
    TOKEN_TOCHKA_BANK = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI3MzVlNDczM2E2MTAzMTkzODE2MjAzMGYwNWNmZTI2OSIsInN1YiI6IjFlZTZiOThjLWQ5N2QtNDQwZC1hNjhjLWRiN2E2MWZmNWIwOSIsImN1c3RvbWVyX2NvZGUiOiIzMDUzNTY3NjUifQ.PD5VKjXkTQZGTlfAUVZdu2D3ny6P2l0r1FBANCXgxaFr3DcLN2pOMYfpMnXTpdDWF6OrAn2hwDN76-ZEB8k3sUajIBB4iSEmXJWGLIJscK7xMRPymIOUipT3vnq_G_rkbeFgVd7sRclSoxHXMjoqKD58CGzt9tuWBlHUHLj9PaYfBXGUenpTR5E5IbrFikcLyYzqNOvikLlovdkiLQU5NNwgtsdKsaOqztNW4zxhmWoNNH4EGjFD8qDM0ucHDoHT4_EiVgRBAn5uHOG1TPP02DQuJA0gBv8PRWfR6h4h9h3tRv9DTVXSutXNEHXFMvvjdTUZrUQTeLHlu6Ki0lKQJIiYnmTjjRV2LIhJGQefsW_W_7hqHOXwptfYrBhTafDHflZzz1ilaHkv0RbidhdrK5h3V7iZQjQRBJP0L305-QTqSw5lm6KfkY0YS8UCf8TRb0wC3dfRzcqXPHG1r6JPDZASLqAHDS9u_2fa6ZUIV2miSxhfT8Hp2J9X1ymgo12Y'
    customer_сode = 305352162
    accountid = '40802810220000801577/044525104'
    redirect_url = 'https://vk.com/roadmappers'
    # get_payment_link(token=TOKEN_FROM_SHUST, customer_code=customer_сode)

    # print(get_balance_info(token=TOKEN_TOCHKA_BANK, account_id=accountid))

    # print(get_payment_link(token=TOKEN_TOCHKA_BANK,
    #                        customer_code=customer_сode,
    #                        payment_link_id='djd2hssdh',
    #                        product_name='BOOTCAMP',
    #                        amount=10.00))

    get_payment_operation_info(token=TOKEN_TOCHKA_BANK, operation_id='157b9069-9efb-4e2e-966f-0f56414f1ba5')




    # set_consents(access_token_local=access_token_loc)
    # get_balanse_info(token_local=TOKEN_THE_BEST)
    # get_customer_code(token=TOKEN_THE_BEST)
# {'purpose': 'Назначение Платежа',
# 'status': 'CREATED',
# 'amount': 10.0,
# 'operationId': '157b9069-9efb-4e2e-966f-0f56414f1ba5',
# 'paymentLink': 'https://merch.tochka.com/order/?uuid=157b9069-9efb-4e2e-966f-0f56414f1ba5',
# 'consumerId': '328656ef-8ea4-4647-8711-45dd6c117a26',
# 'ttl': 10080,
# 'paymentLinkId': 'djd2hssdh',
# 'paymentMode': ['sbp', 'card', 'tinkoff', 'dolyame'],
# 'customerCode': '305352162',
# 'taxSystemCode': 'osn',
# 'Client': {'name': 'Иванов Иван Иванович', 'email': 'ivanov@mail.com'},
# 'Items': [{'name': 'BOOTCAMP', 'amount': 10.0, 'quantity': 1.0, 'measure': 'шт.'}]}