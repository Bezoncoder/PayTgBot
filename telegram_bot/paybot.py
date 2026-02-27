import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from handlers import (greetings, get_subscribe, check_payment_auto, check_payment_manual,
                      get_creds, github_check_subscribe,
                      choosing_direction, choosing_product,
                      get_payment, choosing_stream, check_fio, how_to_pay, check_email)
# from middleware.UserInternalIdMiddleware import UserInternalIdMiddleware
import datetime as dt

from logging.handlers import RotatingFileHandler
import logging
import colorlog

from settings.config import BOT_TOKEN
from utils.github_api import GitHubRepoManager, parse_repo_url
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from db.select_methods import (
    get_userinfo_to_ban,
    get_users_enrollments_to_ban,
    get_streaminfo_to_ban,
    get_product_info,
)

bot = Bot(token=BOT_TOKEN)


# user subscription control @getidsbot - Бот, который выдает ID чата
#  -1002917599861 Bootcamp Supergroup_ID
# await bot.ban_chat_member(chat_id, user_id)
# await bot.unban_chat_member(chat_id, user_id)

async def check_and_ban():
    logging.debug("Запуск Запланированной Задачи")
    list_id_user = []
    list_id_stream = []
    now = dt.datetime.now()


    users_enrollments_to_ban = await get_users_enrollments_to_ban(now_date=now)
    # TODO сделать нормальное отключение подписки.
    for enrollment in users_enrollments_to_ban:
        list_id_user.append(enrollment.user_id)
        list_id_stream.append(enrollment.stream_id)

    users_to_ban = await get_userinfo_to_ban(user_ids=list_id_user)
    stream_list_to_ban = await get_streaminfo_to_ban(stream_ids=list_id_stream)

    count_user = len(users_to_ban)

    logging.info("У %s пользователей закончилась подписка:\n%s", count_user, users_to_ban)




async def main():
    logging.info("Старт Bot Loging")

    # Настройка Шедулера
    logging.info("Настройка Шедулера...")
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    # Запуск кода в определенные часы:

    scheduler.add_job(func=check_and_ban, trigger="cron", hour=0, minute=10)

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
                       check_email.router)

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
