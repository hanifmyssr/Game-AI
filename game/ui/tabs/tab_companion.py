"""Tab 0: Hero Companion & Inventory (Cozy Adventurer Journal Theme).

Menampilkan status Bolu, inventaris peti harta dengan sprite pixel art, dan kontrol game.
"""

from typing import Dict, Any, Optional
import pygame
from ...core import config
from ..components import draw_card, draw_badge_pill, draw_metric_tile, UIButton

MOUSEMOTION = getattr(pygame, "MOUSEMOTION", 1024)
MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1025)


"""Tab 0: Hero Companion & Inventory (Cozy Adventurer Journal Theme).

Menampilkan status Bolu, inventaris peti harta dengan sprite pixel art, dan kontrol game.
"""

from typing import Dict, Any, Optional
import pygame
from ...core import config
from ..components import draw_card, draw_badge_pill, draw_metric_tile, UIButton

MOUSEMOTION = getattr(pygame, "MOUSEMOTION", 1024)
MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1025)
MOUSEWHEEL = getattr(pygame, "MOUSEWHEEL", 1027)


class TabCompanion:
    """Tab 0: Status Karakter & Inventaris Peti."""

    def __init__(self, rect: pygame.Rect, fonts: Dict[str, pygame.font.Font], app_ref: Any):
        self.rect = pygame.Rect(rect)
        self.fonts = fonts
        self.app = app_ref

        # State slider / scroll inventaris
        self.inv_scroll_idx: int = 0
        self.inv_rect = pygame.Rect(0, 0, 0, 0)

        f_tiny = fonts.get("tiny", pygame.font.Font(None, 13))

        # Tombol Navigasi Slide Tas Inventaris [<] dan [>]
        self.btn_inv_prev = UIButton(
            pygame.Rect(0, 0, 24, 22),
            "<",
            f_tiny,
            on_click=self._on_inv_prev,
            bg_color=(246, 240, 230),
            hover_color=(255, 252, 245),
            active_color=(235, 225, 210),
            border_color=(215, 198, 175),
        )
        self.btn_inv_next = UIButton(
            pygame.Rect(0, 0, 24, 22),
            ">",
            f_tiny,
            on_click=self._on_inv_next,
            bg_color=(246, 240, 230),
            hover_color=(255, 252, 245),
            active_color=(235, 225, 210),
            border_color=(215, 198, 175),
        )

        btn_w = self.rect.width - 24
        self.btn_call = UIButton(
            pygame.Rect(self.rect.x + 12, self.rect.y + 540, btn_w, 38),
            "Panggil NPC Pengejar [SPACE]",
            fonts.get("sm", pygame.font.Font(None, 16)),
            on_click=self._on_call_chaser,
            bg_color=(242, 235, 222),
            hover_color=(255, 252, 245),
            active_color=(230, 220, 205),
            border_color=config.COLOR_CARD_BORDER,
        )

    def _on_inv_prev(self) -> None:
        if self.inv_scroll_idx > 0:
            self.inv_scroll_idx -= 1

    def _on_inv_next(self) -> None:
        self.inv_scroll_idx += 1

    def resize(self, rect: pygame.Rect) -> None:
        self.rect = pygame.Rect(rect)
        cx = self.rect.x + 12
        card_w = self.rect.width - 24
        inv_y = self.rect.y + 12 + 115 + 12 + 46 + 12
        self.inv_rect = pygame.Rect(cx, inv_y, card_w, 144)
        btn_next_x = cx + card_w - 32
        btn_prev_x = btn_next_x - 28
        self.btn_inv_prev.rect = pygame.Rect(btn_prev_x, inv_y + 6, 24, 22)
        self.btn_inv_next.rect = pygame.Rect(btn_next_x, inv_y + 6, 24, 22)

    def _on_call_chaser(self) -> None:
        if hasattr(self.app, "_trigger_chase"):
            self.app._trigger_chase()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.btn_call.handle_event(event):
            return True
        if self.btn_inv_prev.handle_event(event):
            return True
        if self.btn_inv_next.handle_event(event):
            return True

        # Dukungan Scroll MouseWheel untuk Slide Tas Inventaris
        if event.type == MOUSEWHEEL:
            mouse_pos = getattr(pygame.mouse, "get_pos", lambda: (0, 0))()
            if self.inv_rect.collidepoint(mouse_pos):
                if event.y < 0 or getattr(event, "x", 0) > 0:
                    self._on_inv_next()
                    return True
                elif event.y > 0 or getattr(event, "x", 0) < 0:
                    self._on_inv_prev()
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

        # 1. KARTU PROFIL BOLU
        hero_card_h = 115
        hero_rect = pygame.Rect(cx, cy, card_w, hero_card_h)
        draw_card(surface, hero_rect, config.COLOR_CARD_BG, border_color=config.COLOR_CARD_BORDER, border_radius=8)

        # Nama & Role Badge
        title_surf = font_title.render("Bolu", True, config.COLOR_TEXT_PRIMARY)
        surface.blit(title_surf, (cx + 14, cy + 10))

        role_badge = pygame.Rect(cx + 66, cy + 12, 105, 22)
        draw_badge_pill(surface, role_badge, "Hero Petualang", (244, 236, 224), config.COLOR_TEXT_SECONDARY, font_tiny)

        # Status HP Bar
        hp = getattr(self.app.player, "persistent_hp", config.MAX_HP)
        max_hp = config.MAX_HP
        hp_ratio = max(0.0, min(1.0, hp / float(max_hp)))

        hp_lbl = font_tiny.render(f"HP: {hp} / {max_hp}", True, config.COLOR_TEXT_PRIMARY)
        surface.blit(hp_lbl, (cx + 14, cy + 40))

        bar_rect = pygame.Rect(cx + 14, cy + 58, card_w - 28, 14)
        pygame.draw.rect(surface, (232, 224, 212), bar_rect, border_radius=7)
        fill_w = int(round(bar_rect.width * hp_ratio))
        if fill_w > 0:
            fill_color = config.COLOR_STATUS_SUCCESS if hp_ratio > 0.4 else config.COLOR_STATUS_DANGER
            pygame.draw.rect(surface, fill_color, pygame.Rect(bar_rect.x, bar_rect.y, fill_w, bar_rect.height), border_radius=7)
        pygame.draw.rect(surface, (195, 182, 165), bar_rect, width=1, border_radius=7)

        # Potions & Koordinat (Bebas missing glyph / tofu emoji)
        potions = getattr(self.app.player, "persistent_potions", 0)
        grid_pos = getattr(self.app.player, "grid", (0, 0))
        sub_info = f"Ramuan: {potions}x   |   Posisi: ({grid_pos[0]}, {grid_pos[1]})"
        sub_surf = font_tiny.render(sub_info, True, config.COLOR_TEXT_SECONDARY)
        surface.blit(sub_surf, (cx + 14, cy + 82))

        # 2. METRIK DUNIA EKSPORASI
        cy += hero_card_h + 12
        tile_w = (card_w - 10) // 2
        tile_h = 46

        opened_chests = sum(1 for c in getattr(self.app, "chests", []) if c.get("opened", False))
        total_chests = len(getattr(self.app, "chests", []))
        chickens_count = len(getattr(self.app, "chicken_entities", []))

        draw_metric_tile(surface, pygame.Rect(cx, cy, tile_w, tile_h),
                         "Peti Dibuka", f"{opened_chests} / {total_chests}",
                         val_color=config.COLOR_ACCENT_GOLD,
                         font_lbl=font_tiny, font_val=font_sm)

        draw_metric_tile(surface, pygame.Rect(cx + tile_w + 10, cy, tile_w, tile_h),
                         "Ayam Roaming", f"{chickens_count} Ekor",
                         val_color=config.COLOR_ACCENT_BLUE,
                         font_lbl=font_tiny, font_val=font_sm)

        # 3. KARTU TAS INVENTARIS (SLIDABLE / SCROLLABLE)
        cy += tile_h + 12
        inv_h = 144
        self.inv_rect = pygame.Rect(cx, cy, card_w, inv_h)
        draw_card(surface, self.inv_rect, config.COLOR_CARD_BG, border_color=config.COLOR_CARD_BORDER, border_radius=8)

        inventory = getattr(self.app.player, "inventory", [])
        item_imgs = getattr(self.app, "item_images", {}) or {}
        potions = getattr(self.app.player, "persistent_potions", 0)

        def has_any(keywords):
            return any(any(kw in str(x).lower() for kw in keywords) for x in inventory)

        # Definisi semua item dalam game (Mendukung hasil pembukaan Peti Harta maupun Rampasan Perang NPC)
        items_def = [
            (
                "Pedang Oyen" if has_any(["oyen"]) else "Pedang",
                "item_sword",
                "ATK",
                "+4 ATK +DEF" if has_any(["oyen"]) else "+5 ATK",
                has_any(["sword", "pedang", "oyen"]),
            ),
            (
                "Perisai",
                "item_shield",
                "DEF",
                "+3 DEF",
                has_any(["shield", "perisai"]),
            ),
            (
                "Ramuan",
                "health_potion",
                "POT",
                f"x{potions} (+25)" if potions > 0 else "+25 HP",
                has_any(["health_potion", "ramuan", "potion"]) or potions > 0,
            ),
            (
                "Tongkat Shiro" if has_any(["shiro", "tongkat"]) else "Mega Pot",
                "mega_potion",
                "MAG" if has_any(["shiro", "tongkat"]) else "M.POT",
                "+3 ATK +DEF" if has_any(["shiro", "tongkat"]) else "+50 HP",
                has_any(["mega_potion", "shiro", "tongkat", "sihir"]),
            ),
            (
                "Boots",
                "item_boots",
                "SPD",
                "+Lincah",
                has_any(["boots", "sepatu"]),
            ),
            (
                "Busur Kuro" if has_any(["kuro"]) else "Busur",
                "item_bow",
                "RNG",
                "+3 ATK +Pot" if has_any(["kuro"]) else "+4 ATK",
                has_any(["bow", "busur", "kuro"]),
            ),
            (
                "Belati Kage" if has_any(["kage"]) else "Belati",
                "item_dagger",
                "DAG",
                "+5 ATK Crit" if has_any(["kage"]) else "+Crit",
                has_any(["dagger", "belati", "kage"]),
            ),
        ]

        visible_count = 3
        max_scroll = max(0, len(items_def) - visible_count)
        self.inv_scroll_idx = max(0, min(self.inv_scroll_idx, max_scroll))

        # Header Inventaris & Tombol Slide [◀] [▶]
        acquired_count = sum(1 for it in items_def if it[4])
        inv_title = font_sm.render(f"Tas Inventaris ({acquired_count}/{len(items_def)})", True, config.COLOR_TEXT_PRIMARY)
        surface.blit(inv_title, (cx + 14, cy + 8))

        # Posisi tombol slide di kanan atas kartu
        btn_next_x = cx + card_w - 32
        btn_prev_x = btn_next_x - 28
        self.btn_inv_prev.rect = pygame.Rect(btn_prev_x, cy + 6, 24, 22)
        self.btn_inv_next.rect = pygame.Rect(btn_next_x, cy + 6, 24, 22)
        self.btn_inv_prev.draw(surface)
        self.btn_inv_next.draw(surface)

        slot_w = (card_w - 32) // visible_count
        slot_h = 80
        slot_y = cy + 34

        visible_items = items_def[self.inv_scroll_idx : self.inv_scroll_idx + visible_count]

        for i, (name, img_key, fallback_code, buff, acquired) in enumerate(visible_items):
            sx = cx + 12 + i * (slot_w + 4)
            s_rect = pygame.Rect(sx, slot_y, slot_w, slot_h)
            s_bg = (248, 242, 230) if acquired else (244, 240, 234)
            s_bd = config.COLOR_ACCENT_GOLD if acquired else (222, 212, 198)
            draw_card(surface, s_rect, s_bg, border_color=s_bd, border_radius=6)

            drawn_sprite = False
            if img_key in item_imgs and item_imgs[img_key]:
                raw_img = item_imgs[img_key]
                scaled_item = pygame.transform.scale(raw_img, (26, 26))
                if not acquired:
                    scaled_item.set_alpha(75)
                surface.blit(scaled_item, (s_rect.centerx - 13, s_rect.y + 6))
                drawn_sprite = True

            if not drawn_sprite:
                ic_surf = font_title.render(f"[{fallback_code}]", True, config.COLOR_ACCENT_GOLD if acquired else config.COLOR_TEXT_MUTED)
                surface.blit(ic_surf, (s_rect.centerx - ic_surf.get_width() // 2, s_rect.y + 8))

            nm_surf = font_tiny.render(name, True, config.COLOR_TEXT_PRIMARY if acquired else config.COLOR_TEXT_MUTED)
            surface.blit(nm_surf, (s_rect.centerx - nm_surf.get_width() // 2, s_rect.y + 35))

            bf_surf = font_tiny.render(buff, True, config.COLOR_STATUS_SUCCESS if acquired else config.COLOR_TEXT_MUTED)
            surface.blit(bf_surf, (s_rect.centerx - bf_surf.get_width() // 2, s_rect.y + 55))

        # Indikator Titik Halaman / Slide di Dasar Kartu
        dot_y = slot_y + slot_h + 10
        total_pages = max_scroll + 1
        dot_gap = 8
        dot_radius = 3
        total_dots_w = total_pages * (dot_radius * 2) + (total_pages - 1) * dot_gap
        dot_start_x = cx + (card_w - total_dots_w) // 2

        for p in range(total_pages):
            dx = dot_start_x + p * (dot_radius * 2 + dot_gap) + dot_radius
            col = config.COLOR_ACCENT_GOLD if p == self.inv_scroll_idx else (210, 198, 180)
            pygame.draw.circle(surface, col, (dx, dot_y), dot_radius)

        # 4. PANDUAN KONTROL CEPAT
        cy += inv_h + 12
        guide_h = 145
        guide_rect = pygame.Rect(cx, cy, card_w, guide_h)
        draw_card(surface, guide_rect, config.COLOR_CARD_BG, border_color=config.COLOR_CARD_BORDER, border_radius=8)

        gd_title = font_sm.render("Petunjuk Kontrol", True, config.COLOR_TEXT_PRIMARY)
        surface.blit(gd_title, (cx + 14, cy + 8))

        keys_info = [
            ("W A S D / Arrow", "Gerak Karakter Bolu"),
            ("[E] / Dekati Peti", "Buka Peti & Gacha Buff"),
            ("[SPACE]", "Panggil NPC Bolu ke posisi"),
            ("[Tab]", "Buka / Tutup Panel Inspektur"),
            ("[T]", "Buka Visualizer Pohon AI"),
        ]

        for idx, (k_btn, k_desc) in enumerate(keys_info):
            ky = cy + 32 + idx * 21
            kb_surf = font_tiny.render(k_btn, True, config.COLOR_ACCENT_GOLD)
            kd_surf = font_tiny.render(f": {k_desc}", True, config.COLOR_TEXT_PRIMARY)
            surface.blit(kb_surf, (cx + 14, ky))
            surface.blit(kd_surf, (cx + 14 + kb_surf.get_width(), ky))

        cy += guide_h + 12
        self.btn_call.rect = pygame.Rect(cx, cy, card_w, 38)
        self.btn_call.draw(surface)

    def draw_popups(self, surface: pygame.Surface) -> None:
        pass
