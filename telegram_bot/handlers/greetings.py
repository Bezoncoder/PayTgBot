import logging
from pprint import pprint

from aiogram import Router, F
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import Message, InputMediaPhoto
from aiogram.utils.deep_linking import decode_payload

from keyboards.get_menu import get_start_menu, get_stream_products_menu
from aiogram.types import FSInputFile

from db.select_methods import get_list_directions, get_product_info, get_user_info_by_tg_id, get_enrollmets_from_user_id
from db.add_methods_dao import check_user_and_add, add_new_referral_rewards

from aiogram.fsm.context import FSMContext

from aiogram.types import CallbackQuery

from settings.config import HOME_PAGE
# from settings.config import START_DATE
# from settings.config import START_DATE
from utils.get_links import get_subscribe_link
from utils.states import OrderPay
from utils.timezone import get_moscow_today

router = Router()


START_CAPTION = (f'🚀 **Добро пожаловать!**\n\n'
                f'✅ Отличный выбор!\n\n'
                f'📡 Самый быстрый VPN с серверами по всему миру и защитой.\n\n'
                f'🗝️ Один ключ на два устройства.\n\n'
                f'🌐 Наш Сайт: <a href="{HOME_PAGE}">QuantumTurboVPN</a>.\n\n'
                f'📺 Как подключить: <a href="https://t.me/QuantumTurboVPN/409">Инструкция для самых маленьких</a>.\n\n'
                f'🛠️️ Техподдержка 24/7 в чате.\n\n'
                f'👇 Выбери нужный вариант!\n\n')




@router.message(CommandStart(deep_link=True))
async def start_with_param(message: Message, command: CommandObject, state: FSMContext):

    # https://t.me/QuantumTurboVPNBot?start={reward_type}_{referred_by_user_id}

    # from aiogram.utils.deep_linking import create_start_link
    # link = await create_start_link(bot, "percent_123456789", encode=True)

    # start="{reward_type}_{referred_by_user_id}" -> set_start

    # await state.clear()

    payload = command.args
    if payload:
        param = decode_payload(payload)
        list_buttons_data = param.split("_")
        reward_type = list_buttons_data[0]
        referred_by_user_id = int(list_buttons_data[1])
    else:
        reward_type = None
        referred_by_user_id = None

    one_user = {"telegram_id": int(message.from_user.id),
                "username": str(message.from_user.username),
                "password": ""}

    logging.info(
        "Зафиксирован переход по реферальной ссылке: %s\nОт пользователя user_id = : %s",
        reward_type,
        referred_by_user_id)



    ############# Проверяем статус пользователя в БД и создаем кнопки. ############################

    user_info = await check_user_and_add(user_data=one_user)
    directions_list = await get_list_directions()
    start_menu = await get_start_menu(list_for_menu=directions_list, one_user_info=user_info)

    ############################ Делаем запись в ReferralRewards ##################################

    referral_rewards = dict(user_id=int(user_info.get("id")),
                            referred_user_id=referred_by_user_id,
                            payment_id=None,
                            reward_type=reward_type,
                            reward_value=None,
                            active_status=None)

    referral_rewards_info = await add_new_referral_rewards(referral_rewards_data=referral_rewards)

    logging.info(f"Добавлена запись referral_rewards_info:\n{referral_rewards_info}")

    #############################################################################

    photo = FSInputFile('source/pictures/vpn_main_menu.jpg')
    await message.answer_photo(photo=photo,
                               caption=START_CAPTION,
                               reply_markup=start_menu,
                               parse_mode="HTML")








@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    logging.debug("cmd_start")

    one_user = {"telegram_id": int(message.from_user.id),
                "username": str(message.from_user.username),
                "password": ""}

    ############# Проверяем статус пользователя в БД и создаем кнопки. ############################

    user_info = await check_user_and_add(user_data=one_user)
    diirections_list = await get_list_directions()
    start_menu = await get_start_menu(list_for_menu=diirections_list, one_user_info=user_info)

    ######################### Устанавливаем State для Пользователя ######################################

    # TODO FUNC FOR STATE

    storage = state.storage

    key = StorageKey(
        bot_id=message.bot.id,
        chat_id=message.from_user.id,  # личный чат пользователя
        user_id=message.from_user.id  # сам пользователь

    )

    await storage.set_state(key, OrderPay.set_order)

    state_from_user = await storage.get_state(key)

    logging.debug(f"Состояние для пользователя user_id = {message.from_user.id} установлено: {state_from_user}")

    #####################################################################################################

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

    ######################### Устанавливаем State для Пользователя ######################################

    # TODO FUNC FOR STATE

    storage = state.storage

    key = StorageKey(
        bot_id=callback.bot.id,
        chat_id=callback.from_user.id,  # личный чат пользователя
        user_id=callback.from_user.id  # сам пользователь

    )

    await storage.set_state(key, OrderPay.set_order)
    state_from_user = await storage.get_state(key)

    logging.debug(f"Состояние для пользователя user_id = {callback.from_user.id} установлено: {state_from_user}")

    #####################################################################################################

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
