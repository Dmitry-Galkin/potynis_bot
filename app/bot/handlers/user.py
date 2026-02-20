from datetime import UTC
from typing import Any, Tuple

import pandas as pd
from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import default_state
from aiogram.types import Message
from aiogram.utils.markdown import hbold, hitalic

from app.bot.utils import (
    MONTH_NAME_MAPPING,
    WEEKDAY_NAME_MAPPING,
    get_actual_templates,
    get_datetime_now_utc,
)
from app.config import DataBaseSettings
from app.db import table_select

user_router = Router()


def get_query_my_bookings(
    db_config: DataBaseSettings, tg_id: int, now: str
) -> Tuple[str, Tuple[Any, ...]]:
    """Запрос для текущих бронирований пользователя."""
    query = f"""
        SELECT 
            t2.session_datetime AS session_datetime,
            t4.weekday AS weekday,
            t4.time AS time
        FROM 
            {db_config.table_registrations} t1
            LEFT JOIN {db_config.table_sessions} t2 ON (t1.session_id = t2.id)
            LEFT JOIN {db_config.table_users} t3 ON (t1.user_id = t3.id)
            LEFT JOIN {db_config.table_templates} t4 ON (t2.template_id = t4.id)
        WHERE
            t1.is_canceled = False 
            AND t2.is_actual = True
            AND t4.is_actual = True
            AND t3.tg_id = ?
            AND t2.session_datetime >= ?
        ORDER BY
            session_datetime
    """
    parameters = (tg_id, now)
    return query, parameters


def get_query_all_bookings(
    db_config: DataBaseSettings, now: str
) -> Tuple[str, Tuple[Any, ...]]:
    """Запрос для всех текущих бронирований."""
    query = f"""
        SELECT 
            t2.session_datetime AS session_datetime,
            t4.weekday AS weekday,
            t4.time AS time,
            t4.participant_limit AS participant_limit,
            t3.first_name AS first_name,
            t3.last_name AS last_name,
            t3.username AS username
        FROM 
            {db_config.table_registrations} t1
            LEFT JOIN {db_config.table_sessions} t2 ON (t1.session_id = t2.id)
            LEFT JOIN {db_config.table_users} t3 ON (t1.user_id = t3.id)
            LEFT JOIN {db_config.table_templates} t4 ON (t2.template_id = t4.id)
        WHERE
            t1.is_canceled = False 
            AND t2.is_actual = True
            AND t4.is_actual = True
            AND t2.session_datetime >= ?
        ORDER BY
            session_datetime, first_name
    """
    parameters = (now,)
    return query, parameters


# Комманда посмотреть все занятия.
# TODO: добавить фильтр, кто может смотреть
@user_router.message(Command(commands="schedule"), StateFilter(default_state))
async def show_schedule(message: Message, **kwargs):
    templates_df = await get_actual_templates(db_config=kwargs["config"].db)
    templates_df = templates_df.sort_values(
        by=["weekday", "time", "participant_limit"], ascending=True
    )
    if templates_df.empty:
        text = "😔 Пока нет занятий."
    else:
        text = "Расписание занятий\n\n"
        for i, row in templates_df.iterrows():
            text += (
                f"✅ *{WEEKDAY_NAME_MAPPING[row.weekday]}*: {row.time} "
                f"(_макс._ {row.participant_limit} чел)\n"
            )
    await message.answer(text, parse_mode="markdown")


# Пользователь нажал посмотреть все свои бронирования.
@user_router.message(Command(commands="my_bookings"), StateFilter(default_state))
async def show_my_bookings(message: Message, **kwargs):
    now = get_datetime_now_utc()
    config = kwargs["config"]
    query, parameters = get_query_my_bookings(
        db_config=config.db, tg_id=message.from_user.id, now=now
    )
    registrations_df = await table_select(
        db_path=config.db.path, query=query, parameters=parameters
    )
    registrations_df["session_datetime"] = (
        pd.to_datetime(registrations_df["session_datetime"])
        .dt.tz_localize(UTC)
        .dt.tz_convert(config.time.local_timezone)
    )
    if registrations_df.empty:
        text = "😔 Вы пока никуда не записаны."
    else:
        text = "Ваши текущие записи:\n\n"
        for i, row in registrations_df.iterrows():
            month, day = (
                row.session_datetime.date().month,
                row.session_datetime.date().day,
            )
            text += (
                f"🧘‍♂️ *{WEEKDAY_NAME_MAPPING[row.weekday]}*: {row.time}"
                f" ({day} _{MONTH_NAME_MAPPING[month]}_)\n"
            )
    await message.answer(text, parse_mode="markdown")


# Пользователь нажал посмотреть все записи на неделю.
@user_router.message(Command(commands="all_bookings"), StateFilter(default_state))
async def show_all_bookings(message: Message, **kwargs):
    now = get_datetime_now_utc()
    config = kwargs["config"]
    query, parameters = get_query_all_bookings(db_config=config.db, now=now)
    registrations_df = await table_select(
        db_path=config.db.path, query=query, parameters=parameters
    )
    registrations_df["session_datetime"] = (
        pd.to_datetime(registrations_df["session_datetime"])
        .dt.tz_localize(UTC)
        .dt.tz_convert(config.time.local_timezone)
    )
    if registrations_df.empty:
        text = "😔 Никто пока никуда не записан."
    else:
        text = "Текущие записи:\n\n"
        for session_datetime in sorted(registrations_df["session_datetime"].unique()):
            df = registrations_df[
                registrations_df.session_datetime == session_datetime
            ].reset_index(drop=True)
            month, day = (
                session_datetime.date().month,
                session_datetime.date().day,
            )
            weekday = df.at[0, "weekday"]
            time = df.at[0, "time"]
            participant_limit = df.at[0, "participant_limit"]
            text += (
                f"🧘‍♂️ {hbold(WEEKDAY_NAME_MAPPING[weekday])}: {time} "
                f"({day} {hitalic(MONTH_NAME_MAPPING[month])})\n"
            )
            for i, row in df.iterrows():
                text += f"{i + 1}) {row.first_name} {row.last_name} (@{row.username})\n"
            delta = participant_limit - df.shape[0]
            if delta > 0:
                text += hbold(f"Осталось {delta} места 🔥\n")
            else:
                text += f"Полная запись 🔥\n"
            text += "\n"
    await message.answer(text, parse_mode="HTML")
