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
from .npc_config_csp import NPCConfigCSP
from .npc_config_optimizer import NPCOptimizer
from .npc_squad import NPCSquad, NPCMember
from .battle_vfx import BattleVFXManager

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
MOUSEBUTTONUP = getattr(pygame, "MOUSEBUTTONUP", 1026)
MOUSEMOTION = getattr(pygame, "MOUSEMOTION", 1024)
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
K_5 = getattr(pygame, "K_5", 53)
K_w = getattr(pygame, "K_w", 119)
K_e = getattr(pygame, "K_e", 101)
K_RETURN = getattr(pygame, "K_RETURN", 13)
K_UP = getattr(pygame, "K_UP", 1073741906)
K_DOWN = getattr(pygame, "K_DOWN", 1073741905)
K_LEFT = getattr(pygame, "K_LEFT", 1073741904)
K_RIGHT = getattr(pygame, "K_RIGHT", 1073741903)
K_SPACE = getattr(pygame, "K_SPACE", 32)
K_b = getattr(pygame, "K_b", 98)
K_t = getattr(pygame, "K_t", 116)


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
        self.vfx = BattleVFXManager(self.fonts)
        self.battle_system.on_action_callback = self._on_battle_action_executed
        self.game_mode = "EXPLORATION"  # "EXPLORATION", "PRE_BATTLE", atau "BATTLE"
        self.battle_reentry_locked = False

        # Modul CSP & Local Search Optimizer (Tahap 3 & 4)
        self.csp = NPCConfigCSP()
        self.optimizer = NPCOptimizer(self.csp)
        self.selected_ls_algo = "HILL_CLIMBING"
        self.current_squad_config = None
        self.current_optimizer_stats = None
        self.current_squad = None

        self.overlay = DebugOverlay(self.events, self.fonts)
        self.overlay.set_battle_system(self.battle_system)
        self.overlay.set_mode(self.game_mode)
        self.overlay.on_ls_algo_changed = self._on_ls_algo_changed

        # Variabel Scroll & Tombol untuk Battle Log (2 aksi terakhir)
        self.battle_log_scroll_offset = 0
        self.battle_log_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_log_up = pygame.Rect(0, 0, 0, 0)
        self.btn_log_down = pygame.Rect(0, 0, 0, 0)

        # Tombol interaktif Pre-Battle & Battle
        self.btn_pre_battle_start = pygame.Rect(0, 0, 0, 0)
        self.btn_pre_battle_reroll = pygame.Rect(0, 0, 0, 0)
        self.btn_pre_battle_cancel = pygame.Rect(0, 0, 0, 0)
        self.btn_tree_modal = pygame.Rect(0, 0, 0, 0)
        self.reroll_toast_timer = 0.0

        self.player = Player(self.map, self.events)

        # 3 NPC di Peta (Opsi B: 1 Pengejar Utama + 2 Patroli Waypoint)
        # NPC 1: Oyen (Pengejar Utama pada [SPACE])
        self.npc = NPC(self.map, self.events, self.player, name="Oyen")
        # NPC 2: Kuro (Patroli Wilayah Barat/Utara - Warna Gelap)
        self.npc_kuro = NPC(
            self.map,
            self.events,
            self.player,
            name="Kuro",
            tint_color=(45, 45, 55),
            is_patrol=True,
            waypoints=[(10, 8), (16, 8), (16, 16), (10, 16)],
        )
        # NPC 3: Shiro (Patroli Wilayah Timur/Selatan - Warna Putih/Silver)
        self.npc_shiro = NPC(
            self.map,
            self.events,
            self.player,
            name="Shiro",
            tint_color=(195, 205, 220),
            is_patrol=True,
            waypoints=[(28, 14), (34, 14), (35, 24), (26, 21)],
        )

        self.events.subscribe_player_moved(self.npc.on_player_moved)
        self.events.subscribe_algorithm_changed(self.npc.set_algorithm)

        # Peti Harta Interaktif & Tas Inventory (Tahap 3 & 4)
        self.chests = [
            {"pos": (6, 20), "opened": False, "item": "health_potion"},
            {"pos": (22, 10), "opened": False, "item": "item_sword"},
            {"pos": (32, 27), "opened": False, "item": "item_shield"},
        ]
        self.item_images = self._load_item_images()
        self.battle_sprites = self._load_battle_sprites()

        # State Animasi Gacha / Loot Peti
        self.gacha_active = False
        self.gacha_timer = 0.0
        self.gacha_current_item = None
        self.gacha_reward_item = None
        self.gacha_message = ""
        self.gacha_message_timer = 0.0

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
            self.npc_kuro.update(dt)
            self.npc_shiro.update(dt)

            if not self.player.moving:
                self._process_continuous_player_movement()

            # Animasi Gacha / Loot Peti
            if self.gacha_active:
                self.gacha_timer -= dt
                item_keys = list(self.item_images.keys())
                if item_keys:
                    self.gacha_current_item = item_keys[int(pygame.time.get_ticks() / 80) % len(item_keys)]
                if self.gacha_timer <= 0.0:
                    self.gacha_active = False
                    self._award_gacha_reward()
            if self.gacha_message_timer > 0:
                self.gacha_message_timer -= dt

            camera_target = (self.player.px, self.player.py)
            if camera_target != self._last_camera_target:
                self.camera.follow(camera_target)
                self._last_camera_target = camera_target

            # Cek jarak kedekatan (Manhattan distance <= 1) dengan NPC mana pun di peta
            all_npcs = [self.npc, self.npc_kuro, self.npc_shiro]
            min_dist = 999
            closest_npc = None
            for n in all_npcs:
                d = abs(self.player.grid[0] - n.grid[0]) + abs(self.player.grid[1] - n.grid[1])
                if d < min_dist:
                    min_dist = d
                    closest_npc = n

            if min_dist > 1:
                self.battle_reentry_locked = False

            if (
                min_dist <= 1
                and not self.battle_reentry_locked
                and not self.player.moving
                and (closest_npc and not closest_npc.moving)
            ):
                self.enter_pre_battle(closest_npc)
        elif self.game_mode == "PRE_BATTLE":
            # State menunggu input player untuk mulai/re-roll
            if self.reroll_toast_timer > 0:
                self.reroll_toast_timer = max(0.0, self.reroll_toast_timer - dt)
        else:
            # Mode Battle: Update floating action text timer & VFX animasi
            self.battle_system.update_action_texts(dt)
            self.vfx.update(dt)

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

    def _on_ls_algo_changed(self, algo_code):
        self.selected_ls_algo = algo_code
        if self.game_mode == "PRE_BATTLE":
            self._run_optimization()

    def _run_optimization(self, randomize=False):
        """Menjalankan Local Search untuk menyeimbangkan squad NPC sesuai kondisi player."""
        player_ctx = {
            "player_hp": self.player.persistent_hp,
            "player_potions": self.player.persistent_potions,
            "player_atk_bonus": self.player.atk_bonus,
            "player_def_bonus": self.player.def_bonus,
        }
        cfg, stats = self.optimizer.optimize(
            self.selected_ls_algo, player_context=player_ctx, randomize_start=randomize
        )
        self.current_squad_config = cfg
        self.current_optimizer_stats = stats
        self.current_squad = NPCSquad.from_config(cfg)
        self.overlay.set_pre_battle_data(cfg, stats, self.selected_ls_algo)
        if randomize:
            self.reroll_toast_timer = 1.4

    def enter_pre_battle(self, leader_npc=None):
        self.game_mode = "PRE_BATTLE"
        self.overlay.set_mode("PRE_BATTLE")
        self.overlay.set_chasing_visualization(False)
        self.overlay.stop_path_animation()
        self.npc.chasing = False
        self._run_optimization()

    def enter_battle(self):
        self.game_mode = "BATTLE"
        self.overlay.set_mode("BATTLE")
        self.overlay.set_chasing_visualization(False)
        self.overlay.stop_path_animation()
        self.npc.chasing = False
        self.npc_battle_turn_timer = 0.0
        self.battle_log_scroll_offset = 0
        if hasattr(self, "vfx") and self.vfx:
            self.vfx.animations.clear()
        if self.current_squad:
            self.battle_system.reset_with_squad(self.current_squad, player=self.player)
        else:
            self.battle_system.reset()

    def exit_battle(self):
        self.game_mode = "EXPLORATION"
        self.overlay.set_mode("EXPLORATION")
        self.battle_reentry_locked = True
        self.npc.chasing = False
        if hasattr(self, "vfx") and self.vfx:
            self.vfx.animations.clear()
        # Sinkronkan sisa HP dan Potion player secara persistent
        if hasattr(self.battle_system, "state"):
            self.player.persistent_hp = max(10, self.battle_system.state.player_hp)
            self.player.persistent_potions = self.battle_system.state.player_potions

    def _get_battle_char_positions(self):
        """Menghitung koordinat posisi pusat Player dan NPC di arena battle."""
        w, h = self.screen.get_size()
        panel_w = config.DEBUG_LEFT_PANEL_WIDTH
        arena_w = w - panel_w
        has_bench = bool(self.current_squad and len(self.current_squad.members) > 1)
        bench_w = 245 if has_bench else 0
        combat_w = arena_w - bench_w - (14 if has_bench else 0)
        area_x = panel_w + combat_w // 2
        char_y = max(180, int(h * 0.38))
        player_arena_x = area_x - 140
        npc_arena_x = area_x + 140
        return (player_arena_x, char_y), (npc_arena_x, char_y)

    def _on_battle_action_executed(self, who: str, action: str):
        """Callback saat aksi pertempuran terjadi untuk memicu Battle VFX prosedural."""
        if not hasattr(self, "vfx") or not self.vfx:
            return
        p_pos, n_pos = self._get_battle_char_positions()
        if who == "PLAYER":
            if action == ACTION_ATTACK:
                self.vfx.trigger_attack(p_pos, n_pos, is_heavy=False, recipient="NPC")
            elif action == ACTION_HEAVY:
                self.vfx.trigger_attack(p_pos, n_pos, is_heavy=True, recipient="NPC")
            elif action == ACTION_DEFEND:
                self.vfx.trigger_defend(p_pos)
            elif action == ACTION_POTION:
                self.vfx.trigger_potion(p_pos, heal_val=config.POTION_HEAL)
        else:
            if action == ACTION_ATTACK:
                self.vfx.trigger_attack(n_pos, p_pos, is_heavy=False, recipient="PLAYER")
            elif action == ACTION_HEAVY:
                self.vfx.trigger_attack(n_pos, p_pos, is_heavy=True, recipient="PLAYER")
            elif action == ACTION_DEFEND:
                self.vfx.trigger_defend(n_pos)
            elif action == ACTION_POTION:
                self.vfx.trigger_potion(n_pos, heal_val=config.POTION_HEAL)

    # ------------------------------------------------------------------ #
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == VIDEORESIZE:
                self.screen = pygame.display.set_mode(event.size, RESIZABLE)
                self._apply_viewport()
            elif event.type == MOUSEWHEEL:
                m_pos = pygame.mouse.get_pos()
                if self.game_mode == "BATTLE":
                    # Scroll mousewheel pada Battle Log
                    if self.battle_log_rect.collidepoint(m_pos):
                        total_logs = len(self.battle_system.battle_logs)
                        max_scroll = max(0, total_logs - 2)
                        # event.y > 0 = scroll ke atas (lihat log lama)
                        # event.y < 0 = scroll ke bawah (lihat log terbaru)
                        self.battle_log_scroll_offset = max(0, min(max_scroll, self.battle_log_scroll_offset + event.y))
                    # Scroll mousewheel pada Decision Tree Overlay
                    elif self.overlay.tree_overlay.panel_rect.collidepoint(m_pos):
                        self.overlay.tree_overlay.handle_event(event)
                    else:
                        self.overlay.handle_event(event)
                else:
                    self._zoom_camera(1.1 if event.y > 0 else 1 / 1.1, m_pos)
            elif event.type == MOUSEBUTTONDOWN:
                pos = event.pos
                if self.game_mode == "PRE_BATTLE":
                    if self.btn_pre_battle_start.collidepoint(pos):
                        self.enter_battle()
                    elif self.btn_pre_battle_reroll.collidepoint(pos):
                        self._run_optimization(randomize=True)
                    elif self.btn_pre_battle_cancel.collidepoint(pos):
                        self.exit_battle()
                    else:
                        self.overlay.handle_event(event)
                elif self.game_mode == "BATTLE":
                    # Klik tombol [Lihat Decision Tree]
                    if self.btn_tree_modal.collidepoint(pos):
                        self.overlay.toggle_tree_overlay()
                    # Klik tombol panah scroll battle log
                    elif self.btn_log_up.collidepoint(pos):
                        total_logs = len(self.battle_system.battle_logs)
                        max_scroll = max(0, total_logs - 2)
                        self.battle_log_scroll_offset = min(max_scroll, self.battle_log_scroll_offset + 1)
                    elif self.btn_log_down.collidepoint(pos):
                        self.battle_log_scroll_offset = max(0, self.battle_log_scroll_offset - 1)
                    elif self.overlay.tree_overlay.visible and self.overlay.tree_overlay.handle_event(event):
                        pass
                    else:
                        self.overlay.handle_event(event)
                else:
                    self.overlay.handle_event(event)
            elif event.type in (MOUSEBUTTONUP, MOUSEMOTION):
                if self.game_mode == "BATTLE":
                    self.overlay.tree_overlay.handle_event(event)
            elif event.type == KEYDOWN:
                self._handle_key(event.key)

    def _handle_key(self, key):
        if key == K_ESCAPE:
            if self.game_mode == "BATTLE":
                if self.overlay.tree_overlay.visible:
                    self.overlay.tree_overlay.visible = False
                    return
                self.exit_battle()
                return
            elif self.game_mode == "PRE_BATTLE":
                self.exit_battle()
                return
            self.running = False
            return

        if key in (K_EQUALS, K_PLUS):
            self._zoom_camera(1.1)
            return
        if key == K_MINUS:
            self._zoom_camera(1 / 1.1)
            return

        if self.game_mode == "PRE_BATTLE":
            if key in (K_SPACE, K_RETURN):
                self.enter_battle()
            elif key == K_r:
                self._run_optimization(randomize=True)
            elif key == K_1:
                self.selected_ls_algo = "HILL_CLIMBING"
                self._run_optimization()
            elif key == K_2:
                self.selected_ls_algo = "SIDEWAYS"
                self._run_optimization()
            elif key == K_3:
                self.selected_ls_algo = "RANDOM_RESTART"
                self._run_optimization()
            elif key == K_4:
                self.selected_ls_algo = "SIMULATED_ANNEALING"
                self._run_optimization()
            elif key == K_5:
                self.selected_ls_algo = "GENETIC_ALGORITHM"
                self._run_optimization()
            elif key in (K_TAB, K_ESCAPE):
                self.exit_battle()
            return

        if self.game_mode == "BATTLE":
            # Shortcut tombol di mode Battle
            if key == K_TAB:
                self.exit_battle()
            elif key == K_r:
                self.battle_log_scroll_offset = 0
                if self.current_squad:
                    self.battle_system.reset_with_squad(self.current_squad, player=self.player)
                else:
                    self.battle_system.reset()
            elif key == K_t:
                self.overlay.toggle_tree_overlay()
            elif self.overlay.tree_overlay.visible:
                if key in (K_t, K_ESCAPE):
                    self.overlay.tree_overlay.visible = False
            elif not self.battle_system.state.is_npc_turn and not self.battle_system.is_finished:
                self.battle_log_scroll_offset = 0  # Auto-scroll ke log aksi terbaru saat giliran jalan
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
            if key in (K_LCTRL, K_RCTRL):
                if self.npc.chasing:
                    self.overlay.set_chasing_visualization(True)
                elif self.overlay.visualization_active:
                    self.overlay.stop_path_animation()
                else:
                    self.npc.find_path(self.player.grid)
                    self.overlay.start_path_animation()
                return

            if key == K_e:
                # Buka peti harta jika berjarak <= 1 langkah ubin
                for ch in self.chests:
                    if not ch["opened"]:
                        d = abs(self.player.grid[0] - ch["pos"][0]) + abs(self.player.grid[1] - ch["pos"][1])
                        if d <= 1:
                            self._open_chest(ch)
                            break
                return

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
                # Tombol pintas untuk masuk fase Pre-Battle
                self.enter_pre_battle()

    # ------------------------------------------------------------------ #
    def _draw(self):
        self.screen.fill(config.BG_COLOR)

        # 1. Gambar peta di sisi kanan
        assert self.scaled_map is not None
        self.screen.blit(self.scaled_map, (int(self.camera.offset_x), int(self.camera.offset_y)))

        if self.game_mode == "EXPLORATION":
            self.overlay.draw_world(self.screen, self.camera, self.map, self.npc, self.player)
            self._draw_chests()
            self._draw_sprite(self.player.sprite.current_image, self.player.px, self.player.py)
            self._draw_sprite(self.npc.sprite.current_image, self.npc.px, self.npc.py)
            self._draw_sprite(self.npc_kuro.sprite.current_image, self.npc_kuro.px, self.npc_kuro.py)
            self._draw_sprite(self.npc_shiro.sprite.current_image, self.npc_shiro.px, self.npc_shiro.py)
            if self.player.call_bubble_visible:
                self._draw_call_bubble()
            self._draw_npc_offscreen_indicator()
            if self.gacha_active or self.gacha_message_timer > 0:
                self._draw_gacha_popup()
        elif self.game_mode == "PRE_BATTLE":
            self._draw_pre_battle_arena()
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
        arena_w = w - panel_w
        area_x = panel_w + arena_w // 2

        # Gelapkan latar peta agar arena pertempuran menonjol
        dark_surf = pygame.Surface((arena_w, h), SRCALPHA)
        dark_surf.fill((10, 12, 18, 180))
        self.screen.blit(dark_surf, (panel_w, 0))

        # Posisi Player (Kiri) dan NPC (Kanan) di arena (sinkron dengan target VFX)
        (player_arena_x, char_y), (npc_arena_x, _) = self._get_battle_char_positions()

        # Gambar Karakter Berukuran Besar (Full-Body Battle Sprites)
        target_h = 145
        p_img = self.battle_sprites.get("player", self.player.sprite.current_image)
        p_aspect = p_img.get_width() / float(p_img.get_height())
        big_player = pygame.transform.smoothscale(p_img, (int(round(target_h * p_aspect)), target_h))

        # Sprite NPC aktif (menggunakan full-body battle sprite)
        active_member = self.current_squad.get_active_member() if self.current_squad else None
        if active_member and hasattr(active_member, "battle_sprite") and active_member.battle_sprite:
            n_img = active_member.battle_sprite
        elif active_member and active_member.char_type in self.battle_sprites:
            n_img = self.battle_sprites[active_member.char_type]
        elif active_member and active_member.portrait:
            n_img = active_member.portrait
        else:
            n_img = self.npc.sprite.current_image

        n_aspect = n_img.get_width() / float(n_img.get_height())
        big_npc = pygame.transform.smoothscale(n_img, (int(round(target_h * n_aspect)), target_h))

        p_ox, p_oy = self.vfx.get_shake_offset("PLAYER")
        n_ox, n_oy = self.vfx.get_shake_offset("NPC")
        self.screen.blit(big_player, big_player.get_rect(center=(player_arena_x + p_ox, char_y + p_oy)))
        self.screen.blit(big_npc, big_npc.get_rect(center=(npc_arena_x + n_ox, char_y + n_oy)))

        # ================================================================== #
        # Kartu Skuad NPC Lawan & Cadangan (Pinggir Kanan Layar)
        # Menampilkan profil lawan aktif dan kartu lawan cadangan berikutnya
        # ================================================================== #
        if self.current_squad and len(self.current_squad.members) > 1:
            bench_w = 245
            bench_x = w - bench_w - 14
            header_y = 18

            # Header Panel Skuad Lawan
            hdr_rect = pygame.Rect(bench_x, header_y, bench_w, 32)
            pygame.draw.rect(self.screen, (18, 22, 32, 235), hdr_rect, border_radius=8)
            pygame.draw.rect(self.screen, (70, 85, 115), hdr_rect, 1, border_radius=8)

            b_icon_txt = self.fonts.get("bubble", self.fonts["sm"]).render("👥 SKUAD LAWAN (TAG-TEAM)", True, (255, 215, 75))
            self.screen.blit(b_icon_txt, (hdr_rect.x + (bench_w - b_icon_txt.get_width()) // 2, hdr_rect.y + 6))

            card_y = header_y + 38
            card_h = 86
            card_gap = 8

            for i, mem in enumerate(self.current_squad.members):
                m_rect = pygame.Rect(bench_x, card_y, bench_w, card_h)
                is_active = (i == self.current_squad.active_index)
                is_defeated = (i < self.current_squad.active_index)
                is_reserve = (i > self.current_squad.active_index)

                ctype_lower = mem.char_type.lower()
                # Tema warna berdasarkan kelas dan status
                if is_defeated:
                    bg_col = (20, 18, 22, 210)
                    border_col = (110, 50, 50)
                    border_w = 1
                    status_badge = "[GUGUR ✕]"
                    badge_bg = (60, 20, 20)
                    badge_col = (220, 100, 100)
                elif is_active:
                    bg_col = (22, 32, 28, 240)
                    border_col = (75, 220, 130)
                    border_w = 2
                    status_badge = "[BERTARUNG ⚔️]"
                    badge_bg = (20, 75, 40)
                    badge_col = (90, 240, 140)
                else:
                    # Cadangan (Lawan berikutnya)
                    if i == self.current_squad.active_index + 1:
                        status_badge = f"[NEXT #{i+1} ⏳]"
                        badge_bg = (85, 65, 15)
                        badge_col = (255, 220, 80)
                    else:
                        status_badge = f"[CADANGAN #{i+1}]"
                        badge_bg = (25, 45, 75)
                        badge_col = (130, 185, 255)

                    if ctype_lower == "warrior":
                        bg_col = (30, 26, 24, 235)
                        border_col = (210, 130, 45)
                    elif ctype_lower == "ranger":
                        bg_col = (22, 30, 26, 235)
                        border_col = (45, 180, 95)
                    elif ctype_lower == "mage":
                        bg_col = (22, 26, 36, 235)
                        border_col = (65, 145, 240)
                    else:
                        bg_col = (24, 24, 30, 235)
                        border_col = (160, 90, 90)
                    border_w = 1

                # Gambar Kartu Member
                pygame.draw.rect(self.screen, bg_col, m_rect, border_radius=8)
                pygame.draw.rect(self.screen, border_col, m_rect, border_w, border_radius=8)

                # Pasang clipping mask untuk jaminan anti-overflow
                old_clip = self.screen.get_clip()
                self.screen.set_clip(m_rect)

                # Thumbnail Member
                thumb_size = 52
                thumb_x = bench_x + 8
                thumb_y = card_y + (card_h - thumb_size) // 2
                thumb_rect = pygame.Rect(thumb_x, thumb_y, thumb_size, thumb_size)
                pygame.draw.rect(self.screen, (12, 14, 20), thumb_rect, border_radius=6)

                raw_thumb = mem.portrait or mem.battle_sprite
                if raw_thumb:
                    t_w, t_h = raw_thumb.get_width(), raw_thumb.get_height()
                    scale = min((thumb_size - 4) / float(t_w), (thumb_size - 4) / float(t_h))
                    nw = max(1, int(round(t_w * scale)))
                    nh = max(1, int(round(t_h * scale)))
                    scaled_thumb = pygame.transform.smoothscale(raw_thumb, (nw, nh))
                    self.screen.blit(scaled_thumb, scaled_thumb.get_rect(center=thumb_rect.center))
                else:
                    icon_lbl = self.fonts.get("bubble", self.fonts["sm"]).render("🐱", True, (255, 255, 255))
                    self.screen.blit(icon_lbl, icon_lbl.get_rect(center=thumb_rect.center))

                pygame.draw.rect(self.screen, border_col, thumb_rect, 1, border_radius=6)

                # Jika gugur, beri tanda silang / overlay pada thumbnail
                if is_defeated:
                    cross_surf = pygame.Surface((thumb_size, thumb_size), SRCALPHA)
                    cross_surf.fill((40, 10, 10, 140))
                    pygame.draw.line(cross_surf, (220, 50, 50), (4, 4), (thumb_size - 4, thumb_size - 4), 3)
                    pygame.draw.line(cross_surf, (220, 50, 50), (4, thumb_size - 4), (thumb_size - 4, 4), 3)
                    self.screen.blit(cross_surf, thumb_rect)

                # Info Nama & Role
                info_x = thumb_x + thumb_size + 8
                info_w = bench_w - (thumb_size + 24)

                # Baris 1: Nama & Badge Status
                cname = mem.char_type.capitalize()
                txt_name = self.fonts.get("bubble", self.fonts["sm"]).render(f"{mem.name}", True, (255, 255, 255) if not is_defeated else (150, 150, 150))
                self.screen.blit(txt_name, (info_x, card_y + 6))

                badge_surf = self.fonts["sm"].render(status_badge, True, badge_col)
                badge_bg_rect = pygame.Rect(bench_x + bench_w - badge_surf.get_width() - 8, card_y + 6, badge_surf.get_width() + 6, 16)
                pygame.draw.rect(self.screen, badge_bg, badge_bg_rect, border_radius=4)
                self.screen.blit(badge_surf, (badge_bg_rect.x + 3, badge_bg_rect.y + 1))

                # Baris 2: Job Role
                job_desc = f"{cname} • {mem.eval_profile}"
                txt_job = self.fonts["sm"].render(job_desc, True, (170, 185, 205) if not is_defeated else (120, 120, 130))
                self.screen.blit(txt_job, (info_x, card_y + 24))

                # Baris 3: Mini Bar HP (Real-time sinkron untuk aktif)
                cur_hp = self.battle_system.state.npc_hp if is_active else max(0, mem.current_hp)
                hp_bar_w = info_w
                hp_bar_h = 7
                hp_bar_y = card_y + 44
                pygame.draw.rect(self.screen, (32, 36, 46), (info_x, hp_bar_y, hp_bar_w, hp_bar_h), border_radius=2)
                fill_w = int(hp_bar_w * (cur_hp / float(max(1, mem.max_hp))))
                if fill_w > 0 and not is_defeated:
                    bar_c = (50, 195, 100) if is_active else (70, 150, 240)
                    pygame.draw.rect(self.screen, bar_c, (info_x, hp_bar_y, fill_w, hp_bar_h), border_radius=2)
                pygame.draw.rect(self.screen, (75, 85, 105), (info_x, hp_bar_y, hp_bar_w, hp_bar_h), 1, border_radius=2)

                # Baris 4: Teks Stat (HP & Atk/Def)
                txt_hp = self.fonts["sm"].render(f"{cur_hp}/{mem.max_hp} HP  │ +{mem.atk_bonus}A +{mem.def_bonus}D", True, (215, 225, 240) if not is_defeated else (130, 130, 140))
                self.screen.blit(txt_hp, (info_x, card_y + 55))

                self.screen.set_clip(old_clip)
                card_y += card_h + card_gap

        # Floating Action Text di atas karakter
        self._draw_action_text(self.battle_system.player_action_text, player_arena_x, char_y - 75)
        self._draw_action_text(self.battle_system.npc_action_text, npc_arena_x, char_y - 75)

        # Status & Bar HP
        st = self.battle_system.state
        player_cd_text = f"  ⏳ Heavy CD: {st.player_heavy_cd}" if st.player_heavy_cd > 0 else ""
        npc_cd_text = f"  ⏳ Heavy CD: {st.npc_heavy_cd}" if st.npc_heavy_cd > 0 else ""
        npc_display_name = active_member.name if active_member else "NPC (Minimax AI)"
        npc_max_hp = active_member.max_hp if active_member else 100
        self._draw_hp_bar(player_arena_x, char_y + 98, "Bolu (Player)", st.player_hp, st.player_defending, st.player_potions, (60, 160, 255), player_cd_text, max_hp=100)
        self._draw_hp_bar(npc_arena_x, char_y + 98, npc_display_name, st.npc_hp, st.npc_defending, st.npc_potions, (255, 90, 80), npc_cd_text, max_hp=npc_max_hp)

        # ------------------------------------------------------------------ #
        # 1. Battle Log Box (Bagian Paling Bawah Layar, Scrollable)
        # ------------------------------------------------------------------ #
        usable_w = arena_w - 30
        log_x = panel_w + 15
        log_h = 76
        log_y = h - log_h - 14
        self.battle_log_rect = pygame.Rect(log_x, log_y, usable_w, log_h)

        pygame.draw.rect(self.screen, (20, 24, 34, 235), self.battle_log_rect, border_radius=8)
        pygame.draw.rect(self.screen, config.DEBUG_PANEL_BORDER, self.battle_log_rect, 1, border_radius=8)

        font_bubble = self.fonts.get("bubble", self.fonts["sm"])
        font_sm = self.fonts["sm"]

        ltitle = font_bubble.render("📜 RIWAYAT PERTEMPURAN (BATTLE LOG)", True, (255, 255, 255))
        self.screen.blit(ltitle, (self.battle_log_rect.x + 12, self.battle_log_rect.y + 6))

        total_logs = len(self.battle_system.battle_logs)
        max_scroll = max(0, total_logs - 2)
        self.battle_log_scroll_offset = max(0, min(max_scroll, self.battle_log_scroll_offset))

        if total_logs > 2:
            end_idx = total_logs - self.battle_log_scroll_offset
            start_idx = max(0, end_idx - 2)
            display_logs = self.battle_system.battle_logs[start_idx:end_idx]
            pos_info = f"[Aksi {start_idx + 1}-{end_idx} dari {total_logs}] (Scroll: MouseWheel)"
        else:
            display_logs = self.battle_system.battle_logs
            pos_info = f"[{total_logs} aksi]" if total_logs > 0 else "[Belum ada aksi]"

        info_surf = font_sm.render(pos_info, True, (170, 185, 210))
        self.screen.blit(info_surf, (self.battle_log_rect.right - info_surf.get_width() - 65, self.battle_log_rect.y + 6))

        # Tombol panah scroll manual (▲ dan ▼)
        btn_w, btn_h = 22, 18
        self.btn_log_up = pygame.Rect(self.battle_log_rect.right - 54, self.battle_log_rect.y + 5, btn_w, btn_h)
        self.btn_log_down = pygame.Rect(self.battle_log_rect.right - 28, self.battle_log_rect.y + 5, btn_w, btn_h)

        up_col = (60, 100, 160) if self.battle_log_scroll_offset < max_scroll else (45, 50, 65)
        down_col = (60, 100, 160) if self.battle_log_scroll_offset > 0 else (45, 50, 65)

        pygame.draw.rect(self.screen, up_col, self.btn_log_up, border_radius=3)
        pygame.draw.rect(self.screen, down_col, self.btn_log_down, border_radius=3)

        ts_up = font_bubble.render("▲", True, (255, 255, 255) if self.battle_log_scroll_offset < max_scroll else (120, 125, 135))
        ts_dn = font_bubble.render("▼", True, (255, 255, 255) if self.battle_log_scroll_offset > 0 else (120, 125, 135))
        self.screen.blit(ts_up, (self.btn_log_up.centerx - ts_up.get_width() // 2, self.btn_log_up.centery - ts_up.get_height() // 2))
        self.screen.blit(ts_dn, (self.btn_log_down.centerx - ts_dn.get_width() // 2, self.btn_log_down.centery - ts_dn.get_height() // 2))

        ly = self.battle_log_rect.y + 28
        if display_logs:
            for log_line in display_logs:
                ts = font_sm.render(f"• {log_line}", True, (245, 245, 250))
                self.screen.blit(ts, (self.battle_log_rect.x + 14, ly))
                ly += 22
        else:
            ts = font_sm.render("• Pertarungan dimulai! Pilih aksi Player untuk bertarung melawan AI.", True, (150, 160, 180))
            self.screen.blit(ts, (self.battle_log_rect.x + 14, ly))

        if total_logs > 2 and max_scroll > 0:
            track_y = self.battle_log_rect.y + 26
            track_h = log_h - 32
            thumb_h = max(10, int(track_h * (2.0 / total_logs)))
            norm_pos = 1.0 - (self.battle_log_scroll_offset / float(max_scroll))
            thumb_y = track_y + int(norm_pos * (track_h - thumb_h))
            pygame.draw.rect(self.screen, (50, 58, 75), pygame.Rect(self.battle_log_rect.right - 6, track_y, 3, track_h), border_radius=1)
            pygame.draw.rect(self.screen, (100, 180, 255), pygame.Rect(self.battle_log_rect.right - 6, thumb_y, 3, thumb_h), border_radius=1)

        # ------------------------------------------------------------------ #
        # 2. Tombol Elegan: [🌲 LIHAT DECISION TREE (T)] di Atas Battle Log
        # ------------------------------------------------------------------ #
        btn_tree_h = 32
        self.btn_tree_modal = pygame.Rect(panel_w + 15, log_y - btn_tree_h - 8, 245, btn_tree_h)
        pygame.draw.rect(self.screen, (35, 125, 70), self.btn_tree_modal, border_radius=6)
        pygame.draw.rect(self.screen, (90, 210, 135), self.btn_tree_modal, 1, border_radius=6)
        tree_btn_txt = font_bubble.render("🌲 LIHAT DECISION TREE [T]", True, (255, 255, 255))
        self.screen.blit(tree_btn_txt, (self.btn_tree_modal.centerx - tree_btn_txt.get_width() // 2, self.btn_tree_modal.centery - tree_btn_txt.get_height() // 2))

        # ------------------------------------------------------------------ #
        # Visual Effect Manager (Pedang Bergerak, Perisai, Ramuan, Partikel)
        # ------------------------------------------------------------------ #
        self.vfx.draw(self.screen)

        # ------------------------------------------------------------------ #
        # 3. Decision Tree Fullscreen Modal Overlay (Semi-Transparan Pop-up)
        # ------------------------------------------------------------------ #
        if self.overlay.tree_overlay.visible:
            if self.battle_system.last_ai_stats:
                tree_data = self.battle_system.last_ai_stats.get("tree", None)
                if tree_data is None and hasattr(self.battle_system.ai_solver, "last_tree"):
                    tree_data = self.battle_system.ai_solver.last_tree
                self.overlay.tree_overlay.set_tree(tree_data)
            self.overlay.tree_overlay.draw(self.screen)

    def _draw_pre_battle_arena(self):
        w, h = self.screen.get_size()
        panel_w = config.DEBUG_LEFT_PANEL_WIDTH
        arena_w = w - panel_w
        area_cx = panel_w + arena_w // 2

        # Latar belakang gelap transparan
        dark_surf = pygame.Surface((arena_w, h), SRCALPHA)
        dark_surf.fill((10, 14, 22, 235))
        self.screen.blit(dark_surf, (panel_w, 0))

        font_huge = self.fonts.get("huge", self.fonts["title"])
        font_title = self.fonts.get("title", self.fonts["sm"])
        font_bubble = self.fonts.get("bubble", self.fonts["sm"])
        font_sm = self.fonts["sm"]

        # Header Title
        t_surf = font_huge.render("⚔️ PERSIAPAN PERTEMPURAN (PRE-BATTLE)", True, (255, 215, 70))
        self.screen.blit(t_surf, (area_cx - t_surf.get_width() // 2, 24))

        sub_txt = "AI menyeimbangkan komposisi skuad lawan via CSP (MRV+LCV+AC-3) & Local Search"
        sub_surf = font_sm.render(sub_txt, True, (170, 190, 215))
        self.screen.blit(sub_surf, (area_cx - sub_surf.get_width() // 2, 58))

        # Sisi Kiri: Profil Player (Bolu) - Diperbesar mengisi space vertikal
        btn_h = 44
        btn_y = h - 68
        available_h = max(380, btn_y - 20 - 92)

        p_card_w = min(290, arena_w // 2 - 35)
        p_card_h = available_h
        p_card_x = panel_w + 25
        p_card_y = 90
        p_card_rect = pygame.Rect(p_card_x, p_card_y, p_card_w, p_card_h)

        pygame.draw.rect(self.screen, (20, 26, 38), p_card_rect, border_radius=12)
        pygame.draw.rect(self.screen, (55, 140, 235), p_card_rect, 2, border_radius=12)

        p_header = font_title.render("🛡️ Bolu (Player Hero)", True, (110, 190, 255))
        self.screen.blit(p_header, (p_card_x + 16, p_card_y + 14))

        # Tampilan Sprite Bolu Besar & Heroik
        p_img = self.battle_sprites.get("player", self.player.sprite.current_image)
        p_aspect = p_img.get_width() / float(p_img.get_height())
        target_bolu_h = min(150, int(available_h * 0.30))
        p_big = pygame.transform.smoothscale(p_img, (int(round(target_bolu_h * p_aspect)), target_bolu_h))
        self.screen.blit(p_big, p_big.get_rect(center=(p_card_x + p_card_w // 2, p_card_y + 36 + target_bolu_h // 2)))

        # Mini Bar HP Player
        hp_bar_y = p_card_y + 42 + target_bolu_h
        hp_bar_w = p_card_w - 36
        hp_bar_h = 16
        pygame.draw.rect(self.screen, (35, 40, 52), (p_card_x + 18, hp_bar_y, hp_bar_w, hp_bar_h), border_radius=4)
        hp_fill = int((self.player.persistent_hp / 100.0) * hp_bar_w)
        if hp_fill > 0:
            pygame.draw.rect(self.screen, (45, 155, 235), (p_card_x + 18, hp_bar_y, hp_fill, hp_bar_h), border_radius=4)
        pygame.draw.rect(self.screen, (90, 130, 180), (p_card_x + 18, hp_bar_y, hp_bar_w, hp_bar_h), 1, border_radius=4)
        hp_lbl = font_sm.render(f"HP: {self.player.persistent_hp} / 100", True, (255, 255, 255))
        self.screen.blit(hp_lbl, (p_card_x + 18 + (hp_bar_w - hp_lbl.get_width()) // 2, hp_bar_y + 1))

        py_stat = hp_bar_y + 26
        p_stats = [
            f"• Ramuan Cadangan : {self.player.persistent_potions} Botol (+25 HP)",
            f"• Bonus Serangan  : +{self.player.atk_bonus} ATK",
            f"• Bonus Ketahanan : +{self.player.def_bonus} DEF Flat",
            "• Gaya Bertarung  : Pendekar Berani",
        ]
        for s in p_stats:
            self.screen.blit(font_sm.render(s, True, (220, 235, 250)), (p_card_x + 18, py_stat))
            py_stat += 22

        # Rincian Inventori Barang
        py_stat += 6
        self.screen.blit(font_bubble.render("🎒 Artefak & Perlengkapan:", True, (255, 215, 90)), (p_card_x + 18, py_stat))
        ix = p_card_x + 18
        iy = py_stat + 24
        for it in (self.player.inventory or ["item_sword"]):
            if it in self.item_images:
                icon = pygame.transform.smoothscale(self.item_images[it], (32, 32))
                self.screen.blit(icon, (ix, iy))
                ix += 38

        # Sisi Kanan: Profil Squad NPC Lawan (1 - 3 Member) - Diperbesar mengisi space vertikal
        squad_area_x = p_card_rect.right + 22
        squad_area_w = (panel_w + arena_w - 25) - squad_area_x

        sq_header = font_title.render("🐱 Skuad Lawan (CSP & Local Search)", True, (255, 120, 90))
        self.screen.blit(sq_header, (squad_area_x, p_card_y - 2))

        members = self.current_squad.members if self.current_squad else []
        num_m = max(1, len(members))
        gap = 10
        member_card_h = max(100, (available_h - 26 - (num_m - 1) * gap) // num_m)
        m_y = p_card_y + 26

        for idx, m in enumerate(members):
            m_rect = pygame.Rect(squad_area_x, m_y, squad_area_w, member_card_h)
            ctype_lower = m.char_type.lower()
            if ctype_lower == "warrior":
                border_col = (220, 130, 40)
                card_bg_col = (28, 26, 32)
                trait_desc = "⚔ Ketahanan tinggi & serangan seimbang"
            elif ctype_lower == "ranger":
                border_col = (45, 185, 90)
                card_bg_col = (22, 28, 25)
                trait_desc = "🏹 Pemanah lincah dengan damage penetrasi tinggi"
            elif ctype_lower == "mage":
                border_col = (70, 140, 245)
                card_bg_col = (22, 26, 36)
                trait_desc = "🔮 Penyihir sakti berdaya hancur tinggi (Glass Cannon)"
            else:
                border_col = (200, 75, 75)
                card_bg_col = (26, 26, 30)
                trait_desc = "🛡 Petarung tangguh tim AI"

            pygame.draw.rect(self.screen, card_bg_col, m_rect, border_radius=10)
            pygame.draw.rect(self.screen, border_col, m_rect, 1, border_radius=10)

            # Thumbnail Besar Full-Body Sprite
            npc_thumb = m.battle_sprite or m.portrait
            if npc_thumb:
                asp = npc_thumb.get_width() / float(npc_thumb.get_height())
                thumb_target_h = min(115, member_card_h - 18)
                p_icon = pygame.transform.smoothscale(npc_thumb, (int(round(thumb_target_h * asp)), thumb_target_h))
                self.screen.blit(p_icon, p_icon.get_rect(center=(m_rect.x + 52, m_rect.centery)))
            else:
                pygame.draw.rect(self.screen, (45, 50, 65), (m_rect.x + 12, m_rect.y + 12, 64, 64), border_radius=6)

            tx = m_rect.x + 104
            ty = m_rect.y + max(8, (member_card_h - 85) // 2)

            # Baris 1: Nama & Badge Job
            t_name = font_title.render(f"{idx+1}. {m.name}", True, (255, 235, 160))
            self.screen.blit(t_name, (tx, ty))

            # Baris 2: Mini HP Bar & Potions
            m_hp_w = min(160, squad_area_w - 280)
            m_hp_y = ty + 24
            pygame.draw.rect(self.screen, (35, 40, 52), (tx, m_hp_y, m_hp_w, 13), border_radius=3)
            m_fill = int((m.max_hp / 120.0) * m_hp_w)
            pygame.draw.rect(self.screen, border_col, (tx, m_hp_y, m_fill, 13), border_radius=3)
            txt_hp = font_sm.render(f"{m.max_hp} HP  │  {m.potions} Potion", True, (240, 245, 255))
            self.screen.blit(txt_hp, (tx + m_hp_w + 12, m_hp_y - 1))

            # Baris 3: ATK, DEF, dan Profil AI
            line3 = f"ATK: +{m.atk_bonus}  │  DEF: +{m.def_bonus}  │  Taktik: {m.eval_profile}"
            self.screen.blit(font_sm.render(line3, True, (215, 225, 240)), (tx, m_hp_y + 18))

            # Baris 4: Deskripsi Karakteristik
            self.screen.blit(font_sm.render(trait_desc, True, (150, 185, 220)), (tx, m_hp_y + 36))

            m_y += member_card_h + gap

        # Bagian Bawah: Tombol CTA Interaktif di Dasar Layar
        btn_w = 210
        self.btn_pre_battle_start = pygame.Rect(area_cx - btn_w - 115, btn_y, btn_w, btn_h)
        self.btn_pre_battle_reroll = pygame.Rect(area_cx - btn_w // 2, btn_y, btn_w, btn_h)
        self.btn_pre_battle_cancel = pygame.Rect(area_cx + btn_w // 2 + 15, btn_y, btn_w - 30, btn_h)

        pygame.draw.rect(self.screen, (40, 165, 80), self.btn_pre_battle_start, border_radius=8)
        pygame.draw.rect(self.screen, (215, 115, 30), self.btn_pre_battle_reroll, border_radius=8)
        pygame.draw.rect(self.screen, (60, 70, 85), self.btn_pre_battle_cancel, border_radius=8)

        t_start = font_bubble.render("▶ MASUK DUEL [SPASI]", True, (255, 255, 255))
        t_reroll = font_bubble.render("🎲 RE-ROLL AI [R]", True, (255, 255, 255))
        t_cancel = font_bubble.render("✕ KEMBALI [ESC]", True, (210, 215, 225))

        self.screen.blit(t_start, (self.btn_pre_battle_start.centerx - t_start.get_width() // 2, self.btn_pre_battle_start.centery - t_start.get_height() // 2))
        self.screen.blit(t_reroll, (self.btn_pre_battle_reroll.centerx - t_reroll.get_width() // 2, self.btn_pre_battle_reroll.centery - t_reroll.get_height() // 2))
        self.screen.blit(t_cancel, (self.btn_pre_battle_cancel.centerx - t_cancel.get_width() // 2, self.btn_pre_battle_cancel.centery - t_cancel.get_height() // 2))

        # Notifikasi visual saat Re-Roll berhasil dijalankan
        if self.reroll_toast_timer > 0:
            toast_text = "🎲 Skuad NPC Berhasil Diacak Ulang & Dioptimasi!"
            toast_surf = font_bubble.render(toast_text, True, (255, 240, 140))
            tw = toast_surf.get_width() + 28
            th = 28
            toast_rect = pygame.Rect(area_cx - tw // 2, btn_y - 34, tw, th)
            pygame.draw.rect(self.screen, (185, 90, 15), toast_rect, border_radius=6)
            pygame.draw.rect(self.screen, (255, 215, 80), toast_rect, 1, border_radius=6)
            self.screen.blit(toast_surf, (toast_rect.centerx - toast_surf.get_width() // 2, toast_rect.centery - toast_surf.get_height() // 2))

    def _draw_chests(self):
        for chest in self.chests:
            cx, cy = self.map.world_to_px(chest["pos"])
            sx, sy = self.camera.world_to_screen(cx, cy)
            sz = int(self.map.cell_size * self.camera.zoom)
            rect = pygame.Rect(int(sx - sz // 2), int(sy - sz // 2), sz, sz)

            if not chest["opened"]:
                pygame.draw.rect(self.screen, (160, 95, 25), rect, border_radius=4)
                pygame.draw.rect(self.screen, (245, 200, 60), rect, width=max(1, int(2 * self.camera.zoom)), border_radius=4)
                k_rect = pygame.Rect(rect.centerx - 3, rect.centery - 2, 6, 6)
                pygame.draw.rect(self.screen, (255, 240, 120), k_rect, border_radius=1)

                dist = abs(self.player.grid[0] - chest["pos"][0]) + abs(self.player.grid[1] - chest["pos"][1])
                if dist <= 1:
                    prompt = self.fonts.get("bubble", self.fonts["sm"]).render("[E] Buka Peti", True, (255, 255, 255))
                    p_box = prompt.get_rect(center=(rect.centerx, rect.top - 16))
                    card = pygame.Surface((p_box.width + 12, p_box.height + 6), SRCALPHA)
                    card.fill((20, 24, 34, 230))
                    pygame.draw.rect(card, (255, 205, 50), card.get_rect(), 1, border_radius=4)
                    self.screen.blit(card, card.get_rect(center=p_box.center))
                    self.screen.blit(prompt, p_box)
            else:
                pygame.draw.rect(self.screen, (85, 75, 65), rect, border_radius=4)
                pygame.draw.rect(self.screen, (120, 110, 100), rect, width=1, border_radius=4)

    def _draw_gacha_popup(self):
        w, h = self.screen.get_size()
        panel_w = config.DEBUG_LEFT_PANEL_WIDTH
        arena_w = w - panel_w
        cx = panel_w + arena_w // 2
        cy = h // 2

        if self.gacha_active:
            pop_w, pop_h = 320, 160
            pop_rect = pygame.Rect(cx - pop_w // 2, cy - pop_h // 2, pop_w, pop_h)
            card = pygame.Surface((pop_w, pop_h), SRCALPHA)
            card.fill((18, 22, 32, 240))
            pygame.draw.rect(card, (255, 200, 60), card.get_rect(), 2, border_radius=10)
            self.screen.blit(card, pop_rect)

            title = self.fonts.get("title", self.fonts["sm"]).render("✨ MEMBUKA PETI HARTA ✨", True, (255, 225, 80))
            self.screen.blit(title, (cx - title.get_width() // 2, pop_rect.y + 14))

            cur_item = self.gacha_current_item
            if cur_item and cur_item in self.item_images:
                img = self.item_images[cur_item]
                self.screen.blit(img, img.get_rect(center=(cx, cy + 8)))

            sub = self.fonts["sm"].render("Memutar keberuntungan...", True, (200, 215, 235))
            self.screen.blit(sub, (cx - sub.get_width() // 2, pop_rect.bottom - 26))

        elif self.gacha_message_timer > 0:
            alpha = min(255, int(255 * (self.gacha_message_timer / 0.5))) if self.gacha_message_timer < 0.5 else 255
            txt = self.fonts.get("bubble", self.fonts["sm"]).render(self.gacha_message, True, (255, 255, 255))
            toast_rect = pygame.Rect(cx - txt.get_width() // 2 - 16, 30, txt.get_width() + 32, txt.get_height() + 14)
            card = pygame.Surface((toast_rect.width, toast_rect.height), SRCALPHA)
            card.fill((20, 28, 45, int(230 * (alpha / 255.0))))
            pygame.draw.rect(card, (70, 200, 120, alpha), card.get_rect(), 2, border_radius=8)
            self.screen.blit(card, toast_rect)
            self.screen.blit(txt, (toast_rect.centerx - txt.get_width() // 2, toast_rect.centery - txt.get_height() // 2))

    def _load_item_images(self):
        items = {}
        item_files = {
            "health_potion": "health_potion.png",
            "mega_potion": "mega_potion.png",
            "item_sword": "item_sword.png",
            "item_shield": "item_shield.png",
            "item_boots": "item_boots.png",
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

    def _load_battle_sprites(self):
        b_sprites = {}
        files = {
            "player": "battle_bolu.png",
            "warrior": "battle_warrior.png",
            "tank": "battle_tank.png",
            "ranger": "battle_ranger.png",
            "assassin": "battle_assassin.png",
            "mage": "battle_mage.png",
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
        if chest.get("opened", False) or self.gacha_active:
            return
        chest["opened"] = True
        self.gacha_active = True
        self.gacha_timer = 1.2
        self.gacha_reward_item = chest.get("item", "health_potion")

    def _award_gacha_reward(self):
        item = self.gacha_reward_item or "health_potion"
        if item == "health_potion":
            self.player.persistent_potions += 1
            msg = "Mendapatkan Health Potion (+1 Ramuan)!"
        elif item == "mega_potion":
            self.player.persistent_hp = min(100, self.player.persistent_hp + 50)
            self.player.persistent_potions += 1
            msg = "Mendapatkan Mega Potion (+50 HP & +1 Ramuan)!"
        elif item == "item_sword":
            self.player.atk_bonus += 5
            self.player.inventory.append("item_sword")
            msg = "Mendapatkan Pedang Ksatria (+5 ATK Bonus)!"
        elif item == "item_shield":
            self.player.def_bonus += 4
            self.player.inventory.append("item_shield")
            msg = "Mendapatkan Perisai Baja (+4 DEF Flat Reduction)!"
        elif item == "item_boots":
            self.player.inventory.append("item_boots")
            msg = "Mendapatkan Boots Lincah (+Kelincahan Bertualang)!"
        else:
            msg = f"Mendapatkan item {item}!"
        self.gacha_message = msg
        self.gacha_message_timer = 3.0

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

    def _draw_hp_bar(self, cx, cy, name, hp, is_defending, potions, col_theme, cd_text="", max_hp=100):
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
        fill_w = int((hp / float(max(1, max_hp))) * bar_w)
        if fill_w > 0:
            fill_rect = pygame.Rect(cx - bar_w // 2, cy, fill_w, bar_h)
            # Warna adaptif jika sekarat
            fill_col = col_theme if hp > int(0.3 * max_hp) else (240, 60, 60)
            pygame.draw.rect(self.screen, fill_col, fill_rect, border_radius=4)

        pygame.draw.rect(self.screen, (100, 110, 130), rect_bg, 1, border_radius=4)

        # Teks Angka HP + Cooldown info
        hp_text = f"{hp} / {max_hp} HP  │  Pot: {potions}{cd_text}"
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