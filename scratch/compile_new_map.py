"""compile_new_map.py
Menyusun peta baru (Sprout Lands & Shining Fields) secara presisi dan menghasilkan
berkas data/map_tubes.json yang baru, dengan cadangan otomatis di data/map_tubes_backup.json.
"""

import json
import os
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
MAP_FILE = os.path.join(DATA_DIR, "map_tubes.json")
BACKUP_FILE = os.path.join(DATA_DIR, "map_tubes_backup.json")

# Pastikan backup ada
if os.path.exists(MAP_FILE) and not os.path.exists(BACKUP_FILE):
    shutil.copy2(MAP_FILE, BACKUP_FILE)
    print(f"Cadangan aman dibuat di: {BACKUP_FILE}")

WIDTH = 44
HEIGHT = 32
CELL_SIZE = 16

# Layer storage
ground = []
water = []
decorations = []
obstacles = []

# 1. SUNGAI & AIR (River: x=19..23, Bridge at y=12..13)
RIVER_WEST_SHORE = 19
RIVER_EAST_SHORE = 23
BRIDGE_Y = [12, 13]

for y in range(HEIGHT):
    for x in range(RIVER_WEST_SHORE, RIVER_EAST_SHORE + 1):
        water.append({
            "x": x, "y": y,
            "src": "sprout/Water.png",
            "atlas_x": 0, "atlas_y": 0
        })

# 2. RUMPUT & DARATAN (Ground Layer)
# West island: x = 0..19, East island: x = 23..43
for y in range(HEIGHT):
    # West ground
    for x in range(0, RIVER_WEST_SHORE):
        ground.append({
            "x": x, "y": y,
            "src": "sprout/Grass.png",
            "atlas_x": 1, "atlas_y": 1  # Solid grass
        })
    # West Shore (x = 19)
    # Jika bukan bridge, ini adalah bibir pantai barat (menghadap air ke timur)
    if True:
        ground.append({
            "x": RIVER_WEST_SHORE, "y": y,
            "src": "sprout/Grass.png",
            "atlas_x": 2, "atlas_y": 1  # Shore facing east
        })

    # East Shore (x = 23)
    # Jika bukan bridge, ini adalah bibir pantai timur (menghadap air ke barat)
    ground.append({
        "x": RIVER_EAST_SHORE, "y": y,
        "src": "sprout/Grass.png",
        "atlas_x": 0, "atlas_y": 1  # Shore facing west
    })

    # East ground
    for x in range(RIVER_EAST_SHORE + 1, WIDTH):
        ground.append({
            "x": x, "y": y,
            "src": "sprout/Grass.png",
            "atlas_x": 1, "atlas_y": 1  # Solid grass
        })

# 3. JALAN UTAMA TANAH (Main Dirt Road)
# Jalan tanah ditempatkan di layer decorations agar dirender DI ATAS rumput hijau (tidak meninggalkan celah hitam).
# Menggunakan tileset Tilled_Dirt yang bersambung halus dengan pinggiran rumput.
for x in range(WIDTH):
    # Di atas sungai, gunakan jembatan kayu, bukan jalan tanah biasa
    if RIVER_WEST_SHORE <= x <= RIVER_EAST_SHORE:
        continue
    decorations.append({
        "x": x, "y": 12,
        "src": "sprout/Tilled_Dirt.png",
        "atlas_x": 1, "atlas_y": 0  # Pinggiran rumput atas
    })
    decorations.append({
        "x": x, "y": 13,
        "src": "sprout/Tilled_Dirt.png",
        "atlas_x": 1, "atlas_y": 2  # Pinggiran rumput bawah
    })

# Cabang jalan ke Rumah 1 (Pondok Bolu di Barat): x=6, y=8..11
for y in range(8, 12):
    decorations.append({
        "x": 6, "y": y,
        "src": "sprout/Tilled_Dirt.png",
        "atlas_x": 1, "atlas_y": 1  # Tanah padat
    })

