import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_mode((1280, 800), pygame.HIDDEN)

from game.app import App
from game.core import config

def capture_overlays():
    app = App()
    brain_dir = r"C:\Users\Pavilion\.gemini\antigravity\brain\38f4bb8b-a421-4acf-b988-2e6d2a7fae0d"
    os.makedirs(brain_dir, exist_ok=True)
    
    # 1. Logic Overlay [K]
    app.logic_overlay.visible = True
    app.planning_overlay.visible = False
    app.overlay.graph_modal.visible = False
    app._draw()
    path_logic = os.path.join(brain_dir, "verify_logic_overlay.png")
    pygame.image.save(app.screen, path_logic)
    print(f"[1] Saved {path_logic}")
    
    # 2. Planning Overlay [P]
    app.logic_overlay.visible = False
    app.planning_overlay.visible = True
    app.overlay.graph_modal.visible = False
    app._draw()
    path_plan = os.path.join(brain_dir, "verify_planning_overlay.png")
    pygame.image.save(app.screen, path_plan)
    print(f"[2] Saved {path_plan}")
    
    # 3. Graph Modal for Logic
    app.logic_overlay.visible = False
    app.planning_overlay.visible = False
    app.open_graph_modal("LOGIC")
    app._draw()
    path_g_logic = os.path.join(brain_dir, "verify_graph_modal_logic.png")
    pygame.image.save(app.screen, path_g_logic)
    print(f"[3] Saved {path_g_logic}")
    
    # 4. Graph Modal for Planning
    app.open_graph_modal("PLANNING")
    app._draw()
    path_g_plan = os.path.join(brain_dir, "verify_graph_modal_planning.png")
    pygame.image.save(app.screen, path_g_plan)
    print(f"[4] Saved {path_g_plan}")
    
    # 5. Tactical Plan Banner in Battle Mode
    from game.battle.npc_squad import NPCSquad, NPCMember
    m1 = NPCMember(name="Warrior Oyen", char_type="warrior", max_hp=50, atk_bonus=2, def_bonus=2, eval_profile="AGGRESSIVE")
    m2 = NPCMember(name="Ranger Kuro", char_type="ranger", max_hp=45, atk_bonus=3, def_bonus=1, eval_profile="BALANCED")
    m3 = NPCMember(name="Mage Shiro", char_type="mage", max_hp=40, atk_bonus=4, def_bonus=1, eval_profile="DEFENSIVE")
    app.current_squad = NPCSquad([m1, m2, m3])
    app.enter_battle()
    app.overlay.graph_modal.visible = False
    app.battle_system._execute_tactical_planning_turn(m1, [m2, m3])
    app._draw()
    path_banner = os.path.join(brain_dir, "verify_tactical_banner.png")
    pygame.image.save(app.screen, path_banner)
    print(f"[5] Saved {path_banner}")
    
    # 6. Tab 4 (Logic) and Tab 5 (Planning) in Inspector Dock
    app.exit_battle()
    app.overlay.dock.open()
    app.overlay.dock.set_active_tab(4)
    app._draw()
    path_tab_logic = os.path.join(brain_dir, "verify_dock_tab_logic.png")
    pygame.image.save(app.screen, path_tab_logic)
    print(f"[6] Saved {path_tab_logic}")
    
    app.overlay.dock.set_active_tab(5)
    app._draw()
    path_tab_plan = os.path.join(brain_dir, "verify_dock_tab_planning.png")
    pygame.image.save(app.screen, path_tab_plan)
    print(f"[7] Saved {path_tab_plan}")
    
    print("\nALL OVERLAYS CAPTURED SUCCESSFULLY!")

if __name__ == "__main__":
    capture_overlays()

