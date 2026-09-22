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
        return max(self.rect.height, 28)

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
        # --- Dark background dropdown ---
        bg_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        bg_surf.fill(config.DEBUG_DROPDOWN_BG)
        surface.blit(bg_surf, (self.rect.x, self.rect.y))

        border_color = config.DEBUG_PANEL_BORDER if self.open else (70, 80, 100, 180)
        pygame.draw.rect(surface, border_color, self.rect, 2, border_radius=4)

        label = self.labels[self.selected] if self.selected < len(self.labels) else ""
        if label:
            surf = fonts["sm"].render(label, True, config.DEBUG_TEXT_PRIMARY)
            surface.blit(surf, (self.rect.x + 10, self.rect.y + (self.rect.height - surf.get_height()) // 2))

        # Panah dropdown
        cx = self.rect.right - 16
        cy = self.rect.centery
        arrow_color = config.DEBUG_TEXT_HIGHLIGHT if self.open else config.DEBUG_TEXT_SECONDARY
        if self.open:
            pygame.draw.polygon(surface, arrow_color, [(cx - 5, cy - 2), (cx + 5, cy - 2), (cx, cy + 4)])
        else:
            pygame.draw.polygon(surface, arrow_color, [(cx - 5, cy + 2), (cx + 5, cy + 2), (cx, cy - 4)])

        # Menu pilihan saat dropdown terbuka
        if self.open:
            menu = self.menu_rect()
            for i, lbl in enumerate(self.labels):
                r = pygame.Rect(menu.x, menu.y + i * self.option_height, menu.w, self.option_height)
                item_surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
                if i == self.selected:
                    item_surf.fill(config.DEBUG_DROPDOWN_SELECTED)
                else:
                    item_surf.fill(config.DEBUG_DROPDOWN_BG)
                surface.blit(item_surf, (r.x, r.y))
                pygame.draw.rect(surface, (60, 90, 140, 160), r, 1)
                ts = fonts["sm"].render(lbl, True, config.DEBUG_TEXT_PRIMARY)
                surface.blit(ts, (r.x + 10, r.y + (r.height - ts.get_height()) // 2))


class DebugOverlay:
    def __init__(self, events, fonts):
        self.events = events
        self.fonts = fonts

        self.expanded_nodes = []
        self.path_nodes = []
        self.last_time_ms = 0.0

        # Data perbandingan UCS vs algoritma terpilih
        self.comparison_data = None

        # Sidebar kiri berdimensi rapi
        self.panel_x = 12
        self.panel_y = 12
        self.panel_w = 326

        # Dropdown diletakkan di dalam sidebar dengan posisi yang pas
        dropdown_y = self.panel_y + 60
        self.dropdown = Dropdown(
            (self.panel_x + 12, dropdown_y, self.panel_w - 24, 34),
            [label for _, label in config.ALGORITHMS],
            self._on_algorithm_selected,
        )

        # Posisi area konten statistik tepat di bawah dropdown tertutup
        # Ketika dropdown tertutup, tinggi dropdown adalah 34. Berikan margin agar pas
        stats_top = dropdown_y + 44
        self.stats_rect = pygame.Rect(self.panel_x, stats_top, self.panel_w, 200)
        self.stats_surface = None
        self.total_panel_h = 700

        events.register_overlay(self)
        self.update_stats(0, 0.0)

    def _on_algorithm_selected(self, index):
        algo_name = config.ALGORITHMS[index][0]
        self.events.emit_algorithm_changed(algo_name)
        self.update_stats(len(self.expanded_nodes), self.last_time_ms)

    # ------------------------------------------------------------------ #
    def set_comparison_data(self, data):
        """Menerima data perbandingan dari NPC untuk ditampilkan di panel."""
        self.comparison_data = data

    def update_debug_data(self, new_expanded, new_path, time_ms):
        self.expanded_nodes = [tuple(p) for p in new_expanded]
        self.path_nodes = [tuple(p) for p in new_path]
        self.last_time_ms = time_ms
        self.update_stats(len(self.expanded_nodes), time_ms)

    def update_stats(self, count, time_ms):
        self.last_time_ms = time_ms
        selected_label = config.ALGORITHMS[self.dropdown.selected][1]
        steps = max(0, len(self.path_nodes) - 1)
        cur_cost = self.comparison_data.get("cur_cost", 0.0) if self.comparison_data else 0.0

        # --- Bangun baris-baris teks dengan warna ---
        lines = []  # list of (text, color)

        # Bobot Terrain
        lines.append(("── BOBOT MEDAN (COST) ────────────────", config.DEBUG_TEXT_SECONDARY))
        lines.append(("  • Jalan Tanah  : Cost 1.0 (Normal)", config.DEBUG_TEXT_PRIMARY))
        lines.append(("  • Area Rumput  : Cost 2.0 (Berat)", config.DEBUG_TEXT_WARN))
        lines.append(("", None))  # spacer

        # Statistik utama
        lines.append(("── STATISTIK JALUR ────────────────────", config.DEBUG_TEXT_SECONDARY))
        lines.append((f"  Node Diekspansi : {count}", config.DEBUG_TEXT_PRIMARY))
        lines.append((f"  Panjang Jalur   : {steps} langkah", config.DEBUG_TEXT_PRIMARY))
        lines.append((f"  Total Cost Rute : {cur_cost:.1f}", config.DEBUG_TEXT_PRIMARY))
        lines.append((f"  Waktu Eksekusi  : {time_ms:.3f} ms", config.DEBUG_TEXT_PRIMARY))
        lines.append(("", None))  # spacer

        # Perbandingan UCS vs A*
        if self.comparison_data:
            cd = self.comparison_data
            lines.append(("── PERBANDINGAN RUTE ──────────────────", config.DEBUG_TEXT_SECONDARY))

            ucs_expanded = cd.get("ucs_expanded", 0)
            ucs_time = cd.get("ucs_time_ms", 0.0)
            ucs_steps = cd.get("ucs_path_len", 0)
            ucs_cost = cd.get("ucs_cost", 0.0)

            cur_expanded = cd.get("cur_expanded", count)
            cur_time = cd.get("cur_time_ms", time_ms)
            cur_steps = cd.get("cur_path_len", steps)
            cur_label = cd.get("cur_label", selected_label)
            cur_heuristic = cd.get("cur_heuristic", "—")

            lines.append(("  UCS (h=0):", config.DEBUG_TEXT_WARN))
            lines.append((f"    Node: {ucs_expanded} │ Cost: {ucs_cost:.1f} │ {ucs_time:.3f} ms", config.DEBUG_TEXT_PRIMARY))

            lines.append((f"  {cur_label}:", config.DEBUG_TEXT_HIGHLIGHT))
            lines.append((f"    Node: {cur_expanded} │ Cost: {cur_cost:.1f} │ {cur_time:.3f} ms", config.DEBUG_TEXT_PRIMARY))

            if cur_heuristic != "—":
                lines.append((f"    Heuristik: {cur_heuristic}", config.DEBUG_TEXT_SECONDARY))

            # Efisiensi
            if ucs_expanded > 0 and cur_expanded > 0:
                ratio = ucs_expanded / cur_expanded
                if ratio > 1.0:
                    eff_text = f"  ⚡ A* {ratio:.1f}x lebih hemat ekspansi"
                    lines.append((eff_text, (100, 255, 120)))
                elif ratio < 1.0:
                    eff_text = f"  ⚠ UCS {1/ratio:.1f}x lebih hemat"
                    lines.append((eff_text, config.DEBUG_TEXT_WARN))
                else:
                    eff_text = f"  ≈ Efisiensi node sama"
                    lines.append((eff_text, config.DEBUG_TEXT_SECONDARY))

        lines.append(("", None))  # spacer
        lines.append(("── KONTROL ────────────────────────────", config.DEBUG_TEXT_SECONDARY))
        lines.append(("  [WASD / Panah]  : Gerakkan Player", config.DEBUG_TEXT_PRIMARY))
        lines.append(("  [Spasi]         : Toggle Kejar NPC", config.DEBUG_TEXT_HIGHLIGHT))
        lines.append(("  [Esc]           : Keluar Game", config.DEBUG_TEXT_SECONDARY))

        # --- Render ke surface teks ---
        line_h = self.fonts["sm"].get_linesize() + 3
        pad_x, pad_y = 12, 6
        total_h = pad_y * 2

        for text, color in lines:
            if text == "":
                total_h += line_h // 2
            else:
                total_h += line_h

        inner_w = self.panel_w - 24
        surface = pygame.Surface((inner_w, total_h), pygame.SRCALPHA)

        y = pad_y
        for text, color in lines:
            if text == "":
                y += line_h // 2
                continue
            ts = self.fonts["sm"].render(text, True, color)
            surface.blit(ts, (pad_x, y))
            y += line_h

        self.stats_surface = surface
        self.stats_rect.height = total_h

    # ------------------------------------------------------------------ #
    def draw_world(self, surface, camera, map_data, npc, player):
        """Gambar visualisasi di world-space (node ekspansi + jalur)."""
        tile_size = map_data.cell_size

        # 1. Node yang diekspansi: kotak biru sangat transparan
        exp_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for node_pos in self.expanded_nodes:
            if not (0 <= node_pos[0] < map_data.width and 0 <= node_pos[1] < map_data.height):
                continue
            center = map_data.world_to_px(node_pos)
            half = tile_size / 2.0
            topleft = (center[0] - half, center[1] - half)
            screen_pos = camera.world_to_screen(topleft[0], topleft[1])
            sz = tile_size * camera.zoom
            rect = (screen_pos[0], screen_pos[1], sz, sz)
            pygame.draw.rect(exp_surf, config.COLOR_EXPANDED_FILL, rect)
            pygame.draw.rect(exp_surf, config.COLOR_EXPANDED_BORDER, rect, 1)
        surface.blit(exp_surf, (0, 0))

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
        screen_h = surface.get_height()

        # 1. Gambar latar belakang Sidebar Kiri (dari atas ke bawah dengan margin rapi)
        sidebar_y = self.panel_y
        sidebar_h = screen_h - self.panel_y * 2
        sidebar_rect = pygame.Rect(self.panel_x, sidebar_y, self.panel_w, sidebar_h)

        sidebar_surf = pygame.Surface((self.panel_w, sidebar_h), pygame.SRCALPHA)
        sidebar_surf.fill(config.DEBUG_PANEL_BG)
        pygame.draw.rect(sidebar_surf, config.DEBUG_PANEL_BORDER, (0, 0, self.panel_w, sidebar_h), 1, border_radius=8)
        surface.blit(sidebar_surf, (self.panel_x, sidebar_y))

        # 2. Header Sidebar
        title_surf = self.fonts.get("title", self.fonts["sm"]).render("AI PATHFINDING", True, config.DEBUG_TEXT_HIGHLIGHT)
        surface.blit(title_surf, (self.panel_x + 14, self.panel_y + 12))

        sub_surf = self.fonts["sm"].render("Pilih Algoritma AI:", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(sub_surf, (self.panel_x + 14, self.panel_y + 38))

        # 3. Konten statistik & perbandingan (teks di bawah dropdown)
        if self.stats_surface:
            surface.blit(self.stats_surface, (self.stats_rect.x + 12, self.stats_rect.y))

        # 4. Gambar dropdown TERAKHIR agar daftar item melayang di atas konten saat terbuka
        self.dropdown.draw(surface, self.fonts)

    def handle_event(self, event):
        return self.dropdown.handle_event(event)