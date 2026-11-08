"""Test and verify that sliding / panning the decision tree in battle mode does NOT crash the game.
Tests:
1. Opening tree overlay in Battle Mode.
2. Horizontal trackpad swipe / MOUSEWHEEL with x != 0 (the exact event that caused the crash).
3. Vertical MOUSEWHEEL with y != 0.
4. Mouse drag panning (MOUSEBUTTONDOWN + MOUSEMOTION + MOUSEBUTTONUP).
5. Keyboard arrow key panning (K_LEFT, K_RIGHT, K_UP, K_DOWN).
6. Camera position preservation (not being reset every frame in draw).
"""

import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pygame
from game.app import App


def run_test():
    print("Initializing App for Battle Tree Test...")
    app = App()

    # Enter battle mode
    app.enter_battle()
    print("Entered Battle Mode.")

    # Execute one turn so AI tree is generated
    app.battle_system.execute_player_action("ATTACK")
    app._update(0.5)

    # Open tree modal
    app.overlay.toggle_tree_overlay()
    assert app.overlay.tree_overlay.visible, "Tree overlay should be visible!"
    print("Tree overlay opened. Initial camera_x:", app.overlay.tree_overlay.camera_x)

    initial_cam_x = app.overlay.tree_overlay.camera_x

    # Test 1: Horizontal slide via MOUSEWHEEL (trackpad horizontal swipe: x=1, y=0)
    print("\n--- Test 1: Trackpad horizontal swipe (MOUSEWHEEL x=2, y=0) ---")
    event_hw = pygame.event.Event(pygame.MOUSEWHEEL, {"x": 2, "y": 0, "flipped": False})
    pygame.event.post(event_hw)
    app._handle_events()
    print("  Handled MOUSEWHEEL horizontal without crash!")
    print("  New camera_x:", app.overlay.tree_overlay.camera_x)
    assert app.overlay.tree_overlay.camera_x != initial_cam_x, "Camera X should have moved!"

    # Test 2: Vertical MOUSEWHEEL (zoom)
    print("\n--- Test 2: Mouse wheel zoom (MOUSEWHEEL x=0, y=1) ---")
    event_vw = pygame.event.Event(pygame.MOUSEWHEEL, {"x": 0, "y": 1, "flipped": False})
    pygame.event.post(event_vw)
    app._handle_events()
    print("  Handled MOUSEWHEEL vertical zoom without crash!")

    # Test 3: Mouse Drag Pan
    print("\n--- Test 3: Mouse drag pan ---")
    cam_before_drag = app.overlay.tree_overlay.camera_x
    down_ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (500, 400)})
    move_ev = pygame.event.Event(pygame.MOUSEMOTION, {"buttons": (1, 0, 0), "pos": (650, 400), "rel": (150, 0)})
    up_ev = pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": (650, 400)})

    pygame.event.post(down_ev)
    app._handle_events()
    pygame.event.post(move_ev)
    app._handle_events()
    pygame.event.post(up_ev)
    app._handle_events()
    print("  Handled Mouse Drag Pan without crash!")
    print("  Camera X after drag:", app.overlay.tree_overlay.camera_x)
    assert round(app.overlay.tree_overlay.camera_x - cam_before_drag) == 150, "Camera X should move by exactly 150 px!"

    # Test 4: Keyboard Pan (Arrow Keys)
    print("\n--- Test 4: Keyboard arrow keys panning ---")
    cam_before_key = app.overlay.tree_overlay.camera_x
    k_right_ev = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RIGHT})
    pygame.event.post(k_right_ev)
    app._handle_events()
    print("  Handled K_RIGHT without crash! Camera X:", app.overlay.tree_overlay.camera_x)
    assert app.overlay.tree_overlay.camera_x == cam_before_key - 60.0

    k_left_ev = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_LEFT})
    pygame.event.post(k_left_ev)
    app._handle_events()
    print("  Handled K_LEFT without crash! Camera X:", app.overlay.tree_overlay.camera_x)
    assert app.overlay.tree_overlay.camera_x == cam_before_key

    # Test 5: Verify Camera Position is PRESERVED during drawing (not reset every frame)
    print("\n--- Test 5: Camera Position Preservation during Render ---")
    app._draw()  # First draw syncs initial tree
    test_cam_x = 999.0
    app.overlay.tree_overlay.camera_x = test_cam_x
    app._draw()
    assert app.overlay.tree_overlay.camera_x == test_cam_x, f"Camera X was reset from {test_cam_x} to {app.overlay.tree_overlay.camera_x}!"
    print("  Camera X preserved across _draw() frames!")

    # Close tree modal
    esc_ev = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE})
    pygame.event.post(esc_ev)
    app._handle_events()
    assert not app.overlay.tree_overlay.visible, "Tree overlay should be closed after ESC!"
    print("  Tree overlay closed successfully.")

    print("\n=== ALL BATTLE TREE SLIDE / PAN TESTS PASSED 100% ===")


if __name__ == "__main__":
    run_test()
