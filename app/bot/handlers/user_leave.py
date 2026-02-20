from aiogram import F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.common import check_owner
from app.bot.handlers.user import user_router
from app.bot.keyboards.common import confirm_keyboard
from app.bot.keyboards.user import booked_sessions_keyboard
from app.bot.utils import WEEKDAY_NAME_MAPPING, get_leave_msg, get_user_info
from app.db import table_select, table_update


class FSMLeaveSession(StatesGroup):
    """Состояния при удалении записи на занятия."""

    # Состояние выбора занятия для отмены.
    choose_session = State()
    # Состояние ожидания подтверждения отмены.
    confirm_leaving = State()


# Пользователь нажал кнопку отменить запись.
@user_router.message(
    Command(commands="leave"),
    StateFilter(default_state),
)
# TODO: добавить фильтр, кто может делать.
async def start_leave_session(message: Message, state: FSMContext, **kwargs):
    await message.answer(
        text="📆 Выберите занятие для отмены записи:",
        reply_markup=await booked_sessions_keyboard(
            db_config=kwargs["config"].db, user_id=message.from_user.id
        ),
    )
    user_info = await get_user_info(
        db_config=kwargs["config"].db, tg_id=message.from_user.id
    )
    await state.update_data(owner_id=message.from_user.id)
    await state.update_data(user_info=user_info)
    await state.set_state(FSMLeaveSession.choose_session)


# Пользователь выбрал занятие.
@user_router.callback_query(
    FSMLeaveSession.choose_session,
    F.data.startswith("booked_session:"),
    ~StateFilter(default_state),
)
async def choose_session(callback: CallbackQuery, state: FSMContext):
    if not await check_owner(callback, state):
        return
    i = callback.data.index(":") + 1
    weekday, time, day, month_name, registration_id = callback.data[i:].split("_")
    await state.update_data(registration_id=int(registration_id))
    await state.update_data(month_name=month_name)
    await state.update_data(day=day)
    await state.update_data(weekday_name=WEEKDAY_NAME_MAPPING[int(weekday)])
    await state.update_data(time=time)
    await callback.message.edit_text(
        "    Подтвердите отмену записи на занятие:\n"
        f"➡️ *{WEEKDAY_NAME_MAPPING[int(weekday)]}* {time} ({day} _{month_name}_)",
        reply_markup=confirm_keyboard(),
        parse_mode="markdown",
    )
    await state.set_state(FSMLeaveSession.confirm_leaving)


# Пользователь подтвердил отмену записи.
@user_router.callback_query(
    FSMLeaveSession.confirm_leaving,
    F.data == "confirm",
    ~StateFilter(default_state),
)
async def confirm_leaving(callback: CallbackQuery, state: FSMContext, **kwargs):
    if not await check_owner(callback, state):
        return
    data = await state.get_data()
    await table_update(
        db_path=kwargs["config"].db.path,
        table=kwargs["config"].db.table_registrations,
        values={"is_canceled": True},
        where={"id": data["registration_id"]},
    )
    await state.clear()
    await callback.message.edit_text("Вы отменили запись на занятие!")
    text_to_chat = f"😢 Отмена записи: {data['day']} {data['month_name']} ({data['weekday_name']}, {data['time']})\n\n"
    text_to_chat += get_leave_msg(username=data["user_info"]["supername"])
    await kwargs["bot"].send_message(
        chat_id=kwargs["config"].bot.group_id,
        text=text_to_chat,
    )
