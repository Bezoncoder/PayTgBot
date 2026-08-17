import asyncio
import logging

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InputMediaPhoto,
)

from aiogram.fsm.storage.base import StorageKey

from aiogram.fsm.context import FSMContext

from db.update_methods_dao import update_payment_data, update_referral_rewards
from keyboards.get_menu import get_back_button, get_errors_button
from utils.calculate_expire_date import get_expire_time_sec
from payment_tools.payments_operations import check_payment_status

from settings.config import USER, PASSWORD, TECH_CHANNEL

from db.add_methods_dao import add_new_enrollments

from utils.states import OrderPay

from db.select_methods import get_product_info, get_stream_info, get_user_info_by_tg_id

from dateutil.relativedelta import relativedelta
import datetime as DT

from vpn_management.vlessuiapi import XUIClient

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
    logging.info(f"Запущена Автоматическая Проверка Оплаты")
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
    pay_method = user_data.get("pay_method")

    ################# Получаем Статус Оплаты в PlategaAPI ########################################

    if user_data.get("operation_id") is not None:
        # payment_status = check_payment_status(operation_id_from_link=user_data.get("operation_id_from_link"))
        try:

            payment_status = check_payment_status(operation_id_from_provider=user_data.get("operation_id", 000))
            logging.info(f"Получен статус оплаты для user_tg_id = {callback.from_user.id}: "
                         f"operation_id = {user_data.get("operation_id")} status = {payment_status}")

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
            stream_id=stream_info.id

        )

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
        if payment_data.amount != 30:

            user_info = await get_user_info_by_tg_id(tg_user_id=int(callback.from_user.id))
            referral_rewards = dict(payment_id=payment_data.id,
                                    reward_value=str(payment_data.amount*0.2),
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
            await callback.message.edit_caption(caption=f"⏳ <b>Выполняется проверка оплаты</b>\n\n"
                                                        f"Пожалуйста, подождите несколько секунд\n\n"
                                                        f"💡 <i>Не закрывайте окно и не обновляйте страницу</i>\n\n"
                                                        f"🔄 <b>Статус:</b>\n"
                                                        f"<code>Проверка в процессе...</code>",
                                                parse_mode="HTML")
            logging.info(f"💡 Отправлено сообщение о выполнении операции")
        except Exception as exception_text:
            buttons = get_errors_button()
            await callback.message.edit_caption(caption=f"❌ <b>Что-то пошло не так</b>… Повторите попытку позже\n\n"
                                                        f"📢 <b>Сообщите в поддержку</b> и прикрепите текст ошибки\n\n"
                                                        f"💡 <i>Чтобы скопировать — просто нажмите на текст</i>\n\n"
                                                        f"🔴 <b>Ошибка:</b>\n"
                                                        f"<code>{exception_text}</code>",
                                                parse_mode="HTML",
                                                reply_markup=buttons)
        await asyncio.sleep(10)
        try:
            vless_client = XUIClient(base_url_from_panel=base_url,
                                     username=USER,
                                     password=PASSWORD,
                                     api_token=product_info.api_vless_token,
                                     verify_ssl=True,
                                     public_inbound_key=product_info.public_key,
                                     sid=product_info.short_id)

            client_uuid_from_payment = str(payment_data.operation_id)

            obj = vless_client.get_client_traffic_by_id(client_uuid=client_uuid_from_payment).get("obj")

            if isinstance(obj, list) and obj == []:
                logging.info(f"📢 Создаем ссылку для клиента с UUID = {client_uuid_from_payment}")
                link = vless_client.add_client(client_uuid=client_uuid_from_payment,
                                               flow="xtls-rprx-vision",
                                               total_gb=product_info.total_gb,
                                               inbound_id=str(product_info.inbound_id),
                                               expiry_time=expire_time_sec,
                                               email=f"{client_uuid_from_payment}").get('subscription_link')
            else:
                logging.info(f"💡 Клиент c UUID = {client_uuid_from_payment} уже есть в 3xui")
                logging.debug(obj)
                link = None

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
            await callback.bot.send_message(chat_id=TECH_CHANNEL,
                                            text=(f"❌ <b>Ошибка создания VLess ссылки</b>\n\n"
                                                  f"📢 user_tg_id = {callback.from_user.id} user_name = {callback.from_user.username}\n"
                                                  f"🔴 <b>Ошибка:</b>\n"
                                                  f"<code>{exception_text}</code>"),
                                            parse_mode="HTML",
                                            reply_markup=None)
            return

        ############### Запись в БД Enrollments ################
        if link:
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
        animation = FSInputFile("source/pictures/successful_payment.jpg")
        media = InputMediaPhoto(media=animation, caption=caption)
        # await state.clear()

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
                                                 new_status=payment_status,
                                                 stream_id=stream_info.id)

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
            # f"📞 Поддержка: @user_post\n\n"
            f"⚠️ Спам = блокировка"
        )

        animation = FSInputFile("source/pictures/payment_not_success.jpg")
        media = InputMediaPhoto(media=animation, caption=caption)

        user_data["message_id"] = callback.message.message_id


        await state.storage.update_data(key=key, data=user_data)
        await state.set_state(OrderPay.send_check)

    await callback.message.edit_media(media=media,
                                      reply_markup=get_back_button(stream_id=stream_id,
                                                                   price=price,
                                                                   product_id=stream_info.product_id,
                                                                   directions_id=directions_id,
                                                                   method_value=pay_method)
                                      )

