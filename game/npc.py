"""NPC (kucing pengejar): port dari Scripts/npc/npc.gd.

Menghitung ulang rute setiap kali player berpindah ubin atau algoritma
diganti, lalu mengejar player selangkah demi selangkah selama mode chase.
"""

from . import config
from .search import AStarAlgorithm, UCS, GridManager, HEURISTICS

ALGO_TO_SEARCH = None


def _build_dispatch():
    def ucs(start, target, gm, h):
        return UCS.search(start, target, gm)

    def astar(hname):
        h = HEURISTICS[hname]

        def run(start, target, gm, _h):
            return AStarAlgorithm.search(start, target, gm, h)

        return run

    return {
        "UCS": ucs,
        "A_STAR_MANHATTAN": astar("MANHATTAN"),
        "A_STAR_EUCLIDEAN": astar("EUCLIDEAN"),
        "A_STAR_CHEBYSHEV": astar("CHEBYSHEV"),
    }


class NPC:
    def __init__(self, map_data, events, player):
        self.map = map_data
        self.events = events
        self.player = player

        self.algorithm = "A_STAR_MANHATTAN"
        self.dispatch = _build_dispatch()
        self.grid_manager = GridManager(map_data)

        self.chasing = False
        self.grid = (0, 0)
        self.px = 0.0
        self.py = 0.0
        self.moving = False
        self.move_t = 0.0
        self.frame_from = (0.0, 0.0)
        self.frame_to = (0.0, 0.0)

        self.chase_timer = 0.0
        self.current_path = []

        self._spawn()
        self.find_path(self.player.grid)

    # ------------------------------------------------------------------ #
    def _spawn(self):
        target_preferred = (
            self.player.grid[0] + 4,
            self.player.grid[1] + 4,
        )
        self.grid = self.map.get_valid_spawn_point(target_preferred)
        self.px, self.py = self.map.world_to_px(self.grid)
        self.frame_from = (self.px, self.py)
        self.frame_to = (self.px, self.py)

    # ------------------------------------------------------------------ #
    def update(self, dt):
        if self.moving:
            self.move_t += dt / config.NPC_STEP_DURATION
            if self.move_t >= 1.0:
                self.move_t = 1.0
                self.moving = False
            ease = self.move_t * self.move_t * (3.0 - 2.0 * self.move_t)
            self.px = self.frame_from[0] + (self.frame_to[0] - self.frame_from[0]) * ease
            self.py = self.frame_from[1] + (self.frame_to[1] - self.frame_from[1]) * ease
            if not self.moving:
                self.px, self.py = self.frame_to
                self._on_movement_finished()

        if self.chasing and not self.moving:
            self.chase_timer += dt
            if self.chase_timer >= config.NPC_CHASE_INTERVAL:
                self.chase_timer = 0.0
                self.move_one_step_towards(self.player.grid)

    def _on_movement_finished(self):
        if self.chasing and self.grid != self.player.grid:
            self.move_one_step_towards(self.player.grid)

    # ------------------------------------------------------------------ #
    def toggle_chase(self):
        self.chasing = not self.chasing
        if self.chasing:
            self.chase_timer = 0.0
            self.move_one_step_towards(self.player.grid)

    def set_algorithm(self, algo_name):
        self.algorithm = algo_name
        self.find_path(self.player.grid)

    def on_player_moved(self, player_grid):
        result = self.find_path(player_grid)
        if self.chasing and not self.moving:
            path = result.get("path", [])
            if len(path) > 1:
                self.move_to_grid(path[1])

    # ------------------------------------------------------------------ #
    def find_path(self, target_pos):
        target_pos = tuple(target_pos)
        run = self.dispatch.get(self.algorithm, self.dispatch["A_STAR_MANHATTAN"])
        result = run(self.grid, target_pos, self.grid_manager, None)

        path = result.get("path", [])
        self.current_path = path
        self.events.path_calculated(
            path,
            result.get("visited_nodes", []),
            result.get("execution_time_ms", 0.0),
        )
        return result

    def move_one_step_towards(self, target_grid_pos):
        if self.moving or self.grid == tuple(target_grid_pos):
            return
        result = self.find_path(target_grid_pos)
        path = result.get("path", [])
        if len(path) > 1:
            self.move_to_grid(path[1])

    def move_to_grid(self, target_grid):
        target_grid = tuple(target_grid)
        self.grid = target_grid
        target_px, target_py = self.map.world_to_px(target_grid)
        self.frame_from = (self.px, self.py)
        self.frame_to = (target_px, target_py)
        self.move_t = 0.0
        self.moving = True