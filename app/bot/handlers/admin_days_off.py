from datetime import UTC

import pandas as pd
from aiogram import F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.admin import admin_router
from app.bot.handlers.common import check_owner
from app.bot.keyboards.admin import actual_days_off_keyboard
from app.bot.keyboards.common import confirm_keyboard
from app.bot.utils import get_datetime_now_utc, is_date_format_valid
from app.config import Config
from app.db import table_insert, table_select, table_update


async def update_session_status(
    date_off_start: str,
    date_off_end: str,
    to_activate: bool,
    config: Config,
) -> None:
    """Активация/деактивация сессий в таблице sessions."""
    # Переведем даты в UTC, т.к. в базе все в UTC.
    # Дата начала отпуска.
    date_off_start = str(
        pd.to_datetime(f"{date_off_start} 00:00:00")
        .tz_localize(config.time.local_timezone)
        .tz_convert(UTC)
    ).split("+")[0]
    if to_activate:
        # Если, например, отпуск отменяем посередине,
        # то возьмем в качестве левой даты текущую.
        date_off_start = str(
            max(pd.Timestamp(date_off_start), pd.Timestamp(get_datetime_now_utc()))
        )
    # Дата конца отпуска.
    date_off_end = str(
        pd.to_datetime(f"{date_off_end} 23:59:59")
        .tz_localize(config.time.local_timezone)
        .tz_convert(UTC)
    ).split("+")[0]
    # Смотрим, какие есть занятия в этот период.
    query = f"""
        SELECT 
            id
        FROM 
            {config.db.table_sessions}
        WHERE 
            session_datetime BETWEEN ? AND ?
            AND is_actual = ?
    """
    params = (date_off_start, date_off_end, not to_activate)
    session_df = await table_select(
        db_path=config.db.path,
        table=config.db.table_sessions,
        query=query,
        parameters=params,
    )
    if session_df.empty:
        return
    # Обновляем статус.
    for _, row in session_df.iterrows():
        await table_update(
            db_path=config.db.path,
            table=config.db.table_sessions,
            where={"id": int(row["id"])},
            values={"is_actual": to_activate},
        )
    return


class FSMAddDaysOff(StatesGroup):
    """Состояния при добавлении отпуска."""

    # Состояние ввода периода отпуска.
    add_days_off = State()
    # Состояние подтверждения введенных данных.
    confirm_days_off_adding = State()


# Админ нажал кнопку добавить отпуск.
@admin_router.callback_query(F.data == "add_days_off", StateFilter(default_state))
async def start_add_days_off(callback: CallbackQuery, state: FSMContext):
    await state.update_data(owner_id=callback.from_user.id)
    await callback.message.edit_text(
        "⏰ Введите дату или период, на которые хотите добавить отпуск.\n\n"
        "Формат: Год-Месяц-День.\n\n"
        "Например\n"
        "➡️ Для одной даты: \t 2026-01-21\n"
        "➡️ Для периода: \t 2026-01-21  2026-01-24"
    )
    await state.set_state(FSMAddDaysOff.add_days_off)


# Админ ввел дату или период.
@admin_router.message(
    FSMAddDaysOff.add_days_off,
    ~StateFilter(default_state),
    ~Command(commands="cancel"),
)
async def enter_period(message: Message, state: FSMContext, **kwargs):
    if not await check_owner(message, state):
        return
    dates = message.text.strip().split()
    for n, date in enumerate(dates):
        if not is_date_format_valid(date):
            await message.answer(
                f"❌ Неверный формат {n + 1}-й даты. Пример: 2026-01-21"
            )
            return
    if len(dates) == 1:
        dates.append(dates[0])
    if pd.Timestamp(dates[0]) > pd.Timestamp(dates[1]):
        await message.answer(
            f"❌ Неправильный порядок дат. Вторая дата должна быть больше."
        )
        return
    await state.update_data(date_off_start=dates[0])
    await state.update_data(date_off_end=dates[1])
    await message.answer(
        f"📋 Подтвердите отпуск:\n" f"✔️ {dates[0]} — {dates[1]}",
        reply_markup=confirm_keyboard(),
    )
    await state.set_state(FSMAddDaysOff.confirm_days_off_adding)


