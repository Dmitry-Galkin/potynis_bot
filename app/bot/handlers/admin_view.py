from datetime import UTC
from typing import Any, Tuple

import pandas as pd
from aiogram import F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.admin import admin_router
from app.bot.handlers.common import check_owner
from app.bot.utils import is_date_format_valid
from app.config import Config, DataBaseSettings
from app.db import table_select


class FSMViewBookingsByDayTemplate(StatesGroup):
    """Состояния при добавлении шаблона занятия."""

    # Состояние ожидания ввода дня недели.
    choose_date = State()


def get_query_bookings_by_day(config: Config, date: str) -> Tuple[str, Tuple[Any, ...]]:
    db_config = config.db
    """Запрос для скачивания, кто был записан на занятия на опредленную дату."""
    query = f"""
        SELECT
            t2.first_name, t2.last_name, t2.username, t3.session_datetime
        FROM
            {db_config.table_registrations} t1
        LEFT JOIN 
            {db_config.table_users} t2 ON (t1.user_id = t2.id)
        LEFT JOIN 
            {db_config.table_sessions} t3 ON (t1.session_id = t3.id)
        WHERE
            t1.is_canceled = False
            AND t3.is_actual = True
            AND t3.session_datetime BETWEEN ? AND ?
        ORDER BY
            t3.session_datetime, t2.username
    """
    datetime_start = (
        pd.Timestamp(f"{date} 00:00:00")
        .tz_localize(config.time.local_timezone)
        .tz_convert(UTC)
    )
    datetime_end = (
        pd.Timestamp(f"{date} 23:59:59")
        .tz_localize(config.time.local_timezone)
        .tz_convert(UTC)
    )
    parameters = (
        str(datetime_start).split("+")[0],
        str(datetime_end).split("+")[0],
    )
    return query, parameters


# Админ нажал кнопку посмотреть записи на определенный день.
@admin_router.callback_query(
    F.data == "view_bookings_by_day", StateFilter(default_state)
)
async def start_add_template(callback: CallbackQuery, state: FSMContext):
    await state.update_data(owner_id=callback.from_user.id)
    await callback.message.edit_text(
        "⏰ Введите дату, на которую хотите посмотреть записи\n"
        "Формат: Год-Месяц-День (например 2026-01-21)"
    )
    await state.set_state(FSMViewBookingsByDayTemplate.choose_date)


# Админ ввел дату.
@admin_router.message(
    FSMViewBookingsByDayTemplate.choose_date,
    ~StateFilter(default_state),
    ~Command(commands="cancel"),
)
async def enter_time(message: Message, state: FSMContext, **kwargs):
    if not await check_owner(message, state):
        return
    date = message.text.strip()
    if not is_date_format_valid(date):
        await message.answer("❌ Неверный формат. Пример: 2026-01-21")
        return
    config = kwargs["config"]
    query, parameters = get_query_bookings_by_day(config=config, date=date)
    bookings_df = await table_select(
        db_path=config.db.path,
        query=query,
        parameters=parameters,
    )
    if bookings_df.empty:
        await message.answer(f"На этот день записей не было.")
    else:
        text = ""
        # Преобразуем время к локальному.
        bookings_df["session_datetime"] = (
            pd.to_datetime(bookings_df["session_datetime"])
            .dt.tz_localize(UTC)
            .dt.tz_convert(config.time.local_timezone)
        )
        for dt in sorted(bookings_df.session_datetime.unique()):
            text += f"🕓 {dt.date()} {dt.time()}\n"
            i = 0
            for _, row in bookings_df[bookings_df.session_datetime == dt].iterrows():
                i += 1
                text += f"{i}) {row.first_name} {row.last_name} (@{row.username})\n"
            text += "\n"
        await message.answer(text)
    await state.clear()
