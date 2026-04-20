import logging
import aiosqlite
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from config import DB_PATH
from database import get_user, create_user, get_character_stats, update_user
from game.levels import exp_for_level, check_level_up
from keyboards import main_menu_keyboard, profile_keyboard, stats_keyboard, profession_keyboard, buffs_keyboard, back_keyboard

logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        telegram_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                user = await create_user(db, telegram_id, username)
                welcome = (
                    f"🎮 Добро пожаловать в игру, {username}!\n\n"
                    "Вы создали нового персонажа. Начните своё приключение!"
                )
            else:
                welcome = f"👋 С возвращением, {username}!"
        await update.message.reply_text(welcome, reply_markup=main_menu_keyboard())
    except Exception as e:
        logger.error(f"Error in cmd_start: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text("🎮 Главное меню:", reply_markup=main_menu_keyboard())
    except Exception as e:
        logger.error(f"Error in handle_main_menu: {e}", exc_info=True)


async def handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
        if not user:
            await query.edit_message_text("Персонаж не найден. Используйте /start.")
            return
        level = user["level"]
        exp = user["exp"]
        needed = exp_for_level(level)
        filled = int((exp / needed) * 10) if needed > 0 else 10
        bar = "█" * filled + "░" * (10 - filled)
        profession = user.get("profession") or "Не выбрана"
        clan_id = user.get("clan_id")
        clan_text = f"Клан ID: {clan_id}" if clan_id else "Нет клана"
        text = (
            f"👤 Профиль: {user['username']}\n"
            f"📊 Уровень: {level}\n"
            f"✨ Опыт: {exp}/{needed} [{bar}]\n"
            f"💰 Золото: {user['gold']}\n"
            f"💎 Премиум: {user['premium_currency']}\n"
            f"❤️ HP: {user['hp']}/{user['max_hp']}\n"
            f"⚔️ Профессия: {profession}\n"
            f"🏰 {clan_text}\n"
            f"📍 Локация: {user['current_location_id']}\n"
        )
        await query.edit_message_text(text, reply_markup=profile_keyboard())
    except Exception as e:
        logger.error(f"Error in handle_profile: {e}", exc_info=True)


async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        free = user["free_points"]
        text = (
            f"📊 Характеристики:\n\n"
            f"💪 Сила: {user['strength']}\n"
            f"🏃 Ловкость: {user['agility']}\n"
            f"🧠 Интеллект: {user['intelligence']}\n"
            f"❤️ Живучесть: {user['vitality']}\n"
            f"🍀 Удача: {user['luck']}\n\n"
            f"⭐ Свободных очков: {free}\n"
        )
        await query.edit_message_text(text, reply_markup=stats_keyboard(free))
    except Exception as e:
        logger.error(f"Error in handle_stats: {e}", exc_info=True)


async def handle_upgrade_stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        stat_key = parts[2]
        stat_map = {
            "str": "strength",
            "agi": "agility",
            "int": "intelligence",
            "vit": "vitality",
            "luck": "luck",
        }
        stat_field = stat_map.get(stat_key)
        if not stat_field:
            await query.answer("Неизвестная характеристика.", show_alert=True)
            return
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                await query.edit_message_text("Персонаж не найден.")
                return
            if user["free_points"] <= 0:
                await query.answer("Нет свободных очков!", show_alert=True)
                return
            new_val = user[stat_field] + 1
            new_fp = user["free_points"] - 1
            await update_user(db, user["id"], **{stat_field: new_val, "free_points": new_fp})
            user = await get_user(db, telegram_id)
        free = user["free_points"]
        text = (
            f"📊 Характеристики:\n\n"
            f"💪 Сила: {user['strength']}\n"
            f"🏃 Ловкость: {user['agility']}\n"
            f"🧠 Интеллект: {user['intelligence']}\n"
            f"❤️ Живучесть: {user['vitality']}\n"
            f"🍀 Удача: {user['luck']}\n\n"
            f"⭐ Свободных очков: {free}\n"
        )
        await query.edit_message_text(text, reply_markup=stats_keyboard(free))
    except Exception as e:
        logger.error(f"Error in handle_upgrade_stat: {e}", exc_info=True)


async def handle_profession_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        text = (
            "⚔️ Выберите профессию:\n\n"
            "🗡 Воин — мастер ближнего боя, высокая сила и живучесть\n"
            "🧙 Маг — использует магию, высокий интеллект\n"
            "🏹 Лучник — дальний бой, высокая ловкость и удача\n"
            "🗡 Разбойник — скрытность и критические удары\n"
            "✝️ Жрец — магия поддержки, интеллект и живучесть\n\n"
            "⚠️ Профессию можно выбрать только один раз!"
        )
        await query.edit_message_text(text, reply_markup=profession_keyboard())
    except Exception as e:
        logger.error(f"Error in handle_profession_menu: {e}", exc_info=True)


async def handle_set_profession(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        profession = parts[2]
        valid_professions = ["Воин", "Маг", "Лучник", "Разбойник", "Жрец"]
        if profession not in valid_professions:
            await query.answer("Неизвестная профессия.", show_alert=True)
            return
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                await query.edit_message_text("Персонаж не найден.")
                return
            if user.get("profession"):
                await query.answer("Профессия уже выбрана!", show_alert=True)
                return
            await update_user(db, user["id"], profession=profession)
        await query.edit_message_text(
            f"✅ Профессия «{profession}» успешно выбрана!",
            reply_markup=back_keyboard("profile:menu")
        )
    except Exception as e:
        logger.error(f"Error in handle_set_profession: {e}", exc_info=True)


async def handle_buffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            from database import get_user_buffs
            buffs = await get_user_buffs(db, user["id"])
        if not buffs:
            text = "✨ У вас нет активных бонусов."
        else:
            lines = ["✨ Активные бонусы:\n"]
            for b in buffs:
                expires = b.get("expires_at") or "Постоянный"
                lines.append(f"• {b['buff_type']}: +{b['value']} ({b['source']}) до {expires}")
            text = "\n".join(lines)
        await query.edit_message_text(text, reply_markup=buffs_keyboard(buffs))
    except Exception as e:
        logger.error(f"Error in handle_buffs: {e}", exc_info=True)


def setup_handlers(app: Application):
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(handle_main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(handle_profile, pattern="^profile:menu$"))
    app.add_handler(CallbackQueryHandler(handle_stats, pattern="^profile:stats$"))
    app.add_handler(CallbackQueryHandler(handle_upgrade_stat, pattern="^stats:up:"))
    app.add_handler(CallbackQueryHandler(handle_profession_menu, pattern="^prof:menu$"))
    app.add_handler(CallbackQueryHandler(handle_set_profession, pattern="^prof:set:"))
    app.add_handler(CallbackQueryHandler(handle_buffs, pattern="^buff:list$"))
