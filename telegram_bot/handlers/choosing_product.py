import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message

from aiogram.fsm.storage.base import StorageKey

from aiogram.fsm.context import FSMContext
import asyncio

from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.get_menu import (
    get_change_user_data_dialog_button,
    get_products_menu,
    get_pay_buttons,
    get_stream_products_menu,
)
from db.select_methods import (
    get_enrollments_count_stream_id,
    get_enrollmets_from_user_id,
    get_product_info,
    get_user_info_by_tg_id,
)
from utils.timezone import get_moscow_today
from handlers.get_creds import get_creds_message

"""

Обрабатываем выбор продукта пользователя.

"""

router = Router()

# set_product:{button.id} choosing_product streams_list set_stream:{button.id}:{price_menu} -> choosing_stream
# set_group:{button['id'] <- set_product:{button.id} -> set_stream:{button.id}:{price_menu}
# source/pictures/choose_product.png


@router.callback_query(F.data.startswith("set_product:"))
async def set_product(callback: CallbackQuery, state: FSMContext):
    list_buttons_data = callback.data.split(":")
    product_id = int(list_buttons_data[1])

    ################## Обрабатываем нужный продукт и передаем на оплату ################
    logging.debug("Выбран продукт %s", product_id)
    product_pydantic = await get_product_info(id_product=product_id)

    await callback.answer(text=f"Выбран продукт {product_pydantic.title}")

    ################## Проверяем, не куплен ли продукт ранее #################
    # user_info = await get_user_info_by_tg_id(tg_user_id=callback.from_user.id)
    logging.info(
        "Выбран продукт: %s\nИмеет Тарифы: %s",
        product_pydantic.title,
        product_pydantic.streams,
    )


    ###################### Сохраняем данные Пользователю в FSM #########################
    user_key = StorageKey(
        bot_id=callback.bot.id,
        chat_id=callback.from_user.id,  # личный чат пользователя
        user_id=callback.from_user.id,  # сам пользователь
    )

    direction_id = product_pydantic.direction_id

    user_data = dict(directions_id=direction_id)

    await state.storage.update_data(user_key, data=user_data)  # <— сохраняем для ЭТОГО пользователя

    product_description = str(product_pydantic.description)

    ################################### PRICE #############################################
    price = str(100) # Не используется
    # product_title_normalized = (product_pydantic.title or "").strip().lower()

    ################# Формируем сообщение и кнопки для пользователя ######################
    enrollments_count = await get_enrollments_count_stream_id(product_id=product_pydantic.id)
    # new_photo = FSInputFile(f"source/pictures/{product_pydantic.title.lower()}.png")
    new_photo = FSInputFile(f"source/pictures/choose_tariff.jpg")
    buttons = await get_stream_products_menu(
        streams_list=product_pydantic.streams,
        product_capacity=product_pydantic.capacity,
        directions_id=product_pydantic.direction_id,
        price_menu=price,
        enrollments_count=enrollments_count)

    if product_pydantic.capacity > enrollments_count:
        new_caption = product_description.replace("|", "\n")
    else:
        new_caption_product = product_description.replace("|", "\n")

        new_caption = (f"{new_caption_product}\n\n"
                       "🔒 Ключи отсутствуют\n"
                       "Все лицензии для этого сервера распроданы\n\n"
                       "👈 Нажмите «Назад» для выбора альтернативы")

    media = InputMediaPhoto(media=new_photo, caption=new_caption, parse_mode="HTML")

    await callback.message.edit_media(media=media, reply_markup=buttons)


