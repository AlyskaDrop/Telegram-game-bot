import logging
import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CallbackQueryHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters, CommandHandler
)

from config import DB_PATH
from database import (
    get_user, get_user_clan, create_clan, get_clan, get_clan_members,
    get_clan_buildings, upgrade_clan_building, update_user, add_gold
)
from keyboards import clan_keyboard, clan_management_keyboard, back_keyboard

logger = logging.getLogger(__name__)

WAITING_CLAN_NAME = 0
CLAN_CREATE_COST = 1000


async def handle_clan_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            clan = await get_user_clan(db, user["id"])
            is_leader = clan and clan["leader_id"] == user["id"] if clan else False
        text = "⚔️ Меню клана\n\n"
        if clan:
            text += f"Ваш клан: {clan['name']}\nУровень: {clan['level']}\nЗолото клана: {clan['gold']}"
        else:
            text += "Вы не состоите в клане."
        await query.edit_message_text(text, reply_markup=clan_keyboard(bool(clan), is_leader))
    except Exception as e:
        logger.error(f"Error in handle_clan_menu: {e}", exc_info=True)


async def handle_clan_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            if user.get("clan_id"):
                await query.edit_message_text("Вы уже состоите в клане!", reply_markup=back_keyboard("clan:menu"))
                return ConversationHandler.END
            if user["gold"] < CLAN_CREATE_COST:
                await query.edit_message_text(
                    f"Недостаточно золота! Нужно {CLAN_CREATE_COST} золота.",
                    reply_markup=back_keyboard("clan:menu")
                )
                return ConversationHandler.END
        await query.edit_message_text(
            f"Создание клана стоит {CLAN_CREATE_COST} золота.\nВведите название клана:"
        )
        return WAITING_CLAN_NAME
    except Exception as e:
        logger.error(f"Error in handle_clan_create: {e}", exc_info=True)
        return ConversationHandler.END


async def handle_clan_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        clan_name = update.message.text.strip()
        if not clan_name or len(clan_name) < 3 or len(clan_name) > 30:
            await update.message.reply_text("Название клана должно быть от 3 до 30 символов. Попробуйте снова:")
            return WAITING_CLAN_NAME
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                await update.message.reply_text("Персонаж не найден.")
                return ConversationHandler.END
            await create_clan(db, clan_name, user["id"])
            await add_gold(db, user["id"], -CLAN_CREATE_COST)
        await update.message.reply_text(
            f"✅ Клан «{clan_name}» успешно создан!",
            reply_markup=back_keyboard("clan:menu")
        )
    except Exception as e:
        logger.error(f"Error in handle_clan_name_input: {e}", exc_info=True)
        await update.message.reply_text("Ошибка при создании клана. Возможно, такое название уже занято.")
    return ConversationHandler.END


async def handle_clan_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            clan = await get_user_clan(db, user["id"])
            if not clan:
                await query.edit_message_text("Вы не в клане.", reply_markup=back_keyboard("clan:menu"))
                return
            members = await get_clan_members(db, clan["id"])
        member_list = "\n".join(f"• {m['username']} (ур. {m['level']})" for m in members[:10])
        text = (
            f"⚔️ Клан: {clan['name']}\n"
            f"Уровень: {clan['level']}\n"
            f"Опыт: {clan['exp']}\n"
            f"Золото: {clan['gold']}\n"
            f"Участников: {len(members)}\n\n"
            f"Участники:\n{member_list}"
        )
        await query.edit_message_text(text, reply_markup=back_keyboard("clan:menu"))
    except Exception as e:
        logger.error(f"Error in handle_clan_info: {e}", exc_info=True)


async def handle_clan_buildings(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            clan = await get_user_clan(db, user["id"])
            if not clan:
                await query.edit_message_text("Вы не в клане.", reply_markup=back_keyboard("clan:menu"))
                return
            buildings = await get_clan_buildings(db, clan["id"])
        building_names = {
            "barracks": "🏋 Казармы",
            "treasury": "💰 Казна",
            "forge": "⚒ Кузница",
            "library": "📚 Библиотека",
        }
        if not buildings:
            lines = ["🏛 Здания клана: нет построенных зданий\n"]
        else:
            lines = ["🏛 Здания клана:\n"]
            for b in buildings:
                name = building_names.get(b["building_type"], b["building_type"])
                lines.append(f"• {name}: уровень {b['level']}")
        upgrade_kb = []
        for bt, bn in building_names.items():
            upgrade_kb.append([InlineKeyboardButton(f"⬆️ Улучшить {bn}", callback_data=f"clan:upgrade:{bt}")])
        upgrade_kb.append([InlineKeyboardButton("🔙 Назад", callback_data="clan:menu")])
        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(upgrade_kb))
    except Exception as e:
        logger.error(f"Error in handle_clan_buildings: {e}", exc_info=True)


