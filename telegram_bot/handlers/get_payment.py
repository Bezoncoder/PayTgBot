import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message

from aiogram.fsm.storage.base import StorageKey

from aiogram.fsm.context import FSMContext
import asyncio

from db.add_methods_dao import add_payments_operation
# from db.update_methods_dao import update_user_email
from keyboards.get_menu import get_payment_notification_button, get_fake_menu_button, get_errors_button
from db.select_methods import get_user_info_by_tg_id, get_stream_info
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


# get_pay:{stream_id_int}:{price_menu}:{directions_id} or '' get_payment
# set_stream:{stream_id}:{price}  <- get_payment check_pay:{stream_id}:{price}:{directions_id} -> check_pay


################################# ФОРМИРОВАНИЕ ПЛАТЕЖА И ПЕРЕХОД К ОПЛАТЕ ###########################################
@router.callback_query(F.data.startswith("get_pay:"))
async def get_pay(callback: CallbackQuery, state: FSMContext):

    await callback.bot.edit_message_caption(chat_id=callback.from_user.id,
                                            message_id=callback.message.message_id,
                                            caption="⏳ Формируем данные для оплаты...")
    await callback.message.edit_reply_markup(reply_markup=get_fake_menu_button())
    await callback.answer(text=f"⏳ Формируем данные для оплаты...")

    # get_pay:{stream_id}:{price_menu}:{product_id}:{directions_id}
    # set_group:{directions_id}' Back

    logging.debug("Callback = %s:", callback.data)

    list_data_buttons = callback.data.split(':')
    stream_id_int = int(list_data_buttons[1])
    price = int(list_data_buttons[2])

    ######################## ФОРМИРУЕМ USER_KEY ########################

    user_key = StorageKey(
        bot_id=callback.bot.id,
        chat_id=callback.from_user.id,  # личный чат пользователя
        user_id=callback.from_user.id,  # сам пользователь
    )

    #################### ПОЛУЧАЕМ ДАННЫЕ ПО ОПЛАТЕ #####################

    user_pay_data = await state.storage.get_data(key=user_key)

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

    # stream_info = await get_stream_info(id_stream=stream_id_int)

    ######################## Получаем Информаци о пользователе #################

    user_info_dict = await get_user_info_by_tg_id(tg_user_id=callback.from_user.id)

    ############################ Обновляем Email ###############################

    # await update_user_email(user_id_from_db=user_info_dict['id'], new_email=email)

    ######################## Записываем Данные об оплате ######################

    payments_data_dict = {"provider": "PLATEGA",
                          "amount": price,
                          "operation_id": "",
                          "status": "CREATE",
                          "user_id": user_info_dict["id"]}

    #################### Добавляем в БД запись об оплате и получаем ссылку на оплату ###########################

    payment_data_from_db = await add_payments_operation(payments_data=payments_data_dict)

    ########################### Получаем Данные о платеже от Провайдера Эквайринга #############################

    payments_data_from_bd = get_payment_link_data(payment_method=PaymentMethod.CARD_ACQUIRING, amount=float(price))
    try:
        url_pay_from_provider = payments_data_from_bd.get('payment_link',
                                                      'Что-то пошло не так... повторите попытку позже.')
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

    ###################### Сохраняем данные Пользователю в FSM #########################

    user_data = dict(stream_id_int=stream_id_int,
                     price=price,
                     operation_id=payments_data_from_bd.get('operation_id_from_provider', 'none_operation_id'),
                     payment_id=payment_data_from_db.id)

    await state.storage.update_data(user_key, data=user_data)  # <— сохраняем для ЭТОГО пользователя

    ############################## Платежные Реквизиты ##############################

    payment_details = (
        f"Способ оплаты: КАРТА РФ 🇷🇺\n\n"
        f"К оплате: {price} 🇷🇺RUB\n"
        f"Ваш ID: {user_info_dict['telegram_id']}\n\n"
        "Реквизиты для оплаты:\n\n"
        f"Ссылка на оплату:\n{url_pay_from_provider}\n\n"
        f"После оплаты вам будут доступны ключи доступа.\n"
    )

    directions_id = user_pay_data.get("directions_id")

    buttons = get_payment_notification_button(price=f"{price}", stream_id=stream_id_int, directions_id=directions_id)
    photo = FSInputFile('source/pictures/payment.png')
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
        payments_operation_data = get_payment_link_data(payment_method=PaymentMethod.CARD_ACQUIRING, amount=10)
        print(payments_operation_data)
    except Exception as e:
        print(e)
