import logging
from aiogram import Router, F
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from db.statistics import get_products_statistics, get_users_statistics, get_products_by_title_statistics
from keyboards.get_menu import get_admin_button
from utils.states import OrderPay

router = Router()


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
    products_by_title_statistics = await get_products_by_title_statistics()

    if users_statistics is None:
        caption = (
            "⚠️ <b>Статистика временно недоступна</b>\n\n"
            "Не удалось получить данные по пользователям."
        )
    else:
        caption = (
            "📊 <b>Статистика QuantumTurboVPN</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👥 <b>Пользователи</b>\n"
            f"• Всего: <b>{users_statistics.all_users}</b>\n"
            f"• Новых за текущий месяц: <b>{users_statistics.new_users_this_month}</b>\n"
            f"• Активных: <b>{users_statistics.active_users}</b>\n"
            f"• Повторных покупателей: "
            f"<b>{users_statistics.users_with_two_or_more_purchases}</b>\n\n"
            "💳 <b>Покупки по тарифам</b>\n"
        )

        if products_statistics is None:
            caption += "• Данные по тарифам временно недоступны.\n"

        elif not products_statistics:
            caption += "• Тарифы пока не найдены.\n"

        else:
            for item in products_statistics:
                stream_title = item.stream_title or "Без названия"

                caption += (
                    f"• <b>{stream_title}</b>\n"
                    f"   Прошлый месяц: <b>{item.purchases_last_month}</b>\n"
                    f"   Текущий месяц: <b>{item.purchases_this_month}</b>\n"
                )

        caption += "\n🛒 <b>Покупки по продуктам</b>\n"

        if products_by_title_statistics is None:
            caption += "• Данные по продуктам временно недоступны.\n"

        elif not products_by_title_statistics:
            caption += "• Продукты пока не найдены.\n"

        else:
            for item in products_by_title_statistics:
                product_title = item.stream_title or "Без названия"

                caption += (
                    f"• <b>{product_title}</b>\n"
                    f"   Прошлый месяц: <b>{item.purchases_last_month}</b>\n"
                    f"   Текущий месяц: <b>{item.purchases_this_month}</b>\n"
                )

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



