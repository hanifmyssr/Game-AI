import os
import pygame
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.app import App

app = App()
app.game_mode = "EXPLORATION"

# Test Health Potion showcase
app.chests[0]["opened"] = False
app._open_chest(app.chests[0])
app._update(1.2)
app._draw()
pygame.image.save(app.screen, "scratch/test_chest_potion.png")

# Test Shield showcase
app.chests[2]["opened"] = False
app._open_chest(app.chests[2])
app._update(1.2)
app._draw()
pygame.image.save(app.screen, "scratch/test_chest_shield.png")

print("Tested all chests successfully!")
