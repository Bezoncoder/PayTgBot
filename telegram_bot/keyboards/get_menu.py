import logging
from typing import List

from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import datetime as DT

from db.schemas import ProductPydantic, StreamPydantic, EnrollmentPydantic
from db.select_methods import get_list_directions, get_enrollments_count_stream_id, get_product_info
from utils.plategaio import PaymentMethod


# from utils.jira_functional.jira_functions import ensure_user, JIRA_BASE
# from settings.config import START_DATE


async def get_start_menu(list_for_menu, one_user_info: dict) -> InlineKeyboardMarkup:
    buttons = list_for_menu

    builder = InlineKeyboardBuilder()
    for button in buttons:
        if button['title'] != "VPN":
            continue
        call_data = f"set_group:{button['id']}"  # Передаем выбранную Группу/Направление
        builder.button(text=f"🌐 {button['title']} Меню", callback_data=call_data)
        logging.debug(call_data)

    builder.button(text="📦 Мои покупки", callback_data=f"get_my_subscribe:{one_user_info['id']}")
    builder.button(text="👩‍💻 Тех поддержка", url="https://t.me/QuantumTurboVPN")
    # builder.button(text="👩‍💻 Тех поддержка", url="https://t.me/user_post")
    if one_user_info['telegram_id'] == "5866726660" or one_user_info['telegram_id'] == 5866726660:
        builder.button(text="GET ID MESSAGE", callback_data="edit_adt_posts")

    builder.button(text="🎁 Получить VPN бесплатно", callback_data=f"get_referral_link:{one_user_info['id']}")
    builder.adjust(1)

    return builder.as_markup(resize_keyboard=True)


async def get_products_menu(
        list_of_products: list[ProductPydantic],
) -> InlineKeyboardMarkup:
    buttons = list_of_products
    logging.debug("get_products_menu")
    builder = InlineKeyboardBuilder()
    for button in buttons:
        call_data = f"set_product:{button.id}"
        builder.button(text=f"{button.title}", callback_data=call_data)
        logging.debug(call_data)
    builder.button(text="Назад", callback_data="set: start")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


async def get_stream_products_menu(enrollments_count: int, price_menu: str, product_capacity: int,
                                   streams_list: list[StreamPydantic] | None, directions_id: int = 1) -> InlineKeyboardMarkup:
    logging.debug("get_stream_products_menu")
    builder = InlineKeyboardBuilder()

    if len(streams_list) > 1:
        for stream in streams_list:
            # enrollments_count = await get_enrollments_count_stream_id(stream_id=stream.id)
            # TODO !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            ########################### PRODUCT CAPACITY ############################
            if product_capacity > enrollments_count:
                call_data = f"set_stream:{stream.id}:{stream.price}:{stream.product_id}"
                builder.button(text=f"{stream.title} {stream.price} ₽", callback_data=call_data)
            else:
                continue
    else:
        pass
    ############################ ПЕРЕХОД К ФОРМИРОВАНИЮ ОПЛАТЫ #########################
        # call_data = f"get_pay:{streams_list[0].id}:{price_menu}:{directions_id}"
        # builder.button(text="Перейти к оплате", callback_data=call_data)
        # logging.debug(call_data)
    builder.button(text="Назад", callback_data=f"set_group:{directions_id}")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


