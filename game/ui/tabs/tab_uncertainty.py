"""Tab 6: Materi 09: Decision Under Uncertainty — Bayesian Belief Sonar.

Menampilkan akurasi sensor, metrik probabilitas Bayes (MAP, Entropi, Sinyal),
kandidat koordinat teratas, serta tombol pindai sonar [F] dan toggle heatmap.
"""

from typing import Dict, Any
import pygame

from ...core import config
from ..components import (
    draw_card,
    draw_badge_pill,
    draw_metric_tile,
    draw_mode_context_banner,
    UIButton,
    UISlider,
    render_fitted_text,
)


class TabUncertainty:
    """Tab 6: Materi 09 Decision Under Uncertainty (Bayesian Belief Sonar)."""

    def __init__(self, rect: pygame.Rect, fonts: Dict[str, pygame.font.Font], app_ref: Any):
        self.rect = pygame.Rect(rect)
        self.fonts = fonts
        self.app = app_ref

        self.slider_acc = UISlider(
            pygame.Rect(self.rect.x + 12, self.rect.y + 60, self.rect.width - 24, 34),
            min_val=0.60,
            max_val=0.95,
            initial_val=0.82,
            label="Akurasi Sensor Sonar",
            format_str="{:.0%}",
            on_change=self._on_acc_changed,
            font=fonts.get("sm", pygame.font.Font(None, 16)),
        )

        btn_w = (self.rect.width - 32) // 2
        self.btn_scan = UIButton(
            pygame.Rect(self.rect.x + 12, self.rect.y + 490, btn_w, 38),
            "Pindai Sonar [F]",
            fonts.get("sm", pygame.font.Font(None, 16)),
            on_click=self._on_scan_clicked,
            bg_color=(232, 246, 252),
            hover_color=(244, 252, 255),
            active_color=(212, 236, 246),
            border_color=config.COLOR_ACCENT_BLUE,
        )

        self.btn_heatmap = UIButton(
            pygame.Rect(self.rect.x + 20 + btn_w, self.rect.y + 490, btn_w, 38),
            "Heatmap: ON",
            fonts.get("sm", pygame.font.Font(None, 16)),
            on_click=self._on_toggle_heatmap,
            bg_color=(242, 235, 222),
            hover_color=(255, 252, 245),
            active_color=(230, 220, 205),
            border_color=config.COLOR_ACCENT_GOLD,
        )

    def resize(self, rect: pygame.Rect) -> None:
        self.rect = pygame.Rect(rect)

    def _on_acc_changed(self, val: float) -> None:
        sonar = getattr(self.app, "relic_sonar", None)
        if sonar:
            sonar.sensor_accuracy = val

    def _on_scan_clicked(self) -> None:
        if self.app and hasattr(self.app, "_trigger_sonar_scan"):
            self.app._trigger_sonar_scan()

    def _on_toggle_heatmap(self) -> None:
        sonar = getattr(self.app, "relic_sonar", None)
        if sonar:
            sonar.heatmap_visible = not sonar.heatmap_visible

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.slider_acc.handle_event(event):
            return True
        if self.btn_scan.handle_event(event):
            return True
        if self.btn_heatmap.handle_event(event):
            return True
        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        font_tiny = self.fonts.get("tiny", pygame.font.Font(None, 13))
        font_sm = self.fonts.get("sm", pygame.font.Font(None, 16))

        cx = self.rect.x + 12
        cy = self.rect.y + 12
        card_w = self.rect.width - 24

        cur_mode = getattr(self.app, "game_mode", "EXPLORATION")
        banner_h = draw_mode_context_banner(
            surface, cx, cy, card_w, cur_mode, "EXPLORATION",
            "Sonar Bayesian & Relik aktif di fase eksplorasi.", font_tiny,
        )
        cy += banner_h
        gap = 8 if banner_h > 0 else 12

        sonar = getattr(self.app, "relic_sonar", None)
        found = bool(sonar and sonar.found)
        scan_count = sonar.scan_count if sonar else 0
        last_sig = (sonar.last_signal or "-") if sonar else "-"
        map_pos, map_prob = sonar.get_map_estimate() if sonar else (None, 0.0)
        entropy = sonar.get_entropy() if sonar else 0.0
        heatmap_on = bool(sonar and sonar.heatmap_visible)

        if sonar and not self.slider_acc.is_dragging:
            self.slider_acc.value = sonar.sensor_accuracy

        # 1. KARTU STATUS RELIK & AKURASI SENSOR
        card_top_h = 104
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_top_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        lbl_st = font_tiny.render("Relik Ikan Emas Kuno:", True, config.COLOR_TEXT_SECONDARY)
        surface.blit(lbl_st, (cx + 12, cy + 10))
        pill_txt = "DITEMUKAN!" if found else "TERSEMBUNYI"
        pill_bg = (232, 248, 236) if found else (252, 243, 218)
        pill_fg = config.COLOR_STATUS_SUCCESS if found else config.COLOR_ACCENT_GOLD
        pw = font_tiny.size(pill_txt)[0] + 18
        draw_badge_pill(surface, pygame.Rect(cx + card_w - pw - 10, cy + 7, pw, 20),
                        pill_txt, pill_bg, pill_fg, font_tiny, border_color=pill_fg)

        self.slider_acc.rect = pygame.Rect(cx + 12, cy + 40, card_w - 24, 40)
        self.slider_acc.draw(surface)

        # 2. KARTU METRIK BAYESIAN BELIEF (GRID 2x2)
        cy += card_top_h + gap
        card_m_h = 132
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_m_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        m_title = font_tiny.render("── METRIK BAYESIAN BELIEF ──", True, config.COLOR_TEXT_SECONDARY)
        surface.blit(m_title, (cx + (card_w - m_title.get_width()) // 2, cy + 6))

        tile_w = (card_w - 28) // 2
        tile_h = 44
        ty1 = cy + 28
        ty2 = ty1 + tile_h + 6

        draw_metric_tile(surface, pygame.Rect(cx + 10, ty1, tile_w, tile_h),
                         "SCAN SONAR", f"{scan_count}x",
                         val_color=config.COLOR_ACCENT_BLUE,
                         font_lbl=font_tiny, font_val=font_sm)

        draw_metric_tile(surface, pygame.Rect(cx + 18 + tile_w, ty1, tile_w, tile_h),
                         "SINYAL TERAKHIR", last_sig,
                         val_color=config.COLOR_ACCENT_GOLD,
                         font_lbl=font_tiny, font_val=font_tiny)

        draw_metric_tile(surface, pygame.Rect(cx + 10, ty2, tile_w, tile_h),
                         "PUNCAK PELUANG", f"{map_prob * 100:.2f}%",
                         val_color=config.COLOR_STATUS_SUCCESS,
                         font_lbl=font_tiny, font_val=font_sm)

        draw_metric_tile(surface, pygame.Rect(cx + 18 + tile_w, ty2, tile_w, tile_h),
                         "ENTROPI (BIT)", f"{entropy:.2f} bit",
                         val_color=config.COLOR_TEXT_PRIMARY,
                         font_lbl=font_tiny, font_val=font_sm)

        # 3. KARTU KANDIDAT LOKASI TERATAS (MAP ESTIMATE)
        cy += card_m_h + gap
        card_cand_h = 120
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_cand_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        c_title = font_tiny.render("── TEBAKAN LOKASI (POSTERIOR) ──", True, config.COLOR_TEXT_SECONDARY)
        surface.blit(c_title, (cx + (card_w - c_title.get_width()) // 2, cy + 6))

        if found:
            render_fitted_text(surface, font_tiny, "Relik sudah ditemukan! Buff Boss Battle aktif.",
                               config.COLOR_STATUS_SUCCESS, (cx + 12, cy + 38), card_w - 24)
        elif scan_count == 0 or not sonar:
            render_fitted_text(surface, font_tiny, "Tekan [F] di peta untuk memancarkan sonar pertama.",
                               config.COLOR_TEXT_MUTED, (cx + 12, cy + 38), card_w - 24)
            render_fitted_text(surface, font_tiny, "Prior saat ini seragam di seluruh daratan.",
                               config.COLOR_TEXT_SECONDARY, (cx + 12, cy + 58), card_w - 24)
        else:
            top3 = sonar.get_top_candidates(3)
            ry = cy + 28
            for idx, (pos, prob) in enumerate(top3, start=1):
                row_r = pygame.Rect(cx + 10, ry, card_w - 20, 26)
                draw_card(surface, row_r, (250, 246, 238), border_color=(226, 216, 202), border_radius=4)
                lbl = f"#{idx} Grid ({pos[0]}, {pos[1]})"
                val = f"{prob * 100:.2f}%"
                col = config.COLOR_STATUS_SUCCESS if idx == 1 else config.COLOR_TEXT_PRIMARY
                surface.blit(font_tiny.render(lbl, True, col), (row_r.x + 8, row_r.y + 5))
                v_surf = font_tiny.render(val, True, config.COLOR_ACCENT_BLUE)
                surface.blit(v_surf, (row_r.right - v_surf.get_width() - 8, row_r.y + 5))
                ry += 29

        # 4. TOMBOL AKSI
        cy += card_cand_h + gap
        btn_w = (card_w - 8) // 2
        self.btn_scan.rect = pygame.Rect(cx, cy, btn_w, 38)
        self.btn_heatmap.rect = pygame.Rect(cx + btn_w + 8, cy, btn_w, 38)
        self.btn_heatmap.text = f"Heatmap: {'ON' if heatmap_on else 'OFF'}"
        self.btn_scan.draw(surface)
        self.btn_heatmap.draw(surface)

    def draw_popups(self, surface: pygame.Surface) -> None:
        pass
