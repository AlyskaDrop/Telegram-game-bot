import logging
import json
import aiosqlite
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters
)

from config import DB_PATH, ADMIN_IDS
from database import get_user, add_gold, add_to_inventory
from keyboards import admin_keyboard, back_keyboard

logger = logging.getLogger(__name__)

(
    ADMIN_GIVE_GOLD_USER, ADMIN_GIVE_GOLD_AMOUNT,
    ADMIN_GIVE_ITEM_USER, ADMIN_GIVE_ITEM_ITEM,
    ADMIN_BAN_USER, ADMIN_UNBAN_USER,
    ADMIN_EVENT_NAME, ADMIN_EVENT_DESC, ADMIN_EVENT_REWARD, ADMIN_EVENT_DATES,
    ADMIN_PROMO_CODE, ADMIN_PROMO_REWARD, ADMIN_PROMO_USES
) = range(13)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Доступ запрещён.")
        return
    await update.message.reply_text("⚙️ Панель администратора:", reply_markup=admin_keyboard())


async def handle_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        await query.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    action = query.data.split(":")[1]
    if action == "give_gold":
        await query.edit_message_text("Введите Telegram ID пользователя для выдачи золота:")
        return ADMIN_GIVE_GOLD_USER
    elif action == "give_item":
        await query.edit_message_text("Введите Telegram ID пользователя для выдачи предмета:")
        return ADMIN_GIVE_ITEM_USER
    elif action == "ban":
        await query.edit_message_text("Введите Telegram ID пользователя для бана:")
        return ADMIN_BAN_USER
    elif action == "unban":
        await query.edit_message_text("Введите Telegram ID пользователя для разбана:")
        return ADMIN_UNBAN_USER
    elif action == "event":
        await query.edit_message_text("Введите название события:")
        return ADMIN_EVENT_NAME
    elif action == "promo":
        await query.edit_message_text("Введите код промокода:")
        return ADMIN_PROMO_CODE
    return ConversationHandler.END


async def admin_give_gold_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tg_id = int(update.message.text.strip())
        context.user_data["admin_target_tg_id"] = tg_id
        await update.message.reply_text(f"Введите количество золота для пользователя {tg_id}:")
        return ADMIN_GIVE_GOLD_AMOUNT
    except ValueError:
        await update.message.reply_text("Некорректный ID. Введите числовой Telegram ID:")
        return ADMIN_GIVE_GOLD_USER


async def admin_give_gold_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = int(update.message.text.strip())
        tg_id = context.user_data.get("admin_target_tg_id")
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, tg_id)
            if not user:
                await update.message.reply_text("Пользователь не найден.")
                return ConversationHandler.END
            await add_gold(db, user["id"], amount)
        await update.message.reply_text(f"✅ Выдано {amount} золота пользователю {tg_id}.", reply_markup=back_keyboard("main_menu"))
    except ValueError:
        await update.message.reply_text("Некорректное количество золота.")
        return ADMIN_GIVE_GOLD_AMOUNT
    except Exception as e:
        logger.error(f"admin_give_gold_amount error: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка.")
    return ConversationHandler.END


async def admin_give_item_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tg_id = int(update.message.text.strip())
        context.user_data["admin_target_tg_id"] = tg_id
        await update.message.reply_text(f"Введите ID предмета для пользователя {tg_id}:")
        return ADMIN_GIVE_ITEM_ITEM
    except ValueError:
        await update.message.reply_text("Некорректный ID. Введите числовой Telegram ID:")
        return ADMIN_GIVE_ITEM_USER


async def admin_give_item_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        item_id = int(update.message.text.strip())
        tg_id = context.user_data.get("admin_target_tg_id")
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, tg_id)
            if not user:
                await update.message.reply_text("Пользователь не найден.")
                return ConversationHandler.END
            from database import get_item
            item = await get_item(db, item_id)
            if not item:
                await update.message.reply_text("Предмет не найден.")
                return ConversationHandler.END
            await add_to_inventory(db, user["id"], item_id, 1)
        await update.message.reply_text(f"✅ Предмет (ID: {item_id}) выдан пользователю {tg_id}.", reply_markup=back_keyboard("main_menu"))
    except ValueError:
        await update.message.reply_text("Некорректный ID предмета.")
        return ADMIN_GIVE_ITEM_ITEM
    except Exception as e:
        logger.error(f"admin_give_item_item error: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка.")
    return ConversationHandler.END


async def admin_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tg_id = int(update.message.text.strip())
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, tg_id)
            if not user:
                await update.message.reply_text("Пользователь не найден.")
                return ConversationHandler.END
            await db.execute("UPDATE users SET is_banned = 1 WHERE telegram_id = ?", (tg_id,))
            await db.commit()
        await update.message.reply_text(f"✅ Пользователь {tg_id} забанен.", reply_markup=back_keyboard("main_menu"))
    except ValueError:
        await update.message.reply_text("Некорректный ID.")
        return ADMIN_BAN_USER
    except Exception as e:
        logger.error(f"admin_ban_user error: {e}", exc_info=True)
    return ConversationHandler.END


async def admin_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tg_id = int(update.message.text.strip())
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("UPDATE users SET is_banned = 0 WHERE telegram_id = ?", (tg_id,))
            await db.commit()
        await update.message.reply_text(f"✅ Пользователь {tg_id} разбанен.", reply_markup=back_keyboard("main_menu"))
    except ValueError:
        await update.message.reply_text("Некорректный ID.")
        return ADMIN_UNBAN_USER
    except Exception as e:
        logger.error(f"admin_unban_user error: {e}", exc_info=True)
    return ConversationHandler.END


async def admin_event_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["admin_event_name"] = update.message.text.strip()
    await update.message.reply_text("Введите описание события:")
    return ADMIN_EVENT_DESC


async def admin_event_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["admin_event_desc"] = update.message.text.strip()
    await update.message.reply_text("Введите награду в формате JSON (например: {\"gold\": 100}):")
    return ADMIN_EVENT_REWARD


async def admin_event_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        reward = json.loads(update.message.text.strip())
        context.user_data["admin_event_reward"] = json.dumps(reward)
        await update.message.reply_text("Введите даты события в формате 'ГГГГ-ММ-ДД ГГГГ-ММ-ДД' (начало конец):")
        return ADMIN_EVENT_DATES
    except json.JSONDecodeError:
        await update.message.reply_text("Некорректный JSON. Попробуйте снова:")
        return ADMIN_EVENT_REWARD


async def admin_event_dates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parts = update.message.text.strip().split()
        if len(parts) < 2:
            await update.message.reply_text("Введите две даты через пробел:")
            return ADMIN_EVENT_DATES
        starts_at = parts[0]
        ends_at = parts[1]
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO events (name, description, reward, starts_at, ends_at) VALUES (?, ?, ?, ?, ?)",
                (
                    context.user_data.get("admin_event_name", "Событие"),
                    context.user_data.get("admin_event_desc", ""),
                    context.user_data.get("admin_event_reward", "{}"),
                    starts_at,
                    ends_at,
                )
            )
            await db.commit()
        await update.message.reply_text("✅ Событие создано!", reply_markup=back_keyboard("main_menu"))
    except Exception as e:
        logger.error(f"admin_event_dates error: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка при создании события.")
    return ConversationHandler.END


async def admin_promo_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["admin_promo_code"] = update.message.text.strip().upper()
    await update.message.reply_text("Введите награду в формате JSON (например: {\"gold\": 500}):")
    return ADMIN_PROMO_REWARD


async def admin_promo_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        reward = json.loads(update.message.text.strip())
        context.user_data["admin_promo_reward"] = json.dumps(reward)
        await update.message.reply_text("Введите максимальное количество использований:")
        return ADMIN_PROMO_USES
    except json.JSONDecodeError:
        await update.message.reply_text("Некорректный JSON. Попробуйте снова:")
        return ADMIN_PROMO_REWARD


async def admin_promo_uses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        max_uses = int(update.message.text.strip())
        code = context.user_data.get("admin_promo_code", "CODE")
        reward = context.user_data.get("admin_promo_reward", "{}")
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO promo_codes (code, reward, max_uses) VALUES (?, ?, ?)",
                (code, reward, max_uses)
            )
            await db.commit()
        await update.message.reply_text(f"✅ Промокод «{code}» создан!", reply_markup=back_keyboard("main_menu"))
    except ValueError:
        await update.message.reply_text("Введите корректное число:")
        return ADMIN_PROMO_USES
    except Exception as e:
        logger.error(f"admin_promo_uses error: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка.")
    return ConversationHandler.END


def setup_handlers(app: Application):
    admin_filter = filters.User(user_id=ADMIN_IDS)

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_admin_menu, pattern="^admin:")],
        states={
            ADMIN_GIVE_GOLD_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, admin_give_gold_user)],
            ADMIN_GIVE_GOLD_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, admin_give_gold_amount)],
            ADMIN_GIVE_ITEM_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, admin_give_item_user)],
            ADMIN_GIVE_ITEM_ITEM: [MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, admin_give_item_item)],
            ADMIN_BAN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, admin_ban_user)],
            ADMIN_UNBAN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, admin_unban_user)],
            ADMIN_EVENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, admin_event_name)],
            ADMIN_EVENT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, admin_event_desc)],
            ADMIN_EVENT_REWARD: [MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, admin_event_reward)],
            ADMIN_EVENT_DATES: [MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, admin_event_dates)],
            ADMIN_PROMO_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, admin_promo_code)],
            ADMIN_PROMO_REWARD: [MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, admin_promo_reward)],
            ADMIN_PROMO_USES: [MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, admin_promo_uses)],
        },
        fallbacks=[CommandHandler("start", lambda u, c: ConversationHandler.END)],
    )
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(conv_handler)
