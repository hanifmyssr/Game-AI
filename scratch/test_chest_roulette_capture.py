import os
import pygame
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.app import App

app = App()
app.game_mode = "EXPLORATION"

# Test Roulette Popup (50% transparent)
app.chests[1]["opened"] = False
app._open_chest(app.chests[1])
app._update(0.1)
app._draw()
pygame.image.save(app.screen, "scratch/test_chest_roulette_50.png")