# Cabang jalan ke Rumah 2 & Dermaga di Timur: x=30, y=14..15
for y in range(14, 16):
    decorations.append({
        "x": 30, "y": y,
        "src": "sprout/Tilled_Dirt.png",
        "atlas_x": 1, "atlas_y": 1  # Tanah padat
    })

# Dermaga kayu di tepi air timur: x=24..27, y=24
for x in range(24, 28):
    decorations.append({
        "x": x, "y": 24,
        "src": "sprout/Wooden_path.png",
        "atlas_x": 1, "atlas_y": 1
    })

# 4. JEMBATAN KAYU (Wood Bridge at x=19..23, y=12..13)
# Jembatan diletakkan di layer decorations
# x=19 (pintu barat), x=20,21,22 (papan tengah), x=23 (pintu timur)
bridge_coords = [
    (19, 12, 0, 0), (19, 13, 0, 1),
    (20, 12, 1, 0), (20, 13, 1, 1),
    (21, 12, 2, 0), (21, 13, 2, 1),
    (22, 12, 3, 0), (22, 13, 3, 1),
    (23, 12, 4, 0), (23, 13, 4, 1),
]
for bx, by, ax, ay in bridge_coords:
    decorations.append({
        "x": bx, "y": by,
        "src": "sprout/Wood_Bridge.png",
        "atlas_x": ax, "atlas_y": ay
    })

# 5. RUMAH 1: PONDOK BOLU (West Cottage: 3x4 ubin, x=5..7, y=4..7)
# Bangunan utuh rapi: puncak atap di y=4, atap di y=5, dinding jendela di y=6, dinding pintu di y=7
house1_tiles = [
    (6, 4, 1, 0),                                # Puncak atap
    (5, 5, 0, 1), (6, 5, 1, 1), (7, 5, 2, 1),    # Atap utama
    (5, 6, 0, 2), (6, 6, 1, 2), (7, 6, 2, 2),    # Dinding jendela
    (5, 7, 0, 3), (6, 7, 1, 3), (7, 7, 2, 3),    # Dinding pintu masuk (pintu di x=6, y=7)
]
for hx, hy, ax, ay in house1_tiles:
    decorations.append({
        "x": hx, "y": hy,
        "src": "sprout/Wooden_House.png",
        "atlas_x": ax, "atlas_y": ay
    })

# 6. RUMAH 2: PONDOK NELAYAN / POS SHIRO (East Cottage: 3x4 ubin, x=29..31, y=16..19)
house2_tiles = [
    (30, 16, 1, 0),                              # Puncak atap
    (29, 17, 0, 1), (30, 17, 1, 1), (31, 17, 2, 1), # Atap utama
    (29, 18, 0, 2), (30, 18, 1, 2), (31, 18, 2, 2), # Dinding jendela
    (29, 19, 0, 3), (30, 19, 1, 3), (31, 19, 2, 3), # Dinding pintu masuk (pintu di x=30, y=19)
]
for hx, hy, ax, ay in house2_tiles:
    decorations.append({
        "x": hx, "y": hy,
        "src": "sprout/Wooden_House.png",
        "atlas_x": ax, "atlas_y": ay
    })

# 7. TEBING BUKIT UTARA (North Cliffs: y=0..2)
# Bukit di sektor barat (x=0..18) dan timur (x=24..43)
for x in range(0, RIVER_WEST_SHORE):
    # Biarkan celah gua di x=10..12
    if 10 <= x <= 12:
        decorations.append({"x": x, "y": 0, "src": "sprout/Hills.png", "atlas_x": 6, "atlas_y": 6})
        decorations.append({"x": x, "y": 1, "src": "sprout/Hills.png", "atlas_x": 6, "atlas_y": 7})
        decorations.append({"x": x, "y": 2, "src": "sprout/Hills.png", "atlas_x": 6, "atlas_y": 8})
    else:
        decorations.append({"x": x, "y": 0, "src": "sprout/Hills.png", "atlas_x": 1, "atlas_y": 0})
        decorations.append({"x": x, "y": 1, "src": "sprout/Hills.png", "atlas_x": 1, "atlas_y": 1})
        decorations.append({"x": x, "y": 2, "src": "sprout/Hills.png", "atlas_x": 1, "atlas_y": 2})

