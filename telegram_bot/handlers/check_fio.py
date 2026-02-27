import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InputMediaPhoto, FSInputFile

from aiogram.fsm.storage.base import StorageKey

from aiogram.fsm.context import FSMContext

from db.select_methods import (
    get_user_info_by_tg_id,
    get_enrollmets_from_user_id,
    get_stream_info,
)
from db.add_methods_dao import set_full_name
from keyboards.get_menu import (
    get_change_user_data_dialog_button,
    get_subscribe_menu,
)
# from db.select_methods import get_expire_date_user_id

# from utils.jira_functional.jira_functions import onboard_user_with_tasks
from utils.states import OrderPay  # <— добавлено

router = Router()


JIRA_INSTRUCTION = (
    "✨ Инструкция: Как сообщить имя и фамилию для создания задач в Jira ✨\n\n"
    "📝 Введите данные\nНапишите ваше имя и фамилию в формате:\n\n"
    "Пример: Алексей Ломов\n\n"
    "🔍 Проверьте правильность\n"
    "Убедитесь, что все данные указаны корректно и без ошибок.\n\n"
    "📤 Отправьте сообщение\nПосле проверки отправьте информацию — мы создадим задачи в Jira!\n\n"
    "Просто отправьте свои данные в чат. 😊"
)


async def _delete_user_message(message: Message) -> bool:
    """Try to delete the user's FIO message from chat."""
    try:
        await message.delete()
        return True
    except Exception as exc:  # pragma: no cover - best-effort cleanup
        logging.warning("Failed to delete Jira message %s: %s", message.message_id, exc)
        return False


async def _get_subscribe_markup(tg_user_id: int):
    user_info = await get_user_info_by_tg_id(tg_user_id=tg_user_id)
    user_id = (user_info or {}).get("id")
    buttons = None
    if user_id:
        enrollments = await get_enrollmets_from_user_id(id_user=user_id)
        stream_titles: dict[int, str] = {}
        for enrolment in enrollments:
            stream_id = enrolment.stream_id
            if not stream_id or stream_id in stream_titles:
                continue
            try:
                stream = await get_stream_info(id_stream=stream_id)
            except Exception as exc:  # pragma: no cover - logging only
                logging.warning("Failed to load stream %s: %s", stream_id, exc)
                continue
            if stream and stream.title:
                stream_titles[stream_id] = stream.title
        buttons = get_subscribe_menu(
            enrolments=enrollments,
            stream_titles=stream_titles,
        )
    return user_info, buttons


@router.message(OrderPay.check_fio, F.text)
async def send_fio_verification(message: Message, state: FSMContext):
    fio = message.text.strip()

    logging.debug("FSM before save: %s", await state.get_data())

    await state.update_data(fullname=fio, fio_user_message_id=message.message_id)  # <— сохраняем для ЭТОГО пользователя

    logging.debug("FSM after save: %s", await state.get_data())

    buttons_data = ["change_fio", "set_jira"]

    confirmation_text = (
        f"Ваши данные указаны Верно?\nТак Вас будут называть на Дейликах!\n\n{fio}"
    )
    target_message_id = (await state.get_data()).get("fio_message_id")
    reply_markup = get_change_user_data_dialog_button(callback_data_list=buttons_data)
    if target_message_id:
        try:
            await message.bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=target_message_id,
                caption=confirmation_text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
            if await _delete_user_message(message):
                await state.update_data(fio_user_message_id=None)
            return
        except Exception as exc:  # pragma: no cover - fallback path
            logging.warning("Failed to edit Jira caption for confirmation: %s", exc)
    sent_message = await message.answer(
        text=confirmation_text,
        reply_markup=reply_markup,
    )
    await state.update_data(fio_message_id=sent_message.message_id)
    if await _delete_user_message(message):
        await state.update_data(fio_user_message_id=None)


