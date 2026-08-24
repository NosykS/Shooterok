# src/core/active_effects.py
"""Shared HoT/DoT/timed-buff infrastructure (RPG_CLASS_SYSTEM.md step 13).

One system backs all three, per the design note in section 7: periodic HP
change (heal-over-time, damage-over-time) and temporary flat stat modifiers
(buffs/debuffs). Entities own a plain `active_effects: list[dict]` — empty
by default, so an unaffected entity costs nothing beyond the empty list
(RPG_CLASS_SYSTEM.md section 8 / CLAUDE.md section 8 performance guidance
for 50-100 simultaneous enemies).

No skill uses this yet — steps 9/14 (skills that actually apply HoT/DoT/
buffs) come later. This module is only the mechanism.
"""
from typing import Any


def add_hot_dot(entity: Any, delta_per_tick: float, ticks: int, tick_interval: int = 60) -> None:
    """Adds a periodic HP-change effect. Positive delta_per_tick heals (HoT),
    negative damages (DoT). Multiple instances stack — each is its own list
    entry, so e.g. several overlapping HoTs from heal_hot simply add up
    (RPG_CLASS_SYSTEM.md section 2)."""
    entity.active_effects.append({
        "kind": "hp_over_time",
        "delta_per_tick": delta_per_tick,
        "ticks_remaining": ticks,
        "tick_interval": tick_interval,
        "_timer": tick_interval,
    })


def add_timed_stat_buff(entity: Any, stat: str, amount: float, duration_ticks: int) -> None:
    """Adds `amount` to entity.<stat> for duration_ticks frames, then reverts it.
    Works for any numeric attribute (damage_mult, speed, evasion,
    damage_reduction_flat, ...) — a debuff is just a negative amount."""
    setattr(entity, stat, getattr(entity, stat) + amount)
    entity.active_effects.append({
        "kind": "stat_buff",
        "stat": stat,
        "amount": amount,
        "ticks_remaining": duration_ticks,
    })


def process_active_effects(entity: Any, max_hp_attr: str = "max_hp") -> None:
    """Ticks and expires an entity's active_effects. Call once per frame from
    Player.update()/Enemy.update(). No-op (cheap empty-list check) for the
    common case of an entity nothing is applied to."""
    effects = entity.active_effects
    if not effects:
        return

    remaining = []
    for effect in effects:
        effect["ticks_remaining"] -= 1

        if effect["kind"] == "hp_over_time":
            effect["_timer"] -= 1
            if effect["_timer"] <= 0:
                effect["_timer"] = effect["tick_interval"]
                max_hp = getattr(entity, max_hp_attr)
                entity.hp = max(0.0, min(max_hp, entity.hp + effect["delta_per_tick"]))

        if effect["ticks_remaining"] > 0:
            remaining.append(effect)
        elif effect["kind"] == "stat_buff":
            # Expired — revert the stat bonus so it doesn't linger permanently
            setattr(entity, effect["stat"], getattr(entity, effect["stat"]) - effect["amount"])

    entity.active_effects = remaining
