import logging
import json
import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from config import DB_PATH
from database import get_user, get_inventory, equip_item, unequip_item, get_equipped_items, get_item
from keyboards import inventory_keyboard, equipment_keyboard, back_keyboard

logger = logging.getLogger(__name__)


async def handle_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        page = int(parts[2]) if len(parts) > 2 else 0
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                await query.edit_message_text("Персонаж не найден.")
                return
            items, total = await get_inventory(db, user["id"], page=page, per_page=8)
        total_pages = max(1, (total + 7) // 8)
        if not items:
            await query.edit_message_text(
                "🎒 Ваш инвентарь пуст.",
                reply_markup=back_keyboard("main_menu")
            )
            return
        text = f"🎒 Инвентарь (стр. {page + 1}/{total_pages}):\n\nВыберите предмет для действий:"
        await query.edit_message_text(text, reply_markup=inventory_keyboard(items, page, total_pages))
    except Exception as e:
        logger.error(f"Error in handle_inventory: {e}", exc_info=True)


async def handle_equip_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        inv_id = int(parts[2])
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                await query.edit_message_text("Персонаж не найден.")
                return
            async with db.execute(
                "SELECT inv.*, i.name, i.type, i.stats, i.level_req, i.description FROM inventory inv JOIN items i ON inv.item_id = i.id WHERE inv.id = ? AND inv.user_id = ?",
                (inv_id, user["id"])
            ) as cursor:
                inv_row = await cursor.fetchone()
            if not inv_row:
                await query.answer("Предмет не найден!", show_alert=True)
                return
            inv_row = dict(inv_row)
            try:
                stats = json.loads(inv_row.get("stats", "{}"))
            except (json.JSONDecodeError, TypeError):
                stats = {}
            stats_text = ", ".join(f"{k}: +{v}" for k, v in stats.items()) if stats else "Без бонусов"
            equipped_mark = "✅ Надето" if inv_row["is_equipped"] else "❌ Снято"
            text = (
                f"🔍 {inv_row['name']}\n"
                f"Тип: {inv_row['type']}\n"
                f"Требуемый уровень: {inv_row['level_req']}\n"
                f"Бонусы: {stats_text}\n"
                f"Описание: {inv_row.get('description', '')}\n"
                f"Статус: {equipped_mark}"
            )
            action_btn = "equip:unequip" if inv_row["is_equipped"] else "equip:do"
            action_label = "❌ Снять" if inv_row["is_equipped"] else "✅ Надеть"
            keyboard = [
                [InlineKeyboardButton(action_label, callback_data=f"{action_btn}:{inv_id}")],
                [InlineKeyboardButton("🔙 Назад", callback_data="equip:inventory:0")],
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in handle_equip_item: {e}", exc_info=True)


async def handle_equip_slot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        if parts[1] == "do":
            inv_id = int(parts[2])
            telegram_id = update.effective_user.id
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                user = await get_user(db, telegram_id)
                if not user:
                    await query.edit_message_text("Персонаж не найден.")
                    return
                success = await equip_item(db, user["id"], inv_id)
            if success:
                await query.edit_message_text("✅ Предмет надет!", reply_markup=back_keyboard("equip:inventory:0"))
            else:
                await query.answer("Не удалось надеть предмет!", show_alert=True)
        elif parts[1] == "unequip":
            inv_id = int(parts[2])
            telegram_id = update.effective_user.id
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                user = await get_user(db, telegram_id)
                if not user:
                    await query.edit_message_text("Персонаж не найден.")
                    return
                await unequip_item(db, user["id"], inv_id)
            await query.edit_message_text("❌ Предмет снят!", reply_markup=back_keyboard("equip:inventory:0"))
        else:
            await query.answer("Неизвестное действие.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in handle_equip_slot: {e}", exc_info=True)


async def handle_equip_slots_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            equipped = await get_equipped_items(db, user["id"])
        slot_names = {
            "weapon": "🗡 Оружие",
            "armor": "🛡 Броня",
            "helmet": "⛑ Шлем",
            "boots": "🥾 Ботинки",
            "ring": "💍 Кольцо",
            "amulet": "📿 Амулет",
        }
        lines = ["🛡 Текущая экипировка:\n"]
        equipped_by_slot = {e["slot"]: e for e in equipped}
        for slot, label in slot_names.items():
            if slot in equipped_by_slot:
                item = equipped_by_slot[slot]
                lines.append(f"{label}: {item['name']}")
            else:
                lines.append(f"{label}: —")
        await query.edit_message_text("\n".join(lines), reply_markup=equipment_keyboard())
    except Exception as e:
        logger.error(f"Error in handle_equip_slots_menu: {e}", exc_info=True)


def setup_handlers(app: Application):
    app.add_handler(CallbackQueryHandler(handle_inventory, pattern="^equip:inventory:"))
    app.add_handler(CallbackQueryHandler(handle_equip_item, pattern="^equip:item:"))
    app.add_handler(CallbackQueryHandler(handle_equip_slot, pattern="^equip:(do|unequip):"))
    app.add_handler(CallbackQueryHandler(handle_equip_slots_menu, pattern="^equip:slots$"))
