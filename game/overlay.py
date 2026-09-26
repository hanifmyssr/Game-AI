"""DebugOverlay: Mendukung 2 mode UI:
1. Mode Eksplorasi (Pathfinding: A* vs UCS, visualisasi node, bobot terrain)
2. Mode Battle (Turn-Based Duel: Minimax vs Alpha-Beta vs Expectimax, evaluation functions, depth limit, node counts, skor aksi)
"""

import math
import pygame

from . import config
from .battle_ai import ACTION_ATTACK, ACTION_HEAVY, ACTION_DEFEND, ACTION_POTION

MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1025)
SRCALPHA = getattr(pygame, "SRCALPHA", 0x00010000)


def draw_card(surface, rect, bg_color, border_color=None, border_radius=8, border_width=1):
    """Fungsi pembantu untuk menggambar kartu/kontainer dengan pinggiran mulus."""
    card_surf = pygame.Surface((rect.width, rect.height), SRCALPHA)
    pygame.draw.rect(card_surf, bg_color, card_surf.get_rect(), border_radius=border_radius)
    surface.blit(card_surf, (rect.x, rect.y))
    if border_color:
        pygame.draw.rect(surface, border_color, rect, border_width, border_radius=border_radius)


class Dropdown:
    def __init__(self, rect, labels, on_select, initial_idx=0, placeholder="-- Pilih Algoritma --"):
        self.rect = pygame.Rect(rect)
        self.labels = labels
        self.on_select = on_select
        self.selected = initial_idx
        self.placeholder = placeholder
        self.open = False

    @property
    def option_height(self):
        return max(self.rect.height, 28)

    def menu_rect(self):
        w = self.rect.width
        h = self.option_height * len(self.labels)
        return pygame.Rect(self.rect.x, self.rect.bottom + 4, w, h)

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
        # Button background & border
        bg_color = (242, 246, 252, 245) if self.open else (238, 242, 248, 235)
        draw_card(surface, self.rect, bg_color, border_color=config.DEBUG_TEXT_HIGHLIGHT if self.open else (140, 155, 180, 200), border_radius=6)

        if self.selected is not None and 0 <= self.selected < len(self.labels):
            label = self.labels[self.selected]
            text_color = config.DEBUG_TEXT_PRIMARY
        else:
            label = self.placeholder
            text_color = config.DEBUG_TEXT_SECONDARY

        if label:
            surf = fonts["sm"].render(label, True, text_color)
            surface.blit(surf, (self.rect.x + 10, self.rect.y + (self.rect.height - surf.get_height()) // 2))

        # Panah indikator dropdown
        cx = self.rect.right - 14
        cy = self.rect.centery
        arrow_color = config.DEBUG_TEXT_HIGHLIGHT if self.open else config.DEBUG_TEXT_SECONDARY
        if self.open:
            pygame.draw.polygon(surface, arrow_color, [(cx - 4, cy + 1), (cx + 4, cy + 1), (cx, cy - 4)])
        else:
            pygame.draw.polygon(surface, arrow_color, [(cx - 4, cy - 2), (cx + 4, cy - 2), (cx, cy + 3)])

        # Menu pilihan saat terbuka
        if self.open:
            menu = self.menu_rect()
            draw_card(surface, menu, (248, 251, 255, 252), border_color=config.DEBUG_TEXT_HIGHLIGHT, border_radius=8, border_width=1)

            for i, lbl in enumerate(self.labels):
                r = pygame.Rect(menu.x + 4, menu.y + i * self.option_height + 2, menu.w - 8, self.option_height - 4)
                if self.selected is not None and i == self.selected:
                    draw_card(surface, r, (210, 228, 250, 240), border_color=(120, 170, 230, 200), border_radius=5)
                    ts = fonts["sm"].render(lbl, True, config.DEBUG_TEXT_HIGHLIGHT)
                else:
                    ts = fonts["sm"].render(lbl, True, config.DEBUG_TEXT_PRIMARY)
                surface.blit(ts, (r.x + 8, r.y + (r.height - ts.get_height()) // 2))


class DebugOverlay:
    def __init__(self, events, fonts):
        self.events = events
        self.fonts = fonts

        self.mode = "EXPLORATION"  # "EXPLORATION" atau "BATTLE"

        # State Pathfinding (Exploration)
        self.expanded_nodes = []
        self.path_nodes = []
        self.animation_time = 0.0
        self.expanded_reveal = 1.0
        self.path_reveal = 1.0
        self.visualization_active = False
        self.chasing_visualization = False
        self.show_costs = False
        self.depth_help_open = False
        self.move_ordering_help_open = False
        self.last_time_ms = 0.0
        self.comparison_data = None

        # Posisi Sidebar Kiri
        self.panel_x = 12
        self.panel_y = 12
        self.panel_w = config.DEBUG_PANEL_WIDTH
        self.cost_toggle_rect = pygame.Rect(self.panel_x + self.panel_w + 10, self.panel_y + 12, 104, 30)

        # --- Dropdown Mode Eksplorasi ---
        dropdown_y = self.panel_y + 60
        self.dropdown_algo = Dropdown(
            (self.panel_x + 12, dropdown_y, self.panel_w - 24, 32),
            [label for _, label in config.ALGORITHMS],
            self._on_algorithm_selected,
            initial_idx=None,
            placeholder="-- Pilih Algoritma --",
        )

        stats_top = dropdown_y + 42
        self.stats_rect = pygame.Rect(self.panel_x, stats_top, self.panel_w, 200)
        self.stats_surface = None

        # --- UI Duel Mode ---
        self.battle_system = None
        self._init_battle_ui()

        events.register_overlay(self)
        self.update_stats(0, 0.0)

    def _init_battle_ui(self):
        px = self.panel_x + 12
        pw = self.panel_w - 24

        # Dropdown AI Battle: Algoritma
        self.dropdown_battle_algo = Dropdown(
            (px + 6, self.panel_y + 70, pw - 12, 28),
            ["Alpha-Beta Pruning", "Pure Minimax", "Expectimax (Stokastik)"],
            self._on_battle_algo_selected,
            initial_idx=0,
        )

        # Dropdown AI Battle: Fungsi Evaluasi
        self.dropdown_battle_eval = Dropdown(
            (px + 6, self.panel_y + 124, pw - 12, 28),
            ["Balanced (Standar)", "Aggressive (Offensif)", "Defensive (Taktis)"],
            self._on_battle_eval_selected,
            initial_idx=0,
        )

        # Tombol Kedalaman AI (Depth - dan +)
        self.btn_depth_minus = pygame.Rect(px + pw - 78, self.panel_y + 162, 30, 24)
        self.btn_depth_plus = pygame.Rect(px + pw - 42, self.panel_y + 162, 30, 24)
        self.btn_depth_help = pygame.Rect(px + 180, self.panel_y + 162, 24, 24)

        # Tombol Move Ordering Toggle
        self.btn_move_ordering = pygame.Rect(px + pw - 62, self.panel_y + 192, 54, 24)
        self.btn_move_ordering_help = pygame.Rect(px + 134, self.panel_y + 192, 24, 24)

        # Tombol Aksi Player (4 Aksi: Attack, Heavy Attack, Defend, Potion)
        bw = (pw - 18) // 2
        btn_y = self.panel_y + 264
        self.btn_attack = pygame.Rect(px + 6, btn_y, bw, 32)
        self.btn_heavy = pygame.Rect(px + 12 + bw, btn_y, bw, 32)
        self.btn_defend = pygame.Rect(px + 6, btn_y + 38, bw, 32)
        self.btn_potion = pygame.Rect(px + 12 + bw, btn_y + 38, bw, 32)

    def set_battle_system(self, battle_system):
        self.battle_system = battle_system

    def set_mode(self, mode: str):
        self.mode = mode

    # ------------------------------------------------------------------ #
    # Event Handlers Dropdown
    # ------------------------------------------------------------------ #
    def _on_algorithm_selected(self, index):
        if index is None or index < 0 or index >= len(config.ALGORITHMS):
            return
        algo_name = config.ALGORITHMS[index][0]
        self.events.emit_algorithm_changed(algo_name)
        self.update_stats(len(self.expanded_nodes), self.last_time_ms)

    def _on_battle_algo_selected(self, index):
        if not self.battle_system:
            return
        algos = ["ALPHA_BETA", "MINIMAX", "EXPECTIMAX"]
        self.battle_system.algorithm = algos[index]

    def _on_battle_eval_selected(self, index):
        if not self.battle_system:
            return
        evals = ["BALANCED", "AGGRESSIVE", "DEFENSIVE"]
        self.battle_system.eval_mode = evals[index]

    # ------------------------------------------------------------------ #
    # Data Update Eksplorasi
    # ------------------------------------------------------------------ #
    def set_comparison_data(self, data):
        self.comparison_data = data

    def update_debug_data(self, new_expanded, new_path, time_ms, start_pos=None):
        expanded_nodes = [tuple(p) for p in new_expanded]
        if start_pos is None and expanded_nodes:
            start_pos = expanded_nodes[0]
        if start_pos is not None:
            start_pos = tuple(start_pos)
            expanded_nodes = [
                node
                for _, node in sorted(
                    enumerate(expanded_nodes),
                    key=lambda item: (
                        abs(item[1][0] - start_pos[0]) + abs(item[1][1] - start_pos[1]),
                        item[0],
                    ),
                )
            ]
        self.expanded_nodes = expanded_nodes
        self.path_nodes = [tuple(p) for p in new_path]
        if self.visualization_active and not self.chasing_visualization:
            self.expanded_reveal = 0.0
            self.path_reveal = 0.0
        else:
            self.expanded_reveal = 1.0
            self.path_reveal = 1.0
        self.last_time_ms = time_ms
        self.update_stats(len(self.expanded_nodes), time_ms)

    def start_path_animation(self):
        self.visualization_active = True
        self.animation_time = 0.0
        self.expanded_reveal = 0.0
        self.path_reveal = 0.0

    def stop_path_animation(self):
        self.visualization_active = False

    def on_camera_zoom(self):
        if not self.chasing_visualization:
            self.stop_path_animation()

    def set_chasing_visualization(self, chasing):
        self.chasing_visualization = chasing
        if chasing:
            self.visualization_active = True
            self.expanded_reveal = 1.0
            self.path_reveal = 1.0

    def update_animation(self, dt):
        if not self.visualization_active:
            return
        self.animation_time += dt
        self.expanded_reveal = min(1.0, self.expanded_reveal + dt * 1.4)
        self.path_reveal = min(1.0, self.path_reveal + dt * 2.2)

    def update_stats(self, count, time_ms):
        self.last_time_ms = time_ms
        if self.dropdown_algo.selected is not None and 0 <= self.dropdown_algo.selected < len(config.ALGORITHMS):
            selected_label = config.ALGORITHMS[self.dropdown_algo.selected][1]
        else:
            selected_label = "-- Pilih Algoritma --"
        steps = max(0, len(self.path_nodes) - 1)
        cur_cost = self.comparison_data.get("cur_cost", 0.0) if self.comparison_data else 0.0

        lines = []
        lines.append(("── BOBOT MEDAN (COST) ────────────────", config.DEBUG_TEXT_SECONDARY))
        lines.append(("  • Jalan Tanah  : Cost 1.0 (Ringan)", config.DEBUG_TEXT_PRIMARY))
        lines.append(("  • Area Rumput  : Cost 2.0 (Normal)", config.DEBUG_TEXT_WARN))
        lines.append(("", None))

        lines.append(("── STATISTIK JALUR ────────────────────", config.DEBUG_TEXT_SECONDARY))
        lines.append((f"  Node Diekspansi : {count}", config.DEBUG_TEXT_PRIMARY))
        lines.append((f"  Panjang Jalur   : {steps} langkah", config.DEBUG_TEXT_PRIMARY))
        lines.append((f"  Total Cost Rute : {cur_cost:.1f}", config.DEBUG_TEXT_PRIMARY))
        lines.append((f"  Waktu Eksekusi  : {time_ms:.3f} ms", config.DEBUG_TEXT_PRIMARY))
        lines.append(("", None))

        if self.comparison_data:
            cd = self.comparison_data
            lines.append(("── PERBANDINGAN RUTE ──────────────────", config.DEBUG_TEXT_SECONDARY))
            ucs_expanded = cd.get("ucs_expanded", 0)
            ucs_time = cd.get("ucs_time_ms", 0.0)
            ucs_cost = cd.get("ucs_cost", 0.0)

            cur_expanded = cd.get("cur_expanded", count)
            cur_time = cd.get("cur_time_ms", time_ms)
            cur_label = cd.get("cur_label", selected_label)
            cur_heuristic = cd.get("cur_heuristic", "—")

            lines.append(("  UCS (h=0):", config.DEBUG_TEXT_WARN))
            lines.append((f"    Node: {ucs_expanded} │ Cost: {ucs_cost:.1f} │ {ucs_time:.3f} ms", config.DEBUG_TEXT_PRIMARY))

            lines.append((f"  {cur_label}:", config.DEBUG_TEXT_HIGHLIGHT))
            lines.append((f"    Node: {cur_expanded} │ Cost: {cur_cost:.1f} │ {cur_time:.3f} ms", config.DEBUG_TEXT_PRIMARY))

            if cur_heuristic != "—":
                lines.append((f"    Heuristik: {cur_heuristic}", config.DEBUG_TEXT_SECONDARY))

            if ucs_expanded > 0 and cur_expanded > 0:
                ratio = ucs_expanded / cur_expanded
                if ratio > 1.0:
                    eff_text = f"  ⚡ A* {ratio:.1f}x lebih hemat ekspansi"
                    lines.append((eff_text, config.DEBUG_TEXT_HIGHLIGHT))
                elif ratio < 1.0:
                    eff_text = f"  ⚠ UCS {1/ratio:.1f}x lebih hemat"
                    lines.append((eff_text, config.DEBUG_TEXT_HIGHLIGHT))
                else:
                    lines.append(("  ≈ Efisiensi node sama", config.DEBUG_TEXT_SECONDARY))

        lines.append(("", None))
        lines.append(("── KONTROL ────────────────────────────", config.DEBUG_TEXT_SECONDARY))
        lines.append(("  [WASD / Panah]  : Gerakkan Player", config.DEBUG_TEXT_PRIMARY))
        lines.append(("  [Ctrl]          : Tampilkan animasi path", config.DEBUG_TEXT_HIGHLIGHT))
        lines.append(("  [Spasi]         : Toggle Kejar NPC", config.DEBUG_TEXT_HIGHLIGHT))
        lines.append(("  [Esc]           : Keluar Game", config.DEBUG_TEXT_SECONDARY))

        line_h = self.fonts["sm"].get_linesize() + 3
        pad_x, pad_y = 12, 6
        max_text_w = self.panel_w - 24 - (pad_x * 2)
        wrapped_lines = []
        for text, color in lines:
            if not text:
                wrapped_lines.append((text, color))
                continue
            words = text.split(" ")
            current = ""
            for word in words:
                candidate = word if not current else f"{current} {word}"
                if self.fonts["sm"].size(candidate)[0] <= max_text_w:
                    current = candidate
                else:
                    if current:
                        wrapped_lines.append((current, color))
                    current = word
            if current:
                wrapped_lines.append((current, color))

        total_h = pad_y * 2

        for text, color in wrapped_lines:
            if text == "":
                total_h += line_h // 2
            else:
                total_h += line_h

        inner_w = self.panel_w - 24
        surface = pygame.Surface((inner_w, total_h), SRCALPHA)

        y = pad_y
        for text, color in wrapped_lines:
            if text == "":
                y += line_h // 2
                continue
            ts = self.fonts["sm"].render(text, True, color)
            surface.blit(ts, (pad_x, y))
            y += line_h

        self.stats_surface = surface
        self.stats_rect.height = total_h

    # ------------------------------------------------------------------ #
    # Drawing World (Hanya aktif saat Mode Eksplorasi)
    # ------------------------------------------------------------------ #
    def draw_world(self, surface, camera, map_data, _npc, _player):
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
    # Drawing UI (Router: Mode Eksplorasi atau Duel)
    # ------------------------------------------------------------------ #
    def draw_ui(self, surface):
        screen_h = surface.get_height()
        sidebar_y = self.panel_y
        sidebar_h = screen_h - self.panel_y * 2

        # 1. Background Sidebar Utama (Pinggiran Mulus dengan Smooth Rounded Corners & Outer Glow Border)
        draw_card(
            surface,
            pygame.Rect(self.panel_x, sidebar_y, self.panel_w, sidebar_h),
            config.DEBUG_PANEL_BG,
            border_color=config.DEBUG_PANEL_BORDER,
            border_radius=12,
            border_width=2,
        )

        if self.mode == "EXPLORATION":
            self._draw_exploration_ui(surface)
            self._draw_cost_toggle(surface)
        else:
            self._draw_battle_ui(surface)

    def _draw_cost_toggle(self, surface):
        fill = (70, 175, 95, 230) if self.show_costs else (225, 230, 238, 230)
        draw_card(surface, self.cost_toggle_rect, fill, border_color=(100, 120, 150, 200), border_radius=6)
        label = "Cost: ON" if self.show_costs else "Cost: OFF"
        text_color = (255, 255, 255) if self.show_costs else config.DEBUG_TEXT_PRIMARY
        text = self.fonts["sm"].render(label, True, text_color)
        surface.blit(text, (self.cost_toggle_rect.centerx - text.get_width() // 2, self.cost_toggle_rect.centery - text.get_height() // 2))

    def _draw_exploration_ui(self, surface):
        px = self.panel_x + 12
        pw = self.panel_w - 24

        # Header Card
        header_rect = pygame.Rect(px, self.panel_y + 8, pw, 38)
        draw_card(surface, header_rect, (235, 242, 252, 230), border_color=(180, 200, 230, 180), border_radius=8)
        title_surf = self.fonts.get("title", self.fonts["sm"]).render("📍 AI PATHFINDING", True, config.DEBUG_TEXT_HIGHLIGHT)
        surface.blit(title_surf, (header_rect.x + 10, header_rect.y + (header_rect.height - title_surf.get_height()) // 2))

        sub_surf = self.fonts["sm"].render("Pilih Algoritma AI:", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(sub_surf, (px + 4, self.panel_y + 48))

        if self.stats_surface:
            stats_card = pygame.Rect(px, self.stats_rect.y, pw, self.stats_rect.height)
            draw_card(surface, stats_card, (244, 247, 252, 220), border_color=(205, 215, 230, 180), border_radius=8)
            surface.blit(self.stats_surface, (px, self.stats_rect.y))

        self.dropdown_algo.draw(surface, self.fonts)

    def _draw_battle_ui(self, surface):
        battle_system = self.battle_system
        if battle_system is None:
            return

        px = self.panel_x + 12
        pw = self.panel_w - 24

        # ---------------------------------------------------------------- #
        # Kartu 1: Header Duel
        # ---------------------------------------------------------------- #
        header_rect = pygame.Rect(px, self.panel_y + 8, pw, 38)
        draw_card(surface, header_rect, (255, 242, 235, 240), border_color=(255, 175, 140, 200), border_radius=8)
        title_surf = self.fonts.get("title", self.fonts["sm"]).render("⚔ DUEL MINIMAX AI", True, (215, 65, 30))
        surface.blit(title_surf, (header_rect.x + 10, header_rect.y + (header_rect.height - title_surf.get_height()) // 2))

        # ---------------------------------------------------------------- #
        # Kartu 2: Konfigurasi AI & Parameter Search
        # ---------------------------------------------------------------- #
        cfg_rect = pygame.Rect(px, self.panel_y + 50, pw, 172)
        draw_card(surface, cfg_rect, (244, 247, 253, 235), border_color=(200, 212, 230, 200), border_radius=8)

        # Labels & Dropdowns
        sub_algo = self.fonts["sm"].render("Algoritma AI NPC:", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(sub_algo, (px + 8, self.panel_y + 54))

        sub_eval = self.fonts["sm"].render("Fungsi Evaluasi:", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(sub_eval, (px + 8, self.panel_y + 108))

        # Baris Depth Control
        depth_y = self.panel_y + 162
        depth_label = self.fonts["sm"].render(f"Kedalaman (Depth): {battle_system.depth}", True, config.DEBUG_TEXT_PRIMARY)
        surface.blit(depth_label, (px + 8, depth_y + 3))

        for btn, text, fill in [
            (self.btn_depth_minus, "-", (210, 75, 75)),
            (self.btn_depth_plus, "+", (50, 160, 85)),
        ]:
            draw_card(surface, btn, fill, border_color=(100, 110, 125, 200), border_radius=5)
            ts = self.fonts.get("bubble", self.fonts["sm"]).render(text, True, (255, 255, 255))
            surface.blit(ts, (btn.centerx - ts.get_width() // 2, btn.centery - ts.get_height() // 2))

        draw_card(surface, self.btn_depth_help, (60, 100, 160), border_color=(100, 110, 125, 200), border_radius=5)
        help_text = self.fonts.get("bubble", self.fonts["sm"]).render("?", True, (255, 255, 255))
        surface.blit(help_text, (self.btn_depth_help.centerx - help_text.get_width() // 2, self.btn_depth_help.centery - help_text.get_height() // 2))

        # Baris Move Ordering Toggle
        mo_y = self.panel_y + 192
        mo_on = battle_system.use_move_ordering
        mo_label = self.fonts["sm"].render("Move Ordering:", True, config.DEBUG_TEXT_PRIMARY)
        surface.blit(mo_label, (px + 8, mo_y + 3))

        draw_card(surface, self.btn_move_ordering_help, (60, 100, 160), border_color=(100, 110, 125, 200), border_radius=5)
        help_text = self.fonts.get("bubble", self.fonts["sm"]).render("?", True, (255, 255, 255))
        surface.blit(help_text, (self.btn_move_ordering_help.centerx - help_text.get_width() // 2, self.btn_move_ordering_help.centery - help_text.get_height() // 2))

        mo_fill = (45, 160, 85) if mo_on else (190, 60, 60)
        draw_card(surface, self.btn_move_ordering, mo_fill, border_color=(100, 110, 125, 200), border_radius=10)
        mo_text = "ON" if mo_on else "OFF"
        ts_mo = self.fonts["sm"].render(mo_text, True, (255, 255, 255))
        surface.blit(ts_mo, (self.btn_move_ordering.centerx - ts_mo.get_width() // 2, self.btn_move_ordering.centery - ts_mo.get_height() // 2))

        # ---------------------------------------------------------------- #
        # Kartu 3: Status Giliran & Tombol Aksi Pemain
        # ---------------------------------------------------------------- #
        state = battle_system.state
        act_card_y = self.panel_y + 226
        act_card_h = 114
        draw_card(surface, pygame.Rect(px, act_card_y, pw, act_card_h), (244, 247, 253, 235), border_color=(200, 212, 230, 200), border_radius=8)

        if state:
            turn_rect = pygame.Rect(px + 6, act_card_y + 6, pw - 12, 24)
            if battle_system.is_finished:
                turn_text = f"Pertarungan Selesai: {battle_system.winner} MENANG!"
                turn_bg = (215, 245, 225, 240)
                turn_color = (15, 110, 45)
            elif state.is_npc_turn:
                turn_text = "Giliran NPC (AI Berpikir...)"
                turn_bg = (255, 238, 210, 240)
                turn_color = (195, 90, 10)
            else:
                turn_text = "Giliran Anda (Pilih Aksi)"
                turn_bg = (220, 238, 255, 240)
                turn_color = (15, 95, 185)

            draw_card(surface, turn_rect, turn_bg, border_color=None, border_radius=5)
            ts_turn = self.fonts.get("bubble", self.fonts["sm"]).render(turn_text, True, turn_color)
            surface.blit(ts_turn, (turn_rect.centerx - ts_turn.get_width() // 2, turn_rect.centery - ts_turn.get_height() // 2))

            # Tombol-tombol Aksi Pemain (Attack, Heavy, Defend, Potion)
            can_act = (not state.is_npc_turn) and (not battle_system.is_finished)
            heavy_ready = state.player_heavy_cd <= 0
            heavy_label = "Heavy (30)" if heavy_ready else f"Heavy (CD:{state.player_heavy_cd})"
            actions_info = [
                (self.btn_attack, "Attack (18)", (205, 55, 55), True),
                (self.btn_heavy, heavy_label, (225, 105, 30), heavy_ready),
                (self.btn_defend, "Defend (-65%)", (45, 115, 205), True),
                (self.btn_potion, f"Potion ({state.player_potions})", (40, 160, 85), state.player_potions > 0 and state.player_hp < config.MAX_HP if hasattr(config, 'MAX_HP') else True),
            ]

            for btn_rect, btn_title, base_col, is_enabled in actions_info:
                if can_act and is_enabled:
                    fill_col = base_col
                    text_col = (255, 255, 255)
                    border_col = (110, 120, 135, 180)
                else:
                    fill_col = (210, 215, 222, 220)
                    text_col = (130, 135, 145)
                    border_col = (180, 185, 195, 160)

                draw_card(surface, btn_rect, fill_col, border_color=border_col, border_radius=6)
                ts = self.fonts["sm"].render(btn_title, True, text_col)
                surface.blit(ts, (btn_rect.centerx - ts.get_width() // 2, btn_rect.centery - ts.get_height() // 2))

        # ---------------------------------------------------------------- #
        # Kartu 4: Evaluasi AI, Node Counts & Pertimbangan Aksi
        # ---------------------------------------------------------------- #
        eval_card_y = self.panel_y + 346
        eval_card_h = 280
        draw_card(surface, pygame.Rect(px, eval_card_y, pw, eval_card_h), (244, 247, 253, 235), border_color=(200, 212, 230, 200), border_radius=8)

        # Header Sub-panel Evaluasi AI
        ts_mtitle = self.fonts["sm"].render("── EVALUASI AKSI & NODE COUNT ──", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(ts_mtitle, (px + (pw - ts_mtitle.get_width()) // 2, eval_card_y + 8))

        stats = battle_system.last_ai_stats
        cur_y = eval_card_y + 30

        if stats:
            nc = stats.get("node_count", 0)
            pc = stats.get("pruned_count", 0)
            t_ms = stats.get("time_ms", 0.0)
            best_a = stats.get("best_action", "—")
            best_s = stats.get("best_score", 0.0)

            # Node Count, Pruning, Timing
            surface.blit(self.fonts["sm"].render(f"Nodes Diekspansi : {nc}", True, config.DEBUG_TEXT_PRIMARY), (px + 10, cur_y))
            cur_y += 18
            pruned_font = self.fonts.get("bubble", self.fonts["sm"])
            surface.blit(pruned_font.render(f"Cabang Dipangkas : {pc}", True, (15, 120, 50)), (px + 10, cur_y))
            cur_y += 18
            surface.blit(self.fonts["sm"].render(f"Waktu Berpikir   : {t_ms:.2f} ms", True, config.DEBUG_TEXT_PRIMARY), (px + 10, cur_y))
            cur_y += 18

            # Best Action Card Highlight
            best_card = pygame.Rect(px + 8, cur_y, pw - 16, 26)
            draw_card(surface, best_card, (215, 235, 255, 230), border_color=(100, 160, 230, 200), border_radius=5)
            best_text = f"Pilihan Terbaik  : {best_a} (Skor: {best_s})"
            ts_best = self.fonts["sm"].render(best_text, True, config.DEBUG_TEXT_HIGHLIGHT)
            surface.blit(ts_best, (best_card.x + 8, best_card.centery - ts_best.get_height() // 2))
            cur_y += 32

            # Tabel Skor Pertimbangan Tiap Aksi di Root
            surface.blit(self.fonts["sm"].render("Pertimbangan Nilai Aksi (Root):", True, config.DEBUG_TEXT_SECONDARY), (px + 10, cur_y))
            cur_y += 18

            scores = stats.get("action_scores", {})
            for act, val in scores.items():
                is_selected = (act == best_a)
                row_rect = pygame.Rect(px + 8, cur_y, pw - 16, 20)

                if is_selected:
                    draw_card(surface, row_rect, (205, 232, 255, 220), border_color=(120, 175, 240, 180), border_radius=4)
                    prefix = "▶ "
                    col = config.DEBUG_TEXT_HIGHLIGHT
                else:
                    draw_card(surface, row_rect, (236, 240, 248, 160), border_radius=4)
                    prefix = "  • "
                    col = config.DEBUG_TEXT_PRIMARY

                surface.blit(self.fonts["sm"].render(f"{prefix}{act:<12}: {val:>7.1f}", True, col), (row_rect.x + 4, row_rect.centery - 7))
                cur_y += 22
        else:
            surface.blit(self.fonts["sm"].render("Menunggu kalkulasi pertama AI...", True, config.DEBUG_TEXT_SECONDARY), (px + 10, cur_y))
            cur_y += 40

        # ---------------------------------------------------------------- #
        # Kartu 5: Petunjuk Shortcut / Footer
        # ---------------------------------------------------------------- #
        footer_y = surface.get_height() - 76
        footer_h = 64
        draw_card(surface, pygame.Rect(px, footer_y, pw, footer_h), (244, 247, 253, 235), border_color=(200, 212, 230, 200), border_radius=8)

        surface.blit(self.fonts["sm"].render("[R] Reset Duel", True, config.DEBUG_TEXT_SECONDARY), (px + 12, footer_y + 8))
        surface.blit(self.fonts["sm"].render("[Tab] Kembali ke Peta", True, config.DEBUG_TEXT_SECONDARY), (px + 12, footer_y + 26))
        surface.blit(self.fonts["sm"].render("[1..4] Shortcut Aksi", True, config.DEBUG_TEXT_HIGHLIGHT), (px + 12, footer_y + 44))

        # Gambar Dropdowns paling atas agar popup melayang tanpa tertutup
        self.dropdown_battle_eval.draw(surface, self.fonts)
        self.dropdown_battle_algo.draw(surface, self.fonts)
        if self.depth_help_open:
            self._draw_depth_help(surface)
        if self.move_ordering_help_open:
            self._draw_move_ordering_help(surface)

    def _draw_depth_help(self, surface):
        help_font = self.fonts["sm"]
        help_lines = self._depth_help_lines(help_font, 250)
        popup = self._depth_help_popup_rect(len(help_lines))
        draw_card(surface, popup, (252, 253, 255, 250), border_color=config.DEBUG_TEXT_HIGHLIGHT, border_radius=10, border_width=1)
        title = self.fonts.get("bubble", self.fonts["sm"]).render("Tentang Kedalaman AI", True, config.DEBUG_TEXT_HIGHLIGHT)
        surface.blit(title, (popup.x + 12, popup.y + 10))
        y = popup.y + 32
        for line in help_lines:
            text = help_font.render(line, True, config.DEBUG_TEXT_PRIMARY)
            surface.blit(text, (popup.x + 12, y))
            y += 18

    def _depth_help_lines(self, font, max_width):
        help_text = (
            "Depth adalah jumlah langkah ke depan yang dianalisis AI sebelum memilih aksi. "
            "Depth + membuat analisis lebih jauh dan detail, tetapi waktu berpikir bisa lebih lama. "
            "Depth - membuat analisis lebih cepat dan ringan."
        )
        return self._wrap_overlay_text(help_text, font, max_width)

    def _depth_help_popup_rect(self, line_count):
        height = 34 + line_count * 18 + 12
        return pygame.Rect(self.panel_x + self.panel_w + 10, self.panel_y + 145, 274, height)

    def _draw_move_ordering_help(self, surface):
        help_font = self.fonts["sm"]
        help_lines = self._move_ordering_help_lines(help_font, 250)
        popup = self._move_ordering_help_popup_rect(len(help_lines))
        draw_card(surface, popup, (252, 253, 255, 250), border_color=config.DEBUG_TEXT_HIGHLIGHT, border_radius=10, border_width=1)
        title = self.fonts.get("bubble", self.fonts["sm"]).render("Tentang Move Ordering", True, config.DEBUG_TEXT_HIGHLIGHT)
        surface.blit(title, (popup.x + 12, popup.y + 10))
        y = popup.y + 32
        for line in help_lines:
            surface.blit(help_font.render(line, True, config.DEBUG_TEXT_PRIMARY), (popup.x + 12, y))
            y += 18

    def _move_ordering_help_lines(self, font, max_width):
        help_text = (
            "Move Ordering mengatur urutan langkah yang diperiksa AI. "
            "ON memeriksa langkah yang dianggap lebih baik lebih dulu, sehingga AI bisa memilih lebih cepat. "
            "OFF memeriksa langkah tanpa pengurutan khusus dan dapat membutuhkan lebih banyak waktu."
        )
        return self._wrap_overlay_text(help_text, font, max_width)

    def _move_ordering_help_popup_rect(self, line_count):
        height = 34 + line_count * 18 + 12
        return pygame.Rect(self.panel_x + self.panel_w + 10, self.panel_y + 175, 274, height)

    @staticmethod
    def _wrap_overlay_text(text, font, max_width):
        words = text.split(" ")
        lines = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    # ------------------------------------------------------------------ #
    # Event Handling Router
    # ------------------------------------------------------------------ #
    def handle_event(self, event):
        if self.mode == "EXPLORATION":
            if event.type == MOUSEBUTTONDOWN and event.button == 1 and self.cost_toggle_rect.collidepoint(event.pos):
                self.show_costs = not self.show_costs
                return True
            return self.dropdown_algo.handle_event(event)

        # Mode BATTLE
        if self.dropdown_battle_algo.handle_event(event):
            return True
        if self.dropdown_battle_eval.handle_event(event):
            return True

        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            if self.btn_depth_help.collidepoint(pos):
                self.depth_help_open = not self.depth_help_open
                return True
            if self.btn_move_ordering_help.collidepoint(pos):
                self.move_ordering_help_open = not self.move_ordering_help_open
                return True
            if self.depth_help_open:
                popup = self._depth_help_popup_rect(len(self._depth_help_lines(self.fonts["sm"], 250)))
                if not popup.collidepoint(pos):
                    self.depth_help_open = False
                    return True
            if self.move_ordering_help_open:
                popup = self._move_ordering_help_popup_rect(
                    len(self._move_ordering_help_lines(self.fonts["sm"], 250))
                )
                if not popup.collidepoint(pos):
                    self.move_ordering_help_open = False
                    return True

            # Tombol Depth
            if self.btn_depth_minus.collidepoint(pos):
                if self.battle_system and self.battle_system.depth > 1:
                    self.battle_system.depth -= 1
                return True
            if self.btn_depth_plus.collidepoint(pos):
                if self.battle_system and self.battle_system.depth < 8:
                    self.battle_system.depth += 1
                return True

            # Tombol Move Ordering Toggle
            if self.btn_move_ordering.collidepoint(pos):
                if self.battle_system:
                    self.battle_system.use_move_ordering = not self.battle_system.use_move_ordering
                return True

            # Tombol Aksi Player
            if self.battle_system and not self.battle_system.state.is_npc_turn and not self.battle_system.is_finished:
                if self.btn_attack.collidepoint(pos):
                    self.battle_system.execute_player_action(ACTION_ATTACK)
                    return True
                elif self.btn_heavy.collidepoint(pos):
                    self.battle_system.execute_player_action(ACTION_HEAVY)
                    return True
                elif self.btn_defend.collidepoint(pos):
                    self.battle_system.execute_player_action(ACTION_DEFEND)
                    return True
                elif self.btn_potion.collidepoint(pos):
                    self.battle_system.execute_player_action(ACTION_POTION)
                    return True

        return False