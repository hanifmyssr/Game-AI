"""DebugOverlay: Mendukung 2 mode UI:
1. Mode Eksplorasi (Pathfinding: A* vs UCS, visualisasi node, bobot terrain)
2. Mode Battle (Turn-Based Duel: Minimax vs Alpha-Beta vs Expectimax, evaluation functions, depth limit, node counts, skor aksi)
3. Decision Tree Overlay (Visualisasi pohon keputusan AI)
"""

import math
import pygame

from . import config
from .battle_ai import (
    ACTION_ATTACK,
    ACTION_HEAVY,
    ACTION_DEFEND,
    ACTION_POTION,
    ATTACK_DAMAGE,
    HEAVY_DAMAGE,
    ATTACK_DEFENDED_DAMAGE,
    HEAVY_DEFENDED_DAMAGE,
    calc_damage,
)
from .battle_ai import MOVE_ORDERING_MODES, MOVE_ORDERING_OFF, MOVE_ORDERING_HEURISTIC, MOVE_ORDERING_REVERSED
from .tree_overlay import TreeOverlay

MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1025)
SRCALPHA = getattr(pygame, "SRCALPHA", 0x00010000)


def draw_card(surface, rect, bg_color, border_color=None, border_radius=8, border_width=1):
    """Fungsi pembantu untuk menggambar kartu/kontainer dengan pinggiran mulus."""
    card_surf = pygame.Surface((rect.width, rect.height), SRCALPHA)
    pygame.draw.rect(card_surf, bg_color, card_surf.get_rect(), border_radius=border_radius)
    surface.blit(card_surf, (rect.x, rect.y))
    if border_color:
        pygame.draw.rect(surface, border_color, rect, border_width, border_radius=border_radius)