# Админ подтвердил введенную инфу о планируемом отпуске.
@admin_router.callback_query(
    FSMAddDaysOff.confirm_days_off_adding,
    F.data == "confirm",
    ~StateFilter(default_state),
)
async def confirm_add(callback: CallbackQuery, state: FSMContext, **kwargs):
    if not await check_owner(callback, state):
        return
    data = await state.get_data()
    await table_insert(
        db_path=kwargs["config"].db.path,
        table=kwargs["config"].db.table_days_off,
        values={
            "date_off_start": data["date_off_start"],
            "date_off_end": data["date_off_end"],
            "is_actual": True,
        },
    )
    # Если у нас уже были активированы занятия на эти даты в таблице sessions,
    # то просто сделаем их не активными.
    await update_session_status(
        date_off_start=data["date_off_start"],
        date_off_end=data["date_off_end"],
        to_activate=False,
        config=kwargs["config"],
    )
    await state.clear()
    await callback.message.edit_text("✅ Отпуск успешно добавлен!")


class FSMRemoveDaysOff(StatesGroup):
    """Состояния при удалении отпуска."""

    # Состояние выбора периода отпуска для удаления.
    choose_days_off_for_removing = State()
    # Состояние подтверждения введенных данных.
    confirm_days_off_removing = State()


# Админ нажал кнопку удалить отпуск.
@admin_router.callback_query(F.data == "remove_days_off", StateFilter(default_state))
async def start_remove_days_off(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.update_data(owner_id=callback.from_user.id)
    await callback.message.edit_text(
        "Выберите отпуск для удаления:",
        reply_markup=await actual_days_off_keyboard(config=kwargs["config"]),
    )
    await state.set_state(FSMRemoveDaysOff.choose_days_off_for_removing)


# Админ выбрал отпуск для удаления.
@admin_router.callback_query(
    FSMRemoveDaysOff.choose_days_off_for_removing,
    F.data.startswith("days_off"),
    ~StateFilter(default_state),
)
async def choose_days_off_remove(callback: CallbackQuery, state: FSMContext):
    if not await check_owner(callback, state):
        return
    i = callback.data.index(":") + 1
    date_off_start, date_off_end, days_off_id = callback.data[i:].split("_")
    await state.update_data(days_off_id=int(days_off_id))
    await state.update_data(date_off_start=date_off_start)
    await state.update_data(date_off_end=date_off_end)
    await callback.message.edit_text(
        f"📋 Подтвердите удаление отпуска {date_off_start} — {date_off_end}",
        reply_markup=confirm_keyboard(),
    )
    await state.set_state(FSMRemoveDaysOff.confirm_days_off_removing)


# Админ подтвердил удаление отпуска.
@admin_router.callback_query(
    FSMRemoveDaysOff.confirm_days_off_removing,
    F.data == "confirm",
    ~StateFilter(default_state),
)
async def confirm_remove(callback: CallbackQuery, state: FSMContext, **kwargs):
    if not await check_owner(callback, state):
        return
    data = await state.get_data()
    await table_update(
        db_path=kwargs["config"].db.path,
        table=kwargs["config"].db.table_days_off,
        where={"id": data["days_off_id"]},
        values={"is_actual": False},
    )
    # Если у нас уже были деактивированы занятия на эти даты в таблице sessions,
    # то снова сделаем их активными.
    await update_session_status(
        date_off_start=data["date_off_start"],
        date_off_end=data["date_off_end"],
        to_activate=True,
        config=kwargs["config"],
    )
    await callback.message.edit_text(f"🚮 Отпуск успешно удален!")
    await state.clear()
