"""Tab 7: Materi 09: Decision Under Uncertainty — Jembatan Antarpulau & Bayesian Update.

Menampilkan pilihan 3 jembatan berisiko (Atas, Kiri, Bawah), Bayesian Belief Update
(Prior -> Posterior), Entropi Shannon, Expected Cost, dan kontrol cuaca.
"""

from typing import Dict, Any
import pygame

from ...core import config
from ...ai.uncertainty import WEATHER_HUJAN, BRIDGE_KEYS, BRIDGE_NAMES
from ..components import (
    draw_card,
    draw_badge_pill,
    draw_metric_tile,
    draw_mode_context_banner,
    UIButton,
    UISlider,
)


class TabUncertainty:
    """Tab 7: Materi 09 Decision Under Uncertainty (3 Jembatan Antarpulau & Bayes)."""

    def __init__(self, rect: pygame.Rect, fonts: Dict[str, pygame.font.Font], app_ref: Any):
        self.rect = pygame.Rect(rect)
        self.fonts = fonts
        self.app = app_ref

        btn_font = fonts.get("sm") or pygame.font.Font(None, 16)
        tiny_font = fonts.get("tiny") or pygame.font.Font(None, 13)

        self.bridge_btns: Dict[str, UIButton] = {}
        for key, lbl in (("atas", "Atas"), ("kiri", "Kiri"), ("bawah", "Bawah")):
            self.bridge_btns[key] = UIButton(
                pygame.Rect(0, 0, 80, 26),
                lbl,
                tiny_font,
                on_click=lambda k=key: self._on_select_bridge(k),
                bg_color=(242, 235, 222),
                hover_color=(255, 252, 245),
                active_color=(230, 220, 205),
                border_color=config.COLOR_CARD_BORDER,
            )

        self.btn_inspect = UIButton(
            pygame.Rect(self.rect.x + 12, self.rect.y + 180, self.rect.width - 24, 34),
            "Cek Jembatan (Observasi Bayes)",
            btn_font,
            on_click=self._on_inspect_clicked,
            bg_color=(232, 246, 252),
            hover_color=(244, 252, 255),
            active_color=(212, 236, 246),
            border_color=config.COLOR_ACCENT_BLUE,
        )

        self.slider_prior = UISlider(
            pygame.Rect(self.rect.x + 12, self.rect.y + 340, self.rect.width - 24, 34),
            min_val=0.05,
            max_val=0.95,
            initial_val=0.40,
            label="Prior Hujan P(Ambruk)",
            format_str="{:.0%}",
            on_change=self._on_prior_changed,
            font=btn_font,
        )

        self.slider_acc = UISlider(
            pygame.Rect(self.rect.x + 12, self.rect.y + 382, self.rect.width - 24, 34),
            min_val=0.65,
            max_val=0.95,
            initial_val=0.85,
            label="Akurasi Sensor Cek",
            format_str="{:.0%}",
            on_change=self._on_acc_changed,
            font=btn_font,
        )

        self.btn_weather = UIButton(
            pygame.Rect(self.rect.x + 12, self.rect.y + 424, self.rect.width - 24, 34),
            "Ubah Cuaca: Hujan",
            btn_font,
            on_click=self._on_toggle_weather,
            bg_color=(236, 242, 252),
            hover_color=(246, 250, 255),
            active_color=(218, 228, 246),
            border_color=config.COLOR_ACCENT_BLUE,
        )

        self.btn_repair = UIButton(
            pygame.Rect(self.rect.x + 12, self.rect.y + 464, self.rect.width - 24, 34),
            "Perbaiki Jembatan",
            btn_font,
            on_click=self._on_repair_clicked,
            bg_color=(235, 248, 238),
            hover_color=(246, 254, 248),
            active_color=(218, 238, 222),
            border_color=config.COLOR_STATUS_SUCCESS,
        )

    def resize(self, rect: pygame.Rect) -> None:
        self.rect = pygame.Rect(rect)

    def _on_select_bridge(self, key: str) -> None:
        eng = getattr(self.app, "bridge_uncertainty", None)
        if eng:
            eng.select_bridge(key)

    def _on_inspect_clicked(self) -> None:
        eng = getattr(self.app, "bridge_uncertainty", None)
        if not eng:
            return
        res = eng.inspect_bridge()
        b_name = BRIDGE_NAMES.get(res.get("bridge", "atas"), "Jembatan")
        if res.get("updated"):
            self.app.ai_ticker_info = {
                "title": f"[M9 BAYES #{res['step']} - {b_name}] Bukti: {res['obs_label']}",
                "detail": (
                    f"Prior {res['prior_before'] * 100:.1f}% -> Posterior {res['posterior'] * 100:.1f}% "
                    f"| Entropi: {res['entropy']:.2f} bit"
                ),
                "timer": 4.5,
            }
        else:
            self.app.ai_ticker_info = {
                "title": f"[M9 BAYES - {b_name}] Inspeksi Selesai",
                "detail": res.get("reason", "Batas inspeksi tercapai."),
                "timer": 3.5,
            }

    def _on_prior_changed(self, val: float) -> None:
        eng = getattr(self.app, "bridge_uncertainty", None)
        if eng:
            eng.set_rain_prior(val)

    def _on_acc_changed(self, val: float) -> None:
        eng = getattr(self.app, "bridge_uncertainty", None)
        if eng:
            eng.set_sensor_accuracy(val)

    def _on_toggle_weather(self) -> None:
        eng = getattr(self.app, "bridge_uncertainty", None)
        if not eng:
            return
        nxt = eng.toggle_weather()
        if hasattr(self.app, "_sync_bridge_walkability"):
            self.app._sync_bridge_walkability()
        lbl = "Hujan Deras (Arus Tinggi)" if nxt == WEATHER_HUJAN else "Cerah (Arus Tenang)"
        self.app.ai_ticker_info = {
            "title": f"[M9 CUACA] Berubah menjadi {lbl}",
            "detail": f"Prior P(Ambruk) awal: {eng.active_prior * 100:.0f}% | Entropi: {eng.get_entropy():.2f} bit",
            "timer": 4.0,
        }

    def _on_repair_clicked(self) -> None:
        eng = getattr(self.app, "bridge_uncertainty", None)
        if not eng:
            return
        res = eng.repair_bridge()
        b_name = BRIDGE_NAMES.get(res.get("bridge", "atas"), "Jembatan")
        if hasattr(self.app, "_sync_bridge_walkability"):
            self.app._sync_bridge_walkability()
        if hasattr(self.app, "refresh_search_focus"):
            self.app.refresh_search_focus(force=True)
        self.app.ai_ticker_info = {
            "title": f"[JEMBATAN DIPERBAIKI] {b_name} Kembali Utuh!",
            "detail": f"Jalur dibuka ulang untuk demo. Prior saat ini: {eng.active_prior * 100:.0f}%.",
            "timer": 4.0,
        }

    def handle_event(self, event: pygame.event.Event) -> bool:
        for btn in self.bridge_btns.values():
            if btn.handle_event(event):
                return True
        if self.btn_inspect.handle_event(event):
            return True
        if self.slider_prior.handle_event(event):
            return True
        if self.slider_acc.handle_event(event):
            return True
        if self.btn_weather.handle_event(event):
            return True
        if self.btn_repair.handle_event(event):
            return True
        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        font_tiny = self.fonts.get("tiny") or pygame.font.Font(None, 13)
        font_sm = self.fonts.get("sm") or pygame.font.Font(None, 16)

        cx = self.rect.x + 12
        cy = self.rect.y + 10
        card_w = self.rect.width - 24

        cur_mode = getattr(self.app, "game_mode", "EXPLORATION")
        banner_h = draw_mode_context_banner(
            surface, cx, cy, card_w, cur_mode, "EXPLORATION",
            "Jembatan antarpulau & Bayes aktif di eksplorasi.", font_tiny,
        )
        cy += banner_h
        gap = 8

        eng = getattr(self.app, "bridge_uncertainty", None)
        if eng:
            is_rain = eng.weather_state == WEATHER_HUJAN
            sel_key = eng.selected_bridge
            status = eng.bridge_status
            prior = eng.active_prior
            post = eng.posterior
            ent = eng.get_entropy()
            obs_lbl = eng.last_obs
            obs_cnt = len(eng.observations)
            max_obs = eng.max_inspections
            exp = eng.get_expected_cost_comparison()
            if not self.slider_prior.is_dragging:
                self.slider_prior.value = eng.rain_prior
            if not self.slider_acc.is_dragging:
                self.slider_acc.value = eng.sensor_accuracy
        else:
            is_rain, sel_key, status, prior, post, ent = False, "atas", "UTUH", 0.10, 0.10, 0.47
            obs_lbl, obs_cnt, max_obs = "-", 0, 4
            exp = {"expected_upper": 15.6, "safe_cost": 28.0, "recommend_detour": False, "recommend_text": "Aman Dilintasi"}

        # 1. KARTU CUACA & PILIH JEMBATAN BERISIKO (ATAS / KIRI / BAWAH)
        card_top_h = 74
        draw_card(
            surface, pygame.Rect(cx, cy, card_w, card_top_h), config.COLOR_CARD_BG,
            border_color=config.COLOR_CARD_BORDER, border_radius=8,
        )
        w_txt = "CUACA: HUJAN" if is_rain else "CUACA: CERAH"
        w_bg = (232, 240, 254) if is_rain else (252, 243, 218)
        w_fg = config.COLOR_ACCENT_BLUE if is_rain else config.COLOR_ACCENT_GOLD
        pw_w = font_tiny.size(w_txt)[0] + 16
        draw_badge_pill(surface, pygame.Rect(cx + 10, cy + 8, pw_w, 22), w_txt, w_bg, w_fg, font_tiny, border_color=w_fg)

        if status == "AMBRUK":
            s_bg, s_fg = (254, 232, 230), config.COLOR_STATUS_DANGER
        elif status == "RAWAN":
            s_bg, s_fg = (255, 242, 216), config.COLOR_ACCENT_GOLD
        else:
            s_bg, s_fg = (232, 248, 236), config.COLOR_STATUS_SUCCESS
        s_txt = f"{BRIDGE_NAMES.get(sel_key, 'Jembatan').upper()}: {status}"
        pw_s = font_tiny.size(s_txt)[0] + 14
        draw_badge_pill(surface, pygame.Rect(cx + card_w - pw_s - 10, cy + 8, pw_s, 22), s_txt, s_bg, s_fg, font_tiny, border_color=s_fg)

        # 3 tombol pilih jembatan (Atas, Kiri, Bawah)
        bw = (card_w - 32) // 3
        for i, k in enumerate(BRIDGE_KEYS):
            btn = self.bridge_btns[k]
            btn.rect = pygame.Rect(cx + 10 + i * (bw + 6), cy + 38, bw, 26)
            is_sel = (k == sel_key)
            btn.bg_color = (232, 244, 254) if is_sel else (244, 238, 226)
            btn.border_color = config.COLOR_ACCENT_BLUE if is_sel else config.COLOR_CARD_BORDER
            btn.text_color = config.COLOR_ACCENT_BLUE if is_sel else config.COLOR_TEXT_PRIMARY
            btn.draw(surface)

        # 2. KARTU BAYESIAN BELIEF UPDATE
        cy += card_top_h + gap
        tile_h = max(44, font_tiny.get_height() + font_sm.get_height() + 14)
        tile_gap = 6
        row1_y = cy + 32
        row2_y = row1_y + tile_h + tile_gap
        inspect_y = row2_y + tile_h + tile_gap
        card_bayes_h = (inspect_y - cy) + 34 + 8
        draw_card(
            surface, pygame.Rect(cx, cy, card_w, card_bayes_h), config.COLOR_CARD_BG,
            border_color=config.COLOR_CARD_BORDER, border_radius=8,
        )
        surface.blit(font_sm.render("Bayesian Belief Update:", True, config.COLOR_TEXT_PRIMARY), (cx + 10, cy + 8))
        cnt_txt = f"Cek {obs_cnt}/{max_obs}"
        pw_c = font_tiny.size(cnt_txt)[0] + 14
        draw_badge_pill(surface, pygame.Rect(cx + card_w - pw_c - 10, cy + 7, pw_c, 20),
                        cnt_txt, (242, 235, 222), config.COLOR_TEXT_SECONDARY, font_tiny, border_color=config.COLOR_CARD_BORDER)

        tile_w = (card_w - 28) // 2
        draw_metric_tile(
            surface, pygame.Rect(cx + 10, row1_y, tile_w, tile_h),
            "Prior Awal", f"{prior * 100:.0f}%",
            val_color=config.COLOR_TEXT_SECONDARY, font_lbl=font_tiny, font_val=font_sm,
        )
        post_col = config.COLOR_STATUS_DANGER if post >= 0.50 else config.COLOR_ACCENT_BLUE
        draw_metric_tile(
            surface, pygame.Rect(cx + 18 + tile_w, row1_y, tile_w, tile_h),
            "Posterior P(Ambruk)", f"{post * 100:.1f}%",
            val_color=post_col, font_lbl=font_tiny, font_val=font_sm,
        )
        draw_metric_tile(
            surface, pygame.Rect(cx + 10, row2_y, tile_w, tile_h),
            "Entropi H(S)", f"{ent:.2f} bit",
            val_color=config.COLOR_STATUS_SUCCESS, font_lbl=font_tiny, font_val=font_sm,
        )
        short_obs = "Retak!" if "Retak" in obs_lbl else ("Kokoh" if "Kokoh" in obs_lbl else "-")
        obs_col = config.COLOR_STATUS_DANGER if short_obs == "Retak!" else config.COLOR_ACCENT_BLUE
        draw_metric_tile(
            surface, pygame.Rect(cx + 18 + tile_w, row2_y, tile_w, tile_h),
            "Bukti Terakhir", short_obs,
            val_color=obs_col, font_lbl=font_tiny, font_val=font_sm,
        )

        self.btn_inspect.rect = pygame.Rect(cx + 10, inspect_y, card_w - 20, 34)
        self.btn_inspect.draw(surface)

        # 3. KARTU EXPECTED COST & REKOMENDASI
        cy += card_bayes_h + gap
        card_exp_h = 32 + tile_h + 8
        draw_card(
            surface, pygame.Rect(cx, cy, card_w, card_exp_h), config.COLOR_CARD_BG,
            border_color=config.COLOR_CARD_BORDER, border_radius=8,
        )
        surface.blit(font_tiny.render("Expected Cost:", True, config.COLOR_TEXT_SECONDARY), (cx + 10, cy + 8))
        rec_txt = exp["recommend_text"]
        rec_fg = config.COLOR_ACCENT_GOLD if exp["recommend_detour"] else config.COLOR_STATUS_SUCCESS
        rec_bg = (255, 242, 216) if exp["recommend_detour"] else (232, 248, 236)
        pw_r = font_tiny.size(rec_txt)[0] + 14
        draw_badge_pill(surface, pygame.Rect(cx + card_w - pw_r - 10, cy + 5, pw_r, 20), rec_txt, rec_bg, rec_fg, font_tiny, border_color=rec_fg)

        exp_up_str = "INF" if exp["expected_upper"] == float("inf") else f"{exp['expected_upper']:.1f}"
        draw_metric_tile(
            surface, pygame.Rect(cx + 10, cy + 32, tile_w, tile_h),
            "Exp. Cost Jembatan", exp_up_str,
            val_color=config.COLOR_STATUS_DANGER if exp["recommend_detour"] else config.COLOR_ACCENT_BLUE,
            font_lbl=font_tiny, font_val=font_sm,
        )
        draw_metric_tile(
            surface, pygame.Rect(cx + 18 + tile_w, cy + 32, tile_w, tile_h),
            "Cost Pulau Tengah", f"{exp['safe_cost']:.1f}",
            val_color=config.COLOR_STATUS_SUCCESS, font_lbl=font_tiny, font_val=font_sm,
        )

        # 4. KARTU KONTROL CUACA & PARAMETER PROBABILITAS
        cy += card_exp_h + gap
        card_ctrl_h = 184
        draw_card(
            surface, pygame.Rect(cx, cy, card_w, card_ctrl_h), config.COLOR_CARD_BG,
            border_color=config.COLOR_CARD_BORDER, border_radius=8,
        )
        self.slider_prior.rect = pygame.Rect(cx + 10, cy + 8, card_w - 20, 36)
        self.slider_prior.draw(surface)

        self.slider_acc.rect = pygame.Rect(cx + 10, cy + 52, card_w - 20, 36)
        self.slider_acc.draw(surface)

        self.btn_weather.text = "Ubah Cuaca: Cerah" if is_rain else "Ubah Cuaca: Hujan Deras"
        self.btn_weather.rect = pygame.Rect(cx + 10, cy + 100, card_w - 20, 34)
        self.btn_weather.draw(surface)

        b_label = BRIDGE_NAMES.get(sel_key, "Jembatan")
        self.btn_repair.text = f"Perbaiki {b_label}" if status == "AMBRUK" else f"Perbaiki / Reset {b_label}"
        self.btn_repair.rect = pygame.Rect(cx + 10, cy + 140, card_w - 20, 34)
        self.btn_repair.draw(surface)

    def draw_popups(self, surface: pygame.Surface) -> None:
        pass
