"""Web-Style Nav Rail bernuansa Kayu Walnut Gelap (Dark Walnut Wood).

Kolom vertikal selebar 64px di sisi paling kiri (x: 0..64)
Menyediakan akses instan dan penanda tab materi AI (Materi 01 s.d. 08).
"""

from typing import Callable, List, Optional, Tuple, Dict
import pygame
from ..core import config
from .components import draw_card

MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1025)
MOUSEMOTION = getattr(pygame, "MOUSEMOTION", 1024)


class NavTabItem:
    """Satu entri tombol tab di dalam Nav Rail."""

    def __init__(self, tab_id: int, label: str, glyph: str, short_code: str, tooltip: str):
        self.tab_id = tab_id
        self.label = label
        self.glyph = glyph
        self.short_code = short_code
        self.tooltip = tooltip
        self.has_badge = False
        self.badge_color = config.COLOR_STATUS_DANGER


class NavRail:
    """Bilah navigasi vertikal ala web di sisi kiri layar (lebar 64px)."""

    def __init__(self, rect: pygame.Rect,
                 on_tab_changed: Optional[Callable[[int], None]] = None,
                 on_tab_toggled: Optional[Callable[[int], None]] = None):
        self.rect = pygame.Rect(rect)
        self.on_tab_changed = on_tab_changed
        self.on_tab_toggled = on_tab_toggled
        self.active_tab = 0
        self.hovered_tab = -1
        self.tabs: List[NavTabItem] = [
            NavTabItem(0, "Hero", "★", "HR", "Status Hero & Inventaris (Game)"),
            NavTabItem(1, "Search", "🔍", "SR", "Materi 01-03: Pathfinding (A*, UCS, Greedy)"),
            NavTabItem(2, "Minimax", "⚔", "MX", "Materi 04: Adversarial Search (Minimax AI)"),
            NavTabItem(3, "CSP-LS", "⚖", "CP", "Materi 05-06: CSP & Local Search Skuad"),
            NavTabItem(4, "Logic", "🧠", "KB", "Materi 07: Logic & Knowledge Base (TELL->ASK)"),
            NavTabItem(5, "Planning", "📋", "PL", "Materi 08: Automated Planning (PDDL)"),
            NavTabItem(6, "Settings", "⚙", "CF", "Pengaturan Game & Audio"),
        ]

        try:
            self.font_glyph = pygame.font.SysFont(["segoeuisymbol", "segoeui", "arial"], 19, bold=True)
            self.font_code = pygame.font.SysFont(["consolas", "segoeui", "arial"], 12, bold=True)
            self.font_tooltip = pygame.font.SysFont(["segoeui", "arial"], 13)
            self.font_badge = pygame.font.SysFont(["arial", "segoeui"], 10, bold=True)
        except Exception:
            self.font_glyph = pygame.font.Font(None, 22)
            self.font_code = pygame.font.Font(None, 14)
            self.font_tooltip = pygame.font.Font(None, 14)
            self.font_badge = pygame.font.Font(None, 11)

        self.item_rects: Dict[int, pygame.Rect] = {}
        self._recompute_item_rects()

    def resize(self, height: int) -> None:
        """Memperbarui tinggi Nav Rail mengikuti ukuran window / fullscreen."""
        self.rect.height = height
        self._recompute_item_rects()

    def _recompute_item_rects(self) -> None:
        btn_size = 46
        pad_x = (self.rect.width - btn_size) // 2
        start_y = 16
        spacing = 54

        for item in self.tabs:
            if item.tab_id == 6:
                y = self.rect.bottom - btn_size - 16
            else:
                y = start_y + item.tab_id * spacing
            self.item_rects[item.tab_id] = pygame.Rect(self.rect.x + pad_x, y, btn_size, btn_size)

    def set_badge(self, tab_id: int, active: bool = True, color: Tuple = config.COLOR_STATUS_DANGER) -> None:
        for item in self.tabs:
            if item.tab_id == tab_id:
                item.has_badge = active
                item.badge_color = color
                break

    def set_active_tab(self, tab_id: int) -> None:
        if 0 <= tab_id < len(self.tabs):
            self.active_tab = tab_id
            if self.on_tab_changed:
                self.on_tab_changed(tab_id)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == MOUSEMOTION:
            prev_hover = self.hovered_tab
            self.hovered_tab = -1
            for tab_id, btn_rect in self.item_rects.items():
                if btn_rect.collidepoint(event.pos):
                    self.hovered_tab = tab_id
                    break
            return self.hovered_tab != prev_hover

        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            for tab_id, btn_rect in self.item_rects.items():
                if btn_rect.collidepoint(event.pos):
                    if tab_id == self.active_tab:
                        if self.on_tab_toggled:
                            self.on_tab_toggled(tab_id)
                        else:
                            self.set_active_tab(tab_id)
                    else:
                        self.set_active_tab(tab_id)
                    return True
            if self.rect.collidepoint(event.pos):
                return True

        return False

    def draw(self, surface: pygame.Surface) -> None:
        # 1. Latar Belakang Nav Rail (Kayu Walnut Gelap)
        draw_card(surface, self.rect, config.COLOR_NAV_BG, border_color=None, border_radius=0)
        # Garis pembatas vertikal di kanan rail
        pygame.draw.line(surface, config.COLOR_NAV_BORDER,
                         (self.rect.right - 1, self.rect.y), (self.rect.right - 1, self.rect.bottom), 1)

        # Garis pemisah sebelum tab Settings di bawah
        sep_y = self.rect.bottom - 72
        pygame.draw.line(surface, (68, 52, 38), (self.rect.x + 10, sep_y), (self.rect.right - 10, sep_y), 1)

        # 2. Gambar tiap tombol item
        tooltip_to_draw = None

        for item in self.tabs:
            btn_rect = self.item_rects[item.tab_id]
            is_active = (item.tab_id == self.active_tab)
            is_hover = (item.tab_id == self.hovered_tab)

            if is_active:
                bg = (72, 55, 40)
                bd = config.COLOR_NAV_ACCENT
            elif is_hover:
                bg = config.COLOR_NAV_HOVER
                bd = (110, 85, 62)
            else:
                bg = (38, 28, 20)
                bd = (58, 44, 32)

            draw_card(surface, btn_rect, bg, border_color=bd, border_radius=8)

            # Indikator aktif: Garis aksen emas di sisi paling kiri
            if is_active:
                accent_rect = pygame.Rect(self.rect.x, btn_rect.y + 7, 4, btn_rect.height - 14)
                pygame.draw.rect(surface, config.COLOR_NAV_ACCENT, accent_rect, border_radius=2)

            # Render Icon Glyph atau Huruf Kode
            icon_color = config.COLOR_NAV_ACCENT if is_active else ((255, 255, 255) if is_hover else (195, 178, 160))
            try:
                g_surf = self.font_glyph.render(item.glyph, True, icon_color)
                if g_surf.get_width() < 5:
                    g_surf = self.font_code.render(item.short_code, True, icon_color)
            except Exception:
                g_surf = self.font_code.render(item.short_code, True, icon_color)

            gx = btn_rect.centerx - g_surf.get_width() // 2
            gy = btn_rect.centery - g_surf.get_height() // 2
            surface.blit(g_surf, (gx, gy))

            if item.has_badge:
                badge_radius = 6
                bx = btn_rect.right - 4
                by = btn_rect.y + 4
                pygame.draw.circle(surface, item.badge_color, (bx, by), badge_radius)
                pygame.draw.circle(surface, (255, 255, 255), (bx, by), badge_radius, 1)
                b_txt = self.font_badge.render("!", True, (255, 255, 255))
                surface.blit(b_txt, (bx - b_txt.get_width() // 2, by - b_txt.get_height() // 2))

            if is_hover:
                tooltip_to_draw = (btn_rect, item.tooltip)

        if tooltip_to_draw:
            target_rect, tt_text = tooltip_to_draw
            tt_surf = self.font_tooltip.render(tt_text, True, (255, 255, 255))
            tt_box = pygame.Rect(self.rect.right + 8, target_rect.centery - 13, tt_surf.get_width() + 16, 26)
            draw_card(surface, tt_box, (46, 35, 25), border_color=config.COLOR_NAV_ACCENT, border_radius=4)
            surface.blit(tt_surf, (tt_box.x + 8, tt_box.y + 4))
