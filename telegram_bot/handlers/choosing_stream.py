import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.context import FSMContext


from keyboards.get_menu import get_stream_payment_buttons
from db.select_methods import get_stream_info, get_product_info, get_user_info_by_tg_id
from settings.config import HOST_URL, HOME_PAGE

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
    user_info = await get_user_info_by_tg_id(tg_user_id=int(callback.from_user.id))
    if not user_info.enrollments:
        price = str(
                    round(float(stream_info.price) * 0.7)
                    )
    else:
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

    ######################################################################################

    ################# Формируем сообщение для пользователя ########################

    politika_url = HOME_PAGE+"policy"
    polzovatelskoe_url = HOME_PAGE+"soglashenie"

    new_caption = (f"🧾 Вы выбрали: {stream_info.title} за {price} ₽.\n\n"
                   f"✅ Нажмите «Продолжить» для перехода к оплате!\n\n"
                   f"📚 Пакет включает доступ и поддержку на весь период!\n\n"
                   f"🚀 Ждём вас на высоких скоростях! ✨\n\n"
                   f"📜 Политика конфиденциальности:\n"
                   f"<a href='{politika_url}'>политика</a>\n\n"
                   f"⚖️ Пользовательское соглашение:\n"
                   f"<a href='{polzovatelskoe_url}'>соглашение</a>\n\n"
                   f"Нажимая продолжить, Вы принимаете условия оферты.\n")

    buttons = get_stream_payment_buttons(price_menu=price,
                                         product_id=stream_info.product_id,
                                         stream_id=stream_id)


    # await callback.message.edit_caption(caption=new_caption, reply_markup=buttons, parse_mode="HTML")
    # buttons = get_payment_notification_button(price=f"{price}", stream_id=stream_id_int, directions_id=directions_id)
    photo = FSInputFile('source/pictures/confirmation_payment_details.jpg')
    media = InputMediaPhoto(
        media=photo,
        caption=new_caption,
        parse_mode='HTML'
    )

    await callback.message.edit_media(media=media, reply_markup=buttons)
