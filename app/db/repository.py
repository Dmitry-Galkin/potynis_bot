from typing import Any, Dict, List, Tuple

import pandas as pd

from app.db import get_db


def create_dataframe(rows, cursor) -> pd.DataFrame:
    columns = [col[0] for col in cursor.description]
    df = pd.DataFrame(rows, columns=columns)
    return df


async def execute_query(
    db_path: str,
    query: str,
    parameters: Tuple[Any, ...] | None = None,
) -> None:
    async with get_db(db_path) as db:
        if parameters:
            await db.execute(query, parameters)
        else:
            await db.execute(query)
        await db.commit()


async def fetch_dataframe(
    db_path: str,
    query: str,
    parameters: Tuple[Any, ...] | None = None,
) -> pd.DataFrame:
    df = pd.DataFrame()
    async with get_db(db_path) as db:
        if parameters:
            cursor = await db.execute(query, parameters)
        else:
            cursor = await db.execute(query)
        rows = await cursor.fetchall()
        df = create_dataframe(rows, cursor)
    return df


async def table_insert(
    db_path: str,
    table: str,
    values: Dict[str, Any],
) -> None:
    """Добавление информации в таблицу."""
    _keys = ", ".join(values.keys())
    _placeholders = ", ".join("?" * len(values))
    query = f"""
        INSERT INTO {table} ({_keys}) VALUES ({_placeholders})
    """
    parameters = tuple(values.values())
    await execute_query(db_path, query, parameters)


async def table_update(
    db_path: str,
    table: str,
    where: Dict[str, Any] | str,
    values: Dict[str, Any],
) -> None:
    """Обновление информации в таблице."""
    _set = ", ".join(f"{k} = ?" for k in values.keys())
    if isinstance(where, dict):
        _where = " AND ".join(f"{k} = ?" for k in where.keys())
        parameters = tuple(values.values()) + tuple(where.values())
    else:
        _where = where
        parameters = tuple(values.values())
    query = f"""
        UPDATE 
            {table}
        SET 
            {_set}
        WHERE
            {_where}
    """
    await execute_query(db_path, query, parameters)


async def table_select(
    db_path: str,
    table: str | None = None,
    select: List[str] | None = None,
    where: Dict[str, Any] | str | None = None,
    query: str | None = None,
    parameters: Tuple[Any, ...] | None = None,
) -> pd.DataFrame:
    """Считывание информации из таблицы."""
    if query is None:
        _select = ", ".join(select)
        if isinstance(where, dict):
            _where = " AND ".join(f"{k} = ?" for k in where.keys())
            parameters = tuple(where.values())
        elif where is not None:
            _where = where
            parameters = parameters
        else:
            # Если вдруг передали только select без where.
            _where = "1 = 1"
            parameters = None
        query = f"""
            SELECT
                {_select}
            FROM 
                {table}
            WHERE
                {_where}
        """
    df = await fetch_dataframe(db_path, query, parameters)
    return df
