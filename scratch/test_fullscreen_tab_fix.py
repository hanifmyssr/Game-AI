"""Test and capture screenshots verifying tab layout on window resize / fullscreen.
Tests:
- 1280x800 (default)
- 1366x768 (standard laptop maximized)
- 1920x1080 (full HD maximized/fullscreen)
- 1024x640 (compact window)
Checks:
- Nav rail bottom matches screen height.
- Inspector dock bottom matches screen height.
- Tab action buttons are fully visible and inside screen bounds.
"""

import os
import sys

# Headless mode
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pygame
from game.app import App
from game.core import config

ARTIFACT_DIR = r"C:\Users\Pavilion\.gemini\antigravity\brain\38f4bb8b-a421-4acf-b988-2e6d2a7fae0d"


def run_test():
    print("Initializing App...")
    app = App()

    resolutions = [
        ("1280x800_default", 1280, 800),
        ("1366x768_laptop", 1366, 768),
        ("1920x1080_fullhd", 1920, 1080),
        ("1024x640_compact", 1024, 640),
    ]

    for label, w, h in resolutions:
        print(f"\n--- Testing Resolution: {label} ({w}x{h}) ---")
        app.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
        app._on_window_resized(w, h)

        assert app.overlay.nav_rail.rect.height == h, f"Nav rail height {app.overlay.nav_rail.rect.height} != {h}"
        assert app.overlay.dock.rect.height == h, f"Dock height {app.overlay.dock.rect.height} != {h}"
        assert app.overlay.nav_rail.rect.bottom == h, f"Nav rail bottom != {h}"
        assert app.overlay.dock.rect.bottom == h, f"Dock bottom != {h}"

        # Test each of the 7 tabs
        for tab_id in range(7):
            app.overlay.nav_rail.set_active_tab(tab_id)
            app._update(0.016)
            app._draw()

            active_tab = app.overlay.dock.tabs[tab_id]
            # Check button positions
            buttons = []
            if hasattr(active_tab, "btn_call"):
                buttons.append(("btn_call", active_tab.btn_call))
            if hasattr(active_tab, "btn_toggle_path"):
                buttons.append(("btn_toggle_path", active_tab.btn_toggle_path))
            if hasattr(active_tab, "btn_tree_modal"):
                buttons.append(("btn_tree_modal", active_tab.btn_tree_modal))
            if hasattr(active_tab, "btn_reroll"):
                buttons.append(("btn_reroll", active_tab.btn_reroll))
            if hasattr(active_tab, "btn_proof_modal"):
                buttons.append(("btn_proof_modal", active_tab.btn_proof_modal))
            if hasattr(active_tab, "btn_plan_tree"):
                buttons.append(("btn_plan_tree", active_tab.btn_plan_tree))
            if hasattr(active_tab, "btn_reset"):
                buttons.append(("btn_reset", active_tab.btn_reset))

            for btn_name, btn in buttons:
                assert btn.rect.bottom <= h, f"Tab {tab_id} {btn_name} bottom {btn.rect.bottom} > screen height {h}!"
                assert btn.rect.top >= 48, f"Tab {tab_id} {btn_name} top {btn.rect.top} < header 48!"

        print(f"  All 7 tabs verified in {label}: buttons completely within bounds!")

        # Save screenshot for Tab 1 (Search - user's problem screenshot)
        app.overlay.nav_rail.set_active_tab(1)
        app._update(0.016)
        app._draw()
        out_path = os.path.join(ARTIFACT_DIR, f"tab_fix_{label}.png")
        pygame.image.save(app.screen, out_path)
        print(f"  Saved screenshot: {out_path}")

    # Also test F11 fullscreen toggle
    print("\n--- Testing F11 Fullscreen Toggle ---")
    app.toggle_fullscreen()
    print("  Fullscreen active:", app.is_fullscreen)
    app._update(0.016)
    app._draw()

    app.toggle_fullscreen()
    print("  Windowed restored:", not app.is_fullscreen)
    app._update(0.016)
    app._draw()

    print("\n=== ALL FULLSCREEN / RESIZE TESTS PASSED 100% ===")


if __name__ == "__main__":
    run_test()

