from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.types import CallbackQuery

from app.bot.handlers.admin import admin_router
from app.bot.handlers.common import check_owner
from app.bot.keyboards.admin import actual_templates_keyboard
from app.bot.keyboards.common import confirm_keyboard
from app.bot.utils import WEEKDAY_NAME_MAPPING, get_datetime_now_utc
from app.db import table_update


class FSMRemoveTemplate(StatesGroup):
    """Состояния при удалении занятия."""

    # Состояние выбора занятия для удаления.
    choose_template = State()
    # Состояние ожидания подтверждения удаления занятия.
    confirm_remove = State()


# Админ нажал кнопку удалить занятие.
@admin_router.callback_query(F.data == "remove_template", StateFilter(default_state))
async def start_remove_template(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.update_data(owner_id=callback.from_user.id)
    await state.set_state(FSMRemoveTemplate.choose_template)
    await callback.message.edit_text(
        text="📆 Выберите занятие, которое хотите удалить:",
        reply_markup=await actual_templates_keyboard(db_config=kwargs["config"].db),
    )


# Админ выбрал занятие для удаления.
@admin_router.callback_query(
    FSMRemoveTemplate.choose_template,
    F.data.startswith("template"),
    ~StateFilter(default_state),
)
async def choose_template_remove(callback: CallbackQuery, state: FSMContext):
    if not await check_owner(callback, state):
        return
    i = callback.data.index(":") + 1
    weekday, time, _, template_id = callback.data[i:].split("_")
    weekday = int(weekday)
    await state.update_data(template_id=int(template_id))
    await callback.message.edit_text(
        f"📋 Подтвердите удаление занятия {WEEKDAY_NAME_MAPPING[weekday]}, {time}:",
        reply_markup=confirm_keyboard(),
    )
    await state.set_state(FSMRemoveTemplate.confirm_remove)


# Админ подтвердил удаление.
@admin_router.callback_query(
    FSMRemoveTemplate.confirm_remove, F.data == "confirm", ~StateFilter(default_state)
)
async def confirm_remove(callback: CallbackQuery, state: FSMContext, **kwargs):
    if not await check_owner(callback, state):
        return
    remove_info = await state.get_data()
    await table_update(
        db_path=kwargs["config"].db.path,
        table=kwargs["config"].db.table_templates,
        where={"id": remove_info["template_id"]},
        values={
            "corrected_at": get_datetime_now_utc(),
            "is_actual": False,
        },
    )
    await callback.message.edit_text(f"🚮 Занятие успешно удалено!")
    await state.clear()
