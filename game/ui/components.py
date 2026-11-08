"""Komponen UI Modular untuk Cozy Adventurer Journal.

Primitif antarmuka bernuansa hangat (Warm Parchment & Dark Walnut RPG):
- UIButton: Tombol interaktif dengan hover & click state.
- UIDropdown: Menu pilihan drop-down dengan menu layer terpisah.
- UISlider: Penggeser nilai numerik (volume, difficulty, dll).
- UIScrollArea: Kontainer dengan scrollbar vertikal & mouse-wheel support.
- Helper rendering kartu, pill badge, dan metric tile.
"""

from typing import Callable, List, Optional, Tuple, Any
import pygame
from ..core import config

MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1025)
MOUSEBUTTONUP = getattr(pygame, "MOUSEBUTTONUP", 1026)
MOUSEMOTION = getattr(pygame, "MOUSEMOTION", 1024)
MOUSEWHEEL = getattr(pygame, "MOUSEWHEEL", 1027)
SRCALPHA = getattr(pygame, "SRCALPHA", 0x00010000)


def fit_text_to_width(font: pygame.font.Font, text: str, max_width: int, ellipsis: str = "...") -> str:
    """Memotong teks dengan elipsis jika lebarnya melebihi batas max_width."""
    if not text or max_width <= 0:
        return ""
    if font.size(text)[0] <= max_width:
        return text
    ell_w = font.size(ellipsis)[0]
    if ell_w >= max_width:
        return text[:1]
    low, high = 1, len(text)
    best = ""
    while low <= high:
        mid = (low + high) // 2
        cand = text[:mid] + ellipsis
        if font.size(cand)[0] <= max_width:
            best = cand
            low = mid + 1
        else:
            high = mid - 1
    return best if best else ellipsis


def render_fitted_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    color: Any,
    pos: Tuple[int, int],
    max_width: int,
    ellipsis: str = "...",
) -> pygame.Rect:
    """Merender teks yang telah dipastikan pas dalam max_width ke permukaan target."""
    fitted = fit_text_to_width(font, text, max_width, ellipsis)
    surf = font.render(fitted, True, color)
    return surface.blit(surf, pos)


def draw_card(surface: pygame.Surface, rect: pygame.Rect, bg_color: Tuple,
              border_color: Optional[Tuple] = None, border_radius: int = 6,
              border_width: int = 1) -> None:
    """Menggambar kartu permukaan dengan border radius halus."""
    if len(bg_color) == 4 and bg_color[3] < 255:
        card_surf = pygame.Surface((rect.width, rect.height), SRCALPHA)
        pygame.draw.rect(card_surf, bg_color, card_surf.get_rect(), border_radius=border_radius)
        surface.blit(card_surf, (rect.x, rect.y))
    else:
        pygame.draw.rect(surface, bg_color[:3], rect, border_radius=border_radius)

    if border_color:
        pygame.draw.rect(surface, border_color[:3], rect, border_width, border_radius=border_radius)


def draw_badge_pill(surface: pygame.Surface, rect: pygame.Rect, text: str,
                    bg_color: Tuple, text_color: Tuple, font: pygame.font.Font,
                    border_color: Optional[Tuple] = None) -> None:
    """Menggambar badge lonjong/pill untuk label status."""
    radius = rect.height // 2
    draw_card(surface, rect, bg_color, border_color=border_color, border_radius=radius)
    txt_surf = font.render(text, True, text_color)
    tx = rect.centerx - txt_surf.get_width() // 2
    ty = rect.centery - txt_surf.get_height() // 2
    surface.blit(txt_surf, (tx, ty))


