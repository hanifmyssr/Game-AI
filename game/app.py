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

MOUSEWHEEL = getattr(pygame, "MOUSEWHEEL", 1027)
K_F11 = getattr(pygame, "K_F11", 292)
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

    def __init__(self, win_w, win_h, map_w, map_h, margin=0.02):
        self.zoom = 2.8
        self.fit_zoom = 1.0
        self.map_w = map_w
        self.map_h = map_h
        self.win_w = win_w
        self.win_h = win_h
        self.left_panel_w = config.NAV_RAIL_WIDTH
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.reset(win_w, win_h, map_w, map_h, margin)

    def reset(self, win_w, win_h, map_w, map_h, margin=0.02, left_panel_w=None):
        self.win_w = win_w
        self.win_h = win_h
        self.map_w = map_w
        self.map_h = map_h
        self.left_panel_w = left_panel_w or config.NAV_RAIL_WIDTH
        usable_w = max(100.0, win_w - self.left_panel_w)
        self.fit_zoom = min(usable_w / map_w, win_h / map_h) * (1.0 - margin)
        # Kamera dekat (close-up) default 2.8x bebas burik
        self.zoom = 2.8
        self._center_map()

    def _center_map(self):
        usable_w = max(100.0, self.win_w - self.left_panel_w)
        scaled_w = self.map_w * self.zoom
        scaled_h = self.map_h * self.zoom
        self.offset_x = self.left_panel_w + (usable_w - scaled_w) / 2.0
        self.offset_y = (self.win_h - scaled_h) / 2.0

    def zoom_by(self, factor, focus_screen=None):
        old_zoom = self.zoom
        min_zoom = max(1.2, self.fit_zoom * 0.8)
        max_zoom = 4.5
        if focus_screen is None:
            focus_screen = (config.SAFE_CAMERA_FOCUS_X, self.win_h / 2.0)
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
        viewport_center_x = config.SAFE_CAMERA_FOCUS_X
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
        self.battle_bg = BattleArenaBackground()
        self.battle_system.on_action_callback = self._on_battle_action_executed
        self.battle_system.on_tag_in = self._on_npc_tag_in
        self.battle_system.on_tactical_plan = self._on_npc_tactical_plan
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
        self.btn_action_attack = pygame.Rect(0, 0, 0, 0)
        self.btn_action_heavy = pygame.Rect(0, 0, 0, 0)
        self.btn_action_defend = pygame.Rect(0, 0, 0, 0)
        self.btn_action_potion = pygame.Rect(0, 0, 0, 0)
        self.btn_battle_exit = pygame.Rect(0, 0, 0, 0)
        self.reroll_toast_timer = 0.0
        self.pre_battle_visualizer = PreBattleVisualizerModal()
        self.overlay.on_open_ai_inspector = self.pre_battle_visualizer.toggle

        self.player = Player(self.map, self.events)

        # 3 NPC di Peta (Opsi B: 1 Pengejar Utama + 2 Patroli Waypoint)
        # NPC 1: Oyen (Pengejar Utama pada [SPACE])
        self.npc = NPC(self.map, self.events, self.player, name="Oyen", sprite_dir=config.OYEN_DIR)
        # NPC 2: Kuro (Patroli Wilayah Barat/Utara di tebing/gua)
        self.npc_kuro = NPC(
            self.map,
            self.events,
            self.player,
            name="Kuro",
            tint_color=(45, 45, 55),
            is_patrol=True,
            waypoints=[(11, 4), (16, 4), (16, 7), (12, 5)],
            sprite_dir=config.KURO_DIR,
        )
        # NPC 3: Shiro (Patroli Wilayah Timur/Selatan di dermaga/pulau)
        self.npc_shiro = NPC(
            self.map,
            self.events,
            self.player,
            name="Shiro",
            tint_color=(195, 205, 220),
            is_patrol=True,
            waypoints=[(35, 20), (37, 20), (37, 23), (34, 23)],
            sprite_dir=config.SHIRO_DIR,
        )

        self.events.subscribe_player_moved(self.npc.on_player_moved)
        self.events.subscribe_player_moved(self.npc_kuro.on_player_moved)
        self.events.subscribe_player_moved(self.npc_shiro.on_player_moved)
        self.events.subscribe_player_moved(self._on_player_moved_sound)
        self.events.subscribe_algorithm_changed(self.npc.set_algorithm)
        self.events.subscribe_algorithm_changed(self.npc_kuro.set_algorithm)
        self.events.subscribe_algorithm_changed(self.npc_shiro.set_algorithm)

        # Audio Manager & BGM (Musik Latar)
        self.audio = AudioManager()
        self.audio.play_bgm(volume=0.15)
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

        # Modul Materi 07: Logic & Knowledge Representation
        self.inter_npc_manager = InterNPCManager(self)
        self.logic_overlay = LogicOverlay(self.fonts, self)

        # Modul Materi 08: Automated Classical Planning (PDDL)
        self.forward_planner = ForwardProgressionPlanner()
        self.backward_planner = BackwardRegressionPlanner()
        self.task_executor = TaskExecutor(self)
        self.latest_plan_result = None
        self.planning_overlay = PlanningOverlay(self.fonts, self)

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

        # 2. Reset Player (Bolu)
        if hasattr(self, "player") and self.player:
            self.player.persistent_hp = config.MAX_HP
            self.player.persistent_potions = 3
            self.player.atk_bonus = 0
            self.player.def_bonus = 0
            if hasattr(self.player, "inventory"):
                self.player.inventory.clear()
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
                    self.latest_plan_result = self.forward_planner.plan(s0, goal, actions)
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

    # ------------------------------------------------------------------ #
    def _build_fonts(self):
        fonts = {}
        try:
            fonts["tiny"] = pygame.font.SysFont(["consolas", "segoeui", "arial"], 13, bold=True)
            fonts["sm"] = pygame.font.SysFont(["consolas", "segoeui", "arial"], 16)
            fonts["bubble"] = pygame.font.SysFont(["consolas", "segoeui", "arial"], 16, bold=True)
            fonts["title"] = pygame.font.SysFont(["segoeui", "arial"], 19, bold=True)
            fonts["huge"] = pygame.font.SysFont(["segoeui", "arial"], 26, bold=True)
        except (OSError, RuntimeError):
            fonts["tiny"] = pygame.font.Font(None, 18)
            fonts["sm"] = pygame.font.Font(None, 22)
            fonts["bubble"] = pygame.font.Font(None, 24)
            fonts["title"] = pygame.font.Font(None, 28)
            fonts["huge"] = pygame.font.Font(None, 38)
        return fonts

    def _apply_viewport(self):
        w, h = self.screen.get_size()
        self.camera = Camera(w, h, self.map_w, self.map_h)
        self.water_anim_timer = 0.0
        self.water_frame = 0
        self._refresh_scaled_map()
        self.camera.follow((self.player.px, self.player.py))
        self._last_camera_target = (self.player.px, self.player.py)

    def _on_window_resized(self, w: int, h: int) -> None:
        """Sinkronisasi kamera dan ukuran panel UI terpadu (NavRail & InspectorDock) saat resolusi berubah."""
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

    def _on_player_moved_sound(self, pos):
        if self.game_mode == "EXPLORATION":
            surface = self.map.get_surface_type(pos)
            self.audio.play_step(surface)

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
        if hasattr(self, "overlay") and hasattr(self.overlay, "nav_rail"):
            self.overlay.nav_rail.set_badge(5, active=False)
        # Jika darah player sebelumnya habis/kalah atau <= 10, pulihkan penuh ke 100
        if getattr(self.player, "persistent_hp", 100) <= 10:
            self.player.persistent_hp = 100
            self.player.persistent_potions = max(2, self.player.persistent_potions)
        if self.current_squad:
            self.current_squad.reset()
            self.battle_system.reset_with_squad(self.current_squad, player=self.player)
        else:
            self.battle_system.reset()
        # Hitung preview awal evaluasi AI untuk metrik & skor aksi di panel
        self.battle_system.update_ai_preview()

    def exit_battle(self):
        self.game_mode = "EXPLORATION"
        self.overlay.set_mode("EXPLORATION")
        self.battle_reentry_locked = True
        self.card_summon_anim = None
        self.loot_toast = None
        self.loot_modal = None
        self.npc_defeat_anim = None
        self.final_loot_shown = False
        if hasattr(self, "vfx") and self.vfx:
            self.vfx.animations.clear()
        if hasattr(self, "overlay") and hasattr(self.overlay, "nav_rail"):
            self.overlay.nav_rail.set_badge(5, active=False)

        # 1. Hentikan status pengejaran (chasing) pada SEMUA NPC tanpa kecuali
        for n in (getattr(self, "npc", None), getattr(self, "npc_kuro", None), getattr(self, "npc_shiro", None)):
            if n:
                n.chasing = False
                n.moving = False
                n.path = []
                n.current_path = []
                n.chase_timer = 0.0

        # 2. Relokasi/respawn NPC yang dihadapi agar kembali ke patroli damai & tidak menumpuk di ubin pemain
        enc_npc = getattr(self, "current_encounter_npc", None) or getattr(self, "npc", None)
        if enc_npc:
            enc_npc._spawn()
            enc_npc.chasing = False
            enc_npc.moving = False
            enc_npc.path = []
            enc_npc.current_path = []
        self.current_encounter_npc = None

        # 3. Matikan visualisasi jalur pengejaran di HUD / NavRail
        if hasattr(self, "overlay"):
            self.overlay.set_chasing_visualization(False)

        # 4. Sinkronkan status Knowledge Base & InterNPCManager: insiden telah diselesaikan
        if hasattr(self, "inter_npc_manager") and self.inter_npc_manager:
            self.inter_npc_manager.chaser_assigned = None
            self.inter_npc_manager.guardians_assigned.clear()
            self.inter_npc_manager.latest_percept_event = "Patroli kondusif kembali setelah duel diselesaikan."
            # Retract status HasLootedItem_Player agar tidak terus-menerus memicu pemburu baru
            self.inter_npc_manager.kb.retract("HasLootedItem_Player")

        # 5. Sinkronkan sisa HP dan Potion player secara persistent
        if hasattr(self.battle_system, "state"):
            if self.battle_system.state.player_hp <= 0 or getattr(self.battle_system, "winner", None) == "NPC":
                # Jika Player kalah/tumbang dalam duel, pulihkan HP kembali PENUH (100) saat kembali ke map!
                self.player.persistent_hp = 100
                self.player.persistent_potions = max(2, self.player.persistent_potions)
            else:
                self.player.persistent_hp = max(10, self.battle_system.state.player_hp)
                self.player.persistent_potions = self.battle_system.state.player_potions

        # 6. Pulihkan visualisasi pathfinding A* / UCS (jalur kuning & biru) di peta eksplorasi
        if hasattr(self, "npc") and hasattr(self, "player"):
            self.npc.find_path(self.player.grid)
        if hasattr(self, "overlay"):
            self.overlay.visualization_active = True
            self.overlay.path_reveal = 1.0
            self.overlay.expanded_reveal = 1.0

    def _get_battle_char_positions(self):
        """Menghitung koordinat posisi pusat Player dan NPC tepat di tengah arena battle."""
        w, h = self.screen.get_size()
        is_dock_open = getattr(self.overlay.dock, "is_open", False) if hasattr(self, "overlay") and hasattr(self.overlay, "dock") else False
        panel_w = config.TOTAL_DOCK_WIDTH if is_dock_open else config.NAV_RAIL_WIDTH
        has_bench = bool(self.current_squad and len(self.current_squad.members) > 1)
        bench_w = 154 if has_bench else 16
        combat_w = w - panel_w - bench_w
        area_x = panel_w + combat_w // 2
        char_y = int(h * 0.28) if h < 750 else int(h * 0.33)
        spacing = 135
        player_arena_x = area_x - spacing
        npc_arena_x = area_x + spacing
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
                    self.overlay.handle_event(event)
            elif event.type in (MOUSEBUTTONUP, MOUSEMOTION):
                if self.game_mode == "BATTLE" and self.overlay.tree_overlay.visible:
                    self.overlay.tree_overlay.handle_event(event)
                    continue
                self.overlay.handle_event(event)
                if self.game_mode == "PRE_BATTLE":
                    if self.pre_battle_visualizer.is_open:
                        self.pre_battle_visualizer.handle_event(event)
            elif event.type == KEYDOWN:
                self._handle_key(event.key)

    def _handle_key(self, key):
        if key == K_F11:
            self.toggle_fullscreen()
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
            self.running = False
            return

        if key in (K_EQUALS, K_PLUS):
            self._zoom_camera(1.1)
            return
        if key == K_MINUS:
            self._zoom_camera(1 / 1.1)
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
                self.overlay.toggle_dock()
            elif key == K_ESCAPE:
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
                if self.npc.chasing:
                    self.overlay.set_chasing_visualization(True)
                elif self.overlay.visualization_active:
                    self.overlay.stop_path_animation()
                else:
                    self.npc.find_path(self.player.grid)
                    self.overlay.start_path_animation()
                return

            if key == K_e:
                # Buka peti harta jika berjarak <= 1 langkah ubin (termasuk diagonal)
                for ch in self.chests:
                    if not ch["opened"]:
                        dx = abs(self.player.grid[0] - ch["pos"][0])
                        dy = abs(self.player.grid[1] - ch["pos"][1])
                        if max(dx, dy) <= 1:
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

        # 1. Gambar peta di sisi kanan (khusus mode eksplorasi)
        assert self.scaled_map is not None
        if self.game_mode == "EXPLORATION":
            self.screen.blit(self.scaled_map, (int(self.camera.offset_x), int(self.camera.offset_y)))

        if self.game_mode == "EXPLORATION":
            self.overlay.draw_world(self.screen, self.camera, self.map, self.npc, self.player)
            self._draw_sparkles()
            self._draw_dust_particles()
            self._draw_swaying_ground_foliage()
            self._draw_chests()
            self._draw_chickens()
            self._draw_sprite(self.player.sprite.current_image, self.player.px, self.player.py)
            self._draw_sprite(self.npc.sprite.current_image, self.npc.px, self.npc.py)
            self._draw_sprite(self.npc_kuro.sprite.current_image, self.npc_kuro.px, self.npc_kuro.py)
            self._draw_sprite(self.npc_shiro.sprite.current_image, self.npc_shiro.px, self.npc_shiro.py)
            self._draw_swaying_tree_canopies()
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

        # 2. Gambar overlay UI terpadu di sisi kiri (Nav Rail & Collapsible Inspector Drawer)
        self.overlay.draw_ui(self.screen)

        # 4. Gambar modal rampasan perang di paling atas (menutup seluruh layar dengan dramatis)
        if self.game_mode == "BATTLE" and getattr(self, "loot_modal", None):
            self._draw_loot_modal()

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
        is_dock_open = getattr(self.overlay.dock, "is_open", False) if hasattr(self, "overlay") and hasattr(self.overlay, "dock") else False
        panel_w = config.TOTAL_DOCK_WIDTH if is_dock_open else config.TOTAL_COLLAPSED_WIDTH
        arena_w = w - panel_w
        area_x = panel_w + arena_w // 2

        # Latar belakang arena hutan lebat soft-focus (statis & cinematic blur)
        self.battle_bg.draw(self.screen, panel_w, arena_w, h)

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
        hp_bar_y = char_y + (80 if h < 750 else 88)
        self._draw_hp_bar(player_arena_x, hp_bar_y, "Hero Player", st.player_hp, st.player_defending, st.player_potions, (60, 160, 255), player_cd_text, max_hp=100)
        self._draw_hp_bar(npc_arena_x, hp_bar_y, npc_display_name, display_npc_hp, st.npc_defending, st.npc_potions, (255, 90, 80), npc_cd_text, max_hp=npc_max_hp)

        # Banner Notifikasi Rampasan Perang (Spoils of War)
        if hasattr(self, "loot_toast") and self.loot_toast and self.loot_toast["timer"] > 0:
            self._draw_loot_toast(w, h, (player_arena_x + npc_arena_x) // 2)

        # Banner Notifikasi Taktik PDDL Skuad NPC (Materi 08: Automated Planning)
        if hasattr(self.battle_system, "tactical_banner_timer") and self.battle_system.tactical_banner_timer > 0:
            self._draw_tactical_plan_banner(w, h, (player_arena_x + npc_arena_x) // 2)

        font_bubble = self.fonts.get("bubble", self.fonts["sm"])
        font_sm = self.fonts["sm"]
        font_tiny = self.fonts.get("tiny", pygame.font.Font(None, 13))

        # ------------------------------------------------------------------ #
        # Layout HUD Arena Bawah: RPG Diamond Action Hub (Tengah) & Battle Log
        # ------------------------------------------------------------------ #
        bench_w = 148
        bench_x = w - bench_w - 12
        combat_w = bench_x - 12 - panel_w
        combat_cx = panel_w + combat_w // 2

        # Dimensi Responsif & Proporsional Sesuai Skala Resolusi Layar
        is_compact = (w < 1180 or h < 750)
        card_w = 208 if is_compact else 230
        card_h = 44 if is_compact else 48
        badge_r = 15 if is_compact else 17
        D_X = 22 if is_compact else 32
        D_Y = 48 if is_compact else 54

        hub_cx = combat_cx
        hub_cy = int(h * 0.69) if h >= 750 else int(h * 0.66)

        m_pos = pygame.mouse.get_pos()
        can_act = (
            not st.is_npc_turn
            and not self.battle_system.is_finished
            and not self.card_summon_anim
            and not getattr(self, "loot_modal", None)
            and not self.npc_defeat_anim
        )

        top_rect = pygame.Rect(hub_cx - card_w // 2, hub_cy - D_Y - card_h, card_w, card_h)
        bot_rect = pygame.Rect(hub_cx - card_w // 2, hub_cy + D_Y, card_w, card_h)
        left_rect = pygame.Rect(hub_cx - D_X - card_w, hub_cy - card_h // 2, card_w, card_h)
        right_rect = pygame.Rect(hub_cx + D_X, hub_cy - card_h // 2, card_w, card_h)

        # Hitbox Tombol Responsif
        self.btn_action_attack = top_rect
        self.btn_action_heavy = left_rect
        self.btn_action_defend = right_rect
        self.btn_action_potion = bot_rect
        self.btn_tree_modal = pygame.Rect(0, 0, 0, 0)

        # ------------------------------------------------------------------ #
        # Tombol Keluar / Exit dari Mode Battle (Pojok Kiri Atas Arena Battle)
        # ------------------------------------------------------------------ #
        btn_exit_w = 118
        btn_exit_h = 30
        self.btn_battle_exit = pygame.Rect(panel_w + 14, 14, btn_exit_w, btn_exit_h)
        is_hov_exit = self.btn_battle_exit.collidepoint(m_pos)
        exit_bg = (68, 36, 32) if is_hov_exit else (46, 26, 24)
        exit_bdr = config.COLOR_ACCENT_GOLD if is_hov_exit else (160, 75, 65)
        draw_card(self.screen, self.btn_battle_exit, exit_bg, border_color=exit_bdr, border_radius=6)

        t_exit = font_tiny.render("[ESC] Keluar", True, (255, 235, 220) if is_hov_exit else (225, 195, 185))
        self.screen.blit(t_exit, (self.btn_battle_exit.centerx - t_exit.get_width() // 2, self.btn_battle_exit.centery - t_exit.get_height() // 2))

        is_hov_atk = can_act and self.btn_action_attack.collidepoint(m_pos)
        heavy_ready = can_act and (st.player_heavy_cd == 0)
        is_hov_hvy = heavy_ready and self.btn_action_heavy.collidepoint(m_pos)
        is_hov_def = can_act and self.btn_action_defend.collidepoint(m_pos)
        pot_ready = can_act and (st.player_potions > 0)
        is_hov_pot = pot_ready and self.btn_action_potion.collidepoint(m_pos)

        # ------------------------------------------------------------------ #
        # 0. Center Ornate Diamond Crest & Gold Connector Lines
        # ------------------------------------------------------------------ #
        crest_size = 24 if is_compact else 28
        pygame.draw.line(self.screen, (205, 160, 50), (hub_cx, hub_cy - crest_size), (hub_cx, top_rect.bottom), 3)
        pygame.draw.line(self.screen, (205, 160, 50), (hub_cx, hub_cy + crest_size), (hub_cx, bot_rect.top), 3)
        pygame.draw.line(self.screen, (205, 160, 50), (hub_cx - crest_size, hub_cy), (left_rect.right, hub_cy), 3)
        pygame.draw.line(self.screen, (205, 160, 50), (hub_cx + crest_size, hub_cy), (right_rect.left, hub_cy), 3)

        diamond_pts = [
            (hub_cx, hub_cy - crest_size),
            (hub_cx + crest_size, hub_cy),
            (hub_cx, hub_cy + crest_size),
            (hub_cx - crest_size, hub_cy),
        ]
        pygame.draw.polygon(self.screen, (26, 20, 16, 245), diamond_pts)
        pygame.draw.polygon(self.screen, (215, 170, 55), diamond_pts, 3)
        inner_dia = [
            (hub_cx, hub_cy - crest_size + 4),
            (hub_cx + crest_size - 4, hub_cy),
            (hub_cx, hub_cy + crest_size - 4),
            (hub_cx - crest_size + 4, hub_cy),
        ]
        pygame.draw.polygon(self.screen, (240, 200, 90, 150), inner_dia, 1)
        pygame.draw.circle(self.screen, config.COLOR_ACCENT_GOLD, (hub_cx, hub_cy), 4)

        tx_off = 42 if is_compact else 48
        max_txt_w = card_w - tx_off - 8

        # ------------------------------------------------------------------ #
        # 1. BAGIAN ATAS: [1] Serang Biasa (Shortcut: 1)
        # ------------------------------------------------------------------ #
        bg_atk = (32, 58, 38, 252) if is_hov_atk else ((22, 44, 28, 245) if can_act else (20, 24, 20, 220))
        bdr_atk = config.COLOR_ACCENT_GOLD if is_hov_atk else ((85, 215, 110) if can_act else (70, 90, 75))
        draw_card(self.screen, top_rect, bg_atk, border_color=bdr_atk, border_radius=8)
        bg1_cx, bg1_cy = top_rect.x + (22 if is_compact else 25), top_rect.centery
        pygame.draw.circle(self.screen, (60, 210, 100) if is_hov_atk else ((45, 185, 80) if can_act else (50, 95, 60)), (bg1_cx, bg1_cy), badge_r)
        pygame.draw.circle(self.screen, (220, 255, 230) if can_act else (110, 140, 120), (bg1_cx, bg1_cy), badge_r, 2)
        txt_1 = font_bubble.render("1", True, (255, 255, 255) if can_act else (180, 190, 180))
        self.screen.blit(txt_1, txt_1.get_rect(center=(bg1_cx, bg1_cy)))
        t_atk = font_bubble.render("Serang Biasa", True, (160, 255, 175) if can_act else config.COLOR_TEXT_MUTED)
        d_atk = font_tiny.render("Dmg: 15-25 • No CD", True, (210, 245, 215) if can_act else config.COLOR_TEXT_MUTED)
        self.screen.blit(t_atk, (top_rect.x + tx_off, top_rect.y + (5 if is_compact else 7)))
        self.screen.blit(d_atk, (top_rect.x + tx_off, top_rect.y + (24 if is_compact else 27)))

        # ------------------------------------------------------------------ #
        # 2. BAGIAN KIRI: [2] Serangan Kuat / Heavy Attack (Shortcut: 2)
        # ------------------------------------------------------------------ #
        bg_hvy = (64, 46, 26, 252) if is_hov_hvy else ((46, 32, 18, 245) if heavy_ready else (26, 22, 18, 220))
        bdr_hvy = config.COLOR_ACCENT_GOLD if is_hov_hvy else ((240, 170, 50) if heavy_ready else (100, 85, 70))
        draw_card(self.screen, left_rect, bg_hvy, border_color=bdr_hvy, border_radius=8)
        bg2_cx, bg2_cy = left_rect.x + (22 if is_compact else 25), left_rect.centery
        pygame.draw.circle(self.screen, (255, 165, 35) if is_hov_hvy else ((235, 145, 25) if heavy_ready else (120, 90, 50)), (bg2_cx, bg2_cy), badge_r)
        pygame.draw.circle(self.screen, (255, 245, 195) if heavy_ready else (140, 110, 70), (bg2_cx, bg2_cy), badge_r, 2)
        txt_2 = font_bubble.render("2", True, (255, 255, 255) if heavy_ready else (180, 170, 160))
        self.screen.blit(txt_2, txt_2.get_rect(center=(bg2_cx, bg2_cy)))
        t_hvy = font_bubble.render("Serangan Kuat", True, (255, 230, 110) if heavy_ready else config.COLOR_TEXT_MUTED)
        d_hvy_txt = "Dmg: 30-45 • Siap" if heavy_ready else f"Jeda CD: {st.player_heavy_cd} Giliran"
        d_hvy = font_tiny.render(d_hvy_txt, True, (245, 225, 200) if heavy_ready else config.COLOR_TEXT_MUTED)
        self.screen.blit(t_hvy, (left_rect.x + tx_off, left_rect.y + (5 if is_compact else 7)))
        self.screen.blit(d_hvy, (left_rect.x + tx_off, left_rect.y + (24 if is_compact else 27)))

        # ------------------------------------------------------------------ #
        # 3. BAGIAN KANAN: [3] Bertahan / Defense (Shortcut: 3)
        # ------------------------------------------------------------------ #
        bg_def = (38, 54, 82, 252) if is_hov_def else ((26, 38, 60, 245) if can_act else (20, 22, 28, 220))
        bdr_def = config.COLOR_ACCENT_GOLD if is_hov_def else ((105, 180, 255) if can_act else (70, 85, 105))
        draw_card(self.screen, right_rect, bg_def, border_color=bdr_def, border_radius=8)
        bg3_cx, bg3_cy = right_rect.x + (22 if is_compact else 25), right_rect.centery
        pygame.draw.circle(self.screen, (75, 145, 245) if is_hov_def else ((55, 125, 225) if can_act else (45, 52, 65)), (bg3_cx, bg3_cy), badge_r)
        pygame.draw.circle(self.screen, (225, 240, 255) if can_act else (110, 120, 140), (bg3_cx, bg3_cy), badge_r, 2)
        txt_3 = font_bubble.render("3", True, (255, 255, 255) if can_act else (175, 180, 190))
        self.screen.blit(txt_3, txt_3.get_rect(center=(bg3_cx, bg3_cy)))
        t_def = font_bubble.render("Bertahan", True, (165, 225, 255) if can_act else config.COLOR_TEXT_MUTED)
        d_def = font_tiny.render("-50% Dmg • Counter", True, (205, 225, 250) if can_act else config.COLOR_TEXT_MUTED)
        self.screen.blit(t_def, (right_rect.x + tx_off, right_rect.y + (5 if is_compact else 7)))
        self.screen.blit(d_def, (right_rect.x + tx_off, right_rect.y + (24 if is_compact else 27)))

        # ------------------------------------------------------------------ #
        # 4. BAGIAN BAWAH: [4] Gunakan Ramuan / Potion (Shortcut: 4)
        # ------------------------------------------------------------------ #
        pot_ready = can_act and (st.player_potions > 0)
        bg_pot = (62, 34, 72, 252) if is_hov_pot else ((44, 24, 52, 245) if pot_ready else (24, 20, 28, 220))
        bdr_pot = config.COLOR_ACCENT_GOLD if is_hov_pot else ((210, 110, 250) if pot_ready else (95, 75, 105))
        draw_card(self.screen, bot_rect, bg_pot, border_color=bdr_pot, border_radius=8)
        bg4_cx, bg4_cy = bot_rect.x + (22 if is_compact else 25), bot_rect.centery
        pygame.draw.circle(self.screen, (185, 90, 235) if is_hov_pot else ((165, 75, 215) if pot_ready else (55, 75, 120)), (bg4_cx, bg4_cy), badge_r)
        pygame.draw.circle(self.screen, (245, 220, 255) if pot_ready else (100, 115, 150), (bg4_cx, bg4_cy), badge_r, 2)
        txt_4 = font_bubble.render("4", True, (255, 255, 255) if pot_ready else (175, 185, 205))
        self.screen.blit(txt_4, txt_4.get_rect(center=(bg4_cx, bg4_cy)))
        t_pot = font_bubble.render("Gunakan Ramuan", True, (245, 185, 255) if pot_ready else config.COLOR_TEXT_MUTED)
        d_pot = font_tiny.render(f"x{st.player_potions} Botol (+25 HP)", True, (235, 210, 250) if pot_ready else config.COLOR_TEXT_MUTED)
        self.screen.blit(t_pot, (bot_rect.x + tx_off, bot_rect.y + (5 if is_compact else 7)))
        self.screen.blit(d_pot, (bot_rect.x + tx_off, bot_rect.y + (24 if is_compact else 27)))

        # ------------------------------------------------------------------ #
        # 2. Battle Log Box (Bagian Paling Bawah Arena, Lebar Penuh & Elegan)
        # ------------------------------------------------------------------ #
        log_h = 92 if h < 750 else 112
        log_y = h - log_h - 10
        log_x = panel_w + 16
        log_w = (bench_x - 12) - log_x

        self.battle_log_rect = pygame.Rect(log_x, log_y, log_w, log_h)
        draw_card(self.screen, self.battle_log_rect, (252, 249, 242, 245), border_color=(208, 196, 178), border_radius=8)

        ltitle = font_bubble.render("RIWAYAT PERTEMPURAN", True, config.COLOR_TEXT_PRIMARY)
        self.screen.blit(ltitle, (self.battle_log_rect.x + 12, self.battle_log_rect.y + 7))

        total_logs = len(self.battle_system.battle_logs)
        max_scroll = max(0, total_logs - 4)
        self.battle_log_scroll_offset = max(0, min(max_scroll, self.battle_log_scroll_offset))

        if total_logs > 4:
            end_idx = total_logs - self.battle_log_scroll_offset
            start_idx = max(0, end_idx - 4)
            display_logs = self.battle_system.battle_logs[start_idx:end_idx]
            pos_info = f"[{start_idx + 1}-{end_idx}/{total_logs}]"
        else:
            display_logs = self.battle_system.battle_logs
            pos_info = f"[{total_logs} aksi]" if total_logs > 0 else "[Awal]"

        info_surf = font_tiny.render(pos_info, True, config.COLOR_TEXT_SECONDARY)
        self.screen.blit(info_surf, (self.battle_log_rect.right - info_surf.get_width() - 58, self.battle_log_rect.y + 8))

        # Tombol panah scroll manual (▲ dan ▼)
        btn_w_scroll, btn_h_scroll = 20, 16
        self.btn_log_up = pygame.Rect(self.battle_log_rect.right - 50, self.battle_log_rect.y + 6, btn_w_scroll, btn_h_scroll)
        self.btn_log_down = pygame.Rect(self.battle_log_rect.right - 26, self.battle_log_rect.y + 6, btn_w_scroll, btn_h_scroll)

        up_col = (238, 230, 218) if self.battle_log_scroll_offset < max_scroll else (248, 245, 240)
        down_col = (238, 230, 218) if self.battle_log_scroll_offset > 0 else (248, 245, 240)

        draw_card(self.screen, self.btn_log_up, up_col, border_color=(205, 195, 180), border_radius=3)
        draw_card(self.screen, self.btn_log_down, down_col, border_color=(205, 195, 180), border_radius=3)

        ts_up = font_tiny.render("▲", True, config.COLOR_TEXT_PRIMARY if self.battle_log_scroll_offset < max_scroll else config.COLOR_TEXT_MUTED)
        ts_dn = font_tiny.render("▼", True, config.COLOR_TEXT_PRIMARY if self.battle_log_scroll_offset > 0 else config.COLOR_TEXT_MUTED)
        self.screen.blit(ts_up, (self.btn_log_up.centerx - ts_up.get_width() // 2, self.btn_log_up.centery - ts_up.get_height() // 2))
        self.screen.blit(ts_dn, (self.btn_log_down.centerx - ts_dn.get_width() // 2, self.btn_log_down.centery - ts_dn.get_height() // 2))

        ly = self.battle_log_rect.y + 28
        if display_logs:
            for log_line in display_logs:
                ts = font_sm.render(f"• {log_line}", True, config.COLOR_TEXT_PRIMARY)
                self.screen.blit(ts, (self.battle_log_rect.x + 12, ly))
                ly += 19
        else:
            ts = font_sm.render("• Pertarungan dimulai. Pilih tombol aksi di sebelah kiri untuk bertarung.", True, config.COLOR_TEXT_SECONDARY)
            self.screen.blit(ts, (self.battle_log_rect.x + 12, ly))

        if total_logs > 4 and max_scroll > 0:
            track_y = self.battle_log_rect.y + 26
            track_h = log_h - 32
            thumb_h = max(10, int(track_h * (4.0 / total_logs)))
            norm_pos = 1.0 - (self.battle_log_scroll_offset / float(max_scroll))
            thumb_y = track_y + int(norm_pos * (track_h - thumb_h))
            pygame.draw.rect(self.screen, (230, 222, 210), pygame.Rect(self.battle_log_rect.right - 5, track_y, 3, track_h), border_radius=1)
            pygame.draw.rect(self.screen, config.COLOR_ACCENT_GOLD, pygame.Rect(self.battle_log_rect.right - 5, thumb_y, 3, thumb_h), border_radius=1)

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
                if tree_data is not getattr(self, "_last_rendered_battle_tree", None):
                    self._last_rendered_battle_tree = tree_data
                    self.overlay.tree_overlay.set_tree(tree_data)
            self.overlay.tree_overlay.draw(self.screen)

    def _draw_battle_queue_deck(self, w: int, h: int):
        """Merender antrian kartu NPC cadangan secara vertikal di sebelah kanan layar (Trails of Cold Steel style).
        
        Sesuai referensi gambar:
        - Tersusun vertikal dari atas ke bawah
        - Ukuran compact (lebar ~148px)
        - Potret bulat (circular token) dengan ring warna sesuai kelas
        - Nama karakter, role badge, mini bar HP, dan badge status 'NEXT' atau 'KO'
        """
        if not self.current_squad or len(self.current_squad.members) <= 1:
            return

        bench_w = 148
        bench_x = w - bench_w - 12
        curr_y = 16

        # 1. Header Panel Cadangan
        hdr_rect = pygame.Rect(bench_x, curr_y, bench_w, 28)
        pygame.draw.rect(self.screen, (16, 20, 30, 235), hdr_rect, border_radius=6)
        pygame.draw.rect(self.screen, (65, 80, 110), hdr_rect, 1, border_radius=6)

        queue = [m for i, m in enumerate(self.current_squad.members) if i > self.current_squad.active_index]
        q_count = len(queue)
        hdr_title = f"CADANGAN ({q_count})"
        t_surf = self.fonts.get("bubble", self.fonts["sm"]).render(hdr_title, True, (255, 215, 75))
        self.screen.blit(t_surf, t_surf.get_rect(center=hdr_rect.center))
        curr_y += 34

        # 2. Daftar Petarung Cadangan yang Siap Masuk (Next Challengers)
        if queue:
            for depth, mem in enumerate(queue):
                is_next = (depth == 0)
                card_h = 52
                card_rect = pygame.Rect(bench_x, curr_y, bench_w, card_h)

                ctype_lower = mem.char_type.lower()
                if ctype_lower == "warrior":
                    role_color = (235, 145, 45)
                    role_tag = "WAR"
                elif ctype_lower == "ranger":
                    role_color = (52, 205, 105)
                    role_tag = "RNG"
                elif ctype_lower == "mage":
                    role_color = (70, 165, 255)
                    role_tag = "MAG"
                elif ctype_lower == "assassin":
                    role_color = (205, 75, 240)
                    role_tag = "ASN"
                else:
                    role_color = (190, 190, 200)
                    role_tag = "NPC"

                bg_col = (26, 32, 46, 245) if is_next else (18, 22, 32, 225)
                bdr_col = (255, 205, 60) if is_next else (55, 68, 92)
                pygame.draw.rect(self.screen, bg_col, card_rect, border_radius=8)
                pygame.draw.rect(self.screen, bdr_col, card_rect, 2 if is_next else 1, border_radius=8)

                # Potret bulat (Circular Portrait Token)
                p_radius = 17
                p_cx = bench_x + 8 + p_radius
                p_cy = curr_y + card_h // 2

                pygame.draw.circle(self.screen, (12, 15, 22), (p_cx, p_cy), p_radius)
                if mem.portrait:
                    p_img = pygame.transform.smoothscale(mem.portrait, (p_radius * 2 - 2, p_radius * 2 - 2))
                    self.screen.blit(p_img, (p_cx - p_radius + 1, p_cy - p_radius + 1))
                else:
                    # Gambar avatar kucing minimalis
                    ear_l = [(p_cx - 9, p_cy - 4), (p_cx - 4, p_cy - 13), (p_cx, p_cy - 5)]
                    ear_r = [(p_cx, p_cy - 5), (p_cx + 4, p_cy - 13), (p_cx + 9, p_cy - 4)]
                    pygame.draw.polygon(self.screen, role_color, ear_l)
                    pygame.draw.polygon(self.screen, role_color, ear_r)
                    pygame.draw.circle(self.screen, role_color, (p_cx, p_cy + 1), 9)

                pygame.draw.circle(self.screen, (255, 215, 80) if is_next else role_color, (p_cx, p_cy), p_radius, 2)

                info_x = p_cx + p_radius + 8
                name_short = mem.name.split()[0]
                txt_name = self.fonts["sm"].render(name_short, True, (255, 255, 255) if is_next else (205, 212, 225))
                self.screen.blit(txt_name, (info_x, curr_y + 6))

                if is_next:
                    next_badge = self.fonts.get("tiny", pygame.font.Font(None, 13)).render("NEXT", True, (20, 15, 5))
                    nb_w = next_badge.get_width() + 6
                    nb_rect = pygame.Rect(bench_x + bench_w - nb_w - 6, curr_y + 6, nb_w, 14)
                    pygame.draw.rect(self.screen, (255, 215, 75), nb_rect, border_radius=3)
                    self.screen.blit(next_badge, (nb_rect.x + 3, nb_rect.y + 1))
                else:
                    role_lbl = self.fonts.get("tiny", pygame.font.Font(None, 13)).render(role_tag, True, role_color)
                    self.screen.blit(role_lbl, (bench_x + bench_w - role_lbl.get_width() - 8, curr_y + 7))

                # Mini HP Bar
                bar_x = info_x
                bar_y = curr_y + 25
                bar_w = bench_x + bench_w - bar_x - 8
                bar_h = 5
                pygame.draw.rect(self.screen, (12, 14, 20), (bar_x, bar_y, bar_w, bar_h), border_radius=2)
                cur_hp = getattr(mem, "current_hp", mem.max_hp)
                hp_ratio = max(0.0, min(1.0, cur_hp / float(max(1, mem.max_hp))))
                fill_w = int(bar_w * hp_ratio)
                if fill_w > 0:
                    hp_col = (65, 205, 100) if hp_ratio > 0.4 else (235, 160, 45) if hp_ratio > 0.2 else (235, 65, 65)
                    pygame.draw.rect(self.screen, hp_col, (bar_x, bar_y, fill_w, bar_h), border_radius=2)

                hp_txt = self.fonts.get("tiny", pygame.font.Font(None, 13)).render(f"{cur_hp}/{mem.max_hp} HP", True, (160, 172, 192))
                self.screen.blit(hp_txt, (bar_x, curr_y + 34))

                curr_y += card_h + 8
        else:
            empty_rect = pygame.Rect(bench_x, curr_y, bench_w, 46)
            pygame.draw.rect(self.screen, (20, 24, 34, 220), empty_rect, border_radius=8)
            pygame.draw.rect(self.screen, (65, 78, 105), empty_rect, 1, border_radius=8)
            t_last = self.fonts["sm"].render("⚔️ Duel Terakhir!", True, (255, 215, 80))
            self.screen.blit(t_last, t_last.get_rect(center=empty_rect.center))
            curr_y += 54

        # 3. Status Petarung yang Telah Gugur (KO)
        defeated = [m for i, m in enumerate(self.current_squad.members) if i < self.current_squad.active_index]
        if defeated:
            for mem in defeated:
                d_rect = pygame.Rect(bench_x, curr_y, bench_w, 24)
                pygame.draw.rect(self.screen, (26, 16, 18, 220), d_rect, border_radius=5)
                pygame.draw.rect(self.screen, (100, 40, 45), d_rect, 1, border_radius=5)
                d_name = mem.name.split()[0]
                d_txt = self.fonts.get("tiny", pygame.font.Font(None, 13)).render(f"💀 {d_name} (KO)", True, (225, 110, 110))
                self.screen.blit(d_txt, (bench_x + 8, curr_y + 5))
                curr_y += 28

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

    def _on_npc_tactical_plan(self, warrior, defender, healer, heal_amount: int, plan_result):
        """Callback saat skuad NPC mengeksekusi rencana darurat PDDL (Materi 08)."""
        self.latest_plan_result = plan_result
        if hasattr(self, "planning_overlay") and self.planning_overlay:
            self.planning_overlay.latest_plan_result = plan_result
        if hasattr(self, "overlay") and hasattr(self.overlay, "nav_rail"):
            # Set badge notifikasi di Nav Rail (Tab 5: Planning)
            self.overlay.nav_rail.set_badge(5, active=True, color=config.COLOR_ACCENT_GOLD)
        (player_arena_x, char_y), (npc_arena_x, _) = self._get_battle_char_positions()
        if hasattr(self, "vfx") and self.vfx:
            # Efek perisai di NPC yang baru maju
            self.vfx.trigger_defend((npc_arena_x, char_y))

    def _draw_tactical_plan_banner(self, w: int, h: int, center_x: int):
        """Menggambar banner notifikasi taktis Automated Planning PDDL saat rotasi darurat skuad terjadi."""
        info = getattr(self.battle_system, "tactical_banner_info", None)
        if not info:
            return

        timer = getattr(self.battle_system, "tactical_banner_timer", 0.0)
        alpha = min(255, int(255 * (timer / 0.5))) if timer < 0.5 else 255

        is_dock_open = getattr(self.overlay.dock, "is_open", False) if hasattr(self, "overlay") and hasattr(self.overlay, "dock") else False
        panel_w = config.TOTAL_DOCK_WIDTH if is_dock_open else config.TOTAL_COLLAPSED_WIDTH
        usable_w = w - panel_w
        banner_w = min(560, usable_w - 40)
        banner_h = 86
        banner_x = center_x - banner_w // 2
        banner_y = 52

        surf = pygame.Surface((banner_w, banner_h), SRCALPHA)

        # Kartu dasar dengan border ganda & warna perkamen
        bg_color = (252, 248, 238, min(245, alpha))
        bd_color = (205, 145, 45, alpha)
        pygame.draw.rect(surf, bg_color, (0, 0, banner_w, banner_h), border_radius=10)
        pygame.draw.rect(surf, bd_color, (0, 0, banner_w, banner_h), 2, border_radius=10)

        # Header Badge
        font_tiny = self.fonts.get("tiny", pygame.font.Font(None, 13))

        # Badge pill judul taktik
        pill_rect = pygame.Rect(12, 8, banner_w - 24, 24)
        pygame.draw.rect(surf, (244, 232, 210, alpha), pill_rect, border_radius=12)
        pygame.draw.rect(surf, (215, 165, 75, alpha), pill_rect, 1, border_radius=12)

        hdr_txt = font_tiny.render("[TAKTIK PDDL] MATERI 08: AUTOMATED PLANNING", True, (165, 95, 15))
        surf.blit(hdr_txt, (pill_rect.centerx - hdr_txt.get_width() // 2, pill_rect.y + 4))

        # Konten langkah taktis
        w_name = info.get("warrior", "Warrior")
        d_name = info.get("defender", "Defender")
        h_name = info.get("healer", "Healer")
        h_amt = info.get("heal_amount", 35)

        line1 = f"* SwapRetreat: {w_name} mundur -> {d_name} maju pasang [DEFEND]!"
        line2 = f"* HealTeammate: {h_name} pulihkan {w_name} (+{h_amt} HP di cadangan)!"
        line3 = "Tekan [P] untuk melihat pohon rencana PDDL (Forward Progression A*)"

        s_l1 = font_tiny.render(line1, True, (45, 35, 25))
        s_l2 = font_tiny.render(line2, True, (35, 120, 65))
        s_l3 = font_tiny.render(line3, True, (135, 110, 85))

        surf.blit(s_l1, (18, 36))
        surf.blit(s_l2, (18, 52))
        surf.blit(s_l3, (banner_w - s_l3.get_width() - 16, 68))

        self.screen.blit(surf, (banner_x, banner_y))

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
        is_dock_open = getattr(self.overlay.dock, "is_open", False) if hasattr(self, "overlay") and hasattr(self.overlay, "dock") else False
        panel_w = config.TOTAL_DOCK_WIDTH if is_dock_open else config.TOTAL_COLLAPSED_WIDTH
        arena_w = w - panel_w
        area_cx = panel_w + arena_w // 2

        # Latar belakang arena hangat bertema Cozy Adventurer Journal
        self.battle_bg.draw(self.screen, panel_w, arena_w, h)
        warm_surf = pygame.Surface((arena_w, h), SRCALPHA)
        warm_surf.fill((46, 35, 25, 140))
        self.screen.blit(warm_surf, (panel_w, 0))

        font_huge = self.fonts.get("huge", self.fonts["title"])
        font_title = self.fonts.get("title", self.fonts["sm"])
        font_bubble = self.fonts.get("bubble", self.fonts["sm"])
        font_sm = self.fonts["sm"]
        font_tiny = self.fonts.get("tiny", font_sm)

        # Header Title
        t_surf = font_huge.render("PERSIAPAN PERTEMPURAN (PRE-BATTLE)", True, (255, 220, 95))
        self.screen.blit(t_surf, (area_cx - t_surf.get_width() // 2, 24))

        sub_txt = "Keseimbangan komposisi skuad lawan dioptimasi via CSP (MRV+LCV+AC-3) & Local Search"
        f_sub = font_sm if font_sm.size(sub_txt)[0] <= arena_w - 40 else font_tiny
        if f_sub.size(sub_txt)[0] > arena_w - 40:
            sub_txt = "Komposisi skuad lawan dioptimasi via CSP & Local Search"
            f_sub = font_tiny
        sub_surf = f_sub.render(sub_txt, True, (245, 235, 215))
        self.screen.blit(sub_surf, (area_cx - sub_surf.get_width() // 2, 58))

        # Sisi Kiri: Profil Player - Diperbesar mengisi space vertikal
        btn_h = 44
        btn_y = h - 68
        available_h = max(380, btn_y - 20 - 92)

        avail_w = arena_w - 44
        p_card_w = min(320, max(220, int(avail_w * 0.38)))
        p_card_h = available_h
        p_card_x = panel_w + 16
        p_card_y = 90
        p_card_rect = pygame.Rect(p_card_x, p_card_y, p_card_w, p_card_h)

        # Kartu Hero Utama Player (Putih Gading Cozy Journal)
        draw_card(self.screen, p_card_rect, (255, 255, 255, 245), border_color=(218, 206, 188), border_radius=10)

        p_header = font_title.render("Hero Utama (Player)", True, config.COLOR_TEXT_PRIMARY)
        self.screen.blit(p_header, (p_card_x + 14, p_card_y + 14))

        # Tampilan Sprite Bolu Besar & Heroik
        p_img = self.battle_sprites.get("player", self.player.sprite.current_image)
        p_aspect = p_img.get_width() / float(p_img.get_height())
        target_bolu_h = min(130, int(available_h * 0.28))
        target_bolu_w = min(p_card_w - 36, int(round(target_bolu_h * p_aspect)))
        p_big = pygame.transform.smoothscale(p_img, (target_bolu_w, target_bolu_h))
        self.screen.blit(p_big, p_big.get_rect(center=(p_card_x + p_card_w // 2, p_card_y + 36 + target_bolu_h // 2)))

        # Mini Bar HP Player
        hp_bar_y = p_card_y + 42 + target_bolu_h
        hp_bar_w = p_card_w - 28
        hp_bar_h = 16
        pygame.draw.rect(self.screen, (235, 226, 215), (p_card_x + 14, hp_bar_y, hp_bar_w, hp_bar_h), border_radius=4)
        hp_fill = int((self.player.persistent_hp / 100.0) * hp_bar_w)
        if hp_fill > 0:
            pygame.draw.rect(self.screen, (42, 138, 62), (p_card_x + 14, hp_bar_y, hp_fill, hp_bar_h), border_radius=4)
        pygame.draw.rect(self.screen, (190, 178, 160), (p_card_x + 14, hp_bar_y, hp_bar_w, hp_bar_h), 1, border_radius=4)
        hp_lbl = font_sm.render(f"HP: {self.player.persistent_hp} / 100", True, (255, 255, 255))
        self.screen.blit(hp_lbl, (p_card_x + 14 + (hp_bar_w - hp_lbl.get_width()) // 2, hp_bar_y + 1))

        py_stat = hp_bar_y + 24
        p_stats = [
            f"• Ramuan    : {self.player.persistent_potions} Botol (+25 HP)",
            f"• Serangan  : +{self.player.atk_bonus} ATK",
            f"• Ketahanan : +{self.player.def_bonus} DEF Flat",
            "• Karakter  : Petualang Tangguh",
        ]
        f_pstat = font_sm if (p_card_w >= 300 and font_sm.size(p_stats[0])[0] <= p_card_w - 30) else font_tiny
        for s in p_stats:
            self.screen.blit(f_pstat.render(s, True, config.COLOR_TEXT_PRIMARY), (p_card_x + 14, py_stat))
            py_stat += 20 if f_pstat == font_tiny else 22

        # Rincian Inventori Barang
        py_stat += 6
        self.screen.blit(font_bubble.render("Artefak & Perlengkapan:", True, config.COLOR_ACCENT_GOLD), (p_card_x + 14, py_stat))
        ix = p_card_x + 14
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
                    ix = p_card_x + 14
                    iy += 38
                icon = pygame.transform.smoothscale(self.item_images[img_key], (32, 32))
                self.screen.blit(icon, (ix, iy))
                ix += 38

        # Sisi Kanan: Profil Squad NPC Lawan (Putih Gading Cozy Journal)
        squad_area_x = p_card_rect.right + 12
        squad_area_w = avail_w - p_card_w

        sq_header = font_title.render("Skuad Lawan (CSP & Local Search)", True, (255, 220, 95))
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
                job_label = "WARRIOR"
                pill_bg = (254, 242, 225)
                pill_border = (225, 150, 50)
                pill_text_col = (185, 100, 20)
                trait_desc = "Ketahanan tinggi & seimbang"
            elif ctype_lower == "ranger":
                job_label = "RANGER"
                pill_bg = (232, 248, 235)
                pill_border = (65, 160, 85)
                pill_text_col = (35, 125, 55)
                trait_desc = "Pemanah lincah & akurat"
            elif ctype_lower == "mage":
                job_label = "MAGE"
                pill_bg = (230, 242, 255)
                pill_border = (75, 145, 220)
                pill_text_col = (25, 100, 180)
                trait_desc = "Spesialis sihir kehancuran"
            elif ctype_lower == "assassin":
                job_label = "ASSASSIN"
                pill_bg = (250, 235, 252)
                pill_border = (175, 85, 195)
                pill_text_col = (135, 50, 155)
                trait_desc = "Penyelinap & serangan kritis"
            else:
                job_label = ctype_lower.upper()
                pill_bg = (242, 238, 230)
                pill_border = (170, 155, 138)
                pill_text_col = (115, 98, 82)
                trait_desc = "Petarung tangguh tim AI"

            # Background Kartu Skuad
            draw_card(self.screen, m_rect, (255, 255, 255, 245), border_color=(218, 206, 188), border_radius=8)

            # Portrait Area Terdedikasi di Kiri Kartu (Mencegah Sprite Menabrak Teks)
            portrait_box = pygame.Rect(m_rect.x + 8, m_rect.y + 6, 62, member_card_h - 12)
            npc_thumb = m.battle_sprite or m.portrait
            if npc_thumb:
                asp = npc_thumb.get_width() / float(npc_thumb.get_height())
                max_sw = 58
                max_sh = member_card_h - 14
                thumb_h = min(max_sh, int(max_sw / asp)) if asp > 0 else max_sh
                thumb_w = int(round(thumb_h * asp))
                if thumb_w > max_sw:
                    thumb_w = max_sw
                    thumb_h = int(round(thumb_w / asp))
                p_icon = pygame.transform.smoothscale(npc_thumb, (thumb_w, thumb_h))
                self.screen.blit(p_icon, p_icon.get_rect(center=portrait_box.center))
            else:
                pygame.draw.rect(self.screen, (240, 234, 224), (m_rect.x + 8, m_rect.y + 8, 56, 56), border_radius=6)

            # Titik Awal Teks (tx dijamin bebas tabrakan dari sprite)
            tx = m_rect.x + 76
            ty = m_rect.y + max(6, (member_card_h - 84) // 2)
            max_txt_w = m_rect.right - tx - 10

            # Baris 1: Nama di kiri, Pill Badge Job di kanan
            pill_txt = font_tiny.render(job_label, True, pill_text_col)
            pill_w = pill_txt.get_width() + 10
            pill_h = 18
            pill_rect = pygame.Rect(m_rect.right - pill_w - 10, ty + 1, pill_w, pill_h)
            draw_card(self.screen, pill_rect, pill_bg, border_color=pill_border, border_radius=4)
            self.screen.blit(pill_txt, (pill_rect.x + 5, pill_rect.y + 1))

            name_avail_w = pill_rect.left - tx - 6
            full_name = f"{idx+1}. {m.name}"
            if font_title.size(full_name)[0] <= name_avail_w:
                t_name = font_title.render(full_name, True, config.COLOR_TEXT_PRIMARY)
            elif font_bubble.size(full_name)[0] <= name_avail_w:
                t_name = font_bubble.render(full_name, True, config.COLOR_TEXT_PRIMARY)
            else:
                short_name = f"{idx+1}. {m.name.split()[0]}"
                t_name = font_title.render(short_name, True, config.COLOR_TEXT_PRIMARY)
            self.screen.blit(t_name, (tx, ty))

            # Baris 2: Mini HP Bar (Warna Coral Konsisten) & Potions
            txt_hp = font_tiny.render(f"{m.max_hp} HP │ {m.potions} Potion", True, config.COLOR_TEXT_PRIMARY)
            m_hp_w = min(90, max(45, max_txt_w - txt_hp.get_width() - 10))
            m_hp_y = ty + 24
            pygame.draw.rect(self.screen, (235, 226, 215), (tx, m_hp_y, m_hp_w, 12), border_radius=3)
            m_fill = max(0, min(m_hp_w, int((m.max_hp / 120.0) * m_hp_w)))
            pygame.draw.rect(self.screen, (215, 65, 55), (tx, m_hp_y, m_fill, 12), border_radius=3)
            self.screen.blit(txt_hp, (tx + m_hp_w + 8, m_hp_y - 2))

            # Baris 3: ATK, DEF, dan Profil AI (Rapi & Kompak)
            line3 = f"+{m.atk_bonus} ATK │ +{m.def_bonus} DEF │ {m.eval_profile}"
            self.screen.blit(font_tiny.render(line3, True, config.COLOR_TEXT_SECONDARY), (tx, ty + 42))

            # Baris 4: Deskripsi Karakteristik (Tidak Melebihi Batas Kartu)
            self.screen.blit(font_tiny.render(trait_desc, True, (135, 118, 102)), (tx, ty + 60))

            m_y += member_card_h + gap

        # Bagian Bawah: 4 Tombol CTA Interaktif di Dasar Layar
        avail_btn_w = arena_w - 40
        btn_gap = 10
        btn_w = max(110, min(185, (avail_btn_w - 3 * btn_gap) // 4))
        total_w = 4 * btn_w + 3 * btn_gap
        start_x = panel_w + (arena_w - total_w) // 2

        self.btn_pre_battle_inspect = pygame.Rect(start_x, btn_y, btn_w, btn_h)
        self.btn_pre_battle_start = pygame.Rect(start_x + (btn_w + btn_gap), btn_y, btn_w, btn_h)
        self.btn_pre_battle_reroll = pygame.Rect(start_x + 2 * (btn_w + btn_gap), btn_y, btn_w, btn_h)
        self.btn_pre_battle_cancel = pygame.Rect(start_x + 3 * (btn_w + btn_gap), btn_y, btn_w, btn_h)

        # 1. Tombol Buka Pohon CSP & Optimasi [T]
        draw_card(self.screen, self.btn_pre_battle_inspect, (244, 248, 255), border_color=(70, 130, 210), border_radius=6)
        # 2. Tombol Mulai Duel [SPASI]
        draw_card(self.screen, self.btn_pre_battle_start, (42, 138, 62), border_color=(30, 110, 48), border_radius=6)
        # 3. Tombol Acak Ulang [R]
        draw_card(self.screen, self.btn_pre_battle_reroll, (205, 135, 25), border_color=(175, 110, 15), border_radius=6)
        # 4. Tombol Batal [ESC]
        draw_card(self.screen, self.btn_pre_battle_cancel, (115, 98, 82), border_color=(88, 72, 60), border_radius=6)

        t_inspect_txt = "[T] Pohon CSP & LS" if btn_w >= 145 else "[T] Pohon CSP"
        t_inspect = font_bubble.render(t_inspect_txt, True, (25, 85, 160))
        t_start = font_bubble.render("[SPASI] Mulai Duel", True, (255, 255, 255))
        t_reroll = font_bubble.render("[R] Acak Ulang", True, (255, 255, 255))
        t_cancel = font_bubble.render("[ESC] Kembali", True, (255, 255, 255))

        self.screen.blit(t_inspect, (self.btn_pre_battle_inspect.centerx - t_inspect.get_width() // 2, self.btn_pre_battle_inspect.centery - t_inspect.get_height() // 2))
        self.screen.blit(t_start, (self.btn_pre_battle_start.centerx - t_start.get_width() // 2, self.btn_pre_battle_start.centery - t_start.get_height() // 2))
        self.screen.blit(t_reroll, (self.btn_pre_battle_reroll.centerx - t_reroll.get_width() // 2, self.btn_pre_battle_reroll.centery - t_reroll.get_height() // 2))
        self.screen.blit(t_cancel, (self.btn_pre_battle_cancel.centerx - t_cancel.get_width() // 2, self.btn_pre_battle_cancel.centery - t_cancel.get_height() // 2))

        # Notifikasi visual saat Re-Roll berhasil dijalankan
        if self.reroll_toast_timer > 0:
            toast_text = "Skuad NPC berhasil diperbarui & dioptimasi."
            toast_surf = font_bubble.render(toast_text, True, (255, 255, 255))
            tw = toast_surf.get_width() + 28
            th = 28
            toast_rect = pygame.Rect(area_cx - tw // 2, btn_y - 34, tw, th)
            draw_card(self.screen, toast_rect, (42, 138, 62), border_color=(30, 110, 48), border_radius=6)
            self.screen.blit(toast_surf, (toast_rect.centerx - toast_surf.get_width() // 2, toast_rect.centery - toast_surf.get_height() // 2))

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
                    prompt = self.fonts.get("bubble", self.fonts["sm"]).render("[E] Buka Peti", True, (255, 255, 255))
                    p_box = prompt.get_rect(center=(rect.centerx, rect.top - 16))
                    card = pygame.Surface((p_box.width + 12, p_box.height + 6), SRCALPHA)
                    card.fill((20, 24, 34, 230))
                    pygame.draw.rect(card, (255, 205, 50), card.get_rect(), 1, border_radius=4)
                    self.screen.blit(card, card.get_rect(center=p_box.center))
                    self.screen.blit(prompt, p_box)

    def _draw_obtained_items_hud(self):
        """Menampilkan panel HUD item yang didapat di bagian bawah kiri layar map (mode searching)."""
        w, h = self.screen.get_size()
        is_dock_open = getattr(self.overlay.dock, "is_open", False) if hasattr(self, "overlay") and hasattr(self.overlay, "dock") else False
        panel_w = config.TOTAL_DOCK_WIDTH if is_dock_open else config.TOTAL_COLLAPSED_WIDTH
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
        t_surf = font_bubble.render(title_text, True, (42, 32, 25))
        c_surf = font_sm.render(count_text, True, (145, 120, 95))

        bonuses = []
        if self.player.atk_bonus > 0:
            bonuses.append(f"ATK +{self.player.atk_bonus}")
        if self.player.def_bonus > 0:
            bonuses.append(f"DEF +{self.player.def_bonus}")
        b_surf = font_tiny.render(" • ".join(bonuses), True, (185, 110, 18)) if bonuses else None

        header_req_w = t_surf.get_width() + c_surf.get_width() + 16
        if b_surf:
            header_req_w += b_surf.get_width() + 20

        slots_total_w = slot_count * slot_w + (slot_count - 1) * slot_gap
        min_hud_w = 260
        hud_w = max(min_hud_w, slots_total_w + pad_x * 2, header_req_w + pad_x * 2)
        hud_y = h - hud_h - 14

        # 1. Background Container Card (Cozy Adventurer Journal Tone)
        shadow_surf = pygame.Surface((hud_w, hud_h), SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 30), (0, 0, hud_w, hud_h), border_radius=10)
        self.screen.blit(shadow_surf, (hud_x + 2, hud_y + 2))

        card_surf = pygame.Surface((hud_w, hud_h), SRCALPHA)
        card_surf.fill((255, 253, 248, 242))
        pygame.draw.rect(card_surf, (215, 202, 184), card_surf.get_rect(), 1, border_radius=10)
        pygame.draw.line(card_surf, (255, 255, 255, 220), (8, 1), (hud_w - 8, 1), 1)
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
                    "color": (210, 160, 45),
                })
                item_key = meta["key"]

                # Background slot terisi (Krem Hangat)
                s_bg = pygame.Surface((slot_w, slot_h), SRCALPHA)
                s_bg.fill((248, 243, 233, 230))
                self.screen.blit(s_bg, (sx, sy))

                # Border slot
                slot_col = meta.get("color", (210, 180, 120))
                pygame.draw.rect(self.screen, slot_col, slot_rect, 1, border_radius=6)

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
                s_bg.fill((242, 236, 225, 180))
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
        panel_w = config.TOTAL_DOCK_WIDTH if is_dock_open else config.TOTAL_COLLAPSED_WIDTH
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
        if hasattr(self, "inter_npc_manager") and self.inter_npc_manager:
            chest_idx = 0
            if chest in self.chests:
                chest_idx = self.chests.index(chest)
            self.inter_npc_manager.on_chest_opened(chest_idx, chest.get("item", "health_potion"))

        # 2. Trigger Automated Planning (Materi 08: Classical Planning STRIPS)
        if hasattr(self, "forward_planner") and self.forward_planner:
            chest_idx = 0
            if chest in self.chests:
                chest_idx = self.chests.index(chest)
            chest_tag = "A" if chest_idx == 0 else ("B" if chest_idx == 1 else ("C" if chest_idx == 2 else "D"))
            s0_p, goal_p, actions_p = create_world_patrol_problem(chest_tag)
            self.latest_plan_result = self.forward_planner.plan(s0_p, goal_p, actions_p)
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

        # Label Nama & Defend Status dengan badge kontras tinggi
        def_str = " [DEFENDING]" if is_defending else ""
        name_font = self.fonts.get("bubble", self.fonts["sm"])
        name_color = (255, 230, 100) if is_defending else (255, 255, 255)
        name_surf = name_font.render(f"{name}{def_str}", True, name_color)
        name_rect = name_surf.get_rect(midbottom=(cx, cy - 6))
        pill_rect = name_rect.inflate(14, 6)
        pill_surf = pygame.Surface(pill_rect.size, SRCALPHA)
        pill_surf.fill((16, 20, 30, 200))
        pygame.draw.rect(pill_surf, (55, 65, 85, 220), pill_surf.get_rect(), 1, border_radius=4)
        self.screen.blit(pill_surf, pill_rect.topleft)
        self.screen.blit(name_surf, name_rect.topleft)

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

        # Teks Angka HP + Cooldown info dengan badge kontras tinggi
        hp_text = f"{hp} / {max_hp} HP  │  Pot: {potions}{cd_text}"
        ts_hp = self.fonts["sm"].render(hp_text, True, (240, 245, 255))
        hp_rect = ts_hp.get_rect(midtop=(cx, cy + bar_h + 5))
        hp_pill = hp_rect.inflate(14, 6)
        hp_pill_surf = pygame.Surface(hp_pill.size, SRCALPHA)
        hp_pill_surf.fill((16, 20, 30, 200))
        pygame.draw.rect(hp_pill_surf, (55, 65, 85, 220), hp_pill_surf.get_rect(), 1, border_radius=4)
        self.screen.blit(hp_pill_surf, hp_pill.topleft)
        self.screen.blit(ts_hp, hp_rect.topleft)

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
        """Menggambar rumput, bunga, dan semak yang bergoyang lembut tertiup angin."""
        fol = getattr(self.map, "foliage", {})
        zoom = self.camera.zoom
        sf = getattr(self, "_scaled_foliage", {})
        tile_cache = getattr(self, "_scaled_foliage_tiles", {})

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
                sway_x = math.sin(self.wind_timer * 3.4 + fx * 1.1 + fy * 0.4) * (1.0 * zoom)
                wx, wy = fx * 16, fy * 16
                sx, sy = self.camera.world_to_screen(wx, wy)
                self.screen.blit(img, (int(sx + sway_x), int(sy)))

        # 3. Kepala Bunga Matahari
        scaled_sunflower = sf.get("sunflower")
        if scaled_sunflower:
            for sx_grid, sy_grid in fol.get("sunflowers", []):
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
                sway_x = math.sin(self.wind_timer * 2.8 + ax_grid * 0.9 + ay_grid * 0.5) * (1.2 * zoom)
                wx, wy = ax_grid * 16, ay_grid * 16
                sx, sy = self.camera.world_to_screen(wx, wy)
                self.screen.blit(img, (int(sx + sway_x), int(sy)))

        # 5. Semak bulat (kompatibilitas map lama jika ada)
        scaled_bush = sf.get("bush")
        if scaled_bush:
            for bx, by in fol.get("bushes", []):
                sway_x = math.sin(self.wind_timer * 2.8 + bx * 0.9) * (1.0 * zoom)
                wx, wy = bx * 16, by * 16
                sx, sy = self.camera.world_to_screen(wx, wy)
                self.screen.blit(scaled_bush, (int(sx + sway_x), int(sy)))

    def _draw_swaying_tree_canopies(self):
        """Menggambar kanopi daun pohon yang melambai tertiup angin (di atas batang pohon & karakter)."""
        fol = getattr(self.map, "foliage", {})
        zoom = self.camera.zoom
        sf = getattr(self, "_scaled_foliage", {})

        scaled_green = sf.get("tree")
        scaled_pink = sf.get("tree_pink") or scaled_green
        scaled_small = sf.get("tree_small")

        if scaled_green:
            for tx, ty in fol.get("trees", []):
                sway_x = math.sin(self.wind_timer * 2.2 + tx * 0.6) * (1.5 * zoom)
                wx = tx * 16
                wy = ty * 16
                sx, sy = self.camera.world_to_screen(wx, wy)
                self.screen.blit(scaled_green, (int(sx + sway_x), int(sy)))

        if scaled_pink:
            for tx, ty in fol.get("trees_pink", []):
                sway_x = math.sin(self.wind_timer * 2.2 + tx * 0.6) * (1.5 * zoom)
                wx = tx * 16
                wy = ty * 16
                sx, sy = self.camera.world_to_screen(wx, wy)
                self.screen.blit(scaled_pink, (int(sx + sway_x), int(sy)))

        if scaled_small:
            for tx, ty in fol.get("trees_small", []):
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

    def _draw_sprite(self, sprite, wx, wy):
        sx, sy = self.camera.world_to_screen(wx, wy)
        nw = max(1, int(round(sprite.get_width() * self.camera.zoom)))
        nh = max(1, int(round(sprite.get_height() * self.camera.zoom)))
        # Nearest-Neighbor scaling untuk sprite karakter (bebas burik & tajam)
        sprite = pygame.transform.scale(sprite, (nw, nh))
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
        """Merender modal dialog rampasan perang di tengah arena battle dengan tema Cozy Warm Parchment."""
        if not self.loot_modal:
            return

        from .ui.components import fit_text_to_width

        modal = self.loot_modal
        loot = modal["loot"]
        old_npc = modal.get("old_npc")
        is_final = modal.get("is_final", False)

        w, h = self.screen.get_size()
        is_dock_open = getattr(self.overlay.dock, "is_open", False) if hasattr(self, "overlay") and hasattr(self.overlay, "dock") else False
        panel_w = config.TOTAL_DOCK_WIDTH if is_dock_open else config.NAV_RAIL_WIDTH
        has_bench = bool(self.current_squad and len(self.current_squad.members) > 1)
        bench_w = 154 if has_bench else 16
        combat_w = w - panel_w - bench_w
        cx = panel_w + combat_w // 2
        cy = h // 2

        # 1. Background Overlay (Warm Parchment Vignette Backdrop)
        dim_surf = pygame.Surface((w, h), SRCALPHA)
        dim_surf.fill((22, 16, 12, 165))
        self.screen.blit(dim_surf, (0, 0))

        # 2. Dimensi & Posisi Modal Card di Tengah Arena Battle
        mw, mh = 560, 416
        mx, my = cx - mw // 2, cy - mh // 2
        modal_rect = pygame.Rect(mx, my, mw, mh)

        # Shadow
        shadow_surf = pygame.Surface((mw, mh), SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 45), (0, 0, mw, mh), border_radius=14)
        self.screen.blit(shadow_surf, (mx + 3, my + 4))

        # Warm Parchment Card Body
        card_surf = pygame.Surface((mw, mh), SRCALPHA)
        card_surf.fill((252, 248, 240, 253))

        theme_col = loot.get("color", config.COLOR_ACCENT_GOLD)
        pygame.draw.rect(card_surf, (168, 140, 102), (0, 0, mw, mh), 2, border_radius=14)
        pygame.draw.rect(card_surf, (235, 222, 204), (2, 2, mw - 4, mh - 4), 1, border_radius=12)

        font_title = self.fonts.get("title", self.fonts.get("bubble"))
        font_bubble = self.fonts.get("bubble", self.fonts["sm"])
        font_sm = self.fonts["sm"]

        # 3. Header Badge: RAMPASAN PERANG DIPEROLEH!
        badge_w, badge_h = 360, 32
        badge_rect = pygame.Rect((mw - badge_w) // 2, 16, badge_w, badge_h)
        pygame.draw.rect(card_surf, (244, 234, 216), badge_rect, border_radius=6)
        pygame.draw.rect(card_surf, (195, 145, 55), badge_rect, 1, border_radius=6)

        hdr_txt = font_bubble.render("RAMPASAN PERANG DIPEROLEH!", True, (165, 110, 20))
        card_surf.blit(hdr_txt, hdr_txt.get_rect(center=badge_rect.center))

        # 4. Sub-teks Info Lawan Gugur
        if old_npc:
            sub_str = f"Bolu berhasil menumbangkan {old_npc.name}!"
        else:
            sub_str = "Kemenangan gemilang di medan pertempuran!"
        sub_fit = fit_text_to_width(font_sm, sub_str, mw - 40)
        sub_txt = font_sm.render(sub_fit, True, (115, 95, 80))
        card_surf.blit(sub_txt, sub_txt.get_rect(center=(mw // 2, 60)))

        # 5. Bingkai Showcase Item (Icon Frame di Tengah)
        frame_sz = 96
        frame_rect = pygame.Rect((mw - frame_sz) // 2, 78, frame_sz, frame_sz)
        pygame.draw.rect(card_surf, (245, 240, 230), frame_rect, border_radius=12)
        pygame.draw.rect(card_surf, (205, 185, 160), frame_rect, 2, border_radius=12)

        # Gambar Item Besar
        img_key = loot.get("image_key", "item_sword")
        item_img = None
        if hasattr(self, "item_images_large") and img_key in self.item_images_large:
            item_img = self.item_images_large[img_key]
        elif img_key in self.item_images:
            item_img = pygame.transform.smoothscale(self.item_images[img_key], (76, 76))

        if item_img:
            card_surf.blit(item_img, item_img.get_rect(center=frame_rect.center))

        # 6. Nama Item Rampasan
        item_name = loot.get("name", "Artefak Misterius")
        name_fit = fit_text_to_width(font_title, item_name, mw - 40)
        name_txt = font_title.render(name_fit, True, (42, 30, 20))
        card_surf.blit(name_txt, name_txt.get_rect(center=(mw // 2, 196)))

        # 7. Badge Stat Boost (+ATK / +DEF / Pulihkan HP)
        stat_w, stat_h = 360, 32
        stat_rect = pygame.Rect((mw - stat_w) // 2, 222, stat_w, stat_h)
        pygame.draw.rect(card_surf, (235, 248, 238), stat_rect, border_radius=6)
        pygame.draw.rect(card_surf, (135, 205, 160), stat_rect, 1, border_radius=6)

        stat_str = f"BONUS STAT: {loot.get('stat_text', '+Stat')}"
        stat_fit = fit_text_to_width(font_bubble, stat_str, stat_w - 20)
        stat_txt = font_bubble.render(stat_fit, True, (30, 130, 65))
        card_surf.blit(stat_txt, stat_txt.get_rect(center=stat_rect.center))

        # 8. Deskripsi Efek Item (Bebas Overflow & Rapi dengan Multi-line Wrapping)
        desc_str = loot.get("desc", "")
        words = desc_str.split(" ")
        desc_lines = []
        cur_l = []
        max_desc_w = mw - 60
        for w_tok in words:
            cand = " ".join(cur_l + [w_tok])
            if font_sm.size(cand)[0] <= max_desc_w:
                cur_l.append(w_tok)
            else:
                if cur_l:
                    desc_lines.append(" ".join(cur_l))
                cur_l = [w_tok]
        if cur_l:
            desc_lines.append(" ".join(cur_l))

        line_h = 20
        total_desc_h = len(desc_lines) * line_h
        desc_center_y = 282
        start_y = desc_center_y - (total_desc_h // 2) + 10
        for i, line_text in enumerate(desc_lines):
            l_fit = fit_text_to_width(font_sm, line_text, max_desc_w)
            l_txt = font_sm.render(l_fit, True, (65, 52, 42))
            card_surf.blit(l_txt, l_txt.get_rect(center=(mw // 2, start_y + i * line_h)))

        # 9. Tombol Interaktif / Petunjuk Tekan ENTER
        btn_w, btn_h = 480, 38
        btn_rect = pygame.Rect((mw - btn_w) // 2, mh - 54, btn_w, btn_h)

        btn_bg = (42, 138, 76) if not is_final else (38, 110, 185)
        btn_bdr = (115, 210, 150) if not is_final else (120, 190, 250)
        pygame.draw.rect(card_surf, btn_bg, btn_rect, border_radius=8)
        pygame.draw.rect(card_surf, btn_bdr, btn_rect, 1, border_radius=8)

        prompt_str = "Tekan [ENTER] / [SPASI] untuk Lawan Berikutnya" if not is_final else "Tekan [ENTER] / [SPASI] untuk Selesaikan Duel"
        p_fit = fit_text_to_width(font_bubble, prompt_str, btn_w - 20)
        p_txt = font_bubble.render(p_fit, True, (255, 255, 255))
        card_surf.blit(p_txt, p_txt.get_rect(center=btn_rect.center))

        # Blit Modal Card ke Layar
        self.screen.blit(card_surf, modal_rect)