@router.callback_query(F.data == "change_fio", )
async def change_fio(callback: CallbackQuery, state: FSMContext):
    tg_user_id = callback.from_user.id
    await callback.answer()

    data = await state.get_data()
    user_message_id = (data or {}).get("fio_user_message_id")
    if user_message_id:
        try:
            await callback.bot.delete_message(
                chat_id=tg_user_id,
                message_id=user_message_id,
            )
        except Exception as exc:  # pragma: no cover - best-effort cleanup
            logging.warning("Failed to delete Jira user message %s: %s", user_message_id, exc)
        finally:
            await state.update_data(fio_user_message_id=None)

    user_info, subscribe_markup = await _get_subscribe_markup(tg_user_id=tg_user_id)
    stored_full_name = (user_info or {}).get("full_name")
    buttons = subscribe_markup or callback.message.reply_markup
    if stored_full_name:
        photo = FSInputFile("source/pictures/jira.png")
        media = InputMediaPhoto(
            media=photo,
            caption=f"Имя для Jira:\n{stored_full_name}",
            parse_mode="HTML",
        )
        try:
            await callback.message.edit_media(
                media=media,
                reply_markup=buttons,
            )
        except Exception:
            await callback.bot.send_photo(
                chat_id=tg_user_id,
                photo=photo,
                caption=f"Имя для Jira:\n{stored_full_name}",
                parse_mode="HTML",
                reply_markup=buttons,
            )
        await state.clear()
        return

    # Ставим состояние ИМЕННО пользователю

    storage = state.storage

    key = StorageKey(
        bot_id=callback.bot.id,
        chat_id=tg_user_id,  # личный чат пользователя
        user_id=tg_user_id  # сам пользователь

    )
    ##### expire_time to FSM Storage ####
    # print("FSM before save:", await state.storage.get_data(key=key))
    # await state.update_data(expire_time_sec=expire_time)  # <— сохраняем для ЭТОГО пользователя
    # await state.storage.update_data(key, data=data)  # <— сохраняем для ЭТОГО пользователя
    # print("FSM after save:", await state.storage.get_data(key=key))

    logging.debug("Состояние для пользователя установлено: %s", await storage.get_state(key))

    instructions_media = InputMediaPhoto(
        media=FSInputFile("source/pictures/jira.png"),
        caption=JIRA_INSTRUCTION,
        parse_mode="HTML",
    )
    message_id = callback.message.message_id
    try:
        await callback.message.edit_media(
            media=instructions_media,
            reply_markup=buttons,
        )
    except Exception as exc:  # pragma: no cover - fallback path
        logging.warning("Failed to edit Jira media for instructions: %s", exc)
        sent_message = await callback.bot.send_photo(
            chat_id=tg_user_id,
            photo=FSInputFile("source/pictures/jira.png"),
            caption=JIRA_INSTRUCTION,
            parse_mode="HTML",
            reply_markup=buttons,
        )
        message_id = sent_message.message_id

    await state.update_data(fio_message_id=message_id)

    await storage.set_state(key, OrderPay.check_fio)


