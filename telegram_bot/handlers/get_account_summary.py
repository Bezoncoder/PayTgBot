import datetime
import logging
from calendar import month
from pprint import pprint

from aiogram.fsm import storage
from dateutil.relativedelta import relativedelta
from aiogram import Router, F
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import Message, InputMediaPhoto

from db.schemas import EnrollmentPydantic
from keyboards.get_menu import get_start_menu, get_stream_products_menu, get_start_button, get_admin_button, \
    get_account_summary_button
from aiogram.types import FSInputFile

from db.select_methods import get_list_directions, get_product_info, get_user_info_by_tg_id, get_enrollmets_from_user_id
from db.add_methods_dao import check_user_and_add

from aiogram.fsm.context import FSMContext

from aiogram.types import CallbackQuery

from settings.config import LOGIN_WEB_PLATEGA, PASSWORD_WEB_PLATEGA
# from settings.config import START_DATE
# from settings.config import START_DATE
from utils.get_links import get_subscribe_link
from utils.platega_api_web_panel import PlategaWebClient
from utils.states import OrderPay
from utils.timezone import get_moscow_today

router = Router()

@router.callback_query(F.data == "get_account_summary_menu")
async def get_account_summary_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Вы выбрали Меню Сводка по аккаунту ")

    photo = FSInputFile('source/pictures/get_account_summary_menu.jpg')

    storage = state.storage

    key = StorageKey(
        bot_id=callback.bot.id,
        chat_id=callback.message.chat.id,  # личный чат пользователя
        user_id=callback.from_user.id  # сам пользователь

    )

    admin_user_data = dict(
        message_id=callback.message.message_id
    )

    await state.storage.update_data(key=key, data=admin_user_data)


    # await storage.set_state(key, OrderPay.check_id_message)
    # state_from_user = await storage.get_state(key)

    await storage.set_state(key, OrderPay.get_account_summary)

    state_from_user = await storage.get_state(key)

    logging.debug(f"Состояние для пользователя user_id = {callback.from_user.id} установлено: {state_from_user}")

    #####################################################################################################

    buttons = get_account_summary_button(user_tg_id=None)

    caption = (
        f"📊 Сводка по аккаунту\n\n"
        f"Хотите получить полную информацию о пользователе?\n"
        f"Просто перешлите сообщение от него в этот чат — и бот автоматически сформирует сводку.\n\n"
        f"💡 Доступная статистика и активные покупки будут отображены в ответе."
    )

    # Вариант с изменением сообщения без удаления.
    media = InputMediaPhoto(
        media=photo,
        caption=caption,
        parse_mode="HTML")

    await callback.bot.edit_message_media(media=media,
                                          chat_id=callback.from_user.id,
                                          message_id=callback.message.message_id,
                                          reply_markup=buttons)

@router.message(OrderPay.get_account_summary)
async def check_account_summary_from_message(message: Message, state: FSMContext):

    #TODO ДЕЛАЕМ ЗАПРОС В БД, ЧТОБЫ УЗНАТЬ ПОДПИСКИ!!!!!!!!!!!!!!!!!!!

    # GET USER ENROLMENTS

    user_info = await get_user_info_by_tg_id(tg_user_id=message.forward_from.id)

    # user_enrolments = [EnrollmentPydantic]



    caption = (
        f"📋 Активные подписки пользователя\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )

    for enrolment in user_info.enrollments:
        if enrolment.active:
            caption.join(f"🏷️ VelesName: <code>{enrolment.vless_user_name}</code>\n")
            caption.join(f"🔗 Link: <code>{enrolment.vless_link}</code>\n\n")

    await message.bot.delete_message(chat_id=message.from_user.id, message_id=message.message_id)


    key = StorageKey(
        bot_id=message.bot.id,
        chat_id=message.chat.id,  # личный чат пользователя
        user_id=message.from_user.id  # сам пользователь

    )

    await state.storage.set_state(key, None)

    admin_user_data = await state.storage.get_data(key=key)

    buttons = get_account_summary_button(user_tg_id=int(message.forward_from.id))

    # Вариант с изменением сообщения без удаления.
    photo = FSInputFile('source/pictures/check_account_summary.jpg')

    media = InputMediaPhoto(
        media=photo,
        caption=caption,
        parse_mode="HTML")



    await message.bot.edit_message_media(media=media,
                                          chat_id=message.from_user.id,
                                          message_id=admin_user_data.get("message_id", 000),
                                          reply_markup=buttons)





# @router.callback_query(F.data == "del_info_message")
# async def del_info_message(callback: CallbackQuery, state: FSMContext):
#     await callback.answer("Удаляем информационное сообщение")
#     await callback.bot.delete_message(chat_id=callback.message.chat.id,
#                                       message_id=callback.message.message_id)




@router.callback_query(F.data.startswith("get_user_summary:") )
async def get_user_summary(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Вы выбрали меню: Сводка по аккаунту")
    logging.info(f"Сводка по аккаунту")

    list_data_buttons = callback.data.split(":")
    user_tg_id = int(list_data_buttons[1])

    #TODO СДЕЛАТЬ ЗАПРОС В БД И СОБРАТЬ АНАЛИТИКУ!!!!!

    # GET USER ENROLMENTS ALL

    user_info = await get_user_info_by_tg_id(tg_user_id=user_tg_id)

    user_enrolments = user_info.enrollments
    active_link = 0
    for enrolment in user_enrolments:
        if enrolment.active:
            active_link += 1

    caption = (
        f"📊 Статистика по пользователю\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Активных подписок: {active_link}\n"
        f"📦 Всего подписок: {len(user_enrolments)}"

    )

    photo = FSInputFile('source/pictures/get_user_summary.jpg')

    storage = state.storage

    key = StorageKey(
        bot_id=callback.bot.id,
        chat_id=callback.message.chat.id,  # личный чат пользователя
        user_id=callback.from_user.id  # сам пользователь

    )

    admin_user_data = dict(
        message_id=callback.message.message_id
    )

    await state.storage.update_data(key=key, data=admin_user_data)


    # await storage.set_state(key, OrderPay.check_id_message)

    await storage.set_state(key, None)
    state_from_user = await storage.get_state(key)


    logging.debug(f"Состояние для пользователя user_id = {callback.from_user.id} установлено: {state_from_user}")

    #####################################################################################################

    buttons = get_account_summary_button(user_tg_id=None)



    # Вариант с изменением сообщения без удаления.
    media = InputMediaPhoto(
        media=photo,
        caption=caption,
        parse_mode="HTML")

    await callback.bot.edit_message_media(media=media,
                                          chat_id=callback.from_user.id,
                                          message_id=callback.message.message_id,
                                          reply_markup=buttons)


