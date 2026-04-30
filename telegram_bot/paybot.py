import asyncio
import random

from aiogram.types import FSInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from db.update_methods_dao import update_enrollment_data
from handlers import (greetings, get_subscribe, check_payment_auto, check_payment_manual,
                      get_creds, github_check_subscribe,
                      choosing_direction, choosing_product,
                      get_payment, choosing_stream, check_fio, how_to_pay, check_email,
                      choosing_payment_method, edit_adt_posts, get_referral_link, get_referal_program)
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
import logging
import colorlog

from keyboards.get_menu import get_start_button, get_del_button
from settings.config import BOT_TOKEN, TECH_CHANNEL, USER, PASSWORD
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from db.select_methods import (get_userinfo_to_ban,
                               get_users_enrollments_to_ban,
                               get_streaminfo_to_ban, select_all_users,
                               get_product_info)
from utils.vlessuiapi import XUIClient

bot = Bot(token=BOT_TOKEN)

ADT_MESSAGE_LIST=[3,5,6,7,8,10,11,12]

# user subscription control @getidsbot - Бот, который выдает ID чата
#  -1002917599861 Bootcamp Supergroup_ID
# await bot.ban_chat_member(chat_id, user_id)
# await bot.unban_chat_member(chat_id, user_id)

async def check_and_ban():
    logging.info("Запуск Проверки Подписок")

    list_id_user = []
    list_id_stream = []
    vless_info = {}

    date_to_check_subscribe = datetime.now() - timedelta(days=1)

    users_enrollments_to_ban = await get_users_enrollments_to_ban(now_date=date_to_check_subscribe.date())

    for enrollment in users_enrollments_to_ban:
        list_id_user.append(enrollment.user_id)
        list_id_stream.append(enrollment.stream_id)

        try:
            new_enrollment = await update_enrollment_data(enrollment_id=enrollment.id, new_active_status=False)
            logging.info(f"Пользователю {new_enrollment.user_id} изменен статус подписки на False")
            logging.info(f"expire_date = {new_enrollment.expire_date}")
        except Exception as e:
            logging.error(e)
            new_enrollment = None

        if  new_enrollment is not None:

            product_info = await get_product_info(id_product=enrollment.product_id)

            vless_client = XUIClient(base_url_from_panel=product_info.base_url,
                                     username=USER,
                                     password=PASSWORD,
                                     verify_ssl=True,
                                     public_inbound_key=product_info.public_key,
                                     sid=product_info.short_id)

            status = vless_client.remove_client(client_id=new_enrollment.vless_user_name)
            vless_info.setdefault(enrollment.user_id, []).append(status)


    info_banned_users = dict(list_id_users=list_id_user,
                          vless_info=vless_info
                          )

    return info_banned_users



