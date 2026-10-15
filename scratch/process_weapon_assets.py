import os
import pygame

def process_item_sprite(src_path, dst_path, size=(128, 128)):
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    surf = pygame.image.load(src_path)
    surf = pygame.transform.smoothscale(surf, size).convert_alpha()
    w, h = surf.get_size()

    # Flood fill exterior black pixels to transparent
    visited = set()
    queue = []
    
    for x in range(w):
        queue.append((x, 0))
        queue.append((x, h - 1))
    for y in range(h):
        queue.append((0, y))
        queue.append((w - 1, y))

    while queue:
        cx, cy = queue.pop(0)
        if (cx, cy) in visited:
            continue
        visited.add((cx, cy))

        r, g, b, a = surf.get_at((cx, cy))
        if r < 20 and g < 20 and b < 20:
            surf.set_at((cx, cy), (0, 0, 0, 0))
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                    queue.append((nx, ny))

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    pygame.image.save(surf, dst_path)
    print(f"Processed: {dst_path} ({size[0]}x{size[1]})")

if __name__ == "__main__":
    bow_src = r"C:\Users\Pavilion\.gemini\antigravity-ide\brain\409736b6-c332-4fc5-89da-c9350a33efdd\item_bow_1791361052334.jpg"
    dagger_src = r"C:\Users\Pavilion\.gemini\antigravity-ide\brain\409736b6-c332-4fc5-89da-c9350a33efdd\item_dagger_1791361071204.jpg"
    
    process_item_sprite(bow_src, "assets/items/item_bow.png")
    process_item_sprite(dagger_src, "assets/items/item_dagger.png")
    print("Done processing weapons!")
