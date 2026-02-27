import logging
from aiogram import Bot

from db.schemas import StreamPydantic, UserPydantic


async def restore_chat_access(bot: Bot,
                              stream_info: StreamPydantic | None,
                              user_info: UserPydantic | None) -> None:
    """Unban user from product chat when they repurchase access."""
    if stream_info is None or stream_info.tg_channel_id is None:
        logging.debug("Skip chat unban: stream does not have tg_channel_id")
        return
    if user_info is None or user_info.telegram_id is None:
        logging.debug("Skip chat unban: telegram_id is missing for user %s", getattr(user_info, "id", None))
        return

    try:
        chat_id = int(stream_info.tg_channel_id)
        user_tg_id = int(user_info.telegram_id)
    except (TypeError, ValueError):
        logging.error("Cannot convert ids for chat unban: chat=%s user=%s",
                      getattr(stream_info, "tg_channel_id", None),
                      getattr(user_info, "telegram_id", None))
        return

    try:
        await bot.unban_chat_member(chat_id=chat_id, user_id=user_tg_id, only_if_banned=True)
        logging.info("Разблокирован пользователь %s в чате %s", user_tg_id, chat_id)
    except Exception as exc:
        logging.error("Не удалось разбанить пользователя %s в чате %s: %s", user_tg_id, chat_id, exc)
