from datetime import date
from typing import List
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Mapped

from db.models import SubscriptionPeriod


class StreamPydantic(BaseModel):
    id: int
    title: str | None
    price: int | None
    product_id: int | None
    status: bool | None
    subscription_period: SubscriptionPeriod
    tg_channel_id: int | None
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class ProductPydantic(BaseModel):  # Продукты по направлениям
    id: int
    title: str | None
    description: str
    capacity: int | None
    direction_id: int
    base_url: str | None
    total_gb: int | None
    inbound_id: int | None
    api_vless_token: str | None
    public_key: str | None
    short_id: str | None
    streams: list[StreamPydantic] | None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class PaymentPydantic(BaseModel):  # Оплата

    id: int
    provider: str | None
    operation_id: str | None
    amount: int
    status: str
    stream_id: int | None
    user_id: int  # Внешний ключ

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class EnrollmentPydantic(BaseModel):  # Наборы/Покупки Пользователя
    id: int
    active: bool | None
    user_id: int | None  # Внешний ключ
    expire_date: date | None
    title_product: str | None
    vless_user_name: str | None
    vless_link: str | None
    product_id: int | None  # Внешний ключ
    stream_id: int | None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class UserPydantic(BaseModel):
    id: int
    telegram_id: int | str | None
    username: str | None
    password: str | None
    reward_type: str | None  # (percent, vpn_month)
    enrollments: list[EnrollmentPydantic] = []
    # referred_by_user_id: int | None
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class ReferralRewardsPydantic(BaseModel):
    id: int
    user_id: int | None
    referred_user_id: int | None
    payment_id: int | None
    reward_type: str | None # (percent, vpn_month)
    reward_value: str | None # (20% или 1 month)
    active_status: bool | None # (pending, available, paid, cancelled)
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)



class UsernameIdPydantic(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


if __name__ == "__main__":
    print()
    # user = UserPydantic.from_orm()

    # all_users = run(select_all_users())
    # for i in all_users:
    #     user_pydantic = UserPydantic.from_orm(i)
    #     print(user_pydantic)

    # rez = run(select_username_id())
    # for i in rez:
    #     rez = UsernameIdPydantic.from_orm(i)
    #     print(rez.dict())
