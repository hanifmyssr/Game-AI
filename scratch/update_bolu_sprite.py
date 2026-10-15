import collections
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

pygame.init()

SRC_PATH = r"C:\Users\Pavilion\.gemini\antigravity-ide\brain\6e833c29-d93e-4d54-9f32-938da0e0debe\battle_bolu_calico_1791343563658.jpg"
OUT_PATH = os.path.join("assets", "battle_sprites", "battle_bolu.png")

def is_background_color(r, g, b):
    # Latar belakang putih / off-white dari generative image
    return r >= 235 and g >= 235 and b >= 235

def process_image(src_path, out_path):
    print(f"Loading {src_path}...")
    img = pygame.image.load(src_path)
    w, h = img.get_size()

    rgba_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    rgba_surf.blit(img, (0, 0))

    # BFS Flood-fill dari seluruh tepi luar (menghapus latar tanpa tembus ke tubuh berbulu putih jika ada outline/border)
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

    # BFS
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

    # Cari bounding box karakter
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

    pygame.image.save(final_surf, out_path)
    print(f"Saved: {out_path} ({final_surf.get_width()}x{final_surf.get_height()})")

if __name__ == "__main__":
    process_image(SRC_PATH, OUT_PATH)
