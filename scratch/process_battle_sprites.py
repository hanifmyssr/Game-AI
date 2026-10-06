"""Script untuk memproses battle sprites:
- Membaca gambar dari artifacts
- Flood fill dari pinggir luar untuk menghapus background putih menjadi transparan (RGBA)
  (Tanpa merusak bulu putih karakter di dalam tubuh)
- Crop bounding box karakter dengan padding rapi
- Simpan ke assets/battle_sprites/
"""

import collections
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

pygame.init()

ARTIFACT_DIR = r"C:\Users\Pavilion\.gemini\antigravity-ide\brain\b2b19d09-f4cb-4521-818a-3ed71602630e"
OUT_DIR = os.path.join("assets", "battle_sprites")
os.makedirs(OUT_DIR, exist_ok=True)

SPRITES = {
    "battle_warrior.png": os.path.join(ARTIFACT_DIR, "battle_warrior_1791297370617.jpg"),
    "battle_ranger.png": os.path.join(ARTIFACT_DIR, "battle_ranger_1791297398474.jpg"),
    "battle_mage.png": os.path.join(ARTIFACT_DIR, "battle_mage_1791297417767.jpg"),
    "battle_bolu.png": os.path.join(ARTIFACT_DIR, "battle_bolu_1791297438587.jpg"),
}


def is_background_color(r, g, b):
    # Latar belakang putih / off-white
    return r >= 235 and g >= 235 and b >= 235


def process_image(src_path, out_name):
    print(f"Memproses {src_path} -> {out_name}...")
    img = pygame.image.load(src_path)
    w, h = img.get_size()

    # Buat surface RGBA 32-bit
    rgba_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    rgba_surf.blit(img, (0, 0))

    # BFS Flood-fill dari seluruh tepi (tepi atas, bawah, kiri, kanan)
    visited = set()
    queue = collections.deque()

    for x in range(w):
        for y in (0, h - 1):
            c = rgba_surf.get_at((x, y))
            if is_background_color(c.r, c.g, c.b):
                queue.append((x, y))
                visited.add((x, y))

    for y in range(h):
        for x in (0, w - 1):
            if (x, y) not in visited:
                c = rgba_surf.get_at((x, y))
                if is_background_color(c.r, c.g, c.b):
                    queue.append((x, y))
                    visited.add((x, y))

    # Jalankan BFS
    while queue:
        cx, cy = queue.popleft()
        rgba_surf.set_at((cx, cy), (0, 0, 0, 0))

        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                nc = rgba_surf.get_at((nx, ny))
                if is_background_color(nc.r, nc.g, nc.b):
                    visited.add((nx, ny))
                    queue.append((nx, ny))

    # Cari bounding box karakter yang tidak transparan
    min_x, min_y, max_x, max_y = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            alpha = rgba_surf.get_at((x, y)).a
            if alpha > 10:
                if x < min_x:
                    min_x = x
                if y < min_y:
                    min_y = y
                if x > max_x:
                    max_x = x
                if y > max_y:
                    max_y = y

    if max_x >= min_x and max_y >= min_y:
        pad = 8
        crop_x = max(0, min_x - pad)
        crop_y = max(0, min_y - pad)
        crop_w = min(w - crop_x, (max_x - min_x + 1) + pad * 2)
        crop_h = min(h - crop_y, (max_y - min_y + 1) + pad * 2)

        cropped_surf = pygame.Surface((crop_w, crop_h), pygame.SRCALPHA)
        cropped_surf.blit(rgba_surf, (0, 0), pygame.Rect(crop_x, crop_y, crop_w, crop_h))
        final_surf = cropped_surf
    else:
        final_surf = rgba_surf

    out_path = os.path.join(OUT_DIR, out_name)
    pygame.image.save(final_surf, out_path)
    print(f"Berhasil disimpan: {out_path} ({final_surf.get_width()}x{final_surf.get_height()})")


for out_name, src_path in SPRITES.items():
    process_image(src_path, out_name)

# Buat salinan alias untuk class lainnya jika diperlukan
aliases = {
    "battle_tank.png": "battle_warrior.png",
    "battle_assassin.png": "battle_ranger.png",
}
for alias_name, target in aliases.items():
    src_target = os.path.join(OUT_DIR, target)
    if os.path.exists(src_target):
        dst = os.path.join(OUT_DIR, alias_name)
        img = pygame.image.load(src_target)
        pygame.image.save(img, dst)
        print(f"Membuat alias: {alias_name} -> {target}")

print("SEMUA PROSES SELESAI!")
