from contextlib import suppress

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.keyboards.admin import main_admin_keyboard

admin_router = Router()


@admin_router.message(Command(commands="admin"))
async def process_start_command(message: Message):
    await message.answer(
        text="Выберите, что вы хотите сделать", reply_markup=main_admin_keyboard()
    )


@admin_router.message(Command(commands="get_chat_id"))
async def process_get_chat_id_command(message: Message, **kwargs):
    """Узнать id группы."""
    print(f"---> chat_id: {message.chat.id}")
    await delete_message(kwargs["bot"], message.chat.id, message.message_id)


async def delete_message(bot, chat_id: int, message_id: int):
    with suppress(Exception):
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
