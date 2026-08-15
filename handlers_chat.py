from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter

import db
from keyboards import MAIN_MENU, friend_confirm_kb

router = Router()


@router.message(F.text == "❌ Завершить чат")
async def end_chat_cmd(message: Message, bot: Bot):
    partner_id = db.end_chat(message.from_user.id)
    if not partner_id:
        await message.answer("У тебя сейчас нет активного анонимного чата.", reply_markup=MAIN_MENU)
        return
    await message.answer("Чат завершён.", reply_markup=MAIN_MENU)
    try:
        await bot.send_message(partner_id, "Собеседник завершил анонимный чат.", reply_markup=MAIN_MENU)
    except Exception:
        pass


@router.callback_query(F.data.startswith("addfriend:"))
async def add_friend_request(callback: CallbackQuery, bot: Bot):
    target_id = int(callback.data.split(":")[1])
    from_id = callback.from_user.id
    db.create_friend_request(from_id, target_id)
    await callback.answer("Запрос отправлен!")
    me = db.get_user(from_id)
    try:
        await bot.send_message(
            target_id,
            f"🤝 {me['name']} хочет добавить тебя в друзья и открыть настоящий диалог "
            f"(с обменом Telegram-профилями). Согласен?",
            reply_markup=friend_confirm_kb(from_id),
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("friendyes:"))
async def friend_accept(callback: CallbackQuery, bot: Bot):
    from_id = int(callback.data.split(":")[1])
    to_id = callback.from_user.id
    db.accept_friend_request(from_id, to_id)
    await callback.answer("Принято!")

    me = db.get_user(to_id)
    them = db.get_user(from_id)

    await callback.message.answer(
        f"Готово! Вот профиль {them['name']} в Telegram — можете общаться напрямую:\n"
        f"tg://user?id={from_id}"
    )
    try:
        await bot.send_message(
            from_id,
            f"{me['name']} принял(а) запрос дружбы! Вот профиль в Telegram:\n"
            f"tg://user?id={to_id}",
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("friendno:"))
async def friend_decline(callback: CallbackQuery):
    await callback.answer("Отклонено")
    await callback.message.answer("Запрос дружбы отклонён.")


@router.message(StateFilter(None))
async def relay_message(message: Message, bot: Bot):
    partner_id = db.get_active_chat_partner(message.from_user.id)
    if not partner_id:
        await message.answer(
            "Не понял команду 🙂 Используй кнопки меню ниже.",
            reply_markup=MAIN_MENU,
        )
        return
    try:
        if message.text:
            await bot.send_message(partner_id, message.text)
        elif message.photo:
            await bot.send_photo(partner_id, message.photo[-1].file_id, caption=message.caption or "")
        elif message.video_note:
            await bot.send_video_note(partner_id, message.video_note.file_id)
        elif message.sticker:
            await bot.send_sticker(partner_id, message.sticker.file_id)
        elif message.voice:
            await bot.send_voice(partner_id, message.voice.file_id)
        else:
            await message.answer("Такой тип сообщения пока не поддерживается в анонимном чате.")
    except Exception:
        await message.answer("Не удалось доставить сообщение собеседнику.")
