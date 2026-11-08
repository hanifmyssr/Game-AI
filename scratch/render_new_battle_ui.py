"""Script rendering dan verifikasi desain baru Battle UI:
1. Forest pixel-art background
2. Centered Player & NPC
3. Vertical compact squad queue (Image 1 style)
4. RPG Diamond Cross Action Hub (Image 3 style)
5. Action scores populated in Minimax tab
"""

import os
import sys
import pygame

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()

from game.app import App


def main():
    app = App()
    app.enter_pre_battle()
    app.enter_battle()

    # Pastikan preview AI terhitung
    app.battle_system.update_ai_preview()

    print("Battle background path:", app.battle_bg.bg_path)
    print("Raw bg loaded:", app.battle_bg.raw_bg is not None)

    surf = pygame.Surface((1024, 668))
    app._draw_battle_arena()
    out_path = r"C:\Users\Pavilion\.gemini\antigravity\brain\38f4bb8b-a421-4acf-b988-2e6d2a7fae0d\battle_ui_current_state.png"
    pygame.image.save(app.screen, out_path)
    print("Current state saved to:", out_path)


if __name__ == "__main__":
    main()