for x in range(RIVER_EAST_SHORE + 1, WIDTH):
    decorations.append({"x": x, "y": 0, "src": "sprout/Hills.png", "atlas_x": 1, "atlas_y": 0})
    decorations.append({"x": x, "y": 1, "src": "sprout/Hills.png", "atlas_x": 1, "atlas_y": 1})
    decorations.append({"x": x, "y": 2, "src": "sprout/Hills.png", "atlas_x": 1, "atlas_y": 2})

# 8. POHON, SEMAK, BATU, BUNGA (Foliage & Decor)
# Foliage (pohon, semak, bunga) akan dirender secara dinamis dengan animasi angin (wind sway),
# sehingga tidak dibakar statis di lapisan dekorasi ground agar tidak berbayang ganda.
tree_positions = [
    (1, 4), (1, 8), (1, 16), (1, 20), (1, 25),
    (14, 18), (14, 25),
    (38, 4), (38, 8), (38, 16), (38, 22), (38, 27)
]
for tx, ty in tree_positions:
    # Batang pohon tetap di ground/decorations agar menancap kokoh di tanah (atlas_x 1 dan 2, atlas_y 1)
    decorations.append({"x": tx, "y": ty+1, "src": "sprout/Basic_Grass_Biom_things.png", "atlas_x": 1, "atlas_y": 1})
    decorations.append({"x": tx+1, "y": ty+1, "src": "sprout/Basic_Grass_Biom_things.png", "atlas_x": 2, "atlas_y": 1})

# Semak bulat hijau
bush_positions = [
    (6, 17), (10, 20), (15, 10), (16, 27),
    (26, 10), (34, 10), (27, 18), (35, 27)
]

# Bunga liar putih
flower_positions = [
    (5, 10), (7, 11), (9, 16), (12, 19), (16, 15),
    (25, 11), (27, 12), (31, 14), (34, 22), (36, 18)
]

# Batu sungai
rock_positions = [
    (21, 6), (22, 9), (21, 18), (22, 27)
]
for rx, ry in rock_positions:
    decorations.append({"x": rx, "y": ry, "src": "sprout/Basic_Grass_Biom_things.png", "atlas_x": 0, "atlas_y": 2})

# Pagar kayu pembatas selatan (y=31)
for x in range(0, RIVER_WEST_SHORE):
    decorations.append({"x": x, "y": 31, "src": "sprout/Fences.png", "atlas_x": 1, "atlas_y": 0})
for x in range(RIVER_EAST_SHORE + 1, WIDTH):
    decorations.append({"x": x, "y": 31, "src": "sprout/Fences.png", "atlas_x": 1, "atlas_y": 0})

# 9. OBSTACLES (Rintangan / Collision)
# A. Seluruh air sungai kecuali jembatan
bridge_tiles_set = {(bx, by) for bx, by, _, _ in bridge_coords}
for y in range(HEIGHT):
    for x in range(RIVER_WEST_SHORE, RIVER_EAST_SHORE + 1):
        if (x, y) not in bridge_tiles_set:
            obstacles.append({"x": x, "y": y, "src": "sprout/Water.png", "atlas_x": 0, "atlas_y": 0})

# B. Tebing atas (y=0..1 kecuali celah gua di x=10..12)
for x in range(0, RIVER_WEST_SHORE):
    if not (10 <= x <= 12 and y == 2):
        obstacles.append({"x": x, "y": 0, "src": "sprout/Hills.png", "atlas_x": 1, "atlas_y": 0})
        obstacles.append({"x": x, "y": 1, "src": "sprout/Hills.png", "atlas_x": 1, "atlas_y": 1})

