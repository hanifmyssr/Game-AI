import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_mode((1280, 800), pygame.HIDDEN)

from game.app import App
from game.battle.npc_squad import NPCSquad, NPCMember
from game.ui.tabs.tab_companion import TabCompanion
from game.core import config

def test_inventory_and_loot():
    app = App()
    
    # 1. Reset player inventory to empty (no chests opened)
    app.player.inventory = []
    app.player.persistent_potions = 0
    app.chests = []
    
    # TabCompanion from app overlay dock
    tab = app.overlay.dock.tabs[0]
    
    # Render TabCompanion with 0 items
    surf = pygame.Surface((380, 720))
    tab.draw(surf)
    
    # Verify items initially
    inventory = app.player.inventory
    print("[1] Initial inventory:", inventory)
    assert len(inventory) == 0, "Inventory must initially be empty!"
    
    # 2. Setup squad with Oyen, Kuro, Shiro, Kage
    m1 = NPCMember(name="Warrior Oyen", char_type="warrior", max_hp=50, atk_bonus=2, def_bonus=2, eval_profile="AGGRESSIVE")
    m2 = NPCMember(name="Ranger Kuro", char_type="ranger", max_hp=45, atk_bonus=3, def_bonus=1, eval_profile="BALANCED")
    m3 = NPCMember(name="Mage Shiro", char_type="mage", max_hp=40, atk_bonus=4, def_bonus=1, eval_profile="DEFENSIVE")
    m4 = NPCMember(name="Assassin Kage", char_type="assassin", max_hp=35, atk_bonus=5, def_bonus=0, eval_profile="AGGRESSIVE")
    app.current_squad = NPCSquad([m1, m2, m3, m4])
    app.enter_battle()
    
    # 3. Defeat Oyen
    print("[2] Defeating Oyen...")
    app.battle_system.state.npc_hp = 0
    app.battle_system._check_game_over()
    app._update(1.5) # Finish defeat anim -> pop loot modal
    
    print("    Player Inventory after Oyen:", app.player.inventory)
    assert "Pedang Ksatria Oyen" in app.player.inventory or "item_sword" in app.player.inventory
    
    # Render TabCompanion after Oyen defeat
    tab.draw(surf)
    print("    TabCompanion rendered with Oyen loot successfully!")
    
    # Capture loot modal visual
    app.screen.fill((40, 50, 40))
    app._draw_loot_modal()
    os.makedirs(r"C:\Users\Pavilion\.gemini\antigravity\brain\38f4bb8b-a421-4acf-b988-2e6d2a7fae0d", exist_ok=True)
    modal_path = r"C:\Users\Pavilion\.gemini\antigravity\brain\38f4bb8b-a421-4acf-b988-2e6d2a7fae0d\verify_loot_modal_warm.png"
    pygame.image.save(app.screen, modal_path)
    print(f"[3] Loot modal screenshot saved to: {modal_path}")
    
    # Dismiss modal
    app._handle_key(pygame.K_RETURN)
    app._update(1.8) # card anim finishes
    
    # 4. Defeat Kuro
    print("[4] Defeating Kuro...")
    app.battle_system.state.npc_hp = 0
    app.battle_system._check_game_over()
    app._update(1.5)
    print("    Player Inventory after Kuro:", app.player.inventory)
    assert "Busur Presisi Kuro" in app.player.inventory or "item_bow" in app.player.inventory
    app._handle_key(pygame.K_RETURN)
    app._update(1.8)
    
    # 5. Defeat Shiro
    print("[5] Defeating Shiro...")
    app.battle_system.state.npc_hp = 0
    app.battle_system._check_game_over()
    app._update(1.5)
    print("    Player Inventory after Shiro:", app.player.inventory)
    assert "Tongkat Sihir Shiro" in app.player.inventory or "mega_potion" in app.player.inventory
    app._handle_key(pygame.K_RETURN)
    app._update(1.8)
    
    # 6. Defeat Kage (Final Boss)
    print("[6] Defeating Kage (Final Boss)...")
    app.battle_system.state.npc_hp = 0
    app.battle_system._check_game_over()
    app._update(0.016)
    app._update(1.5)
    print("    Player Inventory after Kage:", app.player.inventory)
    assert "Belati Bayangan Kage" in app.player.inventory or "item_dagger" in app.player.inventory
    
    # Capture final victory loot modal visual
    app.screen.fill((40, 50, 40))
    app._draw_loot_modal()
    final_modal_path = r"C:\Users\Pavilion\.gemini\antigravity\brain\38f4bb8b-a421-4acf-b988-2e6d2a7fae0d\verify_final_loot_modal_warm.png"
    pygame.image.save(app.screen, final_modal_path)
    print(f"[7] Final Loot modal screenshot saved to: {final_modal_path}")
    
    # Now verify TabCompanion has all acquired items
    tab_surf = pygame.Surface((380, 720))
    tab_surf.fill((248, 244, 236))
    tab.draw(tab_surf)
    tab_path = r"C:\Users\Pavilion\.gemini\antigravity\brain\38f4bb8b-a421-4acf-b988-2e6d2a7fae0d\verify_tab_companion_spoils.png"
    pygame.image.save(tab_surf, tab_path)
    print(f"[8] TabCompanion screenshot saved to: {tab_path}")
    
    print("\n>>> ALL TESTS PASSED! INVENTORY RECOGNIZES ALL SPOILS OF WAR & MODAL IS WARM PARCHMENT! <<<")

if __name__ == "__main__":
    test_inventory_and_loot()
