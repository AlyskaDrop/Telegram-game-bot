import logging
import json
import aiosqlite
from telegram import Update
from telegram.ext import (
    Application, CallbackQueryHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters, CommandHandler
)

from config import DB_PATH
from database import get_user, get_promo_code, use_promo_code, add_gold, add_to_inventory
from keyboards import back_keyboard

logger = logging.getLogger(__name__)

WAITING_PROMO_CODE = 0


async def handle_promo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text("🎟 Введите промокод:")
        return WAITING_PROMO_CODE
    except Exception as e:
        logger.error(f"Error in handle_promo_start: {e}", exc_info=True)
        return ConversationHandler.END


async def handle_promo_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        code = update.message.text.strip().upper()
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                await update.message.reply_text("Персонаж не найден.")
                return ConversationHandler.END
            promo = await get_promo_code(db, code)
            if not promo:
                await update.message.reply_text(
                    "❌ Промокод не найден.",
                    reply_markup=back_keyboard("main_menu")
                )
                return ConversationHandler.END
            if promo.get("expires_at"):
                from datetime import datetime, timezone
                exp = datetime.fromisoformat(promo["expires_at"].replace("Z", "+00:00"))
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > exp:
                    await update.message.reply_text(
                        "❌ Промокод истёк.",
                        reply_markup=back_keyboard("main_menu")
                    )
                    return ConversationHandler.END
            if promo["used_count"] >= promo["max_uses"]:
                await update.message.reply_text(
                    "❌ Промокод уже использован максимальное количество раз.",
                    reply_markup=back_keyboard("main_menu")
                )
                return ConversationHandler.END
            async with db.execute(
                "SELECT id FROM promo_uses WHERE user_id = ? AND code_id = ?",
                (user["id"], promo["id"])
            ) as cursor:
                already_used = await cursor.fetchone()
            if already_used:
                await update.message.reply_text(
                    "❌ Вы уже использовали этот промокод.",
                    reply_markup=back_keyboard("main_menu")
                )
                return ConversationHandler.END
            try:
                reward = json.loads(promo.get("reward", "{}"))
            except (json.JSONDecodeError, TypeError):
                reward = {}
            await use_promo_code(db, user["id"], promo["id"])
            reward_lines = []
            if "gold" in reward:
                await add_gold(db, user["id"], reward["gold"])
                reward_lines.append(f"💰 Золото: +{reward['gold']}")
            if "premium_currency" in reward:
                await db.execute(
                    "UPDATE users SET premium_currency = premium_currency + ? WHERE id = ?",
                    (reward["premium_currency"], user["id"])
                )
                await db.commit()
                reward_lines.append(f"💎 Кристаллы: +{reward['premium_currency']}")
            if "item_id" in reward:
                qty = reward.get("item_qty", 1)
                await add_to_inventory(db, user["id"], reward["item_id"], qty)
                reward_lines.append(f"🎒 Предмет (ID: {reward['item_id']}) x{qty}")
        rewards_text = "\n".join(reward_lines) if reward_lines else "Нет наград"
        await update.message.reply_text(
            f"✅ Промокод активирован!\n\nНаграды:\n{rewards_text}",
            reply_markup=back_keyboard("main_menu")
        )
    except Exception as e:
        logger.error(f"Error in handle_promo_input: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка при активации промокода.")
    return ConversationHandler.END


async def _cancel_promo_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return ConversationHandler.END


def setup_handlers(app: Application):
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_promo_start, pattern="^promo:start$")],
        states={
            WAITING_PROMO_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_promo_input)],
        },
        fallbacks=[CommandHandler("start", _cancel_promo_conv)],
    )
    app.add_handler(conv_handler)
