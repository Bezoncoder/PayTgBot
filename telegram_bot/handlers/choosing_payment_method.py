import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto

from aiogram.fsm.storage.base import StorageKey

from aiogram.fsm.context import FSMContext

# from db.update_methods_dao import update_user_email
from keyboards.get_menu import get_choosing_pay_method_buttons

# from utils.banking_operations import get_card_creds

# from utils.jira_functional.jira_functions import onboard_user_with_tasks

# from utils.get_links import get_subscribe_link
# from utils.creds import get_creds

router = Router()

'''

Формируем  оплату пользователя. 

'''


# choosing_method:{stream_id_int}:{price_menu}:{directions_id} or '' choosing_pay_method
# set_stream:{stream_id}:{price}  <- choosing_pay_method ->
#                       ->get_pay:{stream_id_int}:{price_menu}:{directions_id}{pay_metod}


################################# ВЫБОР СПОСОБА ОПЛАТЫ ###########################################
@router.callback_query(F.data.startswith("get_choosing_method:"))
async def choosing_pay_method(callback: CallbackQuery, state: FSMContext):

    await callback.answer(text=f"⏳ Выбираем метод оплаты...")

    # get_pay:{stream_id}:{price_menu}:{product_id}:{directions_id}
    # set_group:{directions_id}' Back

    logging.debug("Callback = %s:", callback.data)

    list_data_buttons = callback.data.split(':')
    stream_id_int = int(list_data_buttons[1])
    price = int(list_data_buttons[2])

    ######################## ФОРМИРУЕМ USER_KEY ########################

    user_key = StorageKey(
        bot_id=callback.bot.id,
        chat_id=callback.from_user.id,  # личный чат пользователя
        user_id=callback.from_user.id,  # сам пользователь
    )

    #################### ПОЛУЧАЕМ ДАННЫЕ ПО ОПЛАТЕ #####################

    user_pay_data = await state.storage.get_data(key=user_key)

    ###################### Сохраняем данные Пользователю в FSM #########################

    # user_data = dict(stream_id_int=stream_id_int,
    #                  price=price,
    #                  operation_id=payments_data_from_bd.get('operation_id_from_provider', 'none_operation_id'),
    #                  payment_id=payment_data_from_db.id)
    #
    # await state.storage.update_data(user_key, data=user_data)  # <— сохраняем для ЭТОГО пользователя

    ############################## Платежные Реквизиты ##############################

    new_caption = (f"🔄 Для выбора способа оплаты нажмите соответствующую кнопку.\n\n"
                   f"К оплате: {price} 🇷🇺RUB\n\n"
                   f"Вам доступно:\n"
                   f"💳 Карточный эквайринг\n"
                   f"💰 СБП (QR-код)\n"
                   f"₿ Криптовалюта")

    directions_id = user_pay_data.get("directions_id")
    #     0       1           2             3               4              5
    # get_pay:{stream_id}:{price}:{product_id}:{directions_id}:{method_value} NEW
    buttons = get_choosing_pay_method_buttons(price=f"{price}",
                                              stream_id_int=stream_id_int,
                                              directions_id=directions_id)
    photo = FSInputFile('source/pictures/choosing_payment_method.jpg')
    media = InputMediaPhoto(
        media=photo,
        caption=new_caption,
        parse_mode='HTML'
    )

    await callback.message.edit_media(media=media, reply_markup=buttons)
