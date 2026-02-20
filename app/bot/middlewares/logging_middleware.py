import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = logging.getLogger("user_actions")


def _user_str(event: TelegramObject) -> str:
    """Строка с id, first_name, last_name, username пользователя."""
    user = getattr(event, "from_user", None)
    if user is None:
        return "user=?"
    first = getattr(user, "first_name", None) or ""
    last = getattr(user, "last_name", None) or ""
    username = getattr(user, "username", None) or ""
    return (
        f"id={user.id} first_name={first!r} last_name={last!r} username={username!r}"
    )


def _action_str(event: TelegramObject) -> str:
    """Команда или действие пользователя."""
    if isinstance(event, Message):
        text = (event.text or "").strip()
        if text.startswith("/"):
            cmd = text.split(maxsplit=1)[0]
            return f"command={cmd}"
        if text:
            return f"message={text[:80]!r}"
        return "message=(no text)"
    if isinstance(event, CallbackQuery):
        return f"callback={event.data!r}"
    return "action=?"


class LoggingMiddleware(BaseMiddleware):
    """Пишет в лог время и действие пользователя (id, first_name, last_name, username, команда/действие)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_part = _user_str(event)
        action_part = _action_str(event)
        logger.info("%s | %s", user_part, action_part)
        return await handler(event, data)
