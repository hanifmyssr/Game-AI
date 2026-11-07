"""Konverter Otomatis Tiled (.tmj) ke Format Map Tubes (data/map_tubes.json).

Cara pakai:
    python scratch/convert_tiled_to_tubes.py
"""

import json
import os
import xml.etree.ElementTree as ET

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GAME_AI_DIR = os.path.dirname(SCRIPT_DIR)
TMJ_PATH = os.path.join(GAME_AI_DIR, "assets", "map_new.tmj")
OUT_JSON = os.path.join(GAME_AI_DIR, "data", "map_tubes.json")


def convert():
    if not os.path.exists(TMJ_PATH):
        print(f"Error: Berkas tidak ditemukan: {TMJ_PATH}")
        return

    base_dir = os.path.dirname(TMJ_PATH)
    with open(TMJ_PATH, "r", encoding="utf-8") as f:
        tmj = json.load(f)

    w = tmj["width"]
    h = tmj["height"]
    cs = tmj["tilewidth"]

    # 1. Parse seluruh tileset (.tsx) yang direferensikan
    ts_list = []
    for ts in tmj.get("tilesets", []):
        fgid = ts["firstgid"]
        src = ts["source"]
        tsx_path = os.path.normpath(os.path.join(base_dir, src))
        if not os.path.exists(tsx_path):
            print(f"Warning: .tsx tidak ditemukan di {tsx_path}")
            continue

        tree = ET.parse(tsx_path)
        root = tree.getroot()
        img_elem = root.find("image")
        img_src = img_elem.attrib["source"]
        cols = int(root.attrib.get("columns", 1))
        tile_count = int(root.attrib.get("tilecount", 1))
        norm_img = img_src.replace("\\", "/").split("assets/")[-1]

        ts_list.append((fgid, fgid + tile_count - 1, cols, norm_img, root.attrib.get("name", "")))

    ts_list.sort(key=lambda x: x[0])

    def get_tile(gid):
        clean_gid = gid & 0x1FFFFFFF
        for fgid, lgid, cols, img, name in ts_list:
            if fgid <= clean_gid <= lgid:
                lid = clean_gid - fgid
                ax = lid % cols
                ay = lid // cols
                return img, ax, ay, name, lid
        return None

    ground = []
    water = []
    decorations = []
    obstacles = []
    bridge_tiles = set()
    chest_positions = []
    ordered_layers = []

    # Koleksi elemen lingkungan yang bergerak / bergoyang (foliage sway)
    foliage_trees = []
    foliage_trees_pink = []
    foliage_small_trees = []
    foliage_ambushes = []
    foliage_sunflowers = []
    foliage_bushes = []
    foliage_flowers = []
    foliage_grass_tufts = []
    chickens = []

    # 2. Ekstraksi layer dari Tiled
    for l in tmj["layers"]:
        lname = l["name"].lower()
        ltype = l["type"]
        if ltype != "tilelayer":
            continue
        data = l["data"]
        layer_tiles = []
        is_obs_layer = "obstacle" in lname

        for idx, gid in enumerate(data):
            if gid == 0:
                continue
            t = get_tile(gid)
            if not t:
                continue
            img, ax, ay, name, lid = t
            gx = idx % w
            gy = idx // w

            entry = {"x": gx, "y": gy, "src": img, "atlas_x": ax, "atlas_y": ay}
            clean_gid = gid & 0x1FFFFFFF

            if is_obs_layer:
                # Layer obstacle di Tiled adalah collision mask murni (logika game, bukan visual).
                obstacles.append({"x": gx, "y": gy, "src": "", "atlas_x": 0, "atlas_y": ay})
            else:
                # 1. Deteksi Ayam / Chicken (Free Chicken Sprites, firstgid=817)
                # PENTING: Hanya sprite ayam hidup (bukan Free_Chicken_House / kandang ayam)
                if (817 <= clean_gid < 825 or "free chicken sprites" in name.lower() or "free chicken sprites" in img.lower()) and "house" not in name.lower() and "house" not in img.lower():
                    chickens.append((gx, gy))
                    continue

                # 2. Deteksi elemen hidup yang bergoyang tertiup angin (wind sway)
                # BATU, KANDANG AYAM, RUMAH, JEMBATAN, PAGAR, & STRUKTUR 100% STATIS (TIDAK DIGOYANGKAN)
                is_swaying_foliage = False
                img_lower = img.lower()
                name_lower = name.lower()

                is_building_or_structure = any(
                    k in name_lower or k in img_lower
                    for k in ("house", "hut", "mansion", "tower", "clock", "fence", "bridge", "chest", "floor", "wall")
                )

                if is_building_or_structure:
                    is_swaying_foliage = False
                elif "basic_grass_biom" in img_lower and lid in (16, 17, 41, 42):
                    # Batu tetap statis di layer tanah
                    is_swaying_foliage = False
                elif "basic_grass_biom" in img_lower and lid == 1:  # Kanopi kiri pohon hijau
                    foliage_trees.append((gx, gy))
                    is_swaying_foliage = True
                elif "basic_grass_biom" in img_lower and lid == 2:  # Kanopi kanan pohon hijau
                    is_swaying_foliage = True
                elif "basic_grass_biom" in img_lower and lid == 3:  # Kanopi kiri pohon pink
                    foliage_trees_pink.append((gx, gy))
                    is_swaying_foliage = True
                elif "basic_grass_biom" in img_lower and lid == 4:  # Kanopi kanan pohon pink
                    is_swaying_foliage = True
                elif "basic_grass_biom" in img_lower and lid == 0:  # Kanopi pohon ramping kecil
                    foliage_small_trees.append((gx, gy))
                    is_swaying_foliage = True
                elif "basic_grass_biom" in img_lower and lid == 26:  # Kepala bunga matahari kuning
                    foliage_sunflowers.append((gx, gy))
                    is_swaying_foliage = True
                elif "basic_grass_biom" in img_lower and lid in (27, 28, 36, 37):  # Ambush semak berry/hijau/lebar
                    atype = "berry" if lid == 27 else ("green" if lid == 28 else "wide_bush")
                    foliage_ambushes.append({"x": gx, "y": gy, "src": img, "atlas_x": ax, "atlas_y": ay, "type": atype})
                    is_swaying_foliage = True
                elif ("basic_grass_biom" in img_lower and lid in (14, 15, 24, 25, 32, 33, 34)) or \
                     ("grass" in img_lower and lid in (62, 72, 73)):  # Bunga-bunga padang rumput
                    foliage_flowers.append({"x": gx, "y": gy, "src": img, "atlas_x": ax, "atlas_y": ay, "type": "flower"})
                    is_swaying_foliage = True
                elif ("basic_grass_biom" in img_lower and lid in (29, 30, 35, 43, 44)) or \
                     (img_lower.endswith("grass.png") and (55 <= lid <= 76 and lid not in (62, 72, 73))) or \
                     ((name_lower == "objects" or img_lower.endswith("objects.png")) and lid in (0, 1, 4, 5)):  # Rumpun & hiasan rumput (termasuk GID 58, 65, 74, dll)
                    foliage_grass_tufts.append({"x": gx, "y": gy, "src": img, "atlas_x": ax, "atlas_y": ay, "type": "grass"})
                    is_swaying_foliage = True

                if not is_swaying_foliage:
                    layer_tiles.append(entry)
                    if "water" in name.lower() or "water" in img.lower():
                        water.append(entry)
                        obstacles.append({"x": gx, "y": gy, "src": "", "atlas_x": 0, "atlas_y": ay})
                    elif "bridge" in name.lower() or "bridge" in img.lower():
                        bridge_tiles.add((gx, gy))
                        decorations.append(entry)
                    elif "tile layer 1" in lname:
                        ground.append(entry)
                    else:
                        decorations.append(entry)
                        if "chest" in name.lower() or "chest" in img.lower():
                            chest_positions.append((gx, gy))

        if not is_obs_layer and layer_tiles:
            ordered_layers.append({"name": l["name"], "tiles": layer_tiles})

    # Sel jembatan bukan obstacle
    final_obstacles = [o for o in obstacles if (o["x"], o["y"]) not in bridge_tiles]

    # Cari spawn yang valid di jalan atau rumput
    walkable_coords = set()
    for g in ground:
        walkable_coords.add((g["x"], g["y"]))
    walkable_coords.update(bridge_tiles)
    for o in final_obstacles:
        walkable_coords.discard((o["x"], o["y"]))

    # Pilih spawn point default yang nyaman & unik di jalan/rumput terbuka
    def pick_spawn(preferred_list):
        for pt in preferred_list:
            if pt in walkable_coords and pt not in used_spawns:
                return pt
        for pt in sorted(walkable_coords):
            if pt not in used_spawns:
                return pt
        return (18, 17)

    used_spawns = set()
    player_spawn = pick_spawn([(18, 17), (24, 18), (27, 18)])
    used_spawns.add(player_spawn)

    oyen_spawn = pick_spawn([(27, 10), (28, 10), (25, 12)])
    used_spawns.add(oyen_spawn)

    kuro_spawn = pick_spawn([(11, 4), (12, 5), (10, 6)])
    used_spawns.add(kuro_spawn)

    shiro_spawn = pick_spawn([(29, 20), (36, 20), (25, 19)])
    used_spawns.add(shiro_spawn)

    # Format data/map_tubes.json
    map_document = {
        "schema_version": 1,
        "name": "Map_From_Tiled_map_new",
        "cell_size": cs,
        "grid": {
            "min_x": 0,
            "min_y": 0,
            "width": w,
            "height": h
        },
        "ground_asset": "sprout/Grass.png",
        "layers": ordered_layers,
        "water": water,
        "ground": ground,
        "decorations": decorations,
        "obstacles": final_obstacles,
        "foliage": {
            "trees": foliage_trees,
            "trees_pink": foliage_trees_pink,
            "trees_small": foliage_small_trees,
            "ambushes": foliage_ambushes,
            "sunflowers": foliage_sunflowers,
            "bushes": foliage_bushes,
            "flowers": foliage_flowers,
            "grass_tufts": foliage_grass_tufts
        },
        "chickens": [{"x": cx, "y": cy} for cx, cy in chickens],
        "spawns": {
            "player": {"grid_x": player_spawn[0], "grid_y": player_spawn[1]},
            "npc_oyen": {"grid_x": oyen_spawn[0], "grid_y": oyen_spawn[1]},
            "npc_kuro": {"grid_x": kuro_spawn[0], "grid_y": kuro_spawn[1], "waypoints": [(kuro_spawn[0], kuro_spawn[1]), (kuro_spawn[0]+4, kuro_spawn[1])]},
            "npc_shiro": {"grid_x": shiro_spawn[0], "grid_y": shiro_spawn[1], "waypoints": [(shiro_spawn[0], shiro_spawn[1]), (shiro_spawn[0]+4, shiro_spawn[1])]},
            "chests": [
                {"x": pos[0], "y": pos[1], "item": ["health_potion", "item_sword", "item_shield", "health_potion"][i % 4]}
                for i, pos in enumerate(chest_positions)
            ] or [
                {"x": 27, "y": 2, "item": "health_potion"},
                {"x": 11, "y": 3, "item": "item_sword"},
                {"x": 41, "y": 24, "item": "item_shield"},
                {"x": 10, "y": 28, "item": "health_potion"}
            ]
        }
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(map_document, f, indent=2)

    print(f"Berhasil mengonversi {TMJ_PATH} -> {OUT_JSON}!")
    print(f"Dimensi Peta: {w} x {h} ({w*cs} x {h*cs} px)")
    print(f"Total Ground: {len(ground)}, Water: {len(water)}, Decorations: {len(decorations)}, Obstacles: {len(final_obstacles)}")
    print(f"Total Peti Harta: {len(map_document['spawns']['chests'])}")


if __name__ == "__main__":
    convert()

