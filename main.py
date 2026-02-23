import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.filters import IsAdmin, IsAdminOrUser, IsGuest
from app.bot.handlers import admin_router, common_router, guest_router, user_router
from app.bot.interface.interface import setup_commands
from app.bot.middlewares import ConfigMiddleware, LoggingMiddleware
from app.config.config import load_config
from app.db.schema import init_all_tables

# Логирование действий пользователей в терминал: время, id, first_name, last_name, username, команда.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger_actions = logging.getLogger("user_actions")
logger_actions.setLevel(logging.INFO)

config = load_config(path_env=".env", path_yaml="config.yaml")
BOT_TOKEN = config.bot.token
storage = MemoryStorage()

# Создаем объекты бота и диспетчера.
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# Сначала логирование, затем подстановка config/bot.
dp.message.outer_middleware(LoggingMiddleware())
dp.callback_query.outer_middleware(LoggingMiddleware())
config_middleware = ConfigMiddleware(config, bot)
dp.message.outer_middleware(config_middleware)
dp.callback_query.outer_middleware(config_middleware)

# Фильтры доступа: админ — только для admin_router, остальное — IsAdminOrUser, гости — guest_router.
is_admin = IsAdmin(bot, config.bot)
is_admin_or_user = IsAdminOrUser(bot, config.bot)
is_guest = IsGuest(bot, config.bot)
admin_router.message.filter(is_admin)
admin_router.callback_query.filter(is_admin)
common_router.message.filter(is_admin_or_user)
common_router.callback_query.filter(is_admin_or_user)
user_router.message.filter(is_admin_or_user)
user_router.callback_query.filter(is_admin_or_user)
guest_router.message.filter(is_guest)
guest_router.callback_query.filter(is_guest)

dp.include_routers(admin_router, common_router, user_router, guest_router)


async def main():
    await setup_commands(bot, bot_config=config.bot)
    await init_all_tables(db_config=config.db)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
