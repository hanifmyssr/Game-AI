"""GameManager: pusat event yang meniru Autoload GameManager.gd di Godot."""


class GameManager:
    def __init__(self):
        self.debug_overlay = None
        self._player_moved_listeners = []
        self._algorithm_changed_listeners = []

    def register_overlay(self, overlay):
        self.debug_overlay = overlay
        print("GameManager: Debug Overlay berhasil diregistrasi.")

    def subscribe_player_moved(self, fn):
        self._player_moved_listeners.append(fn)

    def emit_player_moved(self, grid_pos):
        for fn in list(self._player_moved_listeners):
            fn(grid_pos)

    def subscribe_algorithm_changed(self, fn):
        self._algorithm_changed_listeners.append(fn)

    def emit_algorithm_changed(self, algo_name):
        for fn in list(self._algorithm_changed_listeners):
            fn(algo_name)

    def path_calculated(self, path, visited, time_ms):
        if self.debug_overlay is not None:
            self.debug_overlay.update_debug_data(visited, path, time_ms)