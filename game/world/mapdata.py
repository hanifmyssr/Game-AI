"""MapData: data peta + surface render, port dari Scripts/map/map_data.gd.

Data asli (grid, tiles, obstacle) di-decode dari map.tscn Godot ke
`data/map_tubes.json` sehingga port ini berdiri sendiri (tanpa Godot).
"""

import json
import os
import sys
from pathlib import Path

import pygame

try:
    from ..core import config
except (ImportError, ValueError):
    # Fallback saat berkas dibuka/dijalankan langsung di luar konteks paket 'game'
    _root = Path(__file__).resolve().parent.parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from game.core import config


def _is_dirt_road_cell(cell_info):
    """Cek apakah ubin adalah jalan tanah/jembatan (cost 1.0) atau rumput/medan (cost 2.0)."""
    if not cell_info:
        return False
    src = cell_info[0]
    ax = cell_info[1]
    ay = cell_info[2]
    if "Wood Bridge" in src or "Wood_Bridge" in src:
        return True
    if "Tilled_Dirt" in src or "Tilled Dirt" in src or "Paths" in src or "Wooden path" in src or "Wooden_path" in src:
        return True
    if "Ext_10a_DEMO" in src:
        if (ax, ay) == (11, 12) or (0 <= ax <= 11 and 2 <= ay <= 4):
            return True
    return False


def _is_bridge_cell(cell_info):
    """Cek apakah ubin adalah jembatan."""
    if not cell_info:
        return False
    src = cell_info[0]
    return "Wood Bridge" in src or "Wood_Bridge" in src