@router.callback_query(F.data == "set_jira")
async def set_jira(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    await callback.answer()

    key = StorageKey(
        bot_id=callback.bot.id,
        chat_id=telegram_id,  # личный чат пользователя
        user_id=telegram_id  # сам пользователь

    )

    data = await state.storage.get_data(key=key)

    fullname = (data or {}).get("fullname", "").strip()

    logging.debug(f"fullname = %s", fullname)

    target_message_id = (data or {}).get("fio_message_id") or callback.message.message_id

    if not fullname or " " not in fullname:
        error_text = (
            "Похоже, ФИО введено некорректно. "
            "Отправьте имя и фамилию в одном сообщении (например: «Виталий Гогунский»)."
        )
        reply_markup = get_change_user_data_dialog_button(
            callback_data_list=["change_fio", "set_jira"]
        )
        try:
            await callback.bot.edit_message_caption(
                chat_id=telegram_id,
                message_id=target_message_id,
                caption=error_text,
                reply_markup=reply_markup,
            )
        except Exception as exc:  # pragma: no cover - fallback path
            logging.warning("Failed to edit Jira caption for error: %s", exc)
            new_message = await callback.bot.send_message(
                chat_id=telegram_id,
                text=error_text,
            )
            target_message_id = new_message.message_id
        await state.update_data(fio_message_id=target_message_id)
        await state.storage.set_state(key, OrderPay.check_fio)
        return

    await set_full_name(telegram_id=telegram_id, full_name=fullname)

    _user_info, subscribe_markup = await _get_subscribe_markup(tg_user_id=telegram_id)
    buttons = subscribe_markup or callback.message.reply_markup
    user_message_id = (data or {}).get("fio_user_message_id")
    success_media = InputMediaPhoto(
        media=FSInputFile("source/pictures/jira.png"),
        caption=(
            f"Имя для Jira:\n{fullname}\n\n"
            "Имя сохранено. Когда выдадим доступы, задачи в Jira создадутся автоматически."
        ),
        parse_mode="HTML",
    )
    try:
        await callback.message.edit_media(
            media=success_media,
            reply_markup=buttons,
        )
    except Exception as exc:  # pragma: no cover - fallback path
        logging.warning("Failed to edit Jira media after save: %s", exc)
        await callback.bot.send_photo(
            chat_id=telegram_id,
            photo=FSInputFile("source/pictures/jira.png"),
            caption=success_media.caption,
            parse_mode="HTML",
            reply_markup=buttons,
        )
    await state.clear()
    if user_message_id:
        try:
            await callback.bot.delete_message(
                chat_id=telegram_id,
                message_id=user_message_id,
            )
        except Exception as exc:  # pragma: no cover - best-effort cleanup
            logging.warning("Failed to delete Jira user message %s: %s", user_message_id, exc)





    # ##################   Отправляем креды  ###################
    #
    # link = await get_subscribe_link()
    # creds_info = await get_creds(str(telegram_id))
    # photo = FSInputFile(f"bootcamp.jpg")
    # # формируем единый caption
    # caption = (
    #     "Оплата прошла успешно.\n\n"
    #     "Добро пожаловать в нашу команду.\n"
    #     f"Ваша ссылка в закрытый чат:\n{link}\n\n"
    #     "Ссылка действует только 24ч.\n"
    #     "Дальнейшие инструкции в закрытом канале.\n\n"
    #     f"{creds_info}\n\n"
    # )
    # await callback.bot.send_photo(
    #     chat_id=telegram_id, photo=photo, caption=caption, parse_mode="HTML"
    # )
    # # fullname = (data or {}).get("fullname", "").strip()
    # current_directory = os.getcwd()
    #
    # # expire_time_sec
    # print(f"Начинаем Создавать сертификат.")
    # print(data)
    # expire_time_sec = data.get("expire_time_sec")
    # print(f"expire_time_sec = {expire_time_sec} имеет тип {type(expire_time_sec)}")
    #
    # cert_path = get_signed_cert(cert_dir=current_directory,
    #                             user_id=telegram_id,
    #                             expiretime=expire_time_sec
    #                             )
    #
    # document = FSInputFile(f"{cert_path}")
    #
    # how_to_usage_openvpn = """<b>Как подключиться к буткемпу через OpenVPN 🔐</b>\n
    #     \n
    #     1. 💻 Установи OpenVPN с официального сайта: <a href="https://openvpn.net/client/">https://openvpn.net/client/</a>\n
    #     2. 📁 Скачай конфигурационный файл, который тебе прислал бот.\n
    #     3. 📂 Открой этот файл — он автоматически запустится в клиенте OpenVPN.\n
    #     4. 🔌 Нажми «Подключиться».\n
    #     \n
    #     🏗️ Инфраструктура буткемпа будет доступна <b>только при включённом VPN</b>.\n
    #     🌍 При этом ты можешь параллельно пользоваться другим VPN для YouTube, ChatGPT и т.д.\n
    #     \n
    #     Если что-то не работает — пиши, поможем! ✉️\n
    #     Контакты: @halltape | @ShustDE
    #     """
    #
    # await callback.bot.send_document(
    #     chat_id=telegram_id,
    #     document=document,
    #     caption=how_to_usage_openvpn,
    #     parse_mode="HTML",
    # )
    # os.remove(cert_path)
