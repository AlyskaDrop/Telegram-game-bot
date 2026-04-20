import json
import random
import logging
from database import get_character_stats, get_equipped_items, get_item

logger = logging.getLogger(__name__)


async def calculate_player_stats(user_id, db):
    """Get full player stats including equipment bonuses."""
    user = await get_character_stats(db, user_id)
    if not user:
        return {}

    strength = user["strength"]
    agility = user["agility"]
    intelligence = user["intelligence"]
    vitality = user["vitality"]
    luck = user["luck"]
    profession = user.get("profession")

    if profession == "Воин":
        strength = int(strength * 1.2)
        vitality = int(vitality * 1.1)
    elif profession == "Маг":
        intelligence = int(intelligence * 1.2)
        agility = int(agility * 1.1)
    elif profession == "Лучник":
        agility = int(agility * 1.2)
        luck = int(luck * 1.1)
    elif profession == "Разбойник":
        agility = int(agility * 1.15)
        luck = int(luck * 1.15)
    elif profession == "Жрец":
        intelligence = int(intelligence * 1.2)
        vitality = int(vitality * 1.1)

    base_hp = 100 + vitality * 10
    if profession in ("Маг", "Жрец"):
        base_attack = 5 + intelligence * 2
    else:
        base_attack = 5 + strength * 2
    base_defense = 2 + vitality
    crit_chance = 5.0 + luck * 0.5
    dodge_chance = 2.0 + agility * 0.3
    speed = agility

    bonus_attack = 0
    bonus_defense = 0
    bonus_hp = 0
    equipped = await get_equipped_items(db, user_id)
    for eq_item in equipped:
        try:
            stats = json.loads(eq_item.get("stats", "{}"))
        except (json.JSONDecodeError, TypeError):
            stats = {}
        bonus_attack += stats.get("attack", 0)
        bonus_defense += stats.get("defense", 0)
        bonus_hp += stats.get("hp", 0)
        crit_chance += stats.get("crit_chance", 0)
        dodge_chance += stats.get("dodge_chance", 0)

    current_hp = user.get("hp", base_hp)

    return {
        "hp": current_hp,
        "max_hp": base_hp + bonus_hp,
        "attack": base_attack + bonus_attack,
        "defense": base_defense + bonus_defense,
        "speed": speed,
        "crit_chance": min(crit_chance, 75.0),
        "dodge_chance": min(dodge_chance, 50.0),
    }


