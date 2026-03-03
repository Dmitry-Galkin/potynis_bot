from datetime import UTC

import pandas as pd

from app.bot.utils import get_datetime_now_utc
from app.config import Config, DataBaseSettings
from app.db import table_select


async def get_actual_templates(
    db_config: DataBaseSettings,
) -> pd.DataFrame:
    """Актуальные занятия."""
    templates_df = await table_select(
        db_path=db_config.path,
        table=db_config.table_templates,
        select=["id", "weekday", "time", "participant_limit"],
        where={"is_actual": True},
    )
    return templates_df


def get_available_sessions(
    templates_df: pd.DataFrame,
    config: Config,
) -> pd.DataFrame:
    """Доступные для записи занятия."""
    # Текущее время.
    now = pd.to_datetime(get_datetime_now_utc()).tz_localize(UTC)
    # Сформируем датафрейм с датами на заданное число дней вперед.
    # Запись идет на текущую и следующую недели.
    current_weekday = now.tz_convert(config.time.local_timezone).weekday()
    periods = config.booking.window_days - current_weekday
    session_df = pd.DataFrame(
        {"dt": pd.date_range(start=now, periods=periods)}
    )
    # Сконвертируем timezone.
    session_df["dt"] = session_df["dt"].dt.tz_convert(config.time.local_timezone)
    # День недели.
    session_df["weekday"] = session_df["dt"].dt.weekday
    # Временные рамки.
    start_time = session_df["dt"].min()
    end_time = session_df["dt"].max()
    # Смерджим с шаблонами занятий.
    session_df = session_df.merge(templates_df, how="left", on="weekday").sort_values(
        by=["dt"]
    )
    # Преобразуем время начала занятий к datetime и проставим корректно дату и timezone.
    session_df["session_datetime"] = pd.to_datetime(
        start_time.strftime("%Y-%m-%d") + " " + session_df["time"]
    )
    days = 0
    for i in range(1, session_df.shape[0]):
        if session_df.at[i, "weekday"] != session_df.at[i - 1, "weekday"]:
            days += 1
        session_df.at[i, "session_datetime"] += pd.Timedelta(days=days)
    session_df["session_datetime"] = session_df["session_datetime"].dt.tz_localize(
        config.time.local_timezone
    )
    # Отфильтруем по времени занятия.
    session_df = (
        session_df.loc[
            (session_df["session_datetime"] >= start_time)
            & (session_df["session_datetime"] <= end_time),
            ["id", "session_datetime"],
        ]
        .reset_index(drop=True)
        .rename(columns={"id": "template_id"})
    )
    # Переведем время начала занятий в UTC.
    session_df["session_datetime"] = (
        session_df["session_datetime"]
        .dt.tz_convert(UTC)
        .astype(str)
        .str.split("+")
        .str[0]
    )
    return session_df
