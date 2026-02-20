from aiogram import F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.admin import admin_router
from app.bot.handlers.common import check_owner
from app.bot.keyboards.admin import weekdays_keyboard
from app.bot.keyboards.common import confirm_keyboard
from app.bot.utils import (
    WEEKDAY_NAME_MAPPING,
    get_datetime_now_utc,
    is_time_format_valid,
)
from app.db import table_insert


class FSMAddTemplate(StatesGroup):
    """Состояния при добавлении шаблона занятия."""

    # Состояние ожидания ввода дня недели.
    choose_weekday = State()
    # Состояние ожидания ввода времени начала занятия.
    enter_time = State()
    # Состояние ожидания ввода максимального количества участников.
    enter_participant_limit = State()
    # Состояние ожидания подтверждения введенной информации.
    confirm_add = State()


# Админ нажал кнопку добавить занятие.
@admin_router.callback_query(F.data == "add_template", StateFilter(default_state))
async def start_add_template(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        text="📆 Выберите день недели:", reply_markup=weekdays_keyboard()
    )
    await state.update_data(owner_id=callback.from_user.id)
    await state.set_state(FSMAddTemplate.choose_weekday)


# Админ выбрал день недели.
@admin_router.callback_query(
    FSMAddTemplate.choose_weekday,
    F.data.startswith("weekday:"),
    ~StateFilter(default_state),
)
async def choose_weekday(callback: CallbackQuery, state: FSMContext):
    if not await check_owner(callback, state):
        return
    weekday = int(callback.data.split(":")[1])
    await state.update_data(weekday=weekday)
    await callback.message.edit_text(
        "⏰ Введите время начала занятия\n" "Формат: ЧЧ:ММ (например 18:30)"
    )
    await state.set_state(FSMAddTemplate.enter_time)


# Админ ввел время начала занятия.
@admin_router.message(
    FSMAddTemplate.enter_time,
    ~StateFilter(default_state),
    ~Command(commands="cancel"),
)
async def enter_time(message: Message, state: FSMContext):
    if not await check_owner(message, state):
        return
    time = message.text.strip()
    if not is_time_format_valid(time):
        await message.answer("❌ Неверный формат. Пример: 18:30")
        return
    await state.update_data(time=time)
    await message.answer("👥 Введите максимальное количество участников:")
    await state.set_state(FSMAddTemplate.enter_participant_limit)


# Админ ввел максимальное количество участников.
@admin_router.message(
    FSMAddTemplate.enter_participant_limit,
    ~StateFilter(default_state),
    ~Command(commands="cancel"),
)
async def enter_participant_limit(message: Message, state: FSMContext):
    if not await check_owner(message, state):
        return
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("❌ Введите положительное число")
        return
    participant_limit = int(message.text)
    await state.update_data(participant_limit=participant_limit)
    data = await state.get_data()
    await message.answer(
        f"📋 Подтвердите занятие:\n"
        f"✔️ День недели: {WEEKDAY_NAME_MAPPING[data['weekday']]}\n"
        f"✔️ Время: {data['time']}\n"
        f"✔️ Количество участников: {data['participant_limit']}\n",
        reply_markup=confirm_keyboard(),
    )
    await state.set_state(FSMAddTemplate.confirm_add)


# Админ подтвердил введенную инфу.
@admin_router.callback_query(
    FSMAddTemplate.confirm_add, F.data == "confirm", ~StateFilter(default_state)
)
async def confirm_add(callback: CallbackQuery, state: FSMContext, **kwargs):
    if not await check_owner(callback, state):
        return
    template_info = await state.get_data()
    await table_insert(
        db_path=kwargs["config"].db.path,
        table=kwargs["config"].db.table_templates,
        values={
            "weekday": template_info["weekday"],
            "time": template_info["time"],
            "participant_limit": template_info["participant_limit"],
            "is_actual": True,
            "created_at": get_datetime_now_utc(),
        },
    )
    await state.clear()
    await callback.message.edit_text("✅ Занятие успешно добавлено!")
