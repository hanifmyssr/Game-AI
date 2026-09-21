"""App: main loop + kamera + rendering, port dari Scenes/main.tscn.

Meniru struktur scene Godot: Map -> player, npc, DebugOverlay.
"""

import os

import pygame

from . import config
from .events import GameManager
from .mapdata import MapData
from .overlay import DebugOverlay
from .player import Player
from .npc import NPC


class Camera:
    """Kamera contain-fit yang memusatkan peta pada layar (mirip camera_anchor.gd)."""

    def __init__(self, win_w, win_h, map_w, map_h, margin=0.02):
        self.zoom = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.reset(win_w, win_h, map_w, map_h, margin)

    def reset(self, win_w, win_h, map_w, map_h, margin=0.02):
        self.zoom = min(win_w / map_w, win_h / map_h) * (1.0 - margin)
        self.offset_x = (win_w - map_w * self.zoom) / 2.0
        self.offset_y = (win_h - map_h * self.zoom) / 2.0

    def world_to_screen(self, wx, wy):
        return (wx * self.zoom + self.offset_x, wy * self.zoom + self.offset_y)


class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(
            (config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.RESIZABLE
        )
        pygame.display.set_caption("BoluKesepian - Port Python (A* & UCS)")
        self.clock = pygame.time.Clock()
        self.running = True

        self.fonts = self._build_fonts()

        self.map = MapData()
        self.events = GameManager()

        self.overlay = DebugOverlay(self.events, self.fonts)

        self.player = Player(self.map, self.events)
        self.npc = NPC(self.map, self.events, self.player)

        self.events.subscribe_player_moved(self.npc.on_player_moved)
        self.events.subscribe_algorithm_changed(self.npc.set_algorithm)

        self.map_surface = None
        self.map_w, self.map_h = self.map.map_px_size()

        self.player_sprite = self._load_character("player.png")
        self.npc_sprite = self._load_character("npc.png")

        self._apply_viewport()

        # hitung jalur awal setelah seluruh pipeline siap
        self.npc.find_path(self.player.grid)

    # ------------------------------------------------------------------ #
    def _build_fonts(self):
        fonts = {}
        try:
            fonts["sm"] = pygame.font.SysFont(["consolas", "segoeui", "arial"], 15)
            fonts["bubble"] = pygame.font.SysFont(["consolas", "segoeui", "arial"], 14, bold=True)
            fonts["title"] = pygame.font.SysFont(["segoeui", "arial"], 18, bold=True)
        except Exception:
            fonts["sm"] = pygame.font.Font(None, 22)
            fonts["bubble"] = pygame.font.Font(None, 26)
            fonts["title"] = pygame.font.Font(None, 28)
        return fonts

    def _load_character(self, name):
        path = os.path.join(config.ASSET_DIR, name)
        img = pygame.image.load(path).convert_alpha()
        size = int(64 * config.CHARACTER_SCALE)
        return pygame.transform.smoothscale(img, (size, size))

    def _apply_viewport(self):
        w, h = self.screen.get_size()
        self.camera = Camera(w, h, self.map_w, self.map_h)
        if self.map_surface is None:
            combined = pygame.Surface((self.map_w, self.map_h))
            combined.blit(self.map.ground_surface, (0, 0))
            combined.blit(self.map.obstacle_surface, (0, 0))
            self.map_surface = combined
        self.scaled_map = pygame.transform.smoothscale(
            self.map_surface, (int(self.map_w * self.camera.zoom), int(self.map_h * self.camera.zoom))
        )
        self.map_offset = (int(self.camera.offset_x), int(self.camera.offset_y))

    # ------------------------------------------------------------------ #
    def run(self):
        while self.running:
            dt = self.clock.tick(config.FPS) / 1000.0
            self._handle_events()
            self.player.update(dt)
            self.npc.update(dt)
            self._draw()
        pygame.quit()

    # ------------------------------------------------------------------ #
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                self._apply_viewport()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.overlay.handle_event(event)
            elif event.type == pygame.KEYDOWN:
                self._handle_key(event.key)

    def _handle_key(self, key):
        mapping = {
            pygame.K_UP: (0, -1),
            pygame.K_w: (0, -1),
            pygame.K_DOWN: (0, 1),
            pygame.K_s: (0, 1),
            pygame.K_LEFT: (-1, 0),
            pygame.K_a: (-1, 0),
            pygame.K_RIGHT: (1, 0),
            pygame.K_d: (1, 0),
        }
        if key in mapping:
            self.player.try_move(mapping[key])
        elif key == pygame.K_SPACE:
            if not self.npc.chasing:
                self.player.show_call_bubble()
            self.npc.toggle_chase()
        elif key == pygame.K_ESCAPE:
            self.running = False

    # ------------------------------------------------------------------ #
    def _draw(self):
        self.screen.fill(config.BG_COLOR)
        self.screen.blit(self.scaled_map, self.map_offset)

        self.overlay.draw_world(self.screen, self.camera, self.map, self.npc, self.player)

        self._draw_sprite(self.player_sprite, self.player.px, self.player.py)
        self._draw_sprite(self.npc_sprite, self.npc.px, self.npc.py)

        if self.player.call_bubble_visible:
            self._draw_call_bubble()

        self.overlay.draw_ui(self.screen)
        pygame.display.flip()

    def _draw_sprite(self, sprite, wx, wy):
        sx, sy = self.camera.world_to_screen(wx, wy)
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