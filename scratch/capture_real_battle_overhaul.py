"""Capture real battle overhaul with enlarged centered hub."""
import os
import sys
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()

sys.path.insert(0, os.path.abspath("Game-AI"))
from game.app import App
from game.ai.battle_ai import ACTION_ATTACK

def run_real_battle_capture():
    app = App()
    app.enter_pre_battle()
    app.enter_battle()

    # 1. 1024x668 Dock Closed
    app.screen = pygame.display.set_mode((1024, 668), pygame.RESIZABLE)
    app._on_window_resized(1024, 668)
    app.overlay.dock.is_open = False
    app._draw()
    out_1024_closed = "C:/Users/Pavilion/.gemini/antigravity/brain/38f4bb8b-a421-4acf-b988-2e6d2a7fae0d/real_battle_centered_hub_1024x668.png"
    pygame.image.save(app.screen, out_1024_closed)
    print(f"Saved: {out_1024_closed}")

    # 2. 1024x668 Dock Open
    app.overlay.dock.is_open = True
    app.overlay.dock.active_tab_id = 2
    app._draw()
    out_1024_open = "C:/Users/Pavilion/.gemini/antigravity/brain/38f4bb8b-a421-4acf-b988-2e6d2a7fae0d/real_battle_centered_hub_1024x668_dock_open.png"
    pygame.image.save(app.screen, out_1024_open)
    print(f"Saved: {out_1024_open}")

    # 3. 1280x800 Dock Open (Fullscreen / Default)
    app.screen = pygame.display.set_mode((1280, 800), pygame.RESIZABLE)
    app._on_window_resized(1280, 800)
    app.overlay.dock.is_open = True
    app.overlay.dock.active_tab_id = 2
    app._draw()
    out_1280_open = "C:/Users/Pavilion/.gemini/antigravity/brain/38f4bb8b-a421-4acf-b988-2e6d2a7fae0d/real_battle_centered_hub_1280x800_dock_open.png"
    pygame.image.save(app.screen, out_1280_open)
    print(f"Saved: {out_1280_open}")

    # 4. 1280x800 Dock Closed
    app.overlay.dock.is_open = False
    app._draw()
    out_1280_closed = "C:/Users/Pavilion/.gemini/antigravity/brain/38f4bb8b-a421-4acf-b988-2e6d2a7fae0d/real_battle_centered_hub_1280x800_dock_closed.png"
    pygame.image.save(app.screen, out_1280_closed)
    print(f"Saved: {out_1280_closed}")

    # Test clicking Attack button
    assert app.btn_action_attack.width > 0
    click_pos = app.btn_action_attack.center
    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": click_pos})
    pygame.event.post(ev)
    app._handle_events()
    print("Mouse click on attack button succeeded!")

if __name__ == "__main__":
    run_real_battle_capture()
