import asyncio
import logging
import os
import re
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto

from db.select_methods import (
    get_enrollmet_info,
    get_product_info,
    get_stream_info,
    get_user_info_by_tg_id,
)
from keyboards.get_menu import get_main_menu_button
from utils.gen_qr_code import get_qr_code

router = Router()



"""

Обработка Доступов Пользователя

"""


# f"get_creds:{enrolment.id}"
# get_my_subscribe:{one_user_info['id']} <- get_creds


@router.callback_query(F.data.startswith("get_creds:"))
async def get_creds_message(callback: CallbackQuery, state: FSMContext):
    # "get_creds:{enrolment.id}"

    list_data_buttons = callback.data.split(":")

    # telegram_id = callback.from_user.id

    ############################ Делаем Запросы в БД #######################################

    enrollment_info = await get_enrollmet_info(id_enrollment=int(list_data_buttons[1]))
    # product_info = await get_product_info(id_product=enrollment_info.product_id)
    # stream_info = await get_stream_info(id_stream=enrollment_info.stream_id)
    # user_info = await get_user_info_by_tg_id(tg_user_id=telegram_id)

    await callback.answer(f"Вы выбрали: {enrollment_info.title_product}")

    ####################### ЕБАНЫЕ КНОПКИ НАЗАД ВПЕРЕД ####################################

    buttons_reply_markup = get_main_menu_button(user_bd_id=enrollment_info.user_id)

    ########################################################################################

    veles_link = f"Ссылка для подключения:\n\n<code>{enrollment_info.vless_link}</code>"
    qrcode_path = get_qr_code(veless_url=enrollment_info.vless_link)

    if os.path.exists(qrcode_path):
        new_media = InputMediaPhoto(
            media=FSInputFile(qrcode_path),
            caption=veles_link,
            parse_mode="HTML")
    else:
        new_media = InputMediaPhoto(
            media=FSInputFile("source/pictures/my_subscribe.png"),
            caption="Ссылка не найдена.\nОбратитесь в поддержку.",
            parse_mode="HTML")

    await callback.message.edit_media(
        media=new_media,
        reply_markup=buttons_reply_markup
    )

    if os.path.exists(qrcode_path):
        os.remove(qrcode_path)

    return