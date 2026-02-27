import logging
from pprint import pprint

from aiogram import Router, F
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import Message, InputMediaPhoto

from handlers.get_creds import get_creds_message
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
                f'📡 Самый быстрый VPN с серверами по всему миру и защитой.\n\n'
                f'🛠️️ Техподдержка 24/7 в чате.\n\n'
                f'💬 Контакты: @user_post\n\n'
                f'📜 Политика конфиденциальности:\n'
                f'https://telegra.ph/Politika-konfidencialnosti-08-15-17\n\n'
                f'⚖️ Пользовательское соглашение:\n'
                f'https://telegra.ph/Polzovatelskoe-soglashenie-08-15-10\n\n'
                f'👇 Выбери нужный вариант!\n\n')

# start greetings diirections_list -> set_group:{button['id'] choosing_direction

# @router.message(CommandStart(deep_link=True))
# async def start_with_param(message: Message, command: CommandObject, state: FSMContext):
#     await state.clear()
#
#     param = command.args  # Получаем параметр из deep link
#
#     # start="setproduct_{product_id}"
#
#     list_buttons_data = param.split("_")
#     product_id = int(list_buttons_data[1])
#
#     ################## Обрабатываем нужный продукт и передаем на оплату ################
#     logging.debug("Выбран продукт %s", product_id)
#     product_pydantic = await get_product_info(id_product=product_id)
#
#     ############# Проверяем статус пользователя в БД. #######
#
#     one_user = {"telegram_id": int(message.from_user.id),
#                 "username": str(message.from_user.username),
#                 "password": ""}
#
#     user_info = await check_user_and_add(user_data=one_user)
#
#     logging.info(
#         "Выбран продукт: %s\nИмеет Потоки: %s",
#         product_pydantic.title,
#         product_pydantic.streams,
#     )
#     # direction_id = product_pydantic.direction_id
#     product_description = str(product_pydantic.description)
#     price = str(product_pydantic.price)
#     # product_title_normalized = (product_pydantic.title or "").strip().lower()
#
#     ################# Формируем сообщение и кнопки для пользователя ######################
#
#     # set_stream
#     today = get_moscow_today()
#     streams_list = [
#         stream
#         for stream in (product_pydantic.streams or [])
#         if stream.end_date is None or stream.end_date >= today
#     ]
#
#     new_photo = FSInputFile(f"source/pictures/{product_pydantic.title.lower()}.png")
#     buttons = await get_stream_products_menu(
#         streams_list=streams_list,
#         directions_id=product_pydantic.direction_id,
#         price_menu=price,
#     )
#     new_caption = product_description.replace("|", "\n")
#     if not streams_list:
#         new_caption += "\n\n⏳ Стартов сейчас нет. Напишите нам, чтобы узнать о следующих."
#
#     # media = InputMediaPhoto(media=new_photo, caption=new_caption, parse_mode="HTML")
#     # await callback.message.edit_media(media=media, reply_markup=buttons)
#     await message.bot.send_photo(chat_id=user_info.get("telegram_id"),
#                                  photo=new_photo,
#                                  caption=new_caption,
#                                  parse_mode="HTML",
#                                  reply_markup=buttons)


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
