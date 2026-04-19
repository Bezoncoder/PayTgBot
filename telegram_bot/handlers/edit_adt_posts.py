import logging
from pprint import pprint

from aiogram import Router, F
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import Message, InputMediaPhoto

from keyboards.get_menu import get_start_menu, get_stream_products_menu, get_start_button
from aiogram.types import FSInputFile

from db.select_methods import get_list_directions, get_product_info, get_user_info_by_tg_id, get_enrollmets_from_user_id
from db.add_methods_dao import check_user_and_add

from aiogram.fsm.context import FSMContext

from aiogram.types import CallbackQuery

# from settings.config import START_DATE
# from settings.config import START_DATE
from utils.get_links import get_subscribe_link
from utils.states import OrderPay
from utils.timezone import get_moscow_today

router = Router()

ID = str

@router.callback_query(F.data == "edit_adt_posts")
async def set_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Вы выбрали Главное Меню")

    photo = FSInputFile('source/pictures/vpn_main_menu.jpg')

    storage = state.storage

    key = StorageKey(
        bot_id=callback.bot.id,
        chat_id=callback.from_user.id,  # личный чат пользователя
        user_id=callback.from_user.id  # сам пользователь

    )

    await storage.set_state(key, OrderPay.check_id_message)
    state_from_user = await storage.get_state(key)

    logging.debug(f"Состояние для пользователя user_id = {callback.from_user.id} установлено: {state_from_user}")

    #####################################################################################################

    buttons = get_start_button()
    ID = callback.message.message_id
    # Вариант с изменением сообщения без удаления.
    media = InputMediaPhoto(
        media=photo,
        caption="START_CAPTION",
        parse_mode="HTML")

    await callback.bot.edit_message_media(media=media,
                                          chat_id=callback.from_user.id,
                                          message_id=callback.message.message_id,
                                          reply_markup=buttons)

@router.message(OrderPay.check_id_message)
async def send_email_verification(message: Message, state: FSMContext):
    data = message.model_dump(exclude_none=True)

    text = "\n".join(f"{k}: {v}" for k, v in data.items())

    buttons = get_start_button()

    # Вариант с изменением сообщения без удаления.

    await message.bot.delete_message(chat_id=message.from_user.id, message_id=message.message_id)

    buttons = get_start_button()

    # Вариант с изменением сообщения без удаления.
    photo = FSInputFile('source/pictures/vpn_main_menu.jpg')

    media = InputMediaPhoto(
        media=photo,
        caption=text,
        parse_mode="HTML")

    await message.bot.edit_message_media(media=media,
                                          chat_id=message.from_user.id,
                                          message_id=ID,
                                          reply_markup=buttons)




