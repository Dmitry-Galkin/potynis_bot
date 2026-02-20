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
