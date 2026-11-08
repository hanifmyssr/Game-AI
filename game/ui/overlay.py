"""DebugOverlay: Unified AI Command Deck & Map Visualizer.

Menghubungkan Bilah Navigasi ala Web (NavRail), Wadah Inspektur Konten AI (InspectorDock),
dan Modal Pohon Universal Bebas Bug (UnifiedGraphModal) dengan game loop.
Mendukung mode Collapsible Drawer (Buka-Tutup) dengan tema Cozy Adventurer Journal.
"""

import math
from typing import Optional, Callable, Any, Dict, List
import pygame

from ..core import config
from ..ai.battle_ai import (
    ACTION_ATTACK,
    ACTION_HEAVY,
    ACTION_DEFEND,
    ACTION_POTION,
    calc_damage,
    MOVE_ORDERING_MODES,
    MOVE_ORDERING_OFF,
    MOVE_ORDERING_HEURISTIC,
)
from .nav_rail import NavRail
from .inspector_dock import InspectorDock
from .graph_modal import UnifiedGraphModal

MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1025)
MOUSEBUTTONUP = getattr(pygame, "MOUSEBUTTONUP", 1026)
MOUSEMOTION = getattr(pygame, "MOUSEMOTION", 1024)
KEYDOWN = getattr(pygame, "KEYDOWN", 768)
K_t = getattr(pygame, "K_t", 116)
K_TAB = getattr(pygame, "K_TAB", 9)
K_ESCAPE = getattr(pygame, "K_ESCAPE", 27)
SRCALPHA = getattr(pygame, "SRCALPHA", 0x00010000)


