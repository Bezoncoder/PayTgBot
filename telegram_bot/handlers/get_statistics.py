import datetime
import logging

from dateutil.relativedelta import relativedelta
from aiogram import Router, F
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import Message, InputMediaPhoto

from keyboards.get_menu import get_start_button, get_admin_button, get_errors_button
from aiogram.types import FSInputFile

from aiogram.fsm.context import FSMContext

from aiogram.types import CallbackQuery

from db.statistics import get_products_statistics, get_users_statistics

from payment_tools.platega_api_web_panel import PlategaWebClient
from utils.states import OrderPay

router = Router()

# @router.callback_query(F.data == "get_statistics")
# async def get_utils(callback: CallbackQuery, state: FSMContext):
#     await callback.answer("Вы выбрали Админ Меню")
#
#     photo = FSInputFile('source/pictures/admin_utils.jpg')
#
#     storage = state.storage
#
#     key = StorageKey(
#         bot_id=callback.bot.id,
#         chat_id=callback.message.chat.id,  # личный чат пользователя
#         user_id=callback.from_user.id  # сам пользователь
#
#     )
#
#     admin_user_data = dict(
#         message_id=callback.message.message_id
#     )
#
#     await state.storage.update_data(key=key, data=admin_user_data)
#
#
#     # await storage.set_state(key, OrderPay.check_id_message)
#     state_from_user = await storage.get_state(key)
#
#     logging.debug(f"Состояние для пользователя user_id = {callback.from_user.id} установлено: {state_from_user}")
#
#     #####################################################################################################
#
#     buttons = get_admin_button()
#
#     caption = (
#         f"⚙️ Админ-панель\n\n"
#         f"Выберите нужное действие:\n\n"
#         f"💰 Посмотреть баланс\n"
#         f"🆔 Узнать ID\n"
#         f"💰🛠️ Тестовая покупка\n"
#         f"🏠 Вернуться в главное меню"
#     )
#
#     # Вариант с изменением сообщения без удаления.
#     media = InputMediaPhoto(
#         media=photo,
#         caption=caption,
#         parse_mode="HTML")
#
#     await callback.bot.edit_message_media(media=media,
#                                           chat_id=callback.from_user.id,
#                                           message_id=callback.message.message_id,
#                                           reply_markup=buttons)
#
#

@router.callback_query(F.data == "get_statistics")
async def get_statistics(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Вы выбрали Меню статистики")

    photo = FSInputFile('source/pictures/get_balance.jpg')

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


    await storage.set_state(key, OrderPay.set_order)
    state_from_user = await storage.get_state(key)

    logging.debug(f"Состояние для пользователя user_id = {callback.from_user.id} установлено: {state_from_user}")

    ################################ GET_STATISTICS #####################################################

    users_statistics = await get_users_statistics()
    products_statistics = await get_products_statistics()

    if users_statistics is None:
        caption = (
            "⚠️ <b>Статистика временно недоступна</b>\n\n"
            "Не удалось получить данные."
        )
    else:
        caption = (
            "📊 <b>Статистика проекта</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"

            "<b>👥 Пользователи</b>\n"
            "<pre>"
            f"Всего пользователей : {users_statistics.all_users}\n"
            f"Новых за месяц      : {users_statistics.new_users_this_month}\n"
            f"Активных            : {users_statistics.active_users}\n"
            f"Повторных покупок   : "
            f"{users_statistics.users_with_two_or_more_purchases}\n"
            "</pre>\n"

            "<b>💳 Покупки по тарифам</b>\n"
        )

        if products_statistics is None:
            caption += "⚠️ Данные по тарифам временно недоступны."

        elif not products_statistics:
            caption += "ℹ️ Тарифы пока не найдены."

        else:
            caption += (
                "<pre>"
                "Тариф                 Прошл.  Текущ.\n"
                "────────────────────  ──────  ──────\n"
            )

            for item in products_statistics:
                title = (item.stream_title or "Без названия")[:20]

                caption += (
                    f"{title:<20}  "
                    f"{item.purchases_last_month:>6}  "
                    f"{item.purchases_this_month:>6}\n"
                )

            caption += "</pre>"


    #####################################################################################################

    buttons = get_admin_button()

    await callback.bot.delete_message(chat_id=callback.message.chat.id,
                                      message_id=callback.message.message_id)
    logging.debug("Сообщение 'get_statistics' удалено.")

    # await callback.bot.edit_message_media(media=media,
    #                                       chat_id=callback.from_user.id,
    #                                       message_id=callback.message.message_id,
    #                                       reply_markup=buttons)

    await callback.bot.send_photo(chat_id=callback.message.chat.id,
                                  photo=photo,
                                  caption=caption,
                                  parse_mode="HTML",
                                  reply_markup=buttons)

    logging.debug("Сообщение 'get_statistics' отправлено.")



