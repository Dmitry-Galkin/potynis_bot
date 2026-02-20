from aiogram import Bot
from aiogram.filters import BaseFilter
from aiogram.types import Message

from app.bot.roles import UserRole, get_user_role
from app.config.config import BotSettings


class IsAdmin(BaseFilter):
    def __init__(self, bot: Bot, bot_config: BotSettings) -> None:
        self.bot = bot
        self.bot_config = bot_config

    async def __call__(self, message: Message) -> bool:
        return UserRole.ADMIN == await get_user_role(
            message.from_user.id, self.bot, self.bot_config
        )


class IsUser(BaseFilter):
    def __init__(self, bot: Bot, bot_config: BotSettings) -> None:
        self.bot = bot
        self.bot_config = bot_config

    async def __call__(self, message: Message) -> bool:
        return UserRole.USER == await get_user_role(
            message.from_user.id, self.bot, self.bot_config
        )


class IsAdminOrUser(BaseFilter):
    def __init__(self, bot: Bot, bot_config: BotSettings) -> None:
        self.bot = bot
        self.bot_config = bot_config

    async def __call__(self, message: Message) -> bool:
        return await get_user_role(message.from_user.id, self.bot, self.bot_config) in (
            UserRole.USER,
            UserRole.ADMIN,
        )
