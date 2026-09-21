"""Mesin pencarian jalur: PathNode, SearchContract, GridManager, UCS, dan A*.

Port dari Scripts/Pathfinding & Scripts/Core pada project Godot.
Posisi grid direpresentasikan sebagai tuple (x, y).
"""

import time
import math


# --------------------------------------------------------------------------- #
# TSK-03: PathNode
# --------------------------------------------------------------------------- #
class PathNode:
    """Data node pencarian: pos, g(n), h(n), f(n), parent."""

    __slots__ = ("pos", "g", "h", "f", "parent")

    def __init__(self, pos, g=0.0, h=0.0, parent=None):
        self.pos = tuple(pos)
        self.g = g
        self.h = h
        self.f = g + h
        self.parent = parent

    def update_scores(self, new_g, new_h, new_parent=None):
        self.g = new_g
        self.h = new_h
        self.f = new_g + new_h
        if new_parent is not None:
            self.parent = new_parent

    def __repr__(self):
        return f"PathNode(pos={self.pos}, g={self.g:.1f}, h={self.h:.1f}, f={self.f:.1f})"


# --------------------------------------------------------------------------- #
# TSK-04: SearchContract
# --------------------------------------------------------------------------- #
class SearchContract:
    """Standar format dictionary hasil pencarian untuk UI/statistik."""

    @staticmethod
    def create_result(path=None, visited_nodes=None, total_expanded=0, execution_time_ms=0.0, total_cost=0.0):
        return {
            "path": list(path) if path else [],
            "visited_nodes": list(visited_nodes) if visited_nodes else [],
            "total_expanded": total_expanded,
            "execution_time_ms": execution_time_ms,
            "total_cost": total_cost,
        }

    @staticmethod
    def create_empty_result():
        return SearchContract.create_result([], [], 0, 0.0, 0.0)


# --------------------------------------------------------------------------- #
# GridManager
# --------------------------------------------------------------------------- #
class GridManager:
    """Wrapper tipis di atas MapData, menyamai GridManager.gd."""

    def __init__(self, map_data=None):
        self.map_data = map_data

    def is_walkable(self, pos):
        return self.map_data.is_walkable(pos) if self.map_data else False

    def get_neighbors(self, pos):
        return self.map_data.get_neighbors(pos) if self.map_data else []

    def get_step_cost(self, _pos):
        return 1.0

    def map_to_world(self, grid_pos):
        return self.map_data.map_to_world(grid_pos) if self.map_data else (0, 0)

    def world_to_map(self, world_pos):
        return self.map_data.world_to_map(world_pos) if self.map_data else (0, 0)


# --------------------------------------------------------------------------- #
# Fungsi Heuristik (TSK-06)
# --------------------------------------------------------------------------- #
def manhattan_distance(a, b):
    return float(abs(a[0] - b[0]) + abs(a[1] - b[1]))


def euclidean_distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def chebyshev_distance(a, b):
    return float(max(abs(a[0] - b[0]), abs(a[1] - b[1])))


HEURISTICS = {
    "MANHATTAN": manhattan_distance,
    "EUCLIDEAN": euclidean_distance,
    "CHEBYSHEV": chebyshev_distance,
}


def reconstruct_path(node):
    path = []
    cur = node
    while cur is not None:
        path.append(cur.pos)
        cur = cur.parent
    path.reverse()
    return path


# --------------------------------------------------------------------------- #
# TSK-05: Uniform Cost Search
# --------------------------------------------------------------------------- #
class UCS:
    """Uniform Cost Search: f(n) = g(n), h(n) = 0."""

    @staticmethod
    def search(start, target, grid_manager):
        start_time = time.perf_counter()

        if not grid_manager.is_walkable(target):
            return SearchContract.create_empty_result()

        open_list = [PathNode(start, 0.0, 0.0, None)]
        closed_list = set()
        all_nodes = {tuple(start): open_list[0]}

        while open_list:
            open_list.sort(key=lambda n: (n.g,))
            current = open_list.pop(0)

            if current.pos in closed_list:
                continue

            closed_list.add(current.pos)

            if current.pos == tuple(target):
                final_path = reconstruct_path(current)
                end_time = time.perf_counter()
                return SearchContract.create_result(
                    final_path,
                    list(closed_list),
                    len(closed_list),
                    (end_time - start_time) * 1000.0,
                    current.g,
                )

            for neighbor_pos in grid_manager.get_neighbors(current.pos):
                if neighbor_pos in closed_list:
                    continue
                step_cost = grid_manager.get_step_cost(neighbor_pos)
                tentative_g = current.g + step_cost

                if neighbor_pos not in all_nodes:
                    node = PathNode(neighbor_pos, tentative_g, 0.0, current)
                    all_nodes[neighbor_pos] = node
                    open_list.append(node)
                else:
                    existing = all_nodes[neighbor_pos]
                    if tentative_g < existing.g:
                        existing.update_scores(tentative_g, 0.0, current)

        end_time = time.perf_counter()
        return SearchContract.create_result(
            [],
            list(closed_list),
            len(closed_list),
            (end_time - start_time) * 1000.0,
        )


# --------------------------------------------------------------------------- #
# TSK-06: A* Search
# --------------------------------------------------------------------------- #
class AStarAlgorithm:
    """A*: f(n) = g(n) + h(n), mendukung Manhattan/Euclidean/Chebyshev.

    Tie-breaking: jika f sama, node dengan h lebih kecil diprioritaskan
    (sama persis dengan implementasi GDScript).
    """

    @staticmethod
    def search(start, target, grid_manager, h_func):
        start_time = time.perf_counter()

        if not grid_manager.is_walkable(target):
            return SearchContract.create_empty_result()

        open_list = [PathNode(start, 0.0, h_func(start, target), None)]
        closed_list = set()
        all_nodes = {tuple(start): open_list[0]}

        while open_list:
            open_list.sort(key=lambda n: (n.f, n.h))
            current = open_list.pop(0)

            if current.pos in closed_list:
                continue

            closed_list.add(current.pos)

            if current.pos == tuple(target):
                final_path = reconstruct_path(current)
                end_time = time.perf_counter()
                return SearchContract.create_result(
                    final_path,
                    list(closed_list),
                    len(closed_list),
                    (end_time - start_time) * 1000.0,
                    current.g,
                )

            for neighbor_pos in grid_manager.get_neighbors(current.pos):
                if neighbor_pos in closed_list:
                    continue

                step_cost = grid_manager.get_step_cost(neighbor_pos)
                tentative_g = current.g + step_cost
                neighbor_h = h_func(neighbor_pos, target)

                if neighbor_pos not in all_nodes:
                    node = PathNode(neighbor_pos, tentative_g, neighbor_h, current)
                    all_nodes[neighbor_pos] = node
                    open_list.append(node)
                else:
                    existing = all_nodes[neighbor_pos]
                    if tentative_g < existing.g:
                        existing.update_scores(tentative_g, neighbor_h, current)

        end_time = time.perf_counter()
        return SearchContract.create_result(
            [],
            list(closed_list),
            len(closed_list),
            (end_time - start_time) * 1000.0,
        )