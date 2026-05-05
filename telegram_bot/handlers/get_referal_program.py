import asyncio
import logging
from pprint import pprint

from aiogram import Router, F
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import Message, InputMediaPhoto
from aiogram.utils.deep_linking import create_start_link
from sqlalchemy.sql.functions import count

from db.update_methods_dao import update_payment_data, update_referral_rewards, update_referral_rewards_month, \
    update_user_reward
from keyboards.get_menu import get_start_menu, get_stream_products_menu, get_choice_refer_button, get_start_button, \
    get_refer_back_button, get_errors_button, get_back_button
from aiogram.types import FSInputFile

from db.select_methods import get_list_directions, get_product_info, get_user_info_by_tg_id, \
    get_enrollmets_from_user_id, get_referralrewards_from_user_id, get_stream_info, get_referralrewards_to_month_user_d
from db.add_methods_dao import check_user_and_add, add_new_referral_rewards, add_new_enrollments

from aiogram.fsm.context import FSMContext

from aiogram.types import CallbackQuery

from settings.config import TECH_CHANNEL, PASSWORD, USER
from utils.calculate_expire_date import get_expire_time_sec
# from settings.config import START_DATE
# from settings.config import START_DATE
from utils.get_links import get_subscribe_link
from utils.states import OrderPay
from utils.timezone import get_moscow_today
from utils.vlessuiapi import XUIClient

from dateutil.relativedelta import relativedelta
import datetime as DT

router = Router()


# def get_main_window_menu():

# "get_referral_program:{user_id}"

@router.callback_query(F.data.startswith("get_referral_program:"))
async def get_referral_program(callback: CallbackQuery, state: FSMContext):

    # get_referral_link:{one_user_info['id']}

    await callback.answer(text=f"Вы выбрали меню Ваши бонусы")

    user_id = callback.data.split(':')[1]

    refer_info = await get_referralrewards_from_user_id(referred_user_id=int(user_id))

    ref_count = len(refer_info)
    bonus_months = 0
    affiliate_payout = 0.0

    for refer in refer_info:
        if refer.active_status == True and refer.reward_type == "month":
            bonus_months+=1
        if refer.active_status == True and refer.reward_type == "percent":
            affiliate_payout+=float(refer.reward_value)

    #####################################################################################################

    # Вариант с изменением сообщения без удаления.

    # referral_caption = (f"Здесь вы можете посмотреть, что доступно именно вам: "
    #                     f"текущий бонусный срок, приглашённых друзей и активные награды.\n\n"
    #                     f"🧾 Ваш отчет:\n\n"
    #                     f"👥 Пришло: {ref_count}\n"
    #                     f"🎁 Бонусные месяцы: {bonus_months} мес.\n"
    #                     f"💸 Выплаты по ссылкам: {affiliate_payout} ₽\n\n"
    #                     f"✨ За каждого нового друга по вашей ссылке начисляется "
    #                     f"1 месяц доступа или проценты от стоимости его покупки\n\n"
    #                     f"👥 Количество приглашений влияет на общий бонусный срок и выплаты\n\n"
    #                     f"🚀 Делитесь ссылкой и продлевайте VPN бесплатно.")

    referral_caption = (
        f"🔥 <b>РЕФЕРАЛКА</b>\n"
        f"Здесь вы можете посмотреть, что доступно именно вам: "
        f"текущий бонусный срок, приглашённых друзей и активные награды.\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📊 <b>СТАТИСТИКА</b>\n"
        f"  • 👥 Приглашено: <b>{ref_count}</b>\n"
        f"  • 🎁 Бонусные месяцы: {bonus_months} мес.\n"
        f"  • 💸 Выплаты по ссылкам: {affiliate_payout} ₽\n\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"💎 <b>1 друг = 1 месяц доступа или проценты от стоимости его покупки</b>\n\n"
        f"👥 Количество приглашений влияет на общий бонусный срок и выплаты\n\n"
        f"🚀 Делитесь ссылкой и продлевайте VPN бесплатно."
    )

    photo = FSInputFile('source/pictures/referral_rewards.jpg')

    media = InputMediaPhoto(
        media=photo,
        caption=referral_caption,
        parse_mode="HTML")

    await callback.bot.edit_message_media(media=media,
                                          chat_id=callback.from_user.id,
                                          message_id=callback.message.message_id,
                                          reply_markup=get_refer_back_button())