############################# get_pay_buttons ##############################################################
def get_pay_buttons(
        text: str, price_menu: str = "", product_id: int = 1, direction_id: int = 1
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # callback_data=f"set: 2"
    callback_menu = "get_pay:" + f"{product_id}:" + f"{price_menu}"
    builder.button(text=f"{text}", callback_data=callback_menu)
    builder.button(text="Назад", callback_data=f"set_product:{product_id}")
    builder.adjust(1)

    return builder.as_markup(resize_keyboard=True)


def get_payment_notification_button(
        price: str, stream_id: int, directions_id: int = None
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # set_stream:stream_id:price
    builder.button(
        text=f"Я оплатил",
        callback_data=f"check_pay:{stream_id}:{price}:{directions_id}",
    )

    # back_callback_menu = f"get_choosing_method:{stream_id}:{price_menu}:{product_id}"

    if directions_id is None:
        builder.button(text="Назад", callback_data=f"set_stream:{stream_id}:{price}")
    else:
        builder.button(text="Назад", callback_data=f"set_group:{directions_id}")
    builder.adjust(1)

    return builder.as_markup(resize_keyboard=True)

def get_choosing_pay_method_buttons(price: str, stream_id_int: int, product_id: int = None, directions_id: int = None,
                                    pay_method: PaymentMethod = None) -> InlineKeyboardMarkup:

    #     0       1           2             3               4              5
    # get_pay:{stream_id}:{price}:{product_id}:{directions_id}:{method_value} NEW

    builder = InlineKeyboardBuilder()
    for method in PaymentMethod:

        if method == PaymentMethod.SBP_QR:
            text_button = "🏦 СБП"
        # elif method == PaymentMethod.CARD_ACQUIRING:
        #     text_button = "💳 Оплата картой"
        else:
            text_button = "💰 Криптовалюта"

        builder.button(text=f"{text_button}",
                       callback_data=f"get_pay:{stream_id_int}:{price}:{product_id}:{directions_id}:{method.value}")

    # get_free_month:{stream_id}:{price}:{directions_id}

    builder.button(text="🎁 Бесплатно", callback_data=f"get_free_month:{stream_id_int}:{price}:{directions_id}")

    if directions_id is None:
        builder.button(text="Назад", callback_data=f"set_stream:{stream_id_int}:{price}")
    else:
        builder.button(text="Назад", callback_data=f"set_group:{directions_id}")

    builder.adjust(1)
    builder.button(text="Главное меню", callback_data=f"set: start")

    return builder.as_markup(resize_keyboard=True)


def get_payment_verification_button() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="ДА", callback_data="approve_check")
    builder.button(text="НЕТ", callback_data="skip_check")
    builder.adjust(1)

    return builder.as_markup(resize_keyboard=True)


def get_change_user_data_dialog_button(callback_data_list: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="Назад", callback_data=callback_data_list[0])
    builder.button(text="Далее", callback_data=callback_data_list[1])
    builder.adjust(1)

    return builder.as_markup(resize_keyboard=True)


def get_stream_payment_buttons(price_menu: str = None,
                               stream_id: int = None,
                               product_id: int = None) -> InlineKeyboardMarkup:

    builder = InlineKeyboardBuilder()

    ######################### ПЕРЕХОД К ФОРМИРОВАНИЮ ОПЛАТЫ ######################
    callback_menu = f"get_choosing_method:{stream_id}:{price_menu}:{product_id}"
    builder.button(text=f"Продолжить и принять условия оферты", callback_data=callback_menu)
    builder.button(text="Назад", callback_data=f"set_product:{product_id}")
    builder.adjust(1)

    return builder.as_markup(resize_keyboard=True)


def get_back_button(stream_id: int=None, price: int=None, product_id: int=None,
                    directions_id: str=None, method_value: str = None) -> InlineKeyboardMarkup:

    builder = InlineKeyboardBuilder()

    # get_pay:{stream_id}:{price}:{product_id}:{directions_id}:{method_value} -> get_payment

    builder.button(
        text="Назад", callback_data=f"get_pay:{stream_id}:{price}:{product_id}:{directions_id}:{method_value}"
    )
    builder.button(
        text="Главное меню", callback_data=f"set: start"
    )

    builder.adjust(1)

    return builder.as_markup(resize_keyboard=True)



def get_start_button() -> InlineKeyboardMarkup:

    builder = InlineKeyboardBuilder()

    builder.button(
        text="Главное меню", callback_data=f"set: start"
    )

    builder.adjust(1)

    return builder.as_markup(resize_keyboard=True)



def get_subscribe_menu(enrolments: list[EnrollmentPydantic] = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if enrolments:
        for enrolment in enrolments:
            button_text= f"{enrolment.title_product} до {enrolment.expire_date.strftime("%d.%m.%Y")}"
            builder.button(
                text=f"{button_text}", callback_data=f"get_creds:{enrolment.id}"
            )
    builder.button(text="Главное меню", callback_data="set: start")
    builder.adjust(1)

    return builder.as_markup(resize_keyboard=True)


def get_main_menu_button(user_bd_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="Назад",
                   callback_data=f"get_my_subscribe:{user_bd_id}")
    builder.button(text="Главное меню",
                   callback_data=f"set: start")

    builder.adjust(1)

    return builder.as_markup(resize_keyboard=True)

def get_fake_menu_button() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="Назад",
                   callback_data=" ")

    builder.adjust(1)

    return builder.as_markup(resize_keyboard=True)

def get_errors_button() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="👩‍💻 Тех поддержка",
                   url="https://t.me/QuantumTurboVPN")

    builder.button(text="Главное меню",
                   callback_data=f"set: start")

    builder.adjust(1)

    return builder.as_markup(resize_keyboard=True)

def get_del_button() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="Удалить сообщение",
                   callback_data=f"del_info_message")

    builder.adjust(1)

    return builder.as_markup(resize_keyboard=True)


def get_choice_refer_button(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="Месяц бесплатно", callback_data="refer:month")
    builder.button(text="Получать 20%", callback_data="refer:percent")
    builder.button(text="🧾 Ваш отчет", callback_data=f"get_referral_program:{user_id}")
    builder.button(text="Назад", callback_data=f"set: start")
    builder.adjust(1)

    return builder.as_markup(resize_keyboard=True)


def get_refer_back_button() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="Назад", callback_data=f"get_referral_link:")
    builder.button(
        text="Главное меню", callback_data=f"set: start"
    )

    builder.adjust(1)

    return builder.as_markup(resize_keyboard=True)


if __name__ == "__main__":
    date_string = "2025-07-10"
# format_string = "%Y-%m-%d"
# datetime_object = DT.datetime.strptime(date_string, format_string)
# expire_data = datetime_object.date()
#
# check_pay = expire_data - DT.timedelta(days=3)
# print(check_pay)
# list1=[]
# list1.append(1)
# print(list1[0])
