from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message

from aiogram.fsm.storage.base import StorageKey

from aiogram.fsm.context import FSMContext
import asyncio

from keyboards.get_menu import get_products_menu
from db.select_methods import get_all_product_from_direction_id
from settings.config import URL, HOME_PAGE
# from utils.jira_functional.jira_functions import onboard_user_with_tasks

from utils.gen_ssl_key import get_signed_cert
from utils.get_links import get_subscribe_link
from utils.creds import get_creds
from utils.calculate_expire_date import get_expire_time_sec
import datetime as DT
import os


'''

Обрабатываем выбор направления пользователя.

'''


router = Router()

# set_group:{button['id'] choosing_direction list_products -> set_product:{button.id} choosing_product
# set_group:{button['id'] -> set_product:{button.id} -> set_stream:{button.id}:{price_menu} ->
@router.callback_query(F.data.startswith("set_group:"))
async def set_group(callback: CallbackQuery, state: FSMContext):

    await callback.answer("🌍 Серверы VPN")

    list_data_buttons = callback.data.split(':')
    group_id = int(list_data_buttons[1])

    list_products_pydantic = await get_all_product_from_direction_id(group_id=group_id)

    list_length = len(list_products_pydantic)

    if list_length > 1:
        choice_text = str(list_length)+' крутых продукта'
    else:
        choice_text ='крутой продукт'

    products_buttons = await get_products_menu(list_of_products=list_products_pydantic)
    photo = FSInputFile('source/pictures/choose_product.png')

    media = InputMediaPhoto(
        media=photo,
        caption=f"✅ Отличный выбор!\n\n"
                f"🌐 Обход блокировок: "
                f"Instagram, YouTube, Netflix...\n"
                f"⚡ Ускорение Интернета.\n"
                f"🛡️ Техподдержка 24/7 в чате.\n"
                f"🎯 У нас есть {choice_text} для тебя!!!\n\n"
                f'🌐 Все детали на:\n\n f"{HOME_PAGE}"\n\n'
                f"👇 Выбери то, что тебе нужно\n",
        parse_mode='HTML'
    )

    await callback.message.edit_media(media=media, reply_markup=products_buttons)
