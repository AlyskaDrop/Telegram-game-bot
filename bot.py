import asyncio
import logging
import json
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
    """Seed initial game data: 10 Solo Leveling themed gates/dungeons, monsters, items"""
    locations = [
        (1, "E-ранг: Тёмный лес", 1, "Врата низшего ранга. Здесь водятся слабые монстры — идеально для начинающих охотников", "Гоблин-король", 500, 25, 10, "[]"),
        (2, "E-ранг: Логово разбойников", 3, "Заброшенный лагерь, полный гоблинов и орков низшего ранга", "Орк-вождь", 1200, 55, 20, "[]"),
        (3, "D-ранг: Ледяные пещеры", 5, "Данж с ледяными монстрами, требует определённой подготовки", "Ледяной фантом", 2500, 90, 40, "[]"),
        (4, "D-ранг: Руины проклятых", 8, "Старые руины, населённые нежитью и проклятыми духами", "Рыцарь смерти", 4000, 130, 55, "[]"),
        (5, "C-ранг: Подземный лабиринт", 10, "Запутанный данж с сильными монстрами и ловушками", "Высший орк Мага", 6000, 170, 70, "[]"),
        (6, "C-ранг: Башня Белджа", 13, "Легендарная башня из игры «Карты теней». Испытание для охотников", "Архимаг Белдж", 9000, 220, 90, "[]"),
        (7, "B-ранг: Остров Чеджу", 16, "Остров, захваченный муравьями-монстрами высшего ранга", "Генерал-муравей", 13000, 280, 110, "[]"),
        (8, "A-ранг: Пещера муравьёв", 20, "Главное гнездо муравьёв-монстров. Чрезвычайно опасно", "Военачальник Барка", 18000, 350, 140, "[]"),
        (9, "S-ранг: Врата Монарха", 25, "Врата, открытые силой Монарха. Появляются только у сильнейших охотников", "Монарх зверей", 25000, 440, 170, "[]"),
        (10, "Подземелье Антареса", 30, "Последняя обитель Монарха разрушения — Антареса. Величайшее испытание", "Антарес — Монарх разрушения", 40000, 600, 220, "[]"),
    ]
    for loc in locations:
        await db.execute(
            """INSERT OR IGNORE INTO locations (id, name, level_req, description, boss_name, boss_hp, boss_attack, boss_defense, loot_table)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            loc
        )

    monsters_data = [
        # E-ранг: Тёмный лес (location_id=1, level_req=1)
        ("Гоблин-разведчик", 1, 1, 40, 8, 3, 10, 5),
        ("Дикий волк", 1, 1, 55, 10, 4, 12, 6),
        ("Гоблин-воин", 1, 2, 65, 12, 5, 15, 8),
        ("Лесной гоблин", 1, 1, 30, 6, 2, 8, 4),
        ("Орк-боец", 1, 2, 70, 14, 5, 18, 10),
        # E-ранг: Логово разбойников (location_id=2, level_req=3)
        ("Орк-охранник", 2, 3, 90, 18, 8, 25, 15),
        ("Горный тролль", 2, 4, 130, 22, 10, 30, 18),
        ("Ядовитый паук-монстр", 2, 3, 75, 16, 6, 22, 12),
        ("Орк-шаман", 2, 4, 110, 20, 9, 28, 16),
        ("Тёмный маг-гоблин", 2, 5, 100, 25, 8, 35, 20),
        # D-ранг: Ледяные пещеры (location_id=3, level_req=5)
        ("Ледяной элементаль", 3, 5, 160, 30, 15, 40, 25),
        ("Снежный великан", 3, 6, 200, 35, 18, 50, 30),
        ("Ледяной рыцарь", 3, 6, 180, 32, 16, 45, 28),
        ("Морозный волк", 3, 5, 150, 28, 14, 38, 22),
        ("Фантом льда", 3, 7, 210, 38, 20, 55, 35),
        # D-ранг: Руины проклятых (location_id=4, level_req=8)
        ("Зомби-воин", 4, 8, 250, 45, 22, 65, 40),
        ("Призрак руин", 4, 8, 220, 42, 20, 60, 38),
        ("Скелет-маг", 4, 9, 270, 48, 25, 70, 45),
        ("Проклятый рыцарь-нежить", 4, 10, 300, 52, 28, 80, 50),
        ("Лич-охотник", 4, 9, 260, 46, 23, 68, 42),
        # C-ранг: Подземный лабиринт (location_id=5, level_req=10)
        ("Высший орк", 5, 10, 350, 60, 30, 90, 55),
        ("Орк-берсерк", 5, 11, 380, 65, 33, 100, 60),
        ("Минотавр-страж", 5, 12, 420, 70, 38, 110, 68),
        ("Тёмный маг-орк", 5, 11, 400, 68, 35, 105, 65),
        ("Орк-военачальник", 5, 12, 370, 63, 32, 95, 58),
        # C-ранг: Башня Белджа (location_id=6, level_req=13)
        ("Тёмный страж башни", 6, 13, 480, 80, 45, 130, 80),
        ("Каменный голем-страж", 6, 14, 530, 88, 50, 145, 90),
        ("Демон-охранник", 6, 15, 580, 95, 55, 160, 100),
        ("Теневой маг", 6, 14, 510, 84, 47, 138, 85),
        ("Рыцарь бездны", 6, 13, 460, 78, 43, 125, 78),
        # B-ранг: Остров Чеджу (location_id=7, level_req=16)
        ("Муравей-солдат", 7, 16, 650, 110, 60, 180, 110),
        ("Муравей-офицер", 7, 17, 700, 118, 65, 195, 120),
        ("Муравей-маг", 7, 18, 750, 126, 70, 210, 130),
        ("Муравей-рыцарь", 7, 17, 680, 114, 62, 187, 115),
        ("Гигантская оса-монстр", 7, 16, 630, 106, 58, 174, 108),
        # A-ранг: Пещера муравьёв (location_id=8, level_req=20)
        ("Элитный муравей-боец", 8, 20, 850, 140, 80, 240, 150),
        ("Муравей-полковник", 8, 21, 900, 150, 85, 260, 160),
        ("Муравей-генерал", 8, 22, 950, 160, 90, 280, 170),
        ("Королевский страж-муравей", 8, 21, 880, 145, 82, 250, 155),
        ("Муравей-тень", 8, 20, 820, 135, 78, 230, 145),
        # S-ранг: Врата Монарха (location_id=9, level_req=25)
        ("Тёмный дракон Монарха", 9, 25, 1100, 190, 110, 340, 210),
        ("Теневой великан", 9, 26, 1200, 205, 118, 370, 230),
        ("Страж бездны", 9, 27, 1300, 220, 126, 400, 250),
        ("Призрак Монарха", 9, 26, 1150, 198, 114, 355, 220),
        ("Теневой рыцарь-монарх", 9, 25, 1050, 183, 106, 325, 200),
        # Подземелье Антареса (location_id=10, level_req=30)
        ("Дракон Антареса", 10, 30, 1500, 260, 150, 500, 300),
        ("Демон-полководец", 10, 31, 1700, 280, 165, 550, 340),
        ("Слуга Монарха разрушения", 10, 30, 1400, 246, 143, 475, 285),
        ("Огненный рыцарь Антареса", 10, 31, 1600, 270, 158, 525, 320),
        ("Архидемон-маг", 10, 32, 1800, 300, 175, 600, 370),
    ]
    for m in monsters_data:
        await db.execute(
            """INSERT OR IGNORE INTO monsters (name, location_id, level, hp, attack, defense, exp_reward, gold_reward)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            m
        )

    items_data = [
        # Оружие (weapon) - NPC магазин охотников
        ("Железный меч охотника", "weapon", "common", 1, json.dumps({"attack": 3}), "Простейшее оружие начинающего охотника", "npc", 50),
        ("Стальной клинок", "weapon", "common", 3, json.dumps({"attack": 8}), "Надёжный клинок для данжей D-ранга", "npc", 150),
        ("Меч убийцы теней", "weapon", "uncommon", 6, json.dumps({"attack": 15}), "Клинок с лёгким теневым напылением", "npc", 400),
        ("Клинок охотника A-ранга", "weapon", "rare", 10, json.dumps({"attack": 25, "crit_chance": 2}), "Оружие опытного охотника высокого ранга", "npc", 1200),
        ("Боевой топор берсерка", "weapon", "uncommon", 5, json.dumps({"attack": 18}), "Любимое оружие орков-берсерков", "npc", 350),
        ("Лук Лю Чжиня", "weapon", "common", 2, json.dumps({"attack": 6, "dodge_chance": 1}), "Лук в стиле лучника гильдии Белой тигрицы", "npc", 120),
        ("Боевой посох мага", "weapon", "uncommon", 4, json.dumps({"attack": 12}), "Посох охотника-мага", "npc", 280),
        ("Кинжал убийцы", "weapon", "uncommon", 4, json.dumps({"attack": 10, "crit_chance": 3}), "Быстрый кинжал для скрытных атак", "npc", 300),
        # Броня (armor) - NPC
        ("Кожаная броня охотника", "armor", "common", 1, json.dumps({"defense": 3}), "Стандартное снаряжение охотника E-ранга", "npc", 80),
        ("Кольчуга охотника", "armor", "common", 4, json.dumps({"defense": 8}), "Надёжная защита для данжей C-ранга", "npc", 200),
        ("Броня из магического сплава", "armor", "uncommon", 7, json.dumps({"defense": 15}), "Усиленная броня из магического металла", "npc", 500),
        ("Доспехи охотника S-ранга", "armor", "rare", 12, json.dumps({"defense": 25, "hp": 50}), "Тяжёлые доспехи для охотников высшего ранга", "npc", 1500),
        ("Мантия охотника-мага", "armor", "uncommon", 5, json.dumps({"defense": 8, "hp": 30}), "Защитная мантия, усиливающая магию", "npc", 380),
        # Шлем (helmet) - NPC
        ("Шлем охотника", "helmet", "common", 1, json.dumps({"defense": 2}), "Стандартный шлем охотника", "npc", 60),
        ("Шлем рыцаря данжа", "helmet", "common", 4, json.dumps({"defense": 5}), "Прочный шлем из стали", "npc", 160),
        ("Шлем командира", "helmet", "uncommon", 8, json.dumps({"defense": 10}), "Шлем, который носят командиры охотников", "npc", 450),
        # Ботинки (boots) - NPC
        ("Сапоги охотника", "boots", "common", 1, json.dumps({"dodge_chance": 1}), "Удобные сапоги для быстрого передвижения", "npc", 70),
        ("Сапоги скорости охотника", "boots", "uncommon", 6, json.dumps({"dodge_chance": 3}), "Лёгкие сапоги из кожи монстров", "npc", 320),
        # Кольца (ring) - NPC
        ("Кольцо удачи охотника", "ring", "common", 1, json.dumps({"crit_chance": 1}), "Кольцо, усиливающее шанс критического удара", "npc", 100),
        ("Кольцо силы данжа", "ring", "uncommon", 5, json.dumps({"attack": 5}), "Кольцо с заключённой магией монстра", "npc", 300),
        # Амулеты (amulet) - NPC
        ("Амулет жизненной силы", "amulet", "common", 1, json.dumps({"hp": 20}), "Амулет, увеличивающий жизненную силу", "npc", 120),
        ("Амулет защитника ворот", "amulet", "uncommon", 6, json.dumps({"defense": 7}), "Амулет, используемый стражниками ворот", "npc", 350),
        # Легендарные предметы из вселенной Поднятия уровня (донат)
        ("Клинок демонического монарха", "weapon", "epic", 15, json.dumps({"attack": 45, "crit_chance": 8}), "Оружие Монарха демонов — источает тьму", "donate", 500),
        ("Доспехи Монарха теней", "armor", "legendary", 25, json.dumps({"defense": 60, "hp": 200}), "Легендарные доспехи Сон Чин-У, Монарха теней", "donate", 2000),
        ("Кольцо алчности", "ring", "epic", 20, json.dumps({"attack": 15, "defense": 10, "crit_chance": 5}), "Кольцо из подземелья испытаний — символ власти", "donate", 1000),
        ("Посох Монарха магии", "weapon", "legendary", 30, json.dumps({"attack": 80, "crit_chance": 10}), "Посох одного из Монархов магии", "donate", 3000),
        ("Сапоги тени", "boots", "epic", 18, json.dumps({"dodge_chance": 15}), "Сапоги, позволяющие перемещаться со скоростью тени", "donate", 800),
        ("Шлем Монарха зверей", "helmet", "epic", 20, json.dumps({"defense": 30, "hp": 100}), "Шлем из черепа Монарха зверей", "donate", 900),
        ("Амулет Властелина теней", "amulet", "legendary", 28, json.dumps({"hp": 500, "defense": 20}), "Амулет, дарующий силу теневой армии", "donate", 2500),
        ("Кинжал «Убийца монархов»", "weapon", "epic", 16, json.dumps({"attack": 35, "crit_chance": 15, "dodge_chance": 5}), "Смертоносный кинжал, изготовленный из клыка дракона Антареса", "donate", 750),
        # Дополнительные NPC предметы
        ("Боевой молот рейда", "weapon", "rare", 12, json.dumps({"attack": 30}), "Тяжёлый молот, применяемый в рейдах", "npc", 800),
        ("Щит охотника S-ранга", "armor", "rare", 10, json.dumps({"defense": 20, "hp": 30}), "Надёжный щит для защиты в S-ранговых данжах", "npc", 700),
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