class MapData:
    def __init__(self, map_file=None):
        self.map_file = map_file or config.MAP_FILE
        self.cell_size = 16
        self.min_x = 0
        self.min_y = 0
        self.width = 0
        self.height = 0
        self.ground_asset = "tubes/Ext_10a_DEMO.png"

        self.water = {}
        self.ground = {}        # (nx, ny) -> (src_name, atlas_x, atlas_y)
        self.decorations = {}
        self.obstacles = {}
        self.ordered_layers = []
        self.foliage = {"trees": [], "bushes": [], "flowers": []}
        self.ground_set = set()
        self.obstacle_set = set()
        self.walkable_set = set()
        self.dirt_road_set = set()

        self._ground_surface = None
        self._obstacle_surface = None
        self._ground_surfaces = []

        self.load_map_data()

    # ------------------------------------------------------------------ #
    def load_map_data(self):
        with open(self.map_file, encoding="utf-8") as f:
            doc = json.load(f)

        self.cell_size = doc.get("cell_size", 16)
        grid = doc["grid"]
        self.min_x = grid["min_x"]
        self.min_y = grid["min_y"]
        self.width = grid["width"]
        self.height = grid["height"]
        self.ground_asset = doc.get("ground_asset", "tubes/Ext_10a_DEMO.png")

        self.water = {}
        self.ground = {}
        self.decorations = {}
        self.obstacles = {}
        self.ground_set = set()
        self.obstacle_set = set()

        self._load_layer(doc["ground"], self.ground)
        self._load_layer(doc.get("water", []), self.water)
        self._load_layer(doc.get("decorations", []), self.decorations)
        self._load_layer(doc.get("obstacles", []), self.obstacles)
        self.foliage = doc.get("foliage", {"trees": [], "bushes": [], "flowers": []})
        self.chickens = doc.get("chickens", [])
        self.chests_data = doc.get("spawns", {}).get("chests", [])

        # Identifikasi sel jembatan dari seluruh layer
        bridge_set = set()
        for layer_dict in (self.ground, self.decorations, self.water, self.obstacles):
            for key, cell_info in layer_dict.items():
                if _is_bridge_cell(cell_info):
                    bridge_set.add(key)

        # Identifikasi seluruh sel jalan tanah & jembatan (bobot langkah 1.0)
        self.dirt_road_set = set()
        for layer_dict in (self.ground, self.decorations, self.water, self.obstacles):
            for key, cell_info in layer_dict.items():
                if _is_dirt_road_cell(cell_info):
                    self.dirt_road_set.add(key)

        # Urutan layer berlapis sesuai Tiled (Layer 1 -> Layer 2 -> Layer 3)
        self.ordered_layers = []
        if "layers" in doc:
            for l_doc in doc["layers"]:
                l_tiles = []
                for item in l_doc.get("tiles", []):
                    pos = (int(item["x"]), int(item["y"]))
                    cell_tuple = (
                        item.get("src", ""),
                        int(item.get("atlas_x", 0)),
                        int(item.get("atlas_y", 0)),
                    )
                    l_tiles.append((pos, cell_tuple))
                    if _is_bridge_cell(cell_tuple):
                        bridge_set.add(pos)
                    if _is_dirt_road_cell(cell_tuple):
                        self.dirt_road_set.add(pos)
                    if cell_tuple[0] and "water" not in cell_tuple[0].lower():
                        self.ground_set.add(pos)
                self.ordered_layers.append(l_tiles)

        self.ground_set.update(self.ground)
        self.ground_set.update(bridge_set)
        self.bridge_set = bridge_set
        self.obstacle_set.update(self.obstacles)
        # Sel jembatan dapat dilalui (bukan obstacle)
        self.obstacle_set.difference_update(bridge_set)

        # walkable = (ground atau jembatan) minus obstacle dan water (kecuali jembatan)
        self.walkable_set = set()
        for key in self.ground_set:
            if key in self.obstacle_set:
                continue
            if key in self.water and key not in bridge_set:
                continue
            self.walkable_set.add(key)

    def _load_layer(self, cells, target):
        for cell in cells:
            key = (cell["x"] - self.min_x, cell["y"] - self.min_y)
            target[key] = (
                cell.get("src", self.ground_asset),
                cell["atlas_x"],
                cell["atlas_y"],
            )

    # ------------------------------------------------------------------ #
    # Query grid
    # ------------------------------------------------------------------ #
    def is_valid_position(self, pos):
        return tuple(pos) in self.ground_set

    def is_walkable(self, pos):
        return tuple(pos) in self.walkable_set

    def is_obstacle(self, pos):
        return not self.is_walkable(pos)

    def is_dirt_road(self, pos):
        return tuple(pos) in self.dirt_road_set

    def get_surface_type(self, pos):
        """Mengembalikan jenis permukaan pada posisi sel ('bridge', 'dirt', atau 'grass')."""
        t = tuple(pos)
        if hasattr(self, "bridge_set") and t in self.bridge_set:
            return "bridge"
        if t in self.dirt_road_set:
            return "dirt"
        return "grass"

    def get_step_cost(self, pos):
        return 1.0 if tuple(pos) in self.dirt_road_set else 2.0

    def get_map_center(self):
        return (self.width // 2, self.height // 2)

    def get_neighbors(self, pos):
        result = []
        for dx, dy in config.DIRS:
            target = (pos[0] + dx, pos[1] + dy)
            if self.is_walkable(target):
                result.append(target)
        return result

    # ------------------------------------------------------------------ #
    # Konversi koordinat
    # ------------------------------------------------------------------ #
    def world_to_px(self, grid_pos):
        """Tengah sel grid dalam piksel dunia+ (0,0 di kiri-atas peta)."""
        return (
            grid_pos[0] * self.cell_size + self.cell_size / 2.0,
            grid_pos[1] * self.cell_size + self.cell_size / 2.0,
        )

    def map_to_world(self, grid_pos):
        raw_x = grid_pos[0] + self.min_x
        raw_y = grid_pos[1] + self.min_y
        return (
            raw_x * self.cell_size + self.cell_size / 2.0,
            raw_y * self.cell_size + self.cell_size / 2.0,
        )

    def world_to_map(self, world_pos):
        return (
            int(world_pos[0] // self.cell_size) - self.min_x,
            int(world_pos[1] // self.cell_size) - self.min_y,
        )

    def px_to_world(self, world_pos):
        return (
            int(world_pos[0] // self.cell_size),
            int(world_pos[1] // self.cell_size),
        )

    # ------------------------------------------------------------------ #
    # Spawn point terdekat (BFS, setara get_valid_spawn_point di GDScript)
    # ------------------------------------------------------------------ #
    def get_valid_spawn_point(self, preferred):
        preferred = tuple(preferred)
        if self.is_walkable(preferred):
            return preferred

        visited = {preferred: True}
        queue = [preferred]

        while queue:
            curr = queue.pop(0)
            if self.is_walkable(curr):
                return curr
            for dx, dy in config.DIRS:
                n = (curr[0] + dx, curr[1] + dy)
                if n not in visited and self.is_valid_position(n):
                    visited[n] = True
                    queue.append(n)

        if self.walkable_set:
            return next(iter(self.walkable_set))
        return (0, 0)

    # ------------------------------------------------------------------ #
    # Pre-render surface peta
    # ------------------------------------------------------------------ #
    def build_surfaces(self):
        cs = self.cell_size
        size = (self.width * cs, self.height * cs)
        has_display = pygame.display.get_surface() is not None

        # Pre-render 4 frame animasi air untuk efisiensi instan (0.00 ms runtime)
        self._ground_surfaces = []
        for frame in range(4):
            surf = pygame.Surface(size)
            if has_display:
                surf = surf.convert()
            if self.ordered_layers:
                for l_tiles in self.ordered_layers:
                    self._blit_layer(surf, l_tiles, water_frame_override=frame)
            else:
                self._blit_layer(surf, self.water, water_frame_override=frame)
                self._blit_layer(surf, self.ground)
                self._blit_layer(surf, self.decorations)
            self._ground_surfaces.append(surf)

        obstacle_surf = pygame.Surface(size, pygame.SRCALPHA)
        if has_display:
            obstacle_surf = obstacle_surf.convert_alpha()
        # Lewati ubin air pada obstacle surface agar tidak menimpa animasi riak air
        self._blit_layer(obstacle_surf, self.obstacles, skip_water=True)

        self._ground_surface = self._ground_surfaces[0]
        self._obstacle_surface = obstacle_surf
        return self._ground_surface, obstacle_surf

    def get_ground_surface(self, frame=0):
        if not self._ground_surfaces:
            self.build_surfaces()
        return self._ground_surfaces[frame % len(self._ground_surfaces)]

    def _blit_layer(self, target, cells, water_frame_override=None, skip_water=False):
        cs = self.cell_size
        has_display = pygame.display.get_surface() is not None
        cache = {}
        cell_items = cells.items() if isinstance(cells, dict) else cells
        for key, (src, atlas_x, atlas_y) in cell_items:
            if not src:
                continue
            if skip_water and "Water" in src:
                continue
            image = cache.get(src)
            if image is None:
                img_path = os.path.join(config.ASSET_DIR, src.replace("/", os.sep))
                raw_img = pygame.image.load(img_path)
                image = raw_img.convert_alpha() if has_display else raw_img
                cache[src] = image
            ax = atlas_x
            ay = atlas_y
            if water_frame_override is not None and "Water" in src:
                ax = water_frame_override
            target.blit(
                image,
                (key[0] * cs, key[1] * cs),
                (ax * cs, ay * cs, cs, cs),
            )

    @property
    def ground_surface(self):
        if self._ground_surface is None:
            self.build_surfaces()
        return self._ground_surface

    @property
    def obstacle_surface(self):
        if self._obstacle_surface is None:
            self.build_surfaces()
        return self._obstacle_surface

    def map_px_size(self):
        return (self.width * self.cell_size, self.height * self.cell_size)