async def handle_clan_upgrade_building(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        building_type = parts[2]
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                await query.edit_message_text("Персонаж не найден.")
                return
            clan = await get_user_clan(db, user["id"])
            if not clan:
                await query.edit_message_text("Вы не в клане.", reply_markup=back_keyboard("clan:menu"))
                return
            if clan["leader_id"] != user["id"]:
                await query.answer("Только лидер клана может улучшать здания!", show_alert=True)
                return
            cost = (clan["level"] + 1) * 500
            if clan["gold"] < cost:
                await query.answer(f"Недостаточно золота клана! Нужно {cost}.", show_alert=True)
                return
            await upgrade_clan_building(db, clan["id"], building_type)
            await db.execute("UPDATE clans SET gold = gold - ? WHERE id = ?", (cost, clan["id"]))
            await db.commit()
        await query.edit_message_text(
            f"✅ Здание «{building_type}» улучшено!",
            reply_markup=back_keyboard("clan:buildings")
        )
    except Exception as e:
        logger.error(f"Error in handle_clan_upgrade_building: {e}", exc_info=True)


async def handle_clan_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            clan = await get_user_clan(db, user["id"])
            if not clan:
                await query.edit_message_text("Вы не в клане.", reply_markup=back_keyboard("clan:menu"))
                return
            if clan["leader_id"] == user["id"]:
                await query.answer("Лидер не может покинуть клан! Передайте лидерство или распустите клан.", show_alert=True)
                return
            await update_user(db, user["id"], clan_id=None)
        await query.edit_message_text("Вы покинули клан.", reply_markup=back_keyboard("clan:menu"))
    except Exception as e:
        logger.error(f"Error in handle_clan_leave: {e}", exc_info=True)


async def handle_clan_manage(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            clan = await get_user_clan(db, user["id"])
            if not clan or clan["leader_id"] != user["id"]:
                await query.answer("Только лидер клана может управлять кланом!", show_alert=True)
                return
        await query.edit_message_text("⚙️ Управление кланом:", reply_markup=clan_management_keyboard())
    except Exception as e:
        logger.error(f"Error in handle_clan_manage: {e}", exc_info=True)


async def handle_clan_join_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM clans ORDER BY level DESC LIMIT 10") as cursor:
                clans = [dict(r) for r in await cursor.fetchall()]
        keyboard = []
        for clan in clans:
            keyboard.append([InlineKeyboardButton(
                f"{clan['name']} (ур. {clan['level']})",
                callback_data=f"clan:join:{clan['id']}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="clan:menu")])
        await query.edit_message_text(
            "🔍 Доступные кланы:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in handle_clan_join_list: {e}", exc_info=True)


def setup_handlers(app: Application):
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_clan_create, pattern="^clan:create$")],
        states={
            WAITING_CLAN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_clan_name_input)],
        },
        fallbacks=[CommandHandler("start", lambda u, c: ConversationHandler.END)],
    )
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(handle_clan_menu, pattern="^clan:menu$"))
    app.add_handler(CallbackQueryHandler(handle_clan_info, pattern="^clan:info$"))
    app.add_handler(CallbackQueryHandler(handle_clan_buildings, pattern="^clan:buildings$"))
    app.add_handler(CallbackQueryHandler(handle_clan_upgrade_building, pattern="^clan:upgrade:"))
    app.add_handler(CallbackQueryHandler(handle_clan_leave, pattern="^clan:leave$"))
    app.add_handler(CallbackQueryHandler(handle_clan_manage, pattern="^clan:manage$"))
    app.add_handler(CallbackQueryHandler(handle_clan_join_list, pattern="^clan:join_list$"))