for x in range(RIVER_EAST_SHORE + 1, WIDTH):
    obstacles.append({"x": x, "y": 0, "src": "sprout/Hills.png", "atlas_x": 1, "atlas_y": 0})
    obstacles.append({"x": x, "y": 1, "src": "sprout/Hills.png", "atlas_x": 1, "atlas_y": 1})

# C. Rumah 1: Atap dan dinding (kecuali pintu di x=6, y=7)
for hx, hy, _, _ in house1_tiles:
    if not (hx == 6 and hy == 7):  # Pintu masuk dapat dilewati
        obstacles.append({"x": hx, "y": hy, "src": "sprout/Wooden_House.png", "atlas_x": 0, "atlas_y": 1})

# D. Rumah 2: Atap dan dinding (kecuali pintu di x=30, y=19)
for hx, hy, _, _ in house2_tiles:
    if not (hx == 30 and hy == 19):
        obstacles.append({"x": hx, "y": hy, "src": "sprout/Wooden_House.png", "atlas_x": 0, "atlas_y": 1})

# E. Pagar selatan (y=31)
for x in range(0, RIVER_WEST_SHORE):
    obstacles.append({"x": x, "y": 31, "src": "sprout/Fences.png", "atlas_x": 1, "atlas_y": 0})
for x in range(RIVER_EAST_SHORE + 1, WIDTH):
    obstacles.append({"x": x, "y": 31, "src": "sprout/Fences.png", "atlas_x": 1, "atlas_y": 0})

# F. Batang pohon
for tx, ty in tree_positions:
    obstacles.append({"x": tx, "y": ty+1, "src": "sprout/Basic_Grass_Biom_things.png", "atlas_x": 1, "atlas_y": 1})
    obstacles.append({"x": tx+1, "y": ty+1, "src": "sprout/Basic_Grass_Biom_things.png", "atlas_x": 2, "atlas_y": 1})

# 10. SPAWN POINTS & CHESTS
spawns = {
    "player": {"grid_x": 8, "grid_y": 16},
    "npc_oyen": {"grid_x": 14, "grid_y": 16},
    "npc_kuro": {"grid_x": 11, "grid_y": 4, "waypoints": [(11, 4), (16, 4), (16, 8), (11, 8)]},
    "npc_shiro": {"grid_x": 28, "grid_y": 15, "waypoints": [(28, 15), (35, 15), (35, 24), (28, 24)]},
    "chests": [
        {"x": 6, "y": 20, "item": "health_potion"},
        {"x": 11, "y": 4, "item": "item_sword"},
        {"x": 36, "y": 24, "item": "item_shield"}
    ]
}

map_document = {
    "schema_version": 1,
    "name": "SproutLands_LivingWorld",
    "cell_size": CELL_SIZE,
    "grid": {
        "min_x": 0,
        "min_y": 0,
        "width": WIDTH,
        "height": HEIGHT
    },
    "ground_asset": "sprout/Grass.png",
    "water": water,
    "ground": ground,
    "decorations": decorations,
    "obstacles": obstacles,
    "foliage": {
        "trees": tree_positions,
        "bushes": bush_positions,
        "flowers": flower_positions
    },
    "spawns": spawns
}

# Simpan ke data/map_tubes.json
with open(MAP_FILE, "w", encoding="utf-8") as f:
    json.dump(map_document, f, indent=2)

print(f"Peta baru berhasil dikompilasi ke: {MAP_FILE}")
print(f"Dimensi Peta: {WIDTH} x {HEIGHT} ({WIDTH * CELL_SIZE} x {HEIGHT * CELL_SIZE} px)")
print(f"Total Ubin Ground: {len(ground)}")
print(f"Total Ubin Water: {len(water)}")
print(f"Total Ubin Decorations: {len(decorations)}")
print(f"Total Ubin Obstacles: {len(obstacles)}")
