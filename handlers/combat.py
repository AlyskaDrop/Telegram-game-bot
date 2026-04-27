import logging
import aiosqlite
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from config import DB_PATH
from database import get_user, get_arena_battle, add_exp, add_gold, get_top_players, update_user
from game.combat import calculate_player_stats, fight_pvp
from keyboards import arena_keyboard, back_keyboard

logger = logging.getLogger(__name__)


async def handle_arena_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                "SELECT COUNT(*) as cnt FROM arena_queue WHERE user_id = ?", (user["id"],)
            ) as cursor:
                row = await cursor.fetchone()
            in_queue = dict(row)["cnt"] > 0
        status = "Вы в очереди ожидания." if in_queue else "Вы не в очереди."
        text = f"🏟 Арена охотников\n\n{status}\n\nСразитесь с другими охотниками за звание сильнейшего!"
        await query.edit_message_text(text, reply_markup=arena_keyboard())
    except Exception as e:
        logger.error(f"Error in handle_arena_menu: {e}", exc_info=True)


async def handle_arena_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            if user["is_banned"]:
                await query.answer("Вы забанены!", show_alert=True)
                return
            async with db.execute(
                "SELECT id FROM arena_queue WHERE user_id = ?", (user["id"],)
            ) as cursor:
                already = await cursor.fetchone()
            if already:
                await query.answer("Вы уже в очереди!", show_alert=True)
                return
            opponent = await get_arena_battle(db, user["id"])
            if opponent:
                opp_id = opponent["opp_user_id"]
                player_stats = await calculate_player_stats(user["id"], db)
                opp_stats = await calculate_player_stats(opp_id, db)
                result = await fight_pvp(player_stats, opp_stats)
                await db.execute("DELETE FROM arena_queue WHERE user_id = ?", (opp_id,))
                await db.commit()
                if result["winner"] == "attacker":
                    winner_id = user["id"]
                    loser_id = opp_id
                    winner_text = "Вы победили!"
                else:
                    winner_id = opp_id
                    loser_id = user["id"]
                    winner_text = "Вы проиграли!"
                exp_reward = 50 + user["level"] * 5
                gold_reward = 30 + user["level"] * 3
                await add_exp(db, winner_id, exp_reward)
                await add_gold(db, winner_id, gold_reward)
                log_preview = "\n".join(result["log"][-5:]) if result["log"] else ""
                text = (
                    f"⚔️ Арена: бой с {opponent.get('username', 'Неизвестный')}\n\n"
                    f"{log_preview}\n\n"
                    f"{winner_text}\n"
                    f"Раундов: {result['rounds']}\n"
                )
                if result["winner"] == "attacker":
                    text += f"✨ Опыт: +{exp_reward}\n💰 Золото: +{gold_reward}"
            else:
                await db.execute("INSERT INTO arena_queue (user_id) VALUES (?)", (user["id"],))
                await db.commit()
                text = "✅ Вы добавлены в очередь арены. Ожидайте противника!"
        await query.edit_message_text(text, reply_markup=back_keyboard("arena:menu"))
    except Exception as e:
        logger.error(f"Error in handle_arena_join: {e}", exc_info=True)


async def handle_pvp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        parts = query.data.split(":")
        target_user_id = int(parts[2])
        telegram_id = update.effective_user.id
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            user = await get_user(db, telegram_id)
            if not user:
                await query.edit_message_text("Персонаж не найден.")
                return
            if user["id"] == target_user_id:
                await query.answer("Нельзя сражаться с собой!", show_alert=True)
                return
            async with db.execute("SELECT * FROM users WHERE id = ?", (target_user_id,)) as cursor:
                target = await cursor.fetchone()
            if not target:
                await query.answer("Противник не найден!", show_alert=True)
                return
            target = dict(target)
            player_stats = await calculate_player_stats(user["id"], db)
            opp_stats = await calculate_player_stats(target_user_id, db)
            result = await fight_pvp(player_stats, opp_stats)
            if result["winner"] == "attacker":
                winner_text = "Вы победили!"
                exp_reward = 30 + user["level"] * 3
                gold_reward = 20 + user["level"] * 2
                await add_exp(db, user["id"], exp_reward)
                await add_gold(db, user["id"], gold_reward)
            else:
                winner_text = "Вы проиграли!"
                exp_reward = 10
                gold_reward = 0
                await add_exp(db, user["id"], exp_reward)
        log_preview = "\n".join(result["log"][-5:]) if result["log"] else ""
        text = (
            f"⚔️ PvP бой с {target['username']}:\n\n"
            f"{log_preview}\n\n"
            f"{winner_text}\nРаундов: {result['rounds']}"
        )
        await query.edit_message_text(text, reply_markup=back_keyboard("arena:menu"))
    except Exception as e:
        logger.error(f"Error in handle_pvp: {e}", exc_info=True)


def setup_handlers(app: Application):
    app.add_handler(CallbackQueryHandler(handle_arena_menu, pattern="^arena:menu$"))
    app.add_handler(CallbackQueryHandler(handle_arena_join, pattern="^arena:join$"))
    app.add_handler(CallbackQueryHandler(handle_pvp, pattern="^pvp:fight:"))
