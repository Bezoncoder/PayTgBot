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

from settings.config import LOGIN_WEB_PLATEGA, PASSWORD_WEB_PLATEGA, TECH_CHANNEL
# from settings.config import START_DATE
# from settings.config import START_DATE
from payment_tools.platega_api_web_panel import PlategaWebClient
from utils.states import OrderPay

router = Router()

@router.callback_query(F.data == "get_utils")
async def get_utils(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Вы выбрали Админ Меню")

    photo = FSInputFile('source/pictures/admin_utils.jpg')

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
    state_from_user = await storage.get_state(key)

    logging.debug(f"Состояние для пользователя user_id = {callback.from_user.id} установлено: {state_from_user}")

    #####################################################################################################

    buttons = get_admin_button()

    caption = (
        f"⚙️ Админ-панель\n\n"
        f"Выберите нужное действие:\n\n"
        f"💰 Посмотреть баланс\n"
        f"🆔 Узнать ID\n"
        f"🏠 Вернуться в главное меню"
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



@router.callback_query(F.data == "get_balance")
async def get_balance(callback: CallbackQuery, state: FSMContext):
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

    ################################ PlategaWebClient #####################################################

    try:
        logging.debug("💳 Подключаемся к платежному шлюзу WEB API")
        platega_web_client = PlategaWebClient(login=LOGIN_WEB_PLATEGA,
                                              password=PASSWORD_WEB_PLATEGA)

    except Exception as exception_text:
        # < code > текст < / code >
        buttons = get_errors_button()
        await callback.message.edit_caption(caption=(f"❌ <b>Что-то пошло не так</b>… Повторите попытку позже\n\n"
                                                    f"📢 <b>Ошибка: </b>\n\n"
                                                    f"<code>{exception_text}</code>"),
                                            parse_mode="HTML",
                                            reply_markup=buttons)
        return


    balance_rub = platega_web_client.get_balance()
    balance_usdt = platega_web_client.get_balance(currencycode="USDT")
    today__date_iso = datetime.datetime.now().date().isoformat()
    statistics_today = platega_web_client.get_statistics_by_currency(date_start=str(today__date_iso), date_end=str(today__date_iso))

    if not statistics_today.statsByCurrency:
        today_sale = 0
    else:
        today_sale = statistics_today.statsByCurrency[0].turnover

    date_start_stat = datetime.datetime.now().replace(day=1).date().isoformat()

    month_to_date_stat = platega_web_client.get_statistics_by_currency(date_start=date_start_stat,
                                                                       date_end=today__date_iso)

    if not month_to_date_stat.statsByCurrency:
        month_to_now_date = 0
    else:
        month_to_now_date = month_to_date_stat.statsByCurrency[0].turnover


    start_prev_month_date = (datetime.datetime.now().replace(day=1) - relativedelta(months=1)).date().isoformat()
    end_prev_month_date = (datetime.datetime.now().replace(day=1) - relativedelta(days=1)).date().isoformat()


    previous_month = platega_web_client.get_statistics_by_currency(date_start=str(start_prev_month_date),
                                                                   date_end=str(end_prev_month_date))

    # "Month-to-Date"
    # previous_month
    # "🧊 Заморожено: "

    buttons = get_admin_button()

    caption = (
        f"🌐 <b>My.Platega</b>\n"
        f"<a href='https://my.platega.io'>Перейти в кабинет</a>\n"
        f"━━━━━━━━━━━━━━\n"
        f"💰 <b>Баланс</b>\n"
        f"  • {balance_rub.amount:} {balance_rub.currency}\n"
        f"  • {balance_usdt.amount:} {balance_usdt.currency}\n"
        f"━━━━━━━━━━━━━━\n"
        f"📈 <b>Оборот</b>\n"
        f"• Прошлый месяц ({start_prev_month_date}-{end_prev_month_date}): "
        f"  {previous_month.statsByCurrency[0].netProfit} RUB\n"
        f"• С начала месяца ({date_start_stat}-{today__date_iso}): "
        f"  {month_to_now_date} RUB\n"
        f"• Сегодня: {today_sale} RUB"
    )


    await callback.bot.delete_message(chat_id=callback.message.chat.id,
                                      message_id=callback.message.message_id)
    logging.debug("Сообщение 'get_balance' удалено.")

    # await callback.bot.edit_message_media(media=media,
    #                                       chat_id=callback.from_user.id,
    #                                       message_id=callback.message.message_id,
    #                                       reply_markup=buttons)

    await callback.bot.send_photo(chat_id=callback.message.chat.id,
                                  photo=photo,
                                  caption=caption,
                                  parse_mode="HTML",
                                  reply_markup=buttons)

    logging.debug("Сообщение 'get_balance' отправлено.")


@router.callback_query(F.data == "get_id_message")
async def get_id_message(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Вы выбрали Узнать ID сообщения")

    photo = FSInputFile('source/pictures/get_id_message.jpg')

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


    await storage.set_state(key, OrderPay.check_id_message)
    state_from_user = await storage.get_state(key)

    logging.debug(f"Состояние для пользователя user_id = {callback.from_user.id} установлено: {state_from_user}")

    #####################################################################################################

    buttons = get_admin_button()
    caption = (
        f"🆔 Узнать ID\n\n"
        f"Чтобы узнать ID, просто перешлите сообщение для анализа в этот чат."
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


@router.message(OrderPay.check_id_message)
async def check_id_from_message(message: Message, state: FSMContext):
    # data = message.model_dump(exclude_none=True)
    # for k, v in data.items():
    #     logging.debug(f"{k} = ---- \n")

    # '''
    # forward_from_chat — чат, из которого переслали сообщение.
    #
    # forward_from_message_id — ID исходного сообщения в этом чате.
    #
    # forward_date — дата пересылки.
    #
    # forward_origin — более новый универсальный объект с информацией об источнике пересылки.
    # '''

    caption = (
        f"📩 Пересланное сообщение:\n\n"
        f"🆔 Chat ID: {message.forward_from_chat.id if message.forward_from_chat else '—'}\n"
        f"💬 Message ID: {message.forward_from_message_id if message.forward_from_message_id else '—'}"
    )

    logging.debug(caption)



    await message.bot.delete_message(chat_id=message.from_user.id, message_id=message.message_id)


    key = StorageKey(
        bot_id=message.bot.id,
        chat_id=message.chat.id,  # личный чат пользователя
        user_id=message.from_user.id  # сам пользователь

    )



    admin_user_data = await state.storage.get_data(key=key)

    buttons = get_start_button()

    # Вариант с изменением сообщения без удаления.
    photo = FSInputFile('source/pictures/get_id_message.jpg')

    media = InputMediaPhoto(
        media=photo,
        caption=caption,
        parse_mode="HTML")



    await message.bot.edit_message_media(media=media,
                                          chat_id=message.from_user.id,
                                          message_id=admin_user_data.get("message_id", 000),
                                          reply_markup=buttons)

    # await message.bot.copy_message(
    #     chat_id=message.from_user.id,
    #     from_chat_id=-1003976745616,
    #     message_id=message.forward_from_message_id
    # )



@router.callback_query(F.data == "del_info_message")
async def del_info_message(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Удаляем информационное сообщение")
    await callback.bot.delete_message(chat_id=callback.message.chat.id,
                                      message_id=callback.message.message_id)


if __name__ == "__main__":


    platega_client = PlategaWebClient(login=LOGIN_WEB_PLATEGA,
                                      password=PASSWORD_WEB_PLATEGA)



    start_prev_month = (datetime.datetime.now().replace(day=1) - relativedelta(months=1)).date().isoformat()
    end_prev_month = (datetime.datetime.now().replace(day=1) - relativedelta(days=1)).date().isoformat()


    month_to_date = platega_client.get_statistics_by_currency(date_start=str(start_prev_month), date_end=str(end_prev_month))
    print(month_to_date)