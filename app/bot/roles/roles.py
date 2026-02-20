from enum import Enum

from aiogram import Bot

from app.config import BotSettings


class UserRole(str, Enum):
    GUEST = "guest"  # кого нет в общей группе.
    USER = "user"
    ADMIN = "admin"


async def is_user_in_group(
    user_id: int,
    bot: Bot,
    bot_config: BotSettings,
) -> bool:
    """Проверка, что пользователь состоит в группе."""
    member = await bot.get_chat_member(bot_config.group_id, user_id)
    return member.status in ("member", "administrator", "creator")


async def get_user_role(
    user_id: int,
    bot: Bot,
    bot_config: BotSettings,
) -> str:
    if user_id in bot_config.admin_ids:
        return UserRole.ADMIN
    elif await is_user_in_group(user_id, bot, bot_config):
        return UserRole.USER
    else:
        return UserRole.GUEST
