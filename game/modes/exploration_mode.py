"""ExplorationModeMixin: Peta, foliage, ayam, peti & gacha, stealth, peluit, portal, dan HUD eksplorasi."""

import math
import os
import random
from typing import Optional, Dict, Any, List, Tuple
import pygame

from ..core import config
from ..ui.components import draw_card
from ..battle.npc_squad import NPCSquad
from ..ai.battle_ai import ACTION_ATTACK, ACTION_HEAVY, ACTION_DEFEND, ACTION_POTION
from ..ai.uncertainty import BayesianRelicSonar
from ..planning.domain_world_patrol import create_world_patrol_problem
from ..planning.domain_battle_tactics import create_battle_tactics_problem

SRCALPHA = getattr(pygame, "SRCALPHA", 0x00010000)


class ExplorationModeMixin:
    """Mixin method mode Eksplorasi untuk App."""

    def _load_visual_effects(self):
        try:
            biom_path = os.path.join(config.ASSET_DIR, "sprout", "Basic_Grass_Biom_things.png")
            biom_sheet = pygame.image.load(biom_path).convert_alpha()
            # Tree canopy: kanopi hijau 2x1 di kolom 1..2, baris 0 (16, 0, 32, 16)
            self.foliage_tree_canopy = biom_sheet.subsurface((16, 0, 32, 16))
            # Tree canopy pink: kanopi pink di kolom 3..4, baris 0 (48, 0, 32, 16)
            self.foliage_tree_canopy_pink = biom_sheet.subsurface((48, 0, 32, 16))
            # Tree canopy small: kanopi pohon ramping di kolom 0, baris 0 (0, 0, 16, 16)
            self.foliage_tree_small = biom_sheet.subsurface((0, 0, 16, 16))
            # Ambush: semak hijau di kolom 1, baris 3 (16, 48, 16, 16)
            self.foliage_ambush_green = biom_sheet.subsurface((16, 48, 16, 16))
            # Ambush: semak berry di kolom 0, baris 3 (0, 48, 16, 16)
            self.foliage_ambush_berry = biom_sheet.subsurface((0, 48, 16, 16))
            # Sunflower: kepala bunga matahari di kolom 8, baris 2 (128, 32, 16, 16)
            self.foliage_sunflower = biom_sheet.subsurface((128, 32, 16, 16))
            # Flower liar: ubin bunga di kolom 7, baris 3 (112, 48, 16, 16)
            self.foliage_flower = biom_sheet.subsurface((112, 48, 16, 16))
            # Flower kuning: ubin bunga kuning di kolom 6, baris 2 (96, 32, 16, 16)
            self.foliage_flower_yellow = biom_sheet.subsurface((96, 32, 16, 16))
        except Exception as e:
            self.foliage_tree_canopy = None
            self.foliage_tree_canopy_pink = None
            self.foliage_tree_small = None
            self.foliage_ambush_green = None
            self.foliage_ambush_berry = None
            self.foliage_sunflower = None
            self.foliage_flower = None
            self.foliage_flower_yellow = None

        try:
            grass_path = os.path.join(config.ASSET_DIR, "sprout", "Grass.png")
            grass_sheet = pygame.image.load(grass_path).convert_alpha()
            self.foliage_grass_flower1 = grass_sheet.subsurface((112, 80, 16, 16))
            self.foliage_grass_flower2 = grass_sheet.subsurface((112, 96, 16, 16))
            self.foliage_grass_tuft = grass_sheet.subsurface((144, 80, 16, 16))
        except Exception as e:
            self.foliage_grass_flower1 = None
            self.foliage_grass_flower2 = None
            self.foliage_grass_tuft = None

        # Ayam / Chicken Animation Frames
        try:
            ch_path = os.path.join(config.ASSET_DIR, "sprout", "Free Chicken Sprites.png")
            if not os.path.exists(ch_path):
                ch_path = os.path.join(config.ASSET_DIR, "Sprout Lands - Sprites - Basic pack", "Sprout Lands - Sprites - Basic pack", "Characters", "Free Chicken Sprites.png")
            ch_sheet = pygame.image.load(ch_path).convert_alpha()
            self.chicken_frames = [
                ch_sheet.subsurface((0, 0, 16, 16)),    # 0: idle 1
                ch_sheet.subsurface((16, 0, 16, 16)),   # 1: idle 2
                ch_sheet.subsurface((32, 0, 16, 16)),   # 2: walk 1
                ch_sheet.subsurface((48, 0, 16, 16)),   # 3: walk 2
                ch_sheet.subsurface((0, 16, 16, 16)),   # 4: peck 1
                ch_sheet.subsurface((16, 16, 16, 16)),  # 5: peck 2 (ground)
                ch_sheet.subsurface((32, 16, 16, 16)),  # 6: peck 3 (chew)
                ch_sheet.subsurface((48, 16, 16, 16)),  # 7: peck 4 (head up)
            ]
        except Exception as e:
            self.chicken_frames = []

        try:
            dust_path = os.path.join(config.ASSET_DIR, "sprout", "Dust_particles.png")
            dust_sheet = pygame.image.load(dust_path).convert_alpha()
            self.dust_frames = [dust_sheet.subsurface((i * 16, 0, 16, 16)) for i in range(4)]
        except Exception as e:
            self.dust_frames = []

        # Peti Harta (Chest _01.png)
        try:
            chest_path = os.path.join(config.ASSET_DIR, "Shining Fields_free_v1.1", "Shining Fields_free_v1.1", "Sprites", "Objects", "Chest _01.png")
            if not os.path.exists(chest_path):
                chest_path = os.path.join(config.ASSET_DIR, "tubes", "Chest.png")
            chest_sheet = pygame.image.load(chest_path).convert_alpha()
            self.chest_closed_surf = chest_sheet.subsurface((0, 0, 16, 16))
            self.chest_opened_surf = chest_sheet.subsurface((48, 0, 16, 16))
        except Exception as e:
            self.chest_closed_surf = None
            self.chest_opened_surf = None

        self._foliage_slice_cache = {}
        self._foliage_sheets = {}

    def _get_foliage_slice(self, src, ax, ay):
        cache_key = (src, ax, ay)
        if cache_key in self._foliage_slice_cache:
            return self._foliage_slice_cache[cache_key]
        sheet = self._foliage_sheets.get(src)
        if sheet is None:
            full_path = os.path.join(config.ASSET_DIR, src.replace("/", os.sep))
            if os.path.exists(full_path):
                try:
                    sheet = pygame.image.load(full_path).convert_alpha()
                    self._foliage_sheets[src] = sheet
                except Exception:
                    self._foliage_sheets[src] = False
            else:
                self._foliage_sheets[src] = False
        if sheet:
            px = ax * 16
            py = ay * 16
            if px + 16 <= sheet.get_width() and py + 16 <= sheet.get_height():
                surf = sheet.subsurface((px, py, 16, 16)).copy()
                # Jika berasal dari Grass.png Sprout Lands, ubah background hijau (192, 212, 112) menjadi transparan
                # agar hanya helai rumput, bunga, dan tanda rumput yang bergoyang di atas peta
                if "grass" in src.lower() and "biom" not in src.lower():
                    surf.set_colorkey((192, 212, 112))
                self._foliage_slice_cache[cache_key] = surf
                return surf
        return None

    def _refresh_scaled_foliage(self):
        zoom = self.camera.zoom
        self._scaled_foliage = {}
        if getattr(self, "foliage_tree_canopy", None):
            tw = max(1, int(round(32 * zoom)))
            th = max(1, int(round(16 * zoom)))
            self._scaled_foliage["tree"] = pygame.transform.scale(self.foliage_tree_canopy, (tw, th))
        if getattr(self, "foliage_tree_canopy_pink", None):
            tw = max(1, int(round(32 * zoom)))
            th = max(1, int(round(16 * zoom)))
            self._scaled_foliage["tree_pink"] = pygame.transform.scale(self.foliage_tree_canopy_pink, (tw, th))
        if getattr(self, "foliage_tree_small", None):
            sw = max(1, int(round(16 * zoom)))
            sh = max(1, int(round(16 * zoom)))
            self._scaled_foliage["tree_small"] = pygame.transform.scale(self.foliage_tree_small, (sw, sh))
        if getattr(self, "foliage_ambush_green", None):
            bw = max(1, int(round(16 * zoom)))
            bh = max(1, int(round(16 * zoom)))
            self._scaled_foliage["ambush_green"] = pygame.transform.scale(self.foliage_ambush_green, (bw, bh))
        if getattr(self, "foliage_ambush_berry", None):
            bw = max(1, int(round(16 * zoom)))
            bh = max(1, int(round(16 * zoom)))
            self._scaled_foliage["ambush_berry"] = pygame.transform.scale(self.foliage_ambush_berry, (bw, bh))
        if getattr(self, "foliage_flower", None):
            fw = max(1, int(round(16 * zoom)))
            fh = max(1, int(round(16 * zoom)))
            self._scaled_foliage["flower"] = pygame.transform.scale(self.foliage_flower, (fw, fh))
        if getattr(self, "foliage_flower_yellow", None):
            fw = max(1, int(round(16 * zoom)))
            fh = max(1, int(round(16 * zoom)))
            self._scaled_foliage["flower_yellow"] = pygame.transform.scale(self.foliage_flower_yellow, (fw, fh))
        if getattr(self, "foliage_sunflower", None):
            sw = max(1, int(round(16 * zoom)))
            sh = max(1, int(round(16 * zoom)))
            self._scaled_foliage["sunflower"] = pygame.transform.scale(self.foliage_sunflower, (sw, sh))
        if getattr(self, "foliage_grass_flower1", None):
            gw = max(1, int(round(16 * zoom)))
            gh = max(1, int(round(16 * zoom)))
            self._scaled_foliage["grass_flower1"] = pygame.transform.scale(self.foliage_grass_flower1, (gw, gh))
        if getattr(self, "foliage_grass_flower2", None):
            gw = max(1, int(round(16 * zoom)))
            gh = max(1, int(round(16 * zoom)))
            self._scaled_foliage["grass_flower2"] = pygame.transform.scale(self.foliage_grass_flower2, (gw, gh))
        if getattr(self, "foliage_grass_tuft", None):
            gw = max(1, int(round(16 * zoom)))
            gh = max(1, int(round(16 * zoom)))
            self._scaled_foliage["grass_tuft"] = pygame.transform.scale(self.foliage_grass_tuft, (gw, gh))
        if getattr(self, "chicken_frames", None):
            cw = max(1, int(round(16 * zoom)))
            ch = max(1, int(round(16 * zoom)))
            self._scaled_foliage["chickens"] = [
                pygame.transform.scale(f, (cw, ch)) for f in self.chicken_frames
            ]
        if self.dust_frames:
            dw = max(1, int(round(16 * zoom)))
            dh = max(1, int(round(16 * zoom)))
            self._scaled_foliage["dust"] = [
                pygame.transform.scale(f, (dw, dh)) for f in self.dust_frames
            ]
        if getattr(self, "chest_closed_surf", None):
            cw = max(1, int(round(16 * zoom)))
            ch = max(1, int(round(16 * zoom)))
            self._scaled_foliage["chest_closed"] = pygame.transform.scale(self.chest_closed_surf, (cw, ch))
        if getattr(self, "chest_opened_surf", None):
            cw = max(1, int(round(16 * zoom)))
            ch = max(1, int(round(16 * zoom)))
            self._scaled_foliage["chest_opened"] = pygame.transform.scale(self.chest_opened_surf, (cw, ch))

        # Pre-scale dynamic foliage tiles dari map data
        self._scaled_foliage_tiles = {}
        tw = max(1, int(round(16 * zoom)))
        th = max(1, int(round(16 * zoom)))
        fol = getattr(self.map, "foliage", {})
        all_fol_items = fol.get("grass_tufts", []) + fol.get("flowers", []) + fol.get("ambushes", [])
        for item in all_fol_items:
            if isinstance(item, dict):
                src = item.get("src")
                ax = item.get("atlas_x")
                ay = item.get("atlas_y")
                if src and ax is not None and ay is not None:
                    k = (src, ax, ay)
                    if k not in self._scaled_foliage_tiles:
                        surf = self._get_foliage_slice(src, ax, ay)
                        if surf:
                            self._scaled_foliage_tiles[k] = pygame.transform.scale(surf, (tw, th))

    def _refresh_scaled_map(self):
        # Pre-scale 4 frame animasi air sungai dengan Nearest-Neighbor scale (anti-burik)
        self.scaled_maps = []
        target_w = max(1, int(self.map_w * self.camera.zoom))
        target_h = max(1, int(self.map_h * self.camera.zoom))
        target_sz = (target_w, target_h)
        for f in range(4):
            base_surf = self.map.get_ground_surface(f).copy()
            if self.map.obstacle_surface is not None:
                base_surf.blit(self.map.obstacle_surface, (0, 0))
            # Nearest-Neighbor scaling: menjaga grafis 16x16 pixel-perfect tajam dan bebas burik
            scaled = pygame.transform.scale(base_surf, target_sz)
            self.scaled_maps.append(scaled)
        self.scaled_map = self.scaled_maps[self.water_frame % len(self.scaled_maps)]
        self.map_surface = self.map.ground_surface
        self._refresh_scaled_foliage()

    def _on_player_moved_sound(self, pos):
        if self.game_mode == "EXPLORATION":
            surface = self.map.get_surface_type(pos)
            self.audio.play_step(surface)

    def _process_continuous_player_movement(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            if self.player.try_move((0, -1)):
                return
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            if self.player.try_move((0, 1)):
                return
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            if self.player.try_move((-1, 0)):
                return
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            if self.player.try_move((1, 0)):
                return

    def _draw_guide_pill_button(self):
        """Merender tombol cepat Buku Panduan [H] di pojok kanan atas area peta eksplorasi."""
        sw = self.screen.get_width()
        font_sm = self.fonts.get("tiny", self.fonts["sm"])
        lbl = "[H] Buku Panduan"
        t_surf = font_sm.render(lbl, True, (115, 62, 16))
        bw = t_surf.get_width() + 26
        bh = 30
        bx = sw - bw - 14
        by = 14
        self.btn_guide_pill = pygame.Rect(bx, by, bw, bh)

        hov = self.btn_guide_pill.collidepoint(pygame.mouse.get_pos())
        bg_col = (255, 252, 244, 245) if hov else (248, 242, 228, 232)
        bd_col = (205, 135, 25) if hov else (196, 174, 144)

        pill = pygame.Surface((bw, bh), SRCALPHA)
        pygame.draw.rect(pill, bg_col, pill.get_rect(), border_radius=8)
        pygame.draw.rect(pill, bd_col, pill.get_rect(), 1, border_radius=8)
        self.screen.blit(pill, self.btn_guide_pill.topleft)
        self.screen.blit(t_surf, t_surf.get_rect(center=self.btn_guide_pill.center))

    def _draw_npc_offscreen_indicator(self):
        # Batas area viewport kamera (sebelah kanan sidebar debug)
        panel_w = self.camera.left_panel_w
        margin = 32
        min_x = panel_w + margin
        max_x = self.screen.get_width() - margin
        min_y = margin
        max_y = self.screen.get_height() - margin
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0
        viewport_rect = pygame.Rect(min_x, min_y, max_x - min_x, max_y - min_y)

        # Efek denyut (pulsing animation) & font seragam untuk seluruh NPC
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.008)
        radius = int(18 + pulse * 3)
        font = self.fonts.get("bubble", self.fonts["sm"])
        placed_badges = []

        for npc in (getattr(self, "npc", None), getattr(self, "npc_kuro", None), getattr(self, "npc_shiro", None)):
            if not npc:
                continue

            npc_sx, npc_sy = self.camera.world_to_screen(npc.px, npc.py)
            is_offscreen = (
                npc_sx < min_x or npc_sx > max_x or
                npc_sy < min_y or npc_sy > max_y
            )
            if not is_offscreen:
                continue

            edge_x = max(min_x, min(max_x, npc_sx))
            edge_y = max(min_y, min(max_y, npc_sy))
            angle = math.atan2(npc_sy - center_y, npc_sx - center_x)
            dist_grid = abs(self.player.grid[0] - npc.grid[0]) + abs(self.player.grid[1] - npc.grid[1])

            # Glow surface transparan
            glow_surf = pygame.Surface((radius * 2 + 16, radius * 2 + 16), SRCALPHA)
            glow_center = (glow_surf.get_width() // 2, glow_surf.get_height() // 2)

            pygame.draw.circle(glow_surf, (255, 140, 0, int(80 + pulse * 60)), glow_center, radius + 5)
            pygame.draw.circle(glow_surf, (255, 120, 0, 230), glow_center, radius)
            pygame.draw.circle(glow_surf, (255, 230, 110, 240), glow_center, radius, width=2)
            self.screen.blit(glow_surf, glow_surf.get_rect(center=(int(edge_x), int(edge_y))))

            # Segitiga panah penunjuk arah NPC
            arrow_len = 12
            p1 = (
                int(edge_x + math.cos(angle) * (radius + arrow_len)),
                int(edge_y + math.sin(angle) * (radius + arrow_len)),
            )
            p2 = (
                int(edge_x + math.cos(angle + 2.5) * radius),
                int(edge_y + math.sin(angle + 2.5) * radius),
            )
            p3 = (
                int(edge_x + math.cos(angle - 2.5) * radius),
                int(edge_y + math.sin(angle - 2.5) * radius),
            )
            pygame.draw.polygon(self.screen, (255, 225, 50), [p1, p2, p3])
            pygame.draw.polygon(self.screen, (210, 80, 0), [p1, p2, p3], 1)

            # Label Teks Badge "Nama (X meter)"
            txt_surf = font.render(f"{npc.name} ({dist_grid} meter)", True, (150, 75, 15))
            txt_x = int(edge_x)
            txt_y = int(edge_y + radius + 16)
            if txt_y > max_y - 10:
                txt_y = int(edge_y - radius - 16)

            bg_rect = txt_surf.get_rect(center=(txt_x, txt_y))
            bg_rect.clamp_ip(viewport_rect)
            for prev in placed_badges:
                if bg_rect.colliderect(prev.inflate(6, 6)):
                    shift = prev.height + 10
                    bg_rect.y = prev.y - shift if bg_rect.centery > max_y // 2 else prev.bottom + 8
                    bg_rect.clamp_ip(viewport_rect)
            placed_badges.append(bg_rect)

            card_bg = pygame.Surface((bg_rect.width + 12, bg_rect.height + 6), SRCALPHA)
            pygame.draw.rect(card_bg, (255, 253, 248, 245), card_bg.get_rect(), border_radius=5)
            pygame.draw.rect(card_bg, (215, 140, 30), card_bg.get_rect(), 1, border_radius=5)
            self.screen.blit(card_bg, card_bg.get_rect(center=bg_rect.center))
            self.screen.blit(txt_surf, bg_rect)

    def _draw_chests(self):
        sf = getattr(self, "_scaled_foliage", {})
        closed_surf = sf.get("chest_closed")
        opened_surf = sf.get("chest_opened")
        sz = int(self.map.cell_size * self.camera.zoom)

        for chest in self.chests:
            cx, cy = self.map.world_to_px(chest["pos"])
            sx, sy = self.camera.world_to_screen(cx, cy)
            rect = pygame.Rect(int(sx - sz // 2), int(sy - sz // 2), sz, sz)

            if chest["opened"]:
                if opened_surf:
                    self.screen.blit(opened_surf, (rect.x, rect.y))
                else:
                    pygame.draw.rect(self.screen, (85, 75, 65), rect, border_radius=4)
                    pygame.draw.rect(self.screen, (120, 110, 100), rect, width=1, border_radius=4)
            else:
                if closed_surf:
                    self.screen.blit(closed_surf, (rect.x, rect.y))
                else:
                    pygame.draw.rect(self.screen, (160, 95, 25), rect, border_radius=4)
                    pygame.draw.rect(self.screen, (245, 200, 60), rect, width=max(1, int(2 * self.camera.zoom)), border_radius=4)

                dx = abs(self.player.grid[0] - chest["pos"][0])
                dy = abs(self.player.grid[1] - chest["pos"][1])
                if max(dx, dy) <= 1:
                    prompt = self.fonts.get("bubble", self.fonts["sm"]).render("[E] Buka Peti", True, (150, 75, 15))
                    p_box = prompt.get_rect(center=(rect.centerx, rect.top - 16))
                    card = pygame.Surface((p_box.width + 12, p_box.height + 6), SRCALPHA)
                    pygame.draw.rect(card, (255, 253, 248, 245), card.get_rect(), border_radius=4)
                    pygame.draw.rect(card, (212, 186, 150), card.get_rect(), 1, border_radius=4)
                    self.screen.blit(card, card.get_rect(center=p_box.center))
                    self.screen.blit(prompt, p_box)

    def _draw_obtained_items_hud(self):
        """Menampilkan panel HUD item yang didapat di bagian bawah kiri layar map (mode searching)."""
        w, h = self.screen.get_size()
        panel_w = self.camera.left_panel_w
        sc = getattr(config, "UI_SCALE", 1.0)
        hud_x = panel_w + int(round(14 * sc))
        hud_h = int(round(88 * sc))

        font_tiny = self.fonts.get("tiny", self.fonts.get("sm"))
        font_sm = self.fonts.get("sm", font_tiny)
        font_bubble = self.fonts.get("bubble", font_sm)

        inventory = self.player.inventory or []

        name_to_meta = {
            "health_potion": {
                "key": "health_potion",
                "name": "Health Potion",
                "badge": "+1 Ramuan",
                "badge_mini": f"x{self.player.persistent_potions}",
                "desc": "Ramuan pemulih HP instan untuk duel pertarungan.",
                "color": (65, 215, 120),
            },
            "mega_potion": {
                "key": "mega_potion",
                "name": "Mega Potion",
                "badge": "+50 HP & +1 Pot",
                "badge_mini": "MEGA",
                "desc": "Ramuan sakti pemulih 50 HP seketika dan +1 ramuan.",
                "color": (80, 225, 230),
            },
            "item_sword": {
                "key": "item_sword",
                "name": "Pedang Ksatria",
                "badge": "+5 ATK Bonus",
                "badge_mini": "+5",
                "desc": "Menempa kekuatan hero, menaikkan damage serangan.",
                "color": (255, 140, 50),
            },
            "item_shield": {
                "key": "item_shield",
                "name": "Perisai Baja",
                "badge": "+4 DEF Flat",
                "badge_mini": "+4",
                "desc": "Pertahanan kokoh memangkas damage dari musuh.",
                "color": (75, 160, 245),
            },
            "item_boots": {
                "key": "item_boots",
                "name": "Boots Lincah",
                "badge": "+Kelincahan",
                "badge_mini": "SPD",
                "desc": "Sepatu pengembara legendaris penambah kelincahan.",
                "color": (240, 200, 60),
            },
            "item_bow": {
                "key": "item_bow",
                "name": "Busur Pemburu",
                "badge": "+4 ATK Jarak Jauh",
                "badge_mini": "+4",
                "desc": "Senjata jarak jauh presisi tinggi menembus musuh.",
                "color": (160, 230, 70),
            },
            "item_dagger": {
                "key": "item_dagger",
                "name": "Belati Bayangan",
                "badge": "+Crit Rate",
                "badge_mini": "CRT",
                "desc": "Belati ringan mematikan menembus titik lemah.",
                "color": (210, 80, 240),
            },
            "Pedang Ksatria Oyen": {
                "key": "item_sword",
                "name": "Pedang Ksatria Oyen",
                "badge": "+15 ATK Bonus",
                "badge_mini": "+15",
                "desc": "Rampasan perang dari Oyen sang Warrior.",
                "color": (255, 140, 50),
            },
            "Busur Presisi Kuro": {
                "key": "item_bow",
                "name": "Busur Presisi Kuro",
                "badge": "+10 ATK Bonus",
                "badge_mini": "+10",
                "desc": "Rampasan perang dari Kuro sang Ranger.",
                "color": (160, 230, 70),
            },
            "Belati Bayangan Kage": {
                "key": "item_dagger",
                "name": "Belati Bayangan Kage",
                "badge": "+12 ATK Bonus",
                "badge_mini": "+12",
                "desc": "Rampasan perang dari Kage sang Assassin.",
                "color": (210, 80, 240),
            },
            "Tongkat Sihir Shiro": {
                "key": "mega_potion",
                "name": "Tongkat Sihir Shiro",
                "badge": "+2 Ramuan & HP",
                "badge_mini": "MEGA",
                "desc": "Rampasan perang dari Shiro sang Mage.",
                "color": (80, 225, 230),
            },
            "Relik Ikan Emas": {
                "key": "mega_potion",
                "name": "Relik Ikan Emas",
                "badge": "+10 ATK & +6 DEF",
                "badge_mini": "RELIK",
                "desc": "Artefak tersembunyi (Materi 09) penguat duel Boss Kage.",
                "color": (255, 200, 60),
            },
        }

        slot_count = max(3, len(inventory))
        slot_w = int(round(48 * sc))
        slot_h = int(round(48 * sc))
        slot_gap = int(round(10 * sc))
        pad_x = int(round(14 * sc))
        pad_y = int(round(10 * sc))

        # Hitung kebutuhan lebar header
        rune_count = len(getattr(self.player, "rune_keys", []))
        if rune_count >= 3:
            title_text = "PORTAL MENARA AKTIF!"
            count_text = f"({rune_count}/3 Kunci) Menuju Menara!"
            t_col = (130, 40, 195)
            c_col = (175, 60, 230)
        else:
            title_text = "ITEM & KUNCI RUNE"
            count_text = f"({rune_count}/3 Kunci)"
            t_col = (42, 32, 25)
            c_col = (145, 120, 95)
        t_surf = font_bubble.render(title_text, True, t_col)
        c_surf = font_sm.render(count_text, True, c_col)

        bonuses = []
        if self.player.atk_bonus > 0:
            bonuses.append(f"ATK +{self.player.atk_bonus}")
        if self.player.def_bonus > 0:
            bonuses.append(f"DEF +{self.player.def_bonus}")
        b_surf = font_tiny.render(" • ".join(bonuses), True, (185, 110, 18)) if bonuses else None

        header_req_w = t_surf.get_width() + c_surf.get_width() + int(round(16 * sc))
        if b_surf:
            header_req_w += b_surf.get_width() + int(round(20 * sc))

        slots_total_w = slot_count * slot_w + (slot_count - 1) * slot_gap
        min_hud_w = int(round(280 * sc))
        hud_w = max(min_hud_w, slots_total_w + pad_x * 2, header_req_w + pad_x * 2)
        hud_y = h - hud_h - int(round(14 * sc))

        # 1. Background Container Card (Cozy Adventurer Journal Tone)
        shadow_surf = pygame.Surface((hud_w, hud_h), SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 30), (0, 0, hud_w, hud_h), border_radius=10)
        self.screen.blit(shadow_surf, (hud_x + 2, hud_y + 2))

        card_surf = pygame.Surface((hud_w, hud_h), SRCALPHA)
        pygame.draw.rect(card_surf, (255, 253, 248, 242), card_surf.get_rect(), border_radius=10)
        pygame.draw.rect(card_surf, (215, 202, 184), card_surf.get_rect(), 1, border_radius=10)
        pygame.draw.line(card_surf, (255, 255, 255, 220), (8, 1), (hud_w - 8, 1), 1)
        self.screen.blit(card_surf, (hud_x, hud_y))

        # 2. Header Bar
        self.screen.blit(t_surf, (hud_x + pad_x, hud_y + 6))
        self.screen.blit(c_surf, (hud_x + pad_x + t_surf.get_width() + 6, hud_y + 6))
        if b_surf:
            self.screen.blit(b_surf, (hud_x + hud_w - pad_x - b_surf.get_width(), hud_y + 8))

        # 3. Item Slots
        sy = hud_y + int(round(30 * sc))
        mouse_pos = pygame.mouse.get_pos()
        hovered_meta = None
        hovered_rect = None

        for i in range(slot_count):
            sx = hud_x + pad_x + i * (slot_w + slot_gap)
            slot_rect = pygame.Rect(sx, sy, slot_w, slot_h)

            if i < len(inventory):
                raw_item = inventory[i]
                meta = name_to_meta.get(raw_item, {
                    "key": raw_item,
                    "name": raw_item.replace("item_", "").replace("_", " ").title(),
                    "badge": "Artefak",
                    "badge_mini": "",
                    "desc": f"Item {raw_item} dalam inventori.",
                    "color": (210, 160, 45),
                })
                item_key = meta["key"]

                # Background slot terisi (Krem Hangat)
                s_bg = pygame.Surface((slot_w, slot_h), SRCALPHA)
                pygame.draw.rect(s_bg, (248, 243, 233, 230), s_bg.get_rect(), border_radius=6)
                self.screen.blit(s_bg, (sx, sy))

                # Border slot
                slot_col = meta.get("color", (210, 180, 120))
                pygame.draw.rect(self.screen, slot_col, slot_rect, 1, border_radius=6)

                # Icon Item
                if item_key in self.item_images:
                    icon_sz = int(round(34 * sc))
                    icon = pygame.transform.scale(self.item_images[item_key], (icon_sz, icon_sz))
                    ix = sx + (slot_w - icon_sz) // 2
                    iy = sy + (slot_h - icon_sz) // 2
                    self.screen.blit(icon, (ix, iy))
                    ix = sx + (slot_w - 30) // 2
                    iy = sy + (slot_h - 30) // 2
                    self.screen.blit(icon, (ix, iy))

                # Mini badge (misal x3 potion, +5 ATK)
                mini_label = meta.get("badge_mini", "")
                if mini_label:
                    m_surf = font_tiny.render(mini_label, True, (255, 255, 255))
                    m_pad = 4
                    mw = m_surf.get_width() + m_pad * 2
                    mh = m_surf.get_height() + 1
                    m_rect = pygame.Rect(slot_rect.right - mw - 2, slot_rect.bottom - mh - 2, mw, mh)
                    pygame.draw.rect(self.screen, (55, 42, 32, 225), m_rect, border_radius=3)
                    pygame.draw.rect(self.screen, slot_col, m_rect, 1, border_radius=3)
                    self.screen.blit(m_surf, (m_rect.x + m_pad, m_rect.y))

                # Cek hover jika tidak sedang gacha modal
                if not self.gacha_active and not getattr(self, "gacha_showcase", None):
                    if slot_rect.collidepoint(mouse_pos):
                        hovered_meta = meta
                        hovered_rect = slot_rect
            else:
                # Slot Kosong (Linen Kertas Perkamen)
                s_bg = pygame.Surface((slot_w, slot_h), SRCALPHA)
                pygame.draw.rect(s_bg, (242, 236, 225, 180), s_bg.get_rect(), border_radius=6)
                self.screen.blit(s_bg, (sx, sy))
                pygame.draw.rect(self.screen, (218, 205, 188), slot_rect, 1, border_radius=6)
                q_surf = font_sm.render("?", True, (175, 160, 140))
                self.screen.blit(q_surf, (slot_rect.centerx - q_surf.get_width() // 2, slot_rect.centery - q_surf.get_height() // 2))

        # Jika inventori masih kosong, tampilkan petunjuk
        if len(inventory) == 0:
            hint_surf = font_tiny.render("Buka Peti [E] di Map", True, (150, 135, 115))
            hint_x = hud_x + pad_x + slot_count * (slot_w + slot_gap) + 8
            if hint_x + hint_surf.get_width() <= hud_x + hud_w - pad_x:
                self.screen.blit(hint_surf, (hint_x, sy + (slot_h - hint_surf.get_height()) // 2))

        # 4. Tooltip saat mouse hover di atas slot
        if hovered_meta and hovered_rect:
            tt_title = font_bubble.render(hovered_meta["name"], True, (38, 30, 24))
            tt_badge = font_tiny.render(f"• {hovered_meta['badge']}", True, (185, 110, 15))
            tt_desc = font_tiny.render(hovered_meta["desc"], True, (95, 80, 70))

            tt_w = max(tt_title.get_width() + tt_badge.get_width() + 30, tt_desc.get_width() + 20)
            tt_h = 44
            tt_x = max(hud_x, min(w - tt_w - 10, hovered_rect.centerx - tt_w // 2))
            tt_y = hud_y - tt_h - 8

            tt_shadow = pygame.Surface((tt_w, tt_h), SRCALPHA)
            pygame.draw.rect(tt_shadow, (0, 0, 0, 30), (0, 0, tt_w, tt_h), border_radius=6)
            self.screen.blit(tt_shadow, (tt_x + 2, tt_y + 2))

            tt_surf = pygame.Surface((tt_w, tt_h), SRCALPHA)
            tt_surf.fill((255, 252, 246, 250))
            pygame.draw.rect(tt_surf, (215, 195, 170), tt_surf.get_rect(), 1, border_radius=6)
            self.screen.blit(tt_surf, (tt_x, tt_y))

            self.screen.blit(tt_title, (tt_x + 8, tt_y + 5))
            self.screen.blit(tt_badge, (tt_x + 14 + tt_title.get_width(), tt_y + 6))
            self.screen.blit(tt_desc, (tt_x + 8, tt_y + 24))

    def _draw_gacha_popup(self):
        w, h = self.screen.get_size()
        is_dock_open = getattr(self.overlay.dock, "is_open", False) if hasattr(self, "overlay") and hasattr(self.overlay, "dock") else False
        panel_w = self.overlay.dock.rect.right if is_dock_open else config.TOTAL_COLLAPSED_WIDTH
        min_x = panel_w + 14
        max_x = w - 14

        # Dapatkan posisi target chest yang sedang dibuka
        chest = getattr(self, "active_gacha_chest", None)
        if chest and "pos" in chest:
            wx, wy = self.map.world_to_px(chest["pos"])
            chest_sx, chest_sy = self.camera.world_to_screen(wx, wy)
            sz = int(self.map.cell_size * self.camera.zoom)
        else:
            chest_sx, chest_sy = self.camera.world_to_screen(self.player.px, self.player.py)
            sz = int(self.map.cell_size * self.camera.zoom)

        chest_top_sy = chest_sy - sz // 2
        chest_bot_sy = chest_sy + sz // 2

        if self.gacha_active:
            # -----------------------------------------------------------------
            # 1. Animasi Pembukaan Peti (Roulette Putar Item) di Atas Chest
            # -----------------------------------------------------------------
            pop_w, pop_h = 270, 114
            arrow_h = 8

            target_y = chest_top_sy - arrow_h - 4
            pop_y = target_y - pop_h
            arrow_points_down = True

            if pop_y < 12:
                pop_y = chest_bot_sy + arrow_h + 4
                arrow_points_down = False

            pop_x = chest_sx - pop_w // 2
            pop_x = max(min_x, min(max_x - pop_w, pop_x))
            pop_rect = pygame.Rect(pop_x, pop_y, pop_w, pop_h)

            # Drop Shadow
            shadow_surf = pygame.Surface((pop_w, pop_h), SRCALPHA)
            pygame.draw.rect(shadow_surf, (0, 0, 0, 35), (0, 0, pop_w, pop_h), border_radius=12)
            self.screen.blit(shadow_surf, (pop_x + 3, pop_y + 3))

            # Body Card (Cozy Warm Ivory)
            card = pygame.Surface((pop_w, pop_h), SRCALPHA)
            card.fill((255, 253, 248, 248))
            pygame.draw.rect(card, (215, 202, 184), (0, 0, pop_w, pop_h), 2, border_radius=12)
            pygame.draw.line(card, (255, 255, 255), (8, 1), (pop_w - 8, 1), 1)
            self.screen.blit(card, pop_rect)

            # Segitiga Pointer (Speech Bubble Arrow ke Chest)
            tip_x = max(pop_rect.left + 16, min(pop_rect.right - 16, chest_sx))
            if arrow_points_down:
                tip_y = pop_rect.bottom + arrow_h
                pts = [(tip_x - 8, pop_rect.bottom), (tip_x + 8, pop_rect.bottom), (tip_x, tip_y)]
            else:
                tip_y = pop_rect.top - arrow_h
                pts = [(tip_x - 8, pop_rect.top), (tip_x + 8, pop_rect.top), (tip_x, tip_y)]

            pygame.draw.polygon(self.screen, (255, 253, 248), pts)
            pygame.draw.line(self.screen, (215, 202, 184), pts[0], pts[2], 2)
            pygame.draw.line(self.screen, (215, 202, 184), pts[1], pts[2], 2)

            # Header Roulette
            title = self.fonts.get("bubble", self.fonts["sm"]).render("✨ MEMBUKA PETI...", True, (185, 120, 20))
            self.screen.blit(title, (pop_rect.centerx - title.get_width() // 2, pop_rect.y + 10))

            # Pedestal Lingkaran Preview Item Roulette
            ped_cx = pop_rect.centerx
            ped_cy = pop_rect.y + 54
            ped_rad = 22
            pygame.draw.circle(self.screen, (246, 238, 224), (ped_cx, ped_cy), ped_rad)
            pygame.draw.circle(self.screen, (218, 190, 140), (ped_cx, ped_cy), ped_rad, width=2)

            cur_item = self.gacha_current_item
            if cur_item and cur_item in self.item_images:
                img = pygame.transform.smoothscale(self.item_images[cur_item], (32, 32))
                self.screen.blit(img, img.get_rect(center=(ped_cx, ped_cy)))

            sub = self.fonts.get("tiny", self.fonts["sm"]).render("Memutar takdir keberuntungan...", True, (120, 105, 90))
            self.screen.blit(sub, (pop_rect.centerx - sub.get_width() // 2, pop_rect.bottom - 22))

        elif getattr(self, "gacha_showcase", None):
            # -----------------------------------------------------------------
            # 2. Pesan Item Didapat Melayang Tepat di Atas Chest (Cozy Card)
            # -----------------------------------------------------------------
            showcase = self.gacha_showcase
            item_key = showcase["item_key"]
            item_name = showcase["name"]
            item_badge = showcase["badge"]
            item_desc = showcase["desc"]
            item_col = showcase.get("color", (215, 160, 45))
            anim_t = showcase.get("anim_time", 0.0)

            pop_w, pop_h = 310, 166
            arrow_h = 8

            target_y = chest_top_sy - arrow_h - 4
            pop_y = target_y - pop_h
            arrow_points_down = True

            if pop_y < 12:
                pop_y = chest_bot_sy + arrow_h + 4
                arrow_points_down = False

            pop_x = chest_sx - pop_w // 2
            pop_x = max(min_x, min(max_x - pop_w, pop_x))
            pop_rect = pygame.Rect(pop_x, pop_y, pop_w, pop_h)

            # Drop Shadow
            shadow_surf = pygame.Surface((pop_w, pop_h), SRCALPHA)
            pygame.draw.rect(shadow_surf, (0, 0, 0, 35), (0, 0, pop_w, pop_h), border_radius=12)
            self.screen.blit(shadow_surf, (pop_x + 3, pop_y + 3))

            # Body Card (Cozy Warm Ivory)
            card = pygame.Surface((pop_w, pop_h), SRCALPHA)
            card.fill((255, 253, 248, 250))
            pygame.draw.rect(card, (215, 202, 184), (0, 0, pop_w, pop_h), 2, border_radius=12)
            pygame.draw.line(card, (255, 255, 255), (8, 1), (pop_w - 8, 1), 1)
            self.screen.blit(card, pop_rect)

            # Segitiga Pointer (Arrow ke Chest)
            tip_x = max(pop_rect.left + 16, min(pop_rect.right - 16, chest_sx))
            if arrow_points_down:
                tip_y = pop_rect.bottom + arrow_h
                pts = [(tip_x - 8, pop_rect.bottom), (tip_x + 8, pop_rect.bottom), (tip_x, tip_y)]
            else:
                tip_y = pop_rect.top - arrow_h
                pts = [(tip_x - 8, pop_rect.top), (tip_x + 8, pop_rect.top), (tip_x, tip_y)]

            pygame.draw.polygon(self.screen, (255, 253, 248), pts)
            pygame.draw.line(self.screen, (215, 202, 184), pts[0], pts[2], 2)
            pygame.draw.line(self.screen, (215, 202, 184), pts[1], pts[2], 2)

            font_bubble = self.fonts.get("bubble", self.fonts["sm"])
            font_sm = self.fonts["sm"]
            font_tiny = self.fonts.get("tiny", self.fonts["sm"])

            # Header Top Pill: ✦ PETI TERBUKA!
            hdr_w, hdr_h = 160, 22
            hdr_rect = pygame.Rect(pop_x + 10, pop_y + 8, hdr_w, hdr_h)
            hdr_bg = pygame.Surface((hdr_w, hdr_h), SRCALPHA)
            hdr_bg.fill((246, 238, 224, 220))
            pygame.draw.rect(hdr_bg, (218, 190, 150), (0, 0, hdr_w, hdr_h), 1, border_radius=11)
            self.screen.blit(hdr_bg, hdr_rect)

            hdr_lbl = font_tiny.render("✦ PETI TERBUKA!", True, (175, 110, 15))
            self.screen.blit(hdr_lbl, hdr_lbl.get_rect(center=hdr_rect.center))

            # Tombol [✕] di sudut kanan atas
            close_lbl = font_tiny.render("✕", True, (150, 130, 115))
            self.screen.blit(close_lbl, (pop_rect.right - 22, pop_rect.y + 10))

            # Pedestal Lingkaran dengan radial glow lembut
            ped_cx = pop_x + 44
            ped_cy = pop_y + 68
            ped_radius = 28

            pulse = 0.5 + 0.5 * math.sin(anim_t * 4.0)
            glow_surf = pygame.Surface((ped_radius * 2 + 16, ped_radius * 2 + 16), SRCALPHA)
            glow_col = (*item_col[:3], int(40 + pulse * 45))
            pygame.draw.circle(glow_surf, glow_col, (ped_radius + 8, ped_radius + 8), int(ped_radius + 2 + pulse * 3))
            self.screen.blit(glow_surf, glow_surf.get_rect(center=(ped_cx, ped_cy)))

            pygame.draw.circle(self.screen, (246, 240, 228), (ped_cx, ped_cy), ped_radius)
            pygame.draw.circle(self.screen, (215, 195, 160), (ped_cx, ped_cy), ped_radius, width=2)

            # Gambar Item
            item_img = None
            if item_key in self.item_images:
                item_img = self.item_images[item_key]
            elif item_key in self.item_images_large:
                item_img = pygame.transform.smoothscale(self.item_images_large[item_key], (44, 44))

            if item_img:
                scale_pulse = 1.0 + 0.05 * math.sin(anim_t * 4.0)
                isz = int(40 * scale_pulse)
                rendered_img = pygame.transform.smoothscale(item_img, (isz, isz))
                self.screen.blit(rendered_img, rendered_img.get_rect(center=(ped_cx, ped_cy)))

            # Sisi Kanan: Nama Item, Stat Badge, Deskripsi
            tx = pop_x + 82
            max_tw = pop_w - 92

            name_lbl = font_bubble.render(item_name, True, (38, 30, 24))
            self.screen.blit(name_lbl, (tx, pop_y + 36))

            # Pill Badge Efek / Stat Bonus
            stat_lbl = font_tiny.render(f"✦ {item_badge}", True, (35, 130, 60))
            bw = stat_lbl.get_width() + 10
            bh = 18
            b_rect = pygame.Rect(tx, pop_y + 58, bw, bh)
            b_bg = pygame.Surface((bw, bh), SRCALPHA)
            b_bg.fill((236, 246, 238, 220))
            pygame.draw.rect(b_bg, (180, 220, 190), (0, 0, bw, bh), 1, border_radius=4)
            self.screen.blit(b_bg, b_rect)
            self.screen.blit(stat_lbl, (tx + 5, pop_y + 59))

            # Deskripsi Efek Item (Wrap)
            words = item_desc.split(" ")
            lines = []
            cur_line = []
            for w_str in words:
                test_str = " ".join(cur_line + [w_str])
                if font_tiny.size(test_str)[0] <= max_tw:
                    cur_line.append(w_str)
                else:
                    if cur_line:
                        lines.append(" ".join(cur_line))
                    cur_line = [w_str]
            if cur_line:
                lines.append(" ".join(cur_line))

            desc_y = pop_y + 80
            for l_idx, line_str in enumerate(lines[:2]):
                desc_lbl = font_tiny.render(line_str, True, (95, 80, 70))
                self.screen.blit(desc_lbl, (tx, desc_y + l_idx * 14))

            # Tombol Interaktif / Petunjuk di Bawah
            btn_w, btn_h = pop_w - 20, 26
            btn_rect = pygame.Rect(pop_x + 10, pop_rect.bottom - btn_h - 8, btn_w, btn_h)
            btn_bg = pygame.Surface((btn_w, btn_h), SRCALPHA)
            btn_bg.fill((246, 240, 230, 240))
            pygame.draw.rect(btn_bg, (215, 195, 170), (0, 0, btn_w, btn_h), 1, border_radius=6)
            self.screen.blit(btn_bg, btn_rect)

            prompt_str = "Simpan ke Tas [E] / [Klik]"
            p_txt = font_tiny.render(prompt_str, True, (140, 95, 20))
            self.screen.blit(p_txt, p_txt.get_rect(center=btn_rect.center))

        elif self.gacha_message_timer > 0:
            alpha = min(255, int(255 * (self.gacha_message_timer / 0.5))) if self.gacha_message_timer < 0.5 else 255
            txt = self.fonts.get("bubble", self.fonts["sm"]).render(self.gacha_message, True, (38, 30, 24))
            toast_w = txt.get_width() + 24
            toast_h = txt.get_height() + 10
            toast_x = max(min_x, min(max_x - toast_w, chest_sx - toast_w // 2))
            toast_y = max(12, chest_top_sy - toast_h - 10)
            toast_rect = pygame.Rect(toast_x, toast_y, toast_w, toast_h)
            card = pygame.Surface((toast_w, toast_h), SRCALPHA)
            card.fill((255, 253, 248, int(245 * (alpha / 255.0))))
            pygame.draw.rect(card, (215, 195, 170, alpha), card.get_rect(), 1, border_radius=6)
            self.screen.blit(card, toast_rect)
            self.screen.blit(txt, txt.get_rect(center=toast_rect.center))

    def _load_item_images(self):
        items = {}
        item_files = {
            "health_potion": "health_potion.png",
            "mega_potion": "mega_potion.png",
            "item_sword": "item_sword.png",
            "item_shield": "item_shield.png",
            "item_boots": "item_boots.png",
            "item_bow": "item_bow.png",
            "item_dagger": "item_dagger.png",
        }
        for key, fn in item_files.items():
            path = os.path.join(config.ASSET_DIR, "items", fn)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    items[key] = pygame.transform.smoothscale(img, (48, 48))
                except Exception:
                    pass
        return items

    def _load_item_images_large(self):
        items_large = {}
        item_files = {
            "health_potion": "health_potion.png",
            "mega_potion": "mega_potion.png",
            "item_sword": "item_sword.png",
            "item_shield": "item_shield.png",
            "item_boots": "item_boots.png",
            "item_bow": "item_bow.png",
            "item_dagger": "item_dagger.png",
        }
        for key, fn in item_files.items():
            path = os.path.join(config.ASSET_DIR, "items", fn)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    items_large[key] = pygame.transform.smoothscale(img, (96, 96))
                except Exception:
                    pass
        return items_large

    def _load_battle_sprites(self):
        b_sprites = {}
        files = {
            "player": "battle_bolu.png",
            "warrior": "battle_warrior.png",
            "tank": "battle_tank.png",
            "ranger": "battle_ranger.png",
            "assassin": "battle_assassin.png",
            "mage": "battle_mage.png",
            "shiro": "battle_shiro.png",
            "kage": "battle_kage.png",
            "boss": "battle_boss.png",
        }
        for key, fn in files.items():
            path = os.path.join(config.ASSET_DIR, "battle_sprites", fn)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    b_sprites[key] = img
                except Exception:
                    pass
        return b_sprites

    def _open_chest(self, chest):
        if chest.get("opened", False) or self.gacha_active or getattr(self, "gacha_showcase", None):
            return
        chest["opened"] = True
        self.active_gacha_chest = chest
        self.gacha_active = True
        self.gacha_timer = 1.0
        self.gacha_reward_item = chest.get("item", "health_potion")
        self.gacha_showcase = None
        if hasattr(self, "overlay") and hasattr(self.overlay, "nav_rail"):
            self.overlay.nav_rail.set_badge(4, active=True)
            self.overlay.nav_rail.set_badge(5, active=True)

        # 1. Trigger InterNPCManager (Materi 07: Logic KB & Resolution Refutation)
        chest_idx = 0
        if chest in self.chests:
            chest_idx = self.chests.index(chest)
        chest_tag = "A" if chest_idx == 0 else ("B" if chest_idx == 1 else ("C" if chest_idx == 2 else "D"))

        # Tambahkan Kunci Rune ke pemain & Basis Pengetahuan
        key_name = f"Kunci Rune {chest_tag}"
        if key_name not in self.player.rune_keys:
            self.player.rune_keys.append(key_name)

        if hasattr(self, "inter_npc_manager") and self.inter_npc_manager:
            self.inter_npc_manager.on_chest_opened(chest_idx, chest.get("item", "health_potion"))

        # Banner Ticker AI Logic Percept
        rune_count = len(self.player.rune_keys)
        self.ai_ticker_info = {
            "title": f"[KB PERCEPT] Peti {chest_tag} Terbuka -> {key_name} Diperoleh ({rune_count}/3)!",
            "detail": f"Status FOL: ChestOpened({chest_tag}) & HasKey_{chest_tag} aktif. Koordinasi penjaga dipicu!",
            "timer": 4.5,
        }

        # 2. Trigger Automated Planning (Materi 08: Classical Planning STRIPS)
        if hasattr(self, "forward_planner") and self.forward_planner:
            s0_p, goal_p, actions_p = create_world_patrol_problem(chest_tag)
            use_backward = getattr(self, "selected_planning_engine", "FORWARD_A_STAR") == "BACKWARD_REGRESSION"
            planner = self.backward_planner if (use_backward and getattr(self, "backward_planner", None)) else self.forward_planner
            self.latest_plan_result = planner.plan(s0_p, goal_p, actions_p)
            if hasattr(self, "task_executor") and self.task_executor:
                self.task_executor.set_plan(self.latest_plan_result)

    def _award_gacha_reward(self):
        item = self.gacha_reward_item or "health_potion"
        item_meta = {
            "health_potion": {
                "name": "Health Potion",
                "badge": "+1 Ramuan Pertempuran",
                "desc": "Ramuan pemulih HP instan untuk pertarungan.",
                "color": (65, 215, 120),
            },
            "mega_potion": {
                "name": "Mega Potion",
                "badge": "+50 HP Langsung & +1 Ramuan",
                "desc": "Ramuan sakti yang memulihkan 50 HP seketika dan menambah stok ramuan.",
                "color": (80, 225, 230),
            },
            "item_sword": {
                "name": "Pedang Ksatria",
                "badge": "+5 ATK Bonus Permanen",
                "desc": "Menempa kekuatan hero, meningkatkan damage serangan setiap giliran.",
                "color": (255, 140, 50),
            },
            "item_shield": {
                "name": "Perisai Baja",
                "badge": "+4 Reduksi DEF Flat",
                "desc": "Pertahanan kokoh yang memangkas damage yang diterima dari musuh.",
                "color": (75, 160, 245),
            },
            "item_boots": {
                "name": "Boots Lincah",
                "badge": "+Kelincahan Bertualang",
                "desc": "Sepatu pengembara legendaris yang meningkatkan kelincahan melangkah.",
                "color": (240, 200, 60),
            },
            "item_bow": {
                "name": "Busur Pemburu",
                "badge": "+4 ATK & Inisiatif Serang",
                "desc": "Senjata jarak jauh presisi tinggi untuk menembus pertahanan lawan.",
                "color": (160, 230, 70),
            },
            "item_dagger": {
                "name": "Belati Bayangan",
                "badge": "+Crit Rate & Ketangkasan",
                "desc": "Belati ringan mematikan dengan ketajaman menusuk titik lemah lawan.",
                "color": (210, 80, 240),
            },
        }

        meta = item_meta.get(item, {
            "name": item.replace("item_", "").replace("_", " ").title(),
            "badge": "Item Baru",
            "desc": f"Item {item} berhasil ditambahkan ke inventori.",
            "color": (255, 215, 80),
        })

        if item == "health_potion":
            self.player.persistent_potions += 1
            if "health_potion" not in self.player.inventory:
                self.player.inventory.append("health_potion")
        elif item == "mega_potion":
            self.player.persistent_hp = min(100, self.player.persistent_hp + 50)
            self.player.persistent_potions += 1
            if "mega_potion" not in self.player.inventory:
                self.player.inventory.append("mega_potion")
        elif item == "item_sword":
            self.player.atk_bonus += 5
            if "item_sword" not in self.player.inventory:
                self.player.inventory.append("item_sword")
        elif item == "item_shield":
            self.player.def_bonus += 4
            if "item_shield" not in self.player.inventory:
                self.player.inventory.append("item_shield")
        elif item == "item_boots":
            if "item_boots" not in self.player.inventory:
                self.player.inventory.append("item_boots")
        else:
            if item not in self.player.inventory:
                self.player.inventory.append(item)

        self.gacha_showcase = {
            "item_key": item,
            "name": meta["name"],
            "badge": meta["badge"],
            "desc": meta["desc"],
            "color": meta["color"],
            "timer": 5.0,
            "max_timer": 5.0,
            "anim_time": 0.0,
            "chest": getattr(self, "active_gacha_chest", None),
        }
        self.gacha_message = f"Mendapatkan {meta['name']}!"
        self.gacha_message_timer = 0.0
        self.audio.play_chest_win()

    def _draw_sparkles(self):
        for sp in self.sparkles:
            sx, sy = self.camera.world_to_screen(sp["wx"], sp["wy"])
            progress = sp["t"] / max(0.01, sp["max_t"])
            alpha_factor = math.sin(progress * math.pi)
            r = int(sp["size"] * self.camera.zoom * alpha_factor)
            if r >= 2:
                pygame.draw.line(self.screen, (255, 255, 240), (sx, sy - r), (sx, sy + r), 1)
                pygame.draw.line(self.screen, (255, 255, 240), (sx - r, sy), (sx + r, sy), 1)
                if r >= 4:
                    pygame.draw.circle(self.screen, (255, 240, 180), (int(sx), int(sy)), max(1, r // 3))

    def _draw_dust_particles(self):
        scaled_dust = getattr(self, "_scaled_foliage", {}).get("dust")
        if not scaled_dust:
            return
        for dp in self.dust_particles:
            f_idx = min(len(scaled_dust) - 1, int((dp["t"] / max(0.01, dp["max_t"])) * len(scaled_dust)))
            surf = scaled_dust[f_idx]
            sx, sy = self.camera.world_to_screen(dp["wx"], dp["wy"])
            rect = surf.get_rect(center=(int(sx), int(sy)))
            self.screen.blit(surf, rect)

    def _draw_swaying_ground_foliage(self):
        """Menggambar rumput, bunga, dan semak yang bergoyang lembut tertiup angin (dengan Grid Frustum Culling)."""
        fol = getattr(self.map, "foliage", {})
        zoom = self.camera.zoom
        sf = getattr(self, "_scaled_foliage", {})
        tile_cache = getattr(self, "_scaled_foliage_tiles", {})

        win_w, win_h = self.screen.get_size()
        pad_px = 32.0
        min_gx = int(((self.camera.left_panel_w - self.camera.offset_x) / zoom - pad_px) // 16)
        max_gx = int(((win_w - self.camera.offset_x) / zoom + pad_px) // 16) + 1
        min_gy = int(((0.0 - self.camera.offset_y) / zoom - pad_px) // 16)
        max_gy = int(((win_h - self.camera.offset_y) / zoom + pad_px) // 16) + 1

        # 1. Grass Tufts & Hiasan Rumput (termasuk tile biom_things & grass.tsx)
        scaled_tuft_default = sf.get("grass_tuft")
        for gt in fol.get("grass_tufts", []):
            if isinstance(gt, dict):
                gx, gy = gt["x"], gt["y"]
                src, ax, ay = gt.get("src"), gt.get("atlas_x"), gt.get("atlas_y")
                img = tile_cache.get((src, ax, ay)) if (src and ax is not None and ay is not None) else None
                if not img:
                    img = scaled_tuft_default
            else:
                gx, gy = gt[0], gt[1]
                img = scaled_tuft_default
            if img:
                if not (min_gx <= gx <= max_gx and min_gy <= gy <= max_gy):
                    continue
                sway_x = math.sin(self.wind_timer * 3.2 + gx * 0.7 + gy * 0.5) * (0.8 * zoom)
                wx, wy = gx * 16, gy * 16
                sx, sy = self.camera.world_to_screen(wx, wy)
                self.screen.blit(img, (int(sx + sway_x), int(sy)))

        # 2. Bunga padang rumput
        scaled_fl1 = sf.get("grass_flower1")
        scaled_fl2 = sf.get("grass_flower2")
        scaled_fl = sf.get("flower")
        for fl in fol.get("flowers", []):
            if isinstance(fl, dict):
                fx, fy = fl["x"], fl["y"]
                src, ax, ay = fl.get("src"), fl.get("atlas_x"), fl.get("atlas_y")
                img = tile_cache.get((src, ax, ay)) if (src and ax is not None and ay is not None) else None
                if not img:
                    img = scaled_fl1 if (fx + fy) % 2 == 0 else (scaled_fl2 or scaled_fl)
            else:
                fx, fy = fl[0], fl[1]
                img = scaled_fl1 if (fx + fy) % 2 == 0 else (scaled_fl2 or scaled_fl)
            if img:
                if not (min_gx <= fx <= max_gx and min_gy <= fy <= max_gy):
                    continue
                sway_x = math.sin(self.wind_timer * 3.4 + fx * 1.1 + fy * 0.4) * (1.0 * zoom)
                wx, wy = fx * 16, fy * 16
                sx, sy = self.camera.world_to_screen(wx, wy)
                self.screen.blit(img, (int(sx + sway_x), int(sy)))

        # 3. Kepala Bunga Matahari
        scaled_sunflower = sf.get("sunflower")
        if scaled_sunflower:
            for sx_grid, sy_grid in fol.get("sunflowers", []):
                if not (min_gx <= sx_grid <= max_gx and min_gy <= sy_grid <= max_gy):
                    continue
                sway_x = math.sin(self.wind_timer * 2.5 + sx_grid * 0.8) * (1.3 * zoom)
                wx, wy = sx_grid * 16, sy_grid * 16
                sx, sy = self.camera.world_to_screen(wx, wy)
                self.screen.blit(scaled_sunflower, (int(sx + sway_x), int(sy)))

        # 4. Ambush (Semak-semak lebat berdaun hijau, ada berry, atau semak lebar)
        scaled_amb_green = sf.get("ambush_green")
        scaled_amb_berry = sf.get("ambush_berry")
        for amb in fol.get("ambushes", []):
            if isinstance(amb, dict):
                ax_grid, ay_grid = amb["x"], amb["y"]
                src, ax, ay = amb.get("src"), amb.get("atlas_x"), amb.get("atlas_y")
                atype = amb.get("type", "green")
                img = tile_cache.get((src, ax, ay)) if (src and ax is not None and ay is not None) else None
                if not img:
                    img = scaled_amb_berry if atype == "berry" else scaled_amb_green
            else:
                ax_grid, ay_grid = amb[0], amb[1]
                img = scaled_amb_green
            if img:
                if not (min_gx <= ax_grid <= max_gx and min_gy <= ay_grid <= max_gy):
                    continue
                sway_x = math.sin(self.wind_timer * 2.8 + ax_grid * 0.9 + ay_grid * 0.5) * (1.2 * zoom)
                wx, wy = ax_grid * 16, ay_grid * 16
                sx, sy = self.camera.world_to_screen(wx, wy)
                self.screen.blit(img, (int(sx + sway_x), int(sy)))

        # 5. Semak bulat (kompatibilitas map lama jika ada)
        scaled_bush = sf.get("bush")
        if scaled_bush:
            for bx, by in fol.get("bushes", []):
                if not (min_gx <= bx <= max_gx and min_gy <= by <= max_gy):
                    continue
                sway_x = math.sin(self.wind_timer * 2.8 + bx * 0.9) * (1.0 * zoom)
                wx, wy = bx * 16, by * 16
                sx, sy = self.camera.world_to_screen(wx, wy)
                self.screen.blit(scaled_bush, (int(sx + sway_x), int(sy)))

    def _draw_swaying_tree_canopies(self):
        """Menggambar kanopi daun pohon yang melambai tertiup angin (di atas batang pohon & karakter)."""
        fol = getattr(self.map, "foliage", {})
        zoom = self.camera.zoom
        sf = getattr(self, "_scaled_foliage", {})

        win_w, win_h = self.screen.get_size()
        pad_px = 48.0
        min_gx = int(((self.camera.left_panel_w - self.camera.offset_x) / zoom - pad_px) // 16)
        max_gx = int(((win_w - self.camera.offset_x) / zoom + pad_px) // 16) + 1
        min_gy = int(((0.0 - self.camera.offset_y) / zoom - pad_px) // 16)
        max_gy = int(((win_h - self.camera.offset_y) / zoom + pad_px) // 16) + 1

        scaled_green = sf.get("tree")
        scaled_pink = sf.get("tree_pink") or scaled_green
        scaled_small = sf.get("tree_small")

        if scaled_green:
            for tx, ty in fol.get("trees", []):
                if not (min_gx <= tx <= max_gx and min_gy <= ty <= max_gy):
                    continue
                sway_x = math.sin(self.wind_timer * 2.2 + tx * 0.6) * (1.5 * zoom)
                wx = tx * 16
                wy = ty * 16
                sx, sy = self.camera.world_to_screen(wx, wy)
                self.screen.blit(scaled_green, (int(sx + sway_x), int(sy)))

        if scaled_pink:
            for tx, ty in fol.get("trees_pink", []):
                if not (min_gx <= tx <= max_gx and min_gy <= ty <= max_gy):
                    continue
                sway_x = math.sin(self.wind_timer * 2.2 + tx * 0.6) * (1.5 * zoom)
                wx = tx * 16
                wy = ty * 16
                sx, sy = self.camera.world_to_screen(wx, wy)
                self.screen.blit(scaled_pink, (int(sx + sway_x), int(sy)))

        if scaled_small:
            for tx, ty in fol.get("trees_small", []):
                if not (min_gx <= tx <= max_gx and min_gy <= ty <= max_gy):
                    continue
                sway_x = math.sin(self.wind_timer * 2.4 + tx * 0.8) * (1.2 * zoom)
                wx = tx * 16
                wy = ty * 16
                sx, sy = self.camera.world_to_screen(wx, wy)
                self.screen.blit(scaled_small, (int(sx + sway_x), int(sy)))

    def _init_chickens(self):
        """Inisialisasi entitas ayam dengan status pergerakan lokal dan animasi masing-masing."""
        chickens_raw = getattr(self.map, "chickens", [])
        self.chicken_entities = []
        import random
        for ch in chickens_raw:
            cx = ch.get("x", 0) if isinstance(ch, dict) else ch[0]
            cy = ch.get("y", 0) if isinstance(ch, dict) else ch[1]
            ox = float(cx * 16)
            oy = float(cy * 16)
            self.chicken_entities.append({
                "origin_x": ox,
                "origin_y": oy,
                "x": ox,
                "y": oy,
                "target_x": ox,
                "target_y": oy,
                "state": random.choice(["idle", "peck"]),
                "timer": random.uniform(1.0, 3.0),
                "anim_timer": random.uniform(0.0, 1.5),
                "facing_left": random.choice([True, False]),
                "frame_idx": 0,
                "hop": 0,
                "speed": random.uniform(10.0, 14.0),
            })

    def _update_chickens(self, dt):
        """Memperbarui pergerakan lokal (wander kecil) dan state animasi ayam."""
        if not hasattr(self, "chicken_entities") or not self.chicken_entities:
            self._init_chickens()
            if not self.chicken_entities:
                return

        # Batasi delta time agar ayam tidak loncat saat FPS drop atau window drag
        dt = min(dt, 0.05)
        import math, random
        for ch in self.chicken_entities:
            ch["anim_timer"] += dt

            if ch["state"] == "walk":
                dx = ch["target_x"] - ch["x"]
                dy = ch["target_y"] - ch["y"]
                dist = math.hypot(dx, dy)
                step = ch["speed"] * dt
                if dist <= step or dist < 0.5:
                    ch["x"] = ch["target_x"]
                    ch["y"] = ch["target_y"]
                    ch["hop"] = 0
                    ch["state"] = random.choice(["idle", "peck"])
                    ch["timer"] = random.uniform(1.5, 3.2) if ch["state"] == "idle" else 1.8
                    ch["anim_timer"] = 0.0
                else:
                    ch["x"] += (dx / dist) * step
                    ch["y"] += (dy / dist) * step
                    ch["facing_left"] = (dx < 0)
                    # Di Free Chicken Sprites, frame 0 & 1 adalah animasi gerak/waddle
                    # (Frame 2 & 3 kosong/transparan, jangan dipakai agar ayam tidak hilang)
                    step_idx = int(ch["anim_timer"] / 0.14) % 2
                    ch["frame_idx"] = step_idx
                    ch["hop"] = -1 if step_idx == 1 else 0

            elif ch["state"] == "idle":
                ch["timer"] -= dt
                ch["hop"] = 0
                ch["frame_idx"] = 0 if ((ch["anim_timer"] % 1.6) < 1.3) else 1
                if ch["timer"] <= 0:
                    action = random.choice(["walk", "peck", "idle"])
                    if action == "walk":
                        ch["state"] = "walk"
                        angle = random.uniform(0, 2 * math.pi)
                        rad = random.uniform(4.0, 10.0)
                        ch["target_x"] = ch["origin_x"] + rad * math.cos(angle)
                        ch["target_y"] = ch["origin_y"] + rad * math.sin(angle)
                    elif action == "peck":
                        ch["state"] = "peck"
                        ch["timer"] = 1.8
                        ch["anim_timer"] = 0.0
                    else:
                        ch["timer"] = random.uniform(1.0, 2.5)

            elif ch["state"] == "peck":
                ch["timer"] -= dt
                ch["hop"] = 0
                peck_seq = [4, 5, 5, 6, 5, 7]
                step_idx = int(ch["anim_timer"] / 0.3) % len(peck_seq)
                ch["frame_idx"] = peck_seq[step_idx]
                if ch["timer"] <= 0:
                    ch["state"] = random.choice(["idle", "walk"])
                    if ch["state"] == "walk":
                        angle = random.uniform(0, 2 * math.pi)
                        rad = random.uniform(4.0, 10.0)
                        ch["target_x"] = ch["origin_x"] + rad * math.cos(angle)
                        ch["target_y"] = ch["origin_y"] + rad * math.sin(angle)
                    else:
                        ch["timer"] = random.uniform(1.5, 3.0)
                    ch["anim_timer"] = 0.0

            # Batasi agar jarak absolut ayam tidak pernah melebihi 12px dari sarang/asalnya
            d_origin = math.hypot(ch["x"] - ch["origin_x"], ch["y"] - ch["origin_y"])
            if d_origin > 12.0:
                ch["x"] = ch["origin_x"] + (ch["x"] - ch["origin_x"]) / d_origin * 12.0
                ch["y"] = ch["origin_y"] + (ch["y"] - ch["origin_y"]) / d_origin * 12.0

    def _draw_chickens(self):
        """Menggambar ayam-ayam yang beranimasi makan / mematuk tanah dan berjalan lokal di peta."""
        if not hasattr(self, "chicken_entities") or not self.chicken_entities:
            self._init_chickens()
            if not self.chicken_entities:
                return

        sf = getattr(self, "_scaled_foliage", {})
        c_frames = sf.get("chickens", [])
        if not c_frames:
            return

        for ch in self.chicken_entities:
            f_idx = min(len(c_frames) - 1, max(0, ch["frame_idx"]))
            frame_surf = c_frames[f_idx]

            if ch["facing_left"]:
                frame_surf = pygame.transform.flip(frame_surf, True, False)

            hop = ch.get("hop", 0) * self.camera.zoom
            sx, sy = self.camera.world_to_screen(ch["x"], ch["y"] + hop)
            self.screen.blit(frame_surf, (int(sx), int(sy)))

    def _draw_sprite(self, sprite, wx, wy, alpha: int = 255):
        sx, sy = self.camera.world_to_screen(wx, wy)
        nw = max(1, int(round(sprite.get_width() * self.camera.zoom)))
        nh = max(1, int(round(sprite.get_height() * self.camera.zoom)))
        # Nearest-Neighbor scaling untuk sprite karakter (bebas burik & tajam)
        scaled = pygame.transform.scale(sprite, (nw, nh))
        if alpha < 255:
            scaled = scaled.copy()
            scaled.set_alpha(alpha)
        # Anchor kaki tepat di batas bawah ubin (midbottom) agar karakter berdiri pas di dalam ubinnya
        tile_bottom_sy = sy + (self.map.cell_size * self.camera.zoom) / 2.0
        rect = scaled.get_rect(midbottom=(int(round(sx)), int(round(tile_bottom_sy))))
        self.screen.blit(scaled, rect)

    def _draw_call_bubble(self):
        sx, sy = self.camera.world_to_screen(self.player.px, self.player.py)
        text = "Bolu!!"
        surf = self.fonts["bubble"].render(text, True, (20, 20, 26))
        pad_x, pad_y = 10, 6
        w = surf.get_width() + pad_x * 2
        h = surf.get_height() + pad_y * 2
        rect = pygame.Rect(0, 0, w, h)
        top_head_sy = sy + (self.map.cell_size * self.camera.zoom) / 2.0 - (32 * self.camera.zoom)
        rect.midbottom = (int(sx), int(top_head_sy - 4))
        pygame.draw.rect(self.screen, (255, 255, 255), rect, border_radius=4)
        pygame.draw.rect(self.screen, (30, 30, 40), rect, 1, border_radius=4)
        self.screen.blit(surf, (rect.x + pad_x, rect.y + pad_y))

    def _draw_stealth_badge(self):
        """Gambar lencana mengambang di atas kepala pemain saat bersembunyi di semak."""
        sx, sy = self.camera.world_to_screen(self.player.px, self.player.py)
        font = self.fonts.get("tiny") or pygame.font.Font(None, 13)
        text = "Sembunyi"
        surf = font.render(text, True, (245, 255, 240))
        pad_x, pad_y = 6, 2
        w = surf.get_width() + pad_x * 2
        h = surf.get_height() + pad_y * 2
        badge_rect = pygame.Rect(0, 0, w, h)
        top_head_sy = sy + (self.map.cell_size * self.camera.zoom) / 2.0 - (32 * self.camera.zoom)
        badge_rect.midbottom = (int(sx), int(top_head_sy - 4))
        bg_surf = pygame.Surface((w, h), SRCALPHA)
        pygame.draw.rect(bg_surf, (30, 90, 45, 215), bg_surf.get_rect(), border_radius=4)
        pygame.draw.rect(bg_surf, (110, 220, 140), bg_surf.get_rect(), 1, border_radius=4)
        self.screen.blit(bg_surf, badge_rect)
        self.screen.blit(surf, (badge_rect.x + pad_x, badge_rect.y + pad_y))

    def _draw_tower_portal(self):
        """Merender aura portal Menara Kuno (Abandoned Tower) di (38, 5)."""
        portal_pos = getattr(self.map, "boss_portal", {"x": 38, "y": 5})
        pt_x, pt_y = portal_pos.get("x", 38), portal_pos.get("y", 5)
        wx = pt_x * 16 + 8
        wy = pt_y * 16 + 8
        sx, sy = self.camera.world_to_screen(wx, wy)

        rune_count = len(getattr(self.player, "rune_keys", []))
        is_ready = rune_count >= 3

        ticks = pygame.time.get_ticks()
        pulse = (math.sin(ticks * 0.005) + 1.0) * 0.5
        radius = int(round((16 + pulse * 6) * self.camera.zoom))

        aura_surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), SRCALPHA)
        if is_ready:
            aura_color = (175, 70, 255, int(90 + pulse * 60))
            ring_color = (255, 225, 110, int(160 + pulse * 70))
        else:
            aura_color = (60, 120, 210, int(60 + pulse * 40))
            ring_color = (120, 180, 255, int(110 + pulse * 50))

        pygame.draw.circle(aura_surf, aura_color, (radius + 2, radius + 2), radius)
        pygame.draw.circle(aura_surf, ring_color, (radius + 2, radius + 2), radius, width=2)
        self.screen.blit(aura_surf, (int(sx - radius - 2), int(sy - radius - 2)))

        dx = abs(self.player.grid[0] - pt_x)
        dy = abs(self.player.grid[1] - pt_y)
        if max(dx, dy) <= 3:
            font = self.fonts.get("bubble", self.fonts.get("sm"))
            font_sub = self.fonts.get("tiny") or pygame.font.Font(None, 12)
            if is_ready:
                main_txt = "[E] Masuk Menara Kuno & Hadapi Boss Kage!"
                sub_txt = "3/3 Kunci Rune Terpasang • Portal Siap!"
                col = (255, 235, 140)
                border_col = (195, 120, 255)
                bg_col = (45, 20, 60, 235)
            else:
                main_txt = f"Gerbang Tersegel ({rune_count}/3 Kunci)"
                sub_txt = "Kumpulkan 3 Kunci Rune dari peti untuk membuka!"
                col = (220, 225, 235)
                border_col = (100, 150, 220)
                bg_col = (25, 35, 55, 230)

            t_surf = font.render(main_txt, True, col)
            s_surf = font_sub.render(sub_txt, True, (210, 200, 190))
            pad_x, pad_y = 12, 6
            bw = max(t_surf.get_width(), s_surf.get_width()) + pad_x * 2
            bh = t_surf.get_height() + s_surf.get_height() + pad_y * 2 + 2
            bx = int(sx - bw // 2)
            by = int(sy - radius - bh - 8)

            box_surf = pygame.Surface((bw, bh), SRCALPHA)
            pygame.draw.rect(box_surf, bg_col, box_surf.get_rect(), border_radius=6)
            pygame.draw.rect(box_surf, border_col, box_surf.get_rect(), 1, border_radius=6)
            self.screen.blit(box_surf, (bx, by))
            self.screen.blit(t_surf, (bx + (bw - t_surf.get_width()) // 2, by + pad_y))
            self.screen.blit(s_surf, (bx + (bw - s_surf.get_width()) // 2, by + pad_y + t_surf.get_height() + 2))

    def _draw_whistle_waves(self):
        """Menggambar cincin gelombang suara ekspansif saat siulan dibunyikan."""
        for wave in self.whistle_waves:
            wx, wy = wave["pos"]
            sx, sy = self.camera.world_to_screen(wx, wy)
            r = int(round(wave["radius"] * self.camera.zoom))
            if r <= 2:
                continue
            surf = pygame.Surface((r * 2 + 4, r * 2 + 4), SRCALPHA)
            alpha = wave.get("alpha", 180)
            color = (255, 230, 100, alpha)
            pygame.draw.circle(surf, color, (r + 2, r + 2), r, width=2)
            if r > 15:
                inner_r = max(2, r - int(12 * self.camera.zoom))
                inner_col = (255, 245, 180, int(alpha * 0.6))
                pygame.draw.circle(surf, inner_col, (r + 2, r + 2), inner_r, width=1)
            self.screen.blit(surf, (int(sx - r - 2), int(sy - r - 2)))

    def _draw_npc_speech_bubbles(self):
        """Menggambar balon dialog percakapan dan respon sensorik di atas kepala NPC."""
        for n in (self.npc, self.npc_kuro, self.npc_shiro):
            if n and getattr(n, "speech_bubble", None):
                sx, sy = self.camera.world_to_screen(n.px, n.py)
                font = self.fonts.get("bubble") or pygame.font.Font(None, 14)
                surf = font.render(n.speech_bubble, True, (35, 25, 20))
                pad_x, pad_y = 8, 4
                bw = surf.get_width() + pad_x * 2
                bh = surf.get_height() + pad_y * 2
                bx = int(sx - bw // 2)
                top_head_sy = sy + (self.map.cell_size * self.camera.zoom) / 2.0 - (32 * self.camera.zoom)
                by = int(top_head_sy - 6 - bh)
                b_surf = pygame.Surface((bw, bh), SRCALPHA)
                pygame.draw.rect(b_surf, (255, 253, 246, 235), b_surf.get_rect(), border_radius=5)
                pygame.draw.rect(b_surf, (200, 160, 110), b_surf.get_rect(), 1, border_radius=5)
                self.screen.blit(b_surf, (bx, by))
                self.screen.blit(surf, (bx + pad_x, by + pad_y))

    def _draw_ai_ticker_banner(self):
        """Menggambar banner notifikasi cerdas AI Ticker di bagian tengah atas layar dengan tema Cozy Warm Parchment."""
        if not self.ai_ticker_info or self.ai_ticker_info.get("timer", 0.0) <= 0:
            return

        w, h = self.screen.get_size()
        panel_w = self.camera.left_panel_w
        free_w = w - panel_w
        cx = panel_w + free_w // 2

        title = self.ai_ticker_info.get("title", "")
        detail = self.ai_ticker_info.get("detail", "")
        timer = self.ai_ticker_info.get("timer", 0.0)
        alpha = min(255, int(255 * (timer / 0.35))) if timer < 0.35 else 255

        font_t = self.fonts.get("bubble", self.fonts.get("sm"))
        font_d = self.fonts.get("tiny") or pygame.font.Font(None, 13)

        # Pilih aksen warna yang harmonis sesuai jenis notifikasi
        if "SOUND PERCEPT" in title:
            t_col = (30, 110, 175)
            accent_col = (50, 135, 205)
        elif "GERBANG TERKUNCI" in title:
            t_col = (185, 50, 35)
            accent_col = (215, 70, 50)
        elif "RESOLUTION" in title:
            t_col = (35, 125, 55)
            accent_col = (55, 155, 75)
        else:
            t_col = (155, 75, 15)
            accent_col = (205, 135, 25)

        t_surf = font_t.render(title, True, t_col)
        d_surf = font_d.render(detail, True, (65, 48, 36))

        pad_x, pad_y = 20, 9
        bw = max(t_surf.get_width(), d_surf.get_width()) + pad_x * 2 + 10
        bh = t_surf.get_height() + d_surf.get_height() + pad_y * 2 + 5
        bx = cx - bw // 2
        by = 16

        # Bayangan lembut (Drop shadow)
        shadow_surf = pygame.Surface((bw, bh), SRCALPHA)
        pygame.draw.rect(shadow_surf, (45, 35, 25, int(35 * (alpha / 255.0))), (0, 0, bw, bh), border_radius=10)
        self.screen.blit(shadow_surf, (bx + 2, by + 3))

        # Kartu utama tema Cozy Warm Parchment
        bg_surf = pygame.Surface((bw, bh), SRCALPHA)
        pygame.draw.rect(bg_surf, (255, 253, 248, min(246, alpha)), bg_surf.get_rect(), border_radius=10)
        # Garis aksen vertikal di tepi kiri banner
        pygame.draw.rect(bg_surf, (*accent_col[:3], alpha), pygame.Rect(5, 6, 4, bh - 12), border_radius=2)
        # Border ganda elegan
        pygame.draw.rect(bg_surf, (212, 186, 150, alpha), (0, 0, bw, bh), 2, border_radius=10)
        pygame.draw.rect(bg_surf, (255, 255, 255, min(200, alpha)), (1, 1, bw - 2, bh - 2), 1, border_radius=9)
        self.screen.blit(bg_surf, (bx, by))

        if alpha < 255:
            t_surf.set_alpha(alpha)
            d_surf.set_alpha(alpha)

        self.screen.blit(t_surf, (bx + pad_x + 6, by + pad_y))
        self.screen.blit(d_surf, (bx + pad_x + 6, by + pad_y + t_surf.get_height() + 4))

    def _trigger_whistle(self):
        """Picu peluit / pancingan suara Bolu (Whistle Mechanic [SPASI] - plan_dev.md Section 4.2)."""
        self.player.show_call_bubble()
        # Efek visual cincin audio yang melebar
        self.whistle_waves.append({
            "pos": (self.player.px, self.player.py),
            "radius": 12.0,
            "max_radius": float(config.WHISTLE_RADIUS) * config.TILE_SIZE,
            "speed": 240.0,
            "alpha": 220,
        })
        if hasattr(self, "audio") and hasattr(self.audio, "play_chest_prompt"):
            self.audio.play_chest_prompt()

        heard_count = 0
        all_npcs = [getattr(self, "npc", None), getattr(self, "npc_kuro", None), getattr(self, "npc_shiro", None)]
        for n in all_npcs:
            if n and hasattr(n, "on_noise_heard"):
                if n.on_noise_heard(self.player.grid):
                    heard_count += 1

        if heard_count > 0:
            self.refresh_search_focus(force=True)
            self.ai_ticker_info = {
                "title": f"[SOUND PERCEPT] Siulan Bolu Didengar ({heard_count} NPC Menyelidiki)!",
                "detail": "Stimulus audio memicu peralihan state NPC ke INVESTIGATING (5.0s) menuju titik siulan.",
                "timer": 3.8,
            }
        else:
            self.ai_ticker_info = {
                "title": f"[SOUND PERCEPT] Siulan Bolu Berbunyi -> Tidak ada NPC dalam jangkauan dengar ({config.WHISTLE_RADIUS} ubin).",
                "detail": "Suara peluit tidak mencapai radius pendengaran NPC di sekeliling peta.",
                "timer": 2.5,
            }

    def _trigger_chase(self):
        """Callback dari tombol Panggil NPC di tab companion."""
        self._trigger_whistle()

    def _interact_tower_portal(self):
        """Interaksi dengan Portal Menara Kuno (Abandoned Tower) menuju Boss Battle."""
        rune_count = len(getattr(self.player, "rune_keys", []))
        if rune_count < 3:
            needed = 3 - rune_count
            self.ai_ticker_info = {
                "title": f"[GERBANG TERKUNCI] Butuh 3 Kunci Rune ({rune_count}/3 Terkumpul)!",
                "detail": f"Buka {needed} peti harta lagi di penjuru peta untuk melengkapi segel Portal Menara Kuno.",
                "timer": 4.0,
            }
            if hasattr(self, "audio") and hasattr(self.audio, "play_chest_prompt"):
                self.audio.play_chest_prompt()
            return

        # Jika sudah memiliki 3 kunci, buktikan klausa logika KB (Resolution Refutation)
        proved, steps, summary = False, [], None
        if hasattr(self, "inter_npc_manager") and self.inter_npc_manager:
            proved, steps, summary = self.inter_npc_manager.can_open_portal()

        self.ai_ticker_info = {
            "title": "[KB RESOLUTION] HasKey_A & HasKey_B & HasKey_C => PortalActive [TERBUKTI!]",
            "detail": "Segel gerbang Menara Kuno terbuka! Memasuki pertarungan menghadapi Boss Kage!",
            "timer": 4.5,
        }
        # Masuk fase Pre-Battle Boss Kage (bisa atur kesulitan di Tab 05-06 sebelum duel)
        self.enter_boss_pre_battle()

    # =========================================================================
    # MATERI 09: DECISION UNDER UNCERTAINTY (BAYESIAN BELIEF SONAR & RELIK)
    # =========================================================================

    def _init_relic_sonar(self):
        """Menempatkan Relik Tersembunyi secara acak di daratan walkable & menginisialisasi Prior seragam."""
        blocked = {tuple(c["pos"]) for c in getattr(self, "chests", [])}
        portal = getattr(self.map, "boss_portal", {"x": 38, "y": 5})
        blocked.add((portal.get("x", 38), portal.get("y", 5)))
        player_g = getattr(self.player, "grid", (0, 0)) if getattr(self, "player", None) else (0, 0)

        walkable = []
        for gx in range(self.map.width):
            for gy in range(self.map.height):
                pos = (gx, gy)
                if pos in blocked:
                    continue
                if self.map.is_walkable(pos):
                    walkable.append(pos)

        far_candidates = [p for p in walkable if abs(p[0] - player_g[0]) + abs(p[1] - player_g[1]) >= 10]
        pool = far_candidates or [p for p in walkable if p != player_g] or walkable
        relic_pos = random.choice(pool) if pool else None

        if getattr(self, "relic_sonar", None) is None:
            self.relic_sonar = BayesianRelicSonar(walkable, sensor_accuracy=0.82)
            self.relic_sonar.reset(walkable_cells=walkable, relic_pos=relic_pos)
        else:
            self.relic_sonar.reset(walkable_cells=walkable, relic_pos=relic_pos)

    def _trigger_sonar_scan(self):
        """Memancarkan gelombang sonar Cyan [F] tanpa memancing NPC & memperbarui Belief via Bayes' Rule."""
        sonar = getattr(self, "relic_sonar", None)
        if not sonar:
            return
        # Matikan overlay jalur pathfinding A* agar tampilan heatmap sonar tetap bersih
        if hasattr(self, "overlay") and self.overlay:
            self.overlay.show_path_visualization = False
            self.overlay.stop_path_animation()
            dock = getattr(self.overlay, "dock", None)
            tab_search = dock.tabs.get(1) if dock and hasattr(dock, "tabs") else None
            if tab_search and hasattr(tab_search, "btn_toggle_path"):
                tab_search.show_path_line = False
                tab_search.btn_toggle_path.text = "Toggle Jalur di Peta: OFF"
        if sonar.found:
            self.ai_ticker_info = {
                "title": "[BAYES SONAR] Relik Ikan Emas Kuno sudah ditemukan!",
                "detail": "Buff Relik sudah aktif di inventaris Bolu untuk melawan Boss Kage.",
                "timer": 3.5,
            }
            return

        self.sonar_waves.append({
            "pos": (self.player.px, self.player.py),
            "radius": 10.0,
            "alpha": 225.0,
        })
        res = sonar.scan(self.player.grid)
        mp = res["map_pos"]
        mp_txt = f"({mp[0]}, {mp[1]})" if mp else "-"
        noise_tag = " [Sinyal Ber-noise]" if res["is_noisy"] else ""
        self.ai_ticker_info = {
            "title": f"[BAYES SONAR #{res['scan_num']}] Sinyal: {res['signal']}{noise_tag}",
            "detail": f"Puncak Peluang: {res['map_prob'] * 100:.2f}% di {mp_txt} | Entropi: {res['entropy']:.2f} bit",
            "timer": 4.5,
        }

    def _collect_hidden_relic(self):
        """Mengambil Relik Tersembunyi saat Bolu menginjak lokasinya."""
        sonar = getattr(self, "relic_sonar", None)
        if not sonar or sonar.found:
            return
        sonar.found = True
        self.player.atk_bonus += 10
        self.player.def_bonus += 6
        self.player.persistent_hp = config.MAX_HP
        self.player.persistent_potions += 1
        if hasattr(self.player, "inventory") and "Relik Ikan Emas" not in self.player.inventory:
            self.player.inventory.append("Relik Ikan Emas")
        if hasattr(self, "overlay") and hasattr(self.overlay, "nav_rail"):
            self.overlay.nav_rail.set_badge(6, active=True, color=config.COLOR_STATUS_SUCCESS)
        self.ai_ticker_info = {
            "title": "[RELIK DITEMUKAN!] Relik Ikan Emas Kuno diperoleh!",
            "detail": "HP Pulih Penuh, +10 ATK, +6 DEF, & +1 Ramuan untuk persiapan Boss Kage!",
            "timer": 5.5,
        }

    def _draw_relic_heatmap(self):
        """Merender heatmap probabilitas Bayesian Belief sebagai kabut gradien halus (smoothscale)."""
        sonar = getattr(self, "relic_sonar", None)
        if not sonar or not sonar.heatmap_visible:
            return
        if sonar.scan_count <= 0 and not sonar.found:
            return
        map_pos, max_p = sonar.get_map_estimate()
        zoom = self.camera.zoom
        sz = max(4, int(round(self.map.cell_size * zoom)))

        if sonar.scan_count > 0 and max_p > 0.0 and sonar.belief:
            n_cells = max(1, len(sonar.belief))
            uniform_p = 1.0 / float(n_cells)
            concentration = max_p / uniform_p
            high_count = sum(1 for p in sonar.belief.values() if p >= 0.70 * max_p)
            focus_t = min(1.0, max(0.0, (concentration - 1.2) / 4.0))

            cache = getattr(self, "_heatmap_cache", None)
            cache_key = (sonar.scan_count, sonar.relic_pos, round(zoom, 3), id(sonar.belief))
            if cache and cache.get("key") == cache_key:
                heat_surf = cache["surf"]
            else:
                mw, mh = self.map.width, self.map.height
                grid_surf = pygame.Surface((mw, mh), SRCALPHA)
                for (gx, gy), prob in sonar.belief.items():
                    ratio = prob / max_p
                    if ratio < 0.30:
                        continue
                    if ratio >= 0.65:
                        t = min(1.0, (ratio - 0.65) / 0.35)
                        r = 255
                        g = int(210 - 55 * t)
                        b = int(65 - 35 * t)
                        a = int((55 + 75 * focus_t) * (0.55 + 0.45 * t))
                    else:
                        t = (ratio - 0.30) / 0.35
                        r = int(45 + 115 * t)
                        g = int(195 + 18 * t)
                        b = int(225 - 60 * t)
                        a = int(24 + 34 * t)
                    if 0 <= gx < mw and 0 <= gy < mh:
                        grid_surf.set_at((gx, gy), (r, g, b, max(0, min(255, a))))

                mid_surf = pygame.transform.smoothscale(grid_surf, (max(1, mw * 3), max(1, mh * 3)))
                target_w = max(1, int(round(self.map_w * zoom)))
                target_h = max(1, int(round(self.map_h * zoom)))
                heat_surf = pygame.transform.smoothscale(mid_surf, (target_w, target_h))
                self._heatmap_cache = {"key": cache_key, "surf": heat_surf}

            self.screen.blit(heat_surf, (int(self.camera.offset_x), int(self.camera.offset_y)))

            # 1. Penanda Tebakan AI Terbaik (MAP) -> Siku bidik Cyan (berbeda dari Relik asli)
            if map_pos and sonar.scan_count >= 2 and high_count <= 150:
                wx, wy = self.map.world_to_px(map_pos)
                sx, sy = self.camera.world_to_screen(wx, wy)
                half = max(6, sz // 2 - 2)
                arm = max(4, half // 2)
                cx_m, cy_m = int(sx), int(sy)
                cyan_col = (25, 175, 225)
                for dx_s, dy_s in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                    px_c = cx_m + dx_s * half
                    py_c = cy_m + dy_s * half
                    pygame.draw.line(self.screen, cyan_col, (px_c, py_c), (px_c - dx_s * arm, py_c), 2)
                    pygame.draw.line(self.screen, cyan_col, (px_c, py_c), (px_c, py_c - dy_s * arm), 2)

        # 2. Penanda Relik Asli (muncul saat <= 2 ubin, atau selalu tampil untuk demo setelah ditemukan jika Heatmap ON)
        if sonar.relic_pos:
            d = abs(self.player.grid[0] - sonar.relic_pos[0]) + abs(self.player.grid[1] - sonar.relic_pos[1])
            if sonar.found or d <= 2:
                wx, wy = self.map.world_to_px(sonar.relic_pos)
                sx, sy = self.camera.world_to_screen(wx, wy)
                bob = 0.0 if sonar.found else math.sin(pygame.time.get_ticks() * 0.007) * 2.5
                rx_c, ry_c = int(sx), int(sy + bob)
                r_gem = max(6, int(sz * 0.28))
                pts = [(rx_c, ry_c - r_gem), (rx_c + r_gem, ry_c), (rx_c, ry_c + r_gem), (rx_c - r_gem, ry_c)]
                pygame.draw.polygon(self.screen, (255, 215, 55), pts)
                border_c = (45, 165, 75) if sonar.found else (170, 95, 15)
                pygame.draw.polygon(self.screen, border_c, pts, 2)
                pygame.draw.circle(self.screen, (255, 250, 220), (rx_c - r_gem // 4, ry_c - r_gem // 4), max(2, r_gem // 4))

    def _draw_sonar_waves(self):
        """Menggambar cincin gelombang sonar warna Cyan saat [F] ditekan."""
        for wave in getattr(self, "sonar_waves", []):
            wx, wy = wave["pos"]
            sx, sy = self.camera.world_to_screen(wx, wy)
            r = int(round(wave["radius"] * self.camera.zoom))
            if r <= 2:
                continue
            surf = pygame.Surface((r * 2 + 4, r * 2 + 4), SRCALPHA)
            alpha = max(0, min(255, int(wave.get("alpha", 200))))
            pygame.draw.circle(surf, (45, 205, 230, alpha), (r + 2, r + 2), r, width=2)
            if r > 14:
                inner_r = max(2, r - int(10 * self.camera.zoom))
                pygame.draw.circle(surf, (150, 240, 255, int(alpha * 0.55)), (r + 2, r + 2), inner_r, width=1)
            self.screen.blit(surf, (int(sx - r - 2), int(sy - r - 2)))

    # =========================================================================
    # KLIK-UNTUK-INSPEKSI ELEMEN MAP (O(1) SAAT KLIK, NOL BEBAN IDLE)
    # =========================================================================

    def _get_layer3_lookup(self) -> Dict[Tuple[int, int], Tuple[str, int, int]]:
        """Cache peta (gx, gy) -> (src, atlas_x, atlas_y) dari layer objek teratas (ordered_layers[-1])."""
        cache = getattr(self, "_layer3_lookup_cache", None)
        if cache is not None:
            return cache
        lookup: Dict[Tuple[int, int], Tuple[str, int, int]] = {}
        skip_tokens = ("wood_bridge", "tilled_dirt", "grass.png", "water.png")

        for src_dict in (getattr(self.map, "decorations", {}), getattr(self.map, "obstacles", {})):
            for pos, val in src_dict.items():
                if isinstance(val, tuple) and len(val) >= 3 and val[0]:
                    if not any(tk in val[0].lower() for tk in skip_tokens):
                        lookup[pos] = (val[0], int(val[1]), int(val[2]))

        ordered = getattr(self.map, "ordered_layers", [])
        if ordered:
            for pos, val in ordered[-1]:
                if isinstance(val, tuple) and len(val) >= 3 and val[0]:
                    if not any(tk in val[0].lower() for tk in skip_tokens):
                        lookup[pos] = (val[0], int(val[1]), int(val[2]))

        self._layer3_lookup_cache = lookup
        return lookup

    def _object_group_key(self, src: str, ax: int, ay: int) -> str:
        """Kunci grup objek agar BFS hanya menyatukan ubin dari benda yang sama."""
        s = src.lower()
        if "ext_10a" in s:
            if ax == 7 and ay in (9, 10):
                return "ext_lamp"
            if ax in (9, 10) and ay in (9, 10):
                return "ext_tree_2x2"
            if ax == 11 and ay in (9, 10):
                return "ext_tree_1x2"
            return "ext_building"
        if "objects.png" in s:
            if ax in (3, 4) and ay in (3, 4):
                return "obj_table"
            if ax == 3 and ay == 0:
                return "obj_sign"
            return f"obj_{ax}_{ay}"
        if "basic_grass_biom_things" in s:
            if ay <= 1 and ax <= 4:
                return "bio_tree"
            return "bio_prop"
        return s

    def _collect_connected_same_src(
        self, start: Tuple[int, int], target_key: str, lookup: Dict[Tuple[int, int], Tuple[str, int, int]], max_tiles: int = 80
    ) -> List[Tuple[int, int]]:
        """Mengumpulkan seluruh ubin terhubung milik satu objek yang sama (BFS cepat saat klik)."""
        from collections import deque

        visited = {start}
        q = deque([start])
        while q and len(visited) < max_tiles:
            cx, cy = q.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = (cx + dx, cy + dy)
                if nb in visited:
                    continue
                meta = lookup.get(nb)
                if meta and self._object_group_key(meta[0], meta[1], meta[2]) == target_key:
                    visited.add(nb)
                    q.append(nb)
        return list(visited)

    def _classify_layer3_object(self, src: str, ax: int, ay: int) -> Tuple[str, str, str, Tuple[int, int, int]]:
        """Mengembalikan (badge, title, detail, color) yang spesifik sesuai aset & koordinat atlas."""
        s = src.lower()
        if "abandoned tower" in s:
            return ("BANGUNAN", "Menara Kuno (Sarang Boss)", "Markas Boss Kage (Obstacle): masuk lewat portal depan dengan 3 Kunci Rune.", (135, 70, 195))
        if "clock tower" in s:
            return ("BANGUNAN", "Menara Jam", "Bangunan menara (Obstacle): memblokir rute Pathfinding A* & UCS.", (175, 80, 60))
        if "mansion" in s:
            return ("BANGUNAN", "Mansion", "Bangunan besar (Obstacle): tidak dapat dilewati Player maupun NPC.", (175, 80, 60))
        if "merchant house" in s:
            return ("BANGUNAN", "Rumah Pedagang", "Bangunan desa (Obstacle): tidak dapat dilewati Player maupun NPC.", (175, 80, 60))
        if "painters house" in s:
            return ("BANGUNAN", "Rumah Pelukis", "Bangunan desa (Obstacle): tidak dapat dilewati Player maupun NPC.", (175, 80, 60))
        if "workshop house" in s:
            return ("BANGUNAN", "Bengkel / Workshop", "Bangunan desa (Obstacle): tidak dapat dilewati Player maupun NPC.", (175, 80, 60))
        if "chicken_house" in s:
            return ("BANGUNAN", "Kandang Ayam", "Kandang desa (Obstacle): memblokir rute Pathfinding.", (175, 80, 60))
        if "ext_10a" in s:
            if ax == 7 and ay in (9, 10):
                return ("DEKORASI", "Lampu Taman (1x2)", "Lampu penerangan desa (Obstacle): memblokir jalur Pathfinding.", (195, 135, 35))
            if ax in (9, 10) and ay in (9, 10):
                return ("POHON", "Pohon Rindang (2x2)", "Obstacle alami: 4 ubin pohon ini diblokir di Pathfinding A* & UCS.", (45, 145, 75))
            if ax == 11 and ay in (9, 10):
                return ("POHON", "Pohon Ramping (1x2)", "Obstacle alami: 2 ubin pohon ini diblokir di Pathfinding A* & UCS.", (45, 145, 75))
            return ("BANGUNAN", "Bangunan Desa", "Struktur bangunan (Obstacle): diblokir di grid Pathfinding.", (175, 80, 60))
        if "fences" in s:
            return ("PAGAR", "Pagar Kayu", "Pembatas jalan (Obstacle): menghalangi jalur Player & NPC.", (165, 105, 45))
        if "hills" in s:
            return ("TEBING", "Tebing / Bukit", "Kontur tinggi (Obstacle): membatasi area dataran.", (155, 100, 55))
        if "basic_grass_biom_things" in s:
            if ay <= 1 and ax <= 4:
                return ("POHON", "Pohon", "Obstacle alami: diblokir di grid Pathfinding A* & UCS.", (45, 145, 75))
            return ("OBJEK", "Batu / Tunggul / Dekorasi", "Objek alam di peta (Obstacle bila tidak bisa dilewati).", (140, 110, 80))
        if "objects.png" in s:
            if ax in (3, 4) and ay in (3, 4):
                return ("OBJEK", "Meja Kayu (2x2)", "Meja taman di tengah pulau (Obstacle): tidak bisa dilewati.", (155, 100, 50))
            if ax == 3 and ay == 0:
                return ("OBJEK", "Papan Petunjuk", "Penanda jalan di pulau.", (155, 105, 55))
            return ("DEKORASI", "Properti Desa", "Objek dekorasi peta.", (145, 115, 65))
        return ("OBJEK", "Objek Peta", "Elemen lingkungan pada peta.", (145, 115, 65))

    def _handle_map_inspect_click(self, pos: Tuple[int, int]):
        """Mengidentifikasi objek utuh (multi-ubin) atau terrain pada peta yang diklik kiri."""
        if getattr(self, "gacha_active", False) or getattr(self, "gacha_showcase", None):
            return
        wx = (pos[0] - self.camera.offset_x) / max(0.01, self.camera.zoom)
        wy = (pos[1] - self.camera.offset_y) / max(0.01, self.camera.zoom)
        gx = int(wx // self.map.cell_size)
        gy = int(wy // self.map.cell_size)
        if not (0 <= gx < self.map.width and 0 <= gy < self.map.height):
            self.inspected_tile = None
            return
        grid_pos = (gx, gy)
        cur = getattr(self, "inspected_tile", None)
        if cur and grid_pos in cur.get("tiles", [cur.get("pos")]):
            self.inspected_tile = None
            return

        tiles = [grid_pos]
        if grid_pos == self.player.grid:
            hidden_note = " (Tersembunyi di semak)" if getattr(self.player, "is_hidden", False) else ""
            info = ("PLAYER", f"Bolu (Hero){hidden_note}", "Karakter utama: gerakkan dengan WASD/Panah.", (55, 145, 90))
        else:
            npc_hit = next(
                (n for n in (getattr(self, "npc", None), getattr(self, "npc_kuro", None), getattr(self, "npc_shiro", None)) if n and n.grid == grid_pos),
                None,
            )
            if npc_hit:
                st = "Mengejar Bolu!" if npc_hit.chasing else ("Investigasi Suara" if getattr(npc_hit, "investigating", False) else "Patroli Rute A*/UCS")
                info = ("NPC AI", npc_hit.name, f"Status: {st} | Sentuh untuk Pre-Battle.", (205, 115, 30))
            else:
                chest_hit = next((c for c in getattr(self, "chests", []) if tuple(c["pos"]) == grid_pos), None)
                portal = getattr(self.map, "boss_portal", {"x": 38, "y": 5})
                portal_pos = (portal.get("x", 38), portal.get("y", 5))
                sonar = getattr(self, "relic_sonar", None)
                relic_visible = bool(
                    sonar and sonar.relic_pos == grid_pos and (
                        sonar.found or abs(self.player.grid[0] - gx) + abs(self.player.grid[1] - gy) <= 2
                    )
                )
                if chest_hit:
                    opened = chest_hit.get("opened", False)
                    info = (
                        "PETI",
                        f"Peti Harta ({'Terbuka' if opened else 'Tersegel'})",
                        "Sudah diambil." if opened else "Dekati & tekan [E] untuk gacha + trigger KB & PDDL.",
                        (195, 135, 30),
                    )
                elif grid_pos == portal_pos:
                    rk = len(getattr(self.player, "rune_keys", []))
                    info = ("BOSS PORTAL", "Portal Menara Kuno", f"Butuh 3 Kunci Rune (Saat ini: {rk}/3) untuk lawan Boss Kage.", (135, 70, 195))
                elif relic_visible:
                    info = ("RELIK M9", "Relik Ikan Emas Kuno", "Artefak Materi 09: +10 ATK, +6 DEF, HP Penuh & +1 Potion.", (210, 145, 25))
                elif self.map.is_bush(grid_pos):
                    info = ("STEALTH", "Semak Persembunyian", "Bolu tak terlihat NPC dari jarak > 1 ubin saat di sini.", (45, 145, 75))
                else:
                    # Cek Pohon 2x2 (trees / trees_pink) dan Pohon 1x2 (trees_small)
                    fol = getattr(self.map, "foliage", {}) or {}
                    tree_tiles = None
                    for tx, ty in fol.get("trees", []) + fol.get("trees_pink", []):
                        box = [(tx, ty), (tx + 1, ty), (tx, ty + 1), (tx + 1, ty + 1)]
                        if grid_pos in box:
                            tree_tiles = box
                            break
                    if not tree_tiles:
                        for tx, ty in fol.get("trees_small", []):
                            box = [(tx, ty), (tx, ty + 1)]
                            if grid_pos in box:
                                tree_tiles = box
                                break

                    if tree_tiles:
                        tiles = tree_tiles
                        sz_lbl = "2x2" if len(tree_tiles) == 4 else "1x2"
                        info = ("POHON", f"Pohon ({sz_lbl})", f"Obstacle alami ({len(tree_tiles)} ubin): diblokir di grid Pathfinding A* & UCS.", (45, 145, 75))
                    else:
                        l3 = self._get_layer3_lookup()
                        if grid_pos in l3:
                            src, ax, ay = l3[grid_pos]
                            info = self._classify_layer3_object(src, ax, ay)
                            g_key = self._object_group_key(src, ax, ay)
                            tiles = self._collect_connected_same_src(grid_pos, g_key, l3)
                        elif grid_pos in self.map.water and grid_pos not in getattr(self.map, "bridge_set", set()):
                            info = ("AIR", "Sungai / Perairan", "Rintangan alami: tidak dapat dilewati Player & NPC.", (45, 130, 195))
                        elif grid_pos in self.map.obstacle_set or not self.map.is_walkable(grid_pos):
                            info = ("OBSTACLE", "Rintangan Peta", "Ubin diblokir pada grid Pathfinding A* & UCS.", (185, 65, 65))
                        elif grid_pos in getattr(self.map, "bridge_set", set()):
                            info = ("JEMBATAN", "Jembatan Kayu", "Jalur penyeberangan sungai (Walkable, Cost: 2.0).", (155, 105, 55))
                        elif self.map.is_dirt_road(grid_pos):
                            info = ("COST 1.0", "Jalan Tanah", "Terrain Cost: 1.0 (Jalur prioritas tercepat bagi A*).", (165, 115, 45))
                        else:
                            info = ("COST 2.0", "Padang Rumput", "Terrain Cost: 2.0 (2x lebih berat dari jalan tanah di A*).", (75, 145, 75))

        self.inspected_tile = {
            "pos": grid_pos,
            "tiles": tiles,
            "badge": info[0],
            "title": info[1],
            "detail": info[2],
            "color": info[3],
        }

    def _draw_inspected_tile_popup(self):
        """Merender highlight objek utuh (seluruh ubin terhubung) & kartu info di atasnya."""
        info = getattr(self, "inspected_tile", None)
        if not info:
            return
        tiles = info.get("tiles") or [info["pos"]]
        tiles_set = set(tiles)
        zoom = self.camera.zoom
        sz = max(8, int(round(self.map.cell_size * zoom)))
        col = info["color"]

        # Hitung bounding box objek & gambar highlight menyatu (hanya garis tepi luar)
        min_x = min_y = 10**9
        max_x = max_y = -10**9
        hl = pygame.Surface((sz, sz), SRCALPHA)
        hl.fill((*col, 50))
        for tg in tiles:
            wx, wy = self.map.world_to_px(tg)
            sx, sy = self.camera.world_to_screen(wx, wy)
            rx, ry = int(sx - sz // 2), int(sy - sz // 2)
            self.screen.blit(hl, (rx, ry))
            min_x = min(min_x, rx)
            min_y = min(min_y, ry)
            max_x = max(max_x, rx + sz)
            max_y = max(max_y, ry + sz)
            gx, gy = tg
            if (gx, gy - 1) not in tiles_set:
                pygame.draw.line(self.screen, col, (rx, ry), (rx + sz, ry), 2)
            if (gx, gy + 1) not in tiles_set:
                pygame.draw.line(self.screen, col, (rx, ry + sz), (rx + sz, ry + sz), 2)
            if (gx - 1, gy) not in tiles_set:
                pygame.draw.line(self.screen, col, (rx, ry), (rx, ry + sz), 2)
            if (gx + 1, gy) not in tiles_set:
                pygame.draw.line(self.screen, col, (rx + sz, ry), (rx + sz, ry + sz), 2)

        font_tiny = self.fonts.get("tiny") or pygame.font.Font(None, 13)
        font_sm = self.fonts.get("sm") or pygame.font.Font(None, 16)
        b_surf = font_tiny.render(f"[{info['badge']}]", True, col)
        t_surf = font_sm.render(info["title"], True, (42, 32, 24))
        d_surf = font_tiny.render(info["detail"], True, (95, 80, 68))

        pad_x, pad_y = 10, 7
        cw = max(b_surf.get_width() + t_surf.get_width() + 26, d_surf.get_width() + pad_x * 2)
        ch = 44
        sw, sh = self.screen.get_size()
        left_w = self.camera.left_panel_w
        obj_cx = (min_x + max_x) // 2
        cx = max(left_w + 8, min(sw - cw - 8, obj_cx - cw // 2))
        cy = min_y - ch - 8
        if cy < 8:
            cy = min(sh - ch - 8, max_y + 8)
        card_r = pygame.Rect(cx, cy, cw, ch)

        card = pygame.Surface((cw, ch), SRCALPHA)
        pygame.draw.rect(card, (255, 253, 248, 246), card.get_rect(), border_radius=8)
        pygame.draw.rect(card, col, card.get_rect(), 2, border_radius=8)
        self.screen.blit(card, card_r.topleft)
        self.screen.blit(b_surf, (card_r.x + pad_x, card_r.y + pad_y))
        self.screen.blit(t_surf, (card_r.x + pad_x + b_surf.get_width() + 6, card_r.y + pad_y - 2))
        self.screen.blit(d_surf, (card_r.x + pad_x, card_r.y + pad_y + 17))
