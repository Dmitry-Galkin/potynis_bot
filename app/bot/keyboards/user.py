from typing import Any, Tuple

import pandas as pd
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.keyboards.common import cancel_inline_button
from app.bot.utils import MONTH_NAME_MAPPING, WEEKDAY_NAME_MAPPING, get_datetime_now_utc
from app.config import DataBaseSettings
from app.db import table_select


def get_query_available_sessions(
    db_config: DataBaseSettings,
) -> Tuple[str, Tuple[Any, ...]]:
    """Запрос для получения занятий, доступных для записи."""
    now = get_datetime_now_utc()
    query = f"""
        SELECT 
            t1.id AS id, 
            session_datetime,
            weekday,
            time
        FROM 
            {db_config.table_sessions} t1
            LEFT JOIN {db_config.table_templates} t2 ON (t1.template_id = t2.id)
        WHERE
            t1.is_actual = True 
            AND t2.is_actual = True
            AND t1.session_datetime >= ?
        ORDER BY
            session_datetime
    """
    parameters = (now,)
    return query, parameters


def get_query_booked_sessions(
    db_config: DataBaseSettings, tg_id: int
) -> Tuple[str, Tuple[Any, ...]]:
    now = get_datetime_now_utc()
    query = f"""
        SELECT 
            t1.id AS id, 
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
            AND t4.is_actual = True
            AND t2.is_actual = True
            AND t3.tg_id = ?
            AND t2.session_datetime >= ?
    """
    parameters = (tg_id, now)
    return query, parameters


async def available_sessions_keyboard(
    db_config: DataBaseSettings, width: int = 2
) -> InlineKeyboardMarkup:
    """Кнопки с возможными занятиями для записи."""
    query, parameters = get_query_available_sessions(db_config)
    following_session_df = await table_select(
        db_path=db_config.path,
        query=query,
        parameters=parameters,
    )
    following_session_df["session_datetime"] = pd.to_datetime(
        following_session_df["session_datetime"]
    )
    kb_builder = InlineKeyboardBuilder()
    buttons = []
    for i, row in following_session_df.iterrows():
        month, day = row.session_datetime.date().month, row.session_datetime.date().day
        text = f"{WEEKDAY_NAME_MAPPING[row.weekday]}, {row.time} ({day} {MONTH_NAME_MAPPING[month]})"
        callback_data = (
            f"available_session:"
            f"{row.weekday}"
            f"_{row.time}"
            f"_{day}"
            f"_{MONTH_NAME_MAPPING[month]}"
            f"_{row['id']}"
        )
        buttons.append(
            InlineKeyboardButton(
                text=text,
                callback_data=callback_data,
            )
        )
    buttons.append(cancel_inline_button())
    kb_builder.row(*buttons, width=width)
    return kb_builder.as_markup()


async def booked_sessions_keyboard(
    db_config: DataBaseSettings, user_id: int, width: int = 2
) -> InlineKeyboardMarkup:
    """Кнопки с занятиями, на которые есть запись у пользователя."""
    query, parameters = get_query_booked_sessions(db_config, user_id)
    booked_session_df = await table_select(
        db_path=db_config.path,
        query=query,
        parameters=parameters,
    )
    booked_session_df["session_datetime"] = pd.to_datetime(
        booked_session_df["session_datetime"]
    )
    kb_builder = InlineKeyboardBuilder()
    buttons = []
    for i, row in booked_session_df.iterrows():
        month, day = row.session_datetime.date().month, row.session_datetime.date().day
        text = f"{WEEKDAY_NAME_MAPPING[row.weekday]}, {row.time} ({day} {MONTH_NAME_MAPPING[month]})"
        callback_data = (
            f"booked_session:"
            f"{row.weekday}"
            f"_{row.time}"
            f"_{day}"
            f"_{MONTH_NAME_MAPPING[month]}"
            f"_{row['id']}"
        )
        buttons.append(
            InlineKeyboardButton(
                text=text,
                callback_data=callback_data,
            )
        )
    buttons.append(cancel_inline_button())
    kb_builder.row(*buttons, width=width)
    return kb_builder.as_markup()
