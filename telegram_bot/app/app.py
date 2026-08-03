import logging

import requests
from aiohttp import web
from aiogram.types import Update, FSInputFile, InputMediaPhoto
from urllib3 import request
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

from db.select_methods import get_userinfo_by_id_operation_id, get_stream_info, get_product_info
from keyboards.get_menu import get_back_button
from settings.config import bot, dp
from pathlib import Path

async def handle_webhook(request: web.Request):
    try:
        update = Update.model_validate(await request.json(), context={"bot": bot})
        await dp.feed_update(bot, update)
        return web.Response(status=200)
    except Exception as e:
        print(f"Webhook error: {e}")
        return web.Response(status=500)

async def home_page(request: web.Request) -> web.Response:
    """
    Обработчик для отображения главной страницы из файла source/templates/index.html.
    """
    file_path = Path("source/templates/index.html")

    if not file_path.exists():
        raise web.HTTPNotFound(text="Файл source/templates/index.html не найден")

    html_content = file_path.read_text(encoding="utf-8")
    return web.Response(text=html_content, content_type="text/html")

async def payment_success(request: web.Request) -> web.Response:
    logging.info("⚠️ Получен payment_success request")

    try:
        operation_id = request.query.get("operation_id")
        successful_raw = request.query.get("successful")

        if operation_id is None or successful_raw is None:
            return web.json_response(
                {"success": False, "message": "operation_id and successful None"},
                status=400
            )

        successful = successful_raw

        if not successful:

            return web.json_response({
                "success": False,
                "message": "Payment not confirmed",
                "operation_id": operation_id
            })

        #RUN CHECK PAYMENT AUTO

        user_info = await get_userinfo_by_id_operation_id(operation_id=operation_id)

        if user_info and user_info.telegram_id:

            key = StorageKey(
                bot_id=bot.id,
                chat_id=int(user_info.telegram_id),
                user_id=int(user_info.telegram_id),
            )

            user_state = FSMContext(
                storage=dp.storage,
                key=key
            )

            current_state = await user_state.get_state()
            user_data = await user_state.get_data()

            logging.info(f"⚠️ {user_data}")

            # Получаем Данные Потока и Продукта
            stream_info = await get_stream_info(id_stream=int(user_data.get("stream_id_int")))
            product_info = await get_product_info(id_product=stream_info.product_id)

            # user_data = dict(stream_id_int=stream_id_int,
            #                  price=price,
            #                  operation_id=operation_id_from_provider,
            #                  payment_id=payment_data_from_db.id,
            #                  pay_method=pay_method,
            #                  tg_user_id=callback.from_user.id,
            #                  tg_message_id=callback.message.message_id)

            logging.info("Получена оплата:\n%s", operation_id)

            caption = (
                "✅ Проверка оплаты прошла успешно!\n\n"
                f"💰 Вы оплатили!\n"
                f"📦 Название Продукта: {stream_info.title}\n"
                f"💳 Стоимость: {stream_info.price} ₽\n\n"
                f"🔓 Чтобы получить доступы\nперейдите в Главное меню,\nнажмите кнопку Мои покупки\n\n"
                f"📱 < Главное меню -> Мои покупки >\n\n"
                f"🚀 Мы рады видеть тебя в нашей команде! 🎊"
            )
            animation = FSInputFile("source/pictures/successful_payment.jpg")
            media = InputMediaPhoto(media=animation, caption=caption)
            await bot.edit_message_media(message_id=user_data.get("tg_message_id"),
                                         media = media,
                                         chat_id=user_info.telegram_id,
                                         reply_markup = get_back_button(stream_id=stream_info.id,
                                                                  price=stream_info.price,
                                                                  product_id=stream_info.product_id,
                                                                  directions_id=int(product_info.direction_id),
                                                                  method_value=user_data.get("pay_method"))
                                   )

            # expected = {"success": True, "message": "operation_id and successful are required"}
            return web.json_response(
                {"success": True, "message": "operation_id and successful are required"},
                status=200
            )
        else:
            return web.json_response({"success": False, "message": f"User telegram_id not found"},
                                     status=400)
    except Exception as e:
        logging.exception("payment_success error")
        return web.json_response({"success": False, "message": f"{e}"},
                                 status=400)

