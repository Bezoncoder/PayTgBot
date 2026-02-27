import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InputMediaPhoto, FSInputFile

from aiogram.fsm.storage.base import StorageKey

from aiogram.fsm.context import FSMContext

from db.select_methods import (
    get_user_info_by_tg_id,
    get_enrollmets_from_user_id,
    get_stream_info,
)
from db.add_methods_dao import set_full_name
from keyboards.get_menu import (
    get_change_user_data_dialog_button,
    get_subscribe_menu,
)
# from db.select_methods import get_expire_date_user_id

# from utils.jira_functional.jira_functions import onboard_user_with_tasks
from utils.states import OrderPay  # <— добавлено

router = Router()


@router.message(OrderPay.send_email, F.text)
async def send_email_verification(message: Message, state: FSMContext):
    email_from_massage = message.text.strip()

    user_email_data = dict(
        email=email_from_massage
    )

    user_key = StorageKey(
        bot_id=message.bot.id,
        chat_id=message.chat.id,  # личный чат пользователя
        user_id=message.from_user.id,  # сам пользователь
    )
    await state.storage.update_data(key=user_key, data=user_email_data)



    confirmation_text = (
        f"{email_from_massage}\n\nВаши данные указаны Верно?\n"
    )
    await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


    #################### ПОЛУЧАЕМ ДАННЫЕ ПО ОПЛАТЕ #####################

    user_pay_data = await state.storage.get_data(key=user_key)

    stream_id_int = user_pay_data.get("stream_id_int")
    price = user_pay_data.get("price")
    directions_id = user_pay_data.get("directions_id", "")

    # get_pay:stream_id:price:directions_id
    list_callback = [f'get_pay:{price}:{directions_id}', 'get_payment_details:']
    buttons = get_change_user_data_dialog_button(callback_data_list=list_callback)
    await message.bot.send_message(chat_id=message.chat.id, text=confirmation_text, reply_markup=buttons)
