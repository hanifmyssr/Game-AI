"""Tab 2: Materi 04: Adversarial Search (Cozy Adventurer Journal Theme).

Menyediakan pengaturan kedalaman pencarian, pemangkasan cabang (Alpha-Beta Pruning),
fungsi evaluasi heuristik, serta pemicu visualisasi pohon keputusan universal.
"""

from typing import Dict, Any, Optional
import pygame
from ...core import config
from ...ai.battle_ai import (
    MOVE_ORDERING_MODES,
    MOVE_ORDERING_OFF,
    MOVE_ORDERING_HEURISTIC,
    MOVE_ORDERING_REVERSED,
)
from ..components import draw_card, draw_badge_pill, draw_metric_tile, UIDropdown, UIButton

MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1025)

BATTLE_ALGORITHMS = [
    ("ALPHA_BETA", "Alpha-Beta Pruning"),
    ("MINIMAX", "Pure Minimax"),
    ("EXPECTIMAX", "Expectimax (Stokastik)"),
]

EVALUATION_MODES = [
    ("BALANCED", "Balanced (Standar)"),
    ("AGGRESSIVE", "Aggressive (Offensif)"),
    ("DEFENSIVE", "Defensive (Taktis)"),
]


class TabMinimax:
    """Tab 2: Adversarial Search Control & Metrics."""

    def __init__(self, rect: pygame.Rect, fonts: Dict[str, pygame.font.Font], app_ref: Any):
        self.rect = pygame.Rect(rect)
        self.fonts = fonts
        self.app = app_ref

        algo_options = [(name, label) for (name, label) in BATTLE_ALGORITHMS]
        eval_options = [(name, label) for (name, label) in EVALUATION_MODES]

        self.dropdown_algo = UIDropdown(
            pygame.Rect(self.rect.x + 12, self.rect.y + 60, self.rect.width - 24, 32),
            algo_options,
            on_select=self._on_algo_selected,
            initial_idx=0,
            font=fonts.get("sm", pygame.font.Font(None, 16)),
        )

        self.dropdown_eval = UIDropdown(
            pygame.Rect(self.rect.x + 12, self.rect.y + 118, self.rect.width - 24, 32),
            eval_options,
            on_select=self._on_eval_selected,
            initial_idx=0,
            font=fonts.get("sm", pygame.font.Font(None, 16)),
        )

        btn_w = self.rect.width - 24
        self.btn_tree_modal = UIButton(
            pygame.Rect(self.rect.x + 12, self.rect.y + 520, btn_w, 38),
            "Buka Pohon Minimax [T]",
            fonts.get("sm", pygame.font.Font(None, 16)),
            on_click=self._on_open_tree,
            bg_color=(242, 235, 222),
            hover_color=(255, 252, 245),
            active_color=(230, 220, 205),
            border_color=config.COLOR_CARD_BORDER,
            icon="🌳",
        )

    def resize(self, rect: pygame.Rect) -> None:
        self.rect = pygame.Rect(rect)

        self.btn_depth_minus = pygame.Rect(0, 0, 28, 26)
        self.btn_depth_plus = pygame.Rect(0, 0, 28, 26)
        self.btn_move_ordering = pygame.Rect(0, 0, 95, 26)

    @property
    def battle_system(self):
        return getattr(self.app, "battle_system", None)

    def _on_algo_selected(self, index: int, key: str) -> None:
        bs = self.battle_system
        if bs:
            bs.algorithm = key
            if hasattr(bs, "update_ai_preview"):
                bs.update_ai_preview()

    def _on_eval_selected(self, index: int, key: str) -> None:
        bs = self.battle_system
        if bs:
            bs.eval_mode = key
            if hasattr(bs, "update_ai_preview"):
                bs.update_ai_preview()

    def _on_open_tree(self) -> None:
        if hasattr(self.app, "overlay") and hasattr(self.app.overlay, "toggle_tree_overlay"):
            self.app.overlay.toggle_tree_overlay()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.dropdown_algo.handle_event(event):
            return True
        if self.dropdown_eval.handle_event(event):
            return True
        if self.btn_tree_modal.handle_event(event):
            return True

        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            bs = self.battle_system
            if not bs:
                return False

            if self.btn_depth_minus.collidepoint(event.pos):
                bs.depth = max(1, bs.depth - 1)
                return True
            if self.btn_depth_plus.collidepoint(event.pos):
                bs.depth = min(8, bs.depth + 1)
                return True
            if self.btn_move_ordering.collidepoint(event.pos):
                cur_idx = MOVE_ORDERING_MODES.index(bs.move_ordering_mode) if bs.move_ordering_mode in MOVE_ORDERING_MODES else 0
                next_mode = MOVE_ORDERING_MODES[(cur_idx + 1) % len(MOVE_ORDERING_MODES)]
                bs.move_ordering_mode = next_mode
                return True

        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        font_tiny = self.fonts.get("tiny", pygame.font.Font(None, 13))
        font_sm = self.fonts.get("sm", pygame.font.Font(None, 16))
        font_title = self.fonts.get("title", pygame.font.Font(None, 19))

        cx = self.rect.x + 12
        cy = self.rect.y + 12
        card_w = self.rect.width - 24
        bs = self.battle_system

        # 1. KARTU KONFIGURASI ALGORITMA MINIMAX
        card_cfg_h = 205
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_cfg_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        lbl_algo = font_tiny.render("Algoritma AI Duel:", True, config.COLOR_TEXT_SECONDARY)
        surface.blit(lbl_algo, (cx + 12, cy + 8))
        self.dropdown_algo.rect = pygame.Rect(cx + 10, cy + 26, card_w - 20, 32)
        self.dropdown_algo.draw(surface)

        lbl_eval = font_tiny.render("Fungsi Evaluasi State:", True, config.COLOR_TEXT_SECONDARY)
        surface.blit(lbl_eval, (cx + 12, cy + 64))
        self.dropdown_eval.rect = pygame.Rect(cx + 10, cy + 82, card_w - 20, 32)
        self.dropdown_eval.draw(surface)

        # Baris Depth Control
        depth_y = cy + 122
        cur_depth = bs.depth if bs else 4
        d_row = pygame.Rect(cx + 10, depth_y, card_w - 20, 34)
        draw_card(surface, d_row, (250, 246, 238), border_color=(226, 216, 202), border_radius=5)
        d_lbl = font_tiny.render(f"Kedalaman (Depth): {cur_depth}", True, config.COLOR_TEXT_PRIMARY)
        surface.blit(d_lbl, (d_row.x + 8, d_row.y + 8))

        self.btn_depth_minus = pygame.Rect(d_row.right - 68, depth_y + 4, 28, 26)
        self.btn_depth_plus = pygame.Rect(d_row.right - 34, depth_y + 4, 28, 26)
        draw_card(surface, self.btn_depth_minus, (255, 255, 255), border_color=config.COLOR_CARD_BORDER, border_radius=4)
        draw_card(surface, self.btn_depth_plus, (255, 255, 255), border_color=config.COLOR_CARD_BORDER, border_radius=4)
        m_txt = font_sm.render("-", True, config.COLOR_STATUS_DANGER)
        p_txt = font_sm.render("+", True, config.COLOR_STATUS_SUCCESS)
        surface.blit(m_txt, (self.btn_depth_minus.centerx - m_txt.get_width() // 2, self.btn_depth_minus.centery - m_txt.get_height() // 2))
        surface.blit(p_txt, (self.btn_depth_plus.centerx - p_txt.get_width() // 2, self.btn_depth_plus.centery - p_txt.get_height() // 2))

        # Baris Move Ordering
        mo_y = cy + 162
        mo_mode = bs.move_ordering_mode if bs else MOVE_ORDERING_OFF
        mo_row = pygame.Rect(cx + 10, mo_y, card_w - 20, 34)
        draw_card(surface, mo_row, (250, 246, 238), border_color=(226, 216, 202), border_radius=5)
        mo_lbl = font_tiny.render("Move Ordering:", True, config.COLOR_TEXT_PRIMARY)
        surface.blit(mo_lbl, (mo_row.x + 8, mo_row.y + 8))

        self.btn_move_ordering = pygame.Rect(mo_row.right - 104, mo_y + 4, 98, 26)
        if mo_mode == MOVE_ORDERING_HEURISTIC:
            mo_bg = (235, 248, 238)
            mo_txt_col = config.COLOR_STATUS_SUCCESS
            mo_str = "HEURISTIC"
        elif mo_mode == MOVE_ORDERING_REVERSED:
            mo_bg = (255, 245, 232)
            mo_txt_col = config.COLOR_ACCENT_GOLD
            mo_str = "REVERSED"
        else:
            mo_bg = (244, 240, 234)
            mo_txt_col = config.COLOR_TEXT_MUTED
            mo_str = "OFF"

        draw_card(surface, self.btn_move_ordering, mo_bg, border_color=config.COLOR_CARD_BORDER, border_radius=4)
        mo_txt = font_tiny.render(mo_str, True, mo_txt_col)
        surface.blit(mo_txt, (self.btn_move_ordering.centerx - mo_txt.get_width() // 2, self.btn_move_ordering.centery - mo_txt.get_height() // 2))

        # 2. KARTU METRIK EVALUASI DUEL
        cy += card_cfg_h + 12
        card_m_h = 132
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_m_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        m_title = font_tiny.render("── STATISTIK KOMPUTASI DUEL ──", True, config.COLOR_TEXT_SECONDARY)
        surface.blit(m_title, (cx + (card_w - m_title.get_width()) // 2, cy + 6))

        stats = getattr(bs, "last_ai_stats", {}) or {}
        eval_nodes = getattr(bs, "last_nodes_evaluated", 0) or stats.get("node_count", 0)
        pruned = getattr(bs, "last_branches_pruned", 0) or stats.get("pruned_count", 0)
        time_ms = getattr(bs, "last_time_ms", 0.0) or stats.get("time_ms", 0.0)

        tile_w = (card_w - 28) // 2
        tile_h = 44
        ty1 = cy + 28
        ty2 = ty1 + tile_h + 6

        draw_metric_tile(surface, pygame.Rect(cx + 10, ty1, tile_w, tile_h),
                         "NODE DIEVALUASI", f"{eval_nodes} node",
                         val_color=config.COLOR_ACCENT_GOLD,
                         font_lbl=font_tiny, font_val=font_sm)

        draw_metric_tile(surface, pygame.Rect(cx + 18 + tile_w, ty1, tile_w, tile_h),
                         "CABANG DIPANGKAS", f"{pruned} branch",
                         val_color=config.COLOR_STATUS_DANGER,
                         font_lbl=font_tiny, font_val=font_sm)

        draw_metric_tile(surface, pygame.Rect(cx + 10, ty2, tile_w, tile_h),
                         "WAKTU BERPIKIR", f"{time_ms:.2f} ms",
                         val_color=config.COLOR_STATUS_SUCCESS,
                         font_lbl=font_tiny, font_val=font_sm)

        total_branch = eval_nodes + pruned
        eff_prune = (pruned / float(total_branch) * 100) if total_branch > 0 else 0.0
        draw_metric_tile(surface, pygame.Rect(cx + 18 + tile_w, ty2, tile_w, tile_h),
                         "EFISIENSI PRUNE", f"{eff_prune:.0f}%",
                         val_color=config.COLOR_ACCENT_BLUE,
                         font_lbl=font_tiny, font_val=font_sm)

        # 3. KARTU PREVIEW SKOR AKSI
        cy += card_m_h + 12
        action_scores = getattr(bs, "last_action_scores", {}) or stats.get("action_scores", {})
        score_count = max(1, min(4, len(action_scores)))
        card_act_h = max(100, 36 + score_count * 22)
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_act_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        ac_title = font_tiny.render("── SKOR AKSI TERAKHIR AI ──", True, config.COLOR_TEXT_SECONDARY)
        surface.blit(ac_title, (cx + (card_w - ac_title.get_width()) // 2, cy + 6))

        action_names_map = {
            "ATTACK": "Serang Biasa",
            "HEAVY": "Serangan Kuat",
            "HEAVY_ATTACK": "Serangan Kuat",
            "DEFEND": "Bertahan",
            "POTION": "Minum Ramuan",
        }

        if action_scores:
            ay = cy + 28
            best_act = stats.get("best_action", None)
            for act_name, score in list(action_scores.items())[:4]:
                readable_name = action_names_map.get(act_name, act_name)
                is_best = (act_name == best_act)
                bullet = "[*]" if is_best else " • "
                score_str = f"{score:+.1f}" if isinstance(score, (int, float)) else str(score)
                txt_col = config.COLOR_STATUS_SUCCESS if is_best else config.COLOR_TEXT_PRIMARY
                sc_col = config.COLOR_ACCENT_GOLD if is_best else config.COLOR_TEXT_SECONDARY
                act_lbl = font_tiny.render(f"{bullet} {readable_name}", True, txt_col)
                sc_lbl = font_tiny.render(score_str, True, sc_col)
                surface.blit(act_lbl, (cx + 14, ay))
                surface.blit(sc_lbl, (cx + card_w - sc_lbl.get_width() - 14, ay))
                ay += 20
        else:
            no_act = font_tiny.render("Duel belum dimulai / kalkulasi...", True, config.COLOR_TEXT_MUTED)
            surface.blit(no_act, (cx + 14, cy + 42))

        cy += card_act_h + 12
        self.btn_tree_modal.rect = pygame.Rect(cx, cy, card_w, 38)
        self.btn_tree_modal.draw(surface)

    def draw_popups(self, surface: pygame.Surface) -> None:
        self.dropdown_algo.draw_menu(surface)
        self.dropdown_eval.draw_menu(surface)
