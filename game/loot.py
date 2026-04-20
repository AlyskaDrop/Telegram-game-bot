import json
import random


def generate_loot(loot_table_json, player_level):
    """loot_table is JSON list of {item_id, chance, quantity_min, quantity_max}.
    Returns list of {item_id, quantity}."""
    try:
        loot_table = json.loads(loot_table_json) if isinstance(loot_table_json, str) else loot_table_json
    except (json.JSONDecodeError, TypeError):
        loot_table = []
    result = []
    for entry in loot_table:
        chance = entry.get("chance", 0)
        if random.random() < chance:
            qty_min = entry.get("quantity_min", 1)
            qty_max = entry.get("quantity_max", 1)
            quantity = random.randint(qty_min, qty_max)
            result.append({"item_id": entry["item_id"], "quantity": quantity})
    return result


def get_rarity_weights(player_level):
    """Returns dict of rarity weights based on player level."""
    return {
        "common": max(10, 80 - player_level),
        "uncommon": 15,
        "rare": 5 + player_level // 5,
        "epic": 2 + player_level // 10,
        "legendary": 1 + player_level // 20,
    }
