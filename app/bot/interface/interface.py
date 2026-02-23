from aiogram import Bot
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    BotCommandScopeChatMember,
    BotCommandScopeDefault,
)

from app.config import BotSettings

USER_COMMANDS = [
    BotCommand(command="/join", description="Записаться на занятие"),
    BotCommand(command="/leave", description="Отменить запись"),
    BotCommand(command="/schedule", description="Расписание занятий"),
    BotCommand(command="/my_bookings", description="Посмотреть мои записи"),
    BotCommand(command="/all_bookings", description="Посмотреть общую запись"),
    BotCommand(command="/help", description="Помощь"),
    BotCommand(command="/cancel", description="Отмена"),
]

ADMIN_COMMANDS = (
    USER_COMMANDS[:-2]
    + [BotCommand(command="/admin", description="Админская панель")]
    + USER_COMMANDS[-2:]
)


async def setup_commands(bot: Bot, bot_config: BotSettings) -> None:
    # Все пользователи (личка + группа).
    await bot.set_my_commands(USER_COMMANDS, scope=BotCommandScopeDefault())

    # Админы.
    for admin_id in bot_config.admin_ids:

        # Личный чат с ботом.
        await bot.set_my_commands(
            ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=admin_id)
        )

        # Общая группа.
        await bot.set_my_commands(
            ADMIN_COMMANDS,
            scope=BotCommandScopeChatMember(
                chat_id=bot_config.group_id, user_id=admin_id
            ),
        )
