"""InspectorDock: Panel Konten AI Bernuansa Kertas Perkamen (Warm Parchment).

Wadah inspektur selebar 356px (x: 64..420) yang mendukung mode Buka/Tutup (Collapsible Drawer).
"""

from typing import Dict, Any, Optional
import pygame
from ..core import config
from .components import draw_card, UIButton, render_fitted_text
from .tab_glossary import draw_tab_glossary
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
MOUSEWHEEL = getattr(pygame, "MOUSEWHEEL", 1027)

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
        self.header_h = 48

        content_rect = pygame.Rect(self.rect.x, self.rect.y + self.header_h, self.rect.width, self.rect.height - self.header_h)

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

        # Tombol Tutup Panel & Tombol Bantuan (?) di Header (Pojok Kanan Atas)
        btn_collapse_w = 84
        btn_help_w = 28
        self.show_glossary: bool = False
        self.glossary_scroll_y: float = 0.0
        self.glossary_max_scroll: float = 0.0

        self.btn_collapse = UIButton(
            pygame.Rect(self.rect.right - btn_collapse_w - 10, self.rect.y + 10, btn_collapse_w, 28),
            "[TAB] Tutup",
            fonts.get("tiny", pygame.font.Font(None, 13)),
            on_click=self.close,
            bg_color=(238, 230, 216),
            hover_color=(255, 252, 245),
            active_color=(226, 216, 200),
            border_color=config.COLOR_INSPECTOR_BORDER,
        )
        self.btn_help = UIButton(
            pygame.Rect(self.btn_collapse.rect.x - btn_help_w - 6, self.rect.y + 10, btn_help_w, 28),
            "?",
            fonts.get("sm", pygame.font.Font(None, 16)),
            on_click=self.toggle_glossary,
            bg_color=(252, 243, 218),
            hover_color=(255, 252, 245),
            active_color=(235, 218, 178),
            border_color=config.COLOR_ACCENT_GOLD,
        )

    def toggle_glossary(self) -> None:
        self.show_glossary = not self.show_glossary
        self.glossary_scroll_y = 0.0

    def toggle(self) -> None:
        self.is_open = not self.is_open

    def open(self) -> None:
        self.is_open = True

    def close(self) -> None:
        self.is_open = False

    def set_active_tab(self, tab_id: int) -> None:
        if tab_id in self.tabs:
            self.active_tab_id = tab_id
            self.glossary_scroll_y = 0.0
            self.is_open = True  # Otomatis buka jika pemain memilih tab baru

    def resize(self, height: int, width: Optional[int] = None, x: Optional[int] = None) -> None:
        """Memperbarui tinggi & lebar Inspector Dock dan seluruh tab konten mengikuti window."""
        self.rect.height = height
        if width is not None:
            self.rect.width = width
        if x is not None:
            self.rect.x = x
        base_w = float(getattr(config, "BASE_INSPECTOR_WIDTH", 356))
        scale = max(1.0, self.rect.width / base_w)
        self.header_h = max(48, int(round(48 * scale)))
        btn_collapse_w = int(round(88 * scale))
        btn_collapse_h = int(round(28 * scale))
        btn_help_w = int(round(28 * scale))
        self.btn_collapse.rect = pygame.Rect(
            self.rect.right - btn_collapse_w - 12,
            self.rect.y + (self.header_h - btn_collapse_h) // 2,
            btn_collapse_w,
            btn_collapse_h,
        )
        self.btn_help.rect = pygame.Rect(
            self.btn_collapse.rect.x - btn_help_w - 6,
            self.btn_collapse.rect.y,
            btn_help_w,
            btn_collapse_h,
        )
        content_rect = pygame.Rect(self.rect.x, self.rect.y + self.header_h, self.rect.width, self.rect.height - self.header_h)
        for tab in self.tabs.values():
            if hasattr(tab, "resize"):
                tab.resize(content_rect)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.is_open:
            return False

        # Klik tombol Bantuan (?) & Tutup Panel
        if self.btn_help.handle_event(event):
            return True
        if self.btn_collapse.handle_event(event):
            return True
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            if hasattr(event, "pos") and self.btn_collapse.rect.collidepoint(event.pos):
                self.close()
                return True

        if self.show_glossary:
            if event.type == MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                if self.rect.collidepoint((mx, my)):
                    self.glossary_scroll_y = max(
                        0.0,
                        min(self.glossary_max_scroll, self.glossary_scroll_y - event.y * 28.0),
                    )
                    return True
            if hasattr(event, "pos") and self.rect.collidepoint(event.pos):
                return True
            return False

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
        header_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.header_h)
        draw_card(surface, header_rect, config.COLOR_HEADER_BG, border_color=None, border_radius=0)
        pygame.draw.line(surface, config.COLOR_INSPECTOR_BORDER,
                         (self.rect.x, header_rect.bottom - 1), (self.rect.right - 1, header_rect.bottom - 1), 1)

        title, subtitle = TAB_HEADERS[self.active_tab_id] if 0 <= self.active_tab_id < len(TAB_HEADERS) else ("INSPEKTOR AI", "Detail Modul")
        font_title = self.fonts.get("title", pygame.font.Font(None, 19))
        font_tiny = self.fonts.get("tiny", pygame.font.Font(None, 13))

        max_title_w = max(80, self.btn_help.rect.x - (self.rect.x + 14) - 8)
        t_surf = font_title.render(title, True, config.COLOR_ACCENT_GOLD)
        st_surf = font_tiny.render(subtitle, True, config.COLOR_TEXT_SECONDARY)
        tot_text_h = t_surf.get_height() + st_surf.get_height() + 2
        t_y = self.rect.y + max(4, (self.header_h - tot_text_h) // 2)
        render_fitted_text(surface, font_title, title, config.COLOR_ACCENT_GOLD, (self.rect.x + 14, t_y), max_title_w)
        render_fitted_text(surface, font_tiny, subtitle, config.COLOR_TEXT_SECONDARY, (self.rect.x + 14, t_y + t_surf.get_height() + 2), max_title_w)

        # Tombol Bantuan (?) & Lipat
        if self.show_glossary:
            self.btn_help.bg_color = config.COLOR_ACCENT_GOLD
            self.btn_help.text_color = (255, 255, 255)
        else:
            self.btn_help.bg_color = (252, 243, 218)
            self.btn_help.text_color = config.COLOR_TEXT_PRIMARY
        self.btn_help.draw(surface)
        self.btn_collapse.draw(surface)

        # 3. Gambar Konten Tab Aktif (atau Glosarium ?) dengan proteksi batas kliping
        content_rect = pygame.Rect(self.rect.x, self.rect.y + self.header_h, self.rect.width, self.rect.height - self.header_h)
        orig_clip = surface.get_clip()
        surface.set_clip(content_rect)
        active_tab = self.tabs.get(self.active_tab_id)
        if self.show_glossary:
            self.glossary_max_scroll = draw_tab_glossary(
                surface, content_rect, self.active_tab_id, self.fonts, self.glossary_scroll_y
            )
            self.glossary_scroll_y = max(0.0, min(self.glossary_max_scroll, self.glossary_scroll_y))
        elif active_tab:
            active_tab.draw(surface)
        surface.set_clip(orig_clip)
        if not self.show_glossary and active_tab:
            active_tab.draw_popups(surface)
