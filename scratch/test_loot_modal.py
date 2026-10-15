import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Headless pygame setup
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_mode((1280, 720), pygame.HIDDEN)

from game.app import App
from game.npc_squad import NPCSquad, NPCMember
from game import config

def test_loot_modal_flow():
    app = App()
    
    # Setup dummy squad: 2 members (Warrior & Ranger)
    m1 = NPCMember(name="Warrior Oyen", char_type="warrior", max_hp=50, atk_bonus=2, def_bonus=2, eval_profile="AGGRESSIVE")
    m2 = NPCMember(name="Ranger Kuro", char_type="ranger", max_hp=45, atk_bonus=3, def_bonus=1, eval_profile="BALANCED")
    squad = NPCSquad([m1, m2])
    
    app.current_squad = squad
    app.enter_battle()
    
    print("[1] In battle mode. Loot modal:", app.loot_modal)
    assert app.loot_modal is None, "loot_modal should initially be None"
    assert app.card_summon_anim is None, "card_summon_anim should initially be None"
    
    # Simulate defeating member 1:
    # Trigger tag-in via battle system
    print("[2] Simulating defeat of NPC 1...")
    app.battle_system.state.npc_hp = 0
    app.battle_system._check_game_over()
    
    # Check that loot modal is active and battle is locked
    print("[3] After NPC 1 defeat:")
    assert app.loot_modal is not None, "loot_modal MUST be populated!"
    assert app.battle_system.is_locked, "Battle system MUST be locked while loot modal is displayed!"
    assert app.card_summon_anim is None, "Next NPC card animation MUST NOT start before player confirms loot!"
    
    loot_data = app.loot_modal["loot"]
    print("    Loot Name:", loot_data["name"])
    print("    Loot Stat:", loot_data["stat_text"])
    print("    Loot Image Key:", loot_data["image_key"])
    print("    Next NPC:", app.loot_modal["next_npc"].name)
    
    # Test drawing the loot modal (ensure no render errors)
    app._draw_loot_modal()
    print("[4] _draw_loot_modal rendered successfully!")
    
    # Now simulate player pressing ENTER to continue
    print("[5] Player presses ENTER...")
    app._handle_key(pygame.K_RETURN)
    
    # Modal should be dismissed, and card summon animation should now start
    assert app.loot_modal is None, "loot_modal should be dismissed after pressing ENTER!"
    assert app.card_summon_anim is not None, "Next NPC card summon animation should start immediately after dismissal!"
    print("    card_summon_anim is active for:", app.card_summon_anim["next_npc"].name)
    
    # Simulate time passing to complete the card summon animation
    app._update_card_summon_anim(1.8) # > duration of 1.75
    assert app.card_summon_anim is None, "card_summon_anim should finish"
    assert not app.battle_system.is_locked, "battle_system should now be unlocked for duel with next NPC"
    print("[6] Tag-in animation completed, duel resumes with next challenger!")

    # Test 7: Defeat the final NPC (Ranger Kuro) and verify final victory loot modal
    print("[7] Simulating defeat of final NPC (Ranger Kuro)...")
    app.battle_system.state.npc_hp = 0
    app.battle_system._check_game_over()
    assert app.battle_system.is_finished, "Battle must be finished!"
    assert app.battle_system.winner == "PLAYER", "Player must be winner!"
    
    # Run _update to let victory trigger the modal
    app._update(0.016)
    assert app.loot_modal is not None, "Final victory loot modal must be active!"
    assert app.loot_modal["is_final"] is True, "is_final must be True for final victory modal!"
    print("    Final Victory Loot:", app.loot_modal["loot"]["name"])
    
    # Test dismissal via MOUSEBUTTONDOWN
    print("[8] Simulating mouse click to dismiss final loot modal...")
    click_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (640, 360), "button": 1})
    pygame.event.post(click_event)
    app._handle_events()
    assert app.loot_modal is None, "loot_modal should be dismissed after mouse click!"
    print("    Final victory modal dismissed successfully via mouse click!")
    
    print("\n>>> ALL LOOT MODAL & TAG-IN FLOW TESTS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    test_loot_modal_flow()
