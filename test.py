import requests


def test_payment_success(base_url: str, operation_id: str = "12345", successful: bool = True):

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


if __name__ == "__main__":

    a = test_payment_success(base_url="https://litva.illiriaakva.online", operation_id=None, successful=False)

    caption = (
        "✅ Проверка оплаты прошла успешно!\n\n"
        f"💰 Вы оплатили!\n"
        f"📦 Название Продукта: {stream_info.title}\n"
        f"💳 Стоимость: {payment_data.amount} ₽\n\n"
        f"🔓 Чтобы получить доступы\nперейдите в Главное меню,\nнажмите кнопку Мои покупки\n\n"
        f"📱 < Главное меню -> Мои покупки >\n\n"
        f"🚀 Мы рады видеть тебя в нашей команде! 🎊"
    )
    animation = FSInputFile("source/pictures/successful_payment.jpg")
    media = InputMediaPhoto(media=animation, caption=caption)



