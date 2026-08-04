import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message, InputMediaAnimation

from aiogram.fsm.storage.base import StorageKey

from aiogram.fsm.context import FSMContext
import asyncio

from db.add_methods_dao import add_payments_operation
# from db.update_methods_dao import update_user_email
from keyboards.get_menu import get_payment_notification_button, get_fake_menu_button, get_errors_button
from db.select_methods import get_user_info_by_tg_id, get_stream_info
from settings.config import TECH_CHANNEL
# from utils.banking_operations import get_card_creds

# from utils.jira_functional.jira_functions import onboard_user_with_tasks

from utils.gen_ssl_key import get_signed_cert
# from utils.get_links import get_subscribe_link
# from utils.creds import get_creds
from utils.calculate_expire_date import get_expire_time_sec
import datetime as DT
import os
from utils.plategaio import PaymentMethod
from utils.payments_operations import get_payment_link_data
from utils.states import OrderPay

router = Router()

'''

Формируем  оплату пользователя. 

'''

# set_stream:{stream_id}:{price}  <- get_payment check_pay:{stream_id}:{price}:{directions_id} -> check_pay
# get_pay:{stream_id_int}:{price_menu}:{directions_id} or '' get_payment

# get_pay:{stream_id}:{price}:{product_id}:{directions_id}:{method_value} NEW



