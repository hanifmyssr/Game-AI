"""App: main loop + kamera + rendering, port dari Scenes/main.tscn + Duel Turn-Based Minimax (Tahap-2).
"""

import math
import os
import pygame

from . import config
from .events import GameManager
from .mapdata import MapData
from .overlay import DebugOverlay
from .player import Player
from .npc import NPC
from .battle_system import BattleSystem
from .battle_ai import ACTION_ATTACK, ACTION_HEAVY, ACTION_DEFEND, ACTION_POTION

MOUSEWHEEL = getattr(pygame, "MOUSEWHEEL", 1027)
K_EQUALS = getattr(pygame, "K_EQUALS", 61)
K_PLUS = getattr(pygame, "K_PLUS", 43)
K_MINUS = getattr(pygame, "K_MINUS", 45)
K_LCTRL = getattr(pygame, "K_LCTRL", 1073742048)
K_RCTRL = getattr(pygame, "K_RCTRL", 1073742052)
RESIZABLE = getattr(pygame, "RESIZABLE", 16)
QUIT = getattr(pygame, "QUIT", 256)
VIDEORESIZE = getattr(pygame, "VIDEORESIZE", 32769)
MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1025)
KEYDOWN = getattr(pygame, "KEYDOWN", 768)
SRCALPHA = getattr(pygame, "SRCALPHA", 0x00010000)
K_ESCAPE = getattr(pygame, "K_ESCAPE", 27)
K_TAB = getattr(pygame, "K_TAB", 9)
K_r = getattr(pygame, "K_r", 114)
K_1 = getattr(pygame, "K_1", 49)
K_a = getattr(pygame, "K_a", 97)
K_2 = getattr(pygame, "K_2", 50)
K_s = getattr(pygame, "K_s", 115)
K_3 = getattr(pygame, "K_3", 51)
K_d = getattr(pygame, "K_d", 100)
K_4 = getattr(pygame, "K_4", 52)
K_w = getattr(pygame, "K_w", 119)
K_UP = getattr(pygame, "K_UP", 1073741906)
K_DOWN = getattr(pygame, "K_DOWN", 1073741905)
K_LEFT = getattr(pygame, "K_LEFT", 1073741904)
K_RIGHT = getattr(pygame, "K_RIGHT", 1073741903)
K_SPACE = getattr(pygame, "K_SPACE", 32)
K_b = getattr(pygame, "K_b", 98)


class Camera:
    """Kamera yang mengikuti player dengan zoom yang dapat diubah."""

    def __init__(self, win_w, win_h, map_w, map_h, margin=0.02):
        self.zoom = 1.0
        self.fit_zoom = 1.0
        self.map_w = map_w
        self.map_h = map_h
        self.win_w = win_w
        self.win_h = win_h
        self.left_panel_w = config.DEBUG_LEFT_PANEL_WIDTH
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.reset(win_w, win_h, map_w, map_h, margin)

    def reset(self, win_w, win_h, map_w, map_h, margin=0.02, left_panel_w=None):
        self.win_w = win_w
        self.win_h = win_h
        self.map_w = map_w
        self.map_h = map_h
        self.left_panel_w = left_panel_w or config.DEBUG_LEFT_PANEL_WIDTH
        usable_w = max(100.0, win_w - self.left_panel_w)
        self.fit_zoom = min(usable_w / map_w, win_h / map_h) * (1.0 - margin)
        self.zoom = self.fit_zoom * 1.2
        self._center_map()

    def _center_map(self):
        usable_w = max(100.0, self.win_w - self.left_panel_w)
        scaled_w = self.map_w * self.zoom
        scaled_h = self.map_h * self.zoom
        self.offset_x = self.left_panel_w + (usable_w - scaled_w) / 2.0
        self.offset_y = (self.win_h - scaled_h) / 2.0

    def zoom_by(self, factor, focus_screen=None):
        old_zoom = self.zoom
        min_zoom = self.fit_zoom * 0.75
        max_zoom = self.fit_zoom * 2.5
        if focus_screen is None:
            usable_w = max(100.0, self.win_w - self.left_panel_w)
            focus_screen = (self.left_panel_w + usable_w / 2.0, self.win_h / 2.0)
        focus_world = (
            (focus_screen[0] - self.offset_x) / self.zoom,
            (focus_screen[1] - self.offset_y) / self.zoom,
        )
        self.zoom = max(min_zoom, min(max_zoom, self.zoom * factor))
        self.offset_x = focus_screen[0] - focus_world[0] * self.zoom
        self.offset_y = focus_screen[1] - focus_world[1] * self.zoom
        self._clamp_offset()
        return self.zoom != old_zoom

    def _clamp_offset(self):
        usable_w = max(100.0, self.win_w - self.left_panel_w)
        scaled_w = self.map_w * self.zoom
        scaled_h = self.map_h * self.zoom

        if scaled_w <= usable_w:
            self.offset_x = self.left_panel_w + (usable_w - scaled_w) / 2.0
        else:
            min_offset_x = self.left_panel_w + usable_w - scaled_w
            self.offset_x = max(min_offset_x, min(self.offset_x, self.left_panel_w))

        if scaled_h <= self.win_h:
            self.offset_y = (self.win_h - scaled_h) / 2.0
        else:
            min_offset_y = self.win_h - scaled_h
            self.offset_y = max(min_offset_y, min(self.offset_y, 0.0))

    def follow(self, world_pos):
        usable_w = max(100.0, self.win_w - self.left_panel_w)
        viewport_center_x = self.left_panel_w + usable_w / 2.0
        viewport_center_y = self.win_h / 2.0
        self.offset_x = viewport_center_x - world_pos[0] * self.zoom
        self.offset_y = viewport_center_y - world_pos[1] * self.zoom
        self._clamp_offset()

    def world_to_screen(self, wx, wy):
        return (wx * self.zoom + self.offset_x, wy * self.zoom + self.offset_y)


