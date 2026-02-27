import asyncio
import logging
import re
from typing import Optional

import requests
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InputMediaPhoto, FSInputFile

from aiogram.fsm.storage.base import StorageKey

from aiogram.fsm.context import FSMContext

from db.add_methods_dao import set_git_link
from db.select_methods import (
    get_user_info_by_tg_id,
    get_enrollmets_from_user_id,
    get_stream_info,
)
from keyboards.get_menu import (
    get_change_user_data_dialog_button,
    get_subscribe_menu,
)
# from settings.config import GIT_TOKEN
from utils.states import OrderPay


router = Router()

GITHUB_USERNAME_RE = re.compile(r"^[A-Za-z0-9](?:-?[A-Za-z0-9]){0,38}$")
GITHUB_INSTRUCTION = (
    "✨ Инструкция: как сообщить GitHub-аккаунт для доступа к репозиторию продукта\n\n"
    "📝 Зачем это нужно\nНам нужен ваш GitHub-ник, чтобы позже добавить вас в репозиторий продукта и выдать доступ.\n\n"
    "📝 Введите ник\nМожно прислать только ник или ссылку на профиль — мы возьмём ник автоматически.\n\n"
    "Пример: username или https://github.com/username\n\n"
    "🔍 Проверьте правильность\nУбедитесь, что ник указан без ошибок.\n\n"
    "📤 Отправьте сообщение\nПосле этого мы сможем добавить вас в репозиторий продукта.\n\n"
    "Просто отправьте никнейм в чат 😊"
)


async def _github_user_exists(username: str) -> Optional[bool]:
    """Check GitHub API for username existence; returns None if validation failed."""
    if not username:
        return None

    def _request():
        headers = {"Accept": "application/vnd.github+json"}
        token = (GIT_TOKEN or "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        url = f"https://api.github.com/users/{username}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
        except requests.RequestException as exc:  # pragma: no cover - logging only
            logging.warning("Failed to validate GitHub username %s: %s", username, exc)
            return None
        if response.status_code == 200:
            return True
        if response.status_code == 404:
            return False
        logging.warning(
            "Got unexpected status %s while validating GitHub username %s",
            response.status_code,
            username,
        )
        return None

    return await asyncio.to_thread(_request)


async def _show_git_error(message: Message, state: FSMContext, error_text: str) -> None:
    """Send or update a GitHub-related error message."""
    target_message_id = (await state.get_data()).get("git_message_id")
    if target_message_id:
        try:
            await message.bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=target_message_id,
                caption=error_text,
                parse_mode="HTML",
            )
            return
        except Exception as exc:  # pragma: no cover - fallback path
            logging.warning("Failed to edit Git caption for error: %s", exc)
    sent_message = await message.answer(error_text, parse_mode="HTML")
    await state.update_data(git_message_id=sent_message.message_id)


async def _delete_user_message(message: Message) -> bool:
    """Try to delete the user's message with their GitHub nickname."""
    try:
        await message.delete()
        return True
    except Exception as exc:  # pragma: no cover - cleanup best effort
        logging.warning("Failed to delete GitHub message %s: %s", message.message_id, exc)
        return False


def _normalize_github_username(raw_value: str) -> Optional[str]:
    """Extract a GitHub username from different input formats."""
    if not raw_value:
        return None

    value = raw_value.strip()
    if not value:
        return None

    value = value.replace("@", "", 1)
    prefixes = (
        "https://github.com/",
        "http://github.com/",
        "github.com/",
        "www.github.com/",
    )
    for prefix in prefixes:
        if value.lower().startswith(prefix):
            value = value[len(prefix):]
            break

    username = value.strip().strip("/").split()[0]
    username = username.split("/")[0]

    if not username or not GITHUB_USERNAME_RE.match(username):
        return None

    return username


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


@router.message(OrderPay.check_git, F.text)
async def send_git_verification(message: Message, state: FSMContext):
    git_from_user = _normalize_github_username(message.text)

    if not git_from_user:
        await _show_git_error(
            message=message,
            state=state,
            error_text=(
                "Не получилось распознать ваш GitHub. Пришлите никнейм или ссылку вида https://github.com/<nickname>."
            ),
        )
        await _delete_user_message(message)
        return

    user_exists = await _github_user_exists(git_from_user)
    if user_exists is False:
        await _show_git_error(
            message=message,
            state=state,
            error_text=(
                f"❌ GitHub пользователя <code>{git_from_user}</code> не существует.\n\n"
                "🔁 Проверьте ник и отправьте его ещё раз."
            ),
        )
        await _delete_user_message(message)
        return
    if user_exists is None:
        logging.warning("Failed to confirm GitHub user existence for %s", git_from_user)

    logging.debug("check_git_verification FSM before save: %s", await state.get_data())
    await state.update_data(
        git_user_name=git_from_user,
        git_user_message_id=message.message_id,
    )  # <— сохраняем для ЭТОГО пользователя
    logging.debug("check_git_verification FSM after save: %s", await state.get_data())

    buttons_data = ["change_git", "set_git"]

    confirmation_text = f"Ваши данные указаны Верно?\n\n{git_from_user}"
    target_message_id = (await state.get_data()).get("git_message_id")
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
                await state.update_data(git_user_message_id=None)
            return
        except Exception as exc:  # pragma: no cover - fallback path
            logging.warning("Failed to edit Git caption for confirmation: %s", exc)
    sent_message = await message.answer(
        text=confirmation_text,
        reply_markup=reply_markup,
    )
    await state.update_data(git_message_id=sent_message.message_id)
    if await _delete_user_message(message):
        await state.update_data(git_user_message_id=None)