async def check_and_posting():

    logging.info("Запуск Запланированной Задачи")

    users_to_posting_rek = await select_all_users()

    loging_info = await check_and_ban()

    logging.info(f"Подписки Vless удалены:\n{loging_info}")

    count_success_send = 0
    count_fail_send = 0

    message_to_post_id = random.choice(ADT_MESSAGE_LIST)
    for user_info in users_to_posting_rek:

        if not user_info.enrollments:
            try:
                await bot.copy_message(
                    chat_id=user_info.telegram_id,
                    from_chat_id=-1003976745616,
                    message_id=message_to_post_id,
                    reply_markup=get_start_button()
                )
                logging.info(f"✅ Отправлено рекламное сообщение пользователю user_name = {user_info.username}")
                count_success_send+=1

            except Exception as e:
                logging.debug(f"⚠️ Ошибка при отпрвке сообщения:\n{e}")
                count_fail_send+=1

            await asyncio.sleep(3)

    count_reminder = 0

    photo = FSInputFile('source/pictures/vpn_main_menu.jpg')
    for i in range(3, 0, -1):
        user_ids = []
        date_to_check = datetime.now() + timedelta(days=i)
        logging.info(f"Начинаем рассылку о продлении ключа VPN.")
        logging.info(f"date_to_check = {date_to_check.date()}")

        if i>1:
            days_str = f"{i} дня"
        else:
            days_str = f"{i} день"

        notification = (
            f"🚨 **Внимание!** Подписка на VPN заканчивается через {days_str}! ⏰\n\n"
            f"🌍🔒 Не теряй доступ к нашему надежному VPN по всему миру.\n\n"
            f"️✨ Продли сейчас и продолжай серфить безопасно!\n\n"
            f"🔗 Открой Главное меню.\n\n"
        )

        try:
            users_enrollments_to_posting = await get_users_enrollments_to_ban(now_date=date_to_check.date())
        except Exception as e:
            logging.error(f"⚠️  Ошибка при get_users_enrollments_to_ban\n{e}")
            users_enrollments_to_posting = []

        for enrollment_paydantic in users_enrollments_to_posting:
            user_ids.append(enrollment_paydantic.user_id)

        try:
            users_to_post_paydantic = await get_userinfo_to_ban(user_ids=user_ids)
        except Exception as e:
            logging.error(f"⚠️  Ошибка при get_userinfo_to_ban\n{e}")
            users_to_post_paydantic = []

        for user_info in users_to_post_paydantic:
            try:
                await bot.send_photo(chat_id=user_info.telegram_id,
                                     photo=photo,
                                     caption=notification,
                                     reply_markup=get_start_button(),
                                     parse_mode="HTML",)
                logging.info(f"✅ Отправлено сообщение о продлении подписки пользователю user_name = {user_info.username}")
                count_reminder+=1

            except Exception as e:
                logging.debug(f"⚠️ Ошибка при отпрвке сообщения:\n{e}")

    text = (
        f"🚀 <b>Рассылка выполнена</b>\n\n"
        f"⏰ Отправлено напоминаний о продлении: {count_reminder}\n\n"
        f"Реклама:\n"
        f"✅ Доставлено: <b>{count_success_send}</b>\n"
        f"⚠️ Не отправилось: <b>{count_fail_send}</b>"
    )

    await bot.send_message(chat_id=TECH_CHANNEL,
                           text=text,
                           parse_mode="HTML",
                           reply_markup=get_del_button())






async def main():
    logging.info("Старт Bot Loging")

    # Настройка Шедулера
    logging.info("Настройка Шедулера...")
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    # Запуск кода в определенные часы:

    scheduler.add_job(func=check_and_posting, trigger="cron", hour=16, minute=10)

    # Запуск кода через определенный интервал
    # now_time = DT.datetime.now() + DT.timedelta(seconds=15)
    # scheduler.add_job(func=unban_user,
    #                   trigger='interval',
    #                   minutes=1,
    #                   next_run_time=DT.datetime.now() + DT.timedelta(seconds=15)
    #                   )

    scheduler.start()
    logging.info("Настройка Шедулера завершена.")

    dp = Dispatcher(storage=MemoryStorage())

    # dp.message.middleware(UserInternalIdMiddleware())
    # dp.callback_query.middleware(how_to_pay.HowToPayCleanupMiddleware())

    # Подключаем маршруты
    dp.include_routers(greetings.router,
                       get_subscribe.router,
                       check_payment_auto.router,
                       check_payment_manual.router,
                       check_fio.router,
                       github_check_subscribe.router,
                       get_creds.router,
                       choosing_direction.router,
                       choosing_product.router,
                       get_payment.router,
                       choosing_stream.router,
                       how_to_pay.router,
                       check_email.router,
                       choosing_payment_method.router,
                       edit_adt_posts.router,
                       get_referral_link.router,
                       get_referal_program.router)

    # Запускаем бота и пропускаем все накопленные входящие
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот Запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    # Настройка логирования
    # pip install colorlog
    # pip install loging
    formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)s:%(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        filename=f'InfraSharing_Bot_Logs.log',
        maxBytes=2000000,
        backupCount=1,
        encoding="UTF-8"
    )

    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[file_handler, handler],
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    # Запуск бота
    asyncio.run(main())