class App:
    def __init__(self):
        getattr(pygame, "init")()
        self.screen = pygame.display.set_mode(
            (config.WINDOW_WIDTH, config.WINDOW_HEIGHT), RESIZABLE
        )
        pygame.display.set_caption("BoluKesepian - AI Pathfinding & Minimax Duel")
        self.clock = pygame.time.Clock()
        self.running = True

        self.fonts = self._build_fonts()

        self.map = MapData()
        self.events = GameManager()

        # Sistem Pertarungan Turn-Based (Minimax AI)
        self.battle_system = BattleSystem()
        self.game_mode = "EXPLORATION"  # "EXPLORATION" atau "BATTLE"
        self.battle_reentry_locked = False

        self.overlay = DebugOverlay(self.events, self.fonts)
        self.overlay.set_battle_system(self.battle_system)
        self.overlay.set_mode(self.game_mode)

        self.player = Player(self.map, self.events)
        self.npc = NPC(self.map, self.events, self.player)

        self.events.subscribe_player_moved(self.npc.on_player_moved)
        self.events.subscribe_algorithm_changed(self.npc.set_algorithm)

        self.map_surface = None
        self.scaled_map = None
        self.map_w, self.map_h = self.map.map_px_size()

        # Timer jeda aksi NPC dalam battle agar animasi/pembacaan terasa wajar
        self.npc_battle_turn_timer = 0.0
        self._last_camera_target = (self.player.px, self.player.py)

        self._apply_viewport()
        self.npc.find_path(self.player.grid)

    # ------------------------------------------------------------------ #
    def _build_fonts(self):
        fonts = {}
        try:
            fonts["sm"] = pygame.font.SysFont(["consolas", "segoeui", "arial"], 14)
            fonts["bubble"] = pygame.font.SysFont(["consolas", "segoeui", "arial"], 14, bold=True)
            fonts["title"] = pygame.font.SysFont(["segoeui", "arial"], 17, bold=True)
            fonts["huge"] = pygame.font.SysFont(["segoeui", "arial"], 24, bold=True)
        except (OSError, RuntimeError):
            fonts["sm"] = pygame.font.Font(None, 20)
            fonts["bubble"] = pygame.font.Font(None, 22)
            fonts["title"] = pygame.font.Font(None, 26)
            fonts["huge"] = pygame.font.Font(None, 36)
        return fonts

    def _apply_viewport(self):
        w, h = self.screen.get_size()
        self.camera = Camera(w, h, self.map_w, self.map_h)
        if self.map_surface is None:
            combined = pygame.Surface((self.map_w, self.map_h))
            ground_surface = self.map.ground_surface
            obstacle_surface = self.map.obstacle_surface
            assert ground_surface is not None
            assert obstacle_surface is not None
            combined.blit(ground_surface, (0, 0))
            combined.blit(obstacle_surface, (0, 0))
            self.map_surface = combined
        self.camera.follow((self.player.px, self.player.py))
        self._last_camera_target = (self.player.px, self.player.py)
        self._refresh_scaled_map()

    def _refresh_scaled_map(self):
        assert self.map_surface is not None
        self.scaled_map = pygame.transform.smoothscale(
            self.map_surface, (int(self.map_w * self.camera.zoom), int(self.map_h * self.camera.zoom))
        )

    def _zoom_camera(self, factor, focus_screen=None):
        self.overlay.on_camera_zoom()
        if self.camera.zoom_by(factor, focus_screen):
            self._refresh_scaled_map()

    # ------------------------------------------------------------------ #
    def run(self):
        while self.running:
            dt = self.clock.tick(config.FPS) / 1000.0
            self._handle_events()
            self._update(dt)
            self._draw()
        getattr(pygame, "quit")()

    def _update(self, dt):
        self.overlay.update_animation(dt)
        if self.game_mode == "EXPLORATION":
            self.player.update(dt)
            self.npc.update(dt)

            if not self.player.moving:
                self._process_continuous_player_movement()

            camera_target = (self.player.px, self.player.py)
            if camera_target != self._last_camera_target:
                self.camera.follow(camera_target)
                self._last_camera_target = camera_target

            # Cek jarak kedekatan (Manhattan distance <= 1) untuk memicu duel
            dx = abs(self.player.grid[0] - self.npc.grid[0])
            dy = abs(self.player.grid[1] - self.npc.grid[1])
            distance = dx + dy
            if distance > 1:
                self.battle_reentry_locked = False
            if (
                distance <= 1
                and not self.battle_reentry_locked
                and not self.player.moving
                and not self.npc.moving
            ):
                self.enter_battle()
        else:
            # Mode Battle: Update floating action text timer
            self.battle_system.update_action_texts(dt)

            # Handle giliran NPC dengan jeda singkat (~0.5 detik)
            if self.battle_system.state.is_npc_turn and not self.battle_system.is_finished:
                self.npc_battle_turn_timer += dt
                if self.npc_battle_turn_timer >= 0.5:
                    self.npc_battle_turn_timer = 0.0
                    self.battle_system.execute_npc_turn()

    def _process_continuous_player_movement(self):
        keys = pygame.key.get_pressed()
        if keys[K_UP] or keys[K_w]:
            if self.player.try_move((0, -1)):
                return
        if keys[K_DOWN] or keys[K_s]:
            if self.player.try_move((0, 1)):
                return
        if keys[K_LEFT] or keys[K_a]:
            if self.player.try_move((-1, 0)):
                return
        if keys[K_RIGHT] or keys[K_d]:
            if self.player.try_move((1, 0)):
                return

    def enter_battle(self):
        self.game_mode = "BATTLE"
        self.overlay.set_mode("BATTLE")
        self.overlay.set_chasing_visualization(False)
        self.overlay.stop_path_animation()
        self.npc.chasing = False
        self.npc_battle_turn_timer = 0.0
        self.battle_system.reset()

    def exit_battle(self):
        self.game_mode = "EXPLORATION"
        self.overlay.set_mode("EXPLORATION")
        self.battle_reentry_locked = True
        # Reposisi sedikit jika bertumpukan
        self.npc.chasing = False

    # ------------------------------------------------------------------ #
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == VIDEORESIZE:
                self.screen = pygame.display.set_mode(event.size, RESIZABLE)
                self._apply_viewport()
            elif event.type == MOUSEWHEEL:
                self._zoom_camera(1.1 if event.y > 0 else 1 / 1.1, pygame.mouse.get_pos())
            elif event.type == MOUSEBUTTONDOWN:
                self.overlay.handle_event(event)
            elif event.type == KEYDOWN:
                self._handle_key(event.key)

    def _handle_key(self, key):
        if key == K_ESCAPE:
            self.running = False
            return

        if key in (K_LCTRL, K_RCTRL):
            if self.game_mode == "EXPLORATION":
                if self.npc.chasing:
                    self.overlay.set_chasing_visualization(True)
                elif self.overlay.visualization_active:
                    self.overlay.stop_path_animation()
                else:
                    self.npc.find_path(self.player.grid)
                    self.overlay.start_path_animation()
            return

        if key in (K_EQUALS, K_PLUS):
            self._zoom_camera(1.1)
            return
        if key == K_MINUS:
            self._zoom_camera(1 / 1.1)
            return

        if self.game_mode == "BATTLE":
            # Shortcut tombol di mode Battle
            if key == K_TAB:
                self.exit_battle()
            elif key == K_r:
                self.battle_system.reset()
            elif not self.battle_system.state.is_npc_turn and not self.battle_system.is_finished:
                if key in (K_1, K_a):
                    self.battle_system.execute_player_action(ACTION_ATTACK)
                elif key in (K_2, K_s):
                    self.battle_system.execute_player_action(ACTION_HEAVY)
                elif key in (K_3, K_d):
                    self.battle_system.execute_player_action(ACTION_DEFEND)
                elif key in (K_4, K_w):
                    self.battle_system.execute_player_action(ACTION_POTION)
        else:
            # Mode Eksplorasi Peta
            mapping = {
                K_UP: (0, -1),
                K_w: (0, -1),
                K_DOWN: (0, 1),
                K_s: (0, 1),
                K_LEFT: (-1, 0),
                K_a: (-1, 0),
                K_RIGHT: (1, 0),
                K_d: (1, 0),
            }
            if key in mapping:
                self.player.try_move(mapping[key])
            elif key == K_SPACE:
                if not self.npc.chasing:
                    self.player.show_call_bubble()
                self.npc.toggle_chase()
                self.overlay.set_chasing_visualization(self.npc.chasing)
            elif key == K_b:
                # Tombol pintas untuk langsung uji coba mode duel
                self.enter_battle()

    # ------------------------------------------------------------------ #
    def _draw(self):
        self.screen.fill(config.BG_COLOR)

        # 1. Gambar peta di sisi kanan
        assert self.scaled_map is not None
        self.screen.blit(self.scaled_map, (int(self.camera.offset_x), int(self.camera.offset_y)))

        if self.game_mode == "EXPLORATION":
            self.overlay.draw_world(self.screen, self.camera, self.map, self.npc, self.player)
            self._draw_sprite(self.player.sprite.current_image, self.player.px, self.player.py)
            self._draw_sprite(self.npc.sprite.current_image, self.npc.px, self.npc.py)
            if self.player.call_bubble_visible:
                self._draw_call_bubble()
            self._draw_npc_offscreen_indicator()
        else:
            # Di mode duel, tampilkan arena duel di atas peta
            self._draw_battle_arena()

        # 2. Tutupi area sidebar kiri dengan warna solid agar peta di belakangnya tidak terlihat
        pygame.draw.rect(
            self.screen,
            config.BG_COLOR,
            (0, 0, config.DEBUG_LEFT_PANEL_WIDTH, self.screen.get_height())
        )

        # 3. Gambar overlay UI di sidebar kiri
        self.overlay.draw_ui(self.screen)
        pygame.display.flip()

    def _draw_npc_offscreen_indicator(self):
        # Hitung posisi screen NPC
        npc_sx, npc_sy = self.camera.world_to_screen(self.npc.px, self.npc.py)

        # Batas area viewport kamera (sebelah kanan sidebar debug)
        panel_w = config.DEBUG_LEFT_PANEL_WIDTH
        margin = 32
        min_x = panel_w + margin
        max_x = self.screen.get_width() - margin
        min_y = margin
        max_y = self.screen.get_height() - margin

        # Cek apakah NPC berada di luar layar yang terlihat
        is_offscreen = (
            npc_sx < min_x or npc_sx > max_x or
            npc_sy < min_y or npc_sy > max_y
        )

        if not is_offscreen:
            return

        # Batasi posisi indikator di pinggir layar
        edge_x = max(min_x, min(max_x, npc_sx))
        edge_y = max(min_y, min(max_y, npc_sy))

        # Arah panah dari pusat layar ke NPC
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0
        angle = math.atan2(npc_sy - center_y, npc_sx - center_x)

        # Jarak dalam langkah ubin
        dist_grid = abs(self.player.grid[0] - self.npc.grid[0]) + abs(self.player.grid[1] - self.npc.grid[1])

        # Efek denyut (pulsing animation)
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.008)
        radius = int(18 + pulse * 3)

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

        # Label Teks Badge "🐱 Oyen (X ubin)"
        font = self.fonts.get("bubble", self.fonts["sm"])
        txt_surf = font.render(f"🐱 Bolu ({dist_grid} meter)", True, (255, 255, 255))

        txt_x = int(edge_x)
        txt_y = int(edge_y + radius + 16)
        if txt_y > max_y - 10:
            txt_y = int(edge_y - radius - 16)

        bg_rect = txt_surf.get_rect(center=(txt_x, txt_y))
        bg_rect.clamp_ip(pygame.Rect(min_x, min_y, max_x - min_x, max_y - min_y))

        card_bg = pygame.Surface((bg_rect.width + 12, bg_rect.height + 6), SRCALPHA)
        card_bg.fill((20, 24, 34, 220))
        pygame.draw.rect(card_bg, (255, 140, 0, 210), card_bg.get_rect(), 1, border_radius=5)
        self.screen.blit(card_bg, card_bg.get_rect(center=bg_rect.center))
        self.screen.blit(txt_surf, bg_rect)

    def _draw_battle_arena(self):
        # Tampilkan arena pertempuran di area kerja kanan
        w, h = self.screen.get_size()
        panel_w = config.DEBUG_LEFT_PANEL_WIDTH
        area_x = panel_w + (w - panel_w) // 2
        area_y = h // 2

        # Gelapkan latar peta agar arena pertempuran menonjol
        dark_surf = pygame.Surface((w - panel_w, h), SRCALPHA)
        dark_surf.fill((10, 12, 18, 180))
        self.screen.blit(dark_surf, (panel_w, 0))

        # Posisi Player (Kiri) dan NPC (Kanan) di arena
        player_arena_x = area_x - 160
        npc_arena_x = area_x + 160
        char_y = area_y - 50

        # Gambar Karakter Berukuran Besar (Menjaga Rasio Aspek Original)
        p_img = self.player.sprite.current_image
        p_aspect = p_img.get_width() / float(p_img.get_height())
        big_player = pygame.transform.smoothscale(p_img, (int(round(128 * p_aspect)), 128))

        n_img = self.npc.sprite.current_image
        n_aspect = n_img.get_width() / float(n_img.get_height())
        big_npc = pygame.transform.smoothscale(n_img, (int(round(128 * n_aspect)), 128))

        self.screen.blit(big_player, big_player.get_rect(center=(player_arena_x, char_y)))
        self.screen.blit(big_npc, big_npc.get_rect(center=(npc_arena_x, char_y)))

        # Floating Action Text di atas karakter
        self._draw_action_text(self.battle_system.player_action_text, player_arena_x, char_y - 70)
        self._draw_action_text(self.battle_system.npc_action_text, npc_arena_x, char_y - 70)

        # Status & Bar HP
        st = self.battle_system.state
        player_cd_text = f"  ⏳ Heavy CD: {st.player_heavy_cd}" if st.player_heavy_cd > 0 else ""
        npc_cd_text = f"  ⏳ Heavy CD: {st.npc_heavy_cd}" if st.npc_heavy_cd > 0 else ""
        self._draw_hp_bar(player_arena_x, char_y + 80, "Bolu (Player)", st.player_hp, st.player_defending, st.player_potions, (60, 160, 255), player_cd_text)
        self._draw_hp_bar(npc_arena_x, char_y + 80, "NPC (Minimax AI)", st.npc_hp, st.npc_defending, st.npc_potions, (255, 90, 80), npc_cd_text)

        # Tampilkan Battle Log Narasi di bagian bawah arena
        log_box = pygame.Rect(panel_w + 30, h - 160, (w - panel_w) - 60, 140)
        pygame.draw.rect(self.screen, (20, 24, 34, 230), log_box, border_radius=8)
        pygame.draw.rect(self.screen, config.DEBUG_PANEL_BORDER, log_box, 1, border_radius=8)

        ltitle = self.fonts.get("bubble", self.fonts["sm"]).render("RIWAYAT PERTEMPURAN (BATTLE LOG)", True, (255, 255, 255))
        self.screen.blit(ltitle, (log_box.x + 14, log_box.y + 10))

        ly = log_box.y + 36
        for log_line in self.battle_system.battle_logs[-4:]:
            ts = self.fonts["sm"].render(f"• {log_line}", True, (255, 255, 255))
            self.screen.blit(ts, (log_box.x + 14, ly))
            ly += 22

    def _draw_action_text(self, action_data, cx, cy):
        """Gambar teks aksi melayang di atas karakter (floating + fade effect)."""
        if not action_data:
            return

        text = action_data["text"]
        timer = action_data["timer"]
        color = action_data["color"]
        duration = self.battle_system.ACTION_TEXT_DURATION

        # Tahan teks agar terbaca, lalu lakukan fade-out hanya di bagian akhir.
        elapsed = duration - timer
        hold_duration = 1.5
        fade_progress = max(0.0, min(1.0, (elapsed - hold_duration) / (duration - hold_duration)))
        float_offset = min(elapsed, hold_duration) / hold_duration * 8 + fade_progress * 12
        alpha = max(0, min(255, int(255 * (1.0 - fade_progress))))

        # Buat surface teks
        font = self.fonts.get("bubble", self.fonts["sm"])
        text_surf = font.render(text, True, color)

        # Buat surface dengan alpha
        combined = pygame.Surface((text_surf.get_width() + 16, text_surf.get_height() + 8), SRCALPHA)

        # Latar belakang gelap semi-transparan
        bg_alpha = max(0, int(180 * (1.0 - fade_progress)))
        combined.fill((15, 18, 25, bg_alpha))

        # Border berwarna
        border_col = (*color[:3], alpha)
        pygame.draw.rect(combined, border_col, combined.get_rect(), 2, border_radius=6)

        # Teks di tengah
        text_alpha_surf = text_surf.copy()
        text_alpha_surf.set_alpha(alpha)
        combined.blit(text_alpha_surf, (8, 4))

        # Posisi final (naik dari posisi awal)
        final_y = cy - float_offset
        rect = combined.get_rect(center=(cx, int(final_y)))
        self.screen.blit(combined, rect)

    def _draw_hp_bar(self, cx, cy, name, hp, is_defending, potions, col_theme, cd_text=""):
        bar_w = 170
        bar_h = 16
        rect_bg = pygame.Rect(cx - bar_w // 2, cy, bar_w, bar_h)

        # Label Nama & Defend Status
        def_str = " [DEFENDING]" if is_defending else ""
        name_surf = self.fonts.get("bubble", self.fonts["sm"]).render(f"{name}{def_str}", True, (255, 230, 100) if is_defending else (255, 255, 255))
        self.screen.blit(name_surf, (cx - bar_w // 2, cy - 22))

        # Background bar
        pygame.draw.rect(self.screen, (35, 38, 48), rect_bg, border_radius=4)

        # Fill bar
        fill_w = int((hp / 100.0) * bar_w)
        if fill_w > 0:
            fill_rect = pygame.Rect(cx - bar_w // 2, cy, fill_w, bar_h)
            # Warna adaptif jika sekarat
            fill_col = col_theme if hp > 30 else (240, 60, 60)
            pygame.draw.rect(self.screen, fill_col, fill_rect, border_radius=4)

        pygame.draw.rect(self.screen, (100, 110, 130), rect_bg, 1, border_radius=4)

        # Teks Angka HP + Cooldown info
        hp_text = f"{hp} / 100 HP  │  Pot: {potions}{cd_text}"
        ts_hp = self.fonts["sm"].render(hp_text, True, (240, 240, 240))
        self.screen.blit(ts_hp, (cx - ts_hp.get_width() // 2, cy + bar_h + 4))

    def _draw_sprite(self, sprite, wx, wy):
        sx, sy = self.camera.world_to_screen(wx, wy)
        zoom_scale = max(1.0, self.camera.zoom / self.camera.fit_zoom)
        if zoom_scale != 1.0:
            nw = max(1, int(round(sprite.get_width() * zoom_scale)))
            nh = max(1, int(round(sprite.get_height() * zoom_scale)))
            sprite = pygame.transform.smoothscale(sprite, (nw, nh))
        rect = sprite.get_rect(center=(int(sx), int(sy)))
        self.screen.blit(sprite, rect)

    def _draw_call_bubble(self):
        sx, sy = self.camera.world_to_screen(self.player.px, self.player.py)
        text = "Bolu!!"
        surf = self.fonts["bubble"].render(text, True, (20, 20, 26))
        pad_x, pad_y = 10, 6
        w = surf.get_width() + pad_x * 2
        h = surf.get_height() + pad_y * 2
        rect = pygame.Rect(0, 0, w, h)
        rect.midbottom = (int(sx), int(sy - 22))
        pygame.draw.rect(self.screen, (255, 255, 255), rect, border_radius=4)
        pygame.draw.rect(self.screen, (30, 30, 40), rect, 1, border_radius=4)
        self.screen.blit(surf, (rect.x + pad_x, rect.y + pad_y))