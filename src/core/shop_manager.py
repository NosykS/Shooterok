# src/core/shop_manager.py
from typing import Any

# Prices for new weapons and upgrades
SHOP_ITEMS: dict[str, dict[str, dict[str, Any]]] = {
    "weapons": {
        "rifle": {"price": 1200, "name": "Assault Rifle"},
        "shotgun": {"price": 1000, "name": "Shotgun"}
    },
    "upgrades": {
        "silencer": {"price": 400, "name": "Silencer (reduces noise by 30%)"},
        "extended_mag": {"price": 300, "name": "Extended Magazine (+50% ammo)"}
    }
}


class ShopManager:
    def __init__(self, game_data: dict[str, Any]) -> None:
        self.data = game_data

    def buy_weapon(self, weapon_id: str) -> tuple[bool, str]:
        """Purchases a new weapon, returns (success, message)."""
        if weapon_id not in SHOP_ITEMS["weapons"]:
            return False, "Weapon does not exist in the shop"

        if weapon_id in self.data["unlocked_weapons"]:
            return False, "This weapon is already purchased!"

        price = SHOP_ITEMS["weapons"][weapon_id]["price"]
        if self.data["money"] >= price:
            self.data["money"] -= price
            self.data["unlocked_weapons"].append(weapon_id)
            return True, f"Successfully purchased {SHOP_ITEMS['weapons'][weapon_id]['name']}!"

        return False, "Not enough money!"

    def add_money(self, amount: int) -> None:
        """Awards currency for completed missions."""
        self.data["money"] += amount
