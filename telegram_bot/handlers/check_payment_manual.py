import logging
from pprint import pprint

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InputMediaPhoto,
    Message,
    InputMediaAnimation,
)

from aiogram.fsm.storage.base import StorageKey

from aiogram.fsm.context import FSMContext

from aiogram.filters import StateFilter

from db.update_methods_dao import update_payment_data
from keyboards.get_menu import get_payment_verification_button, get_back_button, get_errors_button
from utils.get_links import get_subscribe_link
from utils.payments import tochka_bank
# from utils.payments_operations import check_payment_status

from settings.config import TECH_CHANNEL

from db.add_methods_dao import set_pay, add_new_enrollments

from utils.passgen import get_password
from utils.creds import get_creds

from utils.states import OrderPay

from db.select_methods import get_product_info, get_stream_info, get_userinfo_by_id
from utils.access_control import restore_chat_access

from utils.gen_ssl_key import get_signed_cert

from utils.user_veles_manager import UserVelesManagerAPI

from dateutil.relativedelta import relativedelta
import datetime as DT

import calendar
import locale

import os



"""

Проверяем оплату пользователя MANUAL MODE.

"""

router = Router()



@router.message(OrderPay.send_check, F.content_type.in_({"document", "photo"}))
async def send_check(message: Message, state: FSMContext):

    ###################### Получаем данные из FSM #########################

    key = StorageKey(
        bot_id=message.bot.id,
        chat_id=message.from_user.id,  # личный чат пользователя
        user_id=message.from_user.id,  # сам пользователь
    )

    user_data = await state.storage.get_data(key=key)

    logging.debug("Copy Checks data %s", user_data)

    caption = (
            str(message.from_user.id)
            + " "
            + str(message.from_user.username)
            + " "
            + f"{user_data.get('price', 0)}"
            + " "
            + f"{user_data.get('stream_id_int', 0)}"
    )

    await message.bot.delete_messages(
        chat_id=message.from_user.id, message_ids=[user_data.get("message_id", 0)]
    )

    user_data["message_id"] = message.message_id
    await state.storage.update_data(key=key, data=user_data)

    await message.bot.copy_message(
        chat_id=TECH_CHANNEL,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
        caption=caption,
        reply_markup=get_payment_verification_button(),
    )


# TODO Установку оплаты переписать в функцию для чистоты кода


