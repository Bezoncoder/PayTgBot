import logging

from aiogram import Router, F
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, FSInputFile

from db.select_methods import (
    get_enrollmets_from_user_id,
    get_product_info,
    get_stream_info,
)
from keyboards.get_menu import get_subscribe_menu
from utils.timezone import get_moscow_today

router = Router()

"""

Рбота с подписками пользователей

"""


# get_my_subscribe:{one_user_info['id']}


@router.callback_query(F.data.startswith("get_my_subscribe:"))
async def get_creds_subscribe(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Список Ваших подписок")
    list_data_buttons = callback.data.split(":")

    ############################## ПОЛУЧАЕМ ПОТОКИ ##################################
    today_date = get_moscow_today()
    enrolments_list = await get_enrollmets_from_user_id(
        id_user=list_data_buttons[1],
        today_date=today_date

    )

    #################################################################################

    await state.clear()

    if enrolments_list:
        buttons = get_subscribe_menu(enrolments=enrolments_list)
        new_caption = f"Вот что Вам сейчас доступно.\n\n"\
                      f"Чтобы получить доступы, нажмите соотвествющую кнопку.\n\n"\
                      f"👇 Выбери то, что тебе нужно!!!"
    else:
        buttons = get_subscribe_menu(enrolments=None)
        new_caption = (
            f"📭 Нет активных подписок\n\n"
            f"🔒 Выберите VPN в главном меню\n\n"
            f"🛒 После покупки:\n\n"
            f"✅ Ключи станут доступны здесь автоматически"
        )

    photo = FSInputFile("source/pictures/my_subscribe.png")

    # Вариант с изменением сообщения без удаления.
    media = InputMediaPhoto(
        media=photo,
        caption=new_caption,
        parse_mode="HTML"
    )

    await callback.bot.edit_message_media(
        media=media,
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=buttons
    )
