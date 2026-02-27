import logging
from logging.handlers import RotatingFileHandler
from typing import List

import colorlog


from db.dao import UserDAO, DirectionDAO, EnrollmentDAO, ProductDAO, StreamDAO
from db.database import connection

from datetime import date
from asyncio import run
from db.schemas import ProductPydantic, StreamPydantic, EnrollmentPydantic, UserPydantic
from utils.timezone import get_moscow_today


@connection
async def select_username_id(session):
    return await UserDAO.get_username_id(session)


@connection
async def select_all_users(session):
    return await UserDAO.get_all_users(session)


@connection
async def get_pass(session, tg_id: int):
    password_key = await UserDAO.get_password_telegramid(session=session, telegram_id=tg_id)
    return password_key


@connection
async def get_list_of_tg_ids(session, active: bool):  # TODO Check Bag
    user_ids = await UserDAO.get_users_tg_ids(session=session, active=active)
    logging.debug("get_list_of_tg_ids %s", user_ids)
    return user_ids


@connection
async def get_users_enrollments_to_ban(session, now_date: date) -> list[EnrollmentPydantic]:
    users_enrollments_to_ban = []
    enrollments_to_ban = await EnrollmentDAO.get_user_info_to_ban(session=session, now_date=now_date)
    logging.debug("get_users_enrollments_to_ban\n %s", enrollments_to_ban)
    for enrollment_info in enrollments_to_ban:
        users_enrollments_to_ban.append(EnrollmentPydantic.model_validate(enrollment_info))
    return users_enrollments_to_ban

@connection
async def get_userinfo_to_ban(session, user_ids: list) -> list[UserPydantic]:
    usersinfo_to_ban = []
    res = await UserDAO.get_user_ids_info(session=session, ids_list=user_ids)
    for user_info in res:
        usersinfo_to_ban.append(UserPydantic.model_validate(user_info))
    return usersinfo_to_ban


@connection
async def get_userinfo_by_id(session, user_id: int) -> UserPydantic | None:
    res = await UserDAO.get_user_ids_info(session=session, ids_list=[user_id])
    if not res:
        return None
    return UserPydantic.model_validate(res[0])


@connection
async def get_streaminfo_to_ban(session, stream_ids: list) -> list[StreamPydantic]:
    streaminfo_to_ban = []
    res = await StreamDAO.get_stream_ids_info(session=session, ids_list=stream_ids)
    for streaminfo in res:
        streaminfo_to_ban.append(StreamPydantic.model_validate(streaminfo))
    return streaminfo_to_ban


# @connection
# async def check_status_user_id(session, tg_user_id: int):
#     user_info = await UserDAO.get_user_info(session=session, telegram_id=tg_user_id)
#     status = user_info.active
#     logging.info("Пользователь: %s имеет статус актив: %s", tg_user_id, status)
#     return status


# @connection
# async def get_expire_date_user_id(session, tg_user_id: int):
#     user_info = await UserDAO.get_user_info(session=session, telegram_id=tg_user_id)
#     expire_date = user_info.expire_date
#     logging.debug("expire_date = %s", expire_date)
#     return expire_date


@connection
async def get_user_info_by_tg_id(session, tg_user_id: int) -> dict:
    user_info = await UserDAO.get_user_info(session=session, telegram_id=tg_user_id)
    logging.debug("get_user_info_by_tg_id %s", user_info)
    # print(user_info)
    # TODO СДЕЛАТЬ PAIDANTIC ВАЛИДАЦИЮ !!!!!
    return user_info.to_dict()


########## Directions ##########
@connection
async def get_list_directions(session) -> List:
    directions_list = []
    directions = await DirectionDAO.get_all_direction(session)
    for direction in directions:
        directions_list.append(direction.to_dict())

    logging.debug(directions_list)

    return directions_list


