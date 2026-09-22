"""MapData: data peta + surface render, port dari Scripts/map/map_data.gd.

Data asli (grid, tiles, obstacle) di-decode dari map.tscn Godot ke
`data/map.json` sehingga port ini berdiri sendiri (tanpa Godot).
"""

import json
import os

import pygame

from . import config

SRCALPHA = getattr(pygame, "SRCALPHA", 0x00010000)


class MapData:
    def __init__(self, map_file=None):
        self.map_file = map_file or config.MAP_FILE
        self.cell_size = 16
        self.min_x = 0
        self.min_y = 0
        self.width = 0
        self.height = 0

        self.ground = {}          # (nx, ny) -> (atlas_x, atlas_y)
        self.obstacles = {}       # (nx, ny) -> (src_name, atlas_x, atlas_y)
        self.ground_set = set()
        self.obstacle_set = set()
        self.dirt_road_set = set()
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

        self.ground = {}
        self.obstacles = {}
        self.ground_set = set()
        self.obstacle_set = set()
        self.dirt_road_set = set()

        for c in doc["ground"]:
            key = (c["x"] - self.min_x, c["y"] - self.min_y)
            ax, ay = c["atlas_x"], c["atlas_y"]
            self.ground[key] = (ax, ay)
            self.ground_set.add(key)

            # (10,11) dan (10,12) adalah rumput; (11,11) dan (11,12) adalah jalan tanah.
            if ax == 11:
                self.dirt_road_set.add(key)

        for c in doc["obstacles"]:
            key = (c["x"] - self.min_x, c["y"] - self.min_y)
            self.obstacles[key] = (c.get("src", ""), c["atlas_x"], c["atlas_y"])
            self.obstacle_set.add(key)

        # Sel yang bisa dilalui: seluruh sel tanah dikurangi seluruh rintangan
        self.walkable_set = set(self.ground_set) - self.obstacle_set

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

    def is_grass_tile(self, pos):
        return tuple(pos) not in self.dirt_road_set

    def get_step_cost(self, pos):
        """Cost langkah: 0.5 untuk jalan tanah, 1.0 untuk rumput."""
        if self.is_dirt_road(pos):
            return 0.5
        return 1.0

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

    def px_to_world(self, world_pos):
        nx = int((world_pos[0] - self.cell_size / 2.0) // self.cell_size)
        ny = int((world_pos[1] - self.cell_size / 2.0) // self.cell_size)
        return (nx, ny)

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
        obstacle_surf = pygame.Surface(size, SRCALPHA).convert_alpha()

        tileset = pygame.image.load(
            os.path.join(config.ASSET_DIR, "tileset_ground.png")
        ).convert_alpha()

        # cache sub-surface per atlas coord untuk kecepatan
        cache_ground = {}
        for key, (ax, ay) in self.ground.items():
            sub = cache_ground.get((ax, ay))
            if sub is None:
                sub = tileset.subsurface((ax * cs, ay * cs, cs, cs))
                cache_ground[(ax, ay)] = sub
            ground_surf.blit(sub, (key[0] * cs, key[1] * cs))

        cache_obs = {}
        for key, (src, ax, ay) in self.obstacles.items():
            inner = cache_obs.get(src)
            if inner is None:
                inner = pygame.image.load(
                    os.path.join(config.ASSET_DIR, src)
                ).convert_alpha()
                cache_obs[src] = inner
            obstacle_surf.blit(inner, (key[0] * cs, key[1] * cs), (ax * cs, ay * cs, cs, cs))

        self._ground_surface = ground_surf
        self._obstacle_surface = obstacle_surf
        return ground_surf, obstacle_surf

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