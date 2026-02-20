from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message

common_router = Router()


async def check_owner(update: Message | CallbackQuery, state: FSMContext) -> bool:
    data = await state.get_data()
    return update.from_user.id == data.get("owner_id")


@common_router.callback_query(F.data == "cancel", ~StateFilter(default_state))
async def cancel_from_button(callback: CallbackQuery, state: FSMContext):
    if not await check_owner(callback, state):
        return
    await callback.message.edit_text("❌ Действие отменено.")
    await state.clear()


@common_router.message(Command("cancel"), ~StateFilter(default_state))
async def cancel_from_command(message: Message, state: FSMContext):
    if not await check_owner(message, state):
        return
    await message.answer("❌ Действие отменено.")
    await state.clear()