def draw_metric_tile(surface: pygame.Surface, rect: pygame.Rect, label: str, value: str,
                     val_color: Optional[Tuple] = None, font_lbl: Optional[pygame.font.Font] = None,
                     font_val: Optional[pygame.font.Font] = None, bg_color: Optional[Tuple] = None,
                     border_color: Optional[Tuple] = None) -> None:
    """Menggambar satu kotak metrik (label atas, nilai bawah) dengan perlindungan clipping."""
    if val_color is None:
        val_color = config.COLOR_TEXT_PRIMARY
    if bg_color is None:
        bg_color = (255, 255, 255)
    if border_color is None:
        border_color = config.COLOR_CARD_BORDER

    draw_card(surface, rect, bg_color, border_color=border_color, border_radius=6)
    old_clip = surface.get_clip()
    surface.set_clip(rect)
    if font_lbl:
        lbl_surf = font_lbl.render(str(label), True, config.COLOR_TEXT_SECONDARY)
        surface.blit(lbl_surf, (rect.x + 8, rect.y + 3))
    if font_val:
        val_surf = font_val.render(str(value), True, val_color)
        surface.blit(val_surf, (rect.x + 8, rect.y + 19))
    surface.set_clip(old_clip)


class UIButton:
    """Tombol serbaguna bernuansa jurnal RPG."""

    def __init__(self, rect: pygame.Rect, text: str, font: pygame.font.Font,
                 on_click: Optional[Callable[[], None]] = None,
                 bg_color: Tuple = (246, 240, 230),
                 hover_color: Tuple = (255, 253, 248),
                 active_color: Tuple = (235, 226, 212),
                 text_color: Tuple = config.COLOR_TEXT_PRIMARY,
                 border_color: Tuple = config.COLOR_CARD_BORDER,
                 border_radius: int = 6,
                 icon: Optional[str] = None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.on_click = on_click
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.active_color = active_color
        self.text_color = text_color
        self.border_color = border_color
        self.border_radius = border_radius
        self.icon = icon
        self.is_hovered = False
        self.is_pressed = False
        self.enabled = True

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.enabled:
            return False

        if event.type == MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
            return False

        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.is_pressed = True
                return True

        if event.type == MOUSEBUTTONUP and event.button == 1:
            if self.is_pressed:
                self.is_pressed = False
                if self.rect.collidepoint(event.pos):
                    if self.on_click:
                        self.on_click()
                    return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        if not self.enabled:
            bg = (230, 224, 215)
            txt_c = config.COLOR_TEXT_MUTED
            bd = (210, 202, 192)
        elif self.is_pressed:
            bg = self.active_color
            txt_c = self.text_color
            bd = config.COLOR_ACCENT_GOLD
        elif self.is_hovered:
            bg = self.hover_color
            txt_c = (15, 10, 5)
            bd = config.COLOR_ACCENT_GOLD
        else:
            bg = self.bg_color
            txt_c = self.text_color
            bd = self.border_color

        draw_card(surface, self.rect, bg, border_color=bd, border_radius=self.border_radius)

        display_text = f"{self.icon} {self.text}" if self.icon else self.text
        txt_surf = self.font.render(display_text, True, txt_c)
        tx = self.rect.centerx - txt_surf.get_width() // 2
        ty = self.rect.centery - txt_surf.get_height() // 2
        surface.blit(txt_surf, (tx, ty))


class UIDropdown:
    """Menu Dropdown kertas perkamen modern."""

    def __init__(self, rect: pygame.Rect, options: List[Tuple[str, str]],
                 on_select: Optional[Callable[[int, str], None]] = None,
                 initial_idx: int = 0, font: Optional[pygame.font.Font] = None):
        self.rect = pygame.Rect(rect)
        self.options = options
        self.selected_index = max(0, min(initial_idx, len(options) - 1)) if options else 0
        self.on_select = on_select
        self.font = font or pygame.font.Font(None, 14)
        self.is_open = False
        self.hover_index = -1
        self.item_height = max(self.rect.height, 30)

    @property
    def selected_key(self) -> str:
        if 0 <= self.selected_index < len(self.options):
            return self.options[self.selected_index][0]
        return ""

    @property
    def selected_label(self) -> str:
        if 0 <= self.selected_index < len(self.options):
            return self.options[self.selected_index][1]
        return ""

    def set_selected_by_key(self, key: str) -> None:
        for i, (k, _) in enumerate(self.options):
            if k == key:
                self.selected_index = i
                break

    def menu_rect(self) -> pygame.Rect:
        h = self.item_height * len(self.options)
        return pygame.Rect(self.rect.x, self.rect.bottom + 2, self.rect.width, h)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            if self.is_open:
                m_rect = self.menu_rect()
                if m_rect.collidepoint(event.pos):
                    idx = (event.pos[1] - m_rect.y) // self.item_height
                    if 0 <= idx < len(self.options):
                        self.selected_index = idx
                        self.is_open = False
                        if self.on_select:
                            self.on_select(idx, self.options[idx][0])
                        return True
                self.is_open = False
                return True

            if self.rect.collidepoint(event.pos):
                self.is_open = True
                return True

        elif event.type == MOUSEMOTION and self.is_open:
            m_rect = self.menu_rect()
            if m_rect.collidepoint(event.pos):
                self.hover_index = (event.pos[1] - m_rect.y) // self.item_height
            else:
                self.hover_index = -1

        return False

    def draw(self, surface: pygame.Surface) -> None:
        is_hover = self.rect.collidepoint(pygame.mouse.get_pos())
        bg = (255, 255, 255) if (is_hover or self.is_open) else (252, 248, 242)
        border = config.COLOR_ACCENT_GOLD if self.is_open else config.COLOR_CARD_BORDER
        draw_card(surface, self.rect, bg, border_color=border, border_radius=6)

        lbl = self.selected_label
        txt_surf = self.font.render(lbl, True, config.COLOR_TEXT_PRIMARY)
        old_clip = surface.get_clip()
        surface.set_clip(pygame.Rect(self.rect.x + 8, self.rect.y, self.rect.width - 26, self.rect.height))
        surface.blit(txt_surf, (self.rect.x + 8, self.rect.centery - txt_surf.get_height() // 2))
        surface.set_clip(old_clip)

        arrow = "▲" if self.is_open else "▼"
        arrow_surf = self.font.render(arrow, True, config.COLOR_ACCENT_GOLD if self.is_open else config.COLOR_TEXT_SECONDARY)
        surface.blit(arrow_surf, (self.rect.right - 18, self.rect.centery - arrow_surf.get_height() // 2))

    def draw_menu(self, surface: pygame.Surface) -> None:
        if not self.is_open or not self.options:
            return

        m_rect = self.menu_rect()
        draw_card(surface, m_rect, (255, 255, 255), border_color=config.COLOR_ACCENT_GOLD, border_radius=6)

        for i, (_, label) in enumerate(self.options):
            item_rect = pygame.Rect(m_rect.x, m_rect.y + i * self.item_height, m_rect.width, self.item_height)
            if i == self.selected_index:
                pygame.draw.rect(surface, (244, 236, 222), item_rect, border_radius=4)
                pygame.draw.rect(surface, config.COLOR_ACCENT_GOLD, (item_rect.x + 2, item_rect.y + 4, 3, item_rect.height - 8))
            elif i == self.hover_index:
                pygame.draw.rect(surface, (250, 246, 238), item_rect, border_radius=4)

            c = config.COLOR_ACCENT_GOLD if i == self.selected_index else config.COLOR_TEXT_PRIMARY
            txt = self.font.render(label, True, c)
            surface.blit(txt, (item_rect.x + 12, item_rect.centery - txt.get_height() // 2))

            if i < len(self.options) - 1:
                pygame.draw.line(surface, (235, 225, 212), (item_rect.x + 6, item_rect.bottom),
                                 (item_rect.right - 6, item_rect.bottom))


class UISlider:
    """Slider horizontal perkamen interaktif."""

    def __init__(self, rect: pygame.Rect, min_val: float, max_val: float, initial_val: float,
                 label: str = "", format_str: str = "{:.2f}",
                 on_change: Optional[Callable[[float], None]] = None,
                 font: Optional[pygame.font.Font] = None):
        self.rect = pygame.Rect(rect)
        self.min_val = min_val
        self.max_val = max_val
        self.value = max(min_val, min(initial_val, max_val))
        self.label = label
        self.format_str = format_str
        self.on_change = on_change
        self.font = font or pygame.font.Font(None, 14)
        self.is_dragging = False

    @property
    def track_rect(self) -> pygame.Rect:
        return pygame.Rect(self.rect.x, self.rect.y + 20, self.rect.width, 6)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            t_rect = self.track_rect.inflate(12, 16)
            if t_rect.collidepoint(event.pos):
                self.is_dragging = True
                self._update_val_from_mouse(event.pos[0])
                return True

        elif event.type == MOUSEBUTTONUP and event.button == 1:
            if self.is_dragging:
                self.is_dragging = False
                return True

        elif event.type == MOUSEMOTION and self.is_dragging:
            self._update_val_from_mouse(event.pos[0])
            return True

        return False

    def _update_val_from_mouse(self, mouse_x: int) -> None:
        tr = self.track_rect
        ratio = max(0.0, min(1.0, (mouse_x - tr.x) / float(tr.width)))
        new_val = self.min_val + ratio * (self.max_val - self.min_val)
        if abs(new_val - self.value) > 1e-4:
            self.value = new_val
            if self.on_change:
                self.on_change(self.value)

    def draw(self, surface: pygame.Surface) -> None:
        if self.label:
            lbl_surf = self.font.render(self.label, True, config.COLOR_TEXT_SECONDARY)
            surface.blit(lbl_surf, (self.rect.x, self.rect.y))

        val_str = self.format_str.format(self.value)
        val_surf = self.font.render(val_str, True, config.COLOR_ACCENT_GOLD)
        surface.blit(val_surf, (self.rect.right - val_surf.get_width(), self.rect.y))

        tr = self.track_rect
        pygame.draw.rect(surface, (222, 212, 198), tr, border_radius=3)

        ratio = (self.value - self.min_val) / max(1e-6, self.max_val - self.min_val)
        filled_w = int(round(tr.width * ratio))
        if filled_w > 0:
            filled_rect = pygame.Rect(tr.x, tr.y, filled_w, tr.height)
            pygame.draw.rect(surface, config.COLOR_ACCENT_GOLD, filled_rect, border_radius=3)

        knob_cx = tr.x + filled_w
        knob_cy = tr.centery
        knob_radius = 7 if self.is_dragging else 6
        pygame.draw.circle(surface, (255, 255, 255), (knob_cx, knob_cy), knob_radius)
        pygame.draw.circle(surface, config.COLOR_ACCENT_GOLD, (knob_cx, knob_cy), knob_radius, 2)


class UIScrollArea:
    """Kontainer area scroll vertikal dengan penanganan mouse-wheel & scrollbar."""

    def __init__(self, rect: pygame.Rect):
        self.rect = pygame.Rect(rect)
        self.content_height = rect.height
        self.scroll_y = 0.0
        self.is_dragging_bar = False
        self.drag_start_y = 0
        self.drag_start_scroll = 0.0

    @property
    def max_scroll(self) -> float:
        return max(0.0, float(self.content_height - self.rect.height))

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()
            if self.rect.collidepoint(mouse_pos):
                self.scroll_y = max(0.0, min(self.max_scroll, self.scroll_y - event.y * 24.0))
                return True

        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            bar_rect = self.scrollbar_thumb_rect()
            if bar_rect and bar_rect.collidepoint(event.pos):
                self.is_dragging_bar = True
                self.drag_start_y = event.pos[1]
                self.drag_start_scroll = self.scroll_y
                return True

        if event.type == MOUSEBUTTONUP and event.button == 1:
            if self.is_dragging_bar:
                self.is_dragging_bar = False
                return True

        if event.type == MOUSEMOTION and self.is_dragging_bar:
            dy = event.pos[1] - self.drag_start_y
            track_h = self.rect.height - 8
            ratio = dy / float(track_h)
            self.scroll_y = max(0.0, min(self.max_scroll, self.drag_start_scroll + ratio * self.max_scroll))
            return True

        return False

    def scrollbar_thumb_rect(self) -> Optional[pygame.Rect]:
        if self.max_scroll <= 0:
            return None
        visible_ratio = min(1.0, self.rect.height / float(self.content_height))
        thumb_h = max(20, int(self.rect.height * visible_ratio))
        track_h = self.rect.height - thumb_h
        scroll_ratio = self.scroll_y / self.max_scroll
        thumb_y = self.rect.y + int(scroll_ratio * track_h)
        return pygame.Rect(self.rect.right - 6, thumb_y, 4, thumb_h)

    def draw_scrollbar(self, surface: pygame.Surface) -> None:
        thumb = self.scrollbar_thumb_rect()
        if thumb:
            pygame.draw.rect(surface, (190, 178, 162), thumb, border_radius=2)
