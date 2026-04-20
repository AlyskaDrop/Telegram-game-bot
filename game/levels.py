import logging

logger = logging.getLogger(__name__)


def exp_for_level(level):
    """Exponential exp curve: level * level * 100"""
    return level * level * 100


async def check_level_up(user_id, db):
    """Check if user has enough exp to level up. Award 3 free stat points per level.
    Returns (leveled_up_bool, new_level)."""
    import aiosqlite
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT level, exp, free_points FROM users WHERE id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
    if not row:
        return False, 0
    level = row["level"]
    exp = row["exp"]
    free_points = row["free_points"]
    leveled_up = False
    while exp >= exp_for_level(level):
        exp -= exp_for_level(level)
        level += 1
        free_points += 3
        leveled_up = True
    if leveled_up:
        await db.execute(
            "UPDATE users SET level = ?, exp = ?, free_points = ? WHERE id = ?",
            (level, exp, free_points, user_id)
        )
        await db.commit()
    return leveled_up, level


def get_level_rewards(level):
    """Returns dict of gold rewards for reaching a level."""
    gold = 0
    if level == 5:
        gold = 500
    elif level == 10:
        gold = 1000
    elif level == 20:
        gold = 3000
    elif level == 30:
        gold = 5000
    elif level % 5 == 0:
        gold = 100
    return {"gold": gold}
