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
from utils.payments_operations import check_payment_status

from settings.config import TECH_CHANNEL

from db.add_methods_dao import set_pay, add_new_enrollments
from utils.user_veles_manager import UserVelesManagerAPI

from utils.passgen import get_password
from utils.creds import get_creds

from utils.states import OrderPay

from db.select_methods import get_product_info, get_stream_info, get_userinfo_by_id
from utils.access_control import restore_chat_access

from utils.gen_ssl_key import get_signed_cert

from dateutil.relativedelta import relativedelta
import datetime as DT

import calendar
import locale

import os

"""

Проверяем оплату пользователя AUTO MODE.

"""

router = Router()




# check_pay:{stream_id}:{price} check_pay

# Пример работы с калькуляцией даты
# from datetime import datetime
# from dateutil.relativedelta import relativedelta
#
# # Adding months and years
# today = datetime.now()
# future_date = today + relativedelta(months=3, years=1)
# print(f"Today: {today}")
# print(f"Future date: {future_date}")
#
# # Calculating the difference between two dates
# date1 = datetime(2022, 1, 15)
# date2 = datetime(2023, 3, 10)
# diff = relativedelta(date2, date1)
# print(f"Difference: {diff}")
# print(f"Years: {diff.years}, Months: {diff.months}, Days: {diff.days}")


# check_pay:{stream_id}:{price}:{directions_id} check_pay


@router.callback_query(F.data.startswith("check_pay:"))
async def check_pay(callback: CallbackQuery, state: FSMContext):
    # check_pay:{stream_id}:{price}:{directions_id}
    await callback.answer(text=f"Проверка Оплаты")

    list_data_buttons = callback.data.split(":")
    stream_id = int(list_data_buttons[1])
    price = int(list_data_buttons[2])

    # message_id = callback.message.message_id

    ###################### Получаем данные из FSM #########################
    key = StorageKey(
        bot_id=callback.bot.id,
        chat_id=callback.from_user.id,  # личный чат пользователя
        user_id=callback.from_user.id,  # сам пользователь
    )

    # Пример user_data
    # user_data = dict(stream_id_int=stream_id_int,
    #                  price=price,
    #                  directions_id=directions_id,
    #                  operation_id=payments_operation_data.get('operation_id', '*********'),
    #                  payment_id=payment_data_to_provider.id)

    user_data = await state.storage.get_data(key=key)
    logging.debug(f"user_data = {user_data}")
    directions_id = user_data.get("directions_id")

    ################# Получаем Статус Оплаты в PlategaAPI ########################################

    if user_data.get("operation_id") is not None:
        # payment_status = check_payment_status(operation_id_from_link=user_data.get("operation_id_from_link"))
        try:

            payment_status = check_payment_status(operation_id_from_provider=user_data.get("operation_id"))

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


    else:
        payment_status = "MANUAL"

    # Получаем Данные Потока и Продукта

    stream_info = await get_stream_info(id_stream=stream_id)
    product_info = await get_product_info(id_product=stream_info.product_id)

    # 'APPROVED'
    if payment_status == "APPROVED":

        # Обновляем запись в БД об оплате

        payment_data = await update_payment_data(
            payment_id=user_data.get("payment_id"),
            new_operation_id=user_data.get("operation_id"),
            new_status=payment_status,
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

        if len(vles_text_list)>1:
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

        # user_info = await get_userinfo_by_id(user_id=payment_data.user_id)
        # await restore_chat_access(
        #     bot=callback.bot,
        #     stream_info=stream_info,
        #     user_info=user_info,
        # )

        caption = (
            "✅ Проверка оплаты прошла успешно!\n\n"
            f"💰 Вы оплатили!\n"
            f"📦 Название Продукта: {stream_info.title}\n"
            f"💳 Стоимость: {payment_data.amount} ₽\n\n"    
            f"🔓 Чтобы получить доступы\nперейдите в Главное меню,\nнажмите кнопку Мои покупки\n\n"
            f"📱 < Главное меню -> Мои покупки >\n\n"
            f"🚀 Мы рады видеть тебя в нашей команде! 🎊"
        )
        animation = FSInputFile("source/pictures/successful_payment.png")
        media = InputMediaPhoto(media=animation, caption=caption)
        await state.clear()

    # "MANUAL"
    else:
        ################################ MANUAL MODE ###################################
        # TODO Сделать Видео или GIF о том как отправить квитанцию
        # Обновить запись в БД об оплате

        # Пример user_data
        # user_data = dict(stream_id_int=stream_id_int,
        #                  price=price,
        #                  directions_id=directions_id,
        #                  operation_id=payments_operation_data.get('operation_id', '*********'),
        #                  payment_id=payment_data_to_provider.id)

        payment_data = await update_payment_data(payment_id=user_data.get("payment_id", '000000'),
                                                 new_operation_id=user_data.get("operation_id", "None"),
                                                 new_status=payment_status)

        logging.info("Проверка оплаты не прошла:\n%s", payment_data)

        # caption = (
        #     f"💁🏻‍♂️ Оплатили?\n\n🧾 Тогда отправьте сюда (В ЭТОТ БОТ) квитанцию платежа: скриншот или документ.\n\n"
        #     f"Нажмите на «Скрепку» в левом или правом нижнем углу (рядом с полем, где вы пишете текст). "
        #     f"Выберите скриншот или документ.\n\n"
        #     f"Чтобы «Отправить», нажмите на синюю кнопку со стрелочкой в правом нижнем углу.\n\n"
        #     f"На квитанции должны быть четко видны: дата, время и сумма платежа.\n___________________________\n\n"
        #     f"Наши Контакты:\n\n👉 @user_post\n\n__________________________\n"
        #     f"За спам вы можете быть заблокированы!"
        # )

        caption = (
            f"💁‍♂️ Оплата не подтверждена?\n\n"
            f"📤 Отправьте квитанцию в этот бот:\n"
            f"• Скриншот чека\n"
            f"• Фото документа\n\n"
            f"📋 Инструкция:\n"
            f"1️⃣ Нажмите 📎 (скрепка)\n"
            f"2️⃣ Выберите «Фото» или «Документ»\n"
            f"3️⃣ Отправьте ➡️\n\n"
            f"✅ Требования к чеку:\n"
            f"• Четкая дата и время\n"
            f"• Точная сумма платежа\n\n"
            f"📞 Поддержка: @user_post\n\n"
            f"⚠️ Спам = блокировка"
        )

        animation = FSInputFile("source/pictures/payment_not_success.png")
        media = InputMediaPhoto(media=animation, caption=caption)

        user_data["message_id"] = callback.message.message_id

        await state.storage.update_data(key=key, data=user_data)
        await state.set_state(OrderPay.send_check)

    await callback.message.edit_media(media=media,
                                      reply_markup=get_back_button(stream_id=stream_id,
                                                                   price=price,
                                                                   product_id=stream_info.product_id,
                                                                   directions_id=directions_id))

