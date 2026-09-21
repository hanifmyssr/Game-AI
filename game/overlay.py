"""DebugOverlay: port dari Scripts/UI/DebugOverlay.gd.

Menampilkan dropdown pemilihan algoritma, panel statistik, dan visualisasi
world-space (node yang diekspansi + jalur terpendek).
"""

import pygame
from pygame.locals import MOUSEBUTTONDOWN

from . import config


class Dropdown:
    def __init__(self, rect, labels, on_select):
        self.rect = pygame.Rect(rect)
        self.labels = labels
        self.on_select = on_select
        self.selected = 0
        self.open = False

    @property
    def option_height(self):
        return max(self.rect.height, 22)

    def menu_rect(self):
        w = self.rect.width
        h = self.option_height * len(self.labels)
        return pygame.Rect(self.rect.x, self.rect.bottom + 2, w, h)

    def handle_event(self, event):
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            if self.open:
                menu = self.menu_rect()
                if menu.collidepoint(event.pos):
                    idx = (event.pos[1] - menu.y) // self.option_height
                    if 0 <= idx < len(self.labels):
                        self.selected = idx
                        self.open = False
                        if self.on_select:
                            self.on_select(idx)
                    return True
                if self.rect.collidepoint(event.pos):
                    self.open = False
                    return True
                self.open = False
                return True
            else:
                if self.rect.collidepoint(event.pos):
                    self.open = True
                    return True
        return False

    def draw(self, surface, fonts):
        panel = config.UI_PANEL
        border = config.UI_ACCENT if self.open else config.UI_PANEL_BORDER
        pygame.draw.rect(surface, panel, self.rect, border_radius=4)
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=4)

        label = self.labels[self.selected] if self.selected < len(self.labels) else ""
        if label:
            surf = fonts["sm"].render(label, True, config.UI_TEXT)
            surface.blit(surf, (self.rect.x + 8, self.rect.y + (self.rect.height - surf.get_height()) // 2))

        # panah dropdown
        cx = self.rect.right - 14
        cy = self.rect.centery
        if self.open:
            pygame.draw.polygon(surface, config.UI_TEXT, [(cx - 5, cy - 2), (cx + 5, cy - 2), (cx, cy + 4)])
        else:
            pygame.draw.polygon(surface, config.UI_TEXT, [(cx - 5, cy + 2), (cx + 5, cy + 2), (cx, cy - 4)])

        if self.open:
            menu = self.menu_rect()
            for i, lbl in enumerate(self.labels):
                r = pygame.Rect(menu.x, menu.y + i * self.option_height, menu.w, self.option_height)
                if i == self.selected:
                    pygame.draw.rect(surface, config.UI_SELECTED, r)
                else:
                    pygame.draw.rect(surface, config.UI_PANEL, r)
                pygame.draw.rect(surface, config.UI_PANEL_BORDER, r, 1)
                ts = fonts["sm"].render(lbl, True, config.UI_TEXT)
                surface.blit(ts, (r.x + 6, r.y + (r.height - ts.get_height()) // 2))


class DebugOverlay:
    def __init__(self, events, fonts):
        self.events = events
        self.fonts = fonts

        self.expanded_nodes = []
        self.path_nodes = []
        self.last_time_ms = 0.0

        left = 10
        top = 10
        self.dropdown = Dropdown(
            (left, top, 250, 30),
            [label for _, label in config.ALGORITHMS],
            self._on_algorithm_selected,
        )
        self.stats_rect = pygame.Rect(left, top + 40, 250, 118)
        self.stats_surface = None

        events.register_overlay(self)
        self.update_stats(0, 0.0)

    def _on_algorithm_selected(self, index):
        algo_name = config.ALGORITHMS[index][0]
        self.events.emit_algorithm_changed(algo_name)
        self.update_stats(len(self.expanded_nodes), self.last_time_ms)

    # ------------------------------------------------------------------ #
    def update_debug_data(self, new_expanded, new_path, time_ms):
        self.expanded_nodes = [tuple(p) for p in new_expanded]
        self.path_nodes = [tuple(p) for p in new_path]
        self.last_time_ms = time_ms
        self.update_stats(len(self.expanded_nodes), time_ms)

    def update_stats(self, count, time_ms):
        self.last_time_ms = time_ms
        selected = config.ALGORITHMS[self.dropdown.selected][1]
        steps = max(0, len(self.path_nodes) - 1)
        text = (
            f"Algoritma: {selected}\n"
            f"Node Diekspansi: {count}\n"
            f"Panjang Langkah: {steps}\n"
            f"Waktu: {time_ms:.3f} ms\n"
            "(Tekan [Spasi] untuk Toggle Kejar NPC)"
        )
        lines = text.split("\n")
        line_h = self.fonts["sm"].get_linesize() + 3
        self.stats_rect.height = line_h * len(lines) + 12
        surface = pygame.Surface((self.stats_rect.width, self.stats_rect.height), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))
        y = 6
        for line in lines:
            ts = self.fonts["sm"].render(line, True, config.UI_TEXT)
            surface.blit(ts, (6, y))
            y += line_h
        self.stats_surface = surface

    # ------------------------------------------------------------------ #
    def draw_world(self, surface, camera, map_data, npc, player):
        """Gambar visualisasi di world-space (node ekspansi + jalur)."""
        tile_size = map_data.cell_size

        # 1. Node yang diekspansi: kotak biru transparan
        for node_pos in self.expanded_nodes:
            if not (0 <= node_pos[0] < map_data.width and 0 <= node_pos[1] < map_data.height):
                continue
            center = map_data.world_to_px(node_pos)
            half = tile_size / 2.0
            topleft = (center[0] - half, center[1] - half)
            rect = (*camera.world_to_screen(topleft[0], topleft[1]), tile_size * camera.zoom, tile_size * camera.zoom)
            pygame.draw.rect(surface, config.COLOR_EXPANDED_FILL, rect)
            pygame.draw.rect(surface, config.COLOR_EXPANDED_BORDER, rect, 1)

        # 2. Jalur terpendek: garis kuning + titik
        if self.path_nodes:
            points = []
            points.append((npc.px, npc.py))
            if len(self.path_nodes) > 2:
                for p in self.path_nodes[1:-1]:
                    points.append(map_data.world_to_px(p))
            points.append((player.px, player.py))

            if len(points) > 1:
                screen_points = [camera.world_to_screen(x, y) for x, y in points]
                for i in range(len(screen_points) - 1):
                    pygame.draw.line(surface, config.COLOR_PATH, screen_points[i], screen_points[i + 1], 2)
                    pygame.draw.circle(surface, config.COLOR_PATH_NODE, (int(screen_points[i][0]), int(screen_points[i][1])), 3)
                pygame.draw.circle(
                    surface,
                    config.COLOR_PATH_NODE,
                    (int(screen_points[-1][0]), int(screen_points[-1][1])),
                    3,
                )

    # ------------------------------------------------------------------ #
    def draw_ui(self, surface):
        self.dropdown.draw(surface, self.fonts)
        if self.stats_surface:
            surface.blit(self.stats_surface, (self.stats_rect.x, self.stats_rect.y))

    def handle_event(self, event):
        return self.dropdown.handle_event(event)