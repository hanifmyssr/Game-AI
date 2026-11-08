"""Capture visual screenshots for Tahap 4:
- Tab 4 (Logic KB)
- Tab 5 (Automated Planning PDDL)
- Logic Overlay [K]
- Planning Overlay [P]
- Graph Modal LOGIC Proof Tree [T]
- Graph Modal PLANNING Tree [T]
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from game.app import App

ARTIFACT_DIR = r"C:\Users\Pavilion\.gemini\antigravity\brain\38f4bb8b-a421-4acf-b988-2e6d2a7fae0d"


def capture_tahap4():
    app = App()

    # Buka Peti A untuk memicu TELL & ASK logika dan perencanaan PDDL
    chest_a = app.chests[0]
    app._open_chest(chest_a)
    app._update(0.1)

    # 1. Expanded Drawer - Tab 4 (Logic & KB)
    app.overlay.dock.open()
    app.overlay.nav_rail.set_active_tab(4)
    app._update(0.05)
    app._draw()
    path_tab4 = os.path.join(ARTIFACT_DIR, "tahap4_tab4_logic_live.png")
    pygame.image.save(app.screen, path_tab4)
    print("Saved Tab 4 Logic Live:", path_tab4)

    # 2. Expanded Drawer - Tab 5 (Planning PDDL)
    app.overlay.nav_rail.set_active_tab(5)
    app._update(0.05)
    app._draw()
    path_tab5 = os.path.join(ARTIFACT_DIR, "tahap4_tab5_planning_live.png")
    pygame.image.save(app.screen, path_tab5)
    print("Saved Tab 5 Planning Live:", path_tab5)

    # 3. Logic Overlay [K]
    app.overlay.dock.close()
    app.logic_overlay.visible = True
    app._update(0.05)
    app._draw()
    path_k = os.path.join(ARTIFACT_DIR, "tahap4_logic_overlay_k.png")
    pygame.image.save(app.screen, path_k)
    print("Saved Logic Overlay [K]:", path_k)
    app.logic_overlay.visible = False

    # 4. Planning Overlay [P]
    app.planning_overlay.visible = True
    app._update(0.05)
    app._draw()
    path_p = os.path.join(ARTIFACT_DIR, "tahap4_planning_overlay_p.png")
    pygame.image.save(app.screen, path_p)
    print("Saved Planning Overlay [P]:", path_p)
    app.planning_overlay.visible = False

    # 5. Graph Modal - LOGIC Resolution Tree
    app.open_graph_modal("LOGIC")
    app._update(0.05)
    app._draw()
    path_tree_logic = os.path.join(ARTIFACT_DIR, "tahap4_tree_logic_refutation.png")
    pygame.image.save(app.screen, path_tree_logic)
    print("Saved Tree Logic Refutation:", path_tree_logic)
    app.open_graph_modal("LOGIC")  # Close

    # 6. Graph Modal - PLANNING PDDL Tree
    app.open_graph_modal("PLANNING")
    app._update(0.05)
    app._draw()
    path_tree_plan = os.path.join(ARTIFACT_DIR, "tahap4_tree_planning_pddl.png")
    pygame.image.save(app.screen, path_tree_plan)
    print("Saved Tree Planning PDDL:", path_tree_plan)
    app.open_graph_modal("PLANNING")  # Close


if __name__ == "__main__":
    capture_tahap4()

