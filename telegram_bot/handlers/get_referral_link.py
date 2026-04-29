import logging
from pprint import pprint

from aiogram import Router, F
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import Message, InputMediaPhoto
from aiogram.utils.deep_linking import create_start_link

from keyboards.get_menu import get_start_menu, get_stream_products_menu, get_choice_refer_button, get_start_button, \
    get_refer_back_button
from aiogram.types import FSInputFile

from db.select_methods import get_list_directions, get_product_info, get_user_info_by_tg_id, get_enrollmets_from_user_id
from db.add_methods_dao import check_user_and_add, add_new_referral_rewards

from aiogram.fsm.context import FSMContext

from aiogram.types import CallbackQuery

# from settings.config import START_DATE
# from settings.config import START_DATE
from utils.get_links import get_subscribe_link
from utils.states import OrderPay
from utils.timezone import get_moscow_today

router = Router()


# def get_main_window_menu():

@router.callback_query(F.data.startswith("get_referral_link:"))
async def get_referral_link(callback: CallbackQuery, state: FSMContext):

    # get_referral_link:{one_user_info['id']}

    await callback.answer(text=f"Реферальная программа")

    user_info = await get_user_info_by_tg_id(tg_user_id=int(callback.from_user.id))

    #####################################################################################################

    # Вариант с изменением сообщения без удаления.

    referral_caption = ("QuantumTurbo VPN — технология будущего! 🚀\n\n"
                        "Это не просто VPN, а твоя возможность получить максимум пользы уже сегодня.\n\n"
                        "Выбирай один из двух путей:\n"
                        "• Забрать любой VPN бесплатно на 1 месяц.\n"
                        "• Подключиться к реферальной программе и получать 20% с каждой покупки по своей ссылке.\n\n"
                        "Пользуйся сам, делись с друзьями и зарабатывай вместе с QuantumTurbo VPN.\n\n"
                        "Выбирай свой вариант 👇")


    photo = FSInputFile('source/pictures/referral_rewards.jpg')

    media = InputMediaPhoto(
        media=photo,
        caption=referral_caption,
        parse_mode="HTML")

    await callback.bot.edit_message_media(media=media,
                                          chat_id=callback.from_user.id,
                                          message_id=callback.message.message_id,
                                          reply_markup=get_choice_refer_button(user_id=user_info.id))

@router.callback_query(F.data.startswith("refer:"))
async def get_refer_program(callback: CallbackQuery, state: FSMContext):

    # refer_month refer_percent

    # from aiogram.utils.deep_linking import create_start_link
    # link = await create_start_link(bot, "percent_123456789", encode=True)

    await callback.answer(text=f"Реферальная программа")

    list_data_buttons = callback.data.split(":")
    reward_type = list_data_buttons[1]

    user_info = await get_user_info_by_tg_id(tg_user_id=int(callback.from_user.id))

    link = await create_start_link(bot=callback.bot,
                                   payload=f"{reward_type}_{user_info.id}",
                                   encode=True)
    if reward_type == "percent":
        caption = (
                   f"🚀 Ваша реферальная ссылка уже готова!\n\n"
                   f"✨ Делитесь ею с друзьями и зарабатывайте вместе с QuantumTurbo VPN.\n\n"
                   f"Каждая покупка по вашей ссылке приносит вам 20% прибыли — просто, удобно и выгодно.\n\n"
                   f"🔥 Чем больше вы делитесь, тем больше ваш доход.\n\n"
                   f"🔗 Ваша ссылка (нажми, чтобы скопировать):\n"
                   f"👉 <code>{link}</code>"
        )
    else:
        caption = (
                    f"👥 Пригласите друга и получите 1 месяц бесплатно!\n\n"
                    f"✨ Каждый новый переход по вашей ссылке — это ещё +1 месяц к вашему доступу.\n\n"
                    f"🚀 Делитесь ссылкой, приглашайте друзей и продлевайте свой VPN бесплатно.\n\n"
                    f"🔥 Чем больше друзей перейдёт по ссылке, тем дольше ваш бонусный срок!\n\n"
                    f"🔗 Ваша ссылка (нажми, чтобы скопировать):\n"
                    f"👉 <code>{link}</code>"
        )




# 📊 Мои бонусы
# 👥 Пришло: {ref_count}
# 🎁 Бонусные месяцы: {bonus_months} мес.
# 💸 Выплаты по ссылкам: {affiliate_payout} ₽
    #####################################################################################################

    # Вариант с изменением сообщения без удаления.


    photo = FSInputFile('source/pictures/referral_rewards.jpg')

    media = InputMediaPhoto(
        media=photo,
        caption=caption,
        parse_mode="HTML")

    await callback.bot.edit_message_media(media=media,
                                          chat_id=callback.from_user.id,
                                          message_id=callback.message.message_id,
                                          reply_markup=get_refer_back_button())
