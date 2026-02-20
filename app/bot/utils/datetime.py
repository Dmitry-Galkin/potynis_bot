import re
from datetime import UTC, datetime

TIME_RE = re.compile(r"^(2[0-3]|[01]\d):[0-5]\d$")
DATE_RE = re.compile(r"\d\d\d\d-[01]\d-[0-3]\d")


WEEKDAY_NAME_MAPPING = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Вс",
}


MONTH_NAME_MAPPING = {
    1: "янв",
    2: "февр",
    3: "марта",
    4: "апр",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "авг",
    9: "сент",
    10: "окт",
    11: "нояб",
    12: "дек",
}


def get_datetime_now_utc() -> str:
    """Текущее время в UTC."""
    return str(datetime.now(UTC).replace(microsecond=0)).split("+")[0]


def is_time_format_valid(time: str) -> bool:
    return bool(TIME_RE.match(time))


def is_date_format_valid(date: str) -> bool:
    return bool(DATE_RE.match(date))
