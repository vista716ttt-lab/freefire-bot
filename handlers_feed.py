from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery

import db
from cities import distance_km
from keyboards import swipe_kb, restart_kb, chat_kb, MAIN_MENU

router = Router()

MODE_LABELS = {"BR": "Королевская битва (BR)", "CS": "Битва отрядов (CS)"}


def _profile_caption(u: dict) -> str:
    mode = MODE_LABELS.get(u["mode"], u["mode"])
    return f"👤 <b>{u['name']}</b>\n📍 Город: {u['city']}\n🎮 Режим: {mode}"


def _sorted_candidates(viewer_city: str, candidates: list[dict]) -> list[dict]:
    return sorted(candidates, key=lambda c: distance_km(viewer_city, c["city"]))


async def _send_candidate(message: Message, candidate: dict):
    caption = _profile_caption(candidate)
    kb = swipe_kb(candidate["user_id"])
    if candidate["avatar_type"] == "video_note":
        await message.answer_video_note(candidate["avatar_file_id"])
        await message.answer(caption, parse_mode="HTML", reply_markup=kb)
    else:
        await message.answer_photo(candidate["avatar_file_id"], caption=caption,
                                    parse_mode="HTML", reply_markup=kb)


@router.message(F.text == "🎮 Смотреть анкеты")
async def show_feed(message: Message):
    u = db.get_user(message.from_user.id)
    if not u or not u["profile_complete"]:
        await message.answer("Сначала заполни анкету: /start")
        return
    candidates = db.get_candidates(message.from_user.id)
    if not candidates:
        await message.answer(
            "Анкеты закончились 😔 Новые люди появляются постоянно — загляни попозже, "
            "или начни заново, чтобы пересмотреть тех, кого пропускал.",
            reply_markup=restart_kb(),
        )
        return
    ordered = _sorted_candidates(u["city"], candidates)
    await _send_candidate(message, ordered[0])


@router.message(F.text == "💌 Мне симпатизируют")
async def show_likers(message: Message):
    u = db.get_user(message.from_user.id)
    if not u or not u["profile_complete"]:
        await message.answer("Сначала заполни анкету: /start")
        return
    likers = db.get_likers(message.from_user.id)
    if not likers:
        await message.answer("Пока никто не лайкнул твою анкету. Смотри анкеты сам — и тебя увидят чаще!")
        return
    ordered = _sorted_candidates(u["city"], likers)
    await message.answer(f"Тебе симпатизируют {len(ordered)} человек. Вот первый:")
    await _send_candidate(message, ordered[0])


@router.callback_query(F.data == "restart_feed")
async def restart_feed(callback: CallbackQuery):
    db.reset_swipes(callback.from_user.id)
    await callback.answer("Анкеты обновлены!")
    await callback.message.answer("Список сброшен, смотрим заново 🔄")
    u = db.get_user(callback.from_user.id)
    candidates = db.get_candidates(callback.from_user.id)
    if candidates:
        ordered = _sorted_candidates(u["city"], candidates)
        await _send_candidate(callback.message, ordered[0])
    else:
        await callback.message.answer("Анкет пока нет вообще — приходи попозже 🙂")


@router.callback_query(F.data.startswith("swipe:"))
async def handle_swipe(callback: CallbackQuery, bot: Bot):
    _, action, target_str = callback.data.split(":")
    target_id = int(target_str)
    from_id = callback.from_user.id

    db.record_swipe(from_id, target_id, action)
    await callback.answer("❤️ Лайк!" if action == "like" else "👎 Пропущено")

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    if action == "like" and db.has_mutual_like(from_id, target_id):
        db.set_active_chat(from_id, target_id)
        me = db.get_user(from_id)
        them = db.get_user(target_id)
        await callback.message.answer(
            f"🎉 Взаимная симпатия с {them['name']}! Открыт анонимный чат — "
            f"просто пиши сообщения сюда, я передам их собеседнику. "
            f"Свою личность вы не увидите, пока сами не решите добавить друг друга.",
            reply_markup=chat_kb(target_id),
        )
        try:
            await bot.send_message(
                target_id,
                f"🎉 Взаимная симпатия с {me['name']}! Открыт анонимный чат — "
                f"просто пиши сообщения сюда, я передам их собеседнику.",
                reply_markup=chat_kb(from_id),
            )
        except Exception:
            pass
    elif action == "like":
        try:
            await bot.send_message(target_id, "💌 У тебя новая симпатия! Загляни в «Мне симпатизируют».")
        except Exception:
            pass

    u = db.get_user(from_id)
    candidates = db.get_candidates(from_id)
    if candidates:
        ordered = _sorted_candidates(u["city"], candidates)
        await _send_candidate(callback.message, ordered[0])
    else:
        await callback.message.answer(
            "Анкеты закончились 😔 Начать заново?",
            reply_markup=restart_kb(),
      )
