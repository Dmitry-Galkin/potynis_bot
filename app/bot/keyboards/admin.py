from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.keyboards.common import cancel_inline_button
from app.bot.utils import get_actual_templates
from app.bot.utils.datetime import WEEKDAY_NAME_MAPPING
from app.config.config import DataBaseSettings
from app.db.repository import table_select


def main_admin_keyboard(width: int = 1) -> InlineKeyboardMarkup:
    """Главная админская панель."""
    button_add_template = InlineKeyboardButton(
        text="Добавить занятие", callback_data="add_template"
    )
    button_remove_template = InlineKeyboardButton(
        text="Удалить занятие", callback_data="remove_template"
    )
    button_update_template = InlineKeyboardButton(
        text="Корректировать занятие", callback_data="edit_template"
    )
    button_view_bookings_by_period = InlineKeyboardButton(
        text="Посмотреть записи на день/период",
        callback_data="view_bookings_by_period",
    )
    buttons = [
        button_add_template,
        button_remove_template,
        button_update_template,
        button_view_bookings_by_period,
    ]
    kb_builder = InlineKeyboardBuilder()
    kb_builder.row(*buttons, width=width)
    return kb_builder.as_markup()


def weekdays_keyboard(width: int = 7) -> InlineKeyboardMarkup:
    """Клавиатура с днями недели."""
    kb_builder = InlineKeyboardBuilder()
    buttons = [
        InlineKeyboardButton(text=name, callback_data=f"weekday:{num}")
        for num, name in WEEKDAY_NAME_MAPPING.items()
    ]
    buttons.append(cancel_inline_button())
    kb_builder.row(*buttons, width=width)
    return kb_builder.as_markup()


async def actual_templates_keyboard(
    db_config: DataBaseSettings, width: int = 2
) -> InlineKeyboardMarkup:
    """Кнопки с актуальными шаблонами занятий."""
    # Актуальные шаблоны занятий из базы.
    templates_df = await get_actual_templates(db_config=db_config)
    templates_df = templates_df.sort_values(by=["weekday", "time", "participant_limit"])
    kb_builder = InlineKeyboardBuilder()
    buttons = [
        InlineKeyboardButton(
            text=f"{WEEKDAY_NAME_MAPPING[row.weekday]}, {row.time}",
            callback_data=f"template:{row.weekday}_{row.time}_{row.participant_limit}_{row['id']}",
        )
        for i, row in templates_df.iterrows()
    ]
    buttons.append(cancel_inline_button())
    kb_builder.row(*buttons, width=width)
    return kb_builder.as_markup()


async def template_items_keyboard(
    db_config: DataBaseSettings,
    template_id: int,
    width: int = 3,
) -> InlineKeyboardMarkup:
    """Кнопки с параметрами конкретного занятия."""
    templates_df = await table_select(
        db_path=db_config.path,
        table=db_config.table_templates,
        select=["weekday", "time", "participant_limit"],
        where={"id": template_id},
    )
    # А может ли придти пустой датафрейм.
    # По идее нет, т.к. мы выбрали до этого существующее занятие из базы.
    row = templates_df.loc[0]
    buttons = [
        InlineKeyboardButton(
            text=f"{WEEKDAY_NAME_MAPPING[row.weekday]}",
            callback_data=f"template_item:weekday",
        ),
        InlineKeyboardButton(
            text=f"{row.time}",
            callback_data=f"template_item:time",
        ),
        InlineKeyboardButton(
            text=f"{row.participant_limit} чел",
            callback_data=f"template_item:participant_limit",
        ),
        cancel_inline_button(),
    ]
    kb_builder = InlineKeyboardBuilder()
    kb_builder.row(*buttons, width=width)
    return kb_builder.as_markup()
