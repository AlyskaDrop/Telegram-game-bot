import asyncio
import logging
import json
import os
import aiosqlite
from telegram.ext import Application
from config import BOT_TOKEN, DB_PATH
from database import init_db

from handlers.start import setup_handlers as setup_start_handlers
from handlers.clan import setup_handlers as setup_clan_handlers
from handlers.equipment import setup_handlers as setup_equipment_handlers
from handlers.locations import setup_handlers as setup_locations_handlers
from handlers.combat import setup_handlers as setup_combat_handlers
from handlers.market import setup_handlers as setup_market_handlers
from handlers.shop import setup_handlers as setup_shop_handlers
from handlers.business import setup_handlers as setup_business_handlers
from handlers.realestate import setup_handlers as setup_realestate_handlers
from handlers.events import setup_handlers as setup_events_handlers
from handlers.promo import setup_handlers as setup_promo_handlers
from handlers.admin import setup_handlers as setup_admin_handlers

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_data(db):
    """Seed initial game data: 10 locations, 5 monsters per location, 30+ items"""
    locations = [
        (1, "Лесная поляна", 1, "Тихое место для начинающих авантюристов", "Лесной Страж", 500, 25, 10, "[]"),
        (2, "Тёмный лес", 3, "Густой лес, полный опасностей", "Повелитель Теней", 1200, 55, 20, "[]"),
        (3, "Горные пещеры", 5, "Запутанные пещеры в горах", "Каменный Голем", 2500, 90, 40, "[]"),
        (4, "Древние руины", 8, "Руины забытой цивилизации", "Архилич", 4000, 130, 55, "[]"),
        (5, "Болото смерти", 10, "Ядовитое болото, полное нежити", "Болотный Дракон", 6000, 170, 70, "[]"),
        (6, "Вулканические земли", 13, "Раскалённые земли у подножия вулкана", "Огненный Великан", 9000, 220, 90, "[]"),
        (7, "Ледяные пустоши", 16, "Бескрайние ледяные поля", "Ледяной Король", 13000, 280, 110, "[]"),
        (8, "Небесные острова", 20, "Острова парящие в облаках", "Небесный Дракон", 18000, 350, 140, "[]"),
        (9, "Подземное царство", 25, "Глубины подземного мира", "Повелитель Тьмы", 25000, 440, 170, "[]"),
        (10, "Врата ада", 30, "Место силы демонических существ", "Архидемон Бальзар", 40000, 600, 220, "[]"),
    ]
    for loc in locations:
        await db.execute(
            """INSERT OR IGNORE INTO locations (id, name, level_req, description, boss_name, boss_hp, boss_attack, boss_defense, loot_table)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            loc
        )

    monsters_data = [
        # Локация 1 (level_req=1)
        ("Лесной Волк", 1, 1, 40, 8, 3, 10, 5),
        ("Дикий Кабан", 1, 1, 55, 10, 4, 12, 6),
        ("Разбойник", 1, 2, 65, 12, 5, 15, 8),
        ("Огромная Крыса", 1, 1, 30, 6, 2, 8, 4),
        ("Злобный Гоблин", 1, 2, 70, 14, 5, 18, 10),
        # Локация 2 (level_req=3)
        ("Тёмный Эльф", 2, 3, 90, 18, 8, 25, 15),
        ("Лесной Тролль", 2, 4, 130, 22, 10, 30, 18),
        ("Ядовитый Паук", 2, 3, 75, 16, 6, 22, 12),
        ("Оборотень", 2, 4, 110, 20, 9, 28, 16),
        ("Тёмный Маг", 2, 5, 100, 25, 8, 35, 20),
        # Локация 3 (level_req=5)
        ("Каменный Страж", 3, 5, 160, 30, 15, 40, 25),
        ("Горный Тролль", 3, 6, 200, 35, 18, 50, 30),
        ("Ядовитая Мантикора", 3, 6, 180, 32, 16, 45, 28),
        ("Пещерный Медведь", 3, 5, 150, 28, 14, 38, 22),
        ("Огненная Змея", 3, 7, 210, 38, 20, 55, 35),
        # Локация 4 (level_req=8)
        ("Зомби-воин", 4, 8, 250, 45, 22, 65, 40),
        ("Призрак руин", 4, 8, 220, 42, 20, 60, 38),
        ("Скелет-маг", 4, 9, 270, 48, 25, 70, 45),
        ("Проклятый рыцарь", 4, 10, 300, 52, 28, 80, 50),
        ("Мертвец-охотник", 4, 9, 260, 46, 23, 68, 42),
        # Локация 5 (level_req=10)
        ("Болотная тварь", 5, 10, 350, 60, 30, 90, 55),
        ("Ядовитый элементаль", 5, 11, 380, 65, 33, 100, 60),
        ("Болотный великан", 5, 12, 420, 70, 38, 110, 68),
        ("Гнилой дракончик", 5, 11, 400, 68, 35, 105, 65),
        ("Болотная ведьма", 5, 12, 370, 63, 32, 95, 58),
        # Локация 6 (level_req=13)
        ("Огненный элементаль", 6, 13, 480, 80, 45, 130, 80),
        ("Лавовый голем", 6, 14, 530, 88, 50, 145, 90),
        ("Вулканический дракон", 6, 15, 580, 95, 55, 160, 100),
        ("Демон огня", 6, 14, 510, 84, 47, 138, 85),
        ("Горящий рыцарь", 6, 13, 460, 78, 43, 125, 78),
        # Локация 7 (level_req=16)
        ("Ледяной элементаль", 7, 16, 650, 110, 60, 180, 110),
        ("Снежный тролль", 7, 17, 700, 118, 65, 195, 120),
        ("Морозный дракон", 7, 18, 750, 126, 70, 210, 130),
        ("Ледяной рыцарь", 7, 17, 680, 114, 62, 187, 115),
        ("Вьюжная ведьма", 7, 16, 630, 106, 58, 174, 108),
        # Локация 8 (level_req=20)
        ("Облачный страж", 8, 20, 850, 140, 80, 240, 150),
        ("Небесный грифон", 8, 21, 900, 150, 85, 260, 160),
        ("Небесный дракончик", 8, 22, 950, 160, 90, 280, 170),
        ("Ангел хаоса", 8, 21, 880, 145, 82, 250, 155),
        ("Буревестник", 8, 20, 820, 135, 78, 230, 145),
        # Локация 9 (level_req=25)
        ("Демон тьмы", 9, 25, 1100, 190, 110, 340, 210),
        ("Тёмный голем", 9, 26, 1200, 205, 118, 370, 230),
        ("Ночной ужас", 9, 27, 1300, 220, 126, 400, 250),
        ("Хранитель бездны", 9, 26, 1150, 198, 114, 355, 220),
        ("Теневой дракон", 9, 25, 1050, 183, 106, 325, 200),
        # Локация 10 (level_req=30)
        ("Архидемон", 10, 30, 1500, 260, 150, 500, 300),
        ("Повелитель боли", 10, 31, 1700, 280, 165, 550, 340),
        ("Слуга ада", 10, 30, 1400, 246, 143, 475, 285),
        ("Адский рыцарь", 10, 31, 1600, 270, 158, 525, 320),
        ("Демон-маг", 10, 32, 1800, 300, 175, 600, 370),
    ]
    for m in monsters_data:
        await db.execute(
            """INSERT OR IGNORE INTO monsters (name, location_id, level, hp, attack, defense, exp_reward, gold_reward)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            m
        )

    items_data = [
        # Оружие (weapon) - NPC
        ("Деревянный меч", "weapon", "common", 1, json.dumps({"attack": 3}), "Простейшее оружие", "npc", 50),
        ("Железный меч", "weapon", "common", 3, json.dumps({"attack": 8}), "Надёжный меч из железа", "npc", 150),
        ("Стальной меч", "weapon", "uncommon", 6, json.dumps({"attack": 15}), "Меч из хорошей стали", "npc", 400),
        ("Меч воина", "weapon", "rare", 10, json.dumps({"attack": 25, "crit_chance": 2}), "Меч опытного воина", "npc", 1200),
        ("Топор берсерка", "weapon", "uncommon", 5, json.dumps({"attack": 18}), "Топор для ближнего боя", "npc", 350),
        ("Охотничий лук", "weapon", "common", 2, json.dumps({"attack": 6, "dodge_chance": 1}), "Лук для охотника", "npc", 120),
        ("Боевой посох", "weapon", "uncommon", 4, json.dumps({"attack": 12}), "Посох мага", "npc", 280),
        ("Кинжал разбойника", "weapon", "uncommon", 4, json.dumps({"attack": 10, "crit_chance": 3}), "Быстрый кинжал", "npc", 300),
        # Броня (armor) - NPC
        ("Кожаная броня", "armor", "common", 1, json.dumps({"defense": 3}), "Простая кожаная броня", "npc", 80),
        ("Кольчуга", "armor", "common", 4, json.dumps({"defense": 8}), "Надёжная кольчуга", "npc", 200),
        ("Стальная броня", "armor", "uncommon", 7, json.dumps({"defense": 15}), "Броня из стали", "npc", 500),
        ("Доспехи воина", "armor", "rare", 12, json.dumps({"defense": 25, "hp": 50}), "Тяжёлые доспехи воина", "npc", 1500),
        ("Мантия мага", "armor", "uncommon", 5, json.dumps({"defense": 8, "hp": 30}), "Защитная мантия мага", "npc", 380),
        # Шлем (helmet) - NPC
        ("Кожаный шлем", "helmet", "common", 1, json.dumps({"defense": 2}), "Простой шлем из кожи", "npc", 60),
        ("Железный шлем", "helmet", "common", 4, json.dumps({"defense": 5}), "Шлем из железа", "npc", 160),
        ("Стальной шлем", "helmet", "uncommon", 8, json.dumps({"defense": 10}), "Надёжный стальной шлем", "npc", 450),
        # Ботинки (boots) - NPC
        ("Кожаные ботинки", "boots", "common", 1, json.dumps({"dodge_chance": 1}), "Удобные ботинки", "npc", 70),
        ("Сапоги скорости", "boots", "uncommon", 6, json.dumps({"dodge_chance": 3}), "Быстрые сапоги", "npc", 320),
        # Кольца (ring) - NPC
        ("Кольцо удачи", "ring", "common", 1, json.dumps({"crit_chance": 1}), "Приносит немного удачи", "npc", 100),
        ("Кольцо силы", "ring", "uncommon", 5, json.dumps({"attack": 5}), "Усиливает атаку", "npc", 300),
        # Амулеты (amulet) - NPC
        ("Амулет жизни", "amulet", "common", 1, json.dumps({"hp": 20}), "Увеличивает здоровье", "npc", 120),
        ("Амулет защиты", "amulet", "uncommon", 6, json.dumps({"defense": 7}), "Амулет защитника", "npc", 350),
        # Редкие предметы (донат)
        ("Клинок тьмы", "weapon", "epic", 15, json.dumps({"attack": 45, "crit_chance": 8}), "Тёмный клинок из мира теней", "donate", 500),
        ("Доспехи дракона", "armor", "legendary", 25, json.dumps({"defense": 60, "hp": 200}), "Броня из чешуи дракона", "donate", 2000),
        ("Кольцо всевластия", "ring", "epic", 20, json.dumps({"attack": 15, "defense": 10, "crit_chance": 5}), "Кольцо великой силы", "donate", 1000),
        ("Посох архимага", "weapon", "legendary", 30, json.dumps({"attack": 80, "crit_chance": 10}), "Посох великого мага", "donate", 3000),
        ("Сапоги вихря", "boots", "epic", 18, json.dumps({"dodge_chance": 15}), "Сапоги невероятной скорости", "donate", 800),
        ("Шлем дракона", "helmet", "epic", 20, json.dumps({"defense": 30, "hp": 100}), "Шлем из черепа дракона", "donate", 900),
        ("Амулет бессмертия", "amulet", "legendary", 28, json.dumps({"hp": 500, "defense": 20}), "Амулет дарующий бессмертие", "donate", 2500),
        ("Кинжал убийцы", "weapon", "epic", 16, json.dumps({"attack": 35, "crit_chance": 15, "dodge_chance": 5}), "Смертоносный кинжал", "donate", 750),
        # Ещё обычных для разнообразия
        ("Боевой молот", "weapon", "rare", 12, json.dumps({"attack": 30}), "Тяжёлый боевой молот", "npc", 800),
        ("Щит воина", "armor", "rare", 10, json.dumps({"defense": 20, "hp": 30}), "Надёжный щит", "npc", 700),
    ]
    for item in items_data:
        await db.execute(
            """INSERT OR IGNORE INTO items (name, type, rarity, level_req, stats, description, shop_type, price)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            item
        )
    await db.commit()
    logger.info("Seed data inserted successfully.")


async def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) if os.path.dirname(DB_PATH) else None
    app = Application.builder().token(BOT_TOKEN).build()
    async with aiosqlite.connect(DB_PATH) as db:
        await init_db(db)
        await seed_data(db)
    setup_start_handlers(app)
    setup_clan_handlers(app)
    setup_equipment_handlers(app)
    setup_locations_handlers(app)
    setup_combat_handlers(app)
    setup_market_handlers(app)
    setup_shop_handlers(app)
    setup_business_handlers(app)
    setup_realestate_handlers(app)
    setup_events_handlers(app)
    setup_promo_handlers(app)
    setup_admin_handlers(app)
    await app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
