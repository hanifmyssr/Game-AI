"""Script untuk mengambil screenshot visual UI baru di semua state:
- Clean Look / Collapsed Drawer (hanya Nav Rail 64px, map panorama penuh)
- Expanded Drawer Cozy Journal (Tab 0 Hero, Tab 1 Search, Tab 4 Logic, Tab 5 Planning)
- Pre-Battle & Battle
- Unified Graph Modal (Decision Tree)
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from game.app import App
from game.ai.battle_ai import ACTION_ATTACK

ARTIFACT_DIR = r"C:\Users\Pavilion\.gemini\antigravity\brain\38f4bb8b-a421-4acf-b988-2e6d2a7fae0d"

def capture_ui_screenshots():
    app = App()
    
    # 1. Clean Look / Collapsed Drawer State
    app.overlay.dock.close()
    app._update(0.1)
    app._draw()
    path_clean = os.path.join(ARTIFACT_DIR, "ui_refactor_clean_look_collapsed.png")
    pygame.image.save(app.screen, path_clean)
    print("Saved Clean Look (Collapsed):", path_clean)

    # 2. Expanded Drawer - Tab 0 (Hero Companion & Inventory)
    app.overlay.dock.open()
    app.overlay.nav_rail.set_active_tab(0)
    app._update(0.1)
    app._draw()
    path_hero = os.path.join(ARTIFACT_DIR, "ui_refactor_expanded_hero.png")
    pygame.image.save(app.screen, path_hero)
    print("Saved Expanded Hero:", path_hero)

    # 3. Expanded Drawer - Tab 1 (Search Pathfinding)
    app.overlay.nav_rail.set_active_tab(1)
    app._update(0.1)
    app._draw()
    path_search = os.path.join(ARTIFACT_DIR, "ui_refactor_expanded_search.png")
    pygame.image.save(app.screen, path_search)
    print("Saved Expanded Search:", path_search)

    # 4. Open Chest & Check Pulse Badge on Tab 4 (Logic)
    chest = app.chests[0]
    app._open_chest(chest)
    app._update(1.2)
    app._draw()
    path_badge = os.path.join(ARTIFACT_DIR, "ui_refactor_pulse_badge.png")
    pygame.image.save(app.screen, path_badge)
    print("Saved Pulse Badge:", path_badge)

    # 5. Expanded Drawer - Tab 4 (Logic & Knowledge Base)
    app.overlay.nav_rail.set_active_tab(4)
    app._update(0.1)
    app._draw()
    path_logic = os.path.join(ARTIFACT_DIR, "ui_refactor_expanded_logic.png")
    pygame.image.save(app.screen, path_logic)
    print("Saved Expanded Logic:", path_logic)

    # 6. Expanded Drawer - Tab 5 (Automated Planning PDDL)
    app.overlay.nav_rail.set_active_tab(5)
    app._update(0.1)
    app._draw()
    path_planning = os.path.join(ARTIFACT_DIR, "ui_refactor_expanded_planning.png")
    pygame.image.save(app.screen, path_planning)
    print("Saved Expanded Planning:", path_planning)

    # 7. Pre-Battle Mode - Tab 3 (CSP & Local Search)
    app.enter_pre_battle()
    app.overlay.dock.open()
    app.overlay.nav_rail.set_active_tab(3)
    app._update(0.1)
    app._draw()
    path_prebattle = os.path.join(ARTIFACT_DIR, "ui_refactor_prebattle_cozy.png")
    pygame.image.save(app.screen, path_prebattle)
    print("Saved Pre-Battle Tab 3:", path_prebattle)

    # 8. Battle Mode - Tab 2 (Minimax AI)
    app.enter_battle()
    app.overlay.dock.open()
    app.overlay.nav_rail.set_active_tab(2)
    app._update(0.1)
    app._draw()
    path_battle = os.path.join(ARTIFACT_DIR, "ui_refactor_battle_cozy.png")
    pygame.image.save(app.screen, path_battle)
    print("Saved Battle Tab 2:", path_battle)

    # 9. Unified Graph Modal (Decision Tree)
    app.battle_system.execute_player_action(ACTION_ATTACK)
    app.battle_system.execute_npc_turn()
    app.overlay.toggle_tree_overlay()
    app._update(0.1)
    app._draw()
    path_tree = os.path.join(ARTIFACT_DIR, "ui_refactor_tree_modal.png")
    pygame.image.save(app.screen, path_tree)
    print("Saved Unified Graph Modal:", path_tree)

if __name__ == "__main__":
    capture_ui_screenshots()
