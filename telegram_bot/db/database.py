import logging
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Integer, func, BigInteger
from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, mapped_column, class_mapper
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from typing import Annotated, List, Any, Dict
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from db.config import settings

'''
    Модуль Основные настройки Базы Данных.
    
    DeclarativeBase: Основной класс для всех моделей, от которого будут наследоваться все таблицы (модели таблиц). 
    
    AsyncAttrs: Позволяет создавать асинхронные модели.
    
    create_async_engine: Функция, создающая асинхронный движок для соединения с базой данных по предоставленному URL.
    
    DATABASE_URL: Формируется с помощью метода get_db_url из файла конфигурации config.py. Содержит всю необходимую информацию для подключения к базе данных.
    
    engine: Асинхронный движок, необходимый для выполнения операций с базой данных.
    
    async_session_maker: Фабрика сессий, которая позволяет создавать сессии для взаимодействия с базой данных, 
    управлять транзакциями и выполнять запросы.
    
    Base: Абстрактный базовый класс для всех моделей, от которого будут наследоваться все таблицы. 
'''


DATABASE_URL = settings.get_db_url()

# Создаем асинхронный движок для работы с базой данных
engine = create_async_engine(url=DATABASE_URL)
# Создаем фабрику сессий для взаимодействия с базой данных
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
uniq_str_an = Annotated[str, mapped_column(unique=True)]



# Декоратор для создания сессий

def connection(method):
    async def wrapper(*args, **kwargs):
        async with async_session_maker() as session:
            try:
                return await method(*args, session=session, **kwargs)
            except Exception as e:
                await session.rollback()
                raise e
            finally:
                await session.close()  # Закрываем сессию

    return wrapper

# Базовый класс для всех моделей
class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True  # Класс абстрактный, чтобы не создавать отдельную таблицу для него

    # Автоматические поля для всех таблиц
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + 's'

    def to_dict(self) -> dict:
        """Универсальный метод для конвертации объекта SQLAlchemy в словарь"""
        # Получаем маппер для текущей модели
        columns = class_mapper(self.__class__).columns
        # Возвращаем словарь всех колонок и их значений
        return {column.key: getattr(self, column.key) for column in columns}


class BaseDAO:
    model = None  # Устанавливается в дочернем классе

    @classmethod
    async def add(cls, session: AsyncSession, **values):
        # Добавить одну запись
        new_instance = cls.model(**values)
        session.add(new_instance)
        try:
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            logging.error(e)
            raise e
        return new_instance
    @classmethod
    async def update_one_by_id(cls, session: AsyncSession, data_id: int, values: BaseModel):
        values_dict = values.model_dump(exclude_unset=True)
        try:
            record = await session.get(cls.model, data_id)
            for key, value in values_dict.items():
                setattr(record, key, value)
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            logging.error(e)
            raise e
        return record







