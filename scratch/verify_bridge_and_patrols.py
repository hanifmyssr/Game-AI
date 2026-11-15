import os
import sys

# Set SDL to dummy for headless environment
os.environ["SDL_VIDEODRIVER"] = "dummy"

# Add Game-AI root to sys.path
sys.path.insert(0, os.path.abspath("."))

import pygame
from game.app import App
from game import config

print("Initializing Pygame and App...")
pygame.init()
app = App()

print(f"Map size: {app.map.width} x {app.map.height}")

# 1. Test South Bridge walkability
south_bridge_coords = [(19, y) for y in range(20, 30)]
all_walkable = True
for pos in south_bridge_coords:
    walkable = app.map.is_walkable(pos)
    if not walkable:
        all_walkable = False
        print(f"FAILED: South bridge tile {pos} is NOT walkable! (is_water={pos in app.map.water}, is_obs={pos in app.map.obstacle_set})")
    else:
        print(f"OK: South bridge tile {pos} is walkable.")

print(f"South bridge all walkable: {all_walkable}")

# 2. Test Pathfinding across south bridge
app.npc.algorithm = "A*"
test_path = app.npc.find_path((19, 29))
print(f"Path from {app.npc.grid} to south of bridge (19, 29): length={len(test_path.get('path', []))}")
assert len(test_path.get('path', [])) > 0, "No path across south bridge!"

# 3. Check NPCs
print(f"NPC Oyen pos: {app.npc.grid}, is_patrol: {app.npc.is_patrol}, waypoints: {app.npc.waypoints}")
print(f"NPC Kuro pos: {app.npc_kuro.grid}, is_patrol: {app.npc_kuro.is_patrol}, waypoints: {app.npc_kuro.waypoints}")
print(f"NPC Shiro pos: {app.npc_shiro.grid}, is_patrol: {app.npc_shiro.is_patrol}, waypoints: {app.npc_shiro.waypoints}")

# Verify Oyen is in kiri bawah (around chest B at 5, 24)
assert app.npc.grid == (5, 23), f"Expected Oyen at (5, 23), got {app.npc.grid}"
assert (5, 23) in app.npc.waypoints

# Verify Kuro is in east area near chest C (34, 28)
assert app.npc_kuro.grid == (33, 27), f"Expected Kuro at (33, 27), got {app.npc_kuro.grid}"
assert (33, 27) in app.npc_kuro.waypoints

# 4. Simulate a few patrol steps for all NPCs
print("Simulating patrol updates...")
for step in range(60):
    dt = 0.1
    app.npc.update(dt)
    app.npc_kuro.update(dt)
    app.npc_shiro.update(dt)

print(f"After patrol update: Oyen at {app.npc.grid}, Kuro at {app.npc_kuro.grid}, Shiro at {app.npc_shiro.grid}")

# 5. Move Bolu down to south bridge (19, 25)
app.player.grid = (19, 25)
app.player.x = 19 * config.TILE_SIZE
app.player.y = 25 * config.TILE_SIZE
app.player.target_x = app.player.x
app.player.target_y = app.player.y
app.camera.follow((app.player.x, app.player.y))

# Render a frame with Bolu on the south bridge
app.screen.fill((0, 0, 0))
app._draw()
artifact_dir = r"C:\Users\Pavilion\.gemini\antigravity\brain\38f4bb8b-a421-4acf-b988-2e6d2a7fae0d"
bridge_shot = os.path.join(artifact_dir, "verify_bridge_crossing.png")
pygame.image.save(app.screen, bridge_shot)
print(f"Saved bridge screenshot to {bridge_shot}")

# 6. Render frame with camera centered on Kuro (right bridge)
app.camera.follow((app.npc_kuro.px, app.npc_kuro.py))
app.screen.fill((0, 0, 0))
app._draw()
kuro_shot = os.path.join(artifact_dir, "verify_kuro_patrol.png")
pygame.image.save(app.screen, kuro_shot)
print(f"Saved Kuro screenshot to {kuro_shot}")

# 7. Render frame with camera centered on Oyen (bottom-left chest)
app.camera.follow((app.npc.px, app.npc.py))
app.screen.fill((0, 0, 0))
app._draw()
oyen_shot = os.path.join(artifact_dir, "verify_oyen_patrol.png")
pygame.image.save(app.screen, oyen_shot)
print(f"Saved Oyen screenshot to {oyen_shot}")

print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
