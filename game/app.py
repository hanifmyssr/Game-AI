"""App: main loop + kamera + rendering, port dari Scenes/main.tscn + Duel Turn-Based Minimax (Tahap-2).
"""

import math
import os
from typing import Optional, Dict, Any, List, Tuple
import pygame

from .core import config
from .core.events import GameManager
from .core.audio import AudioManager
from .world.mapdata import MapData
from .ui.overlay import DebugOverlay
from .ui.components import draw_card
from .world.player import Player
from .world.npc import NPC
from .battle.battle_system import BattleSystem
from .ai.battle_ai import ACTION_ATTACK, ACTION_HEAVY, ACTION_DEFEND, ACTION_POTION
from .ai.npc_config_csp import NPCConfigCSP
from .ai.npc_config_optimizer import NPCOptimizer
from .ai.uncertainty import BayesianRelicSonar
from .battle.npc_squad import NPCSquad, NPCMember
from .battle.battle_vfx import BattleVFXManager
from .battle.battle_background import BattleArenaBackground
from .ui.pre_battle_visualizer import PreBattleVisualizerModal
from .logic.inter_npc_manager import InterNPCManager
from .planning.planner_engine import ForwardProgressionPlanner, BackwardRegressionPlanner, build_planning_graph_nodes
from .planning.domain_world_patrol import create_world_patrol_problem
from .planning.domain_battle_tactics import create_battle_tactics_problem
from .planning.task_executor import TaskExecutor
from .ui.logic_overlay import LogicOverlay
from .ui.planning_overlay import PlanningOverlay
from .ui.guide_modal import GuideModal
from .modes import ExplorationModeMixin, PreBattleModeMixin, BattleModeMixin

MOUSEWHEEL = getattr(pygame, "MOUSEWHEEL", 1027)
K_F11 = getattr(pygame, "K_F11", 292)
K_h = getattr(pygame, "K_h", 104)
K_k = getattr(pygame, "K_k", 107)
K_p = getattr(pygame, "K_p", 112)
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
K_f = getattr(pygame, "K_f", 102)
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
    """Kamera yang mengikuti player dengan zoom yang dapat diubah dan peredam halus (smooth lerp)."""

    def __init__(self, win_w, win_h, map_w, map_h, margin=0.02, app_ref=None):
        self._app_ref = app_ref
        self._left_panel_w = config.TOTAL_DOCK_WIDTH
        self.zoom = 3.0
        self.fit_zoom = 1.0
        self.map_w = map_w
        self.map_h = map_h
        self.win_w = win_w
        self.win_h = win_h
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.reset(win_w, win_h, map_w, map_h, margin)

    @property
    def left_panel_w(self):
        if self._app_ref and hasattr(self._app_ref, "overlay") and self._app_ref.overlay:
            if hasattr(self._app_ref.overlay, "dock") and self._app_ref.overlay.dock.is_open:
                return self._app_ref.overlay.dock.rect.right
            return config.NAV_RAIL_WIDTH
        return self._left_panel_w or config.TOTAL_DOCK_WIDTH

    @left_panel_w.setter
    def left_panel_w(self, val):
        self._left_panel_w = val

    def reset(self, win_w, win_h, map_w, map_h, margin=0.02, left_panel_w=None):
        self.win_w = win_w
        self.win_h = win_h
        self.map_w = map_w
        self.map_h = map_h
        if left_panel_w is not None:
            self._left_panel_w = left_panel_w

        # Hitung usable width saat panel dock terbuka (lebar minimal area permainan)
        dock_w = config.TOTAL_DOCK_WIDTH
        usable_w_dock = max(100.0, win_w - dock_w)
        self.fit_zoom = min(usable_w_dock / map_w, win_h / map_h) * (1.0 - margin)

        # Hitung zoom kamera standar petualang (2.8x sesuai plan_ui.md)
        # Menampilkan pemandangan padang rumput & sungai yang nyaman dan proporsional
        min_overflow_zoom_x = (usable_w_dock + 64.0) / map_w
        min_overflow_zoom_y = (win_h + 64.0) / map_h
        self.min_overflow_zoom = max(min_overflow_zoom_x, min_overflow_zoom_y)

        # Default zoom: 2.8x (pada 1280x800) dan menyesuaikan proporsional pada resolusi tinggi/fullscreen
        self.base_zoom = max(2.8, self.min_overflow_zoom)
        self.zoom = self.base_zoom
        self._center_map()

    def _center_map(self):
        usable_w = max(100.0, self.win_w - self.left_panel_w)
        scaled_w = self.map_w * self.zoom
        scaled_h = self.map_h * self.zoom
        if scaled_w <= usable_w:
            self.offset_x = self.left_panel_w + (usable_w - scaled_w) / 2.0
        else:
            self.offset_x = self.left_panel_w
        if scaled_h <= self.win_h:
            self.offset_y = (self.win_h - scaled_h) / 2.0
        else:
            self.offset_y = 0.0

    def zoom_by(self, factor, focus_screen=None):
        old_zoom = self.zoom
        min_zoom = max(self.base_zoom * 0.75, self.min_overflow_zoom)
        max_zoom = self.base_zoom * 2.5
        usable_w = max(100.0, self.win_w - self.left_panel_w)
        if focus_screen is None:
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
            min_offset_x = self.win_w - scaled_w
            max_offset_x = self.left_panel_w
            self.offset_x = max(min_offset_x, min(self.offset_x, max_offset_x))

        if scaled_h <= self.win_h:
            self.offset_y = (self.win_h - scaled_h) / 2.0
        else:
            min_offset_y = self.win_h - scaled_h
            self.offset_y = max(min_offset_y, min(self.offset_y, 0.0))

    def follow(self, world_pos, smooth=False, dt=0.016):
        usable_w = max(100.0, self.win_w - self.left_panel_w)
        viewport_center_x = self.left_panel_w + usable_w / 2.0
        viewport_center_y = self.win_h / 2.0
        target_x = viewport_center_x - world_pos[0] * self.zoom
        target_y = viewport_center_y - world_pos[1] * self.zoom
        if smooth:
            factor = min(1.0, 10.0 * dt)
            self.offset_x += (target_x - self.offset_x) * factor
            self.offset_y += (target_y - self.offset_y) * factor
        else:
            self.offset_x = target_x
            self.offset_y = target_y
        self._clamp_offset()

    def world_to_screen(self, wx, wy):
        return (wx * self.zoom + self.offset_x, wy * self.zoom + self.offset_y)