################################# ФОРМИРОВАНИЕ ПЛАТЕЖА И ПЕРЕХОД К ОПЛАТЕ ###########################################
@router.callback_query(F.data.startswith("get_pay:"))
async def get_pay(callback: CallbackQuery, state: FSMContext):

    new_gif = FSInputFile("source/pictures/animation.gif")

    await callback.bot.edit_message_media(chat_id=callback.from_user.id,
                                          message_id=callback.message.message_id,
                                          media=InputMediaAnimation(media=new_gif,
                                                                    caption="⏳ Формируем данные для оплаты...")
                                          )

    # await callback.bot.edit_message_caption(chat_id=callback.from_user.id,
    #                                         message_id=callback.message.message_id,
    #                                         caption="⏳ Формируем данные для оплаты...")
    await callback.message.edit_reply_markup(reply_markup=get_fake_menu_button())
    await callback.answer(text=f"⏳ Формируем данные для оплаты...")

    # get_pay:{stream_id}:{price_menu}:{product_id}:{directions_id}
    # set_group:{directions_id}' Back

    logging.debug("Callback = %s:", callback.data)

    #     0       1           2             3               4              5
    # get_pay:{stream_id}:{price}:{product_id}:{directions_id}:{method_value} NEW


    list_data_buttons = callback.data.split(':')
    stream_id_int = int(list_data_buttons[1])
    price = int(list_data_buttons[2])
    pay_method = list_data_buttons[5]  # "PaymentMethod.CARD_ACQUIRING.value"


    ######################## ФОРМИРУЕМ USER_KEY ########################

    user_key = StorageKey(
        bot_id=callback.bot.id,
        chat_id=callback.from_user.id,  # личный чат пользователя
        user_id=callback.from_user.id,  # сам пользователь
    )

    #################### ПОЛУЧАЕМ ДАННЫЕ ПО ОПЛАТЕ #####################
    logging.debug(f"Получаем Данные об Оплате")
    user_pay_data = await state.storage.get_data(key=user_key)
    logging.debug(f"user_pay_data={user_pay_data}")
    # stream_id_int = user_pay_data.get("stream_id_int")

    # email = user_pay_data.get("email", None)

    # directions_id_raw = user_pay_data.get("directions_id")
    #
    # if directions_id_raw is None or directions_id_raw == "":
    #     directions_id = None
    # else:
    #     directions_id = int(directions_id_raw)

    logging.info("Для оплаты выбран stream_id_int = %s", stream_id_int)

    ######################## Получаем Информаци о потоке #######################

    stream_info = await get_stream_info(id_stream=stream_id_int)

    ######################## Получаем Информаци о пользователе #################
    logging.debug(f"Получаем Информаци о пользователе")
    user_info_paidantic = await get_user_info_by_tg_id(tg_user_id=callback.from_user.id)
    logging.debug(f"user_info_paidantic={user_info_paidantic}")
    ############################ Обновляем Email ###############################

    # await update_user_email(user_id_from_db=user_info_paidantic['id'], new_email=email)

    ########################### Получаем Данные о платеже от Провайдера Эквайринга #############################

    try:
        logging.debug("Подключаемся к платежному шлюзу")
        payments_data_from_provider = get_payment_link_data(payment_method=pay_method, amount=float(price))
        url_pay_from_provider = payments_data_from_provider.get('payment_link',
                                                      'Что-то пошло не так... повторите попытку позже.')

    except Exception as exception_text:
        # < code > текст < / code >
        buttons = get_errors_button()
        await callback.message.edit_caption(caption=f"❌ <b>Что-то пошло не так</b>… Повторите попытку позже\n\n"
                                                    f"📢 <b>Сообщите в поддержку</b>\n\n"
                                                    f"💡 <i>Вы можете нажать главное меню, чтобы выбрать тариф и другой способ оплаты</i>\n\n",
                                            parse_mode="HTML",
                                            reply_markup=buttons)

        await callback.bot.send_message(chat_id=TECH_CHANNEL,
                                        text=(f"❌ <b>Ошибка создания ссылки на оплату</b>\n\n"
                                                    f"📢 user_tg_id = {callback.from_user.id} user_name = {callback.from_user.username}\n"
                                                    f"   pay_method = {pay_method}"
                                                    f""
                                                    f"🔴 <b>Ошибка:</b>\n"
                                                    f"<code>{exception_text}</code>"),
                                        parse_mode="HTML",
                                        reply_markup=None)
        return


    ######################## Записываем Данные об оплате ######################

    operation_id_from_provider = payments_data_from_provider.get('operation_id_from_provider',
                                                                 'none_operation_id')

    payments_data_dict = {"provider": "PLATEGA",
                          "amount": price,
                          "operation_id": operation_id_from_provider,
                          "status": "CREATE",
                          "user_id": user_info_paidantic.id,
                          "stream_id": stream_info.id}

    #################### Добавляем в БД запись об оплате и получаем ссылку на оплату ###########################

    payment_data_from_db = await add_payments_operation(payments_data=payments_data_dict)

    ###################### Сохраняем данные Пользователю в FSM #########################

    user_data = dict(stream_id_int=stream_id_int,
                     price=price,
                     operation_id=operation_id_from_provider,
                     payment_id=payment_data_from_db.id,
                     pay_method=pay_method,
                     tg_user_id=callback.from_user.id,
                     tg_message_id=callback.message.message_id,
                     )

    await state.storage.update_data(user_key, data=user_data)  # <— сохраняем для ЭТОГО пользователя


    ############################## Платежные Реквизиты ##############################

    payment_details = (
        f"Способ оплаты: {pay_method}\n\n"
        f"К оплате: {price} 🇷🇺RUB\n"
        f"Ваш ID: {user_info_paidantic.telegram_id}\n\n"
        "Реквизиты для оплаты:\n\n"
        f"Ссылка на оплату:\n{url_pay_from_provider}\n\n"
        f"После оплаты вам будут доступны ключи доступа.\n"
    )

    directions_id = user_pay_data.get("directions_id")

    buttons = get_payment_notification_button(price=f"{price}", stream_id=stream_id_int, directions_id=directions_id)
    photo = FSInputFile('source/pictures/payment.jpg')
    media = InputMediaPhoto(
        media=photo,
        caption=payment_details,
        parse_mode='HTML'
    )

    await callback.message.edit_media(media=media, reply_markup=buttons)


# Тестовый блок
if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)

    try:
        payments_operation_data = get_payment_link_data(payment_method=int(PaymentMethod.CRYPTOCURRENCY.value), amount=10)
        print(payments_operation_data)
    except Exception as e:
        print(e)
