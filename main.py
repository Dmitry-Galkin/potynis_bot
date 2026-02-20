import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import admin_router, common_router, user_router
from app.bot.interface.interface import setup_commands
from app.bot.middlewares import ConfigMiddleware
from app.config.config import load_config
from app.db.schema import init_all_tables

config = load_config(path_env=".env.dev", path_yaml="config.yaml")
BOT_TOKEN = config.bot.token
storage = MemoryStorage()

# Создаем объекты бота и диспетчера.
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# Подставляем config и bot в обработчики через middleware.
config_middleware = ConfigMiddleware(config, bot)
dp.message.outer_middleware(config_middleware)
dp.callback_query.outer_middleware(config_middleware)

dp.include_routers(admin_router, common_router, user_router)


async def main():
    await setup_commands(bot, bot_config=config.bot)
    await init_all_tables(db_config=config.db)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
