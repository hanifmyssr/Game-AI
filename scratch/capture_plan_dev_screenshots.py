"""Capture screenshots of:
1. Overworld with Abandoned Tower & Portal Aura, Bolu near tower with keys
2. Whistle mechanic with wave rings and NPC reaction
3. Boss Battle against Kage the Shadow Lord (black cat boss)
"""

import os
import sys
import pygame

sys.path.insert(0, os.path.abspath("."))
os.environ["SDL_VIDEODRIVER"] = "dummy"

from game.core import config
from game.app import App

ARTIFACT_DIR = r"C:\Users\Pavilion\.gemini\antigravity\brain\38f4bb8b-a421-4acf-b988-2e6d2a7fae0d"

def capture():
    pygame.init()
    app = App()
    app.screen = pygame.display.set_mode((1024, 600))
    app._on_window_resized(1024, 600)

    # --- Screenshot 1: Whistle Mechanic & Stealth ---
    # Put Bolu in a bush and trigger whistle
    bush_cells = list(app.map.bush_set)
    b_pos = bush_cells[0]
    app.player.grid = b_pos
    app.player.px, app.player.py = app.map.world_to_px(b_pos)
    app.camera.follow((app.player.px, app.player.py), smooth=False)
    app.player.update(0.016)
    
    # Put Kuro within hearing distance
    app.npc_kuro.grid = (b_pos[0] + 3, b_pos[1] + 1)
    app.npc_kuro.px, app.npc_kuro.py = app.map.world_to_px(app.npc_kuro.grid)
    app._trigger_whistle()
    # Advance wave a bit
    app.whistle_waves[0]["radius"] = 45.0
    app._draw()
    shot1_path = os.path.join(ARTIFACT_DIR, "verify_stealth_and_whistle.png")
    pygame.image.save(app.screen, shot1_path)
    print("Saved Shot 1:", shot1_path)

    # --- Screenshot 2: Abandoned Tower & Portal Aura (Overworld) ---
    # Award 3 keys
    app.player.rune_keys = ["Kunci Rune A", "Kunci Rune B", "Kunci Rune C"]
    tower_pos = getattr(app.map, "boss_portal", {"x": 38, "y": 5})
    app.player.grid = (tower_pos["x"], tower_pos["y"] + 1)
    app.player.px, app.player.py = app.map.world_to_px(app.player.grid)
    app.camera.follow((app.player.px, app.player.py), smooth=False)
    app.player.update(0.016)
    app.whistle_waves.clear()
    app.ai_ticker_info = {
        "title": "[KB RESOLUTION] HasKey_A & HasKey_B & HasKey_C => PortalActive [TERBUKTI!]",
        "detail": "Segel gerbang Menara Kuno terbuka! Tekan [E] untuk menantang Boss Kage!",
        "timer": 4.5,
    }
    app._draw()
    shot2_path = os.path.join(ARTIFACT_DIR, "verify_abandoned_tower_portal.png")
    pygame.image.save(app.screen, shot2_path)
    print("Saved Shot 2:", shot2_path)

    # --- Screenshot 3: Boss Battle Against Kage the Shadow Lord ---
    app.enter_boss_battle()
    app._draw()
    shot3_path = os.path.join(ARTIFACT_DIR, "verify_boss_battle_kage.png")
    pygame.image.save(app.screen, shot3_path)
    print("Saved Shot 3:", shot3_path)

if __name__ == "__main__":
    capture()
