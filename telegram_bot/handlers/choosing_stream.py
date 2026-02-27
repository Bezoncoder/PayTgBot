import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.context import FSMContext


from keyboards.get_menu import get_stream_payment_buttons
from db.select_methods import get_stream_info, get_product_info

'''

Обрабатываем выбор потока пользователя.

'''

router = Router()

# set_stream:{button.id}:{price_menu} choosing_stream get_pay:{product_id}:{price_menu} -> get_payed
# set_product:{button.id} <- set_stream:{stream_id}:{price} -> get_pay:{product_id}:{price_menu}

# set_stream:stream_id:price
@router.callback_query(F.data.startswith("set_stream:"))
async def set_stream(callback: CallbackQuery, state: FSMContext):

    list_buttons_data = callback.data.split(':')
    stream_id = int(list_buttons_data[1])

    await callback.answer()

    ################## Обрабатываем нужный поток и передаем на оплату ################

    logging.info("Выбран поток: %s", stream_id)
    stream_info = await get_stream_info(id_stream=stream_id)

    price = str(stream_info.price)

    ########################## Получаем Информацию о Продукте ##########################

    product_info_pydantic = await get_product_info(id_product=stream_info.product_id)

    ###################### Сохраняем данные Пользователю в FSM #########################
    user_key = StorageKey(
        bot_id=callback.bot.id,
        chat_id=callback.from_user.id,  # личный чат пользователя
        user_id=callback.from_user.id,  # сам пользователь
    )

    direction_id = product_info_pydantic.direction_id

    user_data = dict(directions_id=direction_id)

    await state.storage.update_data(user_key, data=user_data)  # <— сохраняем для ЭТОГО пользователя

    # product_description = str(product_pydantic.description)

    ######################################################################################

    ################# Формируем сообщение для пользователя ########################
    # start_date = stream_info.start_date
    # end_date = stream_info.end_date

    # new_photo = FSInputFile(f'source/pictures/payment.png')
    # offerta_link = "https://roadmappers.ru/oferta"  # сюда подставь ссылку, если есть
    # link_part = f" ({offerta_link})" if offerta_link else ""
    # new_caption = (f'Вы выбрали поток: {start_date} - {end_date}\n'
    #                f'Стоимость {price}.\n\n'
    #                f'Нажмите Оплатить для оплаты.\n\n'
    #                f"Нажимая кнопку «Оплатить», вы соглашаетесь с условиями оферты {link_part}.\n\n"
    #                f'\n⚠️ Оплата производится исключительно с карты физического лица!\n\n')

    new_caption = (f"🧾 Вы выбрали: {stream_info.title} за {stream_info.price} ₽.\n\n"
                   f"✅ Нажмите «Продолжить» для перехода к оплате!\n\n"
                   f"📚 Пакет включает доступ и поддержку на весь период!\n\n"
                   f"🚀 Ждём вас на высоких скоростях! ✨\n\n"
                   f"📜 Политика конфиденциальности:\n"
                   f"https://telegra.ph/Politika-konfidencialnosti-08-15-17\n\n"
                   f"⚖️ Пользовательское соглашение:\n"
                   f"https://telegra.ph/Polzovatelskoe-soglashenie-08-15-10\n\n"
                   f"Нажимая продолжить, Вы принимаете условия оферты.\n")

    buttons = get_stream_payment_buttons(price_menu=price,
                                         product_id=stream_info.product_id,
                                         stream_id=stream_id)


    await callback.message.edit_caption(caption=new_caption, reply_markup=buttons)
