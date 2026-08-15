from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

import db
from cities import CITIES
from keyboards import MAIN_MENU, MODE_CHOICE, EDIT_MENU, CANCEL

router = Router()

MODE_LABELS = {
    "BR": "Королевская битва (BR)",
    "CS": "Битва отрядов (CS)",
}


class ProfileForm(StatesGroup):
    name = State()
    city = State()
    mode = State()
    avatar = State()


class EditForm(StatesGroup):
    waiting_value = State()


def _profile_caption(u: dict) -> str:
    mode = MODE_LABELS.get(u["mode"], u["mode"])
    return (
        f"👤 <b>{u['name']}</b>\n"
        f"📍 Город: {u['city']}\n"
        f"🎮 Режим: {mode}"
    )


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    db.upsert_user(message.from_user.id, message.from_user.username)
    if db.is_profile_complete(message.from_user.id):
        await message.answer(
            "С возвращением! 👋 Выбирай, что делать дальше.",
            reply_markup=MAIN_MENU,
        )
        return
    await state.set_state(ProfileForm.name)
    await message.answer(
        "Привет! Это бот для поиска тиммейтов по Free Fire 🔥\n\n"
        "Для начала заполним анкету. Как тебя зовут (или ник)?",
        reply_markup=CANCEL,
    )


@router.message(StateFilter(ProfileForm.name, EditForm.waiting_value), F.text == "⬅️ Отмена")
async def cancel_any(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=MAIN_MENU)


@router.message(ProfileForm.name)
async def form_name(message: Message, state: FSMContext):
    name = message.text.strip()[:40]
    db.set_field(message.from_user.id, "name", name)
    await state.set_state(ProfileForm.city)
    cities_hint = ", ".join(list(CITIES.keys())[:8]) + "…"
    await message.answer(
        f"Отлично, {name}! Теперь напиши свой город (например, Москва).\n"
        f"Примеры городов из базы: {cities_hint}\n"
        f"Если твоего города нет в списке — просто напиши его, это тоже сработает.",
    )


@router.message(ProfileForm.city)
async def form_city(message: Message, state: FSMContext):
    city = message.text.strip().title()
    db.set_field(message.from_user.id, "city", city)
    await state.set_state(ProfileForm.mode)
    await message.answer("Какой режим любишь больше?", reply_markup=MODE_CHOICE)


@router.message(ProfileForm.mode)
async def form_mode(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    mode = "BR" if "король" in text or "br" in text else "CS"
    db.set_field(message.from_user.id, "mode", mode)
    await state.set_state(ProfileForm.avatar)
    await message.answer(
        "Последний шаг: пришли фото для анкеты — можно обычное фото, "
        "можно кружочек (видео-заметку).",
        reply_markup=CANCEL,
    )


@router.message(ProfileForm.avatar, F.photo)
async def form_avatar_photo(message: Message, state: FSMContext):
    db.set_field(message.from_user.id, "avatar_file_id", message.photo[-1].file_id)
    db.set_field(message.from_user.id, "avatar_type", "photo")
    await _finish_profile(message, state)


@router.message(ProfileForm.avatar, F.video_note)
async def form_avatar_video_note(message: Message, state: FSMContext):
    db.set_field(message.from_user.id, "avatar_file_id", message.video_note.file_id)
    db.set_field(message.from_user.id, "avatar_type", "video_note")
    await _finish_profile(message, state)


@router.message(ProfileForm.avatar)
async def form_avatar_wrong(message: Message):
    await message.answer("Пришли, пожалуйста, именно фото или кружочек (видео-заметку) 🙂")


async def _finish_profile(message: Message, state: FSMContext):
    db.set_field(message.from_user.id, "profile_complete", 1)
    await state.clear()
    u = db.get_user(message.from_user.id)
    await message.answer("Анкета готова! Вот как она выглядит:")
    await _send_profile_preview(message, u)
    await message.answer("Погнали искать тиммейтов 👇", reply_markup=MAIN_MENU)


async def _send_profile_preview(message: Message, u: dict):
    caption = _profile_caption(u)
    if u["avatar_type"] == "video_note":
        await message.answer_video_note(u["avatar_file_id"])
        await message.answer(caption, parse_mode="HTML")
    else:
        await message.answer_photo(u["avatar_file_id"], caption=caption, parse_mode="HTML")


@router.message(F.text == "👤 Моя анкета")
async def show_my_profile(message: Message):
    u = db.get_user(message.from_user.id)
    if not u or not u["profile_complete"]:
        await message.answer("У тебя ещё нет анкеты. Напиши /start, чтобы создать.")
        return
    await _send_profile_preview(message, u)


@router.message(F.text == "✏️ Редактировать анкету")
async def edit_menu(message: Message):
    await message.answer("Что хочешь изменить?", reply_markup=EDIT_MENU)


EDIT_FIELD_PROMPTS = {
    "Изменить имя": ("name", "Напиши новое имя:"),
    "Изменить город": ("city", "Напиши новый город:"),
    "Изменить режим": ("mode", "Напиши режим: BR (королевская битва) или CS (битва отрядов):"),
    "Изменить аватар": ("avatar", "Пришли новое фото или кружочек:"),
}


@router.message(F.text.in_(EDIT_FIELD_PROMPTS.keys()))
async def edit_field_start(message: Message, state: FSMContext):
    field, prompt = EDIT_FIELD_PROMPTS[message.text]
    await state.update_data(edit_field=field)
    await state.set_state(EditForm.waiting_value)
    await message.answer(prompt, reply_markup=CANCEL)


@router.message(F.text == "⬅️ Назад в меню")
async def back_to_menu(message: Message):
    await message.answer("Главное меню:", reply_markup=MAIN_MENU)


@router.message(EditForm.waiting_value, F.photo)
async def edit_avatar_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("edit_field") != "avatar":
        return
    db.set_field(message.from_user.id, "avatar_file_id", message.photo[-1].file_id)
    db.set_field(message.from_user.id, "avatar_type", "photo")
    await state.clear()
    await message.answer("Аватар обновлён ✅", reply_markup=MAIN_MENU)


@router.message(EditForm.waiting_value, F.video_note)
async def edit_avatar_video(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("edit_field") != "avatar":
        return
    db.set_field(message.from_user.id, "avatar_file_id", message.video_note.file_id)
    db.set_field(message.from_user.id, "avatar_type", "video_note")
    await state.clear()
    await message.answer("Аватар обновлён ✅", reply_markup=MAIN_MENU)


@router.message(EditForm.waiting_value)
async def edit_field_value(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data.get("edit_field")
    if field == "avatar":
        await message.answer("Пришли, пожалуйста, фото или кружочек 🙂")
        return
    value = message.text.strip()
    if field == "city":
        value = value.title()
    if field == "mode":
        low = value.lower()
        value = "BR" if "br" in low or "король" in low else "CS"
    else:
        value = value[:40]
    db.set_field(message.from_user.id, field, value)
    await state.clear()
    await message.answer("Готово, анкета обновлена ✅", reply_markup=MAIN_MENU)
