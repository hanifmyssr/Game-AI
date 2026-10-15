import os
import sys

sys.path.insert(0, os.path.abspath("."))
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_mode((1024, 768))

from game.app import App
from game.npc_squad import NPCSquad, NPCMember

app = App()

# Buat squad untuk demonstrasi visual
squad = NPCSquad([
    NPCMember("Oyen the Warrior", "warrior", max_hp=50, current_hp=50),
    NPCMember("Kage the Assassin", "assassin", max_hp=65, current_hp=65),
    NPCMember("Shiro the Mage", "mage", max_hp=60, current_hp=60),
])

app.current_squad = squad
app.enter_battle()

# Habisi NPC pertama
app.battle_system.state.npc_hp = 10
app.battle_system.execute_player_action("ATTACK")

dt = 0.02
cur_time = 0.0

snapshots = {
    0.35: "scratch/summon_phase1_flying.png",
    0.95: "scratch/summon_phase2_charging.png",
    1.25: "scratch/summon_phase3_burst_reveal.png",
    1.55: "scratch/summon_phase4_landing.png",
}

captured = set()

while cur_time <= 1.8:
    app._update(dt)
    app.screen.fill((20, 20, 30))
    app._draw_battle_arena()
    cur_time += dt

    for target_t, out_path in snapshots.items():
        if target_t not in captured and cur_time >= target_t:
            pygame.image.save(app.screen, out_path)
            captured.add(target_t)
            print(f"Captured snapshot at t={cur_time:.2f}s -> {out_path}")

print("All snapshots captured successfully!")
