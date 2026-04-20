import aiosqlite
import logging

logger = logging.getLogger(__name__)


async def init_db(db):
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE,
            username TEXT,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            gold INTEGER DEFAULT 100,
            premium_currency INTEGER DEFAULT 0,
            hp INTEGER DEFAULT 100,
            max_hp INTEGER DEFAULT 100,
            strength INTEGER DEFAULT 5,
            agility INTEGER DEFAULT 5,
            intelligence INTEGER DEFAULT 5,
            vitality INTEGER DEFAULT 5,
            luck INTEGER DEFAULT 5,
            free_points INTEGER DEFAULT 0,
            profession TEXT DEFAULT NULL,
            current_location_id INTEGER DEFAULT 1,
            clan_id INTEGER DEFAULT NULL,
            is_banned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            type TEXT,
            rarity TEXT,
            level_req INTEGER DEFAULT 1,
            stats TEXT DEFAULT '{}',
            description TEXT DEFAULT '',
            shop_type TEXT DEFAULT 'npc',
            price INTEGER DEFAULT 100
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            item_id INTEGER,
            quantity INTEGER DEFAULT 1,
            is_equipped INTEGER DEFAULT 0,
            slot TEXT DEFAULT NULL
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY,
            name TEXT,
            level_req INTEGER DEFAULT 1,
            description TEXT DEFAULT '',
            boss_name TEXT,
            boss_hp INTEGER DEFAULT 0,
            boss_attack INTEGER DEFAULT 0,
            boss_defense INTEGER DEFAULT 0,
            loot_table TEXT DEFAULT '[]',
            clan_owner_id INTEGER DEFAULT NULL
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS monsters (
            id INTEGER PRIMARY KEY,
            name TEXT,
            location_id INTEGER,
            level INTEGER DEFAULT 1,
            hp INTEGER DEFAULT 50,
            attack INTEGER DEFAULT 5,
            defense INTEGER DEFAULT 3,
            exp_reward INTEGER DEFAULT 10,
            gold_reward INTEGER DEFAULT 5,
            loot_table TEXT DEFAULT '[]',
            UNIQUE(name, location_id)
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS clans (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            leader_id INTEGER,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            gold INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS clan_buildings (
            id INTEGER PRIMARY KEY,
            clan_id INTEGER,
            building_type TEXT,
            level INTEGER DEFAULT 0,
            UNIQUE(clan_id, building_type)
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS market_listings (
            id INTEGER PRIMARY KEY,
            seller_id INTEGER,
            inventory_id INTEGER,
            item_id INTEGER,
            price INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS buffs (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            buff_type TEXT,
            value REAL,
            source TEXT,
            expires_at TIMESTAMP DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            business_type TEXT,
            level INTEGER DEFAULT 1,
            last_collected TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS real_estate (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            property_type TEXT,
            purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY,
            name TEXT,
            description TEXT,
            reward TEXT DEFAULT '{}',
            starts_at TIMESTAMP,
            ends_at TIMESTAMP
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            id INTEGER PRIMARY KEY,
            code TEXT UNIQUE,
            reward TEXT DEFAULT '{}',
            max_uses INTEGER DEFAULT 1,
            used_count INTEGER DEFAULT 0,
            expires_at TIMESTAMP DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS promo_uses (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            code_id INTEGER,
            used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, code_id)
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS arena_queue (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.commit()


async def get_user(db, telegram_id):
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def create_user(db, telegram_id, username):
    db.row_factory = aiosqlite.Row
    await db.execute(
        "INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)",
        (telegram_id, username)
    )
    await db.commit()
    return await get_user(db, telegram_id)


async def get_character_stats(db, user_id):
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_user(db, user_id, **kwargs):
    db.row_factory = aiosqlite.Row
    if not kwargs:
        return
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    await db.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
    await db.commit()


async def add_exp(db, user_id, exp_amount):
    db.row_factory = aiosqlite.Row
    await db.execute("UPDATE users SET exp = exp + ? WHERE id = ?", (exp_amount, user_id))
    await db.commit()


async def add_gold(db, user_id, gold_amount):
    db.row_factory = aiosqlite.Row
    await db.execute("UPDATE users SET gold = gold + ? WHERE id = ?", (gold_amount, user_id))
    await db.commit()


async def add_to_inventory(db, user_id, item_id, quantity=1):
    db.row_factory = aiosqlite.Row
    async with db.execute(
        "SELECT id, quantity FROM inventory WHERE user_id = ? AND item_id = ? AND is_equipped = 0",
        (user_id, item_id)
    ) as cursor:
        existing = await cursor.fetchone()
    if existing:
        await db.execute(
            "UPDATE inventory SET quantity = quantity + ? WHERE id = ?",
            (quantity, existing["id"])
        )
    else:
        await db.execute(
            "INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)",
            (user_id, item_id, quantity)
        )
    await db.commit()


async def remove_from_inventory(db, inventory_id, quantity=1):
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT quantity FROM inventory WHERE id = ?", (inventory_id,)) as cursor:
        row = await cursor.fetchone()
    if not row:
        return
    if row["quantity"] <= quantity:
        await db.execute("DELETE FROM inventory WHERE id = ?", (inventory_id,))
    else:
        await db.execute(
            "UPDATE inventory SET quantity = quantity - ? WHERE id = ?",
            (quantity, inventory_id)
        )
    await db.commit()


async def equip_item(db, user_id, inventory_id):
    db.row_factory = aiosqlite.Row
    async with db.execute(
        "SELECT inv.*, i.type, i.stats FROM inventory inv JOIN items i ON inv.item_id = i.id WHERE inv.id = ? AND inv.user_id = ?",
        (inventory_id, user_id)
    ) as cursor:
        inv_row = await cursor.fetchone()
    if not inv_row:
        return False
    slot = inv_row["type"]
    await db.execute(
        "UPDATE inventory SET is_equipped = 0, slot = NULL WHERE user_id = ? AND slot = ?",
        (user_id, slot)
    )
    await db.execute(
        "UPDATE inventory SET is_equipped = 1, slot = ? WHERE id = ?",
        (slot, inventory_id)
    )
    await db.commit()
    return True


async def unequip_item(db, user_id, inventory_id):
    db.row_factory = aiosqlite.Row
    await db.execute(
        "UPDATE inventory SET is_equipped = 0, slot = NULL WHERE id = ? AND user_id = ?",
        (inventory_id, user_id)
    )
    await db.commit()


async def get_equipped_items(db, user_id):
    db.row_factory = aiosqlite.Row
    async with db.execute(
        """SELECT inv.id as inv_id, inv.slot, i.* FROM inventory inv
           JOIN items i ON inv.item_id = i.id
           WHERE inv.user_id = ? AND inv.is_equipped = 1""",
        (user_id,)
    ) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_inventory(db, user_id, page=0, per_page=8):
    db.row_factory = aiosqlite.Row
    offset = page * per_page
    async with db.execute(
        """SELECT inv.id as inv_id, inv.quantity, inv.is_equipped, inv.slot, i.*
           FROM inventory inv JOIN items i ON inv.item_id = i.id
           WHERE inv.user_id = ?
           LIMIT ? OFFSET ?""",
        (user_id, per_page, offset)
    ) as cursor:
        rows = await cursor.fetchall()
    async with db.execute("SELECT COUNT(*) FROM inventory WHERE user_id = ?", (user_id,)) as cursor:
        total = (await cursor.fetchone())[0]
    return [dict(r) for r in rows], total


async def get_item(db, item_id):
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT * FROM items WHERE id = ?", (item_id,)) as cursor:
        row = await cursor.fetchone()
    return dict(row) if row else None


async def get_all_items(db):
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT * FROM items") as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_location(db, location_id):
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT * FROM locations WHERE id = ?", (location_id,)) as cursor:
        row = await cursor.fetchone()
    return dict(row) if row else None


async def get_all_locations(db):
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT * FROM locations ORDER BY level_req ASC") as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_monsters_at_location(db, location_id):
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT * FROM monsters WHERE location_id = ?", (location_id,)) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_clan(db, clan_id):
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT * FROM clans WHERE id = ?", (clan_id,)) as cursor:
        row = await cursor.fetchone()
    return dict(row) if row else None


async def get_user_clan(db, user_id):
    db.row_factory = aiosqlite.Row
    async with db.execute(
        "SELECT c.* FROM clans c JOIN users u ON u.clan_id = c.id WHERE u.id = ?",
        (user_id,)
    ) as cursor:
        row = await cursor.fetchone()
    return dict(row) if row else None


async def create_clan(db, name, leader_id):
    db.row_factory = aiosqlite.Row
    await db.execute(
        "INSERT INTO clans (name, leader_id) VALUES (?, ?)",
        (name, leader_id)
    )
    await db.commit()
    async with db.execute("SELECT id FROM clans WHERE name = ?", (name,)) as cursor:
        clan = await cursor.fetchone()
    clan_id = clan["id"]
    await db.execute("UPDATE users SET clan_id = ? WHERE id = ?", (clan_id, leader_id))
    await db.commit()
    return clan_id


async def get_clan_members(db, clan_id):
    db.row_factory = aiosqlite.Row
    async with db.execute(
        "SELECT * FROM users WHERE clan_id = ?",
        (clan_id,)
    ) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_clan_buildings(db, clan_id):
    db.row_factory = aiosqlite.Row
    async with db.execute(
        "SELECT * FROM clan_buildings WHERE clan_id = ?",
        (clan_id,)
    ) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def upgrade_clan_building(db, clan_id, building_type):
    db.row_factory = aiosqlite.Row
    await db.execute(
        """INSERT INTO clan_buildings (clan_id, building_type, level) VALUES (?, ?, 1)
           ON CONFLICT(clan_id, building_type) DO UPDATE SET level = level + 1""",
        (clan_id, building_type)
    )
    await db.commit()


async def get_market_listings(db, page=0, per_page=10):
    db.row_factory = aiosqlite.Row
    offset = page * per_page
    async with db.execute(
        """SELECT ml.*, i.name as item_name, i.rarity, i.type, u.username as seller_name
           FROM market_listings ml
           JOIN items i ON ml.item_id = i.id
           JOIN users u ON ml.seller_id = u.id
           ORDER BY ml.created_at DESC
           LIMIT ? OFFSET ?""",
        (per_page, offset)
    ) as cursor:
        rows = await cursor.fetchall()
    async with db.execute("SELECT COUNT(*) FROM market_listings") as cursor:
        total = (await cursor.fetchone())[0]
    return [dict(r) for r in rows], total


async def create_market_listing(db, seller_id, inventory_id, item_id, price):
    db.row_factory = aiosqlite.Row
    await db.execute(
        "INSERT INTO market_listings (seller_id, inventory_id, item_id, price) VALUES (?, ?, ?, ?)",
        (seller_id, inventory_id, item_id, price)
    )
    await db.commit()


async def remove_market_listing(db, listing_id):
    db.row_factory = aiosqlite.Row
    await db.execute("DELETE FROM market_listings WHERE id = ?", (listing_id,))
    await db.commit()


async def get_user_buffs(db, user_id):
    db.row_factory = aiosqlite.Row
    async with db.execute(
        """SELECT * FROM buffs WHERE user_id = ?
           AND (expires_at IS NULL OR expires_at > datetime('now'))""",
        (user_id,)
    ) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def add_buff(db, user_id, buff_type, value, source, expires_at=None):
    db.row_factory = aiosqlite.Row
    await db.execute(
        "INSERT INTO buffs (user_id, buff_type, value, source, expires_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, buff_type, value, source, expires_at)
    )
    await db.commit()


async def get_user_businesses(db, user_id):
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT * FROM businesses WHERE user_id = ?", (user_id,)) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_user_real_estate(db, user_id):
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT * FROM real_estate WHERE user_id = ?", (user_id,)) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_active_events(db):
    db.row_factory = aiosqlite.Row
    async with db.execute(
        "SELECT * FROM events WHERE starts_at <= datetime('now') AND ends_at >= datetime('now')"
    ) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_promo_code(db, code):
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT * FROM promo_codes WHERE code = ?", (code,)) as cursor:
        row = await cursor.fetchone()
    return dict(row) if row else None


async def use_promo_code(db, user_id, code_id):
    db.row_factory = aiosqlite.Row
    await db.execute(
        "INSERT INTO promo_uses (user_id, code_id) VALUES (?, ?)",
        (user_id, code_id)
    )
    await db.execute(
        "UPDATE promo_codes SET used_count = used_count + 1 WHERE id = ?",
        (code_id,)
    )
    await db.commit()


async def get_arena_battle(db, user_id):
    db.row_factory = aiosqlite.Row
    async with db.execute(
        """SELECT aq.*, u.id as opp_user_id, u.username, u.level, u.strength, u.agility,
                  u.intelligence, u.vitality, u.luck, u.hp, u.max_hp, u.profession
           FROM arena_queue aq
           JOIN users u ON aq.user_id = u.id
           WHERE aq.user_id != ?
           ORDER BY aq.joined_at ASC LIMIT 1""",
        (user_id,)
    ) as cursor:
        row = await cursor.fetchone()
    return dict(row) if row else None


async def get_all_items_of_type(db, shop_type):
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT * FROM items WHERE shop_type = ?", (shop_type,)) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_top_players(db, limit=10):
    db.row_factory = aiosqlite.Row
    async with db.execute(
        "SELECT * FROM users WHERE is_banned = 0 ORDER BY level DESC, exp DESC LIMIT ?",
        (limit,)
    ) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]
