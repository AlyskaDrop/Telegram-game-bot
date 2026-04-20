import logging
import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from config import DB_PATH
from database import get_user, get_all_items_of_type, add_gold, add_to_inventory
from keyboards import shop_keyboard, back_keyboard

logger = logging.getLogger(__name__)


async def handle_shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        text = "🛒 Магазин\n\nВыберите тип магазина:"
        await query.edit_message_text(text, reply_markup=shop_keyboard("none"))
    except Exception as e:
        logger.error(f"Error in handle_shop_menu: {e}", exc_info=True)


async def handle_shop_npc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            items = await get_all_items_of_type(db, "npc")
        if not items:
            await query.edit_message_text("🛒 Обычный магазин пуст.", reply_markup=back_keyboard("shop:menu"))
            return
        keyboard = []
        for item in items[:20]:
            keyboard.append([InlineKeyboardButton(
                f"{item['name']} [{item['rarity']}] — {item['price']}💰",
                callback_data=f"shop:buy:npc:{item['id']}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="shop:menu")])
        text = "🛒 Обычный магазин:\nВыберите предмет для покупки:"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in handle_shop_npc: {e}", exc_info=True)


async def handle_shop_donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            items = await get_all_items_of_type(db, "donate")
        if not items:
            await query.edit_message_text("💎 Донат магазин пуст.", reply_markup=back_keyboard("shop:menu"))
            return
        keyboard = []
        for item in items[:20]:
            keyboard.append([InlineKeyboardButton(
                f"{item['name']} [{item['rarity']}] — {item['price']}💎",
                callback_data=f"shop:buy:donate:{item['id']}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="shop:menu")])
        text = "💎 Донат магазин:\nВыберите предмет для покупки:"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in handle_shop_donate: {e}", exc_info=True)


async def handle_shop_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        shop_type = parts[2]
        item_id = int(parts[3])
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                await query.edit_message_text("Персонаж не найден.")
                return
            from database import get_item
            item = await get_item(db, item_id)
            if not item:
                await query.answer("Предмет не найден!", show_alert=True)
                return
            if user["level"] < item["level_req"]:
                await query.answer(f"Требуется уровень {item['level_req']}!", show_alert=True)
                return
            if shop_type == "donate":
                if user["premium_currency"] < item["price"]:
                    await query.answer(f"Недостаточно кристаллов! Нужно {item['price']} 💎.", show_alert=True)
                    return
                await db.execute(
                    "UPDATE users SET premium_currency = premium_currency - ? WHERE id = ?",
                    (item["price"], user["id"])
                )
                await db.commit()
            else:
                if user["gold"] < item["price"]:
                    await query.answer(f"Недостаточно золота! Нужно {item['price']} 💰.", show_alert=True)
                    return
                await add_gold(db, user["id"], -item["price"])
            await add_to_inventory(db, user["id"], item_id, 1)
        currency = "💎" if shop_type == "donate" else "💰"
        await query.edit_message_text(
            f"✅ Вы купили {item['name']} за {item['price']}{currency}!",
            reply_markup=back_keyboard(f"shop:{shop_type}")
        )
    except Exception as e:
        logger.error(f"Error in handle_shop_buy: {e}", exc_info=True)


def setup_handlers(app: Application):
    app.add_handler(CallbackQueryHandler(handle_shop_menu, pattern="^shop:menu$"))
    app.add_handler(CallbackQueryHandler(handle_shop_npc, pattern="^shop:npc$"))
    app.add_handler(CallbackQueryHandler(handle_shop_donate, pattern="^shop:donate$"))
    app.add_handler(CallbackQueryHandler(handle_shop_buy, pattern="^shop:buy:"))
