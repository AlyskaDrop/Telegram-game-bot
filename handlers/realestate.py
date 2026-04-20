import logging
import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from config import DB_PATH
from database import get_user, get_user_real_estate, add_gold
from keyboards import real_estate_keyboard, back_keyboard

logger = logging.getLogger(__name__)

PROPERTY_TYPES = {
    "small_house": {
        "name": "🏠 Маленький дом",
        "description": "+5% к доходу с золота",
        "cost": 500,
        "gold_bonus_pct": 5,
        "exp_bonus_pct": 0,
        "stat_bonus_pct": 0,
    },
    "manor": {
        "name": "🏡 Усадьба",
        "description": "+10% к доходу с золота, +5% опыта",
        "cost": 2000,
        "gold_bonus_pct": 10,
        "exp_bonus_pct": 5,
        "stat_bonus_pct": 0,
    },
    "castle": {
        "name": "🏰 Замок",
        "description": "+20% к доходу с золота, +10% опыта, +5% ко всем характеристикам",
        "cost": 10000,
        "gold_bonus_pct": 20,
        "exp_bonus_pct": 10,
        "stat_bonus_pct": 5,
    },
}


async def handle_realestate_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            properties = await get_user_real_estate(db, user["id"])
        text = "🏠 Недвижимость\n\nВаша недвижимость:"
        await query.edit_message_text(text, reply_markup=real_estate_keyboard(properties))
    except Exception as e:
        logger.error(f"Error in handle_realestate_menu: {e}", exc_info=True)


async def handle_realestate_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        property_type = parts[2]
        pt = PROPERTY_TYPES.get(property_type)
        if not pt:
            await query.answer("Неизвестный тип недвижимости!", show_alert=True)
            return
        text = (
            f"{pt['name']}\n"
            f"Описание: {pt['description']}\n"
            f"Стоимость: {pt['cost']} золота"
        )
        await query.edit_message_text(text, reply_markup=back_keyboard("re:menu"))
    except Exception as e:
        logger.error(f"Error in handle_realestate_detail: {e}", exc_info=True)


async def handle_realestate_buy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        property_type = parts[2]
        pt = PROPERTY_TYPES.get(property_type)
        if not pt:
            await query.answer("Неизвестный тип недвижимости!", show_alert=True)
            return
        keyboard = [
            [InlineKeyboardButton(f"✅ Купить за {pt['cost']} золота", callback_data=f"re:confirm_buy:{property_type}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="re:menu")],
        ]
        text = (
            f"{pt['name']}\n"
            f"Описание: {pt['description']}\n"
            f"Цена: {pt['cost']} золота"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in handle_realestate_buy_menu: {e}", exc_info=True)


async def handle_realestate_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        property_type = parts[2]
        pt = PROPERTY_TYPES.get(property_type)
        if not pt:
            await query.answer("Неизвестный тип недвижимости!", show_alert=True)
            return
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                await query.edit_message_text("Персонаж не найден.")
                return
            async with db.execute(
                "SELECT id FROM real_estate WHERE user_id = ? AND property_type = ?",
                (user["id"], property_type)
            ) as cursor:
                existing = await cursor.fetchone()
            if existing:
                await query.answer("Вы уже владеете этой недвижимостью!", show_alert=True)
                return
            if user["gold"] < pt["cost"]:
                await query.answer(f"Недостаточно золота! Нужно {pt['cost']}.", show_alert=True)
                return
            await add_gold(db, user["id"], -pt["cost"])
            await db.execute(
                "INSERT INTO real_estate (user_id, property_type) VALUES (?, ?)",
                (user["id"], property_type)
            )
            await db.commit()
        await query.edit_message_text(
            f"✅ Вы купили {pt['name']}!",
            reply_markup=back_keyboard("re:menu")
        )
    except Exception as e:
        logger.error(f"Error in handle_realestate_buy: {e}", exc_info=True)


def setup_handlers(app: Application):
    app.add_handler(CallbackQueryHandler(handle_realestate_menu, pattern="^re:menu$"))
    app.add_handler(CallbackQueryHandler(handle_realestate_detail, pattern="^re:detail:"))
    app.add_handler(CallbackQueryHandler(handle_realestate_buy_menu, pattern="^re:buy:"))
    app.add_handler(CallbackQueryHandler(handle_realestate_buy, pattern="^re:confirm_buy:"))