class App(ExplorationModeMixin, PreBattleModeMixin, BattleModeMixin):
    """Orkestrator utama aplikasi Bakekok (loop, event, kamera, dan koordinasi mode)."""

    def __init__(self):
        getattr(pygame, "init")()
        self.screen = pygame.display.set_mode(
            (config.WINDOW_WIDTH, config.WINDOW_HEIGHT), RESIZABLE
        )
        pygame.display.set_caption("Bakekok - AI Pathfinding & Minimax Duel")
        self.clock = pygame.time.Clock()
        self.running = True

        self.fonts = self._build_fonts()

        self.map = MapData()
        self.events = GameManager()

        # Sistem Pertarungan Turn-Based (Minimax AI)
        self.battle_system = BattleSystem()
        self.vfx = BattleVFXManager(self.fonts)
        self.battle_bg = BattleArenaBackground()
        self.battle_system.on_action_callback = self._on_battle_action_executed
        self.battle_system.on_tag_in = self._on_npc_tag_in
        self.battle_system.on_tactical_plan = self._on_npc_tactical_plan
        self.card_summon_anim = None
        self.game_mode = "EXPLORATION"  # "EXPLORATION", "PRE_BATTLE", atau "BATTLE"
        self.battle_reentry_locked = False
        self.battle_reentry_timer = 0.0

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
        self.btn_action_attack = pygame.Rect(0, 0, 0, 0)
        self.btn_action_heavy = pygame.Rect(0, 0, 0, 0)
        self.btn_action_defend = pygame.Rect(0, 0, 0, 0)
        self.btn_action_potion = pygame.Rect(0, 0, 0, 0)
        self.btn_battle_exit = pygame.Rect(0, 0, 0, 0)
        self.reroll_toast_timer = 0.0
        self.pre_battle_anim = None
        self._pre_battle_scale_cache = {}
        self.pre_battle_visualizer = PreBattleVisualizerModal()
        self.overlay.on_open_ai_inspector = self.pre_battle_visualizer.toggle

        self.player = Player(self.map, self.events)

        # 3 NPC di Peta (Masing-masing berpatroli aktif di zona strategis):
        # NPC 1: Oyen (Warrior) - Patroli Sektor Kiri Bawah (sekitar Chest B di 5, 24)
        self.npc = NPC(
            self.map,
            self.events,
            self.player,
            name="Oyen",
            is_patrol=True,
            waypoints=[(5, 23), (8, 23), (8, 25), (4, 25)],
            sprite_dir=config.OYEN_DIR,
        )
        # NPC 2: Kuro (Ranger - Serigala / Kucing Hitam) - Patroli Sektor Kanan (Area Peti Timur, dekat Chest C di 34, 28)
        self.npc_kuro = NPC(
            self.map,
            self.events,
            self.player,
            name="Kuro",
            tint_color=(45, 45, 55),
            is_patrol=True,
            waypoints=[(33, 27), (36, 27), (36, 29), (33, 29)],
            sprite_dir=config.KURO_DIR,
        )
        # NPC 3: Shiro (Mage) - Patroli Sektor Utara / Tebing (sekitar Chest A di 9, 3)
        self.npc_shiro = NPC(
            self.map,
            self.events,
            self.player,
            name="Shiro",
            tint_color=(195, 205, 220),
            is_patrol=True,
            waypoints=[(8, 2), (11, 2), (11, 5), (8, 5)],
            sprite_dir=config.SHIRO_DIR,
        )

        self.events.subscribe_player_moved(self.npc.on_player_moved)
        self.events.subscribe_player_moved(self.npc_kuro.on_player_moved)
        self.events.subscribe_player_moved(self.npc_shiro.on_player_moved)
        self.events.subscribe_player_moved(self._on_player_moved_sound)
        self.events.subscribe_algorithm_changed(self.npc.set_algorithm)
        self.events.subscribe_algorithm_changed(self.npc_kuro.set_algorithm)
        self.events.subscribe_algorithm_changed(self.npc_shiro.set_algorithm)

        # Fokus NPC untuk visualisasi pathfinding & metrik Tab Search (Opsi B: Auto + Pilih Manual)
        self.search_focus_mode = "AUTO"
        self._last_focused_npc_id = None
        self.events.get_focused_npc = self.get_focused_search_npc
        self.refresh_search_focus(force=True)

        # Audio Manager & BGM (Musik Latar)
        self.audio = AudioManager()
        self.audio.play_bgm(volume=0.22)
        self.was_near_chest = False

        # Peti Harta Interaktif & Tas Inventory (Tahap 3 & 4)
        map_chests = getattr(self.map, "chests_data", [])
        if map_chests:
            self.chests = [
                {"pos": (c["x"], c["y"]), "opened": False, "item": c.get("item", "health_potion")}
                for c in map_chests
            ]
        else:
            self.chests = [
                {"pos": (27, 2), "opened": False, "item": "health_potion"},
                {"pos": (11, 3), "opened": False, "item": "item_sword"},
                {"pos": (41, 24), "opened": False, "item": "item_shield"},
                {"pos": (10, 28), "opened": False, "item": "health_potion"},
            ]
        self._init_chickens()
        self.item_images = self._load_item_images()
        self.item_images_large = self._load_item_images_large()
        self.battle_sprites = self._load_battle_sprites()

        # State Animasi Gacha / Loot Peti
        self.active_gacha_chest = None
        self.gacha_active = False
        self.gacha_timer = 0.0
        self.gacha_current_item = None
        self.gacha_reward_item = None
        self.gacha_message = ""
        self.gacha_message_timer = 0.0
        self.gacha_showcase = None
        self.loot_toast = None
        self.loot_modal = None
        self.battle_result_modal = None
        self.btn_result_restart = pygame.Rect(0, 0, 0, 0)
        self.btn_result_exit = pygame.Rect(0, 0, 0, 0)
        self.npc_defeat_anim = None
        self.final_loot_shown = False

        self.map_surface = None
        self.scaled_map = None
        self.scaled_maps = []
        self.map_w, self.map_h = self.map.map_px_size()

        # State Animasi Lingkungan Hidup (Living World)
        self.wind_timer = 0.0
        self.chicken_timer = 0.0
        self.water_anim_timer = 0.0
        self.water_frame = 0
        self.sparkles = []
        self.sparkle_spawn_timer = 0.0

        # Foliage & Partikel Debu Langkah Kaki
        self.foliage_tree_canopy = None
        self.foliage_bush = None
        self.foliage_flower = None
        self.dust_frames = []
        self.dust_particles = []
        self._last_player_moving = False
        self._step_dust_timer = 0.0
        self._scaled_foliage = {}
        self._load_visual_effects()

        # Timer jeda aksi NPC dalam battle agar animasi/pembacaan terasa wajar
        self.npc_battle_turn_timer = 0.0
        self._last_camera_target = (self.player.px, self.player.py)

        self._apply_viewport()
        self.npc.find_path(self.player.grid)
        self.overlay.set_app(self)
        w, h = self.screen.get_size()
        self._on_window_resized(w, h)

        # Modul Materi 07: Logic & Knowledge Representation
        self.inter_npc_manager = InterNPCManager(self)
        self.logic_overlay = LogicOverlay(self.fonts, self)

        # Modul Materi 08: Automated Classical Planning (PDDL)
        self.forward_planner = ForwardProgressionPlanner()
        self.backward_planner = BackwardRegressionPlanner()
        self.task_executor = TaskExecutor(self)
        self.latest_plan_result = None
        self.planning_overlay = PlanningOverlay(self.fonts, self)

        # Modal Panduan Awal & Buku Panduan 3-Tab [H]
        self.guide_modal = GuideModal(self.fonts, audio=self.audio)
        self.btn_guide_pill = pygame.Rect(0, 0, 0, 0)
        if hasattr(self.overlay, "nav_rail"):
            self.overlay.nav_rail.on_guide_clicked = self.guide_modal.toggle

        # State Fitur Tahap 4 / Plan Dev: Stealth, Whistle & Boss Portal Menara Kuno
        self.whistle_waves = []
        self.sonar_waves = []
        self.relic_sonar = None
        self.inspected_tile = None
        self.ai_ticker_info = None
        self.is_boss_battle = False
        self._tower_prompted = False
        self._init_relic_sonar()

        # Rencana awal problem patroli dunia
        s0_init, goal_init, actions_init = create_world_patrol_problem("A")
        self.latest_plan_result = self.forward_planner.plan(s0_init, goal_init, actions_init)
        self.task_executor.set_plan(self.latest_plan_result)

        self.is_fullscreen = False
        init_w, init_h = self.screen.get_size()
        self._on_window_resized(init_w, init_h)

    def reset_game_state(self):
        """Mereset total status permainan: posisi Player, HP, Ramuan, Buff ATK/DEF, Inventori, dan seluruh Peti Harta."""
        # 1. Reset Peti Harta
        map_chests = getattr(self.map, "chests_data", [])
        if map_chests:
            self.chests = [
                {"pos": (c["x"], c["y"]), "opened": False, "item": c.get("item", "health_potion")}
                for c in map_chests
            ]
        else:
            self.chests = [
                {"pos": (27, 2), "opened": False, "item": "health_potion"},
                {"pos": (11, 3), "opened": False, "item": "item_sword"},
                {"pos": (41, 24), "opened": False, "item": "item_shield"},
                {"pos": (10, 28), "opened": False, "item": "health_potion"},
            ]
        self.active_gacha_chest = None
        self.gacha_active = False
        self.gacha_showcase = None
        self.gacha_message_timer = 0.0
        self.manual_target_difficulty = None

        # 2. Reset Player (Bolu)
        if hasattr(self, "player") and self.player:
            self.player.persistent_hp = config.MAX_HP
            self.player.persistent_potions = 3
            self.player.atk_bonus = 0
            self.player.def_bonus = 0
            if hasattr(self.player, "inventory"):
                self.player.inventory.clear()
            if hasattr(self.player, "rune_keys"):
                self.player.rune_keys.clear()
            self.player.is_hidden = False
            preferred_spawn = self.map.get_map_center()
            self.player.grid = self.map.get_valid_spawn_point(preferred_spawn)
            self.player.px, self.player.py = self.map.world_to_px(self.player.grid)
            self.player.frame_from = (self.player.px, self.player.py)
            self.player.frame_to = (self.player.px, self.player.py)
            self.player.moving = False
            self.events.emit_player_moved(self.player.grid)

        # 3. Reset NPC & Pengejar
        for n in (getattr(self, "npc", None), getattr(self, "npc_kuro", None), getattr(self, "npc_shiro", None)):
            if n:
                n.chasing = False
                n.path = []
                n.moving = False
                n._spawn()
        if hasattr(self, "overlay"):
            self.overlay.set_chasing_visualization(False)

        # 4. Kamera fokus ulang ke Player
        if hasattr(self, "camera") and self.camera:
            self.camera.follow((self.player.px, self.player.py))

        # 5. Reset Logic KB & Classical Planning
        if hasattr(self, "inter_npc_manager") and self.inter_npc_manager:
            self.inter_npc_manager.reset()
        if hasattr(self, "forward_planner") and self.forward_planner:
            s0_r, goal_r, actions_r = create_world_patrol_problem("A")
            self.latest_plan_result = self.forward_planner.plan(s0_r, goal_r, actions_r)
            if hasattr(self, "task_executor") and self.task_executor:
                self.task_executor.set_plan(self.latest_plan_result)

        # 6. Reset State Stealth, Whistle, Boss Portal & Sonar Materi 09
        self.whistle_waves.clear()
        self.sonar_waves.clear()
        self.inspected_tile = None
        self._init_relic_sonar()
        self.ai_ticker_info = None
        self.is_boss_battle = False
        self._tower_prompted = False
        self.refresh_search_focus(force=True)

    def get_focused_search_npc(self):
        """Mengembalikan NPC yang menjadi fokus visualisasi pathfinding & metrik Tab Search."""
        npcs = [n for n in (getattr(self, "npc", None), getattr(self, "npc_kuro", None), getattr(self, "npc_shiro", None)) if n is not None]
        if not npcs:
            return None
        mode = getattr(self, "search_focus_mode", "AUTO")
        if mode != "AUTO":
            for n in npcs:
                if getattr(n, "name", "") == mode:
                    return n
        p_grid = self.player.grid
        active = [n for n in npcs if getattr(n, "chasing", False) or getattr(n, "investigating", False)]
        pool = active if active else npcs
        return min(pool, key=lambda n: abs(n.grid[0] - p_grid[0]) + abs(n.grid[1] - p_grid[1]))

    def refresh_search_focus(self, force: bool = False):
        """Menyegarkan visualisasi jalur kuning-biru & metrik Tab Search jika fokus NPC berubah."""
        focused = self.get_focused_search_npc()
        if focused is None:
            return
        if force or id(focused) != getattr(self, "_last_focused_npc_id", None):
            self._last_focused_npc_id = id(focused)
            target = (
                focused.investigate_target
                if (getattr(focused, "investigating", False) and getattr(focused, "investigate_target", None))
                else self.player.grid
            )
            focused.find_path(target)

    def open_graph_modal(self, mode="MINIMAX"):
        """Membuka modal visualizer pohon keputusan AI universal (Minimax, Logic Refutation, PDDL Planning)."""
        if hasattr(self, "overlay") and hasattr(self.overlay, "graph_modal"):
            if mode == "MINIMAX" and self.battle_system and getattr(self.battle_system, "last_tree_root", None):
                self.overlay.graph_modal.set_tree_from_minimax(self.battle_system.last_tree_root)
            elif mode == "LOGIC" and hasattr(self, "inter_npc_manager") and self.inter_npc_manager:
                summary = self.inter_npc_manager.latest_proof_summary or {
                    "query": "AssignChaser_Kuro",
                    "proved": True,
                    "negated_query": "~AssignChaser_Kuro",
                    "proof_trace": self.inter_npc_manager.latest_steps,
                }
                logic_tree = self.inter_npc_manager.engine.build_graph_nodes(summary)
                self.overlay.graph_modal.set_tree_from_generic(
                    logic_tree,
                    title="POHON RESOLUSI REFUTASI (MATERI 07: LOGIC KB)",
                    mode_tag="LOGIC"
                )
            elif mode == "PLANNING":
                if not getattr(self, "latest_plan_result", None) or (self.game_mode == "BATTLE" and not getattr(self.battle_system, "tactical_plan_executed", False)):
                    if self.game_mode == "BATTLE":
                        warrior = "Oyen the Warrior"
                        tank = "Kuro the Ranger"
                        healer = "Shiro the Mage"
                        if self.current_squad and len(self.current_squad.members) >= 2:
                            m = self.current_squad.members
                            warrior = m[0].name
                            tank = m[1].name
                            healer = m[2].name if len(m) > 2 else m[1].name
                        s0, goal, actions = create_battle_tactics_problem(warrior, tank, healer)
                    else:
                        s0, goal, actions = create_world_patrol_problem("A")
                    use_backward = getattr(self, "selected_planning_engine", "FORWARD_A_STAR") == "BACKWARD_REGRESSION"
                    planner = self.backward_planner if (use_backward and getattr(self, "backward_planner", None)) else self.forward_planner
                    self.latest_plan_result = planner.plan(s0, goal, actions)
                plan_tree = build_planning_graph_nodes(self.latest_plan_result)
                self.overlay.graph_modal.set_tree_from_generic(
                    plan_tree,
                    title=f"POHON PERENCANAAN PDDL ({self.latest_plan_result.engine_name})",
                    mode_tag="PLANNING"
                )
            if not self.overlay.graph_modal.visible:
                self.overlay.graph_modal.toggle()
            else:
                if self.overlay.graph_modal._needs_layout:
                    self.overlay.graph_modal._compute_layout()
                self.overlay.graph_modal.reset_camera()

    def _build_fonts(self, scale: float = 1.0):
        fonts = {}
        sc = max(1.0, min(1.35, scale))
        sz_tiny = int(round(12 * sc))
        sz_sm = int(round(14 * sc))
        sz_bubble = int(round(14 * sc))
        sz_title = int(round(17 * sc))
        sz_huge = int(round(22 * sc))
        try:
            fonts["tiny"] = pygame.font.SysFont(["dejavusans", "liberationsans", "ubuntusans", "arial"], sz_tiny, bold=True)
            fonts["sm"] = pygame.font.SysFont(["dejavusans", "liberationsans", "ubuntusans", "arial"], sz_sm)
            fonts["bubble"] = pygame.font.SysFont(["dejavusans", "liberationsans", "ubuntusans", "arial"], sz_bubble, bold=True)
            fonts["title"] = pygame.font.SysFont(["dejavusans", "liberationsans", "ubuntusans", "arial"], sz_title, bold=True)
            fonts["huge"] = pygame.font.SysFont(["dejavusans", "liberationsans", "ubuntusans", "arial"], sz_huge, bold=True)
        except (OSError, RuntimeError):
            fonts["tiny"] = pygame.font.Font(None, int(round(15 * sc)))
            fonts["sm"] = pygame.font.Font(None, int(round(18 * sc)))
            fonts["bubble"] = pygame.font.Font(None, int(round(18 * sc)))
            fonts["title"] = pygame.font.Font(None, int(round(22 * sc)))
            fonts["huge"] = pygame.font.Font(None, int(round(28 * sc)))
        return fonts

    def _apply_viewport(self):
        w, h = self.screen.get_size()
        self.camera = Camera(w, h, self.map_w, self.map_h, app_ref=self)
        self.water_anim_timer = 0.0
        self.water_frame = 0
        self._refresh_scaled_map()
        self.camera.follow((self.player.px, self.player.py))
        self._last_camera_target = (self.player.px, self.player.py)

    def _on_window_resized(self, w: int, h: int) -> None:
        """Sinkronisasi kamera dan ukuran panel UI terpadu (NavRail & InspectorDock) saat resolusi berubah."""
        ui_scale = config.update_ui_scale(w, h)
        if hasattr(self, "fonts") and self.fonts:
            self.fonts.update(self._build_fonts(ui_scale))
        self._apply_viewport()
        if hasattr(self, "overlay") and self.overlay:
            self.overlay.on_resize(w, h)

    def toggle_fullscreen(self) -> None:
        """Mengalihkan mode fullscreen / windowed resizable (F11)."""
        self.is_fullscreen = not getattr(self, "is_fullscreen", False)
        if self.is_fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), RESIZABLE)
        w, h = self.screen.get_size()
        self._on_window_resized(w, h)

    def _zoom_camera(self, factor, focus_screen=None):
        self.overlay.on_camera_zoom()
        if self.camera.zoom_by(factor, focus_screen):
            self._refresh_scaled_map()

    def run(self):
        if os.environ.get("SDL_VIDEODRIVER") != "dummy" and hasattr(self, "guide_modal"):
            self.guide_modal.open_welcome()
        while self.running:
            dt = self.clock.tick(config.FPS) / 1000.0
            self._handle_events()
            self._update(dt)
            self._draw()
        getattr(pygame, "quit")()

    def _update(self, dt):
        self.overlay.update_animation(dt)

        if getattr(self, "guide_modal", None) and self.guide_modal.is_open:
            return

        # Update gelombang suara siulan [SPASI] (plan_dev.md Section 4.2)
        for wave in self.whistle_waves[:]:
            wave["radius"] += dt * wave.get("speed", 160.0)
            progress = wave["radius"] / wave["max_radius"]
            wave["alpha"] = max(0, int(220 * (1.0 - progress)))
            if wave["radius"] >= wave["max_radius"]:
                self.whistle_waves.remove(wave)

        # Update HUD AI Ticker banner timer
        if self.ai_ticker_info:
            self.ai_ticker_info["timer"] -= dt
            if self.ai_ticker_info["timer"] <= 0:
                self.ai_ticker_info = None

        if self.game_mode == "EXPLORATION":
            self.player.update(dt)
            self.npc.update(dt)
            self.npc_kuro.update(dt)
            self.npc_shiro.update(dt)
            self.refresh_search_focus()

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

            # Animasi riak air sungai (ganti frame tiap 0.2 detik)
            self.water_anim_timer += dt
            new_wf = int(self.water_anim_timer / 0.2) % 4
            if new_wf != self.water_frame:
                self.water_frame = new_wf
                if hasattr(self, "scaled_maps") and self.scaled_maps:
                    self.scaled_map = self.scaled_maps[self.water_frame % len(self.scaled_maps)]

            # Animasi angin, ayam & partikel kilau padang rumput
            self.wind_timer += dt
            self.chicken_timer += dt
            self._update_chickens(dt)

            # Efek suara denting prompt [E] Buka Peti saat pemain mendekat ke peti tertutup
            near_unopened_chest = False
            for ch in self.chests:
                if not ch.get("opened", False):
                    dx = abs(self.player.grid[0] - ch["pos"][0])
                    dy = abs(self.player.grid[1] - ch["pos"][1])
                    if max(dx, dy) <= 1:
                        near_unopened_chest = True
                        break

            if near_unopened_chest and not getattr(self, "was_near_chest", False):
                self.audio.play_chest_prompt()

            self.was_near_chest = near_unopened_chest
            self.sparkle_spawn_timer += dt
            if self.sparkle_spawn_timer >= 0.35 and len(self.sparkles) < 18:
                self.sparkle_spawn_timer = 0.0
                import random
                gx = random.randint(2, self.map.width - 3)
                gy = random.randint(3, self.map.height - 3)
                if self.map.is_walkable((gx, gy)) and not self.map.is_dirt_road((gx, gy)):
                    self.sparkles.append({
                        "wx": gx * 16 + 8,
                        "wy": gy * 16 + 8,
                        "t": 0.0,
                        "max_t": random.uniform(1.2, 2.2),
                        "size": random.choice([3, 4, 5]),
                    })
            for sp in self.sparkles[:]:
                sp["t"] += dt
                if sp["t"] >= sp["max_t"]:
                    self.sparkles.remove(sp)

            # Debu langkah kaki pemain (Footstep Dust)
            if self.player.moving:
                if not self._last_player_moving:
                    self.dust_particles.append({
                        "wx": self.player.px,
                        "wy": self.player.py + 6,
                        "t": 0.0,
                        "max_t": 0.25,
                    })
                    self._step_dust_timer = 0.0
                else:
                    self._step_dust_timer += dt
                    if self._step_dust_timer >= 0.14:
                        self.dust_particles.append({
                            "wx": self.player.px,
                            "wy": self.player.py + 6,
                            "t": 0.0,
                            "max_t": 0.25,
                        })
                        self._step_dust_timer = 0.0
            self._last_player_moving = self.player.moving

            for dp in self.dust_particles[:]:
                dp["t"] += dt
                if dp["t"] >= dp["max_t"]:
                    self.dust_particles.remove(dp)

            camera_target = (self.player.px, self.player.py)
            self.camera.follow(camera_target, smooth=True, dt=dt)
            self._last_camera_target = camera_target

            # Update animasi cincin sonar Bayesian & cek penemuan Relik Tersembunyi
            for sw in getattr(self, "sonar_waves", [])[:]:
                sw["radius"] += 220.0 * dt
                sw["alpha"] -= 170.0 * dt
                if sw["alpha"] <= 0:
                    self.sonar_waves.remove(sw)
            if (
                getattr(self, "relic_sonar", None)
                and not self.relic_sonar.found
                and self.relic_sonar.relic_pos == self.player.grid
                and not self.player.moving
            ):
                self._collect_hidden_relic()

            # Cek jika pemain tiba di ubin portal Menara Kuno (Abandoned Tower)
            portal_pos = getattr(self.map, "boss_portal", {"x": 38, "y": 5})
            pt_x, pt_y = portal_pos.get("x", 38), portal_pos.get("y", 5)
            if self.player.grid == (pt_x, pt_y) and not self.player.moving and not self.battle_reentry_locked:
                if not getattr(self, "_tower_prompted", False):
                    self._tower_prompted = True
                    self._interact_tower_portal()
            else:
                if self.player.grid != (pt_x, pt_y):
                    self._tower_prompted = False

            # Cek jarak kedekatan dengan NPC mana pun di peta (Grid distance <= 1 atau Pixel distance <= 18)
            all_npcs = [getattr(self, "npc", None), getattr(self, "npc_kuro", None), getattr(self, "npc_shiro", None)]
            min_dist = 999
            closest_npc = None
            pixel_collision_npc = None

            for n in all_npcs:
                if not n:
                    continue
                d = abs(self.player.grid[0] - n.grid[0]) + abs(self.player.grid[1] - n.grid[1])
                if d < min_dist:
                    min_dist = d
                    closest_npc = n
                # Cek jarak pixel langsung saat entitas melangkah/bergerak
                px_dist = math.hypot(self.player.px - n.px, self.player.py - n.py)
                if px_dist <= 18.0:
                    pixel_collision_npc = n

            # Unlock reentry lock jika pemain sudah menjauh atau jeda waktu habis
            if getattr(self, "battle_reentry_timer", 0.0) > 0.0:
                self.battle_reentry_timer = max(0.0, self.battle_reentry_timer - dt)
                if self.battle_reentry_timer <= 0.0:
                    self.battle_reentry_locked = False
            elif min_dist > 1:
                self.battle_reentry_locked = False

            target_encounter_npc = pixel_collision_npc or (closest_npc if min_dist <= 1 else None)

            if target_encounter_npc and not self.battle_reentry_locked:
                # Tabrakan fisik terdeteksi! Kunci seketika gerakan kedua entitas agar tidak saling tembus
                self.player.moving = False
                self.player.move_t = 1.0
                self.player.px, self.player.py = self.map.world_to_px(self.player.grid)
                target_encounter_npc.moving = False
                target_encounter_npc.move_t = 1.0
                target_encounter_npc.px, target_encounter_npc.py = self.map.world_to_px(target_encounter_npc.grid)
                self.player.is_hidden = False
                self.enter_pre_battle(target_encounter_npc)
        elif self.game_mode == "PRE_BATTLE":
            # Animasi searching & fade-in satu-per-satu kartu skuad Pre-Battle
            anim = getattr(self, "pre_battle_anim", None)
            if anim:
                anim["timer"] += dt
                if anim["phase"] == "SEARCHING" and anim["timer"] >= anim["search_dur"]:
                    anim["phase"] = "REVEAL"
                    anim["timer"] = 0.0
                    self.reroll_toast_timer = 1.6
                if anim["phase"] == "REVEAL":
                    members_cnt = len(self.current_squad.members) if self.current_squad else 0
                    popped = anim.setdefault("popped", set())
                    for idx in range(members_cnt):
                        if idx not in popped and anim["timer"] >= idx * anim["stagger"]:
                            popped.add(idx)
                            if hasattr(self, "audio") and self.audio:
                                self.audio.play_card_reveal()
                    total_rev = max(0, members_cnt - 1) * anim["stagger"] + anim["fade_dur"]
                    if anim["timer"] >= total_rev:
                        self.pre_battle_anim = None
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
                        loot_data = anim["loot"]
                        if hasattr(self.player, "inventory") and isinstance(self.player.inventory, list):
                            if loot_data["name"] not in self.player.inventory:
                                self.player.inventory.append(loot_data["name"])
                            if loot_data.get("image_key") and loot_data["image_key"] not in self.player.inventory:
                                self.player.inventory.append(loot_data["image_key"])
                        self.loot_modal = {
                            "loot": loot_data,
                            "old_npc": anim["npc"],
                            "next_npc": anim["next_npc"],
                            "heal_amount": anim["heal_amount"],
                            "timer": 0.0,
                            "is_final": anim["is_final"],
                        }
                    elif anim.get("next_npc"):
                        self._start_card_summon_anim(anim["npc"], anim["next_npc"])
                    elif anim.get("is_final"):
                        self._open_battle_result_modal(is_victory=True)

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

            # Mode Battle: Jika Player kalah (winner == NPC), buka pop-up hasil duel
            if (
                self.battle_system.is_finished
                and self.battle_system.winner == "NPC"
                and not getattr(self, "battle_result_modal", None)
                and not self.loot_modal
                and not self.npc_defeat_anim
            ):
                self._open_battle_result_modal(is_victory=False)

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

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
                continue
            if getattr(self, "guide_modal", None) and self.guide_modal.is_open:
                if self.guide_modal.handle_event(event):
                    continue
            # Modal Visualizer Pohon AI Universal (Full-Screen)
            if hasattr(self, "overlay") and hasattr(self.overlay, "tree_overlay") and self.overlay.tree_overlay.visible:
                if self.overlay.tree_overlay.handle_event(event):
                    continue
            if hasattr(self, "logic_overlay") and self.logic_overlay.visible:
                if self.logic_overlay.handle_event(event):
                    continue
            if hasattr(self, "planning_overlay") and self.planning_overlay.visible:
                if self.planning_overlay.handle_event(event):
                    continue

            if event.type == QUIT:
                self.running = False
            elif event.type == VIDEORESIZE:
                self.screen = pygame.display.set_mode(event.size, RESIZABLE)
                self._on_window_resized(event.size[0], event.size[1])
            elif event.type == MOUSEWHEEL:
                m_pos = pygame.mouse.get_pos()
                if self.game_mode == "PRE_BATTLE":
                    if self.pre_battle_visualizer.is_open:
                        self.pre_battle_visualizer.handle_event(event)
                    else:
                        self.overlay.handle_event(event)
                elif self.game_mode == "BATTLE":
                    # Scroll mousewheel pada Decision Tree Overlay (prioritas utama jika aktif)
                    if self.overlay.tree_overlay.visible:
                        self.overlay.tree_overlay.handle_event(event)
                    # Scroll mousewheel pada Battle Log (4 riwayat)
                    elif self.battle_log_rect.collidepoint(m_pos):
                        total_logs = len(self.battle_system.battle_logs)
                        max_scroll = max(0, total_logs - 4)
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
                    if getattr(self, "battle_result_modal", None):
                        if self.btn_result_restart.collidepoint(pos):
                            is_boss = self.battle_result_modal.get("is_boss", False)
                            self.battle_result_modal = None
                            if is_boss:
                                self.enter_boss_battle()
                            else:
                                self.enter_battle()
                        elif self.btn_result_exit.collidepoint(pos):
                            self.exit_battle()
                        return
                    if self.loot_modal:
                        self._dismiss_loot_modal()
                        return

                    # 0. Tombol Keluar / Exit dari Mode Battle
                    if hasattr(self, "btn_battle_exit") and self.btn_battle_exit.collidepoint(pos):
                        self.exit_battle()
                        return

                    # Prioritaskan penanganan klik pada Decision Tree jika sedang aktif
                    if self.overlay.tree_overlay.visible:
                        if self.overlay.tree_overlay.handle_event(event):
                            return

                    # 1. Tombol Aksi Pertempuran Pemain (Interactive Battle Actions)
                    can_act = (
                        not self.battle_system.state.is_npc_turn
                        and not self.battle_system.is_finished
                        and not self.card_summon_anim
                        and not getattr(self, "loot_modal", None)
                        and not self.npc_defeat_anim
                    )
                    if can_act:
                        if self.btn_action_attack.collidepoint(pos):
                            self.battle_log_scroll_offset = 0
                            self.battle_system.execute_player_action(ACTION_ATTACK)
                            return
                        elif self.btn_action_heavy.collidepoint(pos) and self.battle_system.state.player_heavy_cd == 0:
                            self.battle_log_scroll_offset = 0
                            self.battle_system.execute_player_action(ACTION_HEAVY)
                            return
                        elif self.btn_action_defend.collidepoint(pos):
                            self.battle_log_scroll_offset = 0
                            self.battle_system.execute_player_action(ACTION_DEFEND)
                            return
                        elif self.btn_action_potion.collidepoint(pos) and self.battle_system.state.player_potions > 0:
                            self.battle_log_scroll_offset = 0
                            self.battle_system.execute_player_action(ACTION_POTION)
                            return

                    # 2. Klik tombol [Lihat Decision Tree]
                    if self.btn_tree_modal.collidepoint(pos):
                        self.overlay.toggle_tree_overlay()
                    # 3. Klik tombol panah scroll battle log
                    elif self.btn_log_up.collidepoint(pos):
                        total_logs = len(self.battle_system.battle_logs)
                        max_scroll = max(0, total_logs - 4)
                        self.battle_log_scroll_offset = min(max_scroll, self.battle_log_scroll_offset + 1)
                    elif self.btn_log_down.collidepoint(pos):
                        self.battle_log_scroll_offset = max(0, self.battle_log_scroll_offset - 1)
                    else:
                        self.overlay.handle_event(event)
                else:
                    if getattr(self, "gacha_showcase", None):
                        self.gacha_showcase = None
                        return
                    if getattr(self, "btn_guide_pill", None) and self.btn_guide_pill.collidepoint(pos):
                        self.guide_modal.toggle()
                        return
                    if not self.overlay.handle_event(event) and event.button == 1:
                        self._handle_map_inspect_click(pos)
            elif event.type in (MOUSEBUTTONUP, MOUSEMOTION):
                if self.game_mode == "BATTLE" and self.overlay.tree_overlay.visible:
                    self.overlay.tree_overlay.handle_event(event)
                    continue
                self.overlay.handle_event(event)
                if self.game_mode == "PRE_BATTLE":
                    if self.pre_battle_visualizer.is_open:
                        self.pre_battle_visualizer.handle_event(event)
            elif event.type == KEYDOWN:
                self._handle_key(event.key, event=event)

    def _handle_key(self, key, event=None):
        if key == K_F11:
            self.toggle_fullscreen()
            return

        # Shortcut TAB (Buka/Tutup Panel/Dock) & ALT+TAB / CTRL+TAB (Ganti-ganti Tab/Panel)
        if key == K_TAB:
            mods = pygame.key.get_mods()
            if event is not None and hasattr(event, "mod"):
                mods |= event.mod
            is_alt = bool(mods & (pygame.KMOD_ALT | getattr(pygame, "KMOD_LALT", 0) | getattr(pygame, "KMOD_RALT", 0)))
            is_ctrl = bool(mods & (pygame.KMOD_CTRL | getattr(pygame, "KMOD_LCTRL", 0) | getattr(pygame, "KMOD_RCTRL", 0)))
            is_shift = bool(mods & (pygame.KMOD_SHIFT | getattr(pygame, "KMOD_LSHIFT", 0) | getattr(pygame, "KMOD_RSHIFT", 0)))

            if is_alt or is_ctrl:
                self.overlay.cycle_dock_tab(reverse=is_shift)
            else:
                self.overlay.toggle_dock()
            return

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
            elif self.game_mode == "EXPLORATION" and getattr(self, "inspected_tile", None):
                self.inspected_tile = None
                return
            self.running = False
            return

        if key in (K_EQUALS, K_PLUS):
            self._zoom_camera(1.1)
            return
        if key == K_MINUS:
            self._zoom_camera(1 / 1.1)
            return

        if key == K_h:
            if hasattr(self, "guide_modal"):
                self.guide_modal.toggle()
                return
        if key == K_k:
            if hasattr(self, "logic_overlay"):
                self.logic_overlay.toggle()
                return
        if key == K_p:
            if hasattr(self, "planning_overlay"):
                self.planning_overlay.toggle()
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
            elif key == K_ESCAPE:
                self.exit_battle()
            return

        if self.game_mode == "BATTLE":
            if getattr(self, "battle_result_modal", None):
                if key == K_r:
                    is_boss = self.battle_result_modal.get("is_boss", False)
                    self.battle_result_modal = None
                    if is_boss:
                        self.enter_boss_battle()
                    else:
                        self.enter_battle()
                elif key in (K_ESCAPE, K_RETURN, K_KP_ENTER, K_SPACE):
                    self.exit_battle()
                return
            # Jika modal rampasan perang aktif, tekan ENTER atau SPASI untuk lanjut
            if self.loot_modal:
                if key in (K_RETURN, K_KP_ENTER, K_SPACE, K_ESCAPE):
                    self._dismiss_loot_modal()
                return

            # Shortcut tombol di mode Battle
            if key == K_ESCAPE:
                if self.overlay.tree_overlay.visible:
                    self.overlay.tree_overlay.visible = False
                    return
                self.exit_battle()
                return
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
                if key in (K_1, K_w, K_UP):
                    self.battle_system.execute_player_action(ACTION_ATTACK)
                elif key in (K_2, K_a, K_LEFT):
                    self.battle_system.execute_player_action(ACTION_HEAVY)
                elif key in (K_3, K_d, K_RIGHT):
                    self.battle_system.execute_player_action(ACTION_DEFEND)
                elif key in (K_4, K_s, K_DOWN):
                    self.battle_system.execute_player_action(ACTION_POTION)
        else:
            # Mode Eksplorasi Peta
            if getattr(self, "gacha_showcase", None):
                if key in (K_RETURN, K_KP_ENTER, K_SPACE, K_e, K_ESCAPE):
                    self.gacha_showcase = None
                return

            if key in (K_LCTRL, K_RCTRL):
                cur_vis = getattr(self.overlay, "show_path_visualization", True) and self.overlay.visualization_active
                new_vis = not cur_vis
                self.overlay.show_path_visualization = new_vis
                if new_vis:
                    if self.npc.chasing:
                        self.overlay.set_chasing_visualization(True)
                    else:
                        self.npc.find_path(self.player.grid)
                    self.overlay.start_path_animation()
                else:
                    self.overlay.stop_path_animation()
                dock = getattr(self.overlay, "dock", None)
                tab_search = dock.tabs.get(1) if dock and hasattr(dock, "tabs") else None
                if tab_search and hasattr(tab_search, "btn_toggle_path"):
                    tab_search.show_path_line = new_vis
                    tab_search.btn_toggle_path.text = f"Toggle Jalur di Peta: {'AKTIF' if new_vis else 'OFF'}"
                return

            if key == K_e:
                # Buka peti harta jika berjarak <= 1 langkah ubin (termasuk diagonal)
                for ch in self.chests:
                    if not ch["opened"]:
                        dx = abs(self.player.grid[0] - ch["pos"][0])
                        dy = abs(self.player.grid[1] - ch["pos"][1])
                        if max(dx, dy) <= 1:
                            self._open_chest(ch)
                            return
                # Interaksi portal Menara Kuno (Abandoned Tower)
                portal_pos = getattr(self.map, "boss_portal", {"x": 38, "y": 5})
                tx, ty = portal_pos.get("x", 38), portal_pos.get("y", 5)
                if max(abs(self.player.grid[0] - tx), abs(self.player.grid[1] - ty)) <= 2:
                    self._interact_tower_portal()
                    return
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
                self._trigger_whistle()
            elif key == K_f:
                self._trigger_sonar_scan()
            elif key == K_b:
                # Tombol pintas untuk masuk fase Pre-Battle
                self.enter_pre_battle()

    def _draw(self):
        self.screen.fill((118, 186, 178) if self.game_mode == "EXPLORATION" else config.BG_COLOR)

        # 1. Gambar peta di sisi kanan (khusus mode eksplorasi)
        assert self.scaled_map is not None
        if self.game_mode == "EXPLORATION":
            self.screen.blit(self.scaled_map, (int(self.camera.offset_x), int(self.camera.offset_y)))

        if self.game_mode == "EXPLORATION":
            self.overlay.draw_world(self.screen, self.camera, self.map, self.npc, self.player)
            self._draw_sparkles()
            self._draw_dust_particles()
            self._draw_swaying_ground_foliage()
            self._draw_relic_heatmap()
            self._draw_chests()
            self._draw_tower_portal()
            self._draw_whistle_waves()
            self._draw_sonar_waves()
            self._draw_chickens()
            player_alpha = 150 if getattr(self.player, "is_hidden", False) else 255
            self._draw_sprite(self.player.sprite.current_image, self.player.px, self.player.py, alpha=player_alpha)
            if getattr(self.player, "is_hidden", False):
                self._draw_stealth_badge()
            self._draw_sprite(self.npc.sprite.current_image, self.npc.px, self.npc.py)
            self._draw_sprite(self.npc_kuro.sprite.current_image, self.npc_kuro.px, self.npc_kuro.py)
            self._draw_sprite(self.npc_shiro.sprite.current_image, self.npc_shiro.px, self.npc_shiro.py)
            self._draw_npc_speech_bubbles()
            self._draw_swaying_tree_canopies()
            if self.player.call_bubble_visible:
                self._draw_call_bubble()
            self._draw_npc_offscreen_indicator()
            self._draw_inspected_tile_popup()
            self._draw_obtained_items_hud()
            self._draw_guide_pill_button()
            self._draw_ai_ticker_banner()
            if self.gacha_active or getattr(self, "gacha_showcase", None) or self.gacha_message_timer > 0:
                self._draw_gacha_popup()
        elif self.game_mode == "PRE_BATTLE":
            self._draw_pre_battle_arena()
        else:
            # Di mode duel, tampilkan arena duel di atas peta
            self._draw_battle_arena()

        # 2. Gambar overlay UI terpadu di sisi kiri (Nav Rail & Collapsible Inspector Drawer)
        self.overlay.draw_ui(self.screen)

        # 4. Gambar modal rampasan perang & hasil duel di paling atas
        if self.game_mode == "BATTLE" and getattr(self, "loot_modal", None):
            self._draw_loot_modal()
        if self.game_mode == "BATTLE" and getattr(self, "battle_result_modal", None):
            self._draw_battle_result_modal()

        # 5. Gambar modal visualizer Pohon CSP & Local Search jika terbuka di mode PRE_BATTLE
        if self.game_mode == "PRE_BATTLE" and self.pre_battle_visualizer.is_open:
            self.pre_battle_visualizer.draw(self.screen, self.fonts)

        # 6. Gambar modal visualizer Logic Overlay [K] jika aktif
        if hasattr(self, "logic_overlay") and self.logic_overlay.visible:
            self.logic_overlay.draw(self.screen)

        # 7. Gambar modal visualizer Planning Overlay [P] jika aktif
        if hasattr(self, "planning_overlay") and self.planning_overlay.visible:
            self.planning_overlay.draw(self.screen)

        # 8. Unified Graph Modal (Pohon AI Universal) di layer paling atas jika terbuka
        if hasattr(self, "overlay") and hasattr(self.overlay, "graph_modal") and self.overlay.graph_modal.visible:
            self.overlay.graph_modal.draw(self.screen)

        # 9. Modal Panduan Awal & Buku Panduan [H] di layer paling atas
        if hasattr(self, "guide_modal") and self.guide_modal.is_open:
            self.guide_modal.draw(self.screen)

        pygame.display.flip()
