# Shooterok

A 2D top-down stealth-shooter built with Python and Pygame. Sneak through
hand-crafted levels, take out enemies silently, or fight your way through
in loud, gunfire-heavy firefights — the choice (and the noise) is yours.

## Features

* **Stealth mechanics**: hide in bushes to break enemy line of sight; enemies
  build suspicion from footsteps and gunfire noise before fully alerting.
* **Missions**: three mission types — stealth escape (fail on alert),
  elimination, and data heist (collect + escape) — across three levels
  built in Tiled (`assets/maps/*.tmx`).
* **Melee & ranged combat**: silent knife takedowns (instant kill on an
  unaware enemy, damage otherwise) with a directional attack cone, plus a
  growing arsenal of firearms (pistols, rifles, shotguns) with distinct
  fire rates, spread, noise radius, and reload times.
* **Progression & economy**: XP and player levels, a stat-upgrade system
  (HP/armor/speed tiers spent from level-up skill points), a shop to
  unlock new weapons, and persistent save/load (`savegame.json`, manual
  save from the pause menu).
* **Audio**: sound effects (weapons, footsteps, hits) and background
  music, with a dedicated in-game volume settings screen.
* **RPG class system (in development, not yet playable)**: the backend
  data and stat/damage math for 9 class subtypes (Tank/DD/Heal/Support,
  melee and ranged variants) already exists in `src/settings.py`
  (`CLASS_DEFINITIONS`) and is wired into `Player`/`Enemy` — class-based
  stat multipliers, a weapon whitelist per class, and passive combat
  buffs for enemies that scale with player level. **There is no in-game
  UI yet to pick a class**, so this system has no visible effect during
  normal play for now; it's active groundwork for an upcoming feature.

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/NosykS/Shooterok.git
   cd Shooterok
   ```

2. Set up a virtual environment:

   ```bash
   python -m venv .venv
   ```

3. Activate the virtual environment:

   - Windows (PowerShell):
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - Linux/macOS:
     ```bash
     source .venv/bin/activate
     ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Run the game:

   ```bash
   python main.py
   ```

## 🎮 How to Play

**Movement & combat**
- `W`, `A`, `S`, `D`: Move
- `Left Shift` (hold while moving): Stealth walk — slower, silent, no footstep noise
- Mouse: Aim
- Left Mouse Button: Attack (fire the equipped weapon, or melee if a knife is equipped)
- `1` / `2` / `3` / `4`: Switch weapon — bound to knife / pistol (silenced) /
  shotgun / rifle respectively, and only works once that weapon is unlocked
  (shotgun and rifle are bought in the shop between missions)
- `E`: Enter / exit a hiding spot (bush)
- `R` (in a mission): Restart the current mission on a fresh map

**Menus**
- `Space`: Start / continue from the main menu, shop, or after a mission
- `Esc`: Pause during a mission, or back out of menus
- Mouse: All menu buttons and volume sliders

## Project layout

```
main.py
src/
  core/       — game loop, level/mission/save/sound/UI/physics managers
  entities/   — player.py, enemy.py
  objects/    — bullet.py, obstacle.py, hiding_spot.py, mission_elements.py
  settings.py — all game configuration/constants (weapons, enemy types,
                mission configs, and the in-progress CLASS_DEFINITIONS)
```
