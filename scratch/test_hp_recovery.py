import os
import sys

sys.path.insert(0, os.path.abspath("."))
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_mode((1024, 768))

from game.app import App
from game.npc_squad import NPCSquad, NPCMember

print("=== RUNNING TEST HP RECOVERY ===")
app = App()

# Buat squad untuk duel
squad = NPCSquad([
    NPCMember("Oyen the Warrior", "warrior", max_hp=50, current_hp=50),
    NPCMember("Kage the Assassin", "assassin", max_hp=65, current_hp=65),
])
app.current_squad = squad
app.enter_battle()

print("\n--- SKENARIO 1: Player Kalah, Exit Battle, lalu Masuk Battle Lagi ---")
# Simulasikan Player Kalah (HP = 0)
app.battle_system.state.player_hp = 0
app.battle_system._check_game_over()
print(f"Battle finished: {app.battle_system.is_finished}, Winner: {app.battle_system.winner}")
assert app.battle_system.winner == "NPC", "NPC should be the winner"

# Player keluar ke mode map (exit_battle)
app.exit_battle()
print(f"Mode setelah keluar: {app.game_mode}")
print(f"Player persistent HP di map: {app.player.persistent_hp}")
assert app.player.persistent_hp == 100, f"Expected 100 HP, got {app.player.persistent_hp}"

# Player masuk ke pre-battle lagi
app.enter_pre_battle()
print(f"Player persistent HP di pre-battle: {app.player.persistent_hp}")
assert app.player.persistent_hp == 100, f"Expected 100 HP, got {app.player.persistent_hp}"

# Player masuk ke duel lagi
app.enter_battle()
print(f"Player HP di duel baru: {app.battle_system.state.player_hp}")
assert app.battle_system.state.player_hp == 100, f"Expected 100 HP, got {app.battle_system.state.player_hp}"
print("=> SKENARIO 1 BERHASIL! (HP Full 100)")

print("\n--- SKENARIO 2: Player Kalah, lalu Tekan [R] untuk Reset/Refresh di Battle Mode ---")
# Buat player kalah lagi
app.battle_system.state.player_hp = 0
app.battle_system._check_game_over()
print(f"Player HP saat ini: {app.battle_system.state.player_hp}")

# Simulasikan tombol [R] (K_r)
app._handle_key(pygame.K_r)
print(f"Setelah tekan R:")
print(f"Player HP di duel: {app.battle_system.state.player_hp}")
print(f"Player persistent HP: {app.player.persistent_hp}")
print(f"Active squad index: {app.current_squad.active_index}")
print(f"Active NPC: {app.current_squad.get_active_member().name} (HP: {app.current_squad.get_active_member().current_hp})")

assert app.battle_system.state.player_hp == 100, f"Expected 100 HP, got {app.battle_system.state.player_hp}"
assert app.current_squad.active_index == 0, f"Expected squad index 0, got {app.current_squad.active_index}"
assert app.current_squad.get_active_member().current_hp == app.current_squad.get_active_member().max_hp, "NPC HP should be fully restored"
print("=> SKENARIO 2 BERHASIL! (HP Full 100 & Squad Reset)")

print("\nSEMUA PENGUJIAN PEMULIHAN HP BERHASIL 100%!")