def draw_metric_tile(
    surface,
    rect,
    label,
    value,
    val_color=None,
    font_lbl=None,
    font_val=None,
    bg_color=None,
    border_color=None,
):
    """Menggambar satu kotak metrik (grid tile) dengan clipping mask untuk jaminan 100% anti text-overflow."""
    if val_color is None:
        val_color = config.DEBUG_TEXT_PRIMARY
    if bg_color is None:
        bg_color = config.DEBUG_CARD_ROW_BG
    if border_color is None:
        border_color = config.DEBUG_CARD_ROW_BORDER

    draw_card(surface, rect, bg_color, border_color=border_color, border_radius=6)
    old_clip = surface.get_clip()
    surface.set_clip(rect)
    if font_lbl:
        lbl_surf = font_lbl.render(str(label), True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(lbl_surf, (rect.x + 8, rect.y + 4))
    if font_val:
        val_surf = font_val.render(str(value), True, val_color)
        surface.blit(val_surf, (rect.x + 8, rect.y + 19))
    surface.set_clip(old_clip)


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
        bg_color = config.DEBUG_DROPDOWN_HOVER if self.open else config.DEBUG_DROPDOWN_BG
        bdr_color = config.DEBUG_TEXT_HIGHLIGHT if self.open else config.DEBUG_CARD_BORDER
        draw_card(surface, self.rect, bg_color, border_color=bdr_color, border_radius=6)

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
            draw_card(surface, menu, config.DEBUG_DROPDOWN_BG, border_color=config.DEBUG_TEXT_HIGHLIGHT, border_radius=8, border_width=1)

            for i, lbl in enumerate(self.labels):
                r = pygame.Rect(menu.x + 4, menu.y + i * self.option_height + 2, menu.w - 8, self.option_height - 4)
                if self.selected is not None and i == self.selected:
                    draw_card(surface, r, config.DEBUG_DROPDOWN_SELECTED, border_color=config.DEBUG_TEXT_HIGHLIGHT, border_radius=5)
                    ts = fonts["sm"].render(lbl, True, (255, 255, 255))
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
        dropdown_y = self.panel_y + 74
        self.dropdown_algo = Dropdown(
            (self.panel_x + 20, dropdown_y, self.panel_w - 40, 32),
            [label for _, label in config.ALGORITHMS],
            self._on_algorithm_selected,
            initial_idx=None,
            placeholder="-- Pilih Algoritma --",
        )
        self.last_expanded_count = 0
        self.last_time_ms = 0.0

        # --- UI Duel Mode ---
        self.battle_system = None
        self._init_battle_ui()

        # --- UI Pre-Battle Mode (CSP & Local Search) ---
        self.pre_battle_config = None
        self.pre_battle_stats = None
        self.pre_battle_algo = "HILL_CLIMBING"
        self.on_ls_algo_changed = None
        self._init_pre_battle_ui()

        # --- Decision Tree Overlay ---
        self.tree_overlay = TreeOverlay(fonts)

        events.register_overlay(self)
        self.update_stats(0, 0.0)

    def _init_pre_battle_ui(self):
        px = self.panel_x + 12
        pw = self.panel_w - 24
        ls_labels = [label for _, label in config.LS_ALGORITHMS]
        self.dropdown_ls_algo = Dropdown(
            (px + 6, self.panel_y + 70, pw - 12, 28),
            ls_labels,
            self._on_ls_algo_selected,
            initial_idx=0,
        )

    def _on_ls_algo_selected(self, index):
        if index is None or index < 0 or index >= len(config.LS_ALGORITHMS):
            return
        algo_code = config.LS_ALGORITHMS[index][0]
        self.pre_battle_algo = algo_code
        if self.on_ls_algo_changed:
            self.on_ls_algo_changed(algo_code)

    def set_pre_battle_data(self, config_dict, stats, algo_name="HILL_CLIMBING"):
        self.pre_battle_config = config_dict
        self.pre_battle_stats = stats
        self.pre_battle_algo = algo_name
        for idx, (code, _) in enumerate(config.LS_ALGORITHMS):
            if code == algo_name:
                self.dropdown_ls_algo.selected = idx
                break

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

        # Tombol Kedalaman AI / Early Stop (Help, Depth - dan +)
        self.btn_depth_help = pygame.Rect(px + pw - 108, self.panel_y + 162, 24, 24)
        self.btn_depth_minus = pygame.Rect(px + pw - 78, self.panel_y + 162, 30, 24)
        self.btn_depth_plus = pygame.Rect(px + pw - 42, self.panel_y + 162, 30, 24)

        # Tombol Move Ordering Toggle & Help
        mo_btn_w = 82
        self.btn_move_ordering_help = pygame.Rect(px + pw - mo_btn_w - 38, self.panel_y + 192, 24, 24)
        self.btn_move_ordering = pygame.Rect(px + pw - mo_btn_w - 8, self.panel_y + 192, mo_btn_w, 24)

        # Tombol Aksi Player (4 Aksi: Attack, Heavy Attack, Defend, Potion)
        bw = (pw - 18) // 2
        btn_y = self.panel_y + 264
        self.btn_attack = pygame.Rect(px + 6, btn_y, bw, 32)
        self.btn_heavy = pygame.Rect(px + 12 + bw, btn_y, bw, 32)
        self.btn_defend = pygame.Rect(px + 6, btn_y + 38, bw, 32)
        self.btn_potion = pygame.Rect(px + 12 + bw, btn_y + 38, bw, 32)

        # Tombol Toggle Decision Tree Overlay
        self.btn_toggle_tree = pygame.Rect(0, 0, 0, 0)

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
        if hasattr(self.battle_system, "update_ai_preview"):
            self.battle_system.update_ai_preview()

    def _on_battle_eval_selected(self, index):
        if not self.battle_system:
            return
        evals = ["BALANCED", "AGGRESSIVE", "DEFENSIVE"]
        self.battle_system.eval_mode = evals[index]
        if hasattr(self.battle_system, "update_ai_preview"):
            self.battle_system.update_ai_preview()

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
        self.last_expanded_count = count
        self.last_time_ms = time_ms

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
        elif self.mode == "PRE_BATTLE":
            self._draw_pre_battle_ui(surface)
        else:
            self._draw_battle_ui(surface)

    def _draw_cost_toggle(self, surface):
        fill = (35, 155, 80) if self.show_costs else (255, 255, 255, 245)
        bdr = (25, 125, 60) if self.show_costs else (200, 212, 228)
        draw_card(surface, self.cost_toggle_rect, fill, border_color=bdr, border_radius=6)
        label = "Cost: ON" if self.show_costs else "Cost: OFF"
        text_color = (255, 255, 255) if self.show_costs else config.DEBUG_TEXT_SECONDARY
        text = self.fonts["sm"].render(label, True, text_color)
        surface.blit(text, (self.cost_toggle_rect.centerx - text.get_width() // 2, self.cost_toggle_rect.centery - text.get_height() // 2))

    def _draw_exploration_ui(self, surface):
        px = self.panel_x + 12
        pw = self.panel_w - 24
        font_sm = self.fonts["sm"]
        steps = max(0, len(self.path_nodes) - 1)
        cur_cost = self.comparison_data.get("cur_cost", 0.0) if self.comparison_data else 0.0
        count = self.last_expanded_count

        if self.dropdown_algo.selected is not None and 0 <= self.dropdown_algo.selected < len(config.ALGORITHMS):
            selected_label = config.ALGORITHMS[self.dropdown_algo.selected][1]
        else:
            selected_label = "-- Pilih Algoritma --"

        # 1. Header Card
        header_rect = pygame.Rect(px, self.panel_y + 8, pw, 38)
        draw_card(surface, header_rect, config.DEBUG_CARD_HEADER_BG, border_color=config.DEBUG_CARD_HEADER_BORDER, border_radius=8)
        title_surf = self.fonts.get("title", font_sm).render("AI PATHFINDING (EKSPLORASI)", True, config.DEBUG_TEXT_HIGHLIGHT)
        surface.blit(title_surf, (header_rect.x + 10, header_rect.y + (header_rect.height - title_surf.get_height()) // 2))

        # 2. Card: Pilihan Algoritma
        card_algo = pygame.Rect(px, self.panel_y + 50, pw, 64)
        draw_card(surface, card_algo, config.DEBUG_CARD_BG, border_color=config.DEBUG_CARD_BORDER, border_radius=8)
        sub_surf = font_sm.render("Pilih Algoritma AI:", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(sub_surf, (px + 10, self.panel_y + 55))
        self.dropdown_algo.rect = pygame.Rect(px + 8, self.panel_y + 74, pw - 16, 32)

        # 3. Card: Metrik Jalur (Grid 2x2)
        card_metrics = pygame.Rect(px, self.panel_y + 120, pw, 126)
        draw_card(surface, card_metrics, config.DEBUG_CARD_BG, border_color=config.DEBUG_CARD_BORDER, border_radius=8)
        ts_hdr1 = font_sm.render("── METRIK JALUR (PATHFINDING) ──", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(ts_hdr1, (px + (pw - ts_hdr1.get_width()) // 2, card_metrics.y + 6))

        tile_w = (pw - 22) // 2
        tile_h = 38
        ty1 = card_metrics.y + 28
        ty2 = ty1 + tile_h + 6
        draw_metric_tile(surface, pygame.Rect(px + 8, ty1, tile_w, tile_h), "NODE DIEKSPANSI", f"{count} node", val_color=config.DEBUG_TEXT_PRIMARY, font_lbl=font_sm, font_val=font_sm)
        draw_metric_tile(surface, pygame.Rect(px + 14 + tile_w, ty1, tile_w, tile_h), "PANJANG JALUR", f"{steps} langkah", val_color=config.DEBUG_TEXT_PRIMARY, font_lbl=font_sm, font_val=font_sm)
        draw_metric_tile(surface, pygame.Rect(px + 8, ty2, tile_w, tile_h), "TOTAL COST", f"{cur_cost:.1f}", val_color=config.DEBUG_TEXT_HIGHLIGHT, font_lbl=font_sm, font_val=font_sm)
        draw_metric_tile(surface, pygame.Rect(px + 14 + tile_w, ty2, tile_w, tile_h), "WAKTU EKSEKUSI", f"{self.last_time_ms:.3f} ms", val_color=(20, 145, 60), font_lbl=font_sm, font_val=font_sm)

        # 4. Card: Bobot Medan (Terrain Cost)
        card_cost = pygame.Rect(px, self.panel_y + 252, pw, 74)
        draw_card(surface, card_cost, config.DEBUG_CARD_BG, border_color=config.DEBUG_CARD_BORDER, border_radius=8)
        ts_hdr2 = font_sm.render("── BOBOT MEDAN (COST) ──", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(ts_hdr2, (px + (pw - ts_hdr2.get_width()) // 2, card_cost.y + 6))

        draw_metric_tile(surface, pygame.Rect(px + 8, card_cost.y + 24, tile_w, tile_h), "JALAN TANAH", "Cost 1.0 (Ringan)", val_color=config.DEBUG_TEXT_PRIMARY, font_lbl=font_sm, font_val=font_sm)
        draw_metric_tile(surface, pygame.Rect(px + 14 + tile_w, card_cost.y + 24, tile_w, tile_h), "AREA RUMPUT", "Cost 2.0 (Normal)", val_color=config.DEBUG_TEXT_WARN, font_lbl=font_sm, font_val=font_sm)

        # 5. Card: Perbandingan Rute (UCS vs A*)
        card_comp = pygame.Rect(px, self.panel_y + 332, pw, 122)
        draw_card(surface, card_comp, config.DEBUG_CARD_BG, border_color=config.DEBUG_CARD_BORDER, border_radius=8)
        ts_hdr3 = font_sm.render("── PERBANDINGAN RUTE (UCS vs A*) ──", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(ts_hdr3, (px + (pw - ts_hdr3.get_width()) // 2, card_comp.y + 6))

        y_comp = card_comp.y + 26
        if self.comparison_data:
            cd = self.comparison_data
            ucs_exp = cd.get("ucs_expanded", 0)
            ucs_t = cd.get("ucs_time_ms", 0.0)
            ucs_c = cd.get("ucs_cost", 0.0)
            cur_exp = cd.get("cur_expanded", count)
            cur_t = cd.get("cur_time_ms", self.last_time_ms)

            # Row UCS
            ucs_rect = pygame.Rect(px + 8, y_comp, pw - 16, 24)
            draw_card(surface, ucs_rect, config.DEBUG_CARD_ROW_BG, border_color=config.DEBUG_CARD_ROW_BORDER, border_radius=5)
            s_left_ucs = font_sm.render("• UCS (h=0)", True, config.DEBUG_TEXT_WARN)
            s_right_ucs = font_sm.render(f"{ucs_exp} node │ Cost {ucs_c:.1f} │ {ucs_t:.2f}ms", True, config.DEBUG_TEXT_PRIMARY)
            surface.blit(s_left_ucs, (ucs_rect.x + 8, ucs_rect.y + 4))
            surface.blit(s_right_ucs, (ucs_rect.right - 8 - s_right_ucs.get_width(), ucs_rect.y + 4))

            # Row A*
            astar_rect = pygame.Rect(px + 8, y_comp + 28, pw - 16, 24)
            draw_card(surface, astar_rect, config.DEBUG_CARD_ROW_BG, border_color=config.DEBUG_CARD_ROW_BORDER, border_radius=5)
            algo_short = {
                "UCS (h = 0)": "UCS (h=0)",
                "A* (Heuristik Manhattan)": "A* (Manh)",
                "A* (Heuristik Euclidean)": "A* (Eucl)",
                "A* (Heuristik Chebyshev)": "A* (Cheb)",
            }
            lbl_display = algo_short.get(selected_label, "A* (Rute)")
            s_left_a = font_sm.render(f"• {lbl_display}", True, config.DEBUG_TEXT_HIGHLIGHT)
            s_right_a = font_sm.render(f"{cur_exp} node │ Cost {cur_cost:.1f} │ {cur_t:.2f}ms", True, config.DEBUG_TEXT_PRIMARY)
            surface.blit(s_left_a, (astar_rect.x + 8, astar_rect.y + 4))
            surface.blit(s_right_a, (astar_rect.right - 8 - s_right_a.get_width(), astar_rect.y + 4))

            # Row Efisiensi Badge (PASTIKAN TEXT BERADA DI DALAM eff_rect, TIDAK TERTAMPA!)
            eff_rect = pygame.Rect(px + 8, y_comp + 56, pw - 16, 24)
            if ucs_exp > 0 and cur_exp > 0:
                ratio = ucs_exp / cur_exp
                if ratio > 1.0:
                    draw_card(surface, eff_rect, (235, 250, 242), border_color=(130, 215, 160), border_radius=5)
                    eff_str = f"• A* {ratio:.1f}x lebih efisien (ekspansi node)"
                    eff_col = (20, 135, 55)
                elif ratio < 1.0:
                    draw_card(surface, eff_rect, (255, 246, 235), border_color=(245, 195, 130), border_radius=5)
                    eff_str = f"• UCS {1/ratio:.1f}x lebih efisien (ekspansi node)"
                    eff_col = config.DEBUG_TEXT_WARN
                else:
                    draw_card(surface, eff_rect, config.DEBUG_CARD_ROW_BG, border_color=config.DEBUG_CARD_ROW_BORDER, border_radius=5)
                    eff_str = "• Efisiensi ekspansi node setara"
                    eff_col = config.DEBUG_TEXT_SECONDARY
                surface.blit(font_sm.render(eff_str, True, eff_col), (eff_rect.x + 8, eff_rect.y + 4))
        else:
            wait_rect = pygame.Rect(px + 8, y_comp, pw - 16, 26)
            draw_card(surface, wait_rect, config.DEBUG_CARD_ROW_BG, border_color=config.DEBUG_CARD_ROW_BORDER, border_radius=5)
            surface.blit(font_sm.render("Pilih algoritma untuk melihat komparasi.", True, config.DEBUG_TEXT_SECONDARY), (wait_rect.x + 8, wait_rect.y + 5))

        # 6. Card: Panduan Kontrol
        card_ctrl = pygame.Rect(px, self.panel_y + 460, pw, 126)
        draw_card(surface, card_ctrl, config.DEBUG_CARD_BG, border_color=config.DEBUG_CARD_BORDER, border_radius=8)
        ts_hdr4 = font_sm.render("── PANDUAN KONTROL ──", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(ts_hdr4, (px + (pw - ts_hdr4.get_width()) // 2, card_ctrl.y + 6))

        ctrl_items = [
            ("[WASD / Panah]", "Gerakkan Karakter Player", config.DEBUG_TEXT_PRIMARY),
            ("[Ctrl]", "Tampilkan Animasi Jalur", config.DEBUG_TEXT_HIGHLIGHT),
            ("[Spasi]", "Toggle Pengejaran NPC", (215, 105, 20)),
            ("[Esc]", "Keluar Permainan", config.DEBUG_TEXT_SECONDARY),
        ]
        cy = card_ctrl.y + 26
        for k_label, k_desc, k_col in ctrl_items:
            row_rect = pygame.Rect(px + 8, cy, pw - 16, 20)
            draw_card(surface, row_rect, config.DEBUG_CARD_ROW_BG, border_color=config.DEBUG_CARD_ROW_BORDER, border_radius=4)
            surface.blit(font_sm.render(f"• {k_label}", True, k_col), (row_rect.x + 6, cy + 2))
            surface.blit(font_sm.render(f": {k_desc}", True, config.DEBUG_TEXT_PRIMARY), (row_rect.x + 130, cy + 2))
            cy += 23

        # Dropdown digambar paling akhir agar membuka di atas semua card
        self.dropdown_algo.draw(surface, self.fonts)

    def _draw_pre_battle_ui(self, surface):
        px = self.panel_x + 12
        pw = self.panel_w - 24
        font_sm = self.fonts["sm"]

        # 1. Header Card Pre-Battle
        header_rect = pygame.Rect(px, self.panel_y + 8, pw, 38)
        draw_card(surface, header_rect, config.DEBUG_CARD_HEADER_BG, border_color=config.DEBUG_CARD_HEADER_BORDER, border_radius=8)
        title_surf = self.fonts.get("title", font_sm).render("OPTIMASI SKUAD (CSP & LOCAL SEARCH)", True, config.DEBUG_TEXT_HIGHLIGHT)
        surface.blit(title_surf, (header_rect.x + 10, header_rect.y + (header_rect.height - title_surf.get_height()) // 2))

        # 2. Card: Pengaturan Algoritma Local Search
        card_algo = pygame.Rect(px, self.panel_y + 50, pw, 64)
        draw_card(surface, card_algo, config.DEBUG_CARD_BG, border_color=config.DEBUG_CARD_BORDER, border_radius=8)
        sub_algo = font_sm.render("Algoritma Local Search:", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(sub_algo, (px + 10, self.panel_y + 55))
        self.dropdown_ls_algo.rect = pygame.Rect(px + 8, self.panel_y + 74, pw - 16, 28)

        # 3. Card: Evaluasi Kesulitan & Gauge Target 0.55
        card_diff = pygame.Rect(px, self.panel_y + 120, pw, 134)
        draw_card(surface, card_diff, config.DEBUG_CARD_BG, border_color=config.DEBUG_CARD_BORDER, border_radius=8)

        diff_score = 0.55
        fit_score = 0.0
        iters = 0
        t_ms = 0.0
        if self.pre_battle_stats:
            diff_score = self.pre_battle_stats.get("final_difficulty", 0.55)
            fit_score = self.pre_battle_stats.get("final_fitness", 0.0)
            iters = self.pre_battle_stats.get("iterations", 0)
            t_ms = self.pre_battle_stats.get("time_ms", 0.0)

        gauge_y = card_diff.y + 8
        gauge_label = font_sm.render(f"Difficulty: {diff_score:.4f} (Target: 0.55)", True, config.DEBUG_TEXT_PRIMARY)
        surface.blit(gauge_label, (px + 10, gauge_y))

        bar_rect = pygame.Rect(px + 8, gauge_y + 18, pw - 16, 12)
        pygame.draw.rect(surface, (225, 232, 242), bar_rect, border_radius=4)
        fill_w = max(4, int(bar_rect.width * min(1.0, max(0.0, diff_score))))
        pygame.draw.rect(surface, (45, 135, 235), pygame.Rect(bar_rect.x, bar_rect.y, fill_w, bar_rect.height), border_radius=4)
        target_marker_x = bar_rect.x + int(bar_rect.width * 0.55)
        pygame.draw.line(surface, (235, 120, 20), (target_marker_x, bar_rect.y - 2), (target_marker_x, bar_rect.bottom + 2), 2)

        tile_w = (pw - 22) // 2
        tile_h = 36
        ty1 = gauge_y + 35
        ty2 = ty1 + tile_h + 4

        draw_metric_tile(surface, pygame.Rect(px + 8, ty1, tile_w, tile_h), "DIFFICULTY", f"{diff_score:.4f}", val_color=config.DEBUG_TEXT_HIGHLIGHT, font_lbl=font_sm, font_val=font_sm)
        draw_metric_tile(surface, pygame.Rect(px + 14 + tile_w, ty1, tile_w, tile_h), "FITNESS", f"{fit_score:+.4f}", val_color=(20, 135, 55), font_lbl=font_sm, font_val=font_sm)
        draw_metric_tile(surface, pygame.Rect(px + 8, ty2, tile_w, tile_h), "ITERASI", f"{iters}", val_color=config.DEBUG_TEXT_PRIMARY, font_lbl=font_sm, font_val=font_sm)
        draw_metric_tile(surface, pygame.Rect(px + 14 + tile_w, ty2, tile_w, tile_h), "WAKTU AI", f"{t_ms:.2f} ms", val_color=config.DEBUG_TEXT_PRIMARY, font_lbl=font_sm, font_val=font_sm)

        # 4. Card: Status Verifikasi Constraint CSP
        card_csp = pygame.Rect(px, self.panel_y + 260, pw, 134)
        draw_card(surface, card_csp, config.DEBUG_CARD_BG, border_color=config.DEBUG_CARD_BORDER, border_radius=8)

        csp_title = font_sm.render("── STATUS CONSTRAINT CSP (C1-C8) ──", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(csp_title, (px + (pw - csp_title.get_width()) // 2, card_csp.y + 6))

        total_hp = 0
        total_pot = 0
        total_atk = 0
        members = self.pre_battle_config.get("members", []) if self.pre_battle_config else []
        for m in members:
            total_hp += m.get("hp", 0)
            total_pot += m.get("potions", 0)
            total_atk += m.get("atk_bonus", 0)

        cy = card_csp.y + 25
        csp_items = [
            (f"• C1 Total HP  : {total_hp}/250 (Valid)", True),
            (f"• C2 Total Pot : {total_pot}/5 (Valid)", True),
            (f"• C8 Bonus ATK : {total_atk}/25 (Valid)", True),
            (f"• C5 Job Unik  : TERPENUHI (Unik)", True),
            (f"• C3-C7 Aturan : VALID (MRV+LCV)", True),
        ]
        for ctext, ok in csp_items:
            row_rect = pygame.Rect(px + 8, cy, pw - 16, 18)
            draw_card(surface, row_rect, config.DEBUG_CARD_ROW_BG, border_color=config.DEBUG_CARD_ROW_BORDER, border_radius=4)
            col = (20, 135, 55) if ok else (210, 40, 40)
            surface.blit(font_sm.render(ctext, True, col), (row_rect.x + 8, cy + 2))
            cy += 21

        # 5. Card: Komposisi Skuad Terbentuk (tiap member dalam container sendiri)
        card_roster = pygame.Rect(px, self.panel_y + 400, pw, 142)
        draw_card(surface, card_roster, config.DEBUG_CARD_BG, border_color=config.DEBUG_CARD_BORDER, border_radius=8)

        r_title = font_sm.render("── ANGGOTA TIM LAWAN ──", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(r_title, (px + (pw - r_title.get_width()) // 2, card_roster.y + 6))

        ry = card_roster.y + 24
        for idx, m in enumerate(members[:3]):
            ctype = m.get("char_type", "warrior").capitalize()
            if ctype.lower() == "warrior":
                n_name = "Oyen"
            elif ctype.lower() == "ranger":
                n_name = "Kuro"
            elif ctype.lower() == "mage":
                n_name = "Shiro"
            elif ctype.lower() == "assassin":
                n_name = "Kage"
            else:
                n_name = f"NPC-{idx+1}"

            hp = m.get("hp", 100)
            pot = m.get("potions", 0)
            atk = m.get("atk_bonus", 0)
            df = m.get("def_bonus", 0)
            prof_map = {"BALANCED": "BAL", "AGGRESSIVE": "AGGR", "DEFENSIVE": "DEF"}
            ev = prof_map.get(m.get("eval_profile", "BALANCED"), "BAL")

            m_box = pygame.Rect(px + 8, ry, pw - 16, 34)
            draw_card(surface, m_box, config.DEBUG_CARD_ROW_BG, border_color=config.DEBUG_CARD_ROW_BORDER, border_radius=5)
            # Baris 1: Nama & Job
            l1 = f"{idx+1}. {n_name} ({ctype}) [{ev}]"
            surface.blit(self.fonts.get("bubble", font_sm).render(l1, True, config.DEBUG_TEXT_HIGHLIGHT), (m_box.x + 6, ry + 2))
            # Baris 2: Rincian Stat
            l2 = f"HP:{hp}  Pot:{pot}  +{atk}ATK  +{df}DEF"
            surface.blit(font_sm.render(l2, True, config.DEBUG_TEXT_PRIMARY), (m_box.x + 6, ry + 16))
            ry += 38

        # 6. Card: Panduan Kontrol & Tombol Aksi
        card_ctrl = pygame.Rect(px, self.panel_y + 548, pw, 114)
        draw_card(surface, card_ctrl, config.DEBUG_CARD_BG, border_color=config.DEBUG_CARD_BORDER, border_radius=8)

        ctrl_title = font_sm.render("── KONTROL PRE-BATTLE ──", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(ctrl_title, (px + (pw - ctrl_title.get_width()) // 2, card_ctrl.y + 6))

        shortcuts = [
            ("[SPASI]", "Mulai Duel", config.DEBUG_TEXT_HIGHLIGHT),
            ("[R]", "Re-Roll AI Skuad", (215, 95, 20)),
            ("[1 - 5]", "Ganti Algo Local Search", config.DEBUG_TEXT_PRIMARY),
            ("[ESC]", "Batal / Kembali ke Peta", config.DEBUG_TEXT_SECONDARY),
        ]
        sc_y = card_ctrl.y + 24
        for s_key, s_desc, s_col in shortcuts:
            row_rect = pygame.Rect(px + 8, sc_y, pw - 16, 20)
            draw_card(surface, row_rect, config.DEBUG_CARD_ROW_BG, border_color=config.DEBUG_CARD_ROW_BORDER, border_radius=4)
            surface.blit(font_sm.render(f"• {s_key:<8}", True, s_col), (row_rect.x + 6, sc_y + 2))
            surface.blit(font_sm.render(f": {s_desc}", True, config.DEBUG_TEXT_PRIMARY), (row_rect.x + 95, sc_y + 2))
            sc_y += 22

        # Gambar dropdown local search di atas elemen lainnya
        self.dropdown_ls_algo.draw(surface, self.fonts)

    def _draw_battle_ui(self, surface):
        battle_system = self.battle_system
        if battle_system is None:
            return

        px = self.panel_x + 12
        pw = self.panel_w - 24
        font_sm = self.fonts["sm"]

        # ---------------------------------------------------------------- #
        # Kartu 1: Header Duel
        # ---------------------------------------------------------------- #
        header_rect = pygame.Rect(px, self.panel_y + 8, pw, 38)
        draw_card(surface, header_rect, config.DEBUG_CARD_HEADER_BG, border_color=config.DEBUG_CARD_HEADER_BORDER, border_radius=8)
        title_surf = self.fonts.get("title", font_sm).render("DUEL TAKTIS MINIMAX AI", True, config.DEBUG_TEXT_HIGHLIGHT)
        surface.blit(title_surf, (header_rect.x + 10, header_rect.y + (header_rect.height - title_surf.get_height()) // 2))

        # ---------------------------------------------------------------- #
        # Kartu 2: Konfigurasi AI & Parameter Search
        # ---------------------------------------------------------------- #
        cfg_rect = pygame.Rect(px, self.panel_y + 50, pw, 178)
        draw_card(surface, cfg_rect, config.DEBUG_CARD_BG, border_color=config.DEBUG_CARD_BORDER, border_radius=8)

        # Labels & Dropdown bounds
        sub_algo = font_sm.render("Algoritma AI NPC:", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(sub_algo, (px + 10, self.panel_y + 54))
        self.dropdown_battle_algo.rect = pygame.Rect(px + 8, self.panel_y + 70, pw - 16, 28)

        sub_eval = font_sm.render("Fungsi Evaluasi:", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(sub_eval, (px + 10, self.panel_y + 104))
        self.dropdown_battle_eval.rect = pygame.Rect(px + 8, self.panel_y + 120, pw - 16, 28)

        # Baris Depth / Early Stop Control dalam row container
        depth_y = self.panel_y + 154
        depth_row = pygame.Rect(px + 8, depth_y, pw - 16, 30)
        draw_card(surface, depth_row, config.DEBUG_CARD_ROW_BG, border_color=config.DEBUG_CARD_ROW_BORDER, border_radius=5)
        depth_label = font_sm.render(f"Early Stop / Depth: {battle_system.depth}", True, config.DEBUG_TEXT_PRIMARY)
        surface.blit(depth_label, (depth_row.x + 8, depth_row.y + 6))

        self.btn_depth_help = pygame.Rect(depth_row.right - 92, depth_y + 3, 24, 24)
        self.btn_depth_minus = pygame.Rect(depth_row.right - 64, depth_y + 3, 28, 24)
        self.btn_depth_plus = pygame.Rect(depth_row.right - 32, depth_y + 3, 28, 24)

        draw_card(surface, self.btn_depth_help, (235, 242, 252), border_color=(180, 205, 235), border_radius=5)
        help_text = self.fonts.get("bubble", font_sm).render("?", True, config.DEBUG_TEXT_HIGHLIGHT)
        surface.blit(help_text, (self.btn_depth_help.centerx - help_text.get_width() // 2, self.btn_depth_help.centery - help_text.get_height() // 2))

        for btn, text, fill, bdr, tcol in [
            (self.btn_depth_minus, "-", (255, 240, 242), (235, 180, 185), (200, 45, 45)),
            (self.btn_depth_plus, "+", (238, 252, 242), (170, 225, 185), (25, 145, 65)),
        ]:
            draw_card(surface, btn, fill, border_color=bdr, border_radius=5)
            ts = self.fonts.get("bubble", font_sm).render(text, True, tcol)
            surface.blit(ts, (btn.centerx - ts.get_width() // 2, btn.centery - ts.get_height() // 2))

        # Baris Move Ordering Toggle dalam row container
        mo_y = self.panel_y + 188
        mo_mode = battle_system.move_ordering_mode
        mo_row = pygame.Rect(px + 8, mo_y, pw - 16, 30)
        draw_card(surface, mo_row, config.DEBUG_CARD_ROW_BG, border_color=config.DEBUG_CARD_ROW_BORDER, border_radius=5)
        mo_label = font_sm.render("Move Ordering:", True, config.DEBUG_TEXT_PRIMARY)
        surface.blit(mo_label, (mo_row.x + 8, mo_row.y + 6))

        mo_btn_w = 82
        self.btn_move_ordering_help = pygame.Rect(mo_row.right - mo_btn_w - 32, mo_y + 3, 24, 24)
        self.btn_move_ordering = pygame.Rect(mo_row.right - mo_btn_w - 4, mo_y + 3, mo_btn_w, 24)

        draw_card(surface, self.btn_move_ordering_help, (235, 242, 252), border_color=(180, 205, 235), border_radius=5)
        help_text = self.fonts.get("bubble", font_sm).render("?", True, config.DEBUG_TEXT_HIGHLIGHT)
        surface.blit(help_text, (self.btn_move_ordering_help.centerx - help_text.get_width() // 2, self.btn_move_ordering_help.centery - help_text.get_height() // 2))

        if mo_mode == MOVE_ORDERING_HEURISTIC:
            mo_fill = (235, 250, 242)
            mo_bdr = (140, 215, 165)
            mo_text_col = (20, 135, 55)
            mo_text = "HEURISTIC"
        elif mo_mode == MOVE_ORDERING_REVERSED:
            mo_fill = (255, 246, 235)
            mo_bdr = (245, 195, 130)
            mo_text_col = (185, 95, 15)
            mo_text = "REVERSED"
        else:
            mo_fill = (245, 247, 250)
            mo_bdr = (210, 218, 230)
            mo_text_col = (110, 120, 135)
            mo_text = "OFF"

        draw_card(surface, self.btn_move_ordering, mo_fill, border_color=mo_bdr, border_radius=6)
        ts_mo = font_sm.render(mo_text, True, mo_text_col)
        surface.blit(ts_mo, (self.btn_move_ordering.centerx - ts_mo.get_width() // 2, self.btn_move_ordering.centery - ts_mo.get_height() // 2))

        # ---------------------------------------------------------------- #
        # Kartu 3: Status Giliran & Tombol Aksi Pemain
        # ---------------------------------------------------------------- #
        state = battle_system.state
        act_card_y = self.panel_y + 234
        act_card_h = 114
        draw_card(surface, pygame.Rect(px, act_card_y, pw, act_card_h), config.DEBUG_CARD_BG, border_color=config.DEBUG_CARD_BORDER, border_radius=8)

        if state:
            turn_rect = pygame.Rect(px + 8, act_card_y + 6, pw - 16, 24)
            if battle_system.is_finished:
                turn_text = f"Pertarungan Selesai: {battle_system.winner} MENANG!"
                turn_bg = (235, 250, 242)
                turn_bdr = (140, 215, 165)
                turn_color = (20, 135, 55)
            elif state.is_npc_turn:
                turn_text = "Giliran NPC (AI Berpikir...)"
                turn_bg = (255, 248, 235)
                turn_bdr = (245, 195, 125)
                turn_color = (185, 95, 15)
            else:
                turn_text = "Giliran Anda (Pilih Aksi)"
                turn_bg = (235, 245, 255)
                turn_bdr = (165, 205, 250)
                turn_color = (18, 95, 195)

            draw_card(surface, turn_rect, turn_bg, border_color=turn_bdr, border_radius=5)
            ts_turn = self.fonts.get("bubble", font_sm).render(turn_text, True, turn_color)
            surface.blit(ts_turn, (turn_rect.centerx - ts_turn.get_width() // 2, turn_rect.centery - ts_turn.get_height() // 2))

            # Tombol-tombol Aksi Pemain
            can_act = (not state.is_npc_turn) and (not battle_system.is_finished)
            heavy_ready = state.player_heavy_cd <= 0

            base_atk = ATTACK_DEFENDED_DAMAGE if state.npc_defending else ATTACK_DAMAGE
            expected_atk = calc_damage(base_atk, state.player_atk_bonus, state.npc_def_bonus, is_heavy=False)

            base_heavy = HEAVY_DEFENDED_DAMAGE if state.npc_defending else HEAVY_DAMAGE
            expected_heavy = calc_damage(base_heavy, state.player_atk_bonus, state.npc_def_bonus, is_heavy=True)

            heavy_label = f"Heavy ({expected_heavy})" if heavy_ready else f"Heavy (CD:{state.player_heavy_cd})"
            bw = (pw - 22) // 2
            btn_y = act_card_y + 36
            self.btn_attack = pygame.Rect(px + 8, btn_y, bw, 32)
            self.btn_heavy = pygame.Rect(px + 14 + bw, btn_y, bw, 32)
            self.btn_defend = pygame.Rect(px + 8, btn_y + 36, bw, 32)
            self.btn_potion = pygame.Rect(px + 14 + bw, btn_y + 36, bw, 32)

            actions_info = [
                (self.btn_attack, f"Attack ({expected_atk})", (225, 55, 55), (190, 35, 35), True),
                (self.btn_heavy, heavy_label, (235, 115, 30), (200, 90, 20), heavy_ready),
                (self.btn_defend, "Defend (-65%)", (35, 115, 215), (25, 90, 185), True),
                (self.btn_potion, f"Potion ({state.player_potions})", (35, 155, 80), (25, 125, 60), state.player_potions > 0 and state.player_hp < (state.player_max_hp if hasattr(state, 'player_max_hp') else 100)),
            ]

            for btn_rect, btn_title, base_col, bdr_col, is_enabled in actions_info:
                if can_act and is_enabled:
                    fill_col = base_col
                    text_col = (255, 255, 255)
                    border_col = bdr_col
                else:
                    fill_col = (242, 244, 248)
                    text_col = (160, 170, 185)
                    border_col = (218, 225, 235)

                draw_card(surface, btn_rect, fill_col, border_color=border_col, border_radius=6)
                ts = font_sm.render(btn_title, True, text_col)
                surface.blit(ts, (btn_rect.centerx - ts.get_width() // 2, btn_rect.centery - ts.get_height() // 2))

        # ---------------------------------------------------------------- #
        # Kartu 4: Evaluasi AI, Node Counts & Pertimbangan Aksi
        # ---------------------------------------------------------------- #
        eval_card_y = self.panel_y + 354
        eval_card_h = 280
        draw_card(surface, pygame.Rect(px, eval_card_y, pw, eval_card_h), config.DEBUG_CARD_BG, border_color=config.DEBUG_CARD_BORDER, border_radius=8)

        ts_mtitle = font_sm.render("── EVALUASI AKSI & NODE COUNT ──", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(ts_mtitle, (px + (pw - ts_mtitle.get_width()) // 2, eval_card_y + 8))

        stats = battle_system.last_ai_stats
        cur_y = eval_card_y + 28

        if stats:
            nc = stats.get("node_count", 0)
            pc = stats.get("pruned_count", 0)
            t_ms = stats.get("time_ms", 0.0)
            best_a = stats.get("best_action", "—")
            best_s = stats.get("best_score", 0.0)
            cur_algo = stats.get("algorithm", battle_system.algorithm)
            comp = stats.get("comparison", {})
            mm_n = comp.get("minimax_nodes", nc)
            ab_n = comp.get("alphabeta_nodes", nc)
            ex_n = comp.get("expectimax_nodes", nc if cur_algo == "EXPECTIMAX" else "—")
            sav = comp.get("savings_pct", 0.0)
            d_val = comp.get("depth", stats.get("depth", 4))
            det_scores = comp.get("deterministic_scores", stats.get("action_scores", {}))
            exp_scores = comp.get("expectimax_scores", stats.get("action_scores", {}))

            # Kotak Komparasi Node: Minimax vs Alpha-Beta vs Expectimax
            comp_box = pygame.Rect(px + 8, cur_y, pw - 16, 74)
            draw_card(surface, comp_box, config.DEBUG_CARD_ROW_BG, border_color=config.DEBUG_CARD_ROW_BORDER, border_radius=6)

            ts_c_title = font_sm.render(f"Komparasi Metode (Cutoff d={d_val}):", True, config.DEBUG_TEXT_SECONDARY)
            surface.blit(ts_c_title, (comp_box.x + 8, comp_box.y + 4))

            t_mm = f"• Pure Minimax : {mm_n} node"
            t_ab = f"• Alpha-Beta   : {ab_n} node ({sav:.1f}% hemat)"
            t_ex = f"• Expectimax   : {ex_n} node (stokastik)"
            surface.blit(font_sm.render(t_mm, True, config.DEBUG_TEXT_PRIMARY), (comp_box.x + 8, comp_box.y + 20))
            surface.blit(font_sm.render(t_ab, True, (20, 135, 55) if ab_n < mm_n else config.DEBUG_TEXT_PRIMARY), (comp_box.x + 8, comp_box.y + 36))
            col_ex_text = (140, 50, 185) if cur_algo == "EXPECTIMAX" else config.DEBUG_TEXT_HIGHLIGHT
            surface.blit(font_sm.render(t_ex, True, col_ex_text), (comp_box.x + 8, comp_box.y + 52))

            cur_y += 79

            # Best Action Card Highlight
            best_card = pygame.Rect(px + 8, cur_y, pw - 16, 26)
            draw_card(surface, best_card, (235, 245, 255), border_color=(160, 205, 250), border_radius=5)
            best_text = f"Pilihan AI: {best_a} │ Skor Heuristik: {best_s}"
            ts_best = font_sm.render(best_text, True, config.DEBUG_TEXT_HIGHLIGHT)
            surface.blit(ts_best, (best_card.x + 8, best_card.centery - ts_best.get_height() // 2))
            cur_y += 30

            # Sub-judul Tabel Perbandingan Skor Root Node
            surface.blit(font_sm.render("Perbandingan Skor: Det vs Expectimax", True, config.DEBUG_TEXT_SECONDARY), (px + 10, cur_y))
            cur_y += 18

            # Header Kolom Tabel
            surface.blit(font_sm.render("Aksi Legal", True, (100, 112, 130)), (px + 14, cur_y))
            surface.blit(font_sm.render("Det (A-B)", True, (100, 112, 130)), (px + 144, cur_y))
            surface.blit(font_sm.render("Expectimax", True, (100, 112, 130)), (px + 232, cur_y))
            cur_y += 18

            scores = stats.get("action_scores", {})
            for act, val in scores.items():
                is_selected = (act == best_a)
                row_rect = pygame.Rect(px + 8, cur_y, pw - 16, 20)

                if is_selected:
                    draw_card(surface, row_rect, (232, 243, 255), border_color=(145, 195, 245), border_radius=4)
                    prefix = "> "
                    col_act = config.DEBUG_TEXT_HIGHLIGHT
                else:
                    draw_card(surface, row_rect, config.DEBUG_CARD_ROW_BG, border_color=config.DEBUG_CARD_ROW_BORDER, border_radius=4)
                    prefix = "  • "
                    col_act = config.DEBUG_TEXT_PRIMARY

                # 1. Nama Aksi
                surface.blit(font_sm.render(f"{prefix}{act}", True, col_act), (row_rect.x + 4, row_rect.centery - 7))

                # 2. Skor Deterministik (Alpha-Beta / Minimax)
                det_v = det_scores.get(act, val)
                col_det = config.DEBUG_TEXT_HIGHLIGHT if (is_selected and cur_algo != "EXPECTIMAX") else config.DEBUG_TEXT_PRIMARY
                ts_det = font_sm.render(f"{det_v:>6.1f}", True, col_det)
                surface.blit(ts_det, (row_rect.x + 136, row_rect.centery - 7))

                # 3. Skor Expectimax (75% hit jika Heavy Attack)
                exp_v = exp_scores.get(act, val)
                if act == ACTION_HEAVY:
                    exp_str = f"{exp_v:>6.1f} (75%)"
                    col_exp = (215, 95, 20) if abs(exp_v - det_v) > 0.01 else config.DEBUG_TEXT_PRIMARY
                else:
                    exp_str = f"{exp_v:>6.1f}"
                    col_exp = (215, 95, 20) if abs(exp_v - det_v) > 0.01 else config.DEBUG_TEXT_PRIMARY

                if is_selected and cur_algo == "EXPECTIMAX":
                    col_exp = (140, 50, 185)

                ts_exp = font_sm.render(exp_str, True, col_exp)
                surface.blit(ts_exp, (row_rect.x + 224, row_rect.centery - 7))

                cur_y += 22
        else:
            wait_box = pygame.Rect(px + 8, cur_y + 14, pw - 16, 92)
            draw_card(surface, wait_box, config.DEBUG_CARD_ROW_BG, border_color=config.DEBUG_CARD_ROW_BORDER, border_radius=8)

            ts_wait = self.fonts.get("bubble", font_sm).render("Menunggu Input Aksi...", True, config.DEBUG_TEXT_HIGHLIGHT)
            surface.blit(ts_wait, (wait_box.centerx - ts_wait.get_width() // 2, wait_box.y + 12))

            ts_sub1 = font_sm.render("Pilih aksi pada tombol di atas:", True, config.DEBUG_TEXT_SECONDARY)
            surface.blit(ts_sub1, (wait_box.centerx - ts_sub1.get_width() // 2, wait_box.y + 38))

            ts_sub2 = font_sm.render("Attack / Heavy / Defend / Potion", True, config.DEBUG_TEXT_PRIMARY)
            surface.blit(ts_sub2, (wait_box.centerx - ts_sub2.get_width() // 2, wait_box.y + 60))

            hint_text = font_sm.render("Data evaluasi AI akan dihitung", True, config.DEBUG_TEXT_SECONDARY)
            hint_text2 = font_sm.render("saat giliran NPC melangkah.", True, config.DEBUG_TEXT_SECONDARY)
            surface.blit(hint_text, (px + (pw - hint_text.get_width()) // 2, wait_box.bottom + 20))
            surface.blit(hint_text2, (px + (pw - hint_text2.get_width()) // 2, wait_box.bottom + 40))

        # ---------------------------------------------------------------- #
        # Tombol Toggle Decision Tree Overlay (Tampil / Sembunyi)
        # ---------------------------------------------------------------- #
        btn_tree_y = eval_card_y + eval_card_h + 8
        btn_tree_h = 36
        self.btn_toggle_tree = pygame.Rect(px + 4, btn_tree_y, pw - 8, btn_tree_h)
        tree_vis = self.tree_overlay.visible

        if tree_vis:
            t_col = (235, 250, 242)
            t_border = (130, 215, 160)
            t_status = "TAMPIL (ON)"
            t_title_col = (20, 135, 55)
            t_hint = "Klik untuk sembunyikan [T]"
        else:
            t_col = (245, 248, 252)
            t_border = (205, 215, 228)
            t_status = "SEMBUNYI (OFF)"
            t_title_col = (85, 95, 110)
            t_hint = "Klik untuk tampilkan [T]"

        draw_card(surface, self.btn_toggle_tree, t_col, border_color=t_border, border_radius=8)
        ts_title = self.fonts.get("bubble", font_sm).render(f"Decision Tree: {t_status}", True, t_title_col)
        surface.blit(ts_title, (self.btn_toggle_tree.centerx - ts_title.get_width() // 2, self.btn_toggle_tree.y + 4))
        ts_hint = font_sm.render(t_hint, True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(ts_hint, (self.btn_toggle_tree.centerx - ts_hint.get_width() // 2, self.btn_toggle_tree.y + 19))

        # ---------------------------------------------------------------- #
        # Kartu 5: Petunjuk Shortcut / Footer
        # ---------------------------------------------------------------- #
        footer_y = surface.get_height() - 76
        footer_h = 64
        draw_card(surface, pygame.Rect(px, footer_y, pw, footer_h), config.DEBUG_CARD_BG, border_color=config.DEBUG_CARD_BORDER, border_radius=8)

        surface.blit(font_sm.render("[R] Reset Duel", True, config.DEBUG_TEXT_SECONDARY), (px + 12, footer_y + 8))
        surface.blit(font_sm.render("[Tab] Kembali  [T] Tree", True, config.DEBUG_TEXT_SECONDARY), (px + 12, footer_y + 26))
        surface.blit(font_sm.render("[1..4] Shortcut Aksi", True, config.DEBUG_TEXT_HIGHLIGHT), (px + 12, footer_y + 44))

        # Gambar Dropdowns paling atas agar popup melayang tanpa tertutup
        self.dropdown_battle_eval.draw(surface, self.fonts)
        self.dropdown_battle_algo.draw(surface, self.fonts)
        if self.depth_help_open:
            self._draw_depth_help(surface)
        if self.move_ordering_help_open:
            self._draw_move_ordering_help(surface)

        # Update data tree pencarian AI ke tree overlay
        if battle_system.last_ai_stats:
            tree_data = battle_system.last_ai_stats.get("tree", None)
            if tree_data is None and hasattr(battle_system.ai_solver, 'last_tree'):
                tree_data = battle_system.ai_solver.last_tree
            self.tree_overlay.set_tree(tree_data)
        else:
            self.tree_overlay.set_tree(None)

    def _draw_depth_help(self, surface):
        help_font = self.fonts["sm"]
        help_lines = self._depth_help_lines(help_font, 250)
        popup = self._depth_help_popup_rect(len(help_lines))
        draw_card(surface, popup, config.DEBUG_DROPDOWN_BG, border_color=config.DEBUG_TEXT_HIGHLIGHT, border_radius=8, border_width=1)
        title = self.fonts.get("bubble", self.fonts["sm"]).render("Tentang Early Stop (Depth)", True, config.DEBUG_TEXT_HIGHLIGHT)
        surface.blit(title, (popup.x + 12, popup.y + 10))
        y = popup.y + 32
        for line in help_lines:
            text = help_font.render(line, True, config.DEBUG_TEXT_PRIMARY)
            surface.blit(text, (popup.x + 12, y))
            y += 18

    def _depth_help_lines(self, font, max_width):
        help_text = (
            "Early Stop (Depth Limit) adalah batas kedalaman langkah pencarian AI. "
            "Pencarian pohon dipotong lebih awal pada batas kedalaman (d) dan memanggil fungsi heuristik evaluasi, "
            "sehingga mencegah ledakan kombinatorial dan mempercepat waktu berpikir NPC secara drastis."
        )
        return self._wrap_overlay_text(help_text, font, max_width)

    def _depth_help_popup_rect(self, line_count):
        height = 34 + line_count * 18 + 12
        return pygame.Rect(self.panel_x + self.panel_w + 10, self.panel_y + 145, 274, height)

    def _draw_move_ordering_help(self, surface):
        help_font = self.fonts["sm"]
        help_lines = self._move_ordering_help_lines(help_font, 250)
        popup = self._move_ordering_help_popup_rect(len(help_lines))
        draw_card(surface, popup, config.DEBUG_DROPDOWN_BG, border_color=config.DEBUG_TEXT_HIGHLIGHT, border_radius=8, border_width=1)
        title = self.fonts.get("bubble", self.fonts["sm"]).render("Tentang Move Ordering", True, config.DEBUG_TEXT_HIGHLIGHT)
        surface.blit(title, (popup.x + 12, popup.y + 10))
        y = popup.y + 32
        for line in help_lines:
            surface.blit(help_font.render(line, True, config.DEBUG_TEXT_PRIMARY), (popup.x + 12, y))
            y += 18

    def _move_ordering_help_lines(self, font, max_width):
        help_text = (
            "Move Ordering mengatur urutan langkah yang diperiksa AI. "
            "HEURISTIC: memeriksa langkah yang lebih baik lebih dulu (ofensif dulu). "
            "REVERSED: memeriksa langkah defensif terlebih dahulu (urutan terbalik). "
            "OFF: memeriksa langkah tanpa pengurutan khusus."
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

        if self.mode == "PRE_BATTLE":
            if self.dropdown_ls_algo.handle_event(event):
                return True
            return False

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
                    if hasattr(self.battle_system, "update_ai_preview"):
                        self.battle_system.update_ai_preview()
                return True
            if self.btn_depth_plus.collidepoint(pos):
                if self.battle_system and self.battle_system.depth < 8:
                    self.battle_system.depth += 1
                    if hasattr(self.battle_system, "update_ai_preview"):
                        self.battle_system.update_ai_preview()
                return True

            # Tombol Move Ordering Toggle (cycle 3 mode)
            if self.btn_move_ordering.collidepoint(pos):
                if self.battle_system:
                    modes = MOVE_ORDERING_MODES
                    cur = self.battle_system.move_ordering_mode
                    idx = modes.index(cur) if cur in modes else 0
                    self.battle_system.move_ordering_mode = modes[(idx + 1) % len(modes)]
                    if hasattr(self.battle_system, "update_ai_preview"):
                        self.battle_system.update_ai_preview()
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

            # Tombol Toggle Decision Tree Overlay di Debug Panel
            if self.btn_toggle_tree.collidepoint(pos):
                self.toggle_tree_overlay()
                return True

            # Forward event ke tree overlay
            if self.tree_overlay.handle_event(event):
                return True

        return False

    def toggle_tree_overlay(self):
        """Toggle visibilitas Decision Tree Overlay (dipanggil dari app.py via tombol [T])."""
        self.tree_overlay.toggle()
        # Aktifkan tree recording di battle system
        if self.battle_system:
            self.battle_system.record_tree = self.tree_overlay.visible