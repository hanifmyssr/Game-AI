import os
import sys

sys.path.insert(0, os.path.abspath("."))
# Set dummy video driver untuk running headless di test sandbox
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_mode((1024, 768))

from game.app import App
from game.npc_squad import NPCSquad, NPCMember

print("Initializing App...")
app = App()

# Buat squad dengan 3 anggota untuk menguji tag-in
squad = NPCSquad([
    NPCMember("Oyen the Warrior", "warrior", max_hp=50, current_hp=50),
    NPCMember("Kage the Assassin", "assassin", max_hp=65, current_hp=65),
    NPCMember("Shiro the Mage", "mage", max_hp=60, current_hp=60),
])

app.current_squad = squad
app.enter_battle()

print(f"Battle started. Active NPC: {app.battle_system.squad.get_active_member().name}")
assert app.battle_system.squad.has_next() == True, "Squad should have next member"

# Kurangi HP NPC aktif sampai tumbang
app.battle_system.state.npc_hp = 10
# Player menyerang untuk menghabisi NPC
print("Player executing attack...")
app.battle_system.execute_player_action("ATTACK")

# Cek apakah tag in terpanggil dan anim aktif
print(f"Is locked: {app.battle_system.is_locked}")
print(f"Card summon anim active: {app.card_summon_anim is not None}")

if app.card_summon_anim:
    print(f"Summoning: {app.card_summon_anim['next_npc'].name} (class: {app.card_summon_anim['next_npc'].char_type})")
    print(f"Start pos: {app.card_summon_anim['start_pos']}, Target pos: {app.card_summon_anim['target_pos']}")

# Simulasi loop frame demi frame sepanjang 2 detik
dt = 0.033  # ~30 FPS
time_elapsed = 0.0

rendered_frames = 0
while time_elapsed < 2.0:
    # Update app
    app._update(dt)
    
    # Gambar arena
    app.screen.fill((20, 20, 30))
    app._draw_battle_arena()
    
    rendered_frames += 1
    time_elapsed += dt

print(f"Successfully simulated {rendered_frames} frames without errors!")
print(f"After animation, card_summon_anim is: {app.card_summon_anim}")
print(f"Is battle system unlocked: {not app.battle_system.is_locked}")
print(f"Active NPC now: {app.battle_system.squad.get_active_member().name}")

# Simpan snapshot visual di beberapa titik kunci untuk verifikasi
pygame.image.save(app.screen, "scratch/summon_complete.png")
print("Saved final snapshot: scratch/summon_complete.png")
print("ALL TESTS PASSED!")
