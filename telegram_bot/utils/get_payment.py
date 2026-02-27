def create_payment_with_receipt(
        token,
        customer_code,
        amount,
        purpose,
        redirect_url,
        fail_redirect_url,
        payment_modes,
        save_card,
        consumer_id,
        merchant_id,
        pre_authorization,
        ttl,
        payment_link_id,
        tax_system_code,
        client_info,
        items,
        supplier_info
):
    url = "https://enter.tochka.com/uapi/acquiring/v1.0/payments_with_receipt"
    payload = {
        "Data": {
            "customerCode": customer_code,
            "amount": amount,
            "purpose": purpose,
            "redirectUrl": redirect_url,
            "failRedirectUrl": fail_redirect_url,
            "paymentMode": payment_modes,
            "saveCard": save_card,
            "consumerId": consumer_id,
            "merchantId": merchant_id,
            "preAuthorization": pre_authorization,
            "ttl": ttl,
            "paymentLinkId": payment_link_id,
            "taxSystemCode": tax_system_code,
            "Client": client_info,
            "Items": items,
            "Supplier": supplier_info
        }
    }

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    response = requests.post(url, headers=headers, json=payload)
    return response.json()


# Пример вызова метода:
if __name__ == "__main__":
    token = "<token>"
    customer_code = "300000092"
    amount = "1234.00"
    purpose = "Перевод за оказанные услуги"
    redirect_url = "https://example.com"
    fail_redirect_url = "https://example.com/fail"
    payment_modes = ["sbp", "card", "tinkoff", "dolyame"]
    save_card = True
    consumer_id = "fedac807-078d-45ac-a43b-5c01c57edbf8"
    merchant_id = "200000000001056"
    pre_authorization = True
    ttl = 10080
    payment_link_id = "string"
    tax_system_code = "osn"
    client_info = {
        "name": "Иванов Иван Иванович",
        "email": "ivanov@mail.com",
        "phone": "+7999999999"
    }
    items = [
        {
            "vatType": "none",
            "name": "string",
            "amount": "1234.00",
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
    ]
    supplier_info = {
        "phone": "+7999999999",
        "name": "ООО Альтер",
        "taxCode": "660000000000"
    }

    result = create_payment_with_receipt(
        token,
        customer_code,
        amount,
        purpose,
        redirect_url,
        fail_redirect_url,
        payment_modes,
        save_card,
        consumer_id,
        merchant_id,
        pre_authorization,
        ttl,
        payment_link_id,
        tax_system_code,
        client_info,
        items,
        supplier_info
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
# Такой метод принимает все необходимые параметры, строит JSON-тело запроса, добавляет заголовки с токеном авторизации и выполняет POST-запрос через requests.post. Ответ возвращается в формате Python-словаря.
#
# Хотите, чтобы я сделал метод с меньшим числом параметров и значениями по умолчанию?



