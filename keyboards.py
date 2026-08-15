from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎮 Смотреть анкеты")],
        [KeyboardButton(text="💌 Мне симпатизируют")],
        [KeyboardButton(text="👤 Моя анкета"), KeyboardButton(text="✏️ Редактировать анкету")],
        [KeyboardButton(text="❌ Завершить чат")],
    ],
    resize_keyboard=True,
)

MODE_CHOICE = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Королевская битва (BR)")],
        [KeyboardButton(text="Битва отрядов (CS)")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

EDIT_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Изменить имя")],
        [KeyboardButton(text="Изменить город")],
        [KeyboardButton(text="Изменить режим")],
        [KeyboardButton(text="Изменить аватар")],
        [KeyboardButton(text="⬅️ Назад в меню")],
    ],
    resize_keyboard=True,
)

CANCEL = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="⬅️ Отмена")]],
    resize_keyboard=True,
)


def swipe_kb(target_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👎", callback_data=f"swipe:dislike:{target_id}"),
        InlineKeyboardButton(text="❤️", callback_data=f"swipe:like:{target_id}"),
    ]])


def restart_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔄 Начать заново", callback_data="restart_feed"),
    ]])


def chat_kb(partner_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🤝 Добавить в друзья", callback_data=f"addfriend:{partner_id}"),
    ]])


def friend_confirm_kb(from_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Принять", callback_data=f"friendyes:{from_id}"),
        InlineKeyboardButton(text="🚫 Отклонить", callback_data=f"friendno:{from_id}"),
    ]])
