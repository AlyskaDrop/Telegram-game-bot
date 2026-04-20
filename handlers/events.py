import logging
import json
import aiosqlite
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from config import DB_PATH
from database import get_active_events
from keyboards import events_keyboard, back_keyboard

logger = logging.getLogger(__name__)


async def handle_events_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            events = await get_active_events(db)
        if not events:
            await query.edit_message_text(
                "🎉 Нет активных событий.\n\nСледите за обновлениями!",
                reply_markup=back_keyboard("main_menu")
            )
            return
        await query.edit_message_text(
            "🎉 Активные события:",
            reply_markup=events_keyboard(events)
        )
    except Exception as e:
        logger.error(f"Error in handle_events_list: {e}", exc_info=True)


async def handle_event_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        event_id = int(parts[2])
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM events WHERE id = ?", (event_id,)) as cursor:
                event = await cursor.fetchone()
        if not event:
            await query.edit_message_text("Событие не найдено.", reply_markup=back_keyboard("event:list"))
            return
        event = dict(event)
        try:
            reward = json.loads(event.get("reward", "{}"))
        except (json.JSONDecodeError, TypeError):
            reward = {}
        reward_text = ", ".join(f"{k}: {v}" for k, v in reward.items()) if reward else "Нет наград"
        text = (
            f"🎉 {event['name']}\n\n"
            f"{event.get('description', '')}\n\n"
            f"Награды: {reward_text}\n"
            f"Начало: {event.get('starts_at', '—')}\n"
            f"Конец: {event.get('ends_at', '—')}"
        )
        await query.edit_message_text(text, reply_markup=back_keyboard("event:list"))
    except Exception as e:
        logger.error(f"Error in handle_event_detail: {e}", exc_info=True)


def setup_handlers(app: Application):
    app.add_handler(CallbackQueryHandler(handle_events_list, pattern="^event:list$"))
    app.add_handler(CallbackQueryHandler(handle_event_detail, pattern="^event:detail:"))
