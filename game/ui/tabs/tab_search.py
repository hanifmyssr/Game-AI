"""Tab 1: Materi 01-03: Pathfinding & Search (Cozy Adventurer Journal Theme).

Menyajikan metrik komparasi algoritma pencarian rute (A*, UCS, Greedy),
visualisasi node diekspansi, dan bobot medan dengan tipografi jelas.
"""

from typing import Dict, Any, Optional
import pygame
from ...core import config
from ..components import draw_card, draw_badge_pill, draw_metric_tile, UIDropdown, UIButton

MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1025)


class TabSearch:
    """Tab 1: Pathfinding & Search Control."""

    def __init__(self, rect: pygame.Rect, fonts: Dict[str, pygame.font.Font], app_ref: Any):
        self.rect = pygame.Rect(rect)
        self.fonts = fonts
        self.app = app_ref

        options = [(k, lbl) for (k, lbl) in config.ALGORITHMS]
        dropdown_rect = pygame.Rect(self.rect.x + 12, self.rect.y + 60, self.rect.width - 24, 34)
        self.dropdown_algo = UIDropdown(
            dropdown_rect,
            options,
            on_select=self._on_algorithm_selected,
            initial_idx=1,
            font=fonts.get("sm", pygame.font.Font(None, 16)),
        )

        btn_w = self.rect.width - 24
        self.show_path_line = True
        self.btn_toggle_path = UIButton(
            pygame.Rect(self.rect.x + 12, self.rect.y + 540, btn_w, 38),
            "Toggle Jalur di Peta: AKTIF",
            fonts.get("sm", pygame.font.Font(None, 16)),
            on_click=self._on_toggle_path_vis,
            bg_color=(242, 235, 222),
            hover_color=(255, 252, 245),
            active_color=(230, 220, 205),
            border_color=config.COLOR_CARD_BORDER,
            icon="👁",
        )

    def resize(self, rect: pygame.Rect) -> None:
        self.rect = pygame.Rect(rect)

    def _on_algorithm_selected(self, index: int, key: str) -> None:
        if hasattr(self.app, "events") and self.app.events:
            self.app.events.emit_algorithm_changed(key)
        if hasattr(self.app, "npc") and hasattr(self.app, "player"):
            self.app.npc.set_algorithm(key)
            self.app.npc.find_path(self.app.player.grid)

    def _on_toggle_path_vis(self) -> None:
        self.show_path_line = not self.show_path_line
        self.btn_toggle_path.text = f"Toggle Jalur di Peta: {'AKTIF' if self.show_path_line else 'OFF'}"
        if hasattr(self.app, "overlay"):
            setattr(self.app.overlay, "show_path_visualization", self.show_path_line)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.dropdown_algo.handle_event(event):
            return True
        if self.btn_toggle_path.handle_event(event):
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

        # 1. KARTU PILIH ALGORITMA
        card_algo_h = 82
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_algo_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)
        lbl_algo = font_sm.render("Pilih Algoritma AI:", True, config.COLOR_TEXT_PRIMARY)
        surface.blit(lbl_algo, (cx + 12, cy + 8))

        self.dropdown_algo.rect = pygame.Rect(cx + 10, cy + 34, card_w - 20, 36)
        self.dropdown_algo.draw(surface)

        # 2. KARTU METRIK JALUR (GRID 2x2)
        cy += card_algo_h + 12
        card_m_h = 132
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_m_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        m_title = font_tiny.render("── METRIK PENCARIAN REAL-TIME ──", True, config.COLOR_TEXT_SECONDARY)
        surface.blit(m_title, (cx + (card_w - m_title.get_width()) // 2, cy + 6))

        overlay = getattr(self.app, "overlay", None)
        path_nodes = getattr(overlay, "path_nodes", [])
        steps = max(0, len(path_nodes) - 1)
        expanded_count = getattr(overlay, "last_expanded_count", 0)
        time_ms = getattr(overlay, "last_time_ms", 0.0)
        comp_data = getattr(overlay, "comparison_data", {})
        cur_cost = comp_data.get("cur_cost", 0.0) if comp_data else 0.0

        tile_w = (card_w - 28) // 2
        tile_h = 44
        ty1 = cy + 28
        ty2 = ty1 + tile_h + 6

        draw_metric_tile(surface, pygame.Rect(cx + 10, ty1, tile_w, tile_h),
                         "NODE DIEKSPANSI", f"{expanded_count} node",
                         val_color=config.COLOR_ACCENT_GOLD,
                         font_lbl=font_tiny, font_val=font_sm)

        draw_metric_tile(surface, pygame.Rect(cx + 18 + tile_w, ty1, tile_w, tile_h),
                         "PANJANG JALUR", f"{steps} langkah",
                         val_color=config.COLOR_TEXT_PRIMARY,
                         font_lbl=font_tiny, font_val=font_sm)

        draw_metric_tile(surface, pygame.Rect(cx + 10, ty2, tile_w, tile_h),
                         "TOTAL BOBOT", f"{cur_cost:.1f}",
                         val_color=config.COLOR_ACCENT_BLUE,
                         font_lbl=font_tiny, font_val=font_sm)

        draw_metric_tile(surface, pygame.Rect(cx + 18 + tile_w, ty2, tile_w, tile_h),
                         "WAKTU SOLVER", f"{time_ms:.3f} ms",
                         val_color=config.COLOR_STATUS_SUCCESS,
                         font_lbl=font_tiny, font_val=font_sm)

        # 3. KARTU BOBOT MEDAN (TERRAIN COST)
        cy += card_m_h + 12
        card_cost_h = 84
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_cost_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        c_title = font_tiny.render("── BOBOT MEDAN (TERRAIN COST) ──", True, config.COLOR_TEXT_SECONDARY)
        surface.blit(c_title, (cx + (card_w - c_title.get_width()) // 2, cy + 6))

        draw_metric_tile(surface, pygame.Rect(cx + 10, cy + 28, tile_w, tile_h),
                         "JALAN TANAH", "Cost 1.0 (Cepat)",
                         val_color=config.COLOR_STATUS_SUCCESS,
                         font_lbl=font_tiny, font_val=font_tiny)

        draw_metric_tile(surface, pygame.Rect(cx + 18 + tile_w, cy + 28, tile_w, tile_h),
                         "RUMPUT LIAR", "Cost 2.0 (Normal)",
                         val_color=config.COLOR_ACCENT_GOLD,
                         font_lbl=font_tiny, font_val=font_tiny)

        # 4. KARTU PERBANDINGAN KOMPUTASI (UCS vs A*)
        cy += card_cost_h + 12
        card_comp_h = 145
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_comp_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        cp_title = font_tiny.render("── KOMPARASI HEURISTIK (A* vs UCS) ──", True, config.COLOR_TEXT_SECONDARY)
        surface.blit(cp_title, (cx + (card_w - cp_title.get_width()) // 2, cy + 6))

        ucs_exp = comp_data.get("ucs_expanded", 0) if comp_data else 0
        ucs_c = comp_data.get("ucs_cost", 0.0) if comp_data else 0.0

        # Row 1: UCS
        r1_rect = pygame.Rect(cx + 10, cy + 30, card_w - 20, 28)
        draw_card(surface, r1_rect, (250, 246, 238), border_color=(226, 216, 202), border_radius=5)
        u_txt = font_tiny.render("• UCS (h=0)", True, (190, 110, 15))
        u_val = font_tiny.render(f"{ucs_exp} node │ Cost {ucs_c:.1f}", True, config.COLOR_TEXT_PRIMARY)
        surface.blit(u_txt, (r1_rect.x + 8, r1_rect.y + 6))
        surface.blit(u_val, (r1_rect.right - u_val.get_width() - 8, r1_rect.y + 6))

        # Row 2: A* Terpilih
        r2_rect = pygame.Rect(cx + 10, cy + 64, card_w - 20, 28)
        draw_card(surface, r2_rect, (250, 246, 238), border_color=(226, 216, 202), border_radius=5)
        a_txt = font_tiny.render("• A* Terpilih", True, config.COLOR_ACCENT_BLUE)
        a_val = font_tiny.render(f"{expanded_count} node │ Cost {cur_cost:.1f}", True, config.COLOR_TEXT_PRIMARY)
        surface.blit(a_txt, (r2_rect.x + 8, r2_rect.y + 6))
        surface.blit(a_val, (r2_rect.right - a_val.get_width() - 8, r2_rect.y + 6))

        if ucs_exp > 0 and expanded_count > 0:
            saving = max(0, int(round((1.0 - (expanded_count / float(ucs_exp))) * 100)))
            eff_str = f"⚡ Heuristik memangkas {saving}% ekspansi simpul!"
            eff_color = config.COLOR_STATUS_SUCCESS
        else:
            eff_str = "Menunggu kalkulasi kedua rute..."
            eff_color = config.COLOR_TEXT_MUTED

        eff_surf = font_tiny.render(eff_str, True, eff_color)
        surface.blit(eff_surf, (cx + (card_w - eff_surf.get_width()) // 2, cy + 106))

        cy += card_comp_h + 12
        self.btn_toggle_path.rect = pygame.Rect(cx, cy, card_w, 38)
        self.btn_toggle_path.draw(surface)

    def draw_popups(self, surface: pygame.Surface) -> None:
        self.dropdown_algo.draw_menu(surface)
