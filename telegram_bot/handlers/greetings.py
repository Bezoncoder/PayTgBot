import logging
from pprint import pprint

from aiogram import Router, F
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import Message, InputMediaPhoto

from keyboards.get_menu import get_start_menu, get_stream_products_menu
from aiogram.types import FSInputFile

from db.select_methods import get_list_directions, get_product_info, get_user_info_by_tg_id, get_enrollmets_from_user_id
from db.add_methods_dao import check_user_and_add

from aiogram.fsm.context import FSMContext

from aiogram.types import CallbackQuery

# from settings.config import START_DATE
# from settings.config import START_DATE
from utils.get_links import get_subscribe_link
from utils.timezone import get_moscow_today

router = Router()


START_CAPTION = (f'🚀 **Добро пожаловать!**\n\n'
                f'✅ Отличный выбор!\n\n'
                f'📡 Самый быстрый VPN с серверами по всему миру и защитой.\n'
                f'🌐 Наш Сайт: <a href="https://quantumturbovpn.ddns.net/">QuantumTurboVPN</a>\n'
                f'📺 Как подключить: <a href="https://t.me/QuantumTurboVPN/351">смотреть видео</a>\n'
                f'🛠️️ Техподдержка 24/7 в чате.\n\n'
                f'👇 Выбери нужный вариант!\n\n')

# def get_main_window_menu():



@router.message(CommandStart(deep_link=True))
async def start_with_param(message: Message, command: CommandObject, state: FSMContext):

    #https://t.me/QuantumTurboVPNBot?start=seregavk_9999999

    # start="{refer_name}_{user_id}" -> set_start

    await state.clear()

    param = command.args  # Получаем параметр из deep link

    list_buttons_data = param.split("_")
    refer_name = list_buttons_data[0]
    user_id = int(list_buttons_data[1])

    one_user = {"telegram_id": int(message.from_user.id),
                "username": str(message.from_user.username),
                "password": refer_name}

    logging.info(
        "Зафиксирован переход по реферальной ссылке: %s\nОт пользователя user_id = : %s",
        refer_name,
        user_id,
    )

    ############# Проверяем статус пользователя в БД и создаем кнопки. ############################

    user_info = await check_user_and_add(user_data=one_user)
    diirections_list = await get_list_directions()
    start_menu = await get_start_menu(list_for_menu=diirections_list, one_user_info=user_info)

    #############################################################################

    photo = FSInputFile('source/pictures/vpn_main_menu.jpg')
    await message.answer_photo(photo=photo,
                               caption=START_CAPTION,
                               reply_markup=start_menu,
                               parse_mode="HTML")








@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    logging.debug("cmd_start")

    await state.clear()

    one_user = {"telegram_id": int(message.from_user.id),
                "username": str(message.from_user.username),
                "password": ""}

    ############# Проверяем статус пользователя в БД и создаем кнопки. ############################

    user_info = await check_user_and_add(user_data=one_user)
    diirections_list = await get_list_directions()
    start_menu = await get_start_menu(list_for_menu=diirections_list, one_user_info=user_info)

    #############################################################################

    photo = FSInputFile('source/pictures/vpn_main_menu.jpg')
    await message.answer_photo(photo=photo,
                               caption=START_CAPTION,
                               reply_markup=start_menu,
                               parse_mode="HTML")


@router.callback_query(F.data == "set: start")
async def set_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Вы выбрали Главное Меню")

    photo = FSInputFile('source/pictures/vpn_main_menu.jpg')

    logging.debug("set: start")

    one_user = {"telegram_id": int(callback.from_user.id),
                "username": str(callback.from_user.username),
                "password": ""}

    ############# Проверяем статус пользователя в БД и создаем кнопки. ############################

    user_info = await check_user_and_add(user_data=one_user)
    diirections_list = await get_list_directions()
    start_menu = await get_start_menu(list_for_menu=diirections_list, one_user_info=user_info)

    #############################################################################
    await state.clear()

    # Вариант с изменением сообщения без удаления.
    media = InputMediaPhoto(
        media=photo,
        caption=START_CAPTION,
        reply_markup=start_menu,
        parse_mode="HTML")

    await callback.bot.edit_message_media(media=media,
                                          chat_id=one_user["telegram_id"],
                                          message_id=callback.message.message_id,
                                          reply_markup=start_menu)
