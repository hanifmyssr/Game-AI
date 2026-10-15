"""App: main loop + kamera + rendering, port dari Scenes/main.tscn + Duel Turn-Based Minimax (Tahap-2).
"""

import math
import os
from typing import Optional, Dict, Any, List, Tuple
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
from .pre_battle_visualizer import PreBattleVisualizerModal

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
K_KP_ENTER = getattr(pygame, "K_KP_ENTER", 1073741912)
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
        self.battle_system.on_tag_in = self._on_npc_tag_in
        self.card_summon_anim = None
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
        self.btn_pre_battle_inspect = pygame.Rect(0, 0, 0, 0)
        self.btn_pre_battle_start = pygame.Rect(0, 0, 0, 0)
        self.btn_pre_battle_reroll = pygame.Rect(0, 0, 0, 0)
        self.btn_pre_battle_cancel = pygame.Rect(0, 0, 0, 0)
        self.btn_tree_modal = pygame.Rect(0, 0, 0, 0)
        self.reroll_toast_timer = 0.0
        self.pre_battle_visualizer = PreBattleVisualizerModal()
        self.overlay.on_open_ai_inspector = self.pre_battle_visualizer.toggle

        self.player = Player(self.map, self.events)

        # 3 NPC di Peta (Opsi B: 1 Pengejar Utama + 2 Patroli Waypoint)
        # NPC 1: Bolu (Pengejar Utama pada [SPACE])
        self.npc = NPC(self.map, self.events, self.player, name="Bolu")
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
        self.item_images_large = self._load_item_images_large()
        self.battle_sprites = self._load_battle_sprites()

        # State Animasi Gacha / Loot Peti
        self.gacha_active = False
        self.gacha_timer = 0.0
        self.gacha_current_item = None
        self.gacha_reward_item = None
        self.gacha_message = ""
        self.gacha_message_timer = 0.0
        self.gacha_showcase = None
        self.loot_toast = None
        self.loot_modal = None
        self.npc_defeat_anim = None
        self.final_loot_shown = False

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
            fonts["tiny"] = pygame.font.SysFont(["consolas", "segoeui", "arial"], 11, bold=True)
            fonts["sm"] = pygame.font.SysFont(["consolas", "segoeui", "arial"], 14)
            fonts["bubble"] = pygame.font.SysFont(["consolas", "segoeui", "arial"], 14, bold=True)
            fonts["title"] = pygame.font.SysFont(["segoeui", "arial"], 17, bold=True)
            fonts["huge"] = pygame.font.SysFont(["segoeui", "arial"], 24, bold=True)
        except (OSError, RuntimeError):
            fonts["tiny"] = pygame.font.Font(None, 16)
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

            if not self.player.moving and not self.gacha_active and not self.gacha_showcase:
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
            elif self.gacha_showcase:
                self.gacha_showcase["timer"] -= dt
                self.gacha_showcase["anim_time"] += dt
                if self.gacha_showcase["timer"] <= 0.0:
                    self.gacha_showcase = None
            elif self.gacha_message_timer > 0:
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
            if self.pre_battle_visualizer.is_open:
                self.pre_battle_visualizer.update(dt)
        else:
            # Mode Battle: Update animasi pemanggilan kartu (tag-in summon animation)
            if self.card_summon_anim:
                self._update_card_summon_anim(dt)

            # Mode Battle: Update jeda animasi NPC tumbang (Defeat Animation)
            if self.npc_defeat_anim:
                self.npc_defeat_anim["timer"] -= dt
                if self.npc_defeat_anim["timer"] <= 0.0:
                    anim = self.npc_defeat_anim
                    self.npc_defeat_anim = None
                    if anim.get("loot"):
                        self.loot_modal = {
                            "loot": anim["loot"],
                            "old_npc": anim["npc"],
                            "next_npc": anim["next_npc"],
                            "heal_amount": anim["heal_amount"],
                            "timer": 0.0,
                            "is_final": anim["is_final"],
                        }
                    elif anim.get("next_npc"):
                        self._start_card_summon_anim(anim["npc"], anim["next_npc"])
                    elif anim.get("is_final"):
                        self.exit_battle()

            # Mode Battle: Cek kemenangan final jika player memenangkan seluruh duel
            if (
                self.battle_system.is_finished
                and self.battle_system.winner == "PLAYER"
                and hasattr(self.battle_system, "last_loot")
                and self.battle_system.last_loot
                and not getattr(self, "final_loot_shown", False)
                and not self.loot_modal
                and not self.npc_defeat_anim
            ):
                self.final_loot_shown = True
                active_m = getattr(self.current_squad, "active_member", None)
                self.npc_defeat_anim = {
                    "npc": active_m or self.npc,
                    "next_npc": None,
                    "heal_amount": 0,
                    "loot": self.battle_system.last_loot,
                    "timer": 1.4,
                    "duration": 1.4,
                    "is_final": True,
                }

            # Mode Battle: Update floating action text timer & VFX animasi
            self.battle_system.update_action_texts(dt)
            self.vfx.update(dt)

            if hasattr(self, "loot_toast") and self.loot_toast:
                self.loot_toast["timer"] -= dt
                if self.loot_toast["timer"] <= 0:
                    self.loot_toast = None

            # Handle giliran NPC dengan jeda singkat (~0.5 detik), tunda jika kartu sedang meluncur, modal loot aktif, atau animasi kalah
            if (
                self.battle_system.state.is_npc_turn
                and not self.battle_system.is_finished
                and not self.card_summon_anim
                and not self.loot_modal
                and not self.npc_defeat_anim
            ):
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
        init_state = None if randomize else getattr(self.optimizer, "last_csp_initial_state", None)
        cfg, stats = self.optimizer.optimize(
            self.selected_ls_algo, initial_state=init_state, player_context=player_ctx, randomize_start=randomize
        )
        self.current_squad_config = cfg
        self.current_optimizer_stats = stats
        self.current_squad = NPCSquad.from_config(cfg)
        self.overlay.set_pre_battle_data(cfg, stats, self.selected_ls_algo)

        # Sinkronisasi data ke modal visualizer AI
        csp_solver = self.optimizer.csp
        if randomize or not self.pre_battle_visualizer.csp_tree:
            self.pre_battle_visualizer.set_csp_data(
                csp_solver.search_tree,
                csp_solver.timeline_steps,
                csp_solver.solution_path_ids,
                csp_solver.tree_width,
                csp_solver.tree_height,
            )
        self.pre_battle_visualizer.set_ls_data(
            self.optimizer.history,
            self.selected_ls_algo,
            self.optimizer.target_difficulty,
        )

        if randomize:
            self.reroll_toast_timer = 1.4

    def enter_pre_battle(self, leader_npc=None):
        self.current_encounter_npc = leader_npc
        self.game_mode = "PRE_BATTLE"
        self.overlay.set_mode("PRE_BATTLE")
        self.overlay.set_chasing_visualization(False)
        self.overlay.stop_path_animation()
        self.npc.chasing = False
        # Jika darah player sebelumnya habis/kalah atau <= 10, pulihkan penuh ke 100
        if getattr(self.player, "persistent_hp", 100) <= 10:
            self.player.persistent_hp = 100
            self.player.persistent_potions = max(2, self.player.persistent_potions)
        self._run_optimization()

    def enter_battle(self):
        self.game_mode = "BATTLE"
        self.overlay.set_mode("BATTLE")
        self.overlay.set_chasing_visualization(False)
        self.overlay.stop_path_animation()
        self.npc.chasing = False
        self.npc_battle_turn_timer = 0.0
        self.battle_log_scroll_offset = 0
        self.card_summon_anim = None
        self.loot_modal = None
        self.npc_defeat_anim = None
        self.final_loot_shown = False
        if hasattr(self, "vfx") and self.vfx:
            self.vfx.animations.clear()
        # Jika darah player sebelumnya habis/kalah atau <= 10, pulihkan penuh ke 100
        if getattr(self.player, "persistent_hp", 100) <= 10:
            self.player.persistent_hp = 100
            self.player.persistent_potions = max(2, self.player.persistent_potions)
        if self.current_squad:
            self.current_squad.reset()
            self.battle_system.reset_with_squad(self.current_squad, player=self.player)
        else:
            self.battle_system.reset()

    def exit_battle(self):
        self.game_mode = "EXPLORATION"
        self.overlay.set_mode("EXPLORATION")
        self.battle_reentry_locked = True
        self.npc.chasing = False
        self.card_summon_anim = None
        self.loot_toast = None
        self.loot_modal = None
        self.npc_defeat_anim = None
        self.final_loot_shown = False
        if hasattr(self, "vfx") and self.vfx:
            self.vfx.animations.clear()

        # Relokasi/respawn NPC yang kalah agar tidak terjadi loop pertempuran tak berujung
        if getattr(self.battle_system, "winner", None) == "PLAYER":
            enc_npc = getattr(self, "current_encounter_npc", None) or self.npc
            if enc_npc:
                enc_npc._spawn()
                enc_npc.chasing = False
                enc_npc.moving = False
                enc_npc.path = []
        self.current_encounter_npc = None

        # Sinkronkan sisa HP dan Potion player secara persistent
        if hasattr(self.battle_system, "state"):
            if self.battle_system.state.player_hp <= 0 or getattr(self.battle_system, "winner", None) == "NPC":
                # Jika Player kalah/tumbang dalam duel, pulihkan HP kembali PENUH (100) saat kembali ke map!
                self.player.persistent_hp = 100
                self.player.persistent_potions = max(2, self.player.persistent_potions)
            else:
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
            elif action == "SECOND WIND!":
                heal_val = getattr(self.battle_system, "last_second_wind_heal", 45)
                self.vfx.trigger_potion(p_pos, heal_val=heal_val)
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
                if self.game_mode == "PRE_BATTLE":
                    if self.pre_battle_visualizer.is_open:
                        self.pre_battle_visualizer.handle_event(event)
                    else:
                        self.overlay.handle_event(event)
                elif self.game_mode == "BATTLE":
                    # Scroll mousewheel pada Decision Tree Overlay (prioritas utama jika aktif)
                    if self.overlay.tree_overlay.visible and self.overlay.tree_overlay.panel_rect.collidepoint(m_pos):
                        self.overlay.tree_overlay.handle_event(event)
                    # Scroll mousewheel pada Battle Log
                    elif self.battle_log_rect.collidepoint(m_pos):
                        total_logs = len(self.battle_system.battle_logs)
                        max_scroll = max(0, total_logs - 2)
                        # event.y > 0 = scroll ke atas (lihat log lama)
                        # event.y < 0 = scroll ke bawah (lihat log terbaru)
                        self.battle_log_scroll_offset = max(0, min(max_scroll, self.battle_log_scroll_offset + event.y))
                    else:
                        self.overlay.handle_event(event)
                else:
                    self._zoom_camera(1.1 if event.y > 0 else 1 / 1.1, m_pos)
            elif event.type == MOUSEBUTTONDOWN:
                pos = event.pos
                if self.game_mode == "PRE_BATTLE":
                    if self.pre_battle_visualizer.is_open:
                        if self.pre_battle_visualizer.handle_event(event):
                            continue
                    if self.btn_pre_battle_inspect.collidepoint(pos):
                        self.pre_battle_visualizer.toggle()
                    elif self.btn_pre_battle_start.collidepoint(pos):
                        self.enter_battle()
                    elif self.btn_pre_battle_reroll.collidepoint(pos):
                        self._run_optimization(randomize=True)
                    elif self.btn_pre_battle_cancel.collidepoint(pos):
                        self.exit_battle()
                    else:
                        self.overlay.handle_event(event)
                elif self.game_mode == "BATTLE":
                    if self.loot_modal:
                        self._dismiss_loot_modal()
                        return
                    # Prioritaskan penanganan klik pada Decision Tree jika sedang aktif
                    if self.overlay.tree_overlay.visible:
                        if self.overlay.tree_overlay.handle_event(event):
                            return
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
                    else:
                        self.overlay.handle_event(event)
                else:
                    if getattr(self, "gacha_showcase", None):
                        self.gacha_showcase = None
                        return
                    self.overlay.handle_event(event)
            elif event.type in (MOUSEBUTTONUP, MOUSEMOTION):
                if self.game_mode == "PRE_BATTLE":
                    if self.pre_battle_visualizer.is_open:
                        self.pre_battle_visualizer.handle_event(event)
                elif self.game_mode == "BATTLE":
                    self.overlay.tree_overlay.handle_event(event)
            elif event.type == KEYDOWN:
                self._handle_key(event.key)

    def _handle_key(self, key):
        if key == K_ESCAPE:
            if getattr(self, "gacha_showcase", None):
                self.gacha_showcase = None
                return
            if self.game_mode == "BATTLE":
                if self.overlay.tree_overlay.visible:
                    self.overlay.tree_overlay.visible = False
                    return
                self.exit_battle()
                return
            elif self.game_mode == "PRE_BATTLE":
                if self.pre_battle_visualizer.is_open:
                    self.pre_battle_visualizer.toggle()
                    return
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
            if self.pre_battle_visualizer.is_open:
                if key == K_t:
                    self.pre_battle_visualizer.toggle()
                    return
                if key == K_SPACE:
                    self.pre_battle_visualizer.toggle_play()
                    return
                if key == K_LEFT:
                    self.pre_battle_visualizer.step_backward()
                    return
                if key == K_RIGHT:
                    self.pre_battle_visualizer.step_forward()
                    return
                if key in (K_1, K_2):
                    self.pre_battle_visualizer.active_tab = "CSP" if key == K_1 else "LOCAL_SEARCH"
                    return
                if key == K_r:
                    self._run_optimization(randomize=True)
                    return
                return

            if key == K_t:
                self.pre_battle_visualizer.toggle()
                return
            elif key in (K_SPACE, K_RETURN):
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
            # Jika modal rampasan perang aktif, tekan ENTER atau SPASI untuk lanjut
            if self.loot_modal:
                if key in (K_RETURN, K_KP_ENTER, K_SPACE, K_ESCAPE):
                    self._dismiss_loot_modal()
                return

            # Shortcut tombol di mode Battle
            if key == K_TAB:
                self.exit_battle()
            elif key == K_r:
                self.battle_log_scroll_offset = 0
                self.card_summon_anim = None
                self.player.persistent_hp = 100
                self.player.persistent_potions = max(2, self.player.persistent_potions)
                if self.current_squad:
                    self.current_squad.reset()
                    self.battle_system.reset_with_squad(self.current_squad, player=self.player)
                else:
                    self.battle_system.reset()
            elif key == K_t:
                self.overlay.toggle_tree_overlay()
            elif self.overlay.tree_overlay.visible:
                if key in (K_t, K_ESCAPE):
                    self.overlay.tree_overlay.visible = False
            elif not self.battle_system.state.is_npc_turn and not self.battle_system.is_finished and not self.card_summon_anim and not self.loot_modal and not self.npc_defeat_anim:
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
            if getattr(self, "gacha_showcase", None):
                if key in (K_RETURN, K_KP_ENTER, K_SPACE, K_e, K_ESCAPE):
                    self.gacha_showcase = None
                return

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
            self._draw_obtained_items_hud()
            if self.gacha_active or getattr(self, "gacha_showcase", None) or self.gacha_message_timer > 0:
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

        # 4. Gambar modal rampasan perang di paling atas (menutup seluruh layar dengan dramatis)
        if self.game_mode == "BATTLE" and getattr(self, "loot_modal", None):
            self._draw_loot_modal()

        # 5. Gambar modal visualizer Pohon CSP & Local Search jika terbuka di mode PRE_BATTLE
        if self.game_mode == "PRE_BATTLE" and self.pre_battle_visualizer.is_open:
            self.pre_battle_visualizer.draw(self.screen, self.fonts)

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

        # Label Teks Badge "🐱 Bolu (X meter)"
        font = self.fonts.get("bubble", self.fonts["sm"])
        txt_surf = font.render(f"🐱 {self.npc.name} ({dist_grid} meter)", True, (255, 255, 255))

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

        if self.npc_defeat_anim:
            # Sprite NPC yang tumbang berkedip merah dan sedikit transparan
            npc_dead_surf = big_npc.copy()
            red_tint = pygame.Surface(npc_dead_surf.get_size(), SRCALPHA)
            red_tint.fill((255, 30, 30, 130))
            npc_dead_surf.blit(red_tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(npc_dead_surf, npc_dead_surf.get_rect(center=(npc_arena_x + n_ox, char_y + n_oy)))
            self._draw_defeat_badge(npc_arena_x, char_y - 20, self.npc_defeat_anim["npc"])
        elif self.card_summon_anim:
            self._draw_card_summon_animation(npc_arena_x, char_y, target_h)
        else:
            self.screen.blit(big_npc, big_npc.get_rect(center=(npc_arena_x + n_ox, char_y + n_oy)))

        # ================================================================== #
        # Kartu Skuad NPC Cadangan (Deck Portrait Bertumpuk di Kanan Layar)
        # Menampilkan potret NPC antrian bertumpuk (kartu berikutnya di depan)
        # ================================================================== #
        self._draw_battle_queue_deck(w, h)

        # Floating Action Text di atas karakter
        self._draw_action_text(self.battle_system.player_action_text, player_arena_x, char_y - 75)
        if not self.card_summon_anim and not self.npc_defeat_anim:
            self._draw_action_text(self.battle_system.npc_action_text, npc_arena_x, char_y - 75)

        # Status & Bar HP
        st = self.battle_system.state
        player_cd_text = f"  (Heavy CD: {st.player_heavy_cd})" if st.player_heavy_cd > 0 else ""
        npc_cd_text = f"  (Heavy CD: {st.npc_heavy_cd})" if st.npc_heavy_cd > 0 else ""
        npc_display_name = active_member.name if active_member else "NPC (Minimax AI)"
        npc_max_hp = active_member.max_hp if active_member else 100
        display_npc_hp = 0 if self.npc_defeat_anim else st.npc_hp
        self._draw_hp_bar(player_arena_x, char_y + 98, "Hero Player", st.player_hp, st.player_defending, st.player_potions, (60, 160, 255), player_cd_text, max_hp=100)
        self._draw_hp_bar(npc_arena_x, char_y + 98, npc_display_name, display_npc_hp, st.npc_defending, st.npc_potions, (255, 90, 80), npc_cd_text, max_hp=npc_max_hp)

        # Banner Notifikasi Rampasan Perang (Spoils of War)
        if hasattr(self, "loot_toast") and self.loot_toast and self.loot_toast["timer"] > 0:
            self._draw_loot_toast(w, h, (player_arena_x + npc_arena_x) // 2)

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

        ltitle = font_bubble.render("RIWAYAT PERTEMPURAN", True, (240, 245, 255))
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

        up_col = (38, 54, 80) if self.battle_log_scroll_offset < max_scroll else (28, 32, 42)
        down_col = (38, 54, 80) if self.battle_log_scroll_offset > 0 else (28, 32, 42)

        pygame.draw.rect(self.screen, up_col, self.btn_log_up, border_radius=3)
        pygame.draw.rect(self.screen, down_col, self.btn_log_down, border_radius=3)

        ts_up = font_bubble.render("▲", True, (240, 245, 255) if self.battle_log_scroll_offset < max_scroll else (90, 100, 115))
        ts_dn = font_bubble.render("▼", True, (240, 245, 255) if self.battle_log_scroll_offset > 0 else (90, 100, 115))
        self.screen.blit(ts_up, (self.btn_log_up.centerx - ts_up.get_width() // 2, self.btn_log_up.centery - ts_up.get_height() // 2))
        self.screen.blit(ts_dn, (self.btn_log_down.centerx - ts_dn.get_width() // 2, self.btn_log_down.centery - ts_dn.get_height() // 2))

        ly = self.battle_log_rect.y + 28
        if display_logs:
            for log_line in display_logs:
                ts = font_sm.render(f"• {log_line}", True, (240, 245, 250))
                self.screen.blit(ts, (self.battle_log_rect.x + 14, ly))
                ly += 22
        else:
            ts = font_sm.render("• Pertarungan dimulai. Pilih aksi pada panel kiri untuk bertarung.", True, (145, 155, 175))
            self.screen.blit(ts, (self.battle_log_rect.x + 14, ly))

        if total_logs > 2 and max_scroll > 0:
            track_y = self.battle_log_rect.y + 26
            track_h = log_h - 32
            thumb_h = max(10, int(track_h * (2.0 / total_logs)))
            norm_pos = 1.0 - (self.battle_log_scroll_offset / float(max_scroll))
            thumb_y = track_y + int(norm_pos * (track_h - thumb_h))
            pygame.draw.rect(self.screen, (40, 48, 64), pygame.Rect(self.battle_log_rect.right - 6, track_y, 3, track_h), border_radius=1)
            pygame.draw.rect(self.screen, (80, 165, 255), pygame.Rect(self.battle_log_rect.right - 6, thumb_y, 3, thumb_h), border_radius=1)

        # ------------------------------------------------------------------ #
        # 2. Tombol Elegan: [Lihat Decision Tree (T)] di Atas Battle Log
        # ------------------------------------------------------------------ #
        btn_tree_h = 32
        self.btn_tree_modal = pygame.Rect(panel_w + 15, log_y - btn_tree_h - 8, 255, btn_tree_h)
        pygame.draw.rect(self.screen, (32, 90, 58), self.btn_tree_modal, border_radius=6)
        pygame.draw.rect(self.screen, (60, 165, 105), self.btn_tree_modal, 1, border_radius=6)
        tree_btn_txt = font_bubble.render("[T] Lihat Pohon Keputusan (Tree)", True, (255, 255, 255))
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

    def _draw_battle_queue_deck(self, w: int, h: int):
        """Merender antrian kartu NPC cadangan dalam bentuk tumpukan kartu potret (deck).
        
        Karakter yang akan bertarung berikutnya (Next Challenger) berada di paling depan,
        dan karakter berikutnya berada di belakangnya (efek stacked cards).
        """
        if not self.current_squad or len(self.current_squad.members) <= 1:
            return

        bench_w = 232
        bench_x = w - bench_w - 18
        header_y = 20

        # 1. Header Panel Antrian Cadangan
        hdr_rect = pygame.Rect(bench_x, header_y, bench_w, 34)
        pygame.draw.rect(self.screen, (16, 20, 30, 240), hdr_rect, border_radius=8)
        pygame.draw.rect(self.screen, (65, 80, 110), hdr_rect, 1, border_radius=8)

        queue = [m for i, m in enumerate(self.current_squad.members) if i > self.current_squad.active_index]
        q_count = len(queue)
        hdr_title = f"ANTRIAN CADANGAN ({q_count})"
        t_surf = self.fonts.get("bubble", self.fonts["sm"]).render(hdr_title, True, (255, 215, 75))
        self.screen.blit(t_surf, (hdr_rect.x + (bench_w - t_surf.get_width()) // 2, hdr_rect.y + 7))

        curr_y = header_y + 40

        # 2. Status Petarung yang Telah Gugur (jika ada)
        defeated = [m for i, m in enumerate(self.current_squad.members) if i < self.current_squad.active_index]
        if defeated:
            d_h = 24
            d_rect = pygame.Rect(bench_x, curr_y, bench_w, d_h)
            pygame.draw.rect(self.screen, (28, 16, 18, 225), d_rect, border_radius=6)
            pygame.draw.rect(self.screen, (120, 45, 50), d_rect, 1, border_radius=6)
            names_str = ", ".join(m.name.split()[0] for m in defeated)
            d_txt = self.fonts["sm"].render(f"Gugur ({len(defeated)}): {names_str}", True, (240, 110, 110))
            self.screen.blit(d_txt, (bench_x + 8, curr_y + 4))
            curr_y += 30

        if not queue:
            # Tidak ada cadangan tersisa (Duel Terakhir)
            empty_rect = pygame.Rect(bench_x, curr_y + 10, bench_w, 140)
            pygame.draw.rect(self.screen, (18, 20, 28, 225), empty_rect, border_radius=10)
            pygame.draw.rect(self.screen, (70, 80, 105), empty_rect, 1, border_radius=10)

            t1 = self.fonts.get("bubble", self.fonts["sm"]).render("DUEL TERAKHIR", True, (255, 215, 80))
            t2 = self.fonts["sm"].render("Semua cadangan telah turun.", True, (165, 175, 195))
            t3 = self.fonts["sm"].render("Habisi petarung di arena ini", True, (135, 145, 165))
            t4 = self.fonts["sm"].render("untuk meraih kemenangan!", True, (135, 145, 165))

            self.screen.blit(t1, t1.get_rect(center=(empty_rect.centerx, empty_rect.y + 30)))
            self.screen.blit(t2, t2.get_rect(center=(empty_rect.centerx, empty_rect.y + 60)))
            self.screen.blit(t3, t3.get_rect(center=(empty_rect.centerx, empty_rect.y + 88)))
            self.screen.blit(t4, t4.get_rect(center=(empty_rect.centerx, empty_rect.y + 108)))
            return

        # Ukuran kartu portrait deck
        card_w = 188
        card_h = 248

        max_depth = len(queue) - 1
        base_x = bench_x + 4
        base_y = curr_y + 14 + (max_depth * 18)

        # Gambar dari kedalaman terdalam (kartu belakang) ke depth 0 (kartu depan)
        for depth in range(len(queue) - 1, -1, -1):
            mem = queue[depth]
            is_front = (depth == 0)

            offset_x = depth * 22
            offset_y = -depth * 18
            c_x = base_x + offset_x
            c_y = base_y + offset_y

            ctype_lower = mem.char_type.lower()
            if ctype_lower == "warrior":
                theme_border = (225, 140, 45)
                theme_bg = (32, 26, 24)
            elif ctype_lower == "ranger":
                theme_border = (48, 195, 95)
                theme_bg = (20, 30, 24)
            elif ctype_lower == "mage":
                theme_border = (65, 155, 245)
                theme_bg = (20, 26, 38)
            elif ctype_lower == "assassin":
                theme_border = (195, 65, 230)
                theme_bg = (28, 18, 32)
            else:
                theme_border = (180, 180, 190)
                theme_bg = (24, 24, 28)

            # Drop Shadow
            shadow_surf = pygame.Surface((card_w, card_h), SRCALPHA)
            shadow_alpha = 140 if is_front else 85
            shadow_surf.fill((0, 0, 0, shadow_alpha))
            self.screen.blit(shadow_surf, (c_x + 6, c_y + 8))

            # Surface Kartu
            card_surf = self._build_npc_card_surface(mem, is_front=is_front, card_w=card_w, card_h=card_h, depth=depth)
            self.screen.blit(card_surf, (c_x, c_y))

    def _build_npc_card_surface(self, mem, is_front: bool = True, card_w: int = 188, card_h: int = 248, depth: int = 0) -> pygame.Surface:
        """Membuat surface grafis kartu potret NPC dengan visual JRPG elegan."""
        card_surf = pygame.Surface((card_w, card_h), SRCALPHA)

        ctype_lower = mem.char_type.lower()
        if ctype_lower == "warrior":
            theme_border = (225, 140, 45)
            theme_bg = (32, 26, 24)
        elif ctype_lower == "ranger":
            theme_border = (48, 195, 95)
            theme_bg = (20, 30, 24)
        elif ctype_lower == "mage":
            theme_border = (65, 155, 245)
            theme_bg = (20, 26, 38)
        elif ctype_lower == "assassin":
            theme_border = (195, 65, 230)
            theme_bg = (28, 18, 32)
        else:
            theme_border = (180, 180, 190)
            theme_bg = (24, 24, 28)

        if not is_front:
            dim_bg = tuple(max(10, int(c * 0.58)) for c in theme_bg)
            dim_bdr = tuple(max(35, int(c * 0.55)) for c in theme_border)
            card_surf.fill((*dim_bg, 245))
            pygame.draw.rect(card_surf, dim_bdr, (0, 0, card_w, card_h), 1, border_radius=10)

            # Tab nama di pojok kanan atas yang mencuat
            q_num = (self.current_squad.active_index + 1 + depth + 1) if self.current_squad else (depth + 1)
            peek_lbl = self.fonts["sm"].render(f"#{q_num} {mem.name.split()[0]}", True, theme_border)
            peek_rect = pygame.Rect(card_w - peek_lbl.get_width() - 14, 6, peek_lbl.get_width() + 10, 18)
            pygame.draw.rect(card_surf, (18, 22, 32), peek_rect, border_radius=4)
            pygame.draw.rect(card_surf, dim_bdr, peek_rect, 1, border_radius=4)
            card_surf.blit(peek_lbl, (peek_rect.x + 5, peek_rect.y + 2))
        else:
            card_surf.fill((*theme_bg, 252))
            pygame.draw.rect(card_surf, theme_border, (0, 0, card_w, card_h), 2, border_radius=10)
            pygame.draw.rect(card_surf, (255, 255, 255, 45), (2, 2, card_w - 4, card_h - 4), 1, border_radius=8)

            badge_lbl = self.fonts["sm"].render("NEXT CHALLENGER", True, (255, 225, 90))
            badge_rect = pygame.Rect((card_w - badge_lbl.get_width() - 14) // 2, 7, badge_lbl.get_width() + 14, 18)
            pygame.draw.rect(card_surf, (60, 45, 15), badge_rect, border_radius=4)
            pygame.draw.rect(card_surf, (225, 180, 50), badge_rect, 1, border_radius=4)
            card_surf.blit(badge_lbl, (badge_rect.x + 7, badge_rect.y + 2))

        # Bingkai Portrait Tengah
        p_size = 108
        p_x = (card_w - p_size) // 2
        p_y = 29
        p_rect = pygame.Rect(p_x, p_y, p_size, p_size)
        pygame.draw.rect(card_surf, (12, 14, 20), p_rect, border_radius=8)

        if mem.portrait:
            p_img = pygame.transform.smoothscale(mem.portrait, (p_size - 4, p_size - 4))
            if not is_front:
                dark_tint = pygame.Surface((p_size - 4, p_size - 4), SRCALPHA)
                dark_tint.fill((0, 0, 0, 80))
                card_surf.blit(p_img, (p_x + 2, p_y + 2))
                card_surf.blit(dark_tint, (p_x + 2, p_y + 2))
            else:
                card_surf.blit(p_img, (p_x + 2, p_y + 2))
        else:
            ph = self.fonts.get("bubble", self.fonts["sm"]).render("🐱", True, (255, 255, 255))
            card_surf.blit(ph, ph.get_rect(center=p_rect.center))

        p_bdr_col = theme_border if is_front else tuple(max(30, int(c * 0.55)) for c in theme_border)
        pygame.draw.rect(card_surf, p_bdr_col, p_rect, 2 if is_front else 1, border_radius=8)

        # Footer: Nama, Kelas & Profil
        name_font = self.fonts.get("bubble", self.fonts["sm"])
        txt_name = name_font.render(mem.name, True, (255, 255, 255) if is_front else (170, 175, 185))
        card_surf.blit(txt_name, txt_name.get_rect(center=(card_w // 2, p_y + p_size + 14)))

        job_txt = self.fonts["sm"].render(f"{mem.char_type.capitalize()} • {mem.eval_profile}", True, theme_border if is_front else (135, 140, 155))
        card_surf.blit(job_txt, job_txt.get_rect(center=(card_w // 2, p_y + p_size + 30)))

        # Stat Pill: HP & ATK/DEF
        stat_rect = pygame.Rect(10, p_y + p_size + 44, card_w - 20, 24)
        pygame.draw.rect(card_surf, (16, 18, 26, 230), stat_rect, border_radius=6)
        pygame.draw.rect(card_surf, (50, 60, 80) if is_front else (35, 40, 55), stat_rect, 1, border_radius=6)

        stat_str = f"HP {mem.max_hp}  │ +{mem.atk_bonus}A +{mem.def_bonus}D"
        stat_lbl = self.fonts["sm"].render(stat_str, True, (220, 230, 245) if is_front else (145, 150, 160))
        card_surf.blit(stat_lbl, stat_lbl.get_rect(center=stat_rect.center))

        return card_surf

    def _on_npc_tag_in(self, old_npc, next_npc, heal_amount: int = 45, loot: Optional[Dict[str, Any]] = None):
        """Callback saat NPC aktif tumbang dan NPC berikutnya maju ke duel arena."""
        self.battle_system.is_locked = True
        self.npc_battle_turn_timer = 0.0

        if loot is None and hasattr(self.battle_system, "last_loot"):
            loot = self.battle_system.last_loot

        # Mulai animasi kekalahan NPC terlebih dahulu (terlihat tulisan kalah) sebelum modal rampasan
        self.npc_defeat_anim = {
            "npc": old_npc,
            "next_npc": next_npc,
            "heal_amount": heal_amount,
            "loot": loot,
            "timer": 1.4,
            "duration": 1.4,
            "is_final": False,
        }

    def _start_card_summon_anim(self, old_npc, next_npc):
        """Memulai animasi peluncuran kartu potret dan transformasi ke karakter NPC."""
        w, h = self.screen.get_size()
        bench_w = 232
        bench_x = w - bench_w - 18
        header_y = 20
        curr_y = header_y + 40
        defeated_count = self.current_squad.active_index if self.current_squad else 1
        if defeated_count > 0:
            curr_y += 30

        remaining_queue_len = len(self.current_squad.members) - 1 - self.current_squad.active_index if self.current_squad else 0
        base_x = bench_x + 4
        base_y = curr_y + 14 + (remaining_queue_len * 18)

        card_w, card_h = 188, 248
        start_center = (base_x + card_w // 2, base_y + card_h // 2)

        (_, _), (npc_arena_x, char_y) = self._get_battle_char_positions()
        target_center = (npc_arena_x, char_y)

        ctype_lower = next_npc.char_type.lower()
        if ctype_lower == "warrior":
            theme_color = (235, 145, 45)
            trail_colors = [(255, 180, 50), (255, 235, 120)]
        elif ctype_lower == "ranger":
            theme_color = (48, 205, 95)
            trail_colors = [(50, 220, 100), (180, 255, 160)]
        elif ctype_lower == "mage":
            theme_color = (65, 165, 255)
            trail_colors = [(70, 175, 255), (195, 230, 255)]
        elif ctype_lower == "assassin":
            theme_color = (195, 65, 230)
            trail_colors = [(210, 70, 245), (245, 150, 255)]
        else:
            theme_color = (200, 200, 210)
            trail_colors = [(220, 220, 230), (255, 255, 255)]

        self.card_summon_anim = {
            "old_npc": old_npc,
            "next_npc": next_npc,
            "start_pos": start_center,
            "target_pos": target_center,
            "timer": 0.0,
            "duration": 1.75,
            "fly_duration": 0.75,
            "theme_color": theme_color,
            "trail_colors": trail_colors,
            "particles": [],
            "burst_particles": [],
            "burst_triggered": False,
        }

    def _dismiss_loot_modal(self):
        """Menutup modal rampasan perang dan melanjutkan pemanggilan kartu NPC berikutnya."""
        if not self.loot_modal:
            return
        modal = self.loot_modal
        self.loot_modal = None

        if modal.get("next_npc") and not modal.get("is_final", False):
            self._start_card_summon_anim(modal["old_npc"], modal["next_npc"])
        else:
            self.battle_system.is_locked = False
            if modal.get("is_final", False):
                self.exit_battle()

    def _update_card_summon_anim(self, dt: float):
        """Memperbarui fisika partikel dan timeline animasi pemanggilan kartu."""
        if not self.card_summon_anim:
            return

        import random

        anim = self.card_summon_anim
        anim["timer"] += dt
        t = anim["timer"]
        fly_dur = anim["fly_duration"]

        # 1. Update posisi partikel trail
        for p in anim["particles"]:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt
        anim["particles"] = [p for p in anim["particles"] if p["life"] > 0]

        # 2. Spawn partikel trail selama kartu meluncur (Fase 1: 0.0s s/d 0.75s)
        if t < fly_dur:
            prog = min(1.0, t / fly_dur)
            ease = 1.0 - (1.0 - prog) ** 3
            cur_x = anim["start_pos"][0] + (anim["target_pos"][0] - anim["start_pos"][0]) * ease
            arc_y = -math.sin(prog * math.pi) * 38.0
            cur_y = anim["start_pos"][1] + (anim["target_pos"][1] - anim["start_pos"][1]) * ease + arc_y

            for _ in range(3):
                col = random.choice(anim["trail_colors"])
                anim["particles"].append({
                    "x": cur_x + random.uniform(-16, 16),
                    "y": cur_y + random.uniform(-16, 16),
                    "vx": random.uniform(-25, 25),
                    "vy": random.uniform(-25, 25),
                    "life": random.uniform(0.25, 0.45),
                    "max_life": 0.45,
                    "radius": random.uniform(2.5, 5.0),
                    "color": col,
                })

        # 3. Pemicu Burst Transformasi pada t >= 1.15s (Fase 2B)
        if t >= 1.15 and not anim["burst_triggered"]:
            anim["burst_triggered"] = True
            target_x, target_y = anim["target_pos"]
            self.vfx.trigger_hit_shake("NPC", intensity=8.0, duration=0.25)
            # Spawn 36 partikel ledakan memancar 360 derajat
            for i in range(36):
                angle = (i / 36.0) * math.pi * 2 + random.uniform(-0.1, 0.1)
                spd = random.uniform(140.0, 360.0)
                col = random.choice([(255, 255, 255), (255, 240, 160), *anim["trail_colors"]])
                anim["burst_particles"].append({
                    "x": target_x,
                    "y": target_y,
                    "vx": math.cos(angle) * spd,
                    "vy": math.sin(angle) * spd,
                    "life": random.uniform(0.35, 0.65),
                    "max_life": 0.65,
                    "radius": random.uniform(3.0, 6.5),
                    "color": col,
                })

        # 4. Update partikel burst
        for bp in anim["burst_particles"]:
            bp["x"] += bp["vx"] * dt
            bp["y"] += bp["vy"] * dt
            bp["vx"] *= max(0.0, 1.0 - 2.8 * dt)
            bp["vy"] *= max(0.0, 1.0 - 2.8 * dt)
            bp["life"] -= dt
        anim["burst_particles"] = [bp for bp in anim["burst_particles"] if bp["life"] > 0]

        # 5. Selesai animasi (t >= duration)
        if t >= anim["duration"]:
            self.card_summon_anim = None
            self.battle_system.is_locked = False

    def _draw_card_summon_animation(self, npc_arena_x: int, char_y: int, target_h: int):
        """Merender seluruh rangkaian animasi meluncurnya kartu NPC dan transformasi ke karakter."""
        if not self.card_summon_anim:
            return

        anim = self.card_summon_anim
        t = anim["timer"]
        next_npc = anim["next_npc"]
        old_npc = anim.get("old_npc")
        fly_dur = anim["fly_duration"]
        theme_col = anim["theme_color"]

        card_w, card_h = 188, 248

        # --- A. Efek Karakter Lama Memudar (Fade Out) ---
        if old_npc and t < 0.40:
            old_fade = max(0, int(255 * (1.0 - (t / 0.40))))
            old_img = old_npc.battle_sprite or old_npc.portrait or self.npc.sprite.current_image
            asp = old_img.get_width() / float(old_img.get_height())
            old_scaled = pygame.transform.smoothscale(old_img, (int(round(target_h * asp)), target_h))
            f_surf = old_scaled.copy()
            f_surf.fill((160, 40, 40, 120), special_flags=pygame.BLEND_RGBA_MULT)
            f_surf.set_alpha(old_fade)
            self.screen.blit(f_surf, f_surf.get_rect(center=(npc_arena_x, char_y)))

        # --- B. Partikel Jejak & Trail ---
        for p in anim["particles"]:
            alpha = max(0, min(255, int(255 * (p["life"] / p["max_life"]))))
            rad = max(1, int(p["radius"]))
            p_surf = pygame.Surface((rad * 2 + 4, rad * 2 + 4), SRCALPHA)
            pygame.draw.circle(p_surf, (*p["color"], alpha), (rad + 2, rad + 2), rad)
            self.screen.blit(p_surf, (int(p["x"] - rad - 2), int(p["y"] - rad - 2)))

        # --- C. Lingkaran Sihir Pemanggilan (Magic Summoning Circle di Tanah) ---
        if t >= 0.50:
            circle_prog = min(1.0, (t - 0.50) / 0.35)
            circle_fade = 1.0 if t < 1.45 else max(0.0, 1.0 - (t - 1.45) / 0.30)
            circle_alpha = int(210 * circle_prog * circle_fade)

            if circle_alpha > 0:
                cw, ch = 190, 64
                c_surf = pygame.Surface((cw, ch), SRCALPHA)
                pygame.draw.ellipse(c_surf, (*theme_col, circle_alpha), (4, 4, cw - 8, ch - 8), 2)
                pygame.draw.ellipse(c_surf, (255, 255, 255, int(circle_alpha * 0.8)), (24, 12, cw - 48, ch - 24), 1)
                rot_ang = t * 3.5
                pts = []
                for i in range(6):
                    ang = rot_ang + i * (math.pi / 3.0)
                    rx = (cw // 2) + math.cos(ang) * (cw // 2 - 28)
                    ry = (ch // 2) + math.sin(ang) * (ch // 2 - 14)
                    pts.append((int(rx), int(ry)))
                if len(pts) >= 6:
                    pygame.draw.polygon(c_surf, (*theme_col, int(circle_alpha * 0.45)), [pts[0], pts[2], pts[4]], 1)
                    pygame.draw.polygon(c_surf, (*theme_col, int(circle_alpha * 0.45)), [pts[1], pts[3], pts[5]], 1)

                self.screen.blit(c_surf, c_surf.get_rect(center=(npc_arena_x, char_y + 68)))

        # --- D. FASE 1: Kartu Meluncur Menuju Tengah (0.0s s/d 0.75s) ---
        if t < fly_dur:
            prog = min(1.0, t / fly_dur)
            ease = 1.0 - (1.0 - prog) ** 3
            cur_x = anim["start_pos"][0] + (anim["target_pos"][0] - anim["start_pos"][0]) * ease
            arc_y = -math.sin(prog * math.pi) * 38.0
            cur_y = anim["start_pos"][1] + (anim["target_pos"][1] - anim["start_pos"][1]) * ease + arc_y

            scale = 1.0 + 0.12 * math.sin(prog * math.pi)
            angle = -math.sin(prog * math.pi) * 8.0

            raw_card = self._build_npc_card_surface(next_npc, is_front=True, card_w=card_w, card_h=card_h)
            sc_w = int(card_w * scale)
            sc_h = int(card_h * scale)
            card_scaled = pygame.transform.smoothscale(raw_card, (sc_w, sc_h))

            shadow = pygame.Surface((sc_w, sc_h), SRCALPHA)
            shadow.fill((0, 0, 0, 110))
            if abs(angle) > 0.5:
                card_rot = pygame.transform.rotate(card_scaled, angle)
                shadow_rot = pygame.transform.rotate(shadow, angle)
                self.screen.blit(shadow_rot, shadow_rot.get_rect(center=(int(cur_x + 8), int(cur_y + 12))))
                self.screen.blit(card_rot, card_rot.get_rect(center=(int(cur_x), int(cur_y))))
            else:
                self.screen.blit(shadow, shadow.get_rect(center=(int(cur_x + 8), int(cur_y + 12))))
                self.screen.blit(card_scaled, card_scaled.get_rect(center=(int(cur_x), int(cur_y))))

        # --- E. FASE 2: Transformasi dari Kartu ke Karakter NPC (0.75s s/d 1.75s) ---
        else:
            n_ox, n_oy = self.vfx.get_shake_offset("NPC")
            center_x = npc_arena_x + n_ox
            center_y = char_y + n_oy

            # Sub-fase 2A: Kartu Melayang, Menyerap Energi, dan Flip 3D (0.75s s/d 1.15s)
            if t < 1.15:
                flip_prog = (t - 0.75) / 0.40
                cos_val = max(0.01, math.cos(flip_prog * (math.pi / 2.0)))
                raw_card = self._build_npc_card_surface(next_npc, is_front=True, card_w=card_w, card_h=card_h)
                cur_cw = max(2, int(card_w * 1.12 * cos_val))
                cur_ch = int(card_h * 1.12)
                card_scaled = pygame.transform.smoothscale(raw_card, (cur_cw, cur_ch))

                glow_overlay = pygame.Surface((cur_cw, cur_ch), SRCALPHA)
                glow_alpha = int(220 * flip_prog)
                glow_overlay.fill((255, 255, 255, glow_alpha))
                card_scaled.blit(glow_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

                self.screen.blit(card_scaled, card_scaled.get_rect(center=(center_x, center_y)))

            # Sub-fase 2B & 2C: Flash Ledakan & Karakter Terbentuk (1.15s s/d 1.75s)
            else:
                char_prog = min(1.0, (t - 1.15) / 0.60)
                bounce = 1.0 + 0.32 * math.exp(-char_prog * 5.0) * math.cos(char_prog * math.pi * 2.5)

                n_img = next_npc.battle_sprite
                if not n_img and next_npc.char_type in self.battle_sprites:
                    n_img = self.battle_sprites[next_npc.char_type]
                elif not n_img:
                    n_img = next_npc.portrait or self.npc.sprite.current_image

                asp = n_img.get_width() / float(n_img.get_height())
                final_h = int(target_h * bounce)
                final_w = int(round(final_h * asp))
                char_scaled = pygame.transform.smoothscale(n_img, (max(1, final_w), max(1, final_h)))

                if char_prog < 0.70:
                    aura_alpha = int(180 * (1.0 - char_prog / 0.70))
                    aura_surf = char_scaled.copy()
                    aura_surf.fill((*theme_col, aura_alpha), special_flags=pygame.BLEND_RGBA_MULT)
                    self.screen.blit(aura_surf, aura_surf.get_rect(center=(center_x, center_y)))

                self.screen.blit(char_scaled, char_scaled.get_rect(center=(center_x, center_y)))

                flash_dur = 0.20
                if t < 1.15 + flash_dur:
                    flash_prog = (t - 1.15) / flash_dur
                    flash_alpha = int(240 * (1.0 - flash_prog))
                    beam_w = int(90 * (1.0 - flash_prog))
                    if beam_w > 0:
                        beam_surf = pygame.Surface((beam_w, 280), SRCALPHA)
                        beam_surf.fill((255, 255, 255, flash_alpha))
                        self.screen.blit(beam_surf, beam_surf.get_rect(center=(center_x, center_y)))

                banner_font = self.fonts.get("bubble", self.fonts["sm"])
                badge_txt = banner_font.render(f"TAG-IN: {next_npc.name.upper()}", True, (255, 235, 120))
                b_rect = badge_txt.get_rect(center=(center_x, center_y - 88))
                b_bg = pygame.Rect(b_rect.x - 8, b_rect.y - 4, b_rect.width + 16, b_rect.height + 8)
                pygame.draw.rect(self.screen, (20, 24, 34, 230), b_bg, border_radius=6)
                pygame.draw.rect(self.screen, theme_col, b_bg, 2, border_radius=6)
                self.screen.blit(badge_txt, b_rect)

        # --- F. Partikel Burst Transformasi (360 derajat) ---
        for bp in anim["burst_particles"]:
            alpha = max(0, min(255, int(255 * (bp["life"] / bp["max_life"]))))
            rad = max(1, int(bp["radius"]))
            bp_surf = pygame.Surface((rad * 2 + 4, rad * 2 + 4), SRCALPHA)
            pygame.draw.circle(bp_surf, (*bp["color"], alpha), (rad + 2, rad + 2), rad)
            self.screen.blit(bp_surf, (int(bp["x"] - rad - 2), int(bp["y"] - rad - 2)))

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
        t_surf = font_huge.render("PERSIAPAN PERTEMPURAN (PRE-BATTLE)", True, (255, 220, 90))
        self.screen.blit(t_surf, (area_cx - t_surf.get_width() // 2, 24))

        sub_txt = "Keseimbangan komposisi skuad lawan dioptimasi via CSP (MRV+LCV+AC-3) & Local Search"
        sub_surf = font_sm.render(sub_txt, True, (160, 180, 205))
        self.screen.blit(sub_surf, (area_cx - sub_surf.get_width() // 2, 58))

        # Sisi Kiri: Profil Player - Diperbesar mengisi space vertikal
        btn_h = 44
        btn_y = h - 68
        available_h = max(380, btn_y - 20 - 92)

        p_card_w = min(340, int(arena_w * 0.40))
        p_card_h = available_h
        p_card_x = panel_w + 20
        p_card_y = 90
        p_card_rect = pygame.Rect(p_card_x, p_card_y, p_card_w, p_card_h)

        pygame.draw.rect(self.screen, (20, 26, 38), p_card_rect, border_radius=10)
        pygame.draw.rect(self.screen, (55, 95, 145), p_card_rect, 1, border_radius=10)

        p_header = font_title.render("Hero Utama (Player)", True, (140, 205, 255))
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
        pygame.draw.rect(self.screen, (32, 38, 50), (p_card_x + 18, hp_bar_y, hp_bar_w, hp_bar_h), border_radius=4)
        hp_fill = int((self.player.persistent_hp / 100.0) * hp_bar_w)
        if hp_fill > 0:
            pygame.draw.rect(self.screen, (45, 140, 225), (p_card_x + 18, hp_bar_y, hp_fill, hp_bar_h), border_radius=4)
        pygame.draw.rect(self.screen, (75, 105, 150), (p_card_x + 18, hp_bar_y, hp_bar_w, hp_bar_h), 1, border_radius=4)
        hp_lbl = font_sm.render(f"HP: {self.player.persistent_hp} / 100", True, (240, 245, 255))
        self.screen.blit(hp_lbl, (p_card_x + 18 + (hp_bar_w - hp_lbl.get_width()) // 2, hp_bar_y + 1))

        py_stat = hp_bar_y + 26
        p_stats = [
            f"• Ramuan Cadangan : {self.player.persistent_potions} Botol (+25 HP)",
            f"• Bonus Serangan  : +{self.player.atk_bonus} ATK",
            f"• Bonus Ketahanan : +{self.player.def_bonus} DEF Flat",
            "• Karakteristik   : Pengelana Tangguh",
        ]
        for s in p_stats:
            self.screen.blit(font_sm.render(s, True, (215, 228, 245)), (p_card_x + 18, py_stat))
            py_stat += 22

        # Rincian Inventori Barang
        py_stat += 6
        self.screen.blit(font_bubble.render("Artefak & Perlengkapan:", True, (245, 210, 85)), (p_card_x + 18, py_stat))
        ix = p_card_x + 18
        iy = py_stat + 24
        max_ix = p_card_rect.right - 44
        name_to_key = {
            "Pedang Ksatria Oyen": "item_sword",
            "Busur Presisi Kuro": "item_bow",
            "Belati Bayangan Kage": "item_dagger",
            "Tongkat Sihir Shiro": "mega_potion",
            "health_potion": "health_potion",
            "mega_potion": "mega_potion",
            "item_sword": "item_sword",
            "item_shield": "item_shield",
            "item_boots": "item_boots",
            "item_bow": "item_bow",
            "item_dagger": "item_dagger",
        }
        for it in (self.player.inventory or ["item_sword"]):
            img_key = name_to_key.get(it, it)
            if img_key in self.item_images:
                if ix > max_ix:
                    ix = p_card_x + 18
                    iy += 38
                icon = pygame.transform.smoothscale(self.item_images[img_key], (32, 32))
                self.screen.blit(icon, (ix, iy))
                ix += 38

        # Sisi Kanan: Profil Squad NPC Lawan (1 - 3 Member) - Tema Obsidian Slate Elegan & Bersatu
        squad_area_x = p_card_rect.right + 20
        squad_area_w = (panel_w + arena_w - 20) - squad_area_x

        sq_header = font_title.render("Skuad Lawan (CSP & Local Search)", True, (245, 175, 110))
        self.screen.blit(sq_header, (squad_area_x, p_card_y - 2))

        members = self.current_squad.members if self.current_squad else []
        num_m = max(1, len(members))
        gap = 10
        member_card_h = max(100, (available_h - 26 - (num_m - 1) * gap) // num_m)
        m_y = p_card_y + 26

        # Warna Kotak Bersatu yang Teduh & Tidak Terlalu Warna-Warni
        card_bg_col = (22, 26, 36)
        card_border_col = (52, 65, 88)

        for idx, m in enumerate(members):
            m_rect = pygame.Rect(squad_area_x, m_y, squad_area_w, member_card_h)
            ctype_lower = m.char_type.lower()
            if ctype_lower == "warrior":
                job_label = "WARRIOR"
                pill_bg = (38, 28, 20)
                pill_border = (165, 105, 45)
                pill_text_col = (245, 185, 105)
                trait_desc = "Ketahanan tinggi & serangan seimbang"
            elif ctype_lower == "ranger":
                job_label = "RANGER"
                pill_bg = (20, 34, 25)
                pill_border = (50, 135, 75)
                pill_text_col = (115, 230, 150)
                trait_desc = "Pemanah lincah dengan akurasi tinggi"
            elif ctype_lower == "mage":
                job_label = "MAGE"
                pill_bg = (20, 30, 44)
                pill_border = (55, 115, 185)
                pill_text_col = (130, 195, 255)
                trait_desc = "Spesialis sihir berdaya hancur tinggi"
            elif ctype_lower == "assassin":
                job_label = "ASSASSIN"
                pill_bg = (34, 20, 36)
                pill_border = (145, 70, 165)
                pill_text_col = (225, 135, 250)
                trait_desc = "Penyelinap lincah & serangan kritis"
            else:
                job_label = ctype_lower.upper()
                pill_bg = (26, 30, 38)
                pill_border = (100, 115, 135)
                pill_text_col = (200, 210, 225)
                trait_desc = "Petarung tangguh tim AI"

            pygame.draw.rect(self.screen, card_bg_col, m_rect, border_radius=8)
            pygame.draw.rect(self.screen, card_border_col, m_rect, 1, border_radius=8)

            # Thumbnail Besar Full-Body Sprite
            npc_thumb = m.battle_sprite or m.portrait
            if npc_thumb:
                asp = npc_thumb.get_width() / float(npc_thumb.get_height())
                thumb_target_h = min(115, member_card_h - 18)
                p_icon = pygame.transform.smoothscale(npc_thumb, (int(round(thumb_target_h * asp)), thumb_target_h))
                self.screen.blit(p_icon, p_icon.get_rect(center=(m_rect.x + 52, m_rect.centery)))
            else:
                pygame.draw.rect(self.screen, (40, 46, 60), (m_rect.x + 12, m_rect.y + 12, 64, 64), border_radius=6)

            tx = m_rect.x + 104
            ty = m_rect.y + max(8, (member_card_h - 85) // 2)

            # Baris 1: Nama & Pill Badge Job Elegan
            t_name = font_title.render(f"{idx+1}. {m.name}", True, (245, 235, 195))
            self.screen.blit(t_name, (tx, ty))

            pill_txt = font_sm.render(job_label, True, pill_text_col)
            pill_w = pill_txt.get_width() + 12
            pill_h = 18
            pill_rect = pygame.Rect(tx + t_name.get_width() + 10, ty + 2, pill_w, pill_h)
            pygame.draw.rect(self.screen, pill_bg, pill_rect, border_radius=4)
            pygame.draw.rect(self.screen, pill_border, pill_rect, 1, border_radius=4)
            self.screen.blit(pill_txt, (pill_rect.x + 6, pill_rect.y + 1))

            # Baris 2: Mini HP Bar (Warna Coral Konsisten) & Potions
            m_hp_w = max(40, min(140, squad_area_w - 290))
            m_hp_y = ty + 24
            pygame.draw.rect(self.screen, (34, 40, 52), (tx, m_hp_y, m_hp_w, 13), border_radius=3)
            m_fill = max(0, min(m_hp_w, int((m.max_hp / 120.0) * m_hp_w)))
            pygame.draw.rect(self.screen, (215, 85, 75), (tx, m_hp_y, m_fill, 13), border_radius=3)
            txt_hp = font_sm.render(f"{m.max_hp} HP  │  {m.potions} Potion", True, (235, 242, 252))
            self.screen.blit(txt_hp, (tx + m_hp_w + 12, m_hp_y - 1))

            # Baris 3: ATK, DEF, dan Profil AI
            line3 = f"ATK: +{m.atk_bonus}  │  DEF: +{m.def_bonus}  │  AI: {m.eval_profile}"
            self.screen.blit(font_sm.render(line3, True, (205, 218, 235)), (tx, m_hp_y + 18))

            # Baris 4: Deskripsi Karakteristik
            self.screen.blit(font_sm.render(trait_desc, True, (150, 172, 198)), (tx, m_hp_y + 36))

            m_y += member_card_h + gap

        # Bagian Bawah: 4 Tombol CTA Interaktif di Dasar Layar
        btn_w = 185
        btn_gap = 12
        total_w = 4 * btn_w + 3 * btn_gap
        start_x = area_cx - total_w // 2

        self.btn_pre_battle_inspect = pygame.Rect(start_x, btn_y, btn_w, btn_h)
        self.btn_pre_battle_start = pygame.Rect(start_x + (btn_w + btn_gap), btn_y, btn_w, btn_h)
        self.btn_pre_battle_reroll = pygame.Rect(start_x + 2 * (btn_w + btn_gap), btn_y, btn_w, btn_h)
        self.btn_pre_battle_cancel = pygame.Rect(start_x + 3 * (btn_w + btn_gap), btn_y, btn_w, btn_h)

        # 1. Tombol Buka Pohon CSP & Optimasi [T]
        pygame.draw.rect(self.screen, (26, 75, 120), self.btn_pre_battle_inspect, border_radius=6)
        pygame.draw.rect(self.screen, (60, 160, 235), self.btn_pre_battle_inspect, 1, border_radius=6)

        # 2. Tombol Mulai Duel [SPASI]
        pygame.draw.rect(self.screen, (36, 135, 75), self.btn_pre_battle_start, border_radius=6)
        pygame.draw.rect(self.screen, (45, 160, 90), self.btn_pre_battle_start, 1, border_radius=6)

        # 3. Tombol Acak Ulang [R]
        pygame.draw.rect(self.screen, (185, 95, 30), self.btn_pre_battle_reroll, border_radius=6)
        pygame.draw.rect(self.screen, (220, 125, 45), self.btn_pre_battle_reroll, 1, border_radius=6)

        # 4. Tombol Batal [ESC]
        pygame.draw.rect(self.screen, (45, 54, 70), self.btn_pre_battle_cancel, border_radius=6)
        pygame.draw.rect(self.screen, (70, 84, 108), self.btn_pre_battle_cancel, 1, border_radius=6)

        t_inspect = font_bubble.render("[T] 🌳 Pohon CSP & LS", True, (240, 250, 255))
        t_start = font_bubble.render("[SPASI] Mulai Duel", True, (255, 255, 255))
        t_reroll = font_bubble.render("[R] Acak Ulang", True, (255, 255, 255))
        t_cancel = font_bubble.render("[ESC] Kembali", True, (220, 228, 240))

        self.screen.blit(t_inspect, (self.btn_pre_battle_inspect.centerx - t_inspect.get_width() // 2, self.btn_pre_battle_inspect.centery - t_inspect.get_height() // 2))
        self.screen.blit(t_start, (self.btn_pre_battle_start.centerx - t_start.get_width() // 2, self.btn_pre_battle_start.centery - t_start.get_height() // 2))
        self.screen.blit(t_reroll, (self.btn_pre_battle_reroll.centerx - t_reroll.get_width() // 2, self.btn_pre_battle_reroll.centery - t_reroll.get_height() // 2))
        self.screen.blit(t_cancel, (self.btn_pre_battle_cancel.centerx - t_cancel.get_width() // 2, self.btn_pre_battle_cancel.centery - t_cancel.get_height() // 2))

        # Notifikasi visual saat Re-Roll berhasil dijalankan
        if self.reroll_toast_timer > 0:
            toast_text = "Skuad NPC berhasil diperbarui & dioptimasi."
            toast_surf = font_bubble.render(toast_text, True, (245, 235, 160))
            tw = toast_surf.get_width() + 28
            th = 28
            toast_rect = pygame.Rect(area_cx - tw // 2, btn_y - 34, tw, th)
            pygame.draw.rect(self.screen, (28, 36, 52), toast_rect, border_radius=6)
            pygame.draw.rect(self.screen, (75, 140, 225), toast_rect, 1, border_radius=6)
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

    def _draw_obtained_items_hud(self):
        """Menampilkan panel HUD item yang didapat di bagian bawah kiri layar map (mode searching)."""
        w, h = self.screen.get_size()
        panel_w = config.DEBUG_LEFT_PANEL_WIDTH
        hud_x = panel_w + 14
        hud_h = 78

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
        }

        slot_count = max(3, len(inventory))
        slot_w, slot_h = 44, 44
        slot_gap = 8
        pad_x, pad_y = 12, 8

        # Hitung kebutuhan lebar header
        title_text = "ITEM DIDAPAT"
        count_text = f"({len(inventory)}/3)" if len(inventory) <= 3 else f"({len(inventory)})"
        t_surf = font_bubble.render(title_text, True, (245, 210, 85))
        c_surf = font_sm.render(count_text, True, (170, 185, 205))

        bonuses = []
        if self.player.atk_bonus > 0:
            bonuses.append(f"ATK +{self.player.atk_bonus}")
        if self.player.def_bonus > 0:
            bonuses.append(f"DEF +{self.player.def_bonus}")
        b_surf = font_tiny.render(" • ".join(bonuses), True, (255, 185, 110)) if bonuses else None

        header_req_w = t_surf.get_width() + c_surf.get_width() + 16
        if b_surf:
            header_req_w += b_surf.get_width() + 20

        slots_total_w = slot_count * slot_w + (slot_count - 1) * slot_gap
        min_hud_w = 260
        hud_w = max(min_hud_w, slots_total_w + pad_x * 2, header_req_w + pad_x * 2)
        hud_y = h - hud_h - 14

        # 1. Background Container Card (Glassmorphic Dark Theme ~30% Transparan)
        card_surf = pygame.Surface((hud_w, hud_h), SRCALPHA)
        card_surf.fill((16, 20, 28, 165))
        pygame.draw.rect(card_surf, (55, 70, 95, 180), card_surf.get_rect(), 1, border_radius=10)
        pygame.draw.line(card_surf, (90, 120, 165, 110), (10, 1), (hud_w - 10, 1), 1)
        self.screen.blit(card_surf, (hud_x, hud_y))

        # 2. Header Bar
        self.screen.blit(t_surf, (hud_x + pad_x, hud_y + 6))
        self.screen.blit(c_surf, (hud_x + pad_x + t_surf.get_width() + 6, hud_y + 6))
        if b_surf:
            self.screen.blit(b_surf, (hud_x + hud_w - pad_x - b_surf.get_width(), hud_y + 8))

        # 3. Item Slots
        sy = hud_y + 26
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
                    "color": (240, 200, 80),
                })
                item_key = meta["key"]

                # Background slot terisi (transparan selaras)
                s_bg = pygame.Surface((slot_w, slot_h), SRCALPHA)
                s_bg.fill((24, 30, 44, 165))
                self.screen.blit(s_bg, (sx, sy))

                # Border bercahaya sesuai warna rarity item
                pygame.draw.rect(self.screen, meta["color"], slot_rect, 1, border_radius=6)

                # Icon Item
                if item_key in self.item_images:
                    icon = pygame.transform.smoothscale(self.item_images[item_key], (30, 30))
                    ix = sx + (slot_w - 30) // 2
                    iy = sy + (slot_h - 30) // 2
                    self.screen.blit(icon, (ix, iy))

                # Mini badge (misal x3 potion, +5 ATK)
                mini_label = meta.get("badge_mini", "")
                if mini_label:
                    m_surf = font_tiny.render(mini_label, True, (255, 255, 255))
                    m_pad = 3
                    mw = m_surf.get_width() + m_pad * 2
                    mh = m_surf.get_height() + 1
                    m_rect = pygame.Rect(slot_rect.right - mw - 2, slot_rect.bottom - mh - 2, mw, mh)
                    pygame.draw.rect(self.screen, (15, 20, 30, 190), m_rect, border_radius=3)
                    pygame.draw.rect(self.screen, meta["color"], m_rect, 1, border_radius=3)
                    self.screen.blit(m_surf, (m_rect.x + m_pad, m_rect.y))

                # Cek hover jika tidak sedang gacha modal
                if not self.gacha_active and not getattr(self, "gacha_showcase", None):
                    if slot_rect.collidepoint(mouse_pos):
                        hovered_meta = meta
                        hovered_rect = slot_rect
            else:
                # Slot Kosong
                s_bg = pygame.Surface((slot_w, slot_h), SRCALPHA)
                s_bg.fill((20, 24, 34, 110))
                self.screen.blit(s_bg, (sx, sy))
                pygame.draw.rect(self.screen, (52, 64, 84, 130), slot_rect, 1, border_radius=6)
                q_surf = font_sm.render("?", True, (75, 90, 115))
                self.screen.blit(q_surf, (slot_rect.centerx - q_surf.get_width() // 2, slot_rect.centery - q_surf.get_height() // 2))

        # Jika inventori masih kosong, tampilkan petunjuk
        if len(inventory) == 0:
            hint_surf = font_tiny.render("Buka Peti [E] di Map", True, (140, 155, 175))
            hint_x = hud_x + pad_x + slot_count * (slot_w + slot_gap) + 8
            if hint_x + hint_surf.get_width() <= hud_x + hud_w - pad_x:
                self.screen.blit(hint_surf, (hint_x, sy + (slot_h - hint_surf.get_height()) // 2))

        # 4. Tooltip saat mouse hover di atas slot
        if hovered_meta and hovered_rect:
            tt_title = font_bubble.render(hovered_meta["name"], True, hovered_meta["color"])
            tt_badge = font_tiny.render(f"• {hovered_meta['badge']}", True, (255, 230, 120))
            tt_desc = font_tiny.render(hovered_meta["desc"], True, (215, 225, 240))

            tt_w = max(tt_title.get_width() + tt_badge.get_width() + 30, tt_desc.get_width() + 20)
            tt_h = 44
            tt_x = max(hud_x, min(w - tt_w - 10, hovered_rect.centerx - tt_w // 2))
            tt_y = hud_y - tt_h - 8

            tt_surf = pygame.Surface((tt_w, tt_h), SRCALPHA)
            tt_surf.fill((14, 18, 26, 245))
            pygame.draw.rect(tt_surf, hovered_meta["color"], tt_surf.get_rect(), 1, border_radius=6)
            self.screen.blit(tt_surf, (tt_x, tt_y))

            self.screen.blit(tt_title, (tt_x + 8, tt_y + 5))
            self.screen.blit(tt_badge, (tt_x + 14 + tt_title.get_width(), tt_y + 6))
            self.screen.blit(tt_desc, (tt_x + 8, tt_y + 24))

    def _draw_gacha_popup(self):
        w, h = self.screen.get_size()
        panel_w = config.DEBUG_LEFT_PANEL_WIDTH
        arena_w = w - panel_w
        cx = panel_w + arena_w // 2
        cy = h // 2

        if self.gacha_active:
            # 1. Animasi Pembukaan Peti (Roulette Putar Item) - Background 50% Transparan
            pop_w, pop_h = 360, 200
            pop_rect = pygame.Rect(cx - pop_w // 2, cy - pop_h // 2, pop_w, pop_h)
            card = pygame.Surface((pop_w, pop_h), SRCALPHA)
            card.fill((16, 20, 32, 128))  # 50% transparan
            pygame.draw.rect(card, (255, 205, 60, 220), card.get_rect(), 2, border_radius=12)
            pygame.draw.rect(card, (255, 255, 255, 30), (2, 2, pop_w - 4, pop_h - 4), 1, border_radius=10)
            self.screen.blit(card, pop_rect)

            title = self.fonts.get("title", self.fonts["sm"]).render("MEMBUKA PETI HARTA", True, (255, 225, 80))
            self.screen.blit(title, (cx - title.get_width() // 2, pop_rect.y + 16))

            # Pedestal aura glow untuk preview item roulette
            ped_rect = pygame.Rect(cx - 36, cy - 30, 72, 72)
            pygame.draw.circle(self.screen, (28, 36, 55, 140), ped_rect.center, 36)
            pygame.draw.circle(self.screen, (255, 205, 60), ped_rect.center, 36, width=2)

            cur_item = self.gacha_current_item
            if cur_item and cur_item in self.item_images_large:
                raw_img = self.item_images_large[cur_item]
                img = pygame.transform.smoothscale(raw_img, (60, 60))
                self.screen.blit(img, img.get_rect(center=ped_rect.center))
            elif cur_item and cur_item in self.item_images:
                img = self.item_images[cur_item]
                self.screen.blit(img, img.get_rect(center=ped_rect.center))

            sub = self.fonts.get("bubble", self.fonts["sm"]).render("Memutar takdir keberuntungan...", True, (200, 220, 245))
            self.screen.blit(sub, (cx - sub.get_width() // 2, pop_rect.bottom - 28))

        elif getattr(self, "gacha_showcase", None):
            # 2. Modal Item Showcase di Tengah Layar (Center Screen Reveal) - Background 50% Transparan
            showcase = self.gacha_showcase
            item_key = showcase["item_key"]
            item_name = showcase["name"]
            item_badge = showcase["badge"]
            item_desc = showcase["desc"]
            item_col = showcase.get("color", (255, 215, 65))
            anim_t = showcase.get("anim_time", 0.0)

            # A. Backdrop halus transparan pada arena eksplorasi (hanya di viewport permainan)
            dim_surf = pygame.Surface((arena_w, h), SRCALPHA)
            dim_surf.fill((6, 8, 14, 110))
            self.screen.blit(dim_surf, (panel_w, 0))

            # B. Card modal container di tengah layar (50% transparan)
            mw, mh = 480, 350
            modal_rect = pygame.Rect(cx - mw // 2, cy - mh // 2, mw, mh)
            card = pygame.Surface((mw, mh), SRCALPHA)
            card.fill((14, 18, 28, 128))  # 50% transparan

            # Border elegan ganda dengan warna tema item
            pygame.draw.rect(card, (*item_col[:3], 230), (0, 0, mw, mh), 2, border_radius=14)
            pygame.draw.rect(card, (255, 255, 255, 40), (2, 2, mw - 4, mh - 4), 1, border_radius=12)

            font_huge = self.fonts.get("huge", self.fonts["title"])
            font_title = self.fonts.get("title", self.fonts["sm"])
            font_bubble = self.fonts.get("bubble", self.fonts["sm"])
            font_sm = self.fonts["sm"]

            # Header Top Pill: PETI HARTA BERHASIL DIBUKA!
            top_badge_w, top_badge_h = 340, 30
            top_badge_rect = pygame.Rect((mw - top_badge_w) // 2, 14, top_badge_w, top_badge_h)
            badge_bg = pygame.Surface((top_badge_w, top_badge_h), SRCALPHA)
            badge_bg.fill((55, 42, 16, 170))
            pygame.draw.rect(badge_bg, (255, 215, 70), (0, 0, top_badge_w, top_badge_h), 1, border_radius=6)
            card.blit(badge_bg, top_badge_rect)
            hdr_lbl = font_bubble.render("PETI HARTA BERHASIL DIBUKA!", True, (255, 225, 80))
            card.blit(hdr_lbl, hdr_lbl.get_rect(center=top_badge_rect.center))

            # Pedestal showcase lingkaran di tengah dengan radial aura berdenyut
            ped_cx = mw // 2
            ped_cy = 118
            ped_radius = 56

            pulse = 0.5 + 0.5 * math.sin(anim_t * 4.0)
            glow_surf = pygame.Surface((ped_radius * 2 + 32, ped_radius * 2 + 32), SRCALPHA)
            glow_col = (*item_col[:3], int(65 + pulse * 65))
            pygame.draw.circle(glow_surf, glow_col, (glow_surf.get_width() // 2, glow_surf.get_height() // 2), int(ped_radius + pulse * 6))
            card.blit(glow_surf, glow_surf.get_rect(center=(ped_cx, ped_cy)))

            ped_surf = pygame.Surface((ped_radius * 2, ped_radius * 2), SRCALPHA)
            pygame.draw.circle(ped_surf, (24, 30, 46, 170), (ped_radius, ped_radius), ped_radius)
            pygame.draw.circle(ped_surf, (*item_col[:3], 230), (ped_radius, ped_radius), ped_radius, width=2)
            pygame.draw.circle(ped_surf, (255, 255, 255, 60), (ped_radius, ped_radius), ped_radius - 3, width=1)
            card.blit(ped_surf, ped_surf.get_rect(center=(ped_cx, ped_cy)))

            # Render GAMBAR ITEM BESAR (84x84 px)
            item_img = None
            if item_key in self.item_images_large:
                item_img = self.item_images_large[item_key]
            elif item_key in self.item_images:
                item_img = self.item_images[item_key]

            if item_img:
                scale_pulse = 1.0 + 0.04 * math.sin(anim_t * 4.0)
                target_sz = int(84 * scale_pulse)
                rendered_img = pygame.transform.smoothscale(item_img, (target_sz, target_sz))
                card.blit(rendered_img, rendered_img.get_rect(center=(ped_cx, ped_cy)))

            # Nama Item yang diperoleh
            name_lbl = font_huge.render(item_name, True, (255, 245, 180))
            card.blit(name_lbl, name_lbl.get_rect(center=(mw // 2, 194)))

            # Pill Badge Efek / Stat Bonus
            stat_w, stat_h = 380, 30
            stat_rect = pygame.Rect((mw - stat_w) // 2, 220, stat_w, stat_h)
            stat_bg = pygame.Surface((stat_w, stat_h), SRCALPHA)
            stat_bg.fill((18, 38, 30, 180))
            pygame.draw.rect(stat_bg, (45, 205, 120), (0, 0, stat_w, stat_h), 1, border_radius=6)
            card.blit(stat_bg, stat_rect)
            stat_lbl = font_bubble.render(f"BONUS: {item_badge}", True, (95, 255, 175))
            card.blit(stat_lbl, stat_lbl.get_rect(center=stat_rect.center))

            # Deskripsi Efek Item (Automatic Word-Wrap)
            words = item_desc.split(" ")
            lines = []
            cur_line = []
            max_desc_w = mw - 40
            for w_str in words:
                test_str = " ".join(cur_line + [w_str])
                if font_sm.size(test_str)[0] <= max_desc_w:
                    cur_line.append(w_str)
                else:
                    if cur_line:
                        lines.append(" ".join(cur_line))
                    cur_line = [w_str]
            if cur_line:
                lines.append(" ".join(cur_line))

            desc_y = 257 if len(lines) > 1 else 264
            for l_idx, line_str in enumerate(lines[:2]):
                desc_lbl = font_sm.render(line_str, True, (215, 225, 245))
                card.blit(desc_lbl, desc_lbl.get_rect(center=(mw // 2, desc_y + l_idx * 16)))

            # Tombol Interaktif / Petunjuk Tekan Tombol di Bawah
            btn_w, btn_h = 420, 34
            btn_rect = pygame.Rect((mw - btn_w) // 2, mh - 46, btn_w, btn_h)
            btn_bg = pygame.Surface((btn_w, btn_h), SRCALPHA)
            btn_bg.fill((28, 125, 60, 190))
            pygame.draw.rect(btn_bg, (100, 235, 140), (0, 0, btn_w, btn_h), 1, border_radius=7)
            card.blit(btn_bg, btn_rect)

            prompt_str = "Tekan [ENTER] / [SPASI] / [E] atau Klik untuk Menutup"
            p_txt = font_bubble.render(prompt_str, True, (255, 255, 255))
            card.blit(p_txt, p_txt.get_rect(center=btn_rect.center))

            self.screen.blit(card, modal_rect)

        elif self.gacha_message_timer > 0:
            alpha = min(255, int(255 * (self.gacha_message_timer / 0.5))) if self.gacha_message_timer < 0.5 else 255
            txt = self.fonts.get("bubble", self.fonts["sm"]).render(self.gacha_message, True, (255, 255, 255))
            toast_rect = pygame.Rect(cx - txt.get_width() // 2 - 16, cy + 120, txt.get_width() + 32, txt.get_height() + 14)
            card = pygame.Surface((toast_rect.width, toast_rect.height), SRCALPHA)
            card.fill((20, 28, 45, int(128 * (alpha / 255.0))))
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
        self.gacha_active = True
        self.gacha_timer = 1.0
        self.gacha_reward_item = chest.get("item", "health_potion")
        self.gacha_showcase = None

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
            "timer": 4.5,
            "max_timer": 4.5,
            "anim_time": 0.0,
        }
        self.gacha_message = f"Mendapatkan {meta['name']}!"
        self.gacha_message_timer = 0.0

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

    def _draw_loot_toast(self, w: int, h: int, center_x: int):
        """Merender banner pop-up Rampasan Perang (Spoils of War) di atas duel arena."""
        if not self.loot_toast or self.loot_toast["timer"] <= 0:
            return

        toast = self.loot_toast
        loot = toast["loot"]
        timer = toast["timer"]
        max_timer = toast["max_timer"]

        # Efek Fade in / Fade out
        if timer > max_timer - 0.25:
            alpha = int(255 * (max_timer - timer) / 0.25)
        elif timer < 0.4:
            alpha = int(255 * (timer / 0.4))
        else:
            alpha = 255
        alpha = max(0, min(255, alpha))

        bw, bh = 480, 56
        by = 28
        banner_rect = pygame.Rect(center_x - bw // 2, by, bw, bh)

        banner_surf = pygame.Surface((bw, bh), SRCALPHA)
        bg_alpha = int(235 * (alpha / 255.0))
        banner_surf.fill((16, 18, 26, bg_alpha))

        border_col = loot.get("color", (255, 215, 60))
        border_col_alpha = (*border_col[:3], alpha)
        pygame.draw.rect(banner_surf, border_col_alpha, pygame.Rect(0, 0, bw, bh), width=2, border_radius=8)

        glow_bar = pygame.Rect(4, 4, 6, bh - 8)
        pygame.draw.rect(banner_surf, border_col_alpha, glow_bar, border_radius=3)

        font_bubble = self.fonts.get("bubble", self.fonts["sm"])
        font_sm = self.fonts["sm"]

        title_str = "⚔️ RAMPASAN PERANG DIPEROLEH!"
        title_txt = font_bubble.render(title_str, True, (255, 220, 80))
        if alpha < 255:
            title_txt.set_alpha(alpha)
        banner_surf.blit(title_txt, (20, 6))

        desc_str = f"Merebut: {loot['name']} ({loot['desc']})"
        desc_txt = font_sm.render(desc_str, True, (235, 245, 255))
        if alpha < 255:
            desc_txt.set_alpha(alpha)
        banner_surf.blit(desc_txt, (20, 31))

        self.screen.blit(banner_surf, banner_rect)

    def _draw_defeat_badge(self, cx: int, cy: int, npc_obj):
        """Merender badge dramatis 'KALAH!' tepat di atas NPC yang baru saja tumbang."""
        font_huge = self.fonts.get("huge", self.fonts["title"])
        font_bubble = self.fonts.get("bubble", self.fonts["sm"])

        bw, bh = 290, 68
        b_rect = pygame.Rect(cx - bw // 2, cy - bh // 2, bw, bh)

        badge_surf = pygame.Surface((bw, bh), SRCALPHA)
        badge_surf.fill((36, 10, 14, 245))
        border_col = (255, 55, 45)
        pygame.draw.rect(badge_surf, border_col, (0, 0, bw, bh), width=2, border_radius=10)
        pygame.draw.rect(badge_surf, (255, 210, 75), (2, 2, bw - 4, bh - 4), width=1, border_radius=8)

        t_main = font_huge.render("KALAH / TUMBANG!", True, (255, 230, 80))
        badge_surf.blit(t_main, t_main.get_rect(center=(bw // 2, 24)))

        name_str = npc_obj.name if hasattr(npc_obj, "name") else "Musuh"
        t_sub = font_bubble.render(f"{name_str} Telah Gugur!", True, (255, 220, 220))
        badge_surf.blit(t_sub, t_sub.get_rect(center=(bw // 2, 50)))

        self.screen.blit(badge_surf, b_rect)

    def _draw_loot_modal(self):
        """Merender modal dialog rampasan perang di tengah layar dengan latar belakang gelap pekat."""
        if not self.loot_modal:
            return

        modal = self.loot_modal
        loot = modal["loot"]
        old_npc = modal.get("old_npc")
        is_final = modal.get("is_final", False)

        w, h = self.screen.get_size()
        panel_w = config.DEBUG_LEFT_PANEL_WIDTH
        arena_w = w - panel_w
        cx = panel_w + arena_w // 2
        cy = h // 2

        # 1. Background Overlay Gelap (Dimmed Backdrop seluruh layar)
        dim_surf = pygame.Surface((w, h), SRCALPHA)
        dim_surf.fill((4, 6, 12, 225))
        self.screen.blit(dim_surf, (0, 0))

        # 2. Dimensi & Posisi Modal Card di Tengah Layar
        mw, mh = 530, 390
        modal_rect = pygame.Rect(cx - mw // 2, cy - mh // 2, mw, mh)

        card_surf = pygame.Surface((mw, mh), SRCALPHA)
        card_surf.fill((16, 20, 30, 252))

        theme_col = loot.get("color", (255, 215, 60))
        pygame.draw.rect(card_surf, theme_col, (0, 0, mw, mh), 2, border_radius=14)
        pygame.draw.rect(card_surf, (255, 255, 255, 30), (2, 2, mw - 4, mh - 4), 1, border_radius=12)

        font_huge = self.fonts.get("huge", self.fonts["title"])
        font_bubble = self.fonts.get("bubble", self.fonts["sm"])
        font_sm = self.fonts["sm"]

        # 3. Header Badge: RAMPASAN PERANG DIPEROLEH!
        badge_w, badge_h = 370, 32
        badge_rect = pygame.Rect((mw - badge_w) // 2, 16, badge_w, badge_h)
        pygame.draw.rect(card_surf, (55, 42, 16), badge_rect, border_radius=6)
        pygame.draw.rect(card_surf, (255, 215, 70), badge_rect, 1, border_radius=6)

        hdr_txt = font_bubble.render("⚔️ RAMPASAN PERANG DIPEROLEH! ⚔️", True, (255, 225, 80))
        card_surf.blit(hdr_txt, hdr_txt.get_rect(center=badge_rect.center))

        # 4. Sub-teks Info Lawan Gugur
        if old_npc:
            sub_str = f"Bolu berhasil menumbangkan {old_npc.name}!"
        else:
            sub_str = "Kemenangan gemilang di medan pertempuran!"
        sub_txt = font_sm.render(sub_str, True, (190, 205, 230))
        card_surf.blit(sub_txt, sub_txt.get_rect(center=(mw // 2, 60)))

        # 5. Bingkai Showcase Item (Icon Frame di Tengah)
        frame_sz = 108
        frame_rect = pygame.Rect((mw - frame_sz) // 2, 82, frame_sz, frame_sz)
        pygame.draw.rect(card_surf, (26, 32, 48), frame_rect, border_radius=12)
        pygame.draw.rect(card_surf, theme_col, frame_rect, 2, border_radius=12)

        # Efek glowing aura di belakang item
        aura = pygame.Surface((frame_sz - 8, frame_sz - 8), SRCALPHA)
        aura.fill((*theme_col[:3], 35))
        card_surf.blit(aura, (frame_rect.x + 4, frame_rect.y + 4))

        # Gambar Item Besar (96x96 px)
        img_key = loot.get("image_key", "item_sword")
        item_img = None
        if hasattr(self, "item_images_large") and img_key in self.item_images_large:
            item_img = self.item_images_large[img_key]
        elif img_key in self.item_images:
            item_img = pygame.transform.smoothscale(self.item_images[img_key], (96, 96))

        if item_img:
            card_surf.blit(item_img, item_img.get_rect(center=frame_rect.center))

        # 6. Nama Item Rampasan
        item_name = loot.get("name", "Artefak Misterius")
        name_txt = font_huge.render(item_name, True, (255, 240, 140))
        card_surf.blit(name_txt, name_txt.get_rect(center=(mw // 2, 212)))

        # 7. Badge Stat Boost (+ATK / +DEF / Pulihkan HP)
        stat_w, stat_h = 390, 32
        stat_rect = pygame.Rect((mw - stat_w) // 2, 238, stat_w, stat_h)
        pygame.draw.rect(card_surf, (16, 36, 28), stat_rect, border_radius=6)
        pygame.draw.rect(card_surf, (45, 200, 115), stat_rect, 1, border_radius=6)

        stat_str = f"⚡ BONUS: {loot.get('stat_text', '+Stat')}"
        stat_txt = font_bubble.render(stat_str, True, (95, 255, 175))
        card_surf.blit(stat_txt, stat_txt.get_rect(center=stat_rect.center))

        # 8. Deskripsi Efek Item
        desc_str = loot.get("desc", "")
        desc_txt = font_sm.render(desc_str, True, (215, 225, 245))
        card_surf.blit(desc_txt, desc_txt.get_rect(center=(mw // 2, 288)))

        # 9. Tombol Interaktif / Petunjuk Tekan ENTER
        btn_w, btn_h = 430, 38
        btn_rect = pygame.Rect((mw - btn_w) // 2, mh - 54, btn_w, btn_h)

        btn_bg = (32, 135, 68) if not is_final else (45, 110, 195)
        btn_bdr = (110, 245, 150) if not is_final else (120, 190, 255)
        pygame.draw.rect(card_surf, btn_bg, btn_rect, border_radius=8)
        pygame.draw.rect(card_surf, btn_bdr, btn_rect, 1, border_radius=8)

        prompt_str = "▶ Tekan [ENTER] / [SPASI] untuk Hadapi Lawan Berikutnya" if not is_final else "▶ Tekan [ENTER] / [SPASI] untuk Menyelesaikan Duel"
        p_txt = font_bubble.render(prompt_str, True, (255, 255, 255))
        card_surf.blit(p_txt, p_txt.get_rect(center=btn_rect.center))

        # Blit Modal Card ke Layar
        self.screen.blit(card_surf, modal_rect)