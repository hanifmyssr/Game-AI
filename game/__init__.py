"""Package Game-AI: Modul utama game dan AI.

Sub-packages:
- game.core: Konfigurasi, event system, dan sprite animation
- game.ai: Algoritma AI (Pathfinding, CSP, Local Search, Minimax / Alpha-Beta, Adaptive Difficulty)
- game.battle: Turn-based battle system, VFX, dan Squad model
- game.world: Tilemap, Player, dan NPC overworld
- game.ui: Overlay sidebar, Decision Tree visualizer, dan Pre-battle modal visualizer
"""

import sys
from .core import config, events, animation
from .ai import search, npc_config_csp, npc_config_optimizer, battle_ai, difficulty
from .battle import battle_system, battle_vfx, npc_squad
from .world import mapdata, player, npc
from .ui import overlay, tree_overlay, pre_battle_visualizer

# Backward compatibility alias agar script lama / scratch / laporan tetap bisa 'import game.xxx'
_compat_modules = {
    "game.config": config,
    "game.events": events,
    "game.animation": animation,
    "game.search": search,
    "game.npc_config_csp": npc_config_csp,
    "game.npc_config_optimizer": npc_config_optimizer,
    "game.battle_ai": battle_ai,
    "game.difficulty": difficulty,
    "game.battle_system": battle_system,
    "game.battle_vfx": battle_vfx,
    "game.npc_squad": npc_squad,
    "game.mapdata": mapdata,
    "game.player": player,
    "game.npc": npc,
    "game.overlay": overlay,
    "game.tree_overlay": tree_overlay,
    "game.pre_battle_visualizer": pre_battle_visualizer,
}

for _mod_name, _mod_obj in _compat_modules.items():
    sys.modules[_mod_name] = _mod_obj

__version__ = "1.0.0"
__all__ = [
    "core",
    "ai",
    "battle",
    "world",
    "ui",
    "config",
    "events",
    "animation",
    "search",
    "npc_config_csp",
    "npc_config_optimizer",
    "battle_ai",
    "difficulty",
    "battle_system",
    "battle_vfx",
    "npc_squad",
    "mapdata",
    "player",
    "npc",
    "overlay",
    "tree_overlay",
    "pre_battle_visualizer",
]
