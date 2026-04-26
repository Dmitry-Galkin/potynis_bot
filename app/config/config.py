from dataclasses import dataclass
from typing import List

import yaml
from environs import Env
from marshmallow_dataclass import class_schema


@dataclass
class BotSettings:
    token: str
    group_id: int
    admin_ids: List[int]


@dataclass()
class DataBaseSettings:
    path: str
    table_info: str
    table_templates: str
    table_sessions: str
    table_users: str
    table_registrations: str
    table_days_off: str


@dataclass
class BookingSettings:
    window_days: int


@dataclass
class TimeSettings:
    local_timezone: str


@dataclass
class Config:
    bot: BotSettings
    db: DataBaseSettings
    booking: BookingSettings
    time: TimeSettings


db_schema = class_schema(DataBaseSettings)()
booking_schema = class_schema(BookingSettings)()
time_schema = class_schema(TimeSettings)()


def load_config(path_env: str, path_yaml: str) -> Config:

    env = Env()
    env.read_env(path_env)
    token = env("BOT_TOKEN")
    group_id = int(env("GROUP_ID"))
    admin_ids = [int(idx) for idx in env.list("ADMIN_IDS", default=[])]

    with open(path_yaml, "r") as input_stream:
        params = yaml.safe_load(input_stream)

    config = Config(
        bot=BotSettings(token=token, group_id=group_id, admin_ids=admin_ids),
        db=db_schema.load(params["db"]),
        booking=booking_schema.load(params["booking"]),
        time=time_schema.load(params["time"]),
    )

    return config
