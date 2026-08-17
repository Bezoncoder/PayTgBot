from pprint import pprint

import requests


class AlphaPay:
    url_get_order_status = 'https://alfa.rbsuat.com/payment/rest/getOrderStatusExtended.do'
    url_get_link = 'https://alfa.rbsuat.com/payment/rest/register.do'

    def __init__(self, alpha_token, alpha_login, alpha_password):
        self.alpha_token = alpha_token
        self.alpha_login = alpha_login
        self.alpha_password = alpha_password

    def get_pay_link(self, order_number, return_url='https://test.ru', description='Bootcamp'):

        params = {
            'amount': 10000,
            'orderNumber': order_number,
            'token': self.alpha_token,
            'returnUrl': return_url,
            'description': description,
            'language': 'RU'
        }
        response = requests.post(url=self.url_get_link, params=params)
        try:
            response.raise_for_status()
            print("Запрос выполнен успешно!")
        except requests.exceptions.HTTPError as e:
            print(f"Ошибка HTTP: {e}")

        json = {}
        if response.json():
            json = response.json()
        return json

    def get_pay_status(self, orderid):

        params = {
            'orderId': orderid,
            # 'orderNumber': '4',
            'token': self.alpha_token,
        }
        response = requests.post(url=self.url_get_order_status, params=params)

        try:
            response.raise_for_status()
            print("Запрос выполнен успешно!")
        except requests.exceptions.HTTPError as e:
            print(f"Ошибка HTTP: {e}")

        json = {}
        if response.json():
            json = response.json()
        return json


if __name__ == "__main__":
    token = '7eeu8fqnt9h1cs1i781m9puo82'
    login = 'r-club232918273_vk-api'
    password = 'r-club232918273_vk*?1'
    pass_test_card = '12345678'
    login_test = 'r-club232918273_vk-operator'
    password_test = 'r-club232918273_vk*?1'
    # {'formUrl': 'https://alfa.rbsuat.com/payment/merchants/ecom2/payment_ru.html?mdOrder=0113bb68-4109-7b4d-b712-af9b025b4d5d',
    #  'orderId': '0113bb68-4109-7b4d-b712-af9b025b4d5d'
    orderId = '01314744-a1d1-7aa6-b10b-55a9025b4d5d'
    orderNumber = 17

    shustikov_pay = AlphaPay(alpha_token=token, alpha_login=login, alpha_password=password)

    # print(shustikov_pay.get_pay_link(order_number=orderNumber))
    pprint(shustikov_pay.get_pay_status(orderid=orderId))







