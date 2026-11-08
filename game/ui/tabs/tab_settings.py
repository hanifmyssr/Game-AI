"""Tab 6: Pengaturan Game & Audio (Cozy Adventurer Journal Theme).

Menyediakan pengaturan volume Background Music (BGM), Sound Effects (SFX),
serta tombol reset status game.
"""

from typing import Dict, Any, Optional
import pygame
from ...core import config
from ..components import draw_card, draw_badge_pill, draw_metric_tile, UIButton, UISlider

MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1025)


class TabSettings:
    """Tab 6: Game & Audio Settings."""

    def __init__(self, rect: pygame.Rect, fonts: Dict[str, pygame.font.Font], app_ref: Any):
        self.rect = pygame.Rect(rect)
        self.fonts = fonts
        self.app = app_ref

        self.slider_bgm = UISlider(
            pygame.Rect(self.rect.x + 12, self.rect.y + 60, self.rect.width - 24, 38),
            min_val=0.0,
            max_val=1.0,
            initial_val=0.15,
            label="Volume Musik Latar (BGM)",
            format_str="{:.0%}",
            on_change=self._on_bgm_changed,
            font=fonts.get("sm", pygame.font.Font(None, 16)),
        )

        self.slider_sfx = UISlider(
            pygame.Rect(self.rect.x + 12, self.rect.y + 124, self.rect.width - 24, 38),
            min_val=0.0,
            max_val=1.0,
            initial_val=0.50,
            label="Volume Efek Suara (SFX)",
            format_str="{:.0%}",
            on_change=self._on_sfx_changed,
            font=fonts.get("sm", pygame.font.Font(None, 16)),
        )

        btn_w = self.rect.width - 24
        self.btn_reset = UIButton(
            pygame.Rect(self.rect.x + 12, self.rect.y + 208, btn_w, 38),
            "Reset Status Peti Harta & Hero",
            fonts.get("sm", pygame.font.Font(None, 16)),
            on_click=self._on_reset_clicked,
            bg_color=(255, 242, 242),
            hover_color=(255, 230, 230),
            active_color=(245, 218, 218),
            border_color=config.COLOR_STATUS_DANGER,
            icon="🔄",
        )

    def resize(self, rect: pygame.Rect) -> None:
        self.rect = pygame.Rect(rect)

    def _on_bgm_changed(self, val: float) -> None:
        audio = getattr(self.app, "audio", None)
        if audio and hasattr(audio, "set_bgm_volume"):
            audio.set_bgm_volume(val)
        elif audio and hasattr(audio, "bgm_volume"):
            audio.bgm_volume = val

    def _on_sfx_changed(self, val: float) -> None:
        audio = getattr(self.app, "audio", None)
        if audio and hasattr(audio, "set_sfx_volume"):
            audio.set_sfx_volume(val)
        elif audio and hasattr(audio, "sfx_volume"):
            audio.sfx_volume = val

    def _on_reset_clicked(self) -> None:
        if self.app and hasattr(self.app, "reset_game_state"):
            self.app.reset_game_state()
        else:
            chests = getattr(self.app, "chests", [])
            for c in chests:
                c["opened"] = False
            if hasattr(self.app, "player"):
                self.app.player.persistent_hp = config.MAX_HP
                self.app.player.persistent_potions = 3
                self.app.player.atk_bonus = 0
                self.app.player.def_bonus = 0
                if hasattr(self.app.player, "inventory"):
                    self.app.player.inventory.clear()
        self.btn_reset.text = "✓ Status Berhasil Direset!"
        self.reset_msg_timer = 2.5

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.slider_bgm.handle_event(event):
            return True
        if self.slider_sfx.handle_event(event):
            return True
        if self.btn_reset.handle_event(event):
            return True
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            if hasattr(event, "pos") and self.btn_reset.rect.collidepoint(event.pos):
                self._on_reset_clicked()
                return True
        return False

    def update(self, dt: float) -> None:
        if getattr(self, "reset_msg_timer", 0) > 0:
            self.reset_msg_timer -= dt
            if self.reset_msg_timer <= 0:
                self.btn_reset.text = "Reset Status Peti Harta & Hero"

    def draw(self, surface: pygame.Surface) -> None:
        font_tiny = self.fonts.get("tiny", pygame.font.Font(None, 13))
        font_sm = self.fonts.get("sm", pygame.font.Font(None, 16))
        font_title = self.fonts.get("title", pygame.font.Font(None, 19))

        cx = self.rect.x + 12
        cy = self.rect.y + 12
        card_w = self.rect.width - 24

        # 1. KARTU PENGATURAN AUDIO
        card_audio_h = 180
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_audio_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        lbl_aud = font_sm.render("Pengaturan Suara & Musik:", True, config.COLOR_TEXT_PRIMARY)
        surface.blit(lbl_aud, (cx + 12, cy + 8))

        self.slider_bgm.rect = pygame.Rect(cx + 12, cy + 36, card_w - 24, 38)
        self.slider_bgm.draw(surface)

        self.slider_sfx.rect = pygame.Rect(cx + 12, cy + 96, card_w - 24, 38)
        self.slider_sfx.draw(surface)

        # 2. KARTU RESET PERMAINAN
        cy += card_audio_h + 12
        card_rst_h = 96
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_rst_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        lbl_rst = font_sm.render("Manajemen Sesi Game:", True, config.COLOR_TEXT_PRIMARY)
        surface.blit(lbl_rst, (cx + 12, cy + 8))

        self.btn_reset.rect = pygame.Rect(cx + 12, cy + 38, card_w - 24, 38)
        self.btn_reset.draw(surface)

        # 3. KARTU INFORMASI AKADEMIK
        cy += card_rst_h + 12
        card_nfo_h = 175
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_nfo_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        lbl_nfo = font_sm.render("Tentang Aplikasi Game AI", True, config.COLOR_ACCENT_GOLD)
        surface.blit(lbl_nfo, (cx + 12, cy + 8))

        infos = [
            "Proyek Game AI: Bolu Kesepian",
            "Mata Kuliah: Kecerdasan Buatan (SEM 3)",
            "Universitas Pendidikan Indonesia",
            "Materi: Search (01-03), Minimax (04),",
            "CSP & Local Search (05-06),",
            "Logic KB (07), Automated Planning (08)",
        ]
        iy = cy + 34
        for line in infos:
            surface.blit(font_tiny.render(line, True, config.COLOR_TEXT_SECONDARY), (cx + 14, iy))
            iy += 21

    def draw_popups(self, surface: pygame.Surface) -> None:
        pass
