import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_mode((1280, 800), pygame.HIDDEN)

from game.app import App
from game.battle.npc_squad import NPCSquad, NPCMember

def test_battle_exit_and_no_chase():
    print("=== TESTING BATTLE EXIT & POST-BATTLE CHASE RESET ===")
    app = App()
    
    # 1. Player opens Chest A -> Triggers chase via InterNPCManager (Materi 07)
    chest_a = app.chests[0]
    app._open_chest(chest_a)
    print(f"[1] Chest A opened: Percept={app.inter_npc_manager.latest_percept_event}")
    print(f"    Chaser assigned in KB: {app.inter_npc_manager.chaser_assigned}")
    print(f"    Kuro chasing: {app.npc_kuro.chasing}, Oyen chasing: {app.npc.chasing}")
    assert app.npc_kuro.chasing or app.npc.chasing, "At least one NPC should be chasing after chest opened!"
    
    # 2. Transition to Battle Mode
    app.current_encounter_npc = app.npc_kuro if app.npc_kuro.chasing else app.npc
    app.enter_battle()
    assert app.game_mode == "BATTLE", "Game should be in BATTLE mode"
    print(f"[2] Entered battle mode against {app.current_encounter_npc.name}")
    
    # Render and check exit button hitbox
    app._draw()
    assert hasattr(app, "btn_battle_exit"), "app should have btn_battle_exit"
    assert app.btn_battle_exit.width > 0 and app.btn_battle_exit.height > 0, "btn_battle_exit should have valid rect"
    print(f"    Exit button rect: {app.btn_battle_exit}")
    
    # Save visual screenshot of battle screen with exit button
    brain_dir = r"C:\Users\Pavilion\.gemini\antigravity\brain\38f4bb8b-a421-4acf-b988-2e6d2a7fae0d"
    os.makedirs(brain_dir, exist_ok=True)
    shot_path = os.path.join(brain_dir, "verify_battle_with_exit_btn.png")
    pygame.image.save(app.screen, shot_path)
    print(f"    Saved battle screenshot to: {shot_path}")
    
    # 3. Simulate clicking the Exit Button
    click_pos = app.btn_battle_exit.center
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": click_pos, "button": 1})
    pygame.event.post(event)
    app._handle_events()
    
    # Verify exit from battle
    assert app.game_mode == "EXPLORATION", f"Expected EXPLORATION, got {app.game_mode}"
    print("[3] Clicked exit button -> Successfully returned to EXPLORATION mode!")
    
    # 4. Verify that NO NPC is chasing anymore!
    print("[4] Checking post-battle chasing states:")
    print(f"    Oyen chasing: {app.npc.chasing}")
    print(f"    Kuro chasing: {app.npc_kuro.chasing}")
    print(f"    Shiro chasing: {app.npc_shiro.chasing}")
    assert not app.npc.chasing, "Oyen should NOT be chasing!"
    assert not app.npc_kuro.chasing, "Kuro should NOT be chasing!"
    assert not app.npc_shiro.chasing, "Shiro should NOT be chasing!"
    
    # Verify KB facts and manager
    print(f"    InterNPCManager chaser_assigned: {app.inter_npc_manager.chaser_assigned}")
    assert app.inter_npc_manager.chaser_assigned is None, "chaser_assigned should be None!"
    assert "HasLootedItem_Player" not in app.inter_npc_manager.kb.facts, "HasLootedItem_Player should be retracted!"
    print("    HasLootedItem_Player successfully retracted from Knowledge Base!")
    
    # 5. Move player and verify NPCs do NOT chase player
    old_oyen_grid = app.npc.grid
    old_kuro_grid = app.npc_kuro.grid
    old_shiro_grid = app.npc_shiro.grid
    
    # Player moves 5 steps
    for step in range(5):
        app.player.try_move((1, 0))
        app._update(0.1)
    
    print("[5] Player moved 5 steps in exploration mode:")
    print(f"    Oyen grid before={old_oyen_grid}, after={app.npc.grid}, chasing={app.npc.chasing}")
    print(f"    Kuro grid before={old_kuro_grid}, after={app.npc_kuro.grid}, chasing={app.npc_kuro.chasing}")
    print(f"    Shiro grid before={old_shiro_grid}, after={app.npc_shiro.grid}, chasing={app.npc_shiro.chasing}")
    assert not app.npc.chasing, "Oyen still not chasing"
    assert not app.npc_kuro.chasing, "Kuro still not chasing"
    assert not app.npc_shiro.chasing, "Shiro still not chasing"
    
    print("\n[6] Testing battle completion by victory:")
    app.gacha_active = False
    app._open_chest(app.chests[1])
    assert app.npc_kuro.chasing or app.npc.chasing
    app.current_encounter_npc = app.npc
    app.enter_battle()
    assert app.game_mode == "BATTLE"
    
    # Simulate player winning by dealing lethal damage
    app.battle_system.state.npc_hp = 0
    app.battle_system.is_finished = True
    app.battle_system.winner = "PLAYER"
    app.exit_battle()
    
    assert app.game_mode == "EXPLORATION"
    assert not app.npc.chasing, "Oyen should not chase after battle victory"
    assert not app.npc_kuro.chasing, "Kuro should not chase after battle victory"
    assert not app.npc_shiro.chasing, "Shiro should not chase after battle victory"
    print("    Post-victory chasing states: All False, perfectly peaceful!")

    print("\n>>> ALL TESTS PASSED! BATTLE EXIT BUTTON & CHASE RESET WORK 100% PERFECTLY! <<<")

if __name__ == "__main__":
    test_battle_exit_and_no_chase()
