"""InspectorDock: Panel Konten AI Bernuansa Kertas Perkamen (Warm Parchment).

Wadah inspektur selebar 356px (x: 64..420) yang mendukung mode Buka/Tutup (Collapsible Drawer).
"""

from typing import Dict, Any, Optional
import pygame
from ..core import config
from .components import draw_card, UIButton
from .tabs import (
    TabCompanion,
    TabSearch,
    TabMinimax,
    TabCSP,
    TabLogic,
    TabPlanning,
    TabSettings,
)

MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1025)
MOUSEBUTTONUP = getattr(pygame, "MOUSEBUTTONUP", 1026)
MOUSEMOTION = getattr(pygame, "MOUSEMOTION", 1024)

TAB_HEADERS = [
    ("HERO COMPANION", "Status Hero & Inventaris"),
    ("01-03: PATHFINDING", "Pencarian Rute (A*, UCS)"),
    ("04: ADVERSARIAL", "Minimax AI & Alpha-Beta"),
    ("05-06: CSP & LOCAL SEARCH", "Optimasi Skuad Lawan"),
    ("07: LOGIC & REASONING", "Knowledge Base & Resolusi"),
    ("08: AUTOMATED PLANNING", "Perencana Tugas PDDL"),
    ("PENGATURAN & AUDIO", "Volume & Sesi Permainan"),
]


class InspectorDock:
    """Panel inspektur konten AI bergaya jurnal petualang (bisa dilipat/dibuka)."""

    def __init__(self, rect: pygame.Rect, fonts: Dict[str, pygame.font.Font], app_ref: Any):
        self.rect = pygame.Rect(rect)
        self.fonts = fonts
        self.app = app_ref
        self.active_tab_id = 0
        self.is_open = True  # Status buka / tutup drawer

        content_rect = pygame.Rect(self.rect.x, self.rect.y + 48, self.rect.width, self.rect.height - 48)

        # Inisialisasi 7 Tab
        self.tabs = {
            0: TabCompanion(content_rect, fonts, app_ref),
            1: TabSearch(content_rect, fonts, app_ref),
            2: TabMinimax(content_rect, fonts, app_ref),
            3: TabCSP(content_rect, fonts, app_ref),
            4: TabLogic(content_rect, fonts, app_ref),
            5: TabPlanning(content_rect, fonts, app_ref),
            6: TabSettings(content_rect, fonts, app_ref),
        }

        # Tombol Tutup Panel di Header (Pojok Kanan Atas)
        btn_collapse_w = 78
        self.btn_collapse = UIButton(
            pygame.Rect(self.rect.right - btn_collapse_w - 10, self.rect.y + 10, btn_collapse_w, 28),
            "[X] Tutup",
            fonts.get("tiny", pygame.font.Font(None, 13)),
            on_click=self.close,
            bg_color=(238, 230, 216),
            hover_color=(255, 252, 245),
            active_color=(226, 216, 200),
            border_color=config.COLOR_INSPECTOR_BORDER,
        )

    def toggle(self) -> None:
        self.is_open = not self.is_open

    def open(self) -> None:
        self.is_open = True

    def close(self) -> None:
        self.is_open = False

    def set_active_tab(self, tab_id: int) -> None:
        if tab_id in self.tabs:
            self.active_tab_id = tab_id
            self.is_open = True  # Otomatis buka jika pemain memilih tab baru

    def resize(self, height: int) -> None:
        """Memperbarui tinggi Inspector Dock dan seluruh tab konten mengikuti window."""
        self.rect.height = height
        content_rect = pygame.Rect(self.rect.x, self.rect.y + 48, self.rect.width, self.rect.height - 48)
        for tab in self.tabs.values():
            if hasattr(tab, "resize"):
                tab.resize(content_rect)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.is_open:
            return False

        # Klik tombol Tutup Panel
        if self.btn_collapse.handle_event(event):
            return True
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            if hasattr(event, "pos") and self.btn_collapse.rect.collidepoint(event.pos):
                self.close()
                return True

        active_tab = self.tabs.get(self.active_tab_id)
        if active_tab and active_tab.handle_event(event):
            return True

        if hasattr(event, "pos"):
            if self.rect.collidepoint(event.pos):
                return True

        return False

    def update(self, dt: float) -> None:
        if not self.is_open:
            return
        active_tab = self.tabs.get(self.active_tab_id)
        if active_tab:
            active_tab.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        if not self.is_open:
            return

        # 1. Latar Belakang Perkamen Hangat
        draw_card(surface, self.rect, config.COLOR_INSPECTOR_BG, border_color=None, border_radius=0)
        # Garis pembatas buku kulit di sisi kanan (x = 420)
        pygame.draw.line(surface, config.COLOR_INSPECTOR_BORDER,
                         (self.rect.right - 1, self.rect.y), (self.rect.right - 1, self.rect.bottom), 2)

        # 2. Header Pita Perkamen
        header_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 48)
        draw_card(surface, header_rect, config.COLOR_HEADER_BG, border_color=None, border_radius=0)
        pygame.draw.line(surface, config.COLOR_INSPECTOR_BORDER,
                         (self.rect.x, header_rect.bottom - 1), (self.rect.right - 1, header_rect.bottom - 1), 1)

        title, subtitle = TAB_HEADERS[self.active_tab_id] if 0 <= self.active_tab_id < len(TAB_HEADERS) else ("INSPEKTOR AI", "Detail Modul")
        font_title = self.fonts.get("title", pygame.font.Font(None, 19))
        font_tiny = self.fonts.get("tiny", pygame.font.Font(None, 13))

        t_surf = font_title.render(title, True, config.COLOR_ACCENT_GOLD)
        surface.blit(t_surf, (self.rect.x + 14, self.rect.y + 6))

        st_surf = font_tiny.render(subtitle, True, config.COLOR_TEXT_SECONDARY)
        surface.blit(st_surf, (self.rect.x + 14, self.rect.y + 27))

        # Tombol Lipat
        self.btn_collapse.draw(surface)

        # 3. Gambar Konten Tab Aktif dengan proteksi batas kliping
        content_rect = pygame.Rect(self.rect.x, self.rect.y + 48, self.rect.width, self.rect.height - 48)
        orig_clip = surface.get_clip()
        surface.set_clip(content_rect)
        active_tab = self.tabs.get(self.active_tab_id)
        if active_tab:
            active_tab.draw(surface)
        surface.set_clip(orig_clip)
        if active_tab:
            active_tab.draw_popups(surface)
