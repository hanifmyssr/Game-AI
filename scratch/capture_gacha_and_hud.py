import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from game.app import App

ARTIFACT_DIR = r"C:\Users\Pavilion\.gemini\antigravity\brain\38f4bb8b-a421-4acf-b988-2e6d2a7fae0d"

def capture_gacha_and_hud():
    app = App()
    
    # Setup kamera dan posisi player dekat chest pertama
    chest = app.chests[0] # pos: (27, 2)
    # Move player near chest
    cx, cy = chest["pos"]
    app.player.grid = (cx, cy + 1)
    app.player.px, app.player.py = app.map.world_to_px(app.player.grid)
    app.camera.follow((app.player.px, app.player.py))
    
    # 1. State Gacha Spinning (Roulette berputar di atas chest)
    app._open_chest(chest)
    app.gacha_timer = 0.6
    app.gacha_current_item = "item_sword"
    app._update(0.05)
    app._draw()
    
    path_roulette = os.path.join(ARTIFACT_DIR, "ui_refactor_gacha_roulette_above_chest.png")
    pygame.image.save(app.screen, path_roulette)
    print("Saved Gacha Roulette Above Chest:", path_roulette)
    
    # 2. State Gacha Showcase (Card hadiah melayang tepat di atas chest)
    app._update(0.7) # This triggers _award_gacha_reward()
    app._draw()
    
    path_showcase = os.path.join(ARTIFACT_DIR, "ui_refactor_gacha_showcase_above_chest.png")
    pygame.image.save(app.screen, path_showcase)
    print("Saved Gacha Showcase Above Chest:", path_showcase)
    
    # 3. State Inventory HUD Cozy Tone (Setelah item masuk ke tas)
    # Tutup showcase
    app.gacha_showcase = None
    app.overlay.dock.close() # Clean view
    app._update(0.1)
    app._draw()
    
    path_hud = os.path.join(ARTIFACT_DIR, "ui_refactor_inventory_hud_cozy.png")
    pygame.image.save(app.screen, path_hud)
    print("Saved Inventory HUD Cozy:", path_hud)

if __name__ == "__main__":
    capture_gacha_and_hud()
