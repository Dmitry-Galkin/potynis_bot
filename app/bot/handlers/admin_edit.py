from aiogram import F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.admin import admin_router
from app.bot.handlers.common import check_owner
from app.bot.keyboards.admin import (
    actual_templates_keyboard,
    template_items_keyboard,
    weekdays_keyboard,
)
from app.bot.keyboards.common import confirm_keyboard
from app.bot.utils import (
    WEEKDAY_NAME_MAPPING,
    get_datetime_now_utc,
    is_time_format_valid,
)
from app.db import table_update


class FSMEditTemplate(StatesGroup):
    """Состояния при корректировке занятия."""

    # Состояние выбора занятия для корректировки.
    choose_template = State()
    # Состояние выбора, что корректировать в занятии.
    choose_template_item = State()
    # Состояние ожидания ввода новой информации.
    enter_edit_info = State()
    # Состояние ожидания подтверждения корректировки занятия.
    confirm_edit = State()


# Админ нажал кнопку редактировать занятие.
@admin_router.callback_query(F.data == "edit_template", StateFilter(default_state))
async def start_update_template(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.update_data(owner_id=callback.from_user.id)
    await callback.message.edit_text(
        text="📆 Выберите занятие для редактирования:",
        reply_markup=await actual_templates_keyboard(db_config=kwargs["config"].db),
    )
    await state.set_state(FSMEditTemplate.choose_template)


# Админ выбрал занятие для корректировки.
@admin_router.callback_query(
    FSMEditTemplate.choose_template,
    F.data.startswith("template"),
    ~StateFilter(default_state),
)
async def choose_template_item(callback: CallbackQuery, state: FSMContext, **kwargs):
    if not await check_owner(callback, state):
        return
    i = callback.data.index(":") + 1
    weekday, time, participant_limit, template_id = callback.data[i:].split("_")
    template_id = int(template_id)
    await state.update_data(old_weekday=int(weekday))
    await state.update_data(old_time=time)
    await state.update_data(old_participant_limit=int(participant_limit))
    await state.update_data(template_id=template_id)
    await callback.message.edit_text(
        f"🔄 Что будем редактировать:",
        reply_markup=await template_items_keyboard(
            db_config=kwargs["config"].db, template_id=template_id
        ),
    )
    await state.set_state(FSMEditTemplate.choose_template_item)


# Админ выбрал, что корректировать в занятии.
@admin_router.callback_query(
    FSMEditTemplate.choose_template_item,
    F.data.startswith("template_item"),
    ~StateFilter(default_state),
)
async def enter_update_info(callback: CallbackQuery, state: FSMContext):
    if not await check_owner(callback, state):
        return
    template_item = callback.data.split(":")[-1]
    await state.update_data(template_item=template_item)
    if template_item == "weekday":
        await callback.message.edit_text(
            text="📆 Выберите новый день недели:", reply_markup=weekdays_keyboard()
        )
    elif template_item == "time":
        await callback.message.edit_text(
            text="⏰ Введите новое время начала занятия\n"
            "Формат: ЧЧ:ММ (например 18:30)"
        )
    elif template_item == "participant_limit":
        await callback.message.edit_text(
            text="👥 Введите новое максимальное количество участников:"
        )
    else:
        raise NotImplementedError(f"Unknown template item to update {template_item}")
    await state.set_state(FSMEditTemplate.enter_edit_info)


# Админ актуализировал день недели.
@admin_router.callback_query(
    FSMEditTemplate.enter_edit_info,
    F.data.startswith("weekday"),
    ~StateFilter(default_state),
)
async def choose_new_weekday(callback: CallbackQuery, state: FSMContext):
    if not await check_owner(callback, state):
        return
    data = await state.get_data()
    weekday = int(callback.data.split(":")[1])
    await state.update_data(new_weekday=weekday)
    await state.update_data(new_time=data["old_time"])
    await state.update_data(new_participant_limit=data["old_participant_limit"])
    edit_info = await state.get_data()
    text = "🛠 Подтвердите редактирование:\n"
    text += (
        f"*Было*:  {WEEKDAY_NAME_MAPPING[edit_info['old_weekday']]}: {edit_info['old_time']}, "
        f"_макс._ {edit_info['old_participant_limit']} чел\n"
    )
    text += (
        f"*Стало*: {WEEKDAY_NAME_MAPPING[edit_info['new_weekday']]}: {edit_info['old_time']}, "
        f"_макс._ {edit_info['old_participant_limit']} чел\n"
    )
    await callback.message.edit_text(
        text=text, parse_mode="markdown", reply_markup=confirm_keyboard()
    )
    await state.set_state(FSMEditTemplate.confirm_edit)


# Админ актуализировал не день недели.
@admin_router.message(
    FSMEditTemplate.enter_edit_info,
    ~StateFilter(default_state),
    ~Command(commands="cancel"),
)
async def choose_new_time_or_participant_limit(message: Message, state: FSMContext):
    if not await check_owner(message, state):
        return

    data = await state.get_data()

    if data["template_item"] == "participant_limit":
        if not message.text.isdigit() or int(message.text) <= 0:
            await message.answer("❌ Введите положительное число")
            return
        await state.update_data(new_weekday=data["old_weekday"])
        await state.update_data(new_time=data["old_time"])
        await state.update_data(new_participant_limit=int(message.text))
    elif data["template_item"] == "time":
        time = message.text.strip()
        if not is_time_format_valid(time):
            await message.answer("❌ Неверный формат. Пример: 18:30")
            return
        await state.update_data(new_weekday=data["old_weekday"])
        await state.update_data(new_time=message.text)
        await state.update_data(new_participant_limit=data["old_participant_limit"])
    else:
        raise NotImplementedError(
            f"Unknown template item to update {data['template_item']}"
        )

    text = "🛠 Подтвердите редактирование:\n"
    text += (
        f"*Было*:  {WEEKDAY_NAME_MAPPING[data['old_weekday']]}: {data['old_time']}, "
        f"_макс._ {data['old_participant_limit']} чел\n"
    )

    data = await state.get_data()

    text += (
        f"*Стало*: {WEEKDAY_NAME_MAPPING[data['new_weekday']]}: {data['new_time']}, "
        f"_макс._ {data['new_participant_limit']} чел\n"
    )

    await message.answer(
        text=text, parse_mode="markdown", reply_markup=confirm_keyboard()
    )
    await state.set_state(FSMEditTemplate.confirm_edit)


# Админ подтвердил введенную инфу.
@admin_router.callback_query(
    FSMEditTemplate.confirm_edit, F.data == "confirm", ~StateFilter(default_state)
)
async def confirm_add(callback: CallbackQuery, state: FSMContext, **kwargs):
    if not await check_owner(callback, state):
        return
    data = await state.get_data()
    await table_update(
        db_path=kwargs["config"].db.path,
        table=kwargs["config"].db.table_templates,
        where={"id": data["template_id"]},
        values={
            "weekday": data["new_weekday"],
            "time": data["new_time"],
            "participant_limit": data["new_participant_limit"],
            "corrected_at": get_datetime_now_utc(),
        },
    )
    await state.clear()
    await callback.message.edit_text("✅ Занятие успешно отредактировано!")
