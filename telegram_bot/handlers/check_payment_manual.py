import asyncio
import logging
from pprint import pprint

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
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

from db.update_methods_dao import update_payment_data, update_referral_rewards
from keyboards.get_menu import get_payment_verification_button, get_back_button, get_errors_button, get_start_button
from utils.calculate_expire_date import get_expire_time_sec
from utils.get_links import get_subscribe_link
from utils.payments import tochka_bank
# from utils.payments_operations import check_payment_status

from settings.config import TECH_CHANNEL, USER, PASSWORD, API_VLESS_TOKEN

from db.add_methods_dao import set_pay, add_new_enrollments

from utils.passgen import get_password
from utils.creds import get_creds

from utils.states import OrderPay

from db.select_methods import get_product_info, get_stream_info, get_userinfo_by_id, get_user_info_by_tg_id
from utils.access_control import restore_chat_access

from utils.gen_ssl_key import get_signed_cert

from utils.user_veles_manager import UserVelesManagerAPI

from dateutil.relativedelta import relativedelta
import datetime as DT

import calendar
import locale

import os

from utils.vlessuiapi import XUIClient

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

###################################################################################################


    try:
        if user_data.get("message_id"):

            await message.bot.delete_messages(chat_id=message.from_user.id,
                                              message_ids=[user_data.get("message_id")])

            message_to_user = await message.bot.send_message(chat_id=message.from_user.id,
                                           text=(f"Вы отправили чек!\n\n"
                                                f"📢 Он отправится на проверку.\n"
                                                   f"После проверки Вам придет сообщение!\n\n"
                                                f"💡 Сейчас Это сообщение будет удалено.\n "
                                                   f"Ваш чек останется до конца проверки в этом чате\n\n"
                                                f"🔴 Ничего не делайте, дождитесь окончания проверки!\n\n"
                                                   f"Если проверка не пройдет в течении суток, перезапустите бота и "
                                                   f"повторите отправку. Или сообщите в чат техподдержки\n"),
                                           reply_markup=None)


            await asyncio.sleep(15)
            await message.bot.delete_messages(chat_id=message_to_user.chat.id,
                                              message_ids=[message_to_user.message_id])
    except TelegramBadRequest:
        logging.debug("Не удалось удалить старое сообщение:")


    # await message.bot.delete_messages(
    #     chat_id=message.from_user.id, message_ids=[user_data.get("message_id", 0)]
    # )

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
    # TODO payment_id СДЕЛАТЬ ПРОВЕРКУ payment_data
    try:
        payment_data = await update_payment_data(
            payment_id=user_data.get("payment_id", 000),
            new_operation_id=user_data.get("operation_id", "000"),
            new_status="APPROVED_MANUAL",
            stream_id=stream_info.id
        )
    except Exception as e:
        logging.error(f"⚠️ ОШИБКА await update_payment_data\n"
                      f"user_data = {user_data}\n"
                      f"{e}\n")
        payment_data = None

    logging.info("Получена оплата:\n%s", payment_data)

    # Обновляем запись в БД ReferralRewards

    # referral_rewards = dict(user_id=int(user_info.get("id")),
    #                         referred_user_id=referred_by_user_id,
    #                         payment_id=None,
    #                         reward_type=reward_type,
    #                         reward_value=None,
    #                         active_status=None)

    # TODO сделать проверку наличия реферальной записи
    # SELECT referral_rewards WHERE active_status==None
    if payment_data and payment_data.amount != 30:
        print("⚠️ — предупреждение, требует внимания")
        user_info = await get_user_info_by_tg_id(tg_user_id=user_telegram_id)

        reward_value = payment_data.amount * 0.2
        referral_rewards = dict(payment_id=payment_data.id,
                                reward_value=str(reward_value),
                                active_status=True)

        referral_data = await update_referral_rewards(user_id=user_info.id, values_dict=referral_rewards)

        logging.debug(referral_data)

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
    logging.debug(f"expire_date = {expire_date}")
    # Нормализуем к дате
    if isinstance(expire_date, DT.datetime):
        expiredate_to_db = expire_date.date()
    else:
        expiredate_to_db = expire_date

    expire_time_sec = get_expire_time_sec(expire_date=expire_date)

    #################### Vles VPN ###############################

    base_url = product_info.base_url
    # https://155.212.228.65:49699/IIVMNd0IoCAcUBOuKK

    try:
        vless_client = XUIClient(base_url_from_panel=base_url,
                                 username=USER,
                                 password=PASSWORD,
                                 api_token=API_VLESS_TOKEN,
                                 verify_ssl=True,
                                 public_inbound_key=product_info.public_key,
                                 sid=product_info.short_id)

        client_uuid_from_payment = str(payment_data.operation_id)
        # link = vless_client.add_client(client_uuid=client_uuid_from_payment,
        #                                flow="xtls-rprx-vision",
        #                                inbound_id="1",
        #                                expiry_time=expire_time_sec,
        #                                email=f"{user_telegram_id}_{client_uuid_from_payment}").get('subscription_link')
        link = vless_client.add_client(client_uuid=client_uuid_from_payment,
                                       flow="xtls-rprx-vision",
                                       total_gb=product_info.total_gb,
                                       inbound_id=str(product_info.inbound_id),
                                       expiry_time=expire_time_sec,
                                       email=f"{client_uuid_from_payment}").get('subscription_link')
    except Exception as exception_text:
        # < code > текст < / code >
        buttons = get_errors_button()
        new_caption = f"❌ <b>Что-то пошло не так</b>… Повторите попытку позже\n\n"
        f"📢 <b>Сообщите в поддержку</b> и прикрепите текст ошибки\n\n"
        f"💡 <i>Чтобы скопировать — просто нажмите на текст</i>\n\n"
        f"🔴 <b>Ошибка:</b>\n"
        f"<code>{exception_text}</code>"
        await callback.message.edit_caption(caption=new_caption,
                                            parse_mode="HTML",
                                            reply_markup=buttons)

        await callback.bot.send_message(text=new_caption,
                                        chat_id=user_telegram_id,
                                        reply_markup=buttons)
        return

    ############### Запись в БД Enrollments ################

    enrollment_data = dict(
        active=True,
        user_id=payment_data.user_id,
        expire_date=expiredate_to_db,
        title_product=product_info.title,
        product_id=stream_info.product_id,
        stream_id=stream_info.id,
        vless_user_name=client_uuid_from_payment,
        vless_link=link
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
        f"🔓 Чтобы получить доступы\nперейдите в Главное меню,\nнажмите кнопку Мои покупки\n\n"
        f"📱 < Главное меню -> Мои покупки >\n\n"
        f"🚀 Мы рады видеть тебя в нашей команде! 🎊"
    )

    await callback.bot.delete_messages(
        chat_id=TECH_CHANNEL, message_ids=[callback.message.message_id]
    )
    # TODO ПРОДУМАТЬ УДАЛЕНИЯ И ЗАМЕНИТЬ
    await callback.bot.delete_messages(
        chat_id=user_telegram_id, message_ids=[user_data.get("message_id", 0)]
    )

    await callback.bot.send_photo(
        chat_id=user_telegram_id,
        photo=animation,
        caption=caption,
        reply_markup=get_start_button()
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
