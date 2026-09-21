"""Player (kucing Bolu): port dari Scripts/player/player.gd.

Pergerakan per-ubin dengan animasi tween 0.12 detik. Posisi grid berubah
seketika saat tombol ditekan (bukan setelah animasi selesai), setara Godot.
"""

from . import config


class Player:
    def __init__(self, map_data, events):
        self.map = map_data
        self.events = events

        self.grid = (0, 0)
        self.px = 0.0
        self.py = 0.0
        self.moving = False
        self.move_t = 0.0
        self.frame_from = (0.0, 0.0)
        self.frame_to = (0.0, 0.0)

        self.call_bubble_visible = False
        self.call_bubble_timer = 0.0

        preferred_spawn = self.map.get_map_center()
        self.grid = self.map.get_valid_spawn_point(preferred_spawn)
        self.px, self.py = self.map.world_to_px(self.grid)
        self.frame_from = (self.px, self.py)
        self.frame_to = (self.px, self.py)

        self.events.emit_player_moved(self.grid)

    # ------------------------------------------------------------------ #
    def _start_move(self):
        target_px, target_py = self.map.world_to_px(self.grid)
        self.frame_from = (self.px, self.py)
        self.frame_to = (target_px, target_py)
        self.move_t = 0.0
        self.moving = True

    def update(self, dt):
        if self.moving:
            self.move_t += dt / config.PLAYER_MOVE_DURATION
            if self.move_t >= 1.0:
                self.move_t = 1.0
                self.moving = False
            ease = self.move_t * self.move_t * (3.0 - 2.0 * self.move_t)  # smoothstep
            self.px = self.frame_from[0] + (self.frame_to[0] - self.frame_from[0]) * ease
            self.py = self.frame_from[1] + (self.frame_to[1] - self.frame_from[1]) * ease
            if not self.moving:
                self.px, self.py = self.frame_to
                self.events.emit_player_moved(self.grid)

        if self.call_bubble_visible:
            self.call_bubble_timer -= dt
            if self.call_bubble_timer <= 0.0:
                self.call_bubble_visible = False

    # ------------------------------------------------------------------ #
    def try_move(self, direction):
        if self.moving:
            return False

        target = (self.grid[0] + direction[0], self.grid[1] + direction[1])
        if self.map.is_walkable(target):
            self.grid = target
            self.events.emit_player_moved(self.grid)
            self._start_move()
            return True
        return False

    # ------------------------------------------------------------------ #
    def show_call_bubble(self):
        self.call_bubble_visible = True
        self.call_bubble_timer = config.CALL_BUBBLE_TIME

    def hide_call_bubble(self):
        self.call_bubble_visible = False