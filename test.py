import requests

import time


def test_payment_success(base_url: str, operation_id: str = "12345", successful: bool = True):
    '''
        a = test_payment_success(base_url="https://litva.illiriaakva.online", operation_id=None, successful=False)

    :param base_url:
    :param operation_id:
    :param successful:
    :return:
    '''

    url = f"{base_url}/api/payment-success"
    params = {
        "operation_id": operation_id,
        "successful": str(successful).lower(),
    }

    response = requests.post(url, params=params, timeout=10)

    print("URL:", response.url)
    print("Status:", response.status_code)
    print("Text:", response.text)

    return response



def send_payment_success_with_retry(retry_url: str, amount:int, stream_id: int,
                                    operation_id: str, max_retries: int = 3, delay: int = 2, successful: bool = False):
    params = {
        "operation_id": operation_id,
        "successful": successful,
        "stream_id": stream_id,
        "price": amount,

    }

    # user_data = dict(stream_id_int=stream_id_int,
    #                  price=price,
    #                  operation_id=operation_id_from_provider,
    #                  payment_id=payment_data_from_db.id,
    #                  pay_method=pay_method,
    #                  tg_user_id=callback.from_user.id,
    #                  tg_message_id=callback.message.message_id)

    expected = {"success": True, "message": "operation_id and successful are required"}

    # response = requests.post(retry_url, params=params, timeout=10)
    # last_response = response

    last_response = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(retry_url, params=params, timeout=10)
            last_response = response

            try:
                data = response.json()
            except Exception:
                data = None

            if data == expected:
                return response

            print(f"Попытка {attempt}: ответ не совпал, повторяем...")
            print(data)

        except Exception as e:
            print(f"Попытка {attempt}: ошибка запроса: {e}")

        if attempt < max_retries:
            time.sleep(delay)

    return last_response.json()

if __name__ == "__main__":

    # a = test_payment_success(base_url="https://litva.illiriaakva.online", operation_id=None, successful=False)
    # (retry_url: str, amount:int, stream_id: int,
    # operation_id: str, max_retries: int = 3, delay: int = 2)
    print(send_payment_success_with_retry(retry_url="https://litva.illiriaakva.online/api/payment-success",
                                          amount=19,
                                          stream_id=19,
                                          operation_id="13206fd3-3c5f-4d95-8c6b-5685a7856e77",
                                          successful=False))
    # caption = (
    #     "✅ Проверка оплаты прошла успешно!\n\n"
    #     f"💰 Вы оплатили!\n"
    #     f"📦 Название Продукта: {stream_info.title}\n"
    #     f"💳 Стоимость: {payment_data.amount} ₽\n\n"
    #     f"🔓 Чтобы получить доступы\nперейдите в Главное меню,\nнажмите кнопку Мои покупки\n\n"
    #     f"📱 < Главное меню -> Мои покупки >\n\n"
    #     f"🚀 Мы рады видеть тебя в нашей команде! 🎊"
    # )
    # animation = FSInputFile("source/pictures/successful_payment.jpg")
    # media = InputMediaPhoto(media=animation, caption=caption)



