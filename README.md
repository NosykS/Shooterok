# Shooterok

A dynamic 2D Top-Down Stealth Shooter game built with Python and Pygame. Navigate through procedurally generated levels, eliminate enemies silently using a knife, or engage in intense firefights.

## Features

* **Procedural Map Generation**: Walls and hiding spots (bushes) are generated dynamically for every new game session.
* **Stealth Mechanics**: Hide in bushes to break enemy line of sight. Enemies react to footsteps and gunshot noise.
* **Melee & Ranged Combat**: Silent knife takedowns with a 90-degree attack cone and various firearms with distinct fire rates and noise radiuses.
* **Modular Architecture**: Clean, refactored codebase divided into logical packages (`core`, `entities`, `objects`, `world`).

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/Shooterok.git](https://github.com/YOUR_USERNAME/Shooterok.git)
   cd Shooterok
   ```
   
2. Set up a virtual environment:

```Bash
python -m venv .venv
```

3. Activate the virtual environment:

- Windows (PowerShell):

```PowerShell
.venv\Scripts\Activate.ps1
```
- Linux/macOS:

```Bash
source .venv/bin/activate
```
4. Install dependencies:

```Bash
pip install -r requirements.txt
```
🎮 How to Play
W, A, S, D: Move character

Mouse: Aim weapon

- Left Mouse Button (LMB): Attack (Shoot / Slash)
- 1, 2, 3: Switch weapons (Knife, Pistol, Rifle)
- E: Enter / Exit a hiding spot (bush)
- R: Restart game (Generate a new map)
- ESC: Exit to menu / Quit game