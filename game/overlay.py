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


class Dropdown:
    def __init__(self, rect, labels, on_select, initial_idx=0):
        self.rect = pygame.Rect(rect)
        self.labels = labels
        self.on_select = on_select
        self.selected = initial_idx
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
        bg_surf = pygame.Surface((self.rect.width, self.rect.height), SRCALPHA)
        bg_surf.fill(config.DEBUG_DROPDOWN_BG)
        surface.blit(bg_surf, (self.rect.x, self.rect.y))

        border_color = config.DEBUG_PANEL_BORDER if self.open else (70, 80, 100, 180)
        pygame.draw.rect(surface, border_color, self.rect, 2, border_radius=4)

        label = self.labels[self.selected] if self.selected < len(self.labels) else ""
        if label:
            surf = fonts["sm"].render(label, True, config.DEBUG_TEXT_PRIMARY)
            surface.blit(surf, (self.rect.x + 8, self.rect.y + (self.rect.height - surf.get_height()) // 2))

        # Panah dropdown
        cx = self.rect.right - 14
        cy = self.rect.centery
        arrow_color = config.DEBUG_TEXT_HIGHLIGHT if self.open else config.DEBUG_TEXT_SECONDARY
        if self.open:
            pygame.draw.polygon(surface, arrow_color, [(cx - 5, cy - 2), (cx + 5, cy - 2), (cx, cy + 4)])
        else:
            pygame.draw.polygon(surface, arrow_color, [(cx - 5, cy + 2), (cx + 5, cy + 2), (cx, cy - 4)])

        # Menu pilihan saat terbuka
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
            (px, self.panel_y + 60, pw, 30),
            ["Alpha-Beta Pruning", "Pure Minimax", "Expectimax (Stokastik)"],
            self._on_battle_algo_selected,
            initial_idx=0,
        )

        # Dropdown AI Battle: Fungsi Evaluasi
        self.dropdown_battle_eval = Dropdown(
            (px, self.panel_y + 116, pw, 30),
            ["Balanced (Standar)", "Aggressive (Offensif)", "Defensive (Taktis)"],
            self._on_battle_eval_selected,
            initial_idx=0,
        )

        # Tombol Aksi Player (4 Aksi: Attack, Heavy Attack, Defend, Potion)
        bw = (pw - 8) // 2
        btn_y = self.panel_y + 260
        self.btn_attack = pygame.Rect(px, btn_y, bw, 32)
        self.btn_heavy = pygame.Rect(px + bw + 8, btn_y, bw, 32)
        self.btn_defend = pygame.Rect(px, btn_y + 38, bw, 32)
        self.btn_potion = pygame.Rect(px + bw + 8, btn_y + 38, bw, 32)

        # Tombol Kedalaman AI (Depth - dan +)
        self.btn_depth_minus = pygame.Rect(px + pw - 75, self.panel_y + 152, 32, 26)
        self.btn_depth_plus = pygame.Rect(px + pw - 38, self.panel_y + 152, 32, 26)
        self.btn_depth_help = pygame.Rect(px + 184, self.panel_y + 152, 26, 26)

        # Tombol Move Ordering Toggle
        self.btn_move_ordering = pygame.Rect(px + pw - 60, self.panel_y + 182, 54, 24)
        self.btn_move_ordering_help = pygame.Rect(px + 132, self.panel_y + 182, 26, 24)

    def set_battle_system(self, battle_system):
        self.battle_system = battle_system

    def set_mode(self, mode: str):
        self.mode = mode

    # ------------------------------------------------------------------ #
    # Event Handlers Dropdown
    # ------------------------------------------------------------------ #
    def _on_algorithm_selected(self, index):
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
        selected_label = config.ALGORITHMS[self.dropdown_algo.selected][1]
        steps = max(0, len(self.path_nodes) - 1)
        cur_cost = self.comparison_data.get("cur_cost", 0.0) if self.comparison_data else 0.0

        lines = []
        lines.append(("── BOBOT MEDAN (COST) ────────────────", config.DEBUG_TEXT_SECONDARY))
        lines.append(("  • Jalan Tanah  : Cost 0.5 (Ringan)", config.DEBUG_TEXT_PRIMARY))
        lines.append(("  • Area Rumput  : Cost 1.0 (Normal)", config.DEBUG_TEXT_WARN))
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

        # 1. Background Sidebar Kiri
        sidebar_surf = pygame.Surface((self.panel_w, sidebar_h), SRCALPHA)
        sidebar_surf.fill(config.DEBUG_PANEL_BG)
        pygame.draw.rect(sidebar_surf, config.DEBUG_PANEL_BORDER, (0, 0, self.panel_w, sidebar_h), 1, border_radius=8)
        surface.blit(sidebar_surf, (self.panel_x, sidebar_y))

        if self.mode == "EXPLORATION":
            self._draw_exploration_ui(surface)
        else:
            self._draw_battle_ui(surface)

        self._draw_cost_toggle(surface)

    def _draw_cost_toggle(self, surface):
        fill = (70, 175, 95, 210) if self.show_costs else (210, 214, 218, 210)
        toggle_surf = pygame.Surface(self.cost_toggle_rect.size, SRCALPHA)
        pygame.draw.rect(toggle_surf, fill, toggle_surf.get_rect(), border_radius=4)
        pygame.draw.rect(toggle_surf, config.DEBUG_PANEL_BORDER, toggle_surf.get_rect(), 1, border_radius=4)
        surface.blit(toggle_surf, self.cost_toggle_rect.topleft)
        label = "Cost: ON" if self.show_costs else "Cost: OFF"
        text_color = (255, 255, 255) if self.show_costs else config.DEBUG_TEXT_PRIMARY
        text = self.fonts["sm"].render(label, True, text_color)
        surface.blit(text, (self.cost_toggle_rect.centerx - text.get_width() // 2, self.cost_toggle_rect.centery - text.get_height() // 2))

    def _draw_exploration_ui(self, surface):
        title_surf = self.fonts.get("title", self.fonts["sm"]).render("AI PATHFINDING", True, config.DEBUG_TEXT_HIGHLIGHT)
        surface.blit(title_surf, (self.panel_x + 14, self.panel_y + 12))

        sub_surf = self.fonts["sm"].render("Pilih Algoritma AI:", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(sub_surf, (self.panel_x + 14, self.panel_y + 38))

        if self.stats_surface:
            surface.blit(self.stats_surface, (self.stats_rect.x + 12, self.stats_rect.y))

        self.dropdown_algo.draw(surface, self.fonts)

    def _draw_battle_ui(self, surface):
        battle_system = self.battle_system
        if battle_system is None:
            return

        px = self.panel_x + 14
        pw = self.panel_w - 28

        # Header Duel
        title_surf = self.fonts.get("title", self.fonts["sm"]).render("⚔ DUEL MINIMAX AI", True, (255, 120, 80))
        surface.blit(title_surf, (px, self.panel_y + 12))

        sub_algo = self.fonts["sm"].render("Algoritma AI NPC:", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(sub_algo, (px, self.panel_y + 40))

        sub_eval = self.fonts["sm"].render("Fungsi Evaluasi:", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(sub_eval, (px, self.panel_y + 96))

        # Kontrol Kedalaman (Depth)
        depth_y = self.panel_y + 154
        depth_label = self.fonts["sm"].render(f"Kedalaman (Depth): {battle_system.depth}", True, config.DEBUG_TEXT_PRIMARY)
        surface.blit(depth_label, (px, depth_y + 4))

        # Tombol - & +
        for btn, text, fill in [
            (self.btn_depth_minus, "-", (190, 70, 70)),
            (self.btn_depth_plus, "+", (55, 155, 80)),
        ]:
            pygame.draw.rect(surface, fill, btn, border_radius=4)
            pygame.draw.rect(surface, config.DEBUG_PANEL_BORDER, btn, 1, border_radius=4)
            ts = self.fonts.get("bubble", self.fonts["sm"]).render(text, True, config.DEBUG_TEXT_PRIMARY)
            surface.blit(ts, (btn.centerx - ts.get_width() // 2, btn.centery - ts.get_height() // 2))

        pygame.draw.rect(surface, (70, 105, 155), self.btn_depth_help, border_radius=4)
        pygame.draw.rect(surface, config.DEBUG_PANEL_BORDER, self.btn_depth_help, 1, border_radius=4)
        help_text = self.fonts.get("bubble", self.fonts["sm"]).render("?", True, (255, 255, 255))
        surface.blit(help_text, (self.btn_depth_help.centerx - help_text.get_width() // 2, self.btn_depth_help.centery - help_text.get_height() // 2))

        # Move Ordering Toggle
        mo_y = self.panel_y + 184
        mo_on = battle_system.use_move_ordering
        mo_label = self.fonts["sm"].render("Move Ordering:", True, config.DEBUG_TEXT_PRIMARY)
        surface.blit(mo_label, (px, mo_y + 4))
        pygame.draw.rect(surface, (70, 105, 155), self.btn_move_ordering_help, border_radius=4)
        pygame.draw.rect(surface, config.DEBUG_PANEL_BORDER, self.btn_move_ordering_help, 1, border_radius=4)
        help_text = self.fonts.get("bubble", self.fonts["sm"]).render("?", True, (255, 255, 255))
        surface.blit(help_text, (self.btn_move_ordering_help.centerx - help_text.get_width() // 2, self.btn_move_ordering_help.centery - help_text.get_height() // 2))

        mo_color = (40, 150, 70) if mo_on else (90, 40, 40)
        pygame.draw.rect(surface, mo_color, self.btn_move_ordering, border_radius=4)
        pygame.draw.rect(surface, config.DEBUG_PANEL_BORDER, self.btn_move_ordering, 1, border_radius=4)
        mo_text = "ON" if mo_on else "OFF"
        ts_mo = self.fonts["sm"].render(mo_text, True, (255, 255, 255))
        surface.blit(ts_mo, (self.btn_move_ordering.centerx - ts_mo.get_width() // 2, self.btn_move_ordering.centery - ts_mo.get_height() // 2))

        # Pembatas Garis
        sep_y = self.panel_y + 215
        pygame.draw.line(surface, (60, 70, 95), (px, sep_y), (px + pw, sep_y), 1)

        # Status Giliran
        state = battle_system.state
        if state:
            turn_text = "Giliran NPC (AI Berpikir...)" if state.is_npc_turn else "Giliran Anda (Pilih Aksi)"
            turn_color = (255, 180, 80) if state.is_npc_turn else config.DEBUG_TEXT_HIGHLIGHT
            if battle_system.is_finished:
                turn_text = f"Pertarungan Selesai: {battle_system.winner} MENANG!"
                turn_color = (18, 112, 48)

            turn_font = self.fonts.get("bubble", self.fonts["sm"])
            ts_turn = turn_font.render(turn_text, True, turn_color)
            surface.blit(ts_turn, (px, sep_y + 8))

            # Tombol-tombol Aksi Pemain
            can_act = (not state.is_npc_turn) and (not battle_system.is_finished)
            heavy_ready = state.player_heavy_cd <= 0
            heavy_label = "Heavy (30)" if heavy_ready else f"Heavy (CD:{state.player_heavy_cd})"
            actions_info = [
                (self.btn_attack, "Attack (18)", (180, 50, 50), True),
                (self.btn_heavy, heavy_label, (220, 90, 30), heavy_ready),
                (self.btn_defend, "Defend (-65%)", (50, 100, 180), True),
                (self.btn_potion, f"Potion ({state.player_potions})", (40, 150, 90), state.player_potions > 0 and state.player_hp < 100),
            ]

            for btn_rect, btn_title, base_col, is_enabled in actions_info:
                fill_col = base_col if (can_act and is_enabled) else (40, 44, 52)
                text_col = (255, 255, 255) if (can_act and is_enabled) else (120, 125, 135)
                pygame.draw.rect(surface, fill_col, btn_rect, border_radius=5)
                pygame.draw.rect(surface, config.DEBUG_PANEL_BORDER, btn_rect, 1, border_radius=5)
                ts = self.fonts["sm"].render(btn_title, True, text_col)
                surface.blit(ts, (btn_rect.centerx - ts.get_width() // 2, btn_rect.centery - ts.get_height() // 2))

        # Metrik Live AI (Node Count, Execution Time, Skor Tiap Aksi)
        metrics_y = self.panel_y + 340
        pygame.draw.line(surface, (60, 70, 95), (px, metrics_y), (px + pw, metrics_y), 1)

        stats = battle_system.last_ai_stats
        ts_mtitle = self.fonts["sm"].render("── EVALUASI AKSI & NODE COUNT ──", True, config.DEBUG_TEXT_SECONDARY)
        surface.blit(ts_mtitle, (px, metrics_y + 6))

        cur_y = metrics_y + 26
        if stats:
            nc = stats.get("node_count", 0)
            pc = stats.get("pruned_count", 0)
            t_ms = stats.get("time_ms", 0.0)
            best_a = stats.get("best_action", "—")
            best_s = stats.get("best_score", 0.0)

            surface.blit(self.fonts["sm"].render(f"Nodes Diekspansi : {nc}", True, config.DEBUG_TEXT_PRIMARY), (px, cur_y))
            cur_y += 18
            pruned_font = self.fonts.get("bubble", self.fonts["sm"])
            surface.blit(pruned_font.render(f"Cabang Dipangkas : {pc}", True, (18, 112, 48)), (px, cur_y))
            cur_y += 18
            surface.blit(self.fonts["sm"].render(f"Waktu Berpikir   : {t_ms:.2f} ms", True, config.DEBUG_TEXT_PRIMARY), (px, cur_y))
            cur_y += 18
            best_text = f"Pilihan Terbaik  : {best_a} (Skor: {best_s})"
            best_lines = self._wrap_overlay_text(best_text, self.fonts["sm"], pw)
            for best_line in best_lines:
                surface.blit(self.fonts["sm"].render(best_line, True, config.DEBUG_TEXT_HIGHLIGHT), (px, cur_y))
                cur_y += 16
            cur_y += 8

            # Tabel Skor Pertimbangan Tiap Aksi di Root
            surface.blit(self.fonts["sm"].render("Pertimbangan Nilai Aksi (Root):", True, config.DEBUG_TEXT_SECONDARY), (px, cur_y))
            cur_y += 18
            scores = stats.get("action_scores", {})
            for act, val in scores.items():
                is_selected = (act == best_a)
                prefix = "▶ " if is_selected else "  • "
                col = config.DEBUG_TEXT_HIGHLIGHT if is_selected else config.DEBUG_TEXT_PRIMARY
                surface.blit(self.fonts["sm"].render(f"{prefix}{act:<12}: {val:>7.1f}", True, col), (px, cur_y))
                cur_y += 16
        else:
            surface.blit(self.fonts["sm"].render("Menunggu kalkulasi pertama AI...", True, config.DEBUG_TEXT_SECONDARY), (px, cur_y))
            cur_y += 40

        # Shortcut / Petunjuk di bagian bawah
        bottom_y = surface.get_height() - 90
        pygame.draw.line(surface, (60, 70, 95), (px, bottom_y), (px + pw, bottom_y), 1)
        surface.blit(self.fonts["sm"].render("[R] Reset Duel", True, config.DEBUG_TEXT_SECONDARY), (px, bottom_y + 8))
        surface.blit(self.fonts["sm"].render("[Tab] Kembali ke Peta", True, config.DEBUG_TEXT_SECONDARY), (px, bottom_y + 25))
        surface.blit(self.fonts["sm"].render("[1..4] Shortcut Aksi", True, config.DEBUG_TEXT_HIGHLIGHT), (px, bottom_y + 42))

        # Gambar Dropdowns paling atas agar popup melayang
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
        popup_surface = pygame.Surface(popup.size, SRCALPHA)
        popup_surface.fill((250, 250, 247, 242))
        pygame.draw.rect(popup_surface, config.DEBUG_PANEL_BORDER, popup_surface.get_rect(), 1, border_radius=6)
        title = self.fonts.get("bubble", self.fonts["sm"]).render("Tentang Kedalaman AI", True, config.DEBUG_TEXT_HIGHLIGHT)
        popup_surface.blit(title, (10, 8))
        y = 31
        for line in help_lines:
            text = help_font.render(line, True, config.DEBUG_TEXT_PRIMARY)
            popup_surface.blit(text, (10, y))
            y += 17
        surface.blit(popup_surface, popup.topleft)

    def _depth_help_lines(self, font, max_width):
        help_text = (
            "Depth adalah jumlah langkah ke depan yang dianalisis AI sebelum memilih aksi. "
            "Depth + membuat analisis lebih jauh dan detail, tetapi waktu berpikir bisa lebih lama. "
            "Depth - membuat analisis lebih cepat dan ringan."
        )
        return self._wrap_overlay_text(help_text, font, max_width)

    def _depth_help_popup_rect(self, line_count):
        height = 31 + line_count * 17 + 10
        return pygame.Rect(self.panel_x + self.panel_w + 10, self.panel_y + 145, 270, height)

    def _draw_move_ordering_help(self, surface):
        help_font = self.fonts["sm"]
        help_lines = self._move_ordering_help_lines(help_font, 250)
        popup = self._move_ordering_help_popup_rect(len(help_lines))
        popup_surface = pygame.Surface(popup.size, SRCALPHA)
        popup_surface.fill((250, 250, 247, 242))
        pygame.draw.rect(popup_surface, config.DEBUG_PANEL_BORDER, popup_surface.get_rect(), 1, border_radius=6)
        title = self.fonts.get("bubble", self.fonts["sm"]).render("Tentang Move Ordering", True, config.DEBUG_TEXT_HIGHLIGHT)
        popup_surface.blit(title, (10, 8))
        y = 31
        for line in help_lines:
            popup_surface.blit(help_font.render(line, True, config.DEBUG_TEXT_PRIMARY), (10, y))
            y += 17
        surface.blit(popup_surface, popup.topleft)

    def _move_ordering_help_lines(self, font, max_width):
        help_text = (
            "Move Ordering mengatur urutan langkah yang diperiksa AI. "
            "ON memeriksa langkah yang dianggap lebih baik lebih dulu, sehingga AI bisa memilih lebih cepat. "
            "OFF memeriksa langkah tanpa pengurutan khusus dan dapat membutuhkan lebih banyak waktu."
        )
        return self._wrap_overlay_text(help_text, font, max_width)

    def _move_ordering_help_popup_rect(self, line_count):
        height = 31 + line_count * 17 + 10
        return pygame.Rect(self.panel_x + self.panel_w + 10, self.panel_y + 175, 270, height)

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