from typing import Any, Tuple

import pandas as pd
from aiogram import F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.common import check_owner
from app.bot.handlers.user import user_router
from app.bot.keyboards.common import confirm_keyboard
from app.bot.keyboards.user import available_sessions_keyboard
from app.bot.utils import (
    WEEKDAY_NAME_MAPPING,
    get_actual_templates,
    get_available_sessions,
    get_datetime_now_utc,
    get_join_msg,
)
from app.config import Config, DataBaseSettings
from app.db import table_insert, table_select, table_update


async def register_user_if_new(
    message: Message,
    db_config: DataBaseSettings,
    now: str,
) -> Tuple[int, str]:
    """Занесение инфомарции о новом пользователе."""
    user = {
        "tg_id": message.from_user.id,
        "first_name": message.from_user.first_name,
        "last_name": message.from_user.last_name,
        "username": message.from_user.username,
    }
    # Проверка, если какое-то поле пустое пришло.
    for k, v in user.items():
        if pd.isnull(v):
            user[k] = ""
    # Посмотрим, есть ли такой пользователь в БД.
    user_df = await table_select(
        db_path=db_config.path,
        table=db_config.table_users,
        select=["tg_id", "first_name", "last_name", "username"],
        where={"tg_id": user["tg_id"]},
    )
    # Если пользователь новый, то добавим о нем информацию.
    if user_df.empty:
        await table_insert(
            db_path=db_config.path,
            table=db_config.table_users,
            values={
                "tg_id": user["tg_id"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "username": user["username"],
                "created_at": now,
            },
        )
    # Если пользователь обновил информацию о себе, то обновим ее в БД.
    elif any(user_df[user_df[k] == v].empty for k, v in user.items()):
        await table_update(
            db_path=db_config.path,
            table=db_config.table_users,
            where={"tg_id": user["tg_id"]},
            values={
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "username": user["username"],
                "corrected_at": now,
            },
        )
    # Вернем id записи.
    user_df = await table_select(
        db_path=db_config.path,
        table=db_config.table_users,
        select=["id", "username"],
        where={"tg_id": user["tg_id"]},
    )
    return int(user_df.at[0, "id"]), user_df.at[0, "username"]


def get_query_existed_sessions(
    db_config: DataBaseSettings, now: str
) -> Tuple[str, Tuple[Any, ...]]:
    query = f"""
        SELECT
            t1.id AS id, 
            t1.session_datetime AS session_datetime,
            t1.template_id AS template_id
        FROM
            {db_config.table_sessions} t1
        LEFT JOIN 
            {db_config.table_templates} t2 ON (t1.template_id = t2.id)
        WHERE
            t1.is_actual = TRUE
            AND t2.is_actual = TRUE
            AND session_datetime > ?
    """
    parameters = (now,)
    return query, parameters


def get_query_free_spaces(
    db_config: DataBaseSettings, weekday: int, time: str
) -> Tuple[str, Tuple[Any, ...]]:
    query = f"""
        SELECT
            t3.participant_limit > COUNT(*) AS under_limit
        FROM
            {db_config.table_registrations} t1
        LEFT JOIN
            {db_config.table_sessions} t2 ON t1.session_id = t2.id
        LEFT JOIN 
            {db_config.table_templates} t3 ON t2.template_id = t3.id
        WHERE
            t3.time = ?
            AND t3.weekday = ?
            AND t3.is_actual = True
            AND t2.is_actual = TRUE
            AND t1.is_canceled = False
        GROUP BY
            t3.participant_limit
    """
    parameters = (time, weekday)
    return query, parameters


async def update_sessions_schedule(config: Config, now: str) -> None:
    """Обновим актуальное расписание."""
    # Актуальные занятия.
    templates_df = await get_actual_templates(db_config=config.db)
    # Доступные занятия на заданное количество дней вперед.
    session_df = get_available_sessions(templates_df=templates_df, config=config)
    if session_df.empty:
        return
    # Посмотрим, какие занятия сейчас есть в БД.
    query, parameters = get_query_existed_sessions(db_config=config.db, now=now)
    database_session_df = await table_select(
        db_path=config.db.path,
        query=query,
        parameters=parameters,
    )
    # Соединим 2 таблицы, и там, где нет еще инфы в БД - добавим.
    database_session_df = session_df.merge(
        database_session_df, how="left", on=["session_datetime", "template_id"]
    )
    absent_df = database_session_df[pd.isnull(database_session_df["id"])]
    for i, row in absent_df.iterrows():
        await table_insert(
            db_path=config.db.path,
            table=config.db.table_sessions,
            values={
                "session_datetime": str(row["session_datetime"]).split("+")[0],
                "template_id": row["template_id"],
                "is_actual": True,
            },
        )


class FSMJoinSession(StatesGroup):
    """Состояния при записи на занятия."""

    # Состояние выбора занятия для записи.
    choose_session = State()
    # Состояние ожидания подтверждения записи.
    confirm_booking = State()


# Пользователь нажал кнопку записаться на занятие.
@user_router.message(
    Command(commands="join"),
    StateFilter(default_state),
)
# TODO: добавить фильтр, кто может делать.
async def start_join_session(message: Message, state: FSMContext, **kwargs):
    # Текущее время
    now = get_datetime_now_utc()
    # Добавим или обновим информацию о пользователе, если надо.
    user_id, username = await register_user_if_new(
        message=message, db_config=kwargs["config"].db, now=now
    )
    # Обновим информацию о занятиях в БД, если надо.
    await update_sessions_schedule(config=kwargs["config"], now=now)
    await message.answer(
        text="📆 Выберите занятие для записи:",
        reply_markup=await available_sessions_keyboard(kwargs["config"].db),
    )
    await state.update_data(owner_id=message.from_user.id)
    await state.update_data(user_id=user_id)
    await state.update_data(username=username)
    await state.set_state(FSMJoinSession.choose_session)


# Пользователь выбрал занятие.
@user_router.callback_query(
    FSMJoinSession.choose_session,
    F.data.startswith("available_session:"),
    ~StateFilter(default_state),
)
async def choose_session(callback: CallbackQuery, state: FSMContext, **kwargs):
    if not await check_owner(callback, state):
        return
    i = callback.data.index(":") + 1
    weekday, time, day, month_name, session_id = callback.data[i:].split("_")
    db_config = kwargs["config"].db
    query, parameters = get_query_free_spaces(
        db_config=db_config,
        weekday=int(weekday),
        time=time,
    )
    reg_df = await table_select(
        db_path=db_config.path, query=query, parameters=parameters
    )
    if not reg_df.empty and not reg_df.under_limit.values[0]:
        await callback.message.edit_text("К сожалению, все места на этот день заняты😔")
        await state.clear()
    else:
        weekday_name = WEEKDAY_NAME_MAPPING[int(weekday)]
        await state.update_data(weekday_name=weekday_name)
        await state.update_data(time=time)
        await state.update_data(day=int(day))
        await state.update_data(month_name=month_name)
        await state.update_data(session_id=int(session_id))
        await callback.message.edit_text(
            "    Подтвердите запись на занятие:\n"
            f"➡️ *{weekday_name}* {time} ({day} _{month_name}_)",
            reply_markup=confirm_keyboard(),
            parse_mode="markdown",
        )
        await state.set_state(FSMJoinSession.confirm_booking)


# Пользователь подтвердил занятие.
@user_router.callback_query(
    FSMJoinSession.confirm_booking,
    F.data == "confirm",
    ~StateFilter(default_state),
)
async def confirm_booking(callback: CallbackQuery, state: FSMContext, **kwargs):
    if not await check_owner(callback, state):
        return
    data = await state.get_data()
    await table_insert(
        db_path=kwargs["config"].db.path,
        table=kwargs["config"].db.table_registrations,
        values={
            "user_id": data["user_id"],
            "session_id": data["session_id"],
            "is_canceled": False,
            "created_at": get_datetime_now_utc(),
        },
    )
    await state.clear()
    await callback.message.edit_text("🙂 Вы успешно записались на занятие!")
    text_to_chat = f"🥳 Запись на занятие: {data['day']} {data['month_name']} ({data['weekday_name']}, {data['time']})\n\n"
    text_to_chat += get_join_msg(username=data["username"])
    await kwargs["bot"].send_message(
        chat_id=kwargs["config"].bot.group_id,
        text=text_to_chat,
    )
