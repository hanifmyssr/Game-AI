import os
import pygame
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
screen = pygame.display.set_mode((1280, 800))

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.app import App
from game.npc_squad import NPCSquad, NPCMember

app = App()

# Test 1: Exploration overlay
app.game_mode = "EXPLORATION"
# populate comparison data
app.overlay.set_comparison_data({
    "cur_cost": 15.0,
    "ucs_expanded": 84,
    "ucs_time_ms": 1.25,
    "ucs_cost": 15.0,
    "cur_expanded": 32,
    "cur_time_ms": 0.45,
    "cur_label": "A* (Manhattan)",
})
app.overlay.update_stats(32, 0.45)

screen.fill((50, 50, 50))
app.overlay.draw_ui(screen)
pygame.image.save(screen, "scratch/current_exploration_overlay.png")

# Test 2: Pre-Battle overlay
app.game_mode = "PRE_BATTLE"
app.overlay.set_mode("PRE_BATTLE")
app.overlay.set_pre_battle_data(
    config_dict={
        "members": [
            {"char_type": "warrior", "hp": 100, "potions": 2, "atk_bonus": 10, "def_bonus": 4, "eval_profile": "BALANCED"},
            {"char_type": "ranger", "hp": 80, "potions": 1, "atk_bonus": 10, "def_bonus": 2, "eval_profile": "AGGRESSIVE"},
            {"char_type": "mage", "hp": 70, "potions": 2, "atk_bonus": 5, "def_bonus": 0, "eval_profile": "DEFENSIVE"},
        ]
    },
    stats={
        "final_difficulty": 0.5512,
        "final_fitness": 0.0012,
        "iterations": 18,
        "time_ms": 4.12,
    },
    algo_name="HILL_CLIMBING"
)
screen.fill((50, 50, 50))
app.overlay.draw_ui(screen)
pygame.image.save(screen, "scratch/current_prebattle_overlay.png")

# Test 2B: Fullscreen Pre-Battle Arena
app.game_mode = "PRE_BATTLE"
app.current_squad = NPCSquad([
    NPCMember(name="Oyen the Warrior", char_type="warrior", max_hp=100, current_hp=100, potions=2, atk_bonus=15, def_bonus=6, eval_profile="BALANCED"),
    NPCMember(name="Kuro the Ranger", char_type="ranger", max_hp=80, current_hp=80, potions=1, atk_bonus=10, def_bonus=2, eval_profile="AGGRESSIVE"),
    NPCMember(name="Shiro the Mage", char_type="mage", max_hp=70, current_hp=70, potions=2, atk_bonus=5, def_bonus=0, eval_profile="DEFENSIVE"),
])
app._draw()
pygame.image.save(screen, "scratch/current_prebattle_fullscreen.png")

# Test 3: Battle overlay
app.game_mode = "BATTLE"
app.overlay.set_mode("BATTLE")
from game.npc_squad import NPCSquad, NPCMember
squad = NPCSquad([
    NPCMember(name="Oyen the Warrior", char_type="warrior", max_hp=100, current_hp=100, potions=1, atk_bonus=5, def_bonus=5, eval_profile="BALANCED"),
    NPCMember(name="Kuro the Ranger", char_type="ranger", max_hp=80, current_hp=80, potions=1, atk_bonus=10, def_bonus=0, eval_profile="BALANCED"),
])
app.current_squad = squad
app.battle_system.reset_with_squad(squad, player=app.player)
app.battle_system.last_ai_stats = {
    "node_count": 48,
    "pruned_count": 12,
    "time_ms": 1.85,
    "best_action": "ATTACK",
    "best_score": 14.5,
    "algorithm": "ALPHA_BETA",
    "comparison": {
        "minimax_nodes": 128,
        "alphabeta_nodes": 48,
        "expectimax_nodes": 64,
        "savings_pct": 62.5,
        "depth": 4,
        "deterministic_scores": {"ATTACK": 14.5, "HEAVY_ATTACK": 12.0, "DEFEND": 8.5, "POTION": 2.0},
        "expectimax_scores": {"ATTACK": 14.5, "HEAVY_ATTACK": 11.2, "DEFEND": 8.5, "POTION": 2.0},
    },
    "action_scores": {"ATTACK": 14.5, "HEAVY_ATTACK": 12.0, "DEFEND": 8.5, "POTION": 2.0},
}
screen.fill((50, 50, 50))
app.overlay.draw_ui(screen)
pygame.image.save(screen, "scratch/current_battle_overlay.png")

# Test 4: Battle Defeat state
app.npc_defeat_anim = {
    "npc": squad.members[0],
    "next_npc": squad.members[1],
    "heal_amount": 45,
    "loot": {"name": "Pedang Ksatria Oyen", "desc": "+5 ATK, +5 DEF", "color": (255, 215, 60), "stat_text": "+5 ATK, +5 DEF"},
    "timer": 1.2,
    "duration": 1.4,
    "is_final": False,
}
app._draw()
pygame.image.save(screen, "scratch/current_battle_defeat_state.png")

print("Saved all overlay & arena screenshots.")
