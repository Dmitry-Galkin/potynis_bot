from contextlib import asynccontextmanager

import aiosqlite


@asynccontextmanager
async def get_db(db_path: str):
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        yield db
