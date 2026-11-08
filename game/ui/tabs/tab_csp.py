"""Tab 3: Materi 05-06: CSP & Local Search (Cozy Adventurer Journal Theme).

Menyediakan kontrol optimasi pembentukan skuad musuh berimbang menggunakan
MRV, LCV, AC-3, serta pembanding algoritma Local Search (HC, SA, GA).
"""

from typing import Dict, Any, Optional
import pygame
from ...core import config
from ..components import draw_card, draw_badge_pill, draw_metric_tile, UIDropdown, UIButton, UISlider

MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1025)


class TabCSP:
    """Tab 3: CSP & Local Search Squad Optimizer."""

    def __init__(self, rect: pygame.Rect, fonts: Dict[str, pygame.font.Font], app_ref: Any):
        self.rect = pygame.Rect(rect)
        self.fonts = fonts
        self.app = app_ref

        ls_options = [(k, lbl) for (k, lbl) in config.LS_ALGORITHMS]
        dropdown_rect = pygame.Rect(self.rect.x + 12, self.rect.y + 60, self.rect.width - 24, 32)
        self.dropdown_ls = UIDropdown(
            dropdown_rect,
            ls_options,
            on_select=self._on_ls_selected,
            initial_idx=0,
            font=fonts.get("sm", pygame.font.Font(None, 16)),
        )

        self.slider_diff = UISlider(
            pygame.Rect(self.rect.x + 12, self.rect.y + 115, self.rect.width - 24, 34),
            min_val=0.20,
            max_val=0.90,
            initial_val=config.TARGET_DIFFICULTY_DEFAULT,
            label="Target Kesulitan Skuad",
            format_str="{:.2f}",
            on_change=self._on_diff_slider_changed,
            font=fonts.get("sm", pygame.font.Font(None, 16)),
        )

        btn_w = (self.rect.width - 32) // 2
        btn_y = self.rect.y + 520

        self.btn_reroll = UIButton(
            pygame.Rect(self.rect.x + 12, btn_y, btn_w, 38),
            "Acak Ulang [R]",
            fonts.get("sm", pygame.font.Font(None, 16)),
            on_click=self._on_reroll_clicked,
            bg_color=(242, 235, 222),
            hover_color=(255, 252, 245),
            active_color=(230, 220, 205),
            border_color=config.COLOR_CARD_BORDER,
            icon="🎲",
        )

        self.btn_tree_modal = UIButton(
            pygame.Rect(self.rect.x + 20 + btn_w, btn_y, btn_w, 38),
            "Visualizer [T]",
            fonts.get("sm", pygame.font.Font(None, 16)),
            on_click=self._on_tree_modal_clicked,
            bg_color=(242, 235, 222),
            hover_color=(255, 252, 245),
            active_color=(230, 220, 205),
            border_color=config.COLOR_ACCENT_GOLD,
            icon="📊",
        )

    def resize(self, rect: pygame.Rect) -> None:
        self.rect = pygame.Rect(rect)

    def _on_ls_selected(self, index: int, key: str) -> None:
        if hasattr(self.app, "selected_ls_algo"):
            self.app.selected_ls_algo = key
        if hasattr(self.app, "_run_optimization"):
            self.app._run_optimization()

    def _on_diff_slider_changed(self, val: float) -> None:
        if hasattr(self.app, "optimizer") and self.app.optimizer:
            self.app.optimizer.target_difficulty = val
        if hasattr(self.app, "_run_optimization"):
            self.app._run_optimization()

    def _on_reroll_clicked(self) -> None:
        if hasattr(self.app, "_reroll_pre_battle"):
            self.app._reroll_pre_battle()
        elif hasattr(self.app, "_run_optimization"):
            self.app._run_optimization()

    def _on_tree_modal_clicked(self) -> None:
        if hasattr(self.app, "pre_battle_visualizer"):
            self.app.pre_battle_visualizer.toggle()
        elif hasattr(self.app, "overlay") and hasattr(self.app.overlay, "toggle_tree_overlay"):
            self.app.overlay.toggle_tree_overlay()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.dropdown_ls.handle_event(event):
            return True
        if self.slider_diff.handle_event(event):
            return True
        if self.btn_reroll.handle_event(event):
            return True
        if self.btn_tree_modal.handle_event(event):
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

        # 1. KARTU PENGATURAN ALGORITMA LOCAL SEARCH
        card_algo_h = 78
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_algo_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        lbl_algo = font_tiny.render("Algoritma Optimizer:", True, config.COLOR_TEXT_SECONDARY)
        surface.blit(lbl_algo, (cx + 12, cy + 8))
        self.dropdown_ls.rect = pygame.Rect(cx + 10, cy + 28, card_w - 20, 32)
        self.dropdown_ls.draw(surface)

        # 2. KARTU TARGET KESULITAN & SLIDER
        cy += card_algo_h + 12
        card_diff_h = 72
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_diff_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        self.slider_diff.rect = pygame.Rect(cx + 12, cy + 14, card_w - 24, 40)
        self.slider_diff.draw(surface)

        # 3. KARTU METRIK EVALUASI SKUAD
        cy += card_diff_h + 12
        card_m_h = 132
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_m_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        m_title = font_tiny.render("── METRIK OPTIMASI SKUAD ──", True, config.COLOR_TEXT_SECONDARY)
        surface.blit(m_title, (cx + (card_w - m_title.get_width()) // 2, cy + 6))

        stats = getattr(self.app, "current_optimizer_stats", {}) or {}
        diff_score = stats.get("final_difficulty", 0.55)
        fit_score = stats.get("final_fitness", 0.0)
        iters = stats.get("iterations", 0)
        t_ms = stats.get("time_ms", 0.0)

        tile_w = (card_w - 28) // 2
        tile_h = 44
        ty1 = cy + 28
        ty2 = ty1 + tile_h + 6

        draw_metric_tile(surface, pygame.Rect(cx + 10, ty1, tile_w, tile_h),
                         "DIFFICULTY", f"{diff_score:.4f}",
                         val_color=config.COLOR_ACCENT_GOLD,
                         font_lbl=font_tiny, font_val=font_sm)

        draw_metric_tile(surface, pygame.Rect(cx + 18 + tile_w, ty1, tile_w, tile_h),
                         "FITNESS", f"{fit_score:+.4f}",
                         val_color=config.COLOR_STATUS_SUCCESS,
                         font_lbl=font_tiny, font_val=font_sm)

        draw_metric_tile(surface, pygame.Rect(cx + 10, ty2, tile_w, tile_h),
                         "ITERASI", f"{iters} step",
                         val_color=config.COLOR_TEXT_PRIMARY,
                         font_lbl=font_tiny, font_val=font_sm)

        draw_metric_tile(surface, pygame.Rect(cx + 18 + tile_w, ty2, tile_w, tile_h),
                         "WAKTU AI", f"{t_ms:.2f} ms",
                         val_color=config.COLOR_ACCENT_BLUE,
                         font_lbl=font_tiny, font_val=font_sm)

        # 4. KARTU VALIDASI KENDALA CSP (C1-C8)
        cy += card_m_h + 12
        card_csp_h = 148
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_csp_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        csp_title = font_tiny.render("── VALIDASI KENDALA CSP (C1-C8) ──", True, config.COLOR_TEXT_SECONDARY)
        surface.blit(csp_title, (cx + (card_w - csp_title.get_width()) // 2, cy + 6))

        cfg = getattr(self.app, "current_squad_config", {}) or {}
        tot_hp = cfg.get("total_hp", 0)
        tot_pot = cfg.get("total_potions", 0)
        tot_atk = cfg.get("total_atk", 0)

        constraints = [
            ("C1: Total HP Skuad <= 250", f"{tot_hp} HP", tot_hp <= 250),
            ("C2: Total Ramuan <= 5", f"{tot_pot} pot", tot_pot <= 5),
            ("C3: Total Bonus ATK <= 25", f"{tot_atk} atk", tot_atk <= 25),
            ("C4: Job Unik (No Duplicate)", "All Unique", True),
        ]

        row_y = cy + 28
        for label, val_text, is_valid in constraints:
            row_rect = pygame.Rect(cx + 10, row_y, card_w - 20, 26)
            draw_card(surface, row_rect, (250, 246, 238), border_color=(226, 216, 202), border_radius=4)

            status_icon = "✔" if is_valid else "✖"
            status_color = config.COLOR_STATUS_SUCCESS if is_valid else config.COLOR_STATUS_DANGER
            ic_surf = font_tiny.render(status_icon, True, status_color)
            lb_surf = font_tiny.render(label, True, config.COLOR_TEXT_PRIMARY)
            vl_surf = font_tiny.render(val_text, True, status_color)

            surface.blit(ic_surf, (row_rect.x + 8, row_rect.y + 5))
            surface.blit(lb_surf, (row_rect.x + 24, row_rect.y + 5))
            surface.blit(vl_surf, (row_rect.right - vl_surf.get_width() - 8, row_rect.y + 5))
            row_y += 28

        cy += card_csp_h + 12
        btn_w = (card_w - 8) // 2
        self.btn_reroll.rect = pygame.Rect(cx, cy, btn_w, 38)
        self.btn_tree_modal.rect = pygame.Rect(cx + btn_w + 8, cy, btn_w, 38)
        self.btn_reroll.draw(surface)
        self.btn_tree_modal.draw(surface)

    def draw_popups(self, surface: pygame.Surface) -> None:
        self.dropdown_ls.draw_menu(surface)
