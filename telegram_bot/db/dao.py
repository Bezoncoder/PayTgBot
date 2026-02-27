from sqlalchemy.ext.asyncio import AsyncSession
from db.database import BaseDAO
from db.models import User, Enrollment, Direction, Product, Stream, Payment
from sqlalchemy import select, update, func
from datetime import date
import asyncio
import logging


class UserDAO(BaseDAO):
    model = User

    @classmethod
    async def get_all_users(cls, session: AsyncSession):
        # Создаем запрос для выборки всех пользователей
        query = select(cls.model)
        logging.debug("get_all_users %s", query)
        # Выполняем запрос и получаем результат
        result = await session.execute(query)

        # Извлекаем записи как объекты модели
        records = result.scalars().all()

        # Возвращаем список всех пользователей
        return records

    @classmethod
    async def get_username_id(cls, session: AsyncSession):
        # Создаем запрос для выборки id и username всех пользователей
        query = select(cls.model.id, cls.model.full_name)  # Указываем конкретные колонки
        logging.debug("get_username_id %s", query)
        result = await session.execute(query)  # Выполняем асинхронный запрос
        records = result.all()  # Получаем все результаты
        return records  # Возвращаем список записей

    @classmethod
    async def get_user_info(cls, session: AsyncSession, telegram_id: int):
        # query = select(cls.model).filter_by(telegram_id=user_id)
        query = select(cls.model).filter(cls.model.telegram_id == telegram_id)
        logging.info("Делаем запрос данных пользователя в БД")
        result = await session.execute(query)
        logging.info("Получен Ответ из БД")
        user_info = result.scalar_one_or_none()
        logging.debug("user_info %s", user_info)
        return user_info

    @classmethod
    async def get_user_ids_info(cls, session: AsyncSession, ids_list: list[int]):
        query = select(cls.model).filter(cls.model.id.in_(ids_list))
        logging.info(f"Делаем запрос данных пользователей в БД для {len(ids_list)} id")
        result = await session.execute(query)
        logging.info("Получен ответ из БД")
        user_info_list = result.scalars().all()
        logging.debug("user_info_list: %s", user_info_list)
        return user_info_list

    @classmethod
    async def get_password_telegramid(cls, session: AsyncSession, telegram_id):
        query = select(cls.model.password).filter(cls.model.telegram_id == telegram_id)
        logging.debug("get_password_telegramid %s", query)
        result = await session.execute(query)
        password = result.scalar_one_or_none()
        return password


class EnrollmentDAO(BaseDAO):
    model = Enrollment

    @classmethod
    async def get_user_info_to_ban(cls, session: AsyncSession, now_date: date):
        query = select(cls.model).where(
            cls.model.active.is_(True),
            cls.model.expire_date < now_date,
        )
        logging.debug("get_user_info_to_ban %s", query)
        result = await session.execute(query)
        users_enrollments_expired = result.scalars().all()
        return users_enrollments_expired

    @classmethod
    async def get_users_tg_ids(cls, session: AsyncSession, active: bool):
        query = select(cls.model.user_id).filter(cls.model.active == active)
        logging.debug("get_users_tg_ids %s", query)
        result = await session.execute(query)
        users_ids = result.scalars().all()
        return

    @classmethod
    async def get_enrollment(cls, session: AsyncSession, enrollment_id: int):
        # query = select(cls.model).filter_by(telegram_id=user_id)
        query = select(cls.model).filter(cls.model.id == enrollment_id)
        logging.info("Делаем запрос данных пользователя в БД")
        result = await session.execute(query)
        logging.info("Получен Ответ из БД")
        enrollment_info = result.scalar_one_or_none()
        logging.debug("enrollment_info %s", enrollment_info)
        return enrollment_info

    @classmethod
    async def get_enrollmets_userid(
        cls,
        session: AsyncSession,
        now_date: date | None,
        id_user: int,
    ):
        query = select(cls.model).where(cls.model.user_id == int(id_user)).where(cls.model.expire_date>now_date)

        logging.debug("get_enrolmets_userid %s", query)
        result = await session.execute(query)
        enrolments = result.scalars().all()
        return enrolments

    @classmethod
    async def get_count_stream_enrollments(cls, session: AsyncSession, stream_id: int):
        query = select(func.count(cls.model.id)).filter(cls.model.stream_id == int(stream_id))
        result = await session.execute(query)
        count = result.scalars().all()
        logging.debug("get_count_stream_enrollments %s", count)
        return count

    @classmethod
    async def deactivate_user_stream(cls, session: AsyncSession, user_id: int, stream_id: int):
        query = (
            update(cls.model)
            .where(
                cls.model.user_id == int(user_id),
                cls.model.stream_id == int(stream_id),
                cls.model.active.is_(True),
            )
            .values(active=False)
        )
        await session.execute(query)
        await session.commit()

    @classmethod
    async def deactivate_user_product(cls, session: AsyncSession, user_id: int, product_id: int):
        query = (
            update(cls.model)
            .where(
                cls.model.user_id == int(user_id),
                cls.model.product_id == int(product_id),
                cls.model.active.is_(True),
            )
            .values(active=False)
        )
        await session.execute(query)
        await session.commit()