@router.callback_query(F.data == "change_git", )
async def change_git(callback: CallbackQuery, state: FSMContext):
    tg_user_id = callback.from_user.id
    await callback.answer()

    data = await state.get_data()
    user_message_id = (data or {}).get("git_user_message_id")
    if user_message_id:
        try:
            await callback.bot.delete_message(
                chat_id=tg_user_id,
                message_id=user_message_id,
            )
        except Exception as exc:  # pragma: no cover - best-effort cleanup
            logging.warning("Failed to delete Git user message %s: %s", user_message_id, exc)
        finally:
            await state.update_data(git_user_message_id=None)

    user_info, subscribe_markup = await _get_subscribe_markup(tg_user_id=tg_user_id)
    stored_git = (user_info or {}).get("git_link")
    buttons = subscribe_markup or callback.message.reply_markup
    if stored_git:
        photo = FSInputFile("source/pictures/github.png")
        media = InputMediaPhoto(
            media=photo,
            caption=f"Мой Github:\nhttps://github.com/{stored_git}",
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
                caption=f"Мой Github:\nhttps://github.com/{stored_git}",
                parse_mode="HTML",
                reply_markup=buttons,
            )
        await state.clear()
        return

    # Ставим состояние ИМЕННО пользователю

    key = StorageKey(
        bot_id=callback.bot.id,
        chat_id=tg_user_id,  # личный чат пользователя
        user_id=tg_user_id  # сам пользователь

    )
    await state.storage.set_state(key, OrderPay.check_git)
    logging.debug("FSM after save: %s", await state.storage.get_data(key=key))
    logging.info("Состояние для пользователя установлено: %s", await state.storage.get_state(key))
    instructions_media = InputMediaPhoto(
        media=FSInputFile("source/pictures/github.png"),
        caption=GITHUB_INSTRUCTION,
        parse_mode="HTML",
    )
    message_id = callback.message.message_id
    try:
        await callback.message.edit_media(
            media=instructions_media,
            reply_markup=buttons,
        )
    except Exception as exc:  # pragma: no cover - fallback path
        logging.warning("Failed to edit Git media for instructions: %s", exc)
        sent_message = await callback.bot.send_photo(
            chat_id=tg_user_id,
            photo=FSInputFile("source/pictures/github.png"),
            caption=GITHUB_INSTRUCTION,
            parse_mode="HTML",
            reply_markup=buttons,
        )
        message_id = sent_message.message_id

    await state.update_data(git_message_id=message_id)


@router.callback_query(F.data == "set_git")
async def set_git(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    await callback.answer()

    key = StorageKey(
        bot_id=callback.bot.id,
        chat_id=telegram_id,  # личный чат пользователя
        user_id=telegram_id  # сам пользователь

    )

    data = await state.storage.get_data(key=key)
    logging.debug("set: 8 data %s", data)
    git_user_name = (data or {}).get('git_user_name')

    message_id = (data or {}).get("git_message_id") or callback.message.message_id

    if not git_user_name:
        error_text = "Не нашёл никнейм. Отправьте его ещё раз."
        reply_markup = get_change_user_data_dialog_button(
            callback_data_list=["change_git", "set_git"]
        )
        try:
            await callback.bot.edit_message_caption(
                chat_id=telegram_id,
                message_id=message_id,
                caption=error_text,
                reply_markup=reply_markup,
            )
        except Exception as exc:  # pragma: no cover - fallback path
            logging.warning("Failed to edit Git caption for error: %s", exc)
            new_message = await callback.bot.send_message(
                chat_id=telegram_id,
                text=error_text,
            )
            message_id = new_message.message_id
        await state.update_data(git_message_id=message_id)
        await state.storage.set_state(key, OrderPay.check_git)
        return

    await set_git_link(telegram_id=telegram_id, git_link=git_user_name)
    _, subscribe_markup = await _get_subscribe_markup(tg_user_id=telegram_id)
    buttons = subscribe_markup or callback.message.reply_markup
    user_message_id = (data or {}).get("git_user_message_id")
    success_media = InputMediaPhoto(
        media=FSInputFile("source/pictures/github.png"),
        caption=(
            f"Мой Github:\nhttps://github.com/{git_user_name}\n\n"
            "Сохранил ник, в ближайшее время добавим доступы."
        ),
        parse_mode="HTML",
    )
    try:
        await callback.message.edit_media(
            media=success_media,
            reply_markup=buttons,
        )
    except Exception as exc:  # pragma: no cover - fallback path
        logging.warning("Failed to edit Git media after save: %s", exc)
        await callback.bot.send_photo(
            chat_id=telegram_id,
            photo=FSInputFile("source/pictures/github.png"),
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
            logging.warning("Failed to delete Git user message %s: %s", user_message_id, exc)
