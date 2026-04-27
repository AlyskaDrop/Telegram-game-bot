from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("👤 Охотник", callback_data="profile:menu"),
            InlineKeyboardButton("🎒 Инвентарь", callback_data="equip:inventory:0"),
        ],
        [
            InlineKeyboardButton("🚪 Данжи", callback_data="loc:list"),
            InlineKeyboardButton("⚔️ Гильдия", callback_data="clan:menu"),
        ],
        [
            InlineKeyboardButton("🛒 Магазин", callback_data="shop:menu"),
            InlineKeyboardButton("📦 Рынок", callback_data="market:list:0"),
        ],
        [
            InlineKeyboardButton("🏟 Арена охотников", callback_data="arena:menu"),
            InlineKeyboardButton("🏭 Бизнес", callback_data="biz:menu"),
        ],
        [
            InlineKeyboardButton("🏠 Недвижимость", callback_data="re:menu"),
            InlineKeyboardButton("🎉 События", callback_data="event:list"),
        ],
        [
            InlineKeyboardButton("🎟 Промокод", callback_data="promo:start"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def profile_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📊 Характеристики", callback_data="profile:stats"),
            InlineKeyboardButton("🛡 Экипировка", callback_data="equip:slots"),
        ],
        [
            InlineKeyboardButton("✨ Бонусы", callback_data="buff:list"),
        ],
        [
            InlineKeyboardButton("🔙 Назад", callback_data="main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def stats_keyboard(free_points):
    keyboard = []
    if free_points > 0:
        keyboard.append([
            InlineKeyboardButton("💪 Сила +1", callback_data="stats:up:str"),
            InlineKeyboardButton("🏃 Ловкость +1", callback_data="stats:up:agi"),
        ])
        keyboard.append([
            InlineKeyboardButton("🧠 Интеллект +1", callback_data="stats:up:int"),
            InlineKeyboardButton("❤️ Живучесть +1", callback_data="stats:up:vit"),
        ])
        keyboard.append([
            InlineKeyboardButton("🍀 Удача +1", callback_data="stats:up:luck"),
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="profile:menu")])
    return InlineKeyboardMarkup(keyboard)


def clan_keyboard(is_in_clan, is_leader):
    keyboard = []
    if is_in_clan:
        keyboard.append([InlineKeyboardButton("📋 Информация о гильдии", callback_data="clan:info")])
        keyboard.append([InlineKeyboardButton("🏛 Здания гильдии", callback_data="clan:buildings")])
        if is_leader:
            keyboard.append([InlineKeyboardButton("⚙️ Управление", callback_data="clan:manage")])
        keyboard.append([InlineKeyboardButton("🚪 Покинуть гильдию", callback_data="clan:leave")])
    else:
        keyboard.append([InlineKeyboardButton("➕ Создать гильдию", callback_data="clan:create")])
        keyboard.append([InlineKeyboardButton("🔍 Найти гильдию", callback_data="clan:join_list")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


def clan_management_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 Объявление", callback_data="clan:announce")],
        [InlineKeyboardButton("🔙 Назад", callback_data="clan:menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def equipment_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🗡 Оружие", callback_data="equip:slot:weapon"),
            InlineKeyboardButton("🛡 Броня", callback_data="equip:slot:armor"),
        ],
        [
            InlineKeyboardButton("⛑ Шлем", callback_data="equip:slot:helmet"),
            InlineKeyboardButton("🥾 Ботинки", callback_data="equip:slot:boots"),
        ],
        [
            InlineKeyboardButton("💍 Кольцо", callback_data="equip:slot:ring"),
            InlineKeyboardButton("📿 Амулет", callback_data="equip:slot:amulet"),
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="profile:menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def inventory_keyboard(items, page, total_pages):
    keyboard = []
    for item in items:
        equipped_mark = "✅ " if item.get("is_equipped") else ""
        btn_text = f"{equipped_mark}{item.get('name', 'Предмет')} x{item.get('quantity', 1)}"
        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=f"equip:item:{item['inv_id']}")
        ])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Назад", callback_data=f"equip:inventory:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Вперёд ▶️", callback_data=f"equip:inventory:{page + 1}"))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


def locations_keyboard(locations, current_location_id):
    keyboard = []
    for loc in locations:
        mark = "📍 " if loc["id"] == current_location_id else ""
        keyboard.append([
            InlineKeyboardButton(
                f"{mark}{loc['name']} (ур. {loc['level_req']})",
                callback_data=f"loc:detail:{loc['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


def location_action_keyboard(location_id, player_level, loc_level_req, has_clan):
    keyboard = []
    if player_level >= loc_level_req:
        keyboard.append([InlineKeyboardButton("⚔️ Охота на монстров", callback_data=f"fight:monster:{location_id}")])
        keyboard.append([InlineKeyboardButton("👹 Сразиться с боссом данжа", callback_data=f"fight:boss:{location_id}")])
        if has_clan:
            keyboard.append([InlineKeyboardButton("🏰 Захватить врата", callback_data=f"loc:capture:{location_id}")])
    keyboard.append([InlineKeyboardButton("🔙 К воротам", callback_data="loc:list")])
    return InlineKeyboardMarkup(keyboard)


def market_keyboard(page, total_pages):
    keyboard = [
        [InlineKeyboardButton("➕ Выставить предмет", callback_data="market:create")],
        [InlineKeyboardButton("📦 Мои лоты", callback_data="market:mine")],
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Назад", callback_data=f"market:list:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Вперёд ▶️", callback_data=f"market:list:{page + 1}"))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


def shop_keyboard(shop_type):
    keyboard = []
    if shop_type != "npc":
        keyboard.append([InlineKeyboardButton("🛒 Обычный магазин", callback_data="shop:npc")])
    if shop_type != "donate":
        keyboard.append([InlineKeyboardButton("💎 Донат магазин", callback_data="shop:donate")])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


def business_keyboard(businesses):
    business_names = {b["business_type"]: b for b in businesses}
    keyboard = []
    all_types = ["tavern", "mine", "farm"]
    type_labels = {"tavern": "🍺 Таверна", "mine": "⛏ Шахта", "farm": "🌾 Ферма"}
    for bt in all_types:
        if bt in business_names:
            b = business_names[bt]
            keyboard.append([InlineKeyboardButton(
                f"{type_labels[bt]} (ур. {b['level']})",
                callback_data=f"biz:detail:{bt}"
            )])
        else:
            keyboard.append([InlineKeyboardButton(
                f"{type_labels[bt]} (купить)",
                callback_data=f"biz:buy:{bt}"
            )])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


def real_estate_keyboard(properties):
    owned_types = {p["property_type"] for p in properties}
    all_types = [
        ("small_house", "🏠 Маленький дом"),
        ("manor", "🏡 Усадьба"),
        ("castle", "🏰 Замок"),
    ]
    keyboard = []
    for pt, label in all_types:
        if pt in owned_types:
            keyboard.append([InlineKeyboardButton(f"✅ {label}", callback_data=f"re:detail:{pt}")])
        else:
            keyboard.append([InlineKeyboardButton(f"{label} (купить)", callback_data=f"re:buy:{pt}")])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


def events_keyboard(events):
    keyboard = []
    for event in events:
        keyboard.append([
            InlineKeyboardButton(event["name"], callback_data=f"event:detail:{event['id']}")
        ])
    if not events:
        keyboard.append([InlineKeyboardButton("Нет активных событий", callback_data="main_menu")])
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)


def arena_keyboard():
    keyboard = [
        [InlineKeyboardButton("⚔️ Вступить в очередь на бой", callback_data="arena:join")],
        [InlineKeyboardButton("🏆 Топ охотников", callback_data="arena:top")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def admin_keyboard():
    keyboard = [
        [InlineKeyboardButton("💰 Выдать золото", callback_data="admin:give_gold")],
        [InlineKeyboardButton("🎒 Выдать предмет", callback_data="admin:give_item")],
        [InlineKeyboardButton("🚫 Забанить", callback_data="admin:ban")],
        [InlineKeyboardButton("✅ Разбанить", callback_data="admin:unban")],
        [InlineKeyboardButton("🎉 Создать событие", callback_data="admin:event")],
        [InlineKeyboardButton("🎟 Создать промокод", callback_data="admin:promo")],
    ]
    return InlineKeyboardMarkup(keyboard)


def buffs_keyboard(buffs):
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="profile:menu")]]
    return InlineKeyboardMarkup(keyboard)


def back_keyboard(callback="main_menu"):
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=callback)]]
    return InlineKeyboardMarkup(keyboard)


def confirm_keyboard(action, item_id):
    keyboard = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm:{action}:{item_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data="main_menu"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def profession_keyboard():
    professions = ["Убийца", "Маг", "Лучник", "Боец", "Целитель"]
    keyboard = []
    for p in professions:
        keyboard.append([InlineKeyboardButton(p, callback_data=f"prof:set:{p}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="profile:menu")])
    return InlineKeyboardMarkup(keyboard)