@router.callback_query(F.data.startswith("get_free_month:"))
async def get_free_month(callback: CallbackQuery, state: FSMContext):

    # get_free_month

    await callback.answer(text=f"Оформляем Месяц бесплатно")

    # get_free_month:{stream_id}:{price}:{directions_id}

    # choosing_method: {stream_id}:{price}: {directions_id} TODO ADD BACK BUTTON

    list_data_buttons = callback.data.split(":")
    stream_id = int(list_data_buttons[1])
    price = int(list_data_buttons[2])

    # message_id = callback.message.message_id

    ###################### Получаем данные из FSM #########################
    # key = StorageKey(
    #     bot_id=callback.bot.id,
    #     chat_id=callback.from_user.id,  # личный чат пользователя
    #     user_id=callback.from_user.id,  # сам пользователь
    # )
    #
    # # Пример user_data
    # # user_data = dict(stream_id_int=stream_id_int,
    # #                  price=price,
    # #                  directions_id=directions_id,
    # #                  operation_id=payments_operation_data.get('operation_id', '*********'),
    # #                  payment_id=payment_data_to_provider.id)
    #
    # user_data = await state.storage.get_data(key=key)
    # logging.debug(f"user_data = {user_data}")
    # directions_id = user_data.get("directions_id")
    # pay_method = user_data.get("pay_method")

    ################# Получаем Статус для Реферальной программы ########################################

    user_info = await get_user_info_by_tg_id(tg_user_id=int(callback.from_user.id))

    refer_info = await get_referralrewards_to_month_user_d(id_user=int(user_info.id))

    if refer_info:
        refer_status = "APPROVED"
    else:
        refer_status = "NOT_APPROVED"

    # Получаем Данные Потока и Продукта

    stream_info = await get_stream_info(id_stream=stream_id)
    product_info = await get_product_info(id_product=stream_info.product_id)

    # 'APPROVED'
    if refer_status == "APPROVED":

        # # Обновляем запись в БД об оплате
        #
        # payment_data = await update_payment_data(
        #     payment_id=user_data.get("payment_id"),
        #     new_operation_id=user_data.get("operation_id"),
        #     new_status=refer_status,
        #     stream_id=stream_info.id
        #
        # )

        logging.info("Получен запрос на бесплатный месяц.")

        # Обновляем запись в БД ReferralRewards

        # referral_rewards = dict(user_id=int(user_info.get("id")),
        #                         referred_user_id=referred_by_user_id,
        #                         payment_id=None,
        #                         reward_type=reward_type,
        #                         reward_value=None,
        #                         active_status=None)



        referral_rewards = dict(reward_type="month",
                                active_status=False)


        referral_data = await update_user_reward(user_id=user_info.id, values_dict=referral_rewards)

        logging.debug(referral_data)

        #################### EXPIRE_DATE ############################

        delta = "month"
        today = DT.datetime.now()

        if delta == "day":
            expire_date = today + relativedelta(days=1)
        elif delta == "month":
            expire_date = today + relativedelta(months=1)
        elif delta == "year":
            expire_date = today + relativedelta(years=1)
        else:
            expire_date = today

        # Нормализуем к дате
        if isinstance(expire_date, DT.datetime):
            expiredate_to_db = expire_date.date()
        else:
            expiredate_to_db = expire_date

        expire_time_sec = get_expire_time_sec(expire_date=expire_date)

        #################### Vles VPN ###############################

        base_url = product_info.base_url
        # https://155.212.228.65:49699/IIVMNd0IoCAcUBOuKK
        try:
            await callback.message.edit_caption(caption=f"⏳ <b>Выполняется проверка.</b>\n\n"
                                                        f"Пожалуйста, подождите несколько секунд\n\n"
                                                        f"💡 <i>Не закрывайте окно и не обновляйте страницу</i>\n\n"
                                                        f"🔄 <b>Статус:</b>\n"
                                                        f"<code>Проверка в процессе...</code>",
                                                parse_mode="HTML")
            logging.info(f"💡 Отправлено сообщение о выполнении операции")
        except Exception as exception_text:
            buttons = get_errors_button()
            await callback.message.edit_caption(caption=f"❌ <b>Что-то пошло не так</b>… Повторите попытку позже\n\n"
                                                        f"📢 <b>Сообщите в поддержку</b> и прикрепите текст ошибки\n\n"
                                                        f"💡 <i>Чтобы скопировать — просто нажмите на текст</i>\n\n"
                                                        f"🔴 <b>Ошибка:</b>\n"
                                                        f"<code>{exception_text}</code>",
                                                parse_mode="HTML",
                                                reply_markup=buttons)
        await asyncio.sleep(10)
        try:
            vless_client = XUIClient(base_url_from_panel=base_url,
                                     username=USER,
                                     password=PASSWORD,
                                     verify_ssl=True,
                                     public_inbound_key=product_info.public_key,
                                     sid=product_info.short_id)

            client_uuid_from_payment = vless_client._generate_client_uuid()

            obj = vless_client.get_client_traffic_by_id(client_uuid=client_uuid_from_payment).get("obj")

            if isinstance(obj, list) and obj == []:
                logging.info(f"📢 Создаем ссылку для клиента с UUID = {client_uuid_from_payment}")
                link = vless_client.add_client(client_uuid=client_uuid_from_payment,
                                               flow="xtls-rprx-vision",
                                               inbound_id="1",
                                               expiry_time=expire_time_sec,
                                               email=f"{callback.from_user.id}_{client_uuid_from_payment}").get(
                    'subscription_link')
            else:
                logging.info(f"💡 Клиент c UUID = {client_uuid_from_payment} уже есть в 3xui")
                logging.debug(obj)
                link = None

        except Exception as exception_text:
            # < code > текст < / code >
            buttons = get_errors_button()
            await callback.message.edit_caption(caption=f"❌ <b>Что-то пошло не так</b>… Повторите попытку позже\n\n"
                                                        f"📢 <b>Сообщите в поддержку</b> и прикрепите текст ошибки\n\n"
                                                        f"💡 <i>Чтобы скопировать — просто нажмите на текст</i>\n\n"
                                                        f"🔴 <b>Ошибка:</b>\n"
                                                        f"<code>{exception_text}</code>",
                                                parse_mode="HTML",
                                                reply_markup=buttons)
            await callback.bot.send_message(chat_id=TECH_CHANNEL,
                                            text=(f"❌ <b>Ошибка создания VLess ссылки</b>\n\n"
                                                  f"📢 user_tg_id = {callback.from_user.id} user_name = {callback.from_user.username}\n"
                                                  f"🔴 <b>Ошибка:</b>\n"
                                                  f"<code>{exception_text}</code>"),
                                            parse_mode="HTML",
                                            reply_markup=None)
            return

        ############### Запись в БД Enrollments ################
        if link:
            enrollment_data = dict(
                active=True,
                user_id=user_info.id,
                expire_date=expiredate_to_db,
                title_product=product_info.title,
                product_id=stream_info.product_id,
                stream_id=stream_info.id,
                vless_user_name=client_uuid_from_payment,
                vless_link=link
            )

            new_enrollment = await add_new_enrollments(enrollment_data=enrollment_data)

            logging.debug("Сделана запись в Enrollments:\n%s", new_enrollment)

        # user_info = await get_userinfo_by_id(user_id=payment_data.user_id)
        # await restore_chat_access(
        #     bot=callback.bot,
        #     stream_info=stream_info,
        #     user_info=user_info,
        # )

        caption = (
            "✅ Проверка оплаты прошла успешно!\n\n"
            f"💰 Вы оплатили!\n"
            f"📦 Название Продукта: {stream_info.title}\n"
            # f"💳 Стоимость: {payment_data.amount} ₽\n\n"
            f"🔓 Чтобы получить доступы\nперейдите в Главное меню,\nнажмите кнопку Мои покупки\n\n"
            f"📱 < Главное меню -> Мои покупки >\n\n"
            f"🚀 Мы рады видеть тебя в нашей команде! 🎊"
        )
        animation = FSInputFile("source/pictures/referral_rewards.jpg")
        media = InputMediaPhoto(media=animation, caption=caption)
        # await state.clear()

    # "NOT_APPROVED"
    else:
        ################################ MANUAL MODE ###################################
        # TODO Сделать Видео или GIF о том как отправить квитанцию
        # Обновить запись в БД об оплате

        # Пример user_data
        # user_data = dict(stream_id_int=stream_id_int,
        #                  price=price,
        #                  directions_id=directions_id,
        #                  operation_id=payments_operation_data.get('operation_id', '*********'),
        #                  payment_id=payment_data_to_provider.id)

        # payment_data = await update_payment_data(payment_id=user_data.get("payment_id", '000000'),
        #                                          new_operation_id=user_data.get("operation_id", "None"),
        #                                          new_status=refer_status,
        #                                          stream_id=stream_info.id)

        # logging.info("Проверка оплаты не прошла:\n%s", )

        # caption = (
        #     f"💁🏻‍♂️ Оплатили?\n\n🧾 Тогда отправьте сюда (В ЭТОТ БОТ) квитанцию платежа: скриншот или документ.\n\n"
        #     f"Нажмите на «Скрепку» в левом или правом нижнем углу (рядом с полем, где вы пишете текст). "
        #     f"Выберите скриншот или документ.\n\n"
        #     f"Чтобы «Отправить», нажмите на синюю кнопку со стрелочкой в правом нижнем углу.\n\n"
        #     f"На квитанции должны быть четко видны: дата, время и сумма платежа.\n___________________________\n\n"
        #     f"Наши Контакты:\n\n👉 @user_post\n\n__________________________\n"
        #     f"За спам вы можете быть заблокированы!"
        # )
        #

        caption = (
            f"✨ Бесплатных месяцев пока нет.\n\n"
            f"🎉 За каждого нового друга по вашей ссылке начисляется "
            f"1 месяц доступа или проценты от стоимости его покупки\n\n"
            f"👥 Количество приглашений влияет на общий бонусный срок и выплаты\n\n"
            f"🚀 Делитесь ссылкой и продлевайте VPN бесплатно.\n\n"
            f"🔗 Ссылку можно получить в меню реферальной программы"
        )

        animation = FSInputFile("source/pictures/referral_rewards.jpg")
        media = InputMediaPhoto(media=animation, caption=caption)
        #
        # user_data["message_id"] = callback.message.message_id
        #
        # await state.storage.update_data(key=key, data=user_data)
        # await state.set_state(OrderPay.send_check)

    await callback.message.edit_media(media=media,
                                      reply_markup=get_errors_button()
                                      )


