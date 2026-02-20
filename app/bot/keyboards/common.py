from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def cancel_inline_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")


def confirm_keyboard(width: int = 2) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    buttons = [
        InlineKeyboardButton(text="✔️ Подтверждаю", callback_data="confirm"),
        cancel_inline_button(),
    ]
    kb_builder.row(*buttons, width=width)
    return kb_builder.as_markup()