def calculate_damage(attacker_attack, defender_defense, crit_chance=0.1, dodge_chance=0.1):
    """Returns (damage, is_crit, is_dodge)."""
    if random.random() < dodge_chance:
        return 0, False, True
    base = max(1, attacker_attack - defender_defense // 2) + random.randint(-2, 2)
    is_crit = random.random() < crit_chance
    if is_crit:
        base *= 2
    return max(1, base), is_crit, False


async def fight_monster(player_stats, monster):
    """Simulate fight against a monster. Returns result dict."""
    from game.loot import generate_loot

    p_hp = player_stats["hp"]
    p_attack = player_stats["attack"]
    p_defense = player_stats["defense"]
    p_speed = player_stats["speed"]
    p_crit = player_stats["crit_chance"] / 100.0
    p_dodge = player_stats["dodge_chance"] / 100.0

    m_hp = monster["hp"]
    m_attack = monster["attack"]
    m_defense = monster.get("defense", 3)

    log = []
    rounds = 0
    won = False
    player_has_initiative = p_speed >= m_defense

    for _ in range(20):
        rounds += 1
        if player_has_initiative:
            dmg, is_crit, is_dodge = calculate_damage(p_attack, m_defense, p_crit, 0.05)
            if is_dodge:
                log.append(f"Раунд {rounds}: Монстр уклонился!")
            else:
                crit_txt = " (КРИТ!)" if is_crit else ""
                m_hp -= dmg
                log.append(f"Раунд {rounds}: Вы наносите {dmg}{crit_txt} урона монстру. HP монстра: {max(0, m_hp)}")
            if m_hp <= 0:
                won = True
                break
            dmg2, is_crit2, is_dodge2 = calculate_damage(m_attack, p_defense, 0.05, p_dodge)
            if is_dodge2:
                log.append(f"Раунд {rounds}: Вы уклонились от атаки монстра!")
            else:
                crit_txt2 = " (КРИТ!)" if is_crit2 else ""
                p_hp -= dmg2
                log.append(f"Раунд {rounds}: Монстр наносит {dmg2}{crit_txt2} урона вам. Ваш HP: {max(0, p_hp)}")
            if p_hp <= 0:
                break
        else:
            dmg2, is_crit2, is_dodge2 = calculate_damage(m_attack, p_defense, 0.05, p_dodge)
            if is_dodge2:
                log.append(f"Раунд {rounds}: Вы уклонились от атаки монстра!")
            else:
                crit_txt2 = " (КРИТ!)" if is_crit2 else ""
                p_hp -= dmg2
                log.append(f"Раунд {rounds}: Монстр наносит {dmg2}{crit_txt2} урона вам. Ваш HP: {max(0, p_hp)}")
            if p_hp <= 0:
                break
            dmg, is_crit, is_dodge = calculate_damage(p_attack, m_defense, p_crit, 0.05)
            if is_dodge:
                log.append(f"Раунд {rounds}: Монстр уклонился!")
            else:
                crit_txt = " (КРИТ!)" if is_crit else ""
                m_hp -= dmg
                log.append(f"Раунд {rounds}: Вы наносите {dmg}{crit_txt} урона монстру. HP монстра: {max(0, m_hp)}")
            if m_hp <= 0:
                won = True
                break

    exp_gained = 0
    gold_gained = 0
    loot = []
    if won:
        exp_gained = monster.get("exp_reward", 10)
        gold_gained = monster.get("gold_reward", 5)
        loot = generate_loot(monster.get("loot_table", "[]"), 1)

    return {
        "won": won,
        "rounds": rounds,
        "player_hp_remaining": max(0, p_hp),
        "exp_gained": exp_gained,
        "gold_gained": gold_gained,
        "loot": loot,
        "log": log,
    }


async def fight_pvp(attacker_stats, defender_stats):
    """PvP combat. Returns dict: winner, rounds, log."""
    a_hp = attacker_stats["hp"]
    d_hp = defender_stats["hp"]
    a_attack = attacker_stats["attack"]
    d_attack = defender_stats["attack"]
    a_defense = attacker_stats["defense"]
    d_defense = defender_stats["defense"]
    a_crit = attacker_stats["crit_chance"] / 100.0
    d_crit = defender_stats["crit_chance"] / 100.0
    a_dodge = attacker_stats["dodge_chance"] / 100.0
    d_dodge = defender_stats["dodge_chance"] / 100.0

    log = []
    rounds = 0

    for _ in range(20):
        rounds += 1
        dmg, is_crit, is_dodge = calculate_damage(a_attack, d_defense, a_crit, d_dodge)
        if is_dodge:
            log.append(f"Раунд {rounds}: Защитник уклонился!")
        else:
            crit_txt = " (КРИТ!)" if is_crit else ""
            d_hp -= dmg
            log.append(f"Раунд {rounds}: Атакующий наносит {dmg}{crit_txt}. HP защитника: {max(0, d_hp)}")
        if d_hp <= 0:
            return {"winner": "attacker", "rounds": rounds, "log": log}

        dmg2, is_crit2, is_dodge2 = calculate_damage(d_attack, a_defense, d_crit, a_dodge)
        if is_dodge2:
            log.append(f"Раунд {rounds}: Атакующий уклонился!")
        else:
            crit_txt2 = " (КРИТ!)" if is_crit2 else ""
            a_hp -= dmg2
            log.append(f"Раунд {rounds}: Защитник наносит {dmg2}{crit_txt2}. HP атакующего: {max(0, a_hp)}")
        if a_hp <= 0:
            return {"winner": "defender", "rounds": rounds, "log": log}

    winner = "attacker" if a_hp >= d_hp else "defender"
    return {"winner": winner, "rounds": rounds, "log": log}
