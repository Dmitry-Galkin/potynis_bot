from typing import Any, Dict

from app.config import DataBaseSettings
from app.db import table_select


async def get_user_info(db_config: DataBaseSettings, tg_id: int) -> Dict[str, Any]:
    """Данные о пользователе."""
    user_df = await table_select(
        db_path=db_config.path,
        table=db_config.table_users,
        select=["id", "tg_id", "first_name", "last_name", "username"],
        where={"tg_id": tg_id},
    )
    user_info = {}
    if not user_df.empty:
        user_info["tg_id"] = user_df.at[0, "tg_id"]
        user_info["first_name"] = user_df.at[0, "first_name"]
        user_info["last_name"] = user_df.at[0, "last_name"]
        user_info["username"] = user_df.at[0, "username"]
        if user_info["username"]:
            user_info["supername"] = f"@{user_info['username']}"
        elif user_info["first_name"] or user_info["last_name"]:
            user_info["supername"] = (
                user_info["first_name"] + " " + user_info["last_name"]
            )
        else:
            user_info["supername"] = "Unknown"
    return user_info
