import datetime
import logging
import random

from db.dao import UserDAO, EnrollmentDAO, PaymentDAO
from db.database import connection
from asyncio import run

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User
from sqlalchemy import select
import datetime as dt

from db.schemas import PaymentPydantic, EnrollmentPydantic
from utils.passgen import get_password


@connection
async def add_payments_operation(payments_data: dict, session: AsyncSession):
    new_payment = await PaymentDAO.add(session=session, **payments_data)
    logging.info("Добавлена оплата с ID: %s", new_payment.id)
    payment = PaymentPydantic.model_validate(new_payment)
    return payment


@connection
async def check_user_and_add(user_data: dict, session: AsyncSession):
    telegram_id = int(user_data["telegram_id"])
    logging.debug("Проверяем user_data, где telegram_id = %s", telegram_id)
    rez = await UserDAO.get_user_info(session=session, telegram_id=telegram_id)

    if rez:
        logging.info("Пользователь TG_ID = %s уже существует с ID: %s ", telegram_id, rez.id)
        return rez.to_dict()
    else:
        password = get_password(8)
        user_data["password"] = password
        logging.debug("Создан новый пользователь user_data: %s ", user_data)
        new_user = await UserDAO.add(session=session, **user_data)
        logging.info("Добавлен новый пользователь с ID: %s ", new_user.id)
        return new_user.to_dict()


@connection
async def set_pay(pay_data: dict, session: AsyncSession):
    logging.debug("set_pay pay_data['telegram_id'] == %s", pay_data['telegram_id'])

    new_pay = await EnrollmentDAO.add(session=session, **pay_data)
    logging.info("Принята оплата: %s ", new_pay.to_dict())
    return new_pay.to_dict()
    # rez = await UserDAO.get_user_info(session=session, telegram_id=int(user_data['telegram_id']))
    # if rez:
    #     logging.debug("Уже существует пользователь с ID: %s ", rez.id)
    #     user = await session.get(User, rez.id)
    #     user.active = True
    #     user.password = user_data["password"]
    #     user.expire_date = user_data["expire_date"]
    #     await session.commit()
    #     return user
    # else:
    #     new_user = await UserDAO.add(session=session, **user_data)
    #     print(f"Добавлен новый пользователь с ID: {new_user.id}")
    #     return new_user.id


@connection
async def set_git_link(telegram_id, git_link, session: AsyncSession):
    logging.debug("set_pay user_data['telegram_id'] == %s", telegram_id)
    rez = await UserDAO.get_user_info(session=session, telegram_id=int(telegram_id))
    if rez:
        logging.debug("Добавляем ссылку на GIT пользователю c ID: %s ", rez.id)
        user = await session.get(User, rez.id)
        user.git_link = git_link
        await session.commit()
        return user


@connection
async def set_full_name(telegram_id: int, full_name: str, session: AsyncSession):
    logging.debug("set_full_name user_data['telegram_id'] == %s", telegram_id)
    rez = await UserDAO.get_user_info(session=session, telegram_id=int(telegram_id))
    if rez:
        user = await session.get(User, rez.id)
        user.full_name = full_name
        await session.commit()
        return user

@connection
async def add_new_enrollments(enrollment_data: dict, session: AsyncSession):
    user_id = enrollment_data.get("user_id")
    stream_id = enrollment_data.get("stream_id")
    product_id = enrollment_data.get("product_id")
    if user_id is not None and stream_id is not None:
        await EnrollmentDAO.deactivate_user_stream(
            session=session,
            user_id=user_id,
            stream_id=stream_id,
        )
    elif user_id is not None and product_id is not None:
        await EnrollmentDAO.deactivate_user_product(
            session=session,
            user_id=user_id,
            product_id=product_id,
        )
    new_enrollment = await EnrollmentDAO.add(session=session, **enrollment_data)
    logging.info("Добавлен enrollment с ID: %s", new_enrollment.id)
    enrollment = EnrollmentPydantic.model_validate(new_enrollment)
    return enrollment

if __name__ == "__main__":
    one_user = {"telegram_id": '222277777',
                "username": "oliver_jackson",
                "password": "jackson123"}

    payments_data_dict = {"provider": "Tochka_Bank",
                          "amount": 21,
                          "operation_id": "test",
                          "status": "STATUS",
                          "user_id": 3}
    # test_payment = run(add_payments_operation(payments_data=payments_data_dict))
    # print(test_payment)
    # print(test_payment.id)
    # # run(add_one(user_data=one_user))

    date_string = "2026-09-09"

    # Преобразуем строку в объект datetime
    datetime_object = datetime.datetime.strptime(date_string, "%Y-%m-%d")

    # Если нужен только объект даты (без времени), используем .date()
    date_object = datetime_object.date()
    enrollment_data = {
                      "active": True,
                      "user_id": 1,
                      "expire_date": date_object,
                      "title_product": "Bootcamp",
                      "product_id": 3}

    test_enrollment = run(add_new_enrollments(enrollment_data=enrollment_data))
    print(test_enrollment)
