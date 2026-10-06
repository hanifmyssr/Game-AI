"""Pengujian Khusus Layout Battle Mode & Kartu Skuad Cadangan."""
import os
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1200, 800))

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.app import App
from game.npc_squad import NPCSquad, NPCMember

def test_battle_layout():
    app = App()
    
    # 2. Setup squad dengan 3 anggota (Oyen, Kuro, Shiro)
    squad = NPCSquad([
        NPCMember(name="Oyen", char_type="warrior", max_hp=100, current_hp=100, potions=1, atk_bonus=10, def_bonus=5, eval_profile="BALANCED"),
        NPCMember(name="Kuro", char_type="ranger", max_hp=80, current_hp=80, potions=0, atk_bonus=15, def_bonus=0, eval_profile="AGGRESSIVE"),
        NPCMember(name="Shiro", char_type="mage", max_hp=60, current_hp=60, potions=2, atk_bonus=5, def_bonus=2, eval_profile="MINIMAX"),
    ])
    app.current_squad = squad
    app.battle_system.reset_with_squad(squad, player=app.player)
    app.game_mode = "BATTLE"

    p_pos, n_pos = app._get_battle_char_positions()
    print(f"Dengan Squad -> Player pos: {p_pos}, NPC pos: {n_pos}")
    assert p_pos[1] >= 280, f"Posisi char_y ({p_pos[1]}) harus berada di tengah arena (>= 280)!"
    assert n_pos[1] == p_pos[1], "Tinggi y Player dan NPC harus sama!"
    assert p_pos[0] < n_pos[0], "Player di sebelah kiri NPC!"
    assert n_pos[0] < (1200 - 240 - 14), "NPC tidak boleh menabrak kartu cadangan!"
    
    # 3. Render frame awal duel (Oyen aktif, Kuro & Shiro cadangan)
    app.screen.fill((0, 0, 0))
    app._draw_battle_arena()
    screenshot_1 = "scratch/test_battle_frame_1.png"
    pygame.image.save(app.screen, screenshot_1)
    print(f"Frame 1 berhasil disimpan ke {screenshot_1}")
    
    # 4. Simulasikan kekalahan Oyen dan pergantian ke Kuro
    squad.members[0].current_hp = 0
    app.battle_system.state.npc_hp = 0
    app.battle_system._check_game_over()
    
    assert squad.active_index == 1, f"Active index harus 1 (Kuro), didapat: {squad.active_index}"
    assert squad.get_active_member().name == "Kuro", "Kuro harus menjadi active member"
    
    # 5. Render frame kedua duel (Oyen gugur, Kuro aktif, Shiro cadangan)
    app.screen.fill((0, 0, 0))
    app._draw_battle_arena()
    screenshot_2 = "scratch/test_battle_frame_2.png"
    pygame.image.save(app.screen, screenshot_2)
    print(f"Frame 2 berhasil disimpan ke {screenshot_2}")

    print("Semua tes layout battle dan rotasi kartu NPC cadangan LULUS 100%!")

if __name__ == "__main__":
    test_battle_layout()