class DirectionDAO(BaseDAO):
    model = Direction

    @classmethod
    async def get_all_direction(cls, session: AsyncSession):
        # Создаем запрос для выборки всех пользователей
        query = select(cls.model)
        logging.debug("get_all_direction %s", query)
        # Выполняем запрос и получаем результат
        result = await session.execute(query)

        # Извлекаем записи как объекты модели
        records = result.scalars().all()

        # Возвращаем список всех пользователей
        return records



class ProductDAO(BaseDAO):
    model = Product

    @classmethod
    async def get_all_product_from_direction(cls, session: AsyncSession, direction_id: int):
        # Создаем запрос для выборки всех пользователей
        query = select(cls.model).filter(cls.model.direction_id == direction_id)
        logging.debug("get_all_product_from_id_direction %s", query)
        # Выполняем запрос и получаем результат
        result = await session.execute(query)
        unique_result = result.unique()
        records = unique_result.scalars().all()
        # Извлекаем записи как объекты модели
        # records = result.scalars().all()

        # Возвращаем список всех пользователей
        return records

    @classmethod
    async def get_product_from_id(cls, session: AsyncSession, id_product: int):
        # Создаем запрос для выборки всех пользователей
        logging.debug("Запрос в БД ProductDAO")
        query = select(cls.model).filter(cls.model.id == id_product)
        logging.debug("get_product_from_id\n %s", query)
        # Выполняем запрос и получаем результат
        result = await session.execute(query)
        result = result.unique()
        # Извлекаем записи как объекты модели
        records = result.scalar_one_or_none()

        # Возвращаем список всех пользователей
        return records


class StreamDAO(BaseDAO):
    model = Stream

    @classmethod
    async def get_stream_from_id(cls, session: AsyncSession, id_stream: int):
        # Создаем запрос для выборки всех пользователей
        logging.debug("Запрос в БД StreamDAO")
        query = select(cls.model).filter(cls.model.id == id_stream)
        logging.debug("get_stream_from_id\n %s", query)
        # Выполняем запрос и получаем результат
        result = await session.execute(query)
        # result = result.unique()
        # Извлекаем записи как объекты модели
        records = result.scalar_one_or_none()

        # Возвращаем список всех пользователей
        return records

    @classmethod
    async def get_stream_ids_info(cls, session: AsyncSession, ids_list: list[int]):
        query = select(cls.model).filter(cls.model.id.in_(ids_list))
        logging.info(f"Делаем запрос данных потоеов в БД для {len(ids_list)} id")
        result = await session.execute(query)
        logging.info("Получен ответ из БД")
        stream_info_list = result.scalars().all()
        logging.debug("stream_info_list: %s", stream_info_list)
        return stream_info_list


class PaymentDAO(BaseDAO):
    model = Payment

    #     payments_data_dict = {"provider": "Tochka_Bank",
    #                           "amount": price,
    #                           "operation_id": "",
    #                           "status": "CREATE",
    #                           "user_id": user_info_dict["id"]}

    @classmethod
    async def update_pay_from_id(cls, session: AsyncSession, pay_data: dict):
        logging.info("Обновляем оплату для")
        query = (update(cls.model).filter(cls.model.id == int(pay_data.get("id_pay"))).
                 values(operation_id=pay_data["operation_id"]))
