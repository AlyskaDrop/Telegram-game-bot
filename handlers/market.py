import logging
import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CallbackQueryHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters, CommandHandler
)

from config import DB_PATH
from database import (
    get_user, get_market_listings, create_market_listing, remove_market_listing,
    get_inventory, add_gold, remove_from_inventory, add_to_inventory
)
from keyboards import market_keyboard, back_keyboard

logger = logging.getLogger(__name__)

WAITING_ITEM_SELECT = 0
WAITING_PRICE = 1


async def handle_market_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        page = int(parts[2]) if len(parts) > 2 else 0
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            listings, total = await get_market_listings(db, page=page, per_page=10)
        total_pages = max(1, (total + 9) // 10)
        if not listings:
            text = "📦 Рынок пуст.\n\nВыставьте свои предметы на продажу!"
        else:
            lines = [f"📦 Рынок (стр. {page + 1}/{total_pages}):\n"]
            for l in listings:
                lines.append(f"• {l['item_name']} [{l['rarity']}] — {l['price']} золота (от {l['seller_name']})")
            text = "\n".join(lines)
        keyboard = []
        for listing in listings:
            keyboard.append([InlineKeyboardButton(
                f"Купить: {listing['item_name']} за {listing['price']}💰",
                callback_data=f"market:buy:{listing['id']}"
            )])
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("◀️ Назад", callback_data=f"market:list:{page - 1}"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("Вперёд ▶️", callback_data=f"market:list:{page + 1}"))
        if nav:
            keyboard.append(nav)
        keyboard.append([InlineKeyboardButton("➕ Выставить предмет", callback_data="market:create")])
        keyboard.append([InlineKeyboardButton("📦 Мои лоты", callback_data="market:mine")])
        keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in handle_market_list: {e}", exc_info=True)


async def handle_market_mine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                await query.edit_message_text("Персонаж не найден.")
                return
            async with db.execute(
                """SELECT ml.*, i.name as item_name FROM market_listings ml
                   JOIN items i ON ml.item_id = i.id
                   WHERE ml.seller_id = ?""",
                (user["id"],)
            ) as cursor:
                my_listings = [dict(r) for r in await cursor.fetchall()]
        if not my_listings:
            await query.edit_message_text("У вас нет активных лотов.", reply_markup=back_keyboard("market:list:0"))
            return
        keyboard = []
        for l in my_listings:
            keyboard.append([InlineKeyboardButton(
                f"❌ Снять: {l['item_name']} за {l['price']}💰",
                callback_data=f"market:remove:{l['id']}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="market:list:0")])
        await query.edit_message_text("📦 Ваши лоты:", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in handle_market_mine: {e}", exc_info=True)


async def handle_market_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                await query.edit_message_text("Персонаж не найден.")
                return ConversationHandler.END
            items, total = await get_inventory(db, user["id"], page=0, per_page=20)
        if not items:
            await query.edit_message_text("У вас нет предметов для продажи.", reply_markup=back_keyboard("market:list:0"))
            return ConversationHandler.END
        context.user_data["market_items"] = items
        keyboard = []
        for item in items:
            keyboard.append([InlineKeyboardButton(
                f"{item['name']} x{item['quantity']}",
                callback_data=f"market:select:{item['inv_id']}"
            )])
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="market:list:0")])
        await query.edit_message_text("Выберите предмет для продажи:", reply_markup=InlineKeyboardMarkup(keyboard))
        return WAITING_ITEM_SELECT
    except Exception as e:
        logger.error(f"Error in handle_market_create_start: {e}", exc_info=True)
        return ConversationHandler.END


async def handle_market_item_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        inv_id = int(parts[2])
        context.user_data["market_inv_id"] = inv_id
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT inv.*, i.name, i.id as item_id FROM inventory inv JOIN items i ON inv.item_id = i.id WHERE inv.id = ?",
                (inv_id,)
            ) as cursor:
                inv = await cursor.fetchone()
        if not inv:
            await query.edit_message_text("Предмет не найден.")
            return ConversationHandler.END
        inv = dict(inv)
        context.user_data["market_item_id"] = inv["item_id"]
        await query.edit_message_text(
            f"Предмет: {inv['name']}\n\nВведите цену (в золоте):"
        )
        return WAITING_PRICE
    except Exception as e:
        logger.error(f"Error in handle_market_item_selected: {e}", exc_info=True)
        return ConversationHandler.END


async def handle_market_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price_text = update.message.text.strip()
        if not price_text.isdigit() or int(price_text) <= 0:
            await update.message.reply_text("Введите корректную цену (целое число больше 0):")
            return WAITING_PRICE
        price = int(price_text)
        inv_id = context.user_data.get("market_inv_id")
        item_id = context.user_data.get("market_item_id")
        if not inv_id or not item_id:
            await update.message.reply_text("Ошибка: предмет не выбран.")
            return ConversationHandler.END
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                await update.message.reply_text("Персонаж не найден.")
                return ConversationHandler.END
            async with db.execute(
                "SELECT * FROM inventory WHERE id = ? AND user_id = ?",
                (inv_id, user["id"])
            ) as cursor:
                inv = await cursor.fetchone()
            if not inv:
                await update.message.reply_text("Предмет не найден в инвентаре.")
                return ConversationHandler.END
            await create_market_listing(db, user["id"], inv_id, item_id, price)
            await remove_from_inventory(db, inv_id, 1)
        await update.message.reply_text(
            f"✅ Предмет выставлен на рынок за {price} золота!",
            reply_markup=back_keyboard("market:list:0")
        )
    except Exception as e:
        logger.error(f"Error in handle_market_price_input: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка.")
    return ConversationHandler.END


async def handle_market_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        action = parts[1]
        if action == "buy":
            listing_id = int(parts[2])
            telegram_id = update.effective_user.id
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                user = await get_user(db, telegram_id)
                if not user:
                    await query.edit_message_text("Персонаж не найден.")
                    return
                async with db.execute(
                    "SELECT ml.*, i.name as item_name FROM market_listings ml JOIN items i ON ml.item_id = i.id WHERE ml.id = ?",
                    (listing_id,)
                ) as cursor:
                    listing = await cursor.fetchone()
                if not listing:
                    await query.answer("Лот не найден!", show_alert=True)
                    return
                listing = dict(listing)
                if listing["seller_id"] == user["id"]:
                    await query.answer("Нельзя купить свой лот!", show_alert=True)
                    return
                if user["gold"] < listing["price"]:
                    await query.answer(f"Недостаточно золота! Нужно {listing['price']}.", show_alert=True)
                    return
                await add_gold(db, user["id"], -listing["price"])
                await add_gold(db, listing["seller_id"], listing["price"])
                await add_to_inventory(db, user["id"], listing["item_id"], 1)
                await remove_market_listing(db, listing_id)
            await query.edit_message_text(
                f"✅ Вы купили {listing['item_name']} за {listing['price']} золота!",
                reply_markup=back_keyboard("market:list:0")
            )
        elif action == "remove":
            listing_id = int(parts[2])
            telegram_id = update.effective_user.id
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                user = await get_user(db, telegram_id)
                if not user:
                    await query.edit_message_text("Персонаж не найден.")
                    return
                async with db.execute(
                    "SELECT * FROM market_listings WHERE id = ? AND seller_id = ?",
                    (listing_id, user["id"])
                ) as cursor:
                    listing = await cursor.fetchone()
                if not listing:
                    await query.answer("Лот не найден!", show_alert=True)
                    return
                listing = dict(listing)
                await add_to_inventory(db, user["id"], listing["item_id"], 1)
                await remove_market_listing(db, listing_id)
            await query.edit_message_text("✅ Лот снят с продажи, предмет возвращён.", reply_markup=back_keyboard("market:list:0"))
    except Exception as e:
        logger.error(f"Error in handle_market_buy: {e}", exc_info=True)


def setup_handlers(app: Application):
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_market_create_start, pattern="^market:create$")],
        states={
            WAITING_ITEM_SELECT: [CallbackQueryHandler(handle_market_item_selected, pattern="^market:select:")],
            WAITING_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_market_price_input)],
        },
        fallbacks=[CommandHandler("start", lambda u, c: ConversationHandler.END)],
    )
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(handle_market_list, pattern="^market:list:"))
    app.add_handler(CallbackQueryHandler(handle_market_mine, pattern="^market:mine$"))
    app.add_handler(CallbackQueryHandler(handle_market_buy, pattern="^market:(buy|remove):"))
