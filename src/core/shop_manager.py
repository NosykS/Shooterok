# src/core/shop_manager.py
from src.settings import WEAPONS

# Ціни на нову зброю та покращення
SHOP_ITEMS = {
    "weapons": {
        "rifle": {"price": 1200, "name": "Штурмова гвинтівка"},
        "shotgun": {"price": 1000, "name": "Дробовик"}
    },
    "upgrades": {
        "silencer": {"price": 400, "name": "Глушник (Зменшує шум на 30%)"},
        "extended_mag": {"price": 300, "name": "Збільшений магазин (+50% набоїв)"}
    }
}


class ShopManager:
    def __init__(self, game_data):
        self.data = game_data

    def buy_weapon(self, weapon_id):
        """Купівля нової зброї"""
        if weapon_id not in SHOP_ITEMS["weapons"]:
            return False, "Зброя не існує в магазині"

        if weapon_id in self.data["unlocked_weapons"]:
            return False, "Ця зброя вже куплена!"

        price = SHOP_ITEMS["weapons"][weapon_id]["price"]
        if self.data["money"] >= price:
            self.data["money"] -= price
            self.data["unlocked_weapons"].append(weapon_id)
            return True, f"Успішно куплено {SHOP_ITEMS['weapons'][weapon_id]['name']}!"

        return False, "Недостатньо грошей!"

    def add_money(self, amount):
        """Нарахування валюти за місії"""
        self.data["money"] += amount