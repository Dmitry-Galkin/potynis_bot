from collections.abc import Callable

from app.config import DataBaseSettings
from app.db import get_db


async def db_commit(db_path: str, query: str) -> None:
    async with get_db(db_path) as db:
        await db.execute(query)
        await db.commit()


async def init_table(func: Callable, *args, **kwargs) -> None:
    """Создание одной таблицы."""
    query = func(*args)
    await db_commit(db_path=kwargs["db_path"], query=query)


async def init_all_tables(db_config: DataBaseSettings) -> None:
    """Создание всех таблиц."""
    for func, args in [
        # Таблица с общей инфой.
        (query_init_table_info, (db_config.table_info,)),
        # Таблица с шаблонами занятий.
        (query_init_table_templates, (db_config.table_templates,)),
        # Таблица с занятиями.
        (
            query_init_table_sessions,
            (db_config.table_sessions, db_config.table_templates),
        ),
        # Таблица с пользователями.
        (query_init_table_users, (db_config.table_users,)),
        # Таблица с регистрациями на занятия.
        (
            query_init_table_registrations,
            (
                db_config.table_registrations,
                db_config.table_users,
                db_config.table_sessions,
            ),
        ),
        # Таблица с отпусками.
        (
            query_init_table_days_off,
            (db_config.table_days_off,),
        ),
    ]:
        await init_table(func, *args, db_path=db_config.path)


def query_init_table_info(*args) -> str:
    """Запрос для создания таблицы с общей информацией о занятиях."""
    # Общая инфа - адрес, стоимость и пр.
    table = args[0]
    query = f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            info TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """
    return query


def query_init_table_templates(*args) -> str:
    """Запрос для создания таблицы с шаблонами занятий."""
    table = args[0]
    query = f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            weekday INTEGER NOT NULL,
            time TEXT NOT NULL,
            participant_limit INTEGER NOT NULL,
            is_actual BOOLEAN NOT NULL,
            created_at TEXT NOT NULL,
            corrected_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """
    return query


def query_init_table_sessions(*args) -> str:
    """Запрос для создания таблицы с информацией о конкретных занятиях."""
    table, referenced_table_templates = args
    query = f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_datetime TEXT NOT NULL,
            is_actual BOOLEAN NOT NULL,
            template_id INTEGER NOT NULL,
            FOREIGN KEY (template_id) REFERENCES {referenced_table_templates} (id)
        )
    """
    return query


def query_init_table_users(*args) -> str:
    """Запрос для создания таблицы с пользователями."""
    table = args[0]
    query = f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            username TEXT NOT NULL,
            created_at TEXT NOT NULL,
            corrected_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """
    return query


def query_init_table_registrations(*args) -> str:
    """Запрос на создание таблицы с записями на занятия."""
    table, referenced_table_users, referenced_table_sessions = args
    query = f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_id INTEGER NOT NULL,
            is_canceled BOOLEAN NOT NULL,
            created_at TEXT NOT NULL,
            corrected_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES {referenced_table_users} (id),
            FOREIGN KEY (session_id) REFERENCES {referenced_table_sessions} (id)
        )
    """
    return query


def query_init_table_days_off(*args) -> str:
    """Запрос для создания таблицы с датами отсутствия занятий."""
    # На случай отпуска или больничного преподавателя, например.
    table = args[0]
    query = f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_off_start TEXT NOT NULL,
            date_off_end TEXT NOT NULL,
            is_actual BOOLEAN NOT NULL
        )
    """
    return query
