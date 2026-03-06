from datetime import date
from enum import Enum as PyEnum
from sqlalchemy import ForeignKey, BigInteger, func, Integer, text, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.database import Base
from asyncio import run

class SubscriptionPeriod(PyEnum):
    DAY = "day"
    MONTH = "month"
    YEAR = "year"

class User(Base):  # Пользователи
    telegram_id: Mapped[int] = mapped_column(BigInteger)
    username: Mapped[str | None]
    password: Mapped[str | None]

    # Связь один-ко-многим с Payment
    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="user",
        uselist=True,
        cascade="all, delete-orphan"  # При удалении User удаляются и связанные Payment
    )
    # Связь один-ко-многим с Enrollment
    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment",
        back_populates="user",
        cascade="all, delete-orphan"  # При удалении User удаляются и связанные Enrollment
    )


class Payment(Base):  # Покупки Пользователей
    provider: Mapped[str | None]
    operation_id: Mapped[str | None]
    amount: Mapped[float]
    status: Mapped[str]

    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))  # Внешний ключ

    # Связь многие-к-одному с User
    user: Mapped["User"] = relationship(
        "User",
        back_populates="payments"
    )


class Direction(Base):  # Напраления
    title: Mapped[str | None]
    description: Mapped[str] = mapped_column(Text)

    # Связь один-ко-многим с Product
    products: Mapped[list["Product"]] = relationship(
        "Product",
        back_populates="direction",
        cascade="all, delete-orphan"
    )


class Product(Base):  # Продукты по направлениям
    title: Mapped[str | None]
    description: Mapped[str] = mapped_column(Text)
    capacity: Mapped[int | None]
    direction_id: Mapped[int] = mapped_column(ForeignKey('directions.id'))  # Внешний ключ
    base_url: Mapped[str | None]

    # Связь один-ко-многим с Stream
    streams: Mapped[list["Stream"]] = relationship(
        "Stream",
        back_populates="product",
        uselist=True,
        lazy="joined",
        cascade="all, delete-orphan"
    )
    # Связь один-ко-многим с Enrollment
    enrollments: Mapped[list["Enrollment"]] = relationship(
        "Enrollment",
        back_populates="product",
        cascade="all, delete-orphan"
    )

    # Связь многие-к-одному с Direction
    direction: Mapped["Direction"] = relationship(
        "Direction",
        back_populates="products"
    )


class Stream(Base):  # Потоки
    title: Mapped[str | None]
    price: Mapped[int | None]
    subscription_period: Mapped[SubscriptionPeriod] = mapped_column(
        SQLEnum(SubscriptionPeriod, name="subscription_period"),
        nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))  # Внешний ключ
    status: Mapped[bool | None] = mapped_column(default=True, server_default=text("'True'"))
    tg_channel_id: Mapped[int | None] = mapped_column(BigInteger)

    # Связь многие-к-одному с Product
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="streams",
        uselist=False
    )


class Enrollment(Base):  # Наборы/Покупки Пользователя
    active: Mapped[bool | None]
    title_product: Mapped[str | None]
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))  # Внешний ключ
    vless_user_name: Mapped[str | None]
    vless_link: Mapped[str] = mapped_column(Text, nullable=True)
    expire_date: Mapped[date | None]
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))  # Внешний ключ
    stream_id: Mapped[int | None]
    # Связь многие-к-одному с User
    user: Mapped["User"] = relationship(
        "User",
        back_populates="enrollments")

    # Связь многие-к-одному с Product
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="enrollments"
    )
