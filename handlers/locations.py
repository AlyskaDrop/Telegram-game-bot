import logging
import random
import aiosqlite
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from config import DB_PATH
from database import (
    get_user, get_location, get_all_locations, get_monsters_at_location,
    update_user, add_exp, add_gold, add_to_inventory
)
from game.combat import calculate_player_stats, fight_monster
from game.levels import check_level_up
from keyboards import locations_keyboard, location_action_keyboard, back_keyboard

logger = logging.getLogger(__name__)


async def handle_locations_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            locations = await get_all_locations(db)
        await query.edit_message_text(
            f"🗺 Локации (ваш уровень: {user['level']}):",
            reply_markup=locations_keyboard(locations, user["current_location_id"])
        )
    except Exception as e:
        logger.error(f"Error in handle_locations_list: {e}", exc_info=True)


async def handle_location_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        location_id = int(parts[2])
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                await query.edit_message_text("Персонаж не найден.")
                return
            location = await get_location(db, location_id)
            if not location:
                await query.edit_message_text("Локация не найдена.")
                return
            monsters = await get_monsters_at_location(db, location_id)
            clan = None
            if user.get("clan_id"):
                from database import get_user_clan
                clan = await get_user_clan(db, user["id"])
            if user["current_location_id"] != location_id:
                await update_user(db, user["id"], current_location_id=location_id)
        monster_list = ", ".join(m["name"] for m in monsters) if monsters else "Нет монстров"
        owner_text = f"\n👑 Владелец: клан {location.get('clan_owner_id')}" if location.get("clan_owner_id") else ""
        text = (
            f"📍 {location['name']}\n"
            f"Требуемый уровень: {location['level_req']}\n"
            f"Описание: {location.get('description', '')}\n"
            f"Монстры: {monster_list}\n"
            f"🐉 Босс: {location.get('boss_name', 'Нет')} (HP: {location.get('boss_hp', 0)}){owner_text}"
        )
        await query.edit_message_text(
            text,
            reply_markup=location_action_keyboard(
                location_id, user["level"], location["level_req"], bool(clan)
            )
        )
    except Exception as e:
        logger.error(f"Error in handle_location_detail: {e}", exc_info=True)


async def handle_fight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        location_id = int(parts[2])
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                await query.edit_message_text("Персонаж не найден.")
                return
            if user["is_banned"]:
                await query.answer("Вы забанены!", show_alert=True)
                return
            location = await get_location(db, location_id)
            if not location or user["level"] < location["level_req"]:
                await query.answer("Недостаточный уровень для этой локации!", show_alert=True)
                return
            monsters = await get_monsters_at_location(db, location_id)
            if not monsters:
                await query.edit_message_text("В этой локации нет монстров.", reply_markup=back_keyboard("loc:list"))
                return
            monster = random.choice(monsters)
            player_stats = await calculate_player_stats(user["id"], db)
            result = await fight_monster(player_stats, monster)
            if result["won"]:
                await add_exp(db, user["id"], result["exp_gained"])
                await add_gold(db, user["id"], result["gold_gained"])
                for loot in result["loot"]:
                    await add_to_inventory(db, user["id"], loot["item_id"], loot["quantity"])
                leveled_up, new_level = await check_level_up(user["id"], db)
                new_hp = max(1, result["player_hp_remaining"])
                await update_user(db, user["id"], hp=new_hp)
            else:
                hp_left = max(1, result["player_hp_remaining"])
                await update_user(db, user["id"], hp=hp_left)
                leveled_up = False
                new_level = user["level"]
        log_preview = "\n".join(result["log"][-5:]) if result["log"] else ""
        if result["won"]:
            loot_text = ", ".join(f"{l['item_id']}x{l['quantity']}" for l in result["loot"]) if result["loot"] else "Нет"
            level_up_text = f"\n🎉 Уровень повышен до {new_level}!" if leveled_up else ""
            text = (
                f"⚔️ Бой с {monster['name']}:\n\n"
                f"{log_preview}\n\n"
                f"✅ Победа! Раундов: {result['rounds']}\n"
                f"✨ Опыт: +{result['exp_gained']}\n"
                f"💰 Золото: +{result['gold_gained']}\n"
                f"🎒 Добыча: {loot_text}"
                f"{level_up_text}"
            )
        else:
            text = (
                f"⚔️ Бой с {monster['name']}:\n\n"
                f"{log_preview}\n\n"
                f"❌ Поражение! Раундов: {result['rounds']}\n"
                f"HP осталось: {result['player_hp_remaining']}"
            )
        await query.edit_message_text(text, reply_markup=back_keyboard(f"loc:detail:{location_id}"))
    except Exception as e:
        logger.error(f"Error in handle_fight: {e}", exc_info=True)


async def handle_boss_fight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        location_id = int(parts[2])
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                await query.edit_message_text("Персонаж не найден.")
                return
            if user["is_banned"]:
                await query.answer("Вы забанены!", show_alert=True)
                return
            location = await get_location(db, location_id)
            if not location:
                await query.edit_message_text("Локация не найдена.")
                return
            if not location.get("boss_name") or not location.get("boss_hp"):
                await query.edit_message_text("В этой локации нет босса.", reply_markup=back_keyboard(f"loc:detail:{location_id}"))
                return
            boss = {
                "name": location["boss_name"],
                "hp": location["boss_hp"],
                "attack": location["boss_attack"],
                "defense": location["boss_defense"],
                "exp_reward": location["boss_hp"] // 2,
                "gold_reward": location["boss_hp"] // 3,
                "loot_table": location.get("loot_table", "[]"),
            }
            player_stats = await calculate_player_stats(user["id"], db)
            result = await fight_monster(player_stats, boss)
            if result["won"]:
                await add_exp(db, user["id"], result["exp_gained"])
                await add_gold(db, user["id"], result["gold_gained"])
                for loot in result["loot"]:
                    await add_to_inventory(db, user["id"], loot["item_id"], loot["quantity"])
                leveled_up, new_level = await check_level_up(user["id"], db)
                new_hp = max(1, result["player_hp_remaining"])
                await update_user(db, user["id"], hp=new_hp)
                level_up_text = f"\n🎉 Уровень повышен до {new_level}!" if leveled_up else ""
                text = (
                    f"🐉 Бой с боссом {boss['name']}:\n\n"
                    f"✅ Победа! Раундов: {result['rounds']}\n"
                    f"✨ Опыт: +{result['exp_gained']}\n"
                    f"💰 Золото: +{result['gold_gained']}"
                    f"{level_up_text}"
                )
            else:
                hp_left = max(1, result["player_hp_remaining"])
                await update_user(db, user["id"], hp=hp_left)
                text = (
                    f"🐉 Бой с боссом {boss['name']}:\n\n"
                    f"❌ Поражение! Раундов: {result['rounds']}"
                )
        await query.edit_message_text(text, reply_markup=back_keyboard(f"loc:detail:{location_id}"))
    except Exception as e:
        logger.error(f"Error in handle_boss_fight: {e}", exc_info=True)


def setup_handlers(app: Application):
    app.add_handler(CallbackQueryHandler(handle_locations_list, pattern="^loc:list$"))
    app.add_handler(CallbackQueryHandler(handle_location_detail, pattern="^loc:detail:"))
    app.add_handler(CallbackQueryHandler(handle_fight, pattern="^fight:monster:"))
    app.add_handler(CallbackQueryHandler(handle_boss_fight, pattern="^fight:boss:"))
