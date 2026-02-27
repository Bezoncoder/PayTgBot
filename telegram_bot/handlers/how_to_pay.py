import logging
from typing import Any, Awaitable, Callable, Dict, Tuple

from aiogram import Router, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, FSInputFile, TelegramObject

router = Router()

# user_id -> (chat_id, message_id) для сообщения с видео "Как оплатить"
how_to_pay_messages: Dict[int, Tuple[int, int]] = {}


# class HowToPayCleanupMiddleware(BaseMiddleware):
#     async def __call__(
#         self,
#         handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
#         event: TelegramObject,
#         data: Dict[str, Any],
#     ) -> Any:
#         if isinstance(event, CallbackQuery):
#             info = how_to_pay_messages.pop(event.from_user.id, None)
#             if info:
#                 chat_id, message_id = info
#                 try:
#                     await event.bot.delete_message(chat_id=chat_id, message_id=message_id)
#                 except Exception as exc:  # pragma: no cover - защитное логирование
#                     logging.warning("Не удалось удалить сообщение how_to_pay: %s", exc)
#         return await handler(event, data)


@router.callback_query(F.data == "how_to_pay_video")
async def send_how_to_pay(callback: CallbackQuery):
    """Send payment instruction video and brief description."""
    await callback.answer()

    # Удалим предыдущее сообщение, если оно есть
    prev = how_to_pay_messages.pop(callback.from_user.id, None)
    if prev:
        chat_id, message_id = prev
        try:
            await callback.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as exc:
            logging.warning("Не удалось удалить предыдущее сообщение how_to_pay: %s", exc)

    video = FSInputFile("videos/how_to_pay.mp4")
    caption = (
        "Как оплатить подписку или доступы.\n"
        "Оплата доступна по СБП или сервисом «Долями»."
    )
    sent = await callback.message.answer_video(
        video=video,
        caption=caption,
        width=1080,
        height=1920,
        supports_streaming=True,
    )
    how_to_pay_messages[callback.from_user.id] = (sent.chat.id, sent.message_id)


@router.message(Command("info"))
async def info(message: Message):
    """Provide contact info for questions."""
    await message.answer("Если возникли вопросы, писать @halltape или @ShustDE")
