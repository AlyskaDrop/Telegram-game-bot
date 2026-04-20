import logging
import aiosqlite
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from config import DB_PATH
from database import get_user, get_user_businesses, add_gold
from keyboards import business_keyboard, back_keyboard

logger = logging.getLogger(__name__)

BUSINESS_TYPES = {
    "tavern": {
        "name": "🍺 Таверна",
        "income_per_hour": 50,
        "purchase_cost": 500,
        "max_level": 5,
        "upgrade_cost_per_level": 300,
    },
    "mine": {
        "name": "⛏ Шахта",
        "income_per_hour": 100,
        "purchase_cost": 1000,
        "max_level": 5,
        "upgrade_cost_per_level": 600,
    },
    "farm": {
        "name": "🌾 Ферма",
        "income_per_hour": 30,
        "purchase_cost": 200,
        "max_level": 5,
        "upgrade_cost_per_level": 150,
    },
}


def calc_income(business, hours):
    bt = BUSINESS_TYPES.get(business["business_type"])
    if not bt:
        return 0
    return int(bt["income_per_hour"] * business["level"] * hours)


async def handle_business_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            businesses = await get_user_businesses(db, user["id"])
        text = "🏭 Бизнес\n\nВаши бизнесы:"
        await query.edit_message_text(text, reply_markup=business_keyboard(businesses))
    except Exception as e:
        logger.error(f"Error in handle_business_menu: {e}", exc_info=True)


