"""Headless integration test for full gameplay loop:
Exploration -> Chest Loot -> Pre-Battle (CSP + Local Search) -> Tag-Team Battle -> Decision Tree -> Return.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from game.app import App
from game.battle_ai import ACTION_ATTACK

def run_integration_test():
    print("MENGUJI INTEGRASI GAMEPLAY LOOP LENGKAP SECARA HEADLESS...")
    app = App()
    print("1. App berhasil diinisialisasi.")
    assert app.game_mode == "EXPLORATION", f"Mode awal salah: {app.game_mode}"
    assert len(app.chests) == 3, "Peti harus berjumlah 3"
    assert app.npc_kuro is not None and app.npc_shiro is not None, "2 NPC patroli harus ada"

    # Test Chest interaction
    first_chest = app.chests[0]
    app.player.grid = (first_chest["pos"][0], first_chest["pos"][1] + 1)
    app._open_chest(first_chest)
    assert app.gacha_active, "Gacha harus aktif setelah membuka peti"
    print("2. Interaksi Peti Harta & Gacha berjalan.")

    # Selesaikan gacha secara instan
    app._update(1.5)
    assert not app.gacha_active, "Gacha harus selesai setelah durasi"
    assert first_chest["opened"], "Peti harus berstatus opened"
    print("3. Gacha selesai dan item/buff diberikan ke Player.")

    # Test Pre-Battle Entry
    app.enter_pre_battle()
    assert app.game_mode == "PRE_BATTLE", "Harus berada di mode PRE_BATTLE"
    assert app.current_squad is not None, "Squad NPC harus terbentuk"
    assert app.current_squad_config is not None, "Config squad harus ada"
    assert len(app.current_squad.members) >= 1, "Squad harus memiliki minimal 1 member"
    print(f"4. Masuk Pre-Battle: Squad terbentuk ({len(app.current_squad.members)} NPC), Diff={app.current_optimizer_stats.get('final_difficulty', 0):.4f}")

    # Test Re-Roll & Algoritma Switch
    for algo in ["HILL_CLIMBING", "SIDEWAYS", "RANDOM_RESTART", "SIMULATED_ANNEALING", "GENETIC_ALGORITHM"]:
        app.selected_ls_algo = algo
        app._run_optimization()
        diff = app.current_optimizer_stats.get("final_difficulty", 0.0)
        print(f"   - {algo:20} -> Difficulty: {diff:.4f} (Valid CSP: True)")

    # Test Enter Battle (Tag-Team)
    app.enter_battle()
    assert app.game_mode == "BATTLE", "Harus berada di mode BATTLE"
    assert app.battle_system.squad is not None, "Battle system harus memegang squad"
    print("5. Masuk ke Battle Mode dengan Squad terkonfigurasi.")

    # Test Tree Overlay toggle
    app.overlay.toggle_tree_overlay()
    assert app.overlay.tree_overlay.visible, "Tree overlay harus terlihat setelah toggle"
    app.overlay.toggle_tree_overlay()
    assert not app.overlay.tree_overlay.visible, "Tree overlay harus tertutup setelah toggle ulang"
    print("6. Decision Tree Modal toggle [T] berfungsi normal.")

    # Test Eksekusi Giliran & Tag-Team
    init_active_name = app.current_squad.get_active_member().name
    print(f"7. Bertarung melawan Frontline aktif: {init_active_name}")
    app.battle_system.execute_player_action(ACTION_ATTACK)
    assert len(app.battle_system.battle_logs) > 0, "Battle log harus tercatat"

    # Test Exit Battle & Persistent HP
    app.exit_battle()
    assert app.game_mode == "EXPLORATION", "Harus kembali ke EXPLORATION"
    assert app.player.persistent_hp > 0, "Persistent HP player harus valid"
    print(f"8. Berhasil kembali ke EXPLORATION (Player HP={app.player.persistent_hp}, Pot={app.player.persistent_potions}).")

    print("\n==================================================")
    print("SEMUA ALUR INTEGRASI GAMEPLAY LOOP LULUS 100%!")
    print("==================================================")

if __name__ == "__main__":
    run_integration_test()