########## Product ##########
@connection
async def get_all_product_from_direction_id(session, group_id) -> list[ProductPydantic]:
    """Return only products that still have active streams (end_date in future or unset)."""
    today = get_moscow_today()
    products: list[ProductPydantic] = []
    raw_products = await ProductDAO.get_all_product_from_direction(session=session, direction_id=group_id)
    if not raw_products:
        return products
    for raw_product in raw_products:
        product = ProductPydantic.model_validate(raw_product)
        # active_streams = [
        #     stream
        #     for stream in (product.streams or [])
        #     if stream.end_date is None or stream.end_date >= today
        # ]
        # if not active_streams:
        #     continue
        products.append(product)
    return products


@connection
async def get_product_info(session, id_product: int) -> ProductPydantic:
    logging.debug("Запрос get_product_info")
    product_raw = await ProductDAO.get_product_from_id(session=session, id_product=id_product)
    logging.debug("Ответ на get_products получен: %s", product_raw)
    product = ProductPydantic.model_validate(product_raw)
    return product



########## Stream ##########
@connection
async def get_stream_info(session, id_stream: int) -> StreamPydantic:
    logging.debug("Запрос get_stream id = %s", id_stream)
    stream_raw = await StreamDAO.get_stream_from_id(session=session, id_stream=int(id_stream))
    logging.debug("Ответ на get_stream получен: %s", stream_raw)
    stream = StreamPydantic.model_validate(stream_raw)
    return stream


########## Enrollment ##########
@connection
async def get_enrollmets_from_user_id(session, id_user: int,
                                      today_date: date = None) -> list[EnrollmentPydantic]:
    logging.debug("Запрос get_stream id = %s", id_user)

    enrollments_raw = await EnrollmentDAO.get_enrollmets_userid(
        session=session,
        now_date=today_date,
        id_user=id_user)
    logging.debug("Ответ на get_stream получен: %s", enrollments_raw)
    enrolments_list = []
    for enrollment_raw in enrollments_raw:
        enrolments_list.append(EnrollmentPydantic.model_validate(enrollment_raw))
    return enrolments_list

@connection
async def get_enrollmet_info(session, id_enrollment: int):
    info = await EnrollmentDAO.get_enrollment(session=session, enrollment_id=id_enrollment)
    enrollment = EnrollmentPydantic.model_validate(info)
    return enrollment

@connection
async def get_enrollments_count_stream_id(session, stream_id: int) -> int:
    enrollments_count = await EnrollmentDAO.get_count_stream_enrollments(session=session,  stream_id=stream_id)
    # for enrollment in enrollments:
    #     enrollments_list.append(EnrollmentPydantic.model_validate(enrollment))
    return enrollments_count[0]





if "__main__" == __name__:

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
    # print(date.today())
    rez = run(get_enrollments_count_stream_id(stream_id=1))
    print(type(rez))
    print(rez)



    # rez = run(get_all_product_from_direction_id(group_id=1))
    # print(rez)
    # rez = run(get_stream_info(id_stream=2))
    # print(rez.title)
    # zalupa = ProductPydantic.model_validate(rez)
    # pprint(zalupa.model_dump())
    # print(zalupa)

    # print(rez.streams)
    #
    # list_zaluoa = rez.streams
    # print(list_zaluoa[0].title)
    # print(zalupa.streams[0])
    # for i in zalupa.streams:
    #     print(i.title)

# all_users = run(select_all_users())
# for i in all_users:
#     print(i.to_dict())
#
# rez = run(select_username_id())
# for i in rez:
#     print(i)

# run(get_pass(tg_id= 5866726660))

# run(get_list_of_tg_ids(active=None))
# run(check_status_user_id(tg_user_id=7079617286))
# run(get_pass(tg_id=5866726660))
# now = DT.datetime.now()
# run(get_id_to_ban(now_date=now))
# currentdate = DT.datetime.now().date()
# print(currentdate)
# run(get_users_to_ban(now_date=currentdate))