async def handle_business_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        business_type = parts[2]
        bt = BUSINESS_TYPES.get(business_type)
        if not bt:
            await query.answer("Неизвестный тип бизнеса!", show_alert=True)
            return
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                await query.edit_message_text("Персонаж не найден.")
                return
            async with db.execute(
                "SELECT * FROM businesses WHERE user_id = ? AND business_type = ?",
                (user["id"], business_type)
            ) as cursor:
                biz = await cursor.fetchone()
        if not biz:
            await query.edit_message_text(
                f"{bt['name']}\nЦена покупки: {bt['purchase_cost']} золота\nДоход: {bt['income_per_hour']} золота/час",
                reply_markup=back_keyboard("biz:menu")
            )
            return
        biz = dict(biz)
        now = datetime.now(timezone.utc)
        last = datetime.fromisoformat(biz["last_collected"].replace("Z", "+00:00")) if biz["last_collected"] else now
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        hours = max(0, (now - last).total_seconds() / 3600)
        pending = calc_income(biz, hours)
        upgrade_cost = biz["level"] * bt["upgrade_cost_per_level"]
        keyboard = [
            [InlineKeyboardButton(f"💰 Собрать ({pending} золота)", callback_data=f"biz:collect:{business_type}")],
        ]
        if biz["level"] < bt["max_level"]:
            keyboard.append([InlineKeyboardButton(f"⬆️ Улучшить ({upgrade_cost} золота)", callback_data=f"biz:upgrade:{business_type}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="biz:menu")])
        text = (
            f"{bt['name']}\n"
            f"Уровень: {biz['level']}/{bt['max_level']}\n"
            f"Доход: {bt['income_per_hour'] * biz['level']} золота/час\n"
            f"Накоплено: {pending} золота"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in handle_business_detail: {e}", exc_info=True)


async def handle_business_buy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        business_type = parts[2]
        bt = BUSINESS_TYPES.get(business_type)
        if not bt:
            await query.answer("Неизвестный тип бизнеса!", show_alert=True)
            return
        keyboard = [
            [InlineKeyboardButton(f"✅ Купить за {bt['purchase_cost']} золота", callback_data=f"biz:confirm_buy:{business_type}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="biz:menu")],
        ]
        text = (
            f"{bt['name']}\n"
            f"Цена: {bt['purchase_cost']} золота\n"
            f"Доход: {bt['income_per_hour']} золота/час\n"
            f"Макс. уровень: {bt['max_level']}"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in handle_business_buy_menu: {e}", exc_info=True)


async def handle_business_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        business_type = parts[2]
        bt = BUSINESS_TYPES.get(business_type)
        if not bt:
            await query.answer("Неизвестный тип бизнеса!", show_alert=True)
            return
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                await query.edit_message_text("Персонаж не найден.")
                return
            async with db.execute(
                "SELECT id FROM businesses WHERE user_id = ? AND business_type = ?",
                (user["id"], business_type)
            ) as cursor:
                existing = await cursor.fetchone()
            if existing:
                await query.answer("Вы уже владеете этим бизнесом!", show_alert=True)
                return
            if user["gold"] < bt["purchase_cost"]:
                await query.answer(f"Недостаточно золота! Нужно {bt['purchase_cost']}.", show_alert=True)
                return
            await add_gold(db, user["id"], -bt["purchase_cost"])
            await db.execute(
                "INSERT INTO businesses (user_id, business_type, level) VALUES (?, ?, 1)",
                (user["id"], business_type)
            )
            await db.commit()
        await query.edit_message_text(
            f"✅ Вы купили {bt['name']}!",
            reply_markup=back_keyboard("biz:menu")
        )
    except Exception as e:
        logger.error(f"Error in handle_business_buy: {e}", exc_info=True)


async def handle_business_collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        business_type = parts[2]
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                await query.edit_message_text("Персонаж не найден.")
                return
            async with db.execute(
                "SELECT * FROM businesses WHERE user_id = ? AND business_type = ?",
                (user["id"], business_type)
            ) as cursor:
                biz = await cursor.fetchone()
            if not biz:
                await query.answer("Бизнес не найден!", show_alert=True)
                return
            biz = dict(biz)
            bt = BUSINESS_TYPES.get(business_type, {})
            now = datetime.now(timezone.utc)
            last = datetime.fromisoformat(biz["last_collected"].replace("Z", "+00:00")) if biz["last_collected"] else now
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            hours = max(0, (now - last).total_seconds() / 3600)
            income = calc_income(biz, hours)
            if income <= 0:
                await query.answer("Нечего собирать! Приходите позже.", show_alert=True)
                return
            await add_gold(db, user["id"], income)
            await db.execute(
                "UPDATE businesses SET last_collected = datetime('now') WHERE id = ?",
                (biz["id"],)
            )
            await db.commit()
        await query.edit_message_text(
            f"✅ Собрано {income} золота с {bt.get('name', business_type)}!",
            reply_markup=back_keyboard("biz:menu")
        )
    except Exception as e:
        logger.error(f"Error in handle_business_collect: {e}", exc_info=True)


async def handle_business_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        business_type = parts[2]
        bt = BUSINESS_TYPES.get(business_type)
        if not bt:
            await query.answer("Неизвестный тип бизнеса!", show_alert=True)
            return
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                await query.edit_message_text("Персонаж не найден.")
                return
            async with db.execute(
                "SELECT * FROM businesses WHERE user_id = ? AND business_type = ?",
                (user["id"], business_type)
            ) as cursor:
                biz = await cursor.fetchone()
            if not biz:
                await query.answer("Бизнес не найден!", show_alert=True)
                return
            biz = dict(biz)
            if biz["level"] >= bt["max_level"]:
                await query.answer("Достигнут максимальный уровень!", show_alert=True)
                return
            upgrade_cost = biz["level"] * bt["upgrade_cost_per_level"]
            if user["gold"] < upgrade_cost:
                await query.answer(f"Недостаточно золота! Нужно {upgrade_cost}.", show_alert=True)
                return
            await add_gold(db, user["id"], -upgrade_cost)
            await db.execute(
                "UPDATE businesses SET level = level + 1 WHERE id = ?",
                (biz["id"],)
            )
            await db.commit()
        await query.edit_message_text(
            f"✅ {bt['name']} улучшен до уровня {biz['level'] + 1}!",
            reply_markup=back_keyboard("biz:menu")
        )
    except Exception as e:
        logger.error(f"Error in handle_business_upgrade: {e}", exc_info=True)


def setup_handlers(app: Application):
    app.add_handler(CallbackQueryHandler(handle_business_menu, pattern="^biz:menu$"))
    app.add_handler(CallbackQueryHandler(handle_business_detail, pattern="^biz:detail:"))
    app.add_handler(CallbackQueryHandler(handle_business_buy_menu, pattern="^biz:buy:"))
    app.add_handler(CallbackQueryHandler(handle_business_buy, pattern="^biz:confirm_buy:"))
    app.add_handler(CallbackQueryHandler(handle_business_collect, pattern="^biz:collect:"))
    app.add_handler(CallbackQueryHandler(handle_business_upgrade, pattern="^biz:upgrade:"))
