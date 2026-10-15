"""Script untuk memproses portrait dan battle sprite assassin."""

import collections
import os
from PIL import Image

BRAIN_DIR = r"C:\Users\Pavilion\.gemini\antigravity-ide\brain\409736b6-c332-4fc5-89da-c9350a33efdd"
PORTRAIT_SRC = os.path.join(BRAIN_DIR, "portrait_assassin_1791354445592.jpg")
BATTLE_SRC = os.path.join(BRAIN_DIR, "battle_assassin_1791354464051.jpg")

PORTRAIT_DST = os.path.join("assets", "portraits", "portrait_assassin.png")
BATTLE_DST = os.path.join("assets", "battle_sprites", "battle_assassin.png")

os.makedirs(os.path.dirname(PORTRAIT_DST), exist_ok=True)
os.makedirs(os.path.dirname(BATTLE_DST), exist_ok=True)


def process_portrait(src_path, dst_path, target_size=256, threshold=30):
    print(f"Processing portrait: {src_path} -> {dst_path}")
    img = Image.open(src_path).convert("RGBA")
    img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)
    w, h = img.size
    pixels = img.load()

    # BFS from corners/edges for black background (r <= threshold, g <= threshold, b <= threshold)
    visited = set()
    queue = collections.deque()

    def is_bg(x, y):
        r, g, b, _ = pixels[x, y]
        return r <= threshold and g <= threshold and b <= threshold

    for x in range(w):
        for y in (0, h - 1):
            if is_bg(x, y):
                queue.append((x, y))
                visited.add((x, y))

    for y in range(h):
        for x in (0, w - 1):
            if (x, y) not in visited and is_bg(x, y):
                queue.append((x, y))
                visited.add((x, y))

    while queue:
        cx, cy = queue.popleft()
        pixels[cx, cy] = (0, 0, 0, 0)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                if is_bg(nx, ny):
                    visited.add((nx, ny))
                    queue.append((nx, ny))

    img.save(dst_path, "PNG")
    print(f"Saved portrait: {dst_path}")


def process_battle_sprite(src_path, dst_path):
    print(f"Processing battle sprite: {src_path} -> {dst_path}")
    img = Image.open(src_path).convert("RGBA")
    w, h = img.size
    pixels = img.load()

    # BFS from outside edges for white background (r >= 235 and g >= 235 and b >= 235)
    def is_bg(x, y):
        r, g, b, _ = pixels[x, y]
        return r >= 230 and g >= 230 and b >= 230

    visited = set()
    queue = collections.deque()

    for x in range(w):
        for y in (0, h - 1):
            if is_bg(x, y):
                queue.append((x, y))
                visited.add((x, y))

    for y in range(h):
        for x in (0, w - 1):
            if (x, y) not in visited and is_bg(x, y):
                queue.append((x, y))
                visited.add((x, y))

    while queue:
        cx, cy = queue.popleft()
        pixels[cx, cy] = (0, 0, 0, 0)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                if is_bg(nx, ny):
                    visited.add((nx, ny))
                    queue.append((nx, ny))

    # Crop bounding box
    bbox = img.getbbox()
    if bbox:
        pad = 8
        crop_box = (
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(w, bbox[2] + pad),
            min(h, bbox[3] + pad),
        )
        img = img.crop(crop_box)

    img.save(dst_path, "PNG")
    print(f"Saved battle sprite: {dst_path} ({img.size})")


if __name__ == "__main__":
    process_portrait(PORTRAIT_SRC, PORTRAIT_DST)
    process_battle_sprite(BATTLE_SRC, BATTLE_DST)