class DebugOverlay:
    """Manajer antarmuka terpadu (Cozy Adventurer Journal) dan visualisasi peta."""

    def __init__(self, events: Any, fonts: Dict[str, pygame.font.Font], app_ref: Optional[Any] = None):
        self.events = events
        self.fonts = fonts
        self.app = app_ref
        self.mode = "EXPLORATION"

        # 1. State Visualisasi Pathfinding (World Map)
        self.expanded_nodes: List[Any] = []
        self.path_nodes: List[Any] = []
        self.animation_time = 0.0
        self.expanded_reveal = 1.0
        self.path_reveal = 1.0
        self.visualization_active = False
        self.chasing_visualization = False
        self.show_costs = False
        self.last_expanded_count = 0
        self.last_time_ms = 0.0
        self.comparison_data: Optional[Dict[str, Any]] = None

        # 2. Inisialisasi Modul UI Baru (Web Nav Rail + Collapsible Inspector Dock)
        rail_rect = pygame.Rect(0, 0, config.NAV_RAIL_WIDTH, config.WINDOW_HEIGHT)
        self.nav_rail = NavRail(
            rail_rect,
            on_tab_changed=self._on_nav_tab_changed,
            on_tab_toggled=self._on_nav_tab_toggled,
        )

        dock_rect = pygame.Rect(config.NAV_RAIL_WIDTH, 0, config.INSPECTOR_WIDTH, config.WINDOW_HEIGHT)
        self.dock = InspectorDock(dock_rect, fonts, app_ref)

        # 3. Inisialisasi Visualizer Pohon Universal (UnifiedGraphModal)
        self.graph_modal = UnifiedGraphModal(fonts)
        self.tree_overlay = self.graph_modal

        # Callback sistem lama
        self.battle_system = None
        self.pre_battle_config = None
        self.pre_battle_stats = None
        self.pre_battle_algo = "HILL_CLIMBING"
        self.on_ls_algo_changed: Optional[Callable[[Any], None]] = None
        self.on_open_ai_inspector: Optional[Callable[[], Any]] = None

        if self.events and hasattr(self.events, "register_overlay"):
            self.events.register_overlay(self)

    def set_app(self, app_ref: Any) -> None:
        self.app = app_ref
        self.dock.app = app_ref
        for tab in self.dock.tabs.values():
            tab.app = app_ref

    def set_battle_system(self, battle_system: Any) -> None:
        self.battle_system = battle_system
        if self.battle_system:
            self.battle_system.record_tree = True

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        if mode == "EXPLORATION":
            if self.nav_rail.active_tab not in (1, 4, 5):
                self.nav_rail.set_active_tab(0)
        elif mode == "PRE_BATTLE":
            self.nav_rail.set_active_tab(3)
        elif mode == "BATTLE":
            self.nav_rail.set_active_tab(2)

    def _on_nav_tab_changed(self, tab_id: int) -> None:
        self.dock.set_active_tab(tab_id)

    def _on_nav_tab_toggled(self, tab_id: int) -> None:
        self.dock.toggle()

    def toggle_dock(self) -> None:
        self.dock.toggle()

    def on_resize(self, w: int, h: int) -> None:
        """Menyesuaikan ukuran elemen Nav Rail & Inspector Dock saat resolusi layar berubah."""
        self.nav_rail.resize(h)
        self.dock.resize(h)

    def set_pre_battle_data(self, config_dict: Any, stats: Any, algo_name: str = "HILL_CLIMBING") -> None:
        self.pre_battle_config = config_dict
        self.pre_battle_stats = stats
        self.pre_battle_algo = algo_name

    def set_comparison_data(self, data: Any) -> None:
        self.comparison_data = data

    def update_debug_data(self, new_expanded: List[Any], new_path: List[Any], time_ms: float, start_pos: Optional[Any] = None) -> None:
        self.expanded_nodes = list(new_expanded)
        self.path_nodes = list(new_path)
        self.last_expanded_count = len(new_expanded)
        self.last_time_ms = time_ms
        self.expanded_reveal = 1.0
        self.path_reveal = 1.0
        self.visualization_active = True

    def update_stats(self, count: int, time_ms: float) -> None:
        self.last_expanded_count = count
        self.last_time_ms = time_ms

    def start_path_animation(self) -> None:
        self.path_reveal = 0.0
        self.expanded_reveal = 0.0
        self.animation_time = 0.0
        self.visualization_active = True

    def stop_path_animation(self) -> None:
        self.visualization_active = False

    def on_camera_zoom(self) -> None:
        pass

    def set_chasing_visualization(self, chasing: bool) -> None:
        self.chasing_visualization = chasing

    def update_animation(self, dt: float) -> None:
        self.animation_time += dt
        if self.visualization_active:
            if self.expanded_reveal < 1.0:
                self.expanded_reveal = min(1.0, self.expanded_reveal + dt * 2.5)
            elif self.path_reveal < 1.0:
                self.path_reveal = min(1.0, self.path_reveal + dt * 3.5)

        self.dock.update(dt)

    def toggle_tree_overlay(self) -> None:
        tree_data = None
        if self.battle_system:
            if getattr(self.battle_system, "last_ai_stats", None):
                tree_data = self.battle_system.last_ai_stats.get("tree", None)
            if not tree_data and hasattr(self.battle_system, "ai_solver"):
                tree_data = getattr(self.battle_system.ai_solver, "last_tree", None)

        if tree_data:
            self.graph_modal.set_tree(tree_data)

        self.graph_modal.toggle()
        if self.battle_system:
            self.battle_system.record_tree = self.graph_modal.visible

    # ------------------------------------------------------------------ #
    # Drawing: Peta Dunia Game (World Space)
    # ------------------------------------------------------------------ #
    def draw_world(self, surface: pygame.Surface, camera: Any, map_data: Any, _npc: Any, _player: Any) -> None:
        if self.mode != "EXPLORATION" or not self.visualization_active:
            return

        tile_size = map_data.cell_size
        exp_surf = pygame.Surface(surface.get_size(), SRCALPHA)
        expanded_position = len(self.expanded_nodes) * self.expanded_reveal
        pulse_alpha = int(75 + 35 * (0.5 + 0.5 * math.sin(self.animation_time * 2.0)))

        for index, node_pos in enumerate(self.expanded_nodes):
            node_reveal = max(0.0, min(1.0, expanded_position - index))
            if node_reveal <= 0.0:
                continue
            if not (0 <= node_pos[0] < map_data.width and 0 <= node_pos[1] < map_data.height):
                continue
            center = map_data.world_to_px(node_pos)
            half = tile_size / 2.0
            topleft = (center[0] - half, center[1] - half)
            screen_pos = camera.world_to_screen(topleft[0], topleft[1])
            sz = tile_size * camera.zoom
            rect = (screen_pos[0], screen_pos[1], sz, sz)
            expanded_alpha = int(pulse_alpha * node_reveal)
            expanded_fill = (*config.COLOR_EXPANDED_FILL[:3], expanded_alpha)
            expanded_border = (*config.COLOR_EXPANDED_BORDER[:3], min(255, expanded_alpha + 70))
            pygame.draw.rect(exp_surf, expanded_fill, rect)
            pygame.draw.rect(exp_surf, expanded_border, rect, 1)

            if self.show_costs:
                cost = map_data.get_step_cost(node_pos)
                cost_text = self.fonts["sm"].render(f"{cost:.1f}", True, (255, 255, 255))
                cost_text.set_alpha(int(255 * node_reveal))
                cost_bg = cost_text.get_rect(center=(int(screen_pos[0] + sz / 2), int(screen_pos[1] + sz / 2)))
                pygame.draw.rect(exp_surf, (80, 0, 0, int(190 * node_reveal)), cost_bg.inflate(4, 2), border_radius=2)
                exp_surf.blit(cost_text, cost_bg)

        surface.blit(exp_surf, (0, 0))

        if self.path_nodes:
            path_surf = pygame.Surface(surface.get_size(), SRCALPHA)
            path_position = len(self.path_nodes) * self.path_reveal
            for index, node_pos in enumerate(self.path_nodes):
                node_reveal = max(0.0, min(1.0, path_position - index))
                if node_reveal <= 0.0:
                    continue
                if not (0 <= node_pos[0] < map_data.width and 0 <= node_pos[1] < map_data.height):
                    continue
                center = map_data.world_to_px(node_pos)
                half = tile_size / 2.0
                topleft = (center[0] - half, center[1] - half)
                screen_pos = camera.world_to_screen(topleft[0], topleft[1])
                sz = tile_size * camera.zoom
                rect = (screen_pos[0], screen_pos[1], sz, sz)
                path_alpha = int((55 + 80 * self.path_reveal) * node_reveal)
                path_fill = (*config.COLOR_PATH[:3], path_alpha)
                path_border = (*config.COLOR_PATH_BORDER[:3], min(255, path_alpha + 55))
                pygame.draw.rect(path_surf, path_fill, rect)
                pygame.draw.rect(path_surf, path_border, rect, 1)

            surface.blit(path_surf, (0, 0))

    # ------------------------------------------------------------------ #
    # Drawing: Bilah UI Kiri (Nav Rail & Collapsible Inspector Drawer)
    # ------------------------------------------------------------------ #
    def draw_ui(self, surface: pygame.Surface) -> None:
        # 1. Gambar Nav Rail di kolom x: 0..64 (selalu tampil sebagai anchor)
        self.nav_rail.draw(surface)

        # 2. Gambar Inspector Dock hanya jika sedang terbuka (x: 64..420)
        if self.dock.is_open:
            self.dock.draw(surface)

    # ------------------------------------------------------------------ #
    # Event Handling
    # ------------------------------------------------------------------ #
    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.graph_modal.visible:
            return self.graph_modal.handle_event(event)

        if event.type == KEYDOWN:
            if event.key == K_t:
                self.toggle_tree_overlay()
                return True
            if event.key == K_TAB:
                self.toggle_dock()
                return True
            if event.key == K_ESCAPE and self.dock.is_open:
                self.dock.close()
                return True

        # Nav Rail menangani event klik & hover
        if self.nav_rail.handle_event(event):
            return True

        # Inspector Dock menangani event saat terbuka
        if self.dock.is_open:
            if self.dock.handle_event(event):
                return True

        # Blokir klik mouse di area yang sedang tertutup panel UI
        if hasattr(event, "pos"):
            active_w = config.TOTAL_DOCK_WIDTH if self.dock.is_open else config.NAV_RAIL_WIDTH
            if event.pos[0] < active_w:
                return True

        return False