@router.callback_query(F.data == "approve_check")
async def approve_check(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    # Пример caption
    # caption = (
    #         str(message.from_user.id)
    #         + " "
    #         + str(message.from_user.username)
    #         + " "
    #         + f"{user_data.get("price", 0)}"
    #         + " "
    #         + f"{user_data.get("stream_id_int", 0)}}"
    # )

    # Получаем caption из сообщения
    caption = callback.message.caption

    user_for_check_list = caption.split(" ")
    user_telegram_id = int(user_for_check_list[0])
    stream_id = user_for_check_list[3]

    ###################### Получаем данные из FSM #########################

    key = StorageKey(
        bot_id=callback.bot.id,
        chat_id=user_telegram_id,  # личный чат пользователя
        user_id=user_telegram_id,  # сам пользователь
    )

    # Пример user_data
    # user_data = dict(stream_id_int=stream_id_int,
    #                  price=price,
    #                  directions_id=directions_id,
    #                  operation_id=payments_operation_data.get('operation_id', '*********'),
    #                  payment_id=payment_data_to_provider.id)
    #                  message_id="message_id"

    user_data = await state.storage.get_data(key=key)

    # Получаем Данные Потока и Продукта

    stream_info = await get_stream_info(id_stream=stream_id)
    product_info = await get_product_info(id_product=stream_info.product_id)

    # Обновляем запись в БД об оплате

    payment_data = await update_payment_data(
        payment_id=user_data.get("payment_id"),
        new_operation_id=user_data.get("operation_id"),
        new_status="MANUAL",
    )

    logging.info("Получена оплата:\n%s", payment_data)

    #################### EXPIRE_DATE ############################

    delta = stream_info.subscription_period
    today = DT.datetime.now()

    if delta == "day":
        expire_date = today + relativedelta(days=1)
    elif delta == "month":
        expire_date = today + relativedelta(months=1)
    elif delta == "year":
        expire_date = today + relativedelta(years=1)
    else:
        expire_date = today

    # Нормализуем к дате
    if isinstance(expire_date, DT.datetime):
        expiredate_to_db = expire_date.date()
    else:
        expiredate_to_db = expire_date

    #################### Vles VPN ###############################

    base_url = product_info.base_url

    try:
        veles = UserVelesManagerAPI(base_url=base_url)
        vless_user_name = str(payment_data.operation_id)
        link = veles.add_user(username=str(payment_data.operation_id))

    except Exception as exception_text:
        # < code > текст < / code >
        buttons = get_errors_button()
        await callback.message.edit_caption(caption=f"❌ <b>Что-то пошло не так</b>… Повторите попытку позже\n\n"
                                                    f"📢 <b>Сообщите в поддержку</b> и прикрепите текст ошибки\n\n"
                                                    f"💡 <i>Чтобы скопировать — просто нажмите на текст</i>\n\n"
                                                    f"🔴 <b>Ошибка:</b>\n"
                                                    f"<code>{exception_text}</code>",
                                            parse_mode="HTML",
                                            reply_markup=buttons)
        return


    vles_text_list = link.split("\n")

    if len(vles_text_list) > 1:
        vles_text_link = vles_text_list[1]
    else:
        vles_text_link = vles_text_list[0]

    ############### Запись в БД Enrollments ################

    enrollment_data = dict(
        active=True,
        user_id=payment_data.user_id,
        expire_date=expiredate_to_db,
        title_product=product_info.title,
        product_id=stream_info.product_id,
        stream_id=stream_info.id,
        vless_user_name=vless_user_name,
        vless_link=vles_text_link
    )

    new_enrollment = await add_new_enrollments(enrollment_data=enrollment_data)

    logging.debug("Сделана запись в Enrollments:\n%s", new_enrollment)
    logging.debug(f"payment_data={payment_data}")
    # user_info = await get_userinfo_by_id(user_id=payment_data.user_id)
    #
    # await restore_chat_access(
    #     bot=callback.bot,
    #     stream_info=stream_info,
    #     user_info=user_info,
    # )

    animation = FSInputFile("source/pictures/successful_payment.png")

    caption = (
        "✅ Проверка оплаты прошла успешно!\n\n"
        f"💰 Вы оплатили!\n"
        f"📦 Название Продукта: {stream_info.title}\n"
        f"💳 Стоимость: {payment_data.amount} ₽\n\n"
        f"🔓 Чтобы получить доступы\nперейдите в Главное меню,\nнажмите кнопку Мои доступы\n\n"
        f"📱 < Главное меню -> Мои покупки >\n\n"
        f"🚀 Мы рады видеть тебя в нашей команде! 🎊"
    )

    await callback.bot.delete_messages(
        chat_id=TECH_CHANNEL, message_ids=[callback.message.message_id]
    )

    await callback.bot.delete_messages(
        chat_id=user_telegram_id, message_ids=[user_data.get("message_id", 0)]
    )

    await callback.bot.send_photo(
        chat_id=user_telegram_id,
        photo=animation,
        caption=caption,
        reply_markup=get_back_button(
            stream_id=stream_info.id,
            price=stream_info.price,
            product_id=stream_info.product_id,
            directions_id=str(product_info.direction_id),
        ),
    )


@router.callback_query(F.data == "skip_check")
async def set5(callback: CallbackQuery, state: FSMContext):
    # Получаем caption из сообщения
    caption_message = callback.message.caption
    user_for_check = caption_message.split(" ")
    user_telegram_id = int(user_for_check[0])

    ###################### Получаем данные из FSM #########################

    key = StorageKey(
        bot_id=callback.bot.id,
        chat_id=user_telegram_id,  # личный чат пользователя
        user_id=user_telegram_id,  # сам пользователь
    )

    user_data = await state.storage.get_data(key=key)

    # Получаем Данные Потока и Продукта

    stream_info = await get_stream_info(id_stream=user_data.get("stream_id_int", 0))
    product_info = await get_product_info(id_product=stream_info.product_id)

    await callback.answer(text="Проверка оплаты не прошла.")

    await callback.bot.delete_messages(
        chat_id=callback.message.chat.id, message_ids=[int(callback.message.message_id)]
    )

    caption = (
        f"🤷‍♀️ Проверка не прошла!!!\n\n"
        "Свяжитесь с нами или отправьте квитанцию еще раз чуть позже.\n\n"
        "🧾 Вы можете отправить сюда квитанцию платежа: скриншот или документ.\n\n"
        "На квитанции должны быть четко видны: дата, время и сумма платежа.\n___________________________\n\n"
        "Наши Контакты:\n\n👉 https://t.me/QuantumTurboVPN\n\n__________________________\n"
        "За спам вы можете быть заблокированы!"
    )

    await callback.bot.delete_messages(
        chat_id=user_telegram_id, message_ids=[user_data.get("message_id", 0)]
    )
    # get_pay:{stream_id}:{price_menu}:{product_id}:{directions_id}
    await callback.bot.send_message(
        chat_id=user_telegram_id,
        text=caption,
        reply_markup=get_back_button(
            stream_id=stream_info.id,
            price=stream_info.price,
            product_id=stream_info.product_id,
            directions_id=str(product_info.direction_id),
        ),
    )
