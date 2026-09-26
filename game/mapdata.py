"""MapData: data peta + surface render, port dari Scripts/map/map_data.gd.

Data asli (grid, tiles, obstacle) di-decode dari map.tscn Godot ke
`data/map_tubes.json` sehingga port ini berdiri sendiri (tanpa Godot).
"""

import json
import os

import pygame

from . import config


def _is_dirt_road_cell(cell_info):
    """Cek apakah ubin adalah jalan tanah/jembatan (cost 1.0) atau rumput/medan (cost 2.0)."""
    if not cell_info:
        return False
    src, ax, ay = cell_info
    if "Wood Bridge" in src:
        return True
    if "Ext_10a_DEMO" in src:
        if (ax, ay) == (11, 12) or (0 <= ax <= 11 and 2 <= ay <= 4):
            return True
    return False


def _is_bridge_cell(cell_info):
    """Cek apakah ubin adalah jembatan."""
    if not cell_info:
        return False
    src, ax, ay = cell_info
    return "Wood Bridge" in src


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
        self.ground_set = set()
        self.obstacle_set = set()
        self.walkable_set = set()

        self._ground_surface = None
        self._obstacle_surface = None

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

        # Identifikasi sel jembatan dari seluruh layer
        bridge_set = set()
        for layer_dict in (self.ground, self.decorations, self.water, self.obstacles):
            for key, cell_info in layer_dict.items():
                if _is_bridge_cell(cell_info):
                    bridge_set.add(key)

        self.ground_set.update(self.ground)
        self.ground_set.update(bridge_set)
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

    def get_step_cost(self, pos):
        pos = tuple(pos)
        for layer in (self.decorations, self.ground, self.water, self.obstacles):
            if pos in layer and _is_dirt_road_cell(layer[pos]):
                return 1.0
        return 2.0

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

        ground_surf = pygame.Surface(size).convert()
        obstacle_surf = pygame.Surface(size, pygame.SRCALPHA).convert_alpha()

        self._blit_layer(ground_surf, self.water)
        self._blit_layer(ground_surf, self.ground)
        self._blit_layer(ground_surf, self.decorations)
        self._blit_layer(obstacle_surf, self.obstacles)

        self._ground_surface = ground_surf
        self._obstacle_surface = obstacle_surf
        return ground_surf, obstacle_surf

    def _blit_layer(self, target, cells):
        cs = self.cell_size
        cache = {}
        for key, (src, atlas_x, atlas_y) in cells.items():
            image = cache.get(src)
            if image is None:
                image = pygame.image.load(
                    os.path.join(config.ASSET_DIR, src.replace("/", os.sep))
                ).convert_alpha()
                cache[src] = image
            target.blit(
                image,
                (key[0] * cs, key[1] * cs),
                (atlas_x * cs, atlas_y * cs, cs, cs),
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