import math, random

# Test chicken state machine
ch = {
    "origin_x": 100.0,
    "origin_y": 100.0,
    "x": 100.0,
    "y": 100.0,
    "target_x": 100.0,
    "target_y": 100.0,
    "state": "walk",
    "timer": 2.0,
    "facing_left": False,
    "frame_idx": 2,
    "anim_timer": 0.0,
    "speed": 15.0
}
ch["target_x"] = 110.0
ch["target_y"] = 105.0

positions = []
frames = []
for step in range(120): # 2 seconds at 60 fps
    dt = 0.016
    ch["timer"] -= dt
    ch["anim_timer"] += dt

    if ch["state"] == "walk":
        if ch["anim_timer"] >= 0.18:
            ch["anim_timer"] = 0.0
            ch["frame_idx"] = 3 if ch["frame_idx"] == 2 else 2

        dx = ch["target_x"] - ch["x"]
        dy = ch["target_y"] - ch["y"]
        dist = math.hypot(dx, dy)
        move_step = ch["speed"] * dt

        if dist <= move_step or ch["timer"] <= 0:
            ch["x"] = ch["target_x"]
            ch["y"] = ch["target_y"]
            ch["state"] = "peck"
            ch["timer"] = 1.5
            ch["anim_timer"] = 0.0
            ch["frame_idx"] = 4
        else:
            ch["x"] += (dx / dist) * move_step
            ch["y"] += (dy / dist) * move_step

    positions.append((round(ch["x"], 1), round(ch["y"], 1)))
    frames.append(ch["frame_idx"])

print(f"Start pos: {positions[0]}, End pos: {positions[-1]}")
print(f"Max distance from origin: {max(math.hypot(x - 100, y - 100) for x, y in positions):.2f} px")
print(f"Frames used during walk: {set(frames)}")

