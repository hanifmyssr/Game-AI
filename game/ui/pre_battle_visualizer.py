"""Pre-Battle AI Visualizer: Modal Overlay Interaktif untuk Pohon CSP & Trajectory Local Search.

Fitur:
1. Tab 1: Pohon Keputusan CSP (Backtracking, MRV Variable Selection, LCV Value Ordering,
   Pruning Unary/Binary C1-C8, Dead-end Backtrack, dan Jalur Solusi Lengkap).
2. Tab 2: Trajectory Local Search & Konvergensi (Hill Climbing, Sideways, Random Restart,
   Simulated Annealing, Genetic Algorithm) dengan grafik fitness vs iterasi dan preview skuad live.
3. Kontrol Timeline Animasi: Play/Pause, Step Back/Forward, Scrubber Slider, Kecepatan (0.5x - Instant).
4. Navigasi Kanvas: Drag untuk Pan, Mouse Wheel untuk Zoom halus tanpa patah.
5. Visual Rendering: Kurva Bezier halus anti-aliased (tanpa sudut tajam) dan kotak rounded anti-overlap.
"""

import math
import copy
import pygame
from typing import Dict, List, Tuple, Any, Optional

SRCALPHA = getattr(pygame, "SRCALPHA", 0x00010000)

# Palet Warna: 2 warna inti (Slate gelap + Warm Sand) + 1 aksen (Teal)
# Mengikuti antislop-ui R-29: cap 2-3 core + 1 accent.
COLOR_MODAL_BG = (18, 22, 32, 245)
COLOR_MODAL_BORDER = (52, 65, 88)
COLOR_HEADER_BG = (22, 28, 40, 255)
COLOR_TAB_ACTIVE_BG = (38, 130, 128)
COLOR_TAB_ACTIVE_TXT = (240, 245, 240)
COLOR_TAB_INACTIVE_BG = (30, 36, 50)
COLOR_TAB_INACTIVE_TXT = (145, 160, 180)

# Kanvas: solid, tanpa grid dekoratif (antislop R-07)
COLOR_CANVAS_BG = (16, 20, 30)

# Warna Node Pohon CSP (muted, kontras cukup terhadap kanvas gelap)
COLOR_NODE_ROOT = (34, 42, 58)
COLOR_NODE_ROOT_BORDER = (100, 125, 170)

COLOR_NODE_ASSIGN = (28, 45, 65)
COLOR_NODE_ASSIGN_BORDER = (70, 135, 195)

COLOR_NODE_PRUNED = (60, 32, 40)
COLOR_NODE_PRUNED_BORDER = (190, 85, 100)

COLOR_NODE_BACKTRACK = (60, 46, 28)
COLOR_NODE_BACKTRACK_BORDER = (195, 145, 60)

COLOR_NODE_SOLUTION = (26, 58, 42)
COLOR_NODE_SOLUTION_BORDER = (55, 175, 110)

# Garis Koneksi Mulus
COLOR_LINE_NORMAL = (65, 82, 115)
COLOR_LINE_PRUNED = (185, 80, 95)
COLOR_LINE_BACKTRACK = (190, 140, 60)
COLOR_LINE_SOLUTION = (55, 180, 115)

# Warna Teks Umum
COLOR_TEXT_PRIMARY = (225, 230, 240)
COLOR_TEXT_SECONDARY = (160, 175, 195)
COLOR_TEXT_ACCENT = (75, 195, 180)
COLOR_TEXT_HEADING = (225, 200, 140)
COLOR_CARD_BG = (22, 28, 40)
COLOR_CARD_BORDER = (42, 55, 75)


def _get_bezier_points_horizontal(p0: Tuple[float, float], p3: Tuple[float, float], steps: int = 20) -> List[Tuple[int, int]]:
    """Menghasilkan titik-titik kurva Bezier kubik horizontal (mengalir halus dari kiri ke kanan)."""
    dx = p3[0] - p0[0]
    p1 = (p0[0] + dx * 0.5, p0[1])
    p2 = (p3[0] - dx * 0.5, p3[1])
    pts = []
    for i in range(steps + 1):
        t = i / float(steps)
        u = 1.0 - t
        x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
        y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
        pts.append((int(round(x)), int(round(y))))
    return pts


def _draw_smooth_curve(surface: pygame.Surface, color: Tuple[int, int, int], p0: Tuple[float, float], p3: Tuple[float, float], is_solution: bool = False, is_pruned: bool = False, width: int = 2):
    """Menggambar garis kurva S horizontal halus dengan anti-aliasing tanpa siku tajam."""
    pts = _get_bezier_points_horizontal(p0, p3, steps=20)
    if is_pruned:
        # Garis putus-putus merah marun halus
        i = 0
        while i < len(pts) - 1:
            end_idx = min(i + 2, len(pts) - 1)
            sub_pts = pts[i:end_idx + 1]
            if len(sub_pts) >= 2:
                pygame.draw.lines(surface, color, False, sub_pts, width=max(1, width))
            i += 3
    elif is_solution:
        # Garis jalur solusi tebal bercahaya zamrud
        pygame.draw.lines(surface, (20, 120, 60), False, pts, width=width + 3)
        pygame.draw.aalines(surface, (95, 245, 150), False, pts)
    else:
        # Garis normal anti-aliased
        pygame.draw.lines(surface, color, False, pts, width=max(1, width))
        pygame.draw.aalines(surface, color, False, pts)


class PreBattleVisualizerModal:
    """Modal Overlay Visualizer untuk CSP Backtracking Tree & Local Search Trajectory."""

    def __init__(self):
        self.is_open: bool = False
        self.active_tab: str = "CSP"  # "CSP" atau "LOCAL_SEARCH"

        # Data Sumber
        self.csp_tree: Dict[int, Dict[str, Any]] = {}
        self.csp_timeline: List[Dict[str, Any]] = []
        self.solution_path_ids: set = set()
        self.csp_tree_w: int = 1000
        self.csp_tree_h: int = 600

        self.ls_history: List[Dict[str, Any]] = []
        self.ls_algo_name: str = "HILL_CLIMBING"
        self.target_difficulty: float = 0.55

        # Pan & Zoom Kanvas
        self.pan_x: float = 0.0
        self.pan_y: float = 0.0
        self.target_pan_x: float = 0.0
        self.target_pan_y: float = 0.0
        self.user_nav_override_timer: float = 0.0
        self.zoom: float = 1.0
        self.is_dragging: bool = False
        self.drag_start_pos: Tuple[int, int] = (0, 0)
        self.drag_start_pan: Tuple[float, float] = (0.0, 0.0)

        # Timeline Controller Playback (Tempo default lebih perlahan ~0.85s/step)
        self.csp_current_step: int = 0
        self.ls_current_step: int = 0
        self.is_playing: bool = False
        self.playback_speed: float = 1.0
        self.play_timer: float = 0.0
        self.speeds: List[float] = [0.25, 0.5, 1.0, 2.0, 999.0]
        self.speed_idx: int = 2

        # Node terpilih di Tree untuk info detail
        self.selected_node_id: Optional[int] = None
        self.hovered_node_id: Optional[int] = None

        # Bounding boxes UI interaktif (diperbarui saat draw)
        self.rect_modal = pygame.Rect(0, 0, 0, 0)
        self.rect_canvas = pygame.Rect(0, 0, 0, 0)
        self.rect_btn_close = pygame.Rect(0, 0, 0, 0)
        self.rect_tab_csp = pygame.Rect(0, 0, 0, 0)
        self.rect_tab_ls = pygame.Rect(0, 0, 0, 0)

        self.rect_btn_play = pygame.Rect(0, 0, 0, 0)
        self.rect_btn_step_back = pygame.Rect(0, 0, 0, 0)
        self.rect_btn_step_fwd = pygame.Rect(0, 0, 0, 0)
        self.rect_btn_reset = pygame.Rect(0, 0, 0, 0)
        self.rect_btn_speed = pygame.Rect(0, 0, 0, 0)
        self.rect_scrubber_track = pygame.Rect(0, 0, 0, 0)
        self.is_scrubbing: bool = False

        self.rect_btn_zoom_in = pygame.Rect(0, 0, 0, 0)
        self.rect_btn_zoom_out = pygame.Rect(0, 0, 0, 0)
        self.rect_btn_zoom_reset = pygame.Rect(0, 0, 0, 0)

        # Cache Surface Blur Background (mencegah lag fps saat modal terbuka)
        self.cached_blurred_bg: Optional[pygame.Surface] = None

        # Scroll state untuk kolom penjelasan sidebar
        self.sidebar_scroll_y: float = 0.0
        self.max_sidebar_scroll: float = 0.0
        self.rect_sidebar: pygame.Rect = pygame.Rect(0, 0, 0, 0)

        # Popup Penjelasan Aturan C1-C8
        self.show_rules_popup: bool = False
        self.rect_btn_help_rules: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self.rect_rules_popup: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self.rect_btn_close_rules: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    # ----------------------------------------------------------------------- #
    # Set Data Baru & Reset Timeline
    # ----------------------------------------------------------------------- #
    def set_csp_data(self, tree: Dict[int, Dict[str, Any]], timeline: List[Dict[str, Any]], solution_path_ids: set, tree_w: int, tree_h: int):
        """Memperbarui data pohon pencarian CSP."""
        self.csp_tree = tree or {}
        self.csp_timeline = timeline or []
        self.solution_path_ids = solution_path_ids or set()
        self.csp_tree_w = max(800, tree_w)
        self.csp_tree_h = max(500, tree_h)
        self.csp_current_step = 0
        self.selected_node_id = None
        self.sidebar_scroll_y = 0.0
        self.show_rules_popup = False
        self.reset_view()

    def set_ls_data(self, history: List[Dict[str, Any]], algo_name: str, target_diff: float = 0.55):
        """Memperbarui data trajectory Local Search."""
        self.ls_history = history or []
        self.ls_algo_name = algo_name
        self.target_difficulty = target_diff
        self.ls_current_step = 0
        if self.active_tab == "LOCAL_SEARCH":
            self.reset_view()

    def open(self):
        """Membuka modal visualizer."""
        self.is_open = True
        self.is_playing = True
        self.show_rules_popup = False
        self.cached_blurred_bg = None
        self.reset_view()

    def close(self):
        """Menutup modal visualizer."""
        self.is_open = False
        self.is_playing = False
        self.show_rules_popup = False
        self.cached_blurred_bg = None

    def toggle(self):
        if self.is_open:
            self.close()
        else:
            self.open()

    def toggle_play(self):
        """Toggle play / pause timeline animasi."""
        self.is_playing = not self.is_playing

    def reset_view(self):
        """Mereset posisi pan dan zoom ke posisi optimal awal (kiri tengah)."""
        if self.rect_canvas.width > 0:
            if self.active_tab == "CSP":
                if self.csp_tree_h > 0:
                    scale_fit_y = (self.rect_canvas.height - 80) / float(max(1, self.csp_tree_h))
                    scale_fit_x = (self.rect_canvas.width - 80) / float(max(1, self.csp_tree_w))
                    self.zoom = max(0.45, min(1.0, min(scale_fit_y, scale_fit_x * 1.1)))
                else:
                    self.zoom = 1.0
                # Mulai dari kiri kanvas dengan padding yang rapi
                self.pan_x = 40.0
                self.pan_y = max(30.0, (self.rect_canvas.height - self.csp_tree_h * self.zoom) / 2.0)
            else:
                self.zoom = 1.0
                self.pan_x = 30.0
                self.pan_y = 30.0
        else:
            self.zoom = 1.0
            self.pan_x = 40.0
            self.pan_y = 40.0
        self.target_pan_x = self.pan_x
        self.target_pan_y = self.pan_y

    # ----------------------------------------------------------------------- #
    # Event Handling
    # ----------------------------------------------------------------------- #
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Memproses event mouse & keyboard jika modal sedang aktif.
        
        Mengembalikan True jika event ditangani oleh visualizer (mencegah klik tembus).
        """
        if not self.is_open:
            return False

        # 1. Keyboard Shortcuts
        if event.type == pygame.KEYDOWN:
            if self.show_rules_popup:
                if event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN):
                    self.show_rules_popup = False
                    return True
            if event.key in (pygame.K_ESCAPE, pygame.K_t):
                self.close()
                return True
            elif event.key == pygame.K_SPACE:
                self.is_playing = not self.is_playing
                return True
            elif event.key == pygame.K_LEFT:
                self.step_backward()
                self.is_playing = False
                return True
            elif event.key == pygame.K_RIGHT:
                self.step_forward()
                self.is_playing = False
                return True
            elif event.key == pygame.K_r:
                self.reset_playback()
                return True
            elif event.key == pygame.K_TAB:
                self.active_tab = "LOCAL_SEARCH" if self.active_tab == "CSP" else "CSP"
                self.reset_view()
                return True

        # 2. Touchpad Multi-Gesture (Pinch Hardware Langsung)
        if event.type == getattr(pygame, "MULTIGESTURE", -999):
            if hasattr(event, "dDist") and abs(event.dDist) > 0.0005:
                mx = int(event.x * self.rect_canvas.width) + self.rect_canvas.x
                my = int(event.y * self.rect_canvas.height) + self.rect_canvas.y
                zoom_factor = 1.0 + event.dDist * 3.5
                new_zoom = max(0.30, min(2.5, self.zoom * zoom_factor))
                rel_x = mx - (self.rect_canvas.x + self.pan_x)
                rel_y = my - (self.rect_canvas.y + self.pan_y)
                self.pan_x -= rel_x * (new_zoom / self.zoom - 1.0)
                self.pan_y -= rel_y * (new_zoom / self.zoom - 1.0)
                self.zoom = new_zoom
                self.target_pan_x = self.pan_x
                self.target_pan_y = self.pan_y
                self.user_nav_override_timer = 2.5
                return True

        # 3. Touchpad 2-Jari Scroll / Pinch & Mouse Wheel
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()

            # Scroll di atas panel penjelasan sidebar
            if self.active_tab == "CSP" and self.rect_sidebar.collidepoint((mx, my)):
                self.sidebar_scroll_y = max(0.0, min(self.max_sidebar_scroll, self.sidebar_scroll_y - event.y * 32.0))
                return True

            if self.rect_canvas.collidepoint((mx, my)):
                mods = pygame.key.get_mods()
                is_ctrl = bool(mods & pygame.KMOD_CTRL)

                if is_ctrl:
                    # Pinch-to-zoom Windows Touchpad (otomatis mengirim Ctrl + Wheel)
                    # 2 jari dari dalam ke luar = event.y > 0 (Zoom In)
                    # 2 jari dari luar ke dalam = event.y < 0 (Zoom Out)
                    zoom_factor = 1.12 if event.y > 0 else 0.89
                    new_zoom = max(0.30, min(2.5, self.zoom * zoom_factor))
                    rel_x = mx - (self.rect_canvas.x + self.pan_x)
                    rel_y = my - (self.rect_canvas.y + self.pan_y)
                    self.pan_x -= rel_x * (new_zoom / self.zoom - 1.0)
                    self.pan_y -= rel_y * (new_zoom / self.zoom - 1.0)
                    self.zoom = new_zoom
                    self.target_pan_x = self.pan_x
                    self.target_pan_y = self.pan_y
                    self.user_nav_override_timer = 2.5
                    return True
                else:
                    # Gesekan 2 jari biasa = PAN / MENGGESER KAMERA
                    scroll_speed = 36.0
                    self.pan_y += event.y * scroll_speed
                    if hasattr(event, "x") and event.x != 0:
                        self.pan_x -= event.x * scroll_speed  # Geser horizontal natural
                    self.target_pan_x = self.pan_x
                    self.target_pan_y = self.pan_y
                    self.user_nav_override_timer = 2.5
                    return True

        # 4. Mouse Button Down
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos

            # Interaksi Popup Rules C1-C8 jika sedang terbuka
            if self.show_rules_popup:
                if event.button == 1:
                    if self.rect_btn_close_rules.collidepoint((mx, my)):
                        self.show_rules_popup = False
                        return True
                    if not self.rect_rules_popup.collidepoint((mx, my)):
                        self.show_rules_popup = False
                        return True
                return True  # Menelan klik agar tidak tembus ke visualizer di belakang

            if not self.rect_modal.collidepoint((mx, my)):
                self.close()
                return True

            if event.button == 1:
                # Tombol Buka Popup Penjelasan Aturan C1-C8 (di samping tab)
                if self.rect_btn_help_rules.collidepoint((mx, my)):
                    self.show_rules_popup = not self.show_rules_popup
                    return True

                # Tombol Close Modal Utama
                if self.rect_btn_close.collidepoint((mx, my)):
                    self.close()
                    return True

                # Tab Switcher
                if self.rect_tab_csp.collidepoint((mx, my)):
                    self.active_tab = "CSP"
                    self.reset_view()
                    return True
                elif self.rect_tab_ls.collidepoint((mx, my)):
                    self.active_tab = "LOCAL_SEARCH"
                    self.reset_view()
                    return True

                # Kontrol Playback
                if self.rect_btn_play.collidepoint((mx, my)):
                    self.is_playing = not self.is_playing
                    return True
                elif self.rect_btn_step_back.collidepoint((mx, my)):
                    self.step_backward()
                    self.is_playing = False
                    return True
                elif self.rect_btn_step_fwd.collidepoint((mx, my)):
                    self.step_forward()
                    self.is_playing = False
                    return True
                elif self.rect_btn_reset.collidepoint((mx, my)):
                    self.reset_playback()
                    return True
                elif self.rect_btn_speed.collidepoint((mx, my)):
                    self.speed_idx = (self.speed_idx + 1) % len(self.speeds)
                    self.playback_speed = self.speeds[self.speed_idx]
                    return True

                # Scrubber Timeline Bar
                if self.rect_scrubber_track.collidepoint((mx, my)):
                    self.is_scrubbing = True
                    self.is_playing = False
                    self.sidebar_scroll_y = 0.0
                    self._update_scrubber(mx)
                    return True

                # Zoom Buttons
                if self.rect_btn_zoom_in.collidepoint((mx, my)):
                    self.zoom = min(2.5, self.zoom * 1.2)
                    return True
                elif self.rect_btn_zoom_out.collidepoint((mx, my)):
                    self.zoom = max(0.35, self.zoom / 1.2)
                    return True
                elif self.rect_btn_zoom_reset.collidepoint((mx, my)):
                    self.reset_view()
                    return True

                # Klik pada Node Tree CSP di Canvas
                if self.active_tab == "CSP" and self.rect_canvas.collidepoint((mx, my)):
                    clicked_node = self._find_node_at((mx, my))
                    self.sidebar_scroll_y = 0.0
                    if clicked_node is not None:
                        self.selected_node_id = clicked_node
                        return True
                    else:
                        self.selected_node_id = None

                # Mulai Drag Kanvas (Pan)
                if self.rect_canvas.collidepoint((mx, my)):
                    self.is_dragging = True
                    self.drag_start_pos = (mx, my)
                    self.drag_start_pan = (self.pan_x, self.pan_y)
                    return True

        # 4. Mouse Motion (Drag Pan & Scrubber)
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            if self.is_scrubbing:
                self._update_scrubber(mx)
                return True

            if self.is_dragging:
                dx = mx - self.drag_start_pos[0]
                dy = my - self.drag_start_pos[1]
                self.pan_x = self.drag_start_pan[0] + dx
                self.pan_y = self.drag_start_pan[1] + dy
                self.target_pan_x = self.pan_x
                self.target_pan_y = self.pan_y
                self.user_nav_override_timer = 2.5
                return True

            if self.active_tab == "CSP" and self.rect_canvas.collidepoint((mx, my)):
                self.hovered_node_id = self._find_node_at((mx, my))
            else:
                self.hovered_node_id = None

        # 5. Mouse Button Up
        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.is_dragging = False
                self.is_scrubbing = False

        return True

    def _update_scrubber(self, mouse_x: int):
        """Menghitung step berdasarkan posisi drag kursor mouse pada timeline scrubber."""
        track = self.rect_scrubber_track
        if track.width <= 0:
            return
        rel = max(0.0, min(1.0, (mouse_x - track.x) / float(track.width)))
        if self.active_tab == "CSP":
            max_s = max(0, len(self.csp_timeline) - 1)
            self.csp_current_step = int(round(rel * max_s))
        else:
            max_s = max(0, len(self.ls_history) - 1)
            self.ls_current_step = int(round(rel * max_s))

    def _find_node_at(self, screen_pos: Tuple[int, int]) -> Optional[int]:
        """Mencari ID node pohon di bawah koordinat kursor mouse."""
        if not self.csp_tree:
            return None
        mx, my = screen_pos
        cx = self.rect_canvas.x + self.pan_x
        cy = self.rect_canvas.y + self.pan_y
        node_w = 310 * self.zoom
        node_h = 86 * self.zoom

        # Hanya periksa node yang telah muncul sampai step saat ini
        visible_node_ids = self._get_visible_csp_node_ids()
        for nid in visible_node_ids:
            nd = self.csp_tree.get(nid)
            if not nd:
                continue
            nx = cx + nd["x"] * self.zoom
            ny = cy + nd["y"] * self.zoom
            if nx <= mx <= nx + node_w and ny <= my <= ny + node_h:
                return nid
        return None

    def _get_visible_csp_node_ids(self) -> set:
        """Mengambil set node_id yang sudah dieksplorasi sampai csp_current_step."""
        if not self.csp_timeline:
            return set(self.csp_tree.keys())
        visible = set()
        step_limit = min(self.csp_current_step, len(self.csp_timeline) - 1)
        for i in range(step_limit + 1):
            st = self.csp_timeline[i]
            nid = st.get("node_id")
            if nid is not None:
                visible.add(nid)
        return visible

    def _update_camera_tracking(self, dt: float):
        """Kamera otomatis mengikuti kemunculan cabang atau simpul baru di pohon."""
        if self.user_nav_override_timer > 0:
            self.user_nav_override_timer = max(0.0, self.user_nav_override_timer - dt)
            return

        if self.active_tab == "CSP" and self.csp_timeline:
            step_idx = min(self.csp_current_step, len(self.csp_timeline) - 1)
            cur_step_info = self.csp_timeline[step_idx]
            nid = cur_step_info.get("node_id")
            if nid is not None and nid in self.csp_tree:
                nd = self.csp_tree[nid]
                node_w_base = 310.0
                node_h_base = 86.0
                node_center_x = (nd["x"] + node_w_base * 0.5) * self.zoom
                node_center_y = (nd["y"] + node_h_base * 0.5) * self.zoom

                # Posisikan simpul aktif di sekitar 40% horizontal dan 48% vertikal kanvas
                target_x = (self.rect_canvas.width * 0.40) - node_center_x
                target_y = (self.rect_canvas.height * 0.48) - node_center_y
                self.target_pan_x = target_x
                self.target_pan_y = target_y

                # Smooth lerp interpolation
                lerp_speed = min(1.0, dt * 4.2)
                self.pan_x += (self.target_pan_x - self.pan_x) * lerp_speed
                self.pan_y += (self.target_pan_y - self.pan_y) * lerp_speed

    # ----------------------------------------------------------------------- #
    # Logika Playback Update (Per Frame)
    # ----------------------------------------------------------------------- #
    def update(self, dt: float):
        """Memajukan frame animasi otomatis saat status is_playing aktif."""
        self._update_camera_tracking(dt)

        if not self.is_open or not self.is_playing:
            return

        # Durasi antar step berdasarkan kecepatan (default lebih santai ~0.85s/step)
        if self.playback_speed >= 900.0:
            if self.active_tab == "CSP":
                self.csp_current_step = max(0, len(self.csp_timeline) - 1)
            else:
                self.ls_current_step = max(0, len(self.ls_history) - 1)
            self.is_playing = False
            return

        interval = 0.85 / self.playback_speed
        self.play_timer += dt
        if self.play_timer >= interval:
            self.play_timer = 0.0
            if self.active_tab == "CSP":
                if self.csp_current_step < len(self.csp_timeline) - 1:
                    self.csp_current_step += 1
                    self.sidebar_scroll_y = 0.0
                else:
                    self.is_playing = False
            else:
                if self.ls_current_step < len(self.ls_history) - 1:
                    self.ls_current_step += 1
                else:
                    self.is_playing = False

    def step_forward(self):
        if self.active_tab == "CSP":
            if self.csp_current_step < len(self.csp_timeline) - 1:
                self.csp_current_step += 1
                self.user_nav_override_timer = 0.0
                self.sidebar_scroll_y = 0.0
        else:
            if self.ls_current_step < len(self.ls_history) - 1:
                self.ls_current_step += 1

    def step_backward(self):
        if self.active_tab == "CSP":
            if self.csp_current_step > 0:
                self.csp_current_step -= 1
                self.user_nav_override_timer = 0.0
                self.sidebar_scroll_y = 0.0
        else:
            if self.ls_current_step > 0:
                self.ls_current_step -= 1

    def reset_playback(self):
        if self.active_tab == "CSP":
            self.csp_current_step = 0
            self.user_nav_override_timer = 0.0
            self.sidebar_scroll_y = 0.0
        else:
            self.ls_current_step = 0
        self.is_playing = True

    # ----------------------------------------------------------------------- #
    # Render Utama Modal
    # ----------------------------------------------------------------------- #
    def draw(self, screen: pygame.Surface, fonts: Dict[str, pygame.font.Font]):
        """Menggambar seluruh antarmuka modal visualizer di atas layar."""
        if not self.is_open:
            return

        sw, sh = screen.get_size()
        font_sm = fonts["sm"]
        font_tiny = fonts.get("tiny", font_sm)
        font_title = fonts.get("title", font_sm)
        font_bubble = fonts.get("bubble", font_sm)

        # 1. Background Blur + Dim (Membuat konten di belakang modal blur dan gelap)
        self._draw_blurred_background(screen, sw, sh)

        # 2. Kotak Modal Utama (94% Lebar & 90% Tinggi Layar)
        mw = int(sw * 0.94)
        mh = int(sh * 0.90)
        mx = (sw - mw) // 2
        my = (sh - mh) // 2
        self.rect_modal = pygame.Rect(mx, my, mw, mh)

        # Body Modal (solid, satu layer glass saja per antislop R-10)
        modal_surf = pygame.Surface((mw, mh), SRCALPHA)
        modal_surf.fill(COLOR_MODAL_BG)
        screen.blit(modal_surf, (mx, my))
        pygame.draw.rect(screen, COLOR_MODAL_BORDER, self.rect_modal, 1, border_radius=10)

        # 3. Header Bar Atas
        hdr_h = 58
        hdr_rect = pygame.Rect(mx, my, mw, hdr_h)
        pygame.draw.rect(screen, COLOR_HEADER_BG, hdr_rect, border_top_left_radius=10, border_top_right_radius=10)
        pygame.draw.line(screen, (38, 50, 70), (mx, my + hdr_h), (mx + mw, my + hdr_h), 1)

        # Judul & Subtitle (tanpa emoji, antislop R-04)
        t_surf = font_title.render("INSPEKSI AI PRE-BATTLE", True, COLOR_TEXT_HEADING)
        sub_surf = font_sm.render("Pohon Backtracking CSP  |  Optimasi Local Search", True, COLOR_TEXT_SECONDARY)
        screen.blit(t_surf, (mx + 20, my + 10))
        screen.blit(sub_surf, (mx + 20, my + 34))

        # Tombol Tutup [X] di pojok kanan atas
        self.rect_btn_close = pygame.Rect(mx + mw - 46, my + 12, 34, 34)
        pygame.draw.rect(screen, (145, 40, 40), self.rect_btn_close, border_radius=6)
        x_lbl = font_title.render("X", True, (255, 255, 255))
        screen.blit(x_lbl, x_lbl.get_rect(center=self.rect_btn_close.center))

        # Tab Switcher & Info C1-C8
        tab_w = 210
        tab_h = 36
        tab_y = my + 11
        btn_rules_w = 145
        self.rect_tab_ls = pygame.Rect(mx + mw - 46 - tab_w - 12, tab_y, tab_w, tab_h)
        self.rect_tab_csp = pygame.Rect(self.rect_tab_ls.x - tab_w - 8, tab_y, tab_w, tab_h)
        self.rect_btn_help_rules = pygame.Rect(self.rect_tab_csp.x - btn_rules_w - 10, tab_y, btn_rules_w, tab_h)

        # Draw Tombol Info Aturan C1-C8 di samping tab
        mx_cur, my_cur = pygame.mouse.get_pos()
        rules_hover = self.rect_btn_help_rules.collidepoint((mx_cur, my_cur))
        rules_active = self.show_rules_popup
        if rules_active:
            r_bg = (38, 95, 140)
            r_border = (115, 215, 255)
            r_txt = (255, 255, 255)
        elif rules_hover:
            r_bg = (35, 55, 80)
            r_border = (90, 185, 245)
            r_txt = (235, 248, 255)
        else:
            r_bg = (24, 34, 52)
            r_border = (55, 95, 145)
            r_txt = (165, 205, 245)
        pygame.draw.rect(screen, r_bg, self.rect_btn_help_rules, border_radius=6)
        pygame.draw.rect(screen, r_border, self.rect_btn_help_rules, 1, border_radius=6)
        t_rules = font_sm.render("[?] Aturan C1-C8", True, r_txt)
        screen.blit(t_rules, t_rules.get_rect(center=self.rect_btn_help_rules.center))

        # Draw Tab CSP (tanpa emoji)
        csp_active = (self.active_tab == "CSP")
        c_bg = COLOR_TAB_ACTIVE_BG if csp_active else COLOR_TAB_INACTIVE_BG
        c_txt = COLOR_TAB_ACTIVE_TXT if csp_active else COLOR_TAB_INACTIVE_TXT
        pygame.draw.rect(screen, c_bg, self.rect_tab_csp, border_radius=6)
        if csp_active:
            pygame.draw.rect(screen, COLOR_TEXT_ACCENT, self.rect_tab_csp, 1, border_radius=6)
        t_csp = font_sm.render("1. Pohon CSP & Pruning", True, c_txt)
        screen.blit(t_csp, t_csp.get_rect(center=self.rect_tab_csp.center))

        # Draw Tab Local Search (tanpa emoji)
        ls_active = (self.active_tab == "LOCAL_SEARCH")
        l_bg = COLOR_TAB_ACTIVE_BG if ls_active else COLOR_TAB_INACTIVE_BG
        l_txt = COLOR_TAB_ACTIVE_TXT if ls_active else COLOR_TAB_INACTIVE_TXT
        pygame.draw.rect(screen, l_bg, self.rect_tab_ls, border_radius=6)
        if ls_active:
            pygame.draw.rect(screen, COLOR_TEXT_ACCENT, self.rect_tab_ls, 1, border_radius=6)
        t_ls = font_sm.render(f"2. Optimasi ({self.ls_algo_name[:12]})", True, l_txt)
        screen.blit(t_ls, t_ls.get_rect(center=self.rect_tab_ls.center))

        # 4. Area Kontrol Bawah (Playback Controller & Scrubber)
        ctrl_h = 64
        ctrl_y = my + mh - ctrl_h
        self._draw_bottom_playback_controls(screen, mx, ctrl_y, mw, ctrl_h, font_sm, font_bubble)

        # 5. Canvas Utama & Kolom Penjelasan Samping Kanan
        canvas_x = mx + 12
        canvas_y = my + hdr_h + 8
        canvas_w = mw - 24
        canvas_h = (mh - hdr_h - ctrl_h - 16)

        if self.active_tab == "CSP":
            # Tab 1: Kiri (Kanvas Pohon 60%), Kanan (Kolom Penjelasan CSP 40%)
            tree_w = int(canvas_w * 0.60)
            sidebar_w = canvas_w - tree_w - 12
            self.rect_canvas = pygame.Rect(canvas_x, canvas_y, tree_w, canvas_h)
            rect_sidebar = pygame.Rect(canvas_x + tree_w + 12, canvas_y, sidebar_w, canvas_h)

            # Klip rendering hanya di dalam area canvas pohon
            old_clip = screen.get_clip()
            screen.set_clip(self.rect_canvas)

            pygame.draw.rect(screen, COLOR_CANVAS_BG, self.rect_canvas, border_radius=6)
            # Grid dekoratif dihilangkan (antislop R-07)
            self._draw_csp_tree_view(screen, font_sm, font_bubble, font_tiny)

            screen.set_clip(old_clip)
            pygame.draw.rect(screen, COLOR_MODAL_BORDER, self.rect_canvas, 1, border_radius=6)

            # Floating Zoom Controls di Pojok Kanan Atas Kanvas Pohon
            self._draw_zoom_controls(screen, font_sm)

            # Kolom Penjelasan Teori & Analisis CSP di Samping Kanan
            self._draw_csp_theory_sidebar(screen, rect_sidebar, font_sm, font_bubble, font_tiny, font_title)

        else:
            # Tab 2: Kanvas Penuh yang memuat Grafik di Kiri (53%) dan Kolom Penjelasan di Kanan (47%)
            self.rect_canvas = pygame.Rect(canvas_x, canvas_y, canvas_w, canvas_h)
            old_clip = screen.get_clip()
            screen.set_clip(self.rect_canvas)

            pygame.draw.rect(screen, COLOR_CANVAS_BG, self.rect_canvas, border_radius=6)
            # Grid dekoratif dihilangkan (antislop R-07)
            self._draw_local_search_view(screen, font_sm, font_bubble, font_title, font_tiny)

            screen.set_clip(old_clip)
            pygame.draw.rect(screen, COLOR_MODAL_BORDER, self.rect_canvas, 1, border_radius=6)

        # 6. Modal Popup Penjelasan Aturan C1-C8 jika dibuka
        if self.show_rules_popup:
            self._draw_rules_popup(screen, sw, sh, font_sm, font_bubble, font_tiny, font_title)

    # ----------------------------------------------------------------------- #
    # Modal Popup Penjelasan Aturan C1 - C8
    # ----------------------------------------------------------------------- #
    def _draw_rules_popup(
        self,
        screen: pygame.Surface,
        sw: int,
        sh: int,
        font_sm: pygame.font.Font,
        font_bubble: pygame.font.Font,
        font_tiny: pygame.font.Font,
        font_title: pygame.font.Font
    ):
        """Menampilkan dialog popup ringkas penjelasan seluruh aturan konsistensi C1 - C8."""
        # 1. Dimmer latar belakang semi-transparan
        dimmer = pygame.Surface((sw, sh), SRCALPHA)
        dimmer.fill((8, 12, 18, 175))
        screen.blit(dimmer, (0, 0))

        # 2. Kotak Modal Popup
        pw = min(680, int(sw * 0.88))
        ph = min(480, int(sh * 0.85))
        px = (sw - pw) // 2
        py = (sh - ph) // 2
        self.rect_rules_popup = pygame.Rect(px, py, pw, ph)

        pygame.draw.rect(screen, (18, 24, 36), self.rect_rules_popup, border_radius=8)
        pygame.draw.rect(screen, (70, 115, 175), self.rect_rules_popup, 2, border_radius=8)

        # 3. Header Bar Popup (44px)
        hdr_h = 44
        hdr_rect = pygame.Rect(px, py, pw, hdr_h)
        pygame.draw.rect(screen, (24, 32, 48), hdr_rect, border_top_left_radius=8, border_top_right_radius=8)
        pygame.draw.line(screen, (45, 62, 92), (px, py + hdr_h), (px + pw, py + hdr_h), 1)

        t_title = font_bubble.render("RINGKASAN ATURAN KONSISTENSI CSP (C1 - C8)", True, COLOR_TEXT_HEADING)
        screen.blit(t_title, (px + 14, py + 12))

        # Tombol Tutup [X] di Header Popup
        self.rect_btn_close_rules = pygame.Rect(px + pw - 34, py + 10, 24, 24)
        mx_cur, my_cur = pygame.mouse.get_pos()
        is_hover_x = self.rect_btn_close_rules.collidepoint((mx_cur, my_cur))
        x_bg = (195, 55, 55) if is_hover_x else (145, 40, 40)
        pygame.draw.rect(screen, x_bg, self.rect_btn_close_rules, border_radius=4)
        x_lbl = font_title.render("X", True, (255, 255, 255))
        screen.blit(x_lbl, x_lbl.get_rect(center=self.rect_btn_close_rules.center))

        # 4. Daftar 8 Aturan C1 - C8 (Padat & Jelas)
        rules_list = [
            ("C1", "Budget Total HP", "Total HP seluruh anggota tim <= 200 (mencegah tim musuh terlalu tebal).", (100, 205, 255)),
            ("C2", "Budget Ramuan (Potion)", "Total inventaris ramuan tim <= 2 (menjaga batas pemulihan HP).", (100, 205, 255)),
            ("C3", "Syarat Role Tank (HP)", "Karakter Tank wajib memiliki HP >= 90 (sesuai peran penyerap damage).", (135, 235, 175)),
            ("C4", "Syarat Role Ranger (ATK)", "Karakter Ranger wajib Bonus ATK >= 5 (penyerang jarak jauh).", (135, 235, 175)),
            ("C5", "Keunikan Role Skuad", "Tipe karakter harus unik di tim (tidak boleh ada role kembar jika NPC >= 2).", (255, 185, 90)),
            ("C6", "Glass Cannon Mage", "Karakter Mage HP <= 90 & AI bertipe BALANCED atau AGGRESSIVE.", (245, 130, 140)),
            ("C7", "Pelindung Tank (AI)", "Karakter Tank AI bertipe BALANCED atau DEFENSIVE (fokus guard).", (135, 235, 175)),
            ("C8", "Assassin & Budget ATK", "Assassin ATK >= 10, HP <= 90, AI agresif & Total Bonus ATK tim <= 12.", (215, 150, 250)),
        ]

        item_y = py + hdr_h + 8
        avail_h = ph - hdr_h - 38
        item_h = avail_h // len(rules_list)

        for code, name, desc, badge_col in rules_list:
            card_rect = pygame.Rect(px + 12, item_y, pw - 24, item_h - 4)
            pygame.draw.rect(screen, (24, 30, 44), card_rect, border_radius=4)
            pygame.draw.rect(screen, (38, 48, 68), card_rect, 1, border_radius=4)

            # Badge Kode [C1], [C2], dst.
            badge_rect = pygame.Rect(card_rect.x + 6, card_rect.y + 4, 36, card_rect.height - 8)
            pygame.draw.rect(screen, (16, 22, 34), badge_rect, border_radius=3)
            pygame.draw.rect(screen, badge_col, badge_rect, 1, border_radius=3)
            s_code = font_bubble.render(code, True, badge_col)
            screen.blit(s_code, s_code.get_rect(center=badge_rect.center))

            # Nama Aturan
            s_name = font_sm.render(name, True, COLOR_TEXT_PRIMARY)
            screen.blit(s_name, (card_rect.x + 48, card_rect.y + 3))

            # Penjelasan Ringkas
            s_desc = font_tiny.render(desc, True, COLOR_TEXT_SECONDARY)
            screen.blit(s_desc, (card_rect.x + 48, card_rect.y + 20))

            item_y += item_h

        # Footer Petunjuk Tutup
        lbl_hint = font_tiny.render("Tips: Tekan [ESC] atau klik [X] / klik di luar kotak untuk kembali", True, (140, 155, 175))
        screen.blit(lbl_hint, (px + 14, py + ph - 22))

    # ----------------------------------------------------------------------- #
    # Blur Background Helper
    # ----------------------------------------------------------------------- #
    def _draw_blurred_background(self, screen: pygame.Surface, sw: int, sh: int):
        """Menangkap layar, menskalakan turun lalu naik untuk efek blur, lalu dimming."""
        if self.cached_blurred_bg is None or self.cached_blurred_bg.get_size() != (sw, sh):
            snapshot = screen.copy()
            # Downscale faktor 10x lalu upscale kembali = blur halus elegan
            small_w = max(1, sw // 10)
            small_h = max(1, sh // 10)
            small = pygame.transform.smoothscale(snapshot, (small_w, small_h))
            blurred = pygame.transform.smoothscale(small, (sw, sh))
            dimmer = pygame.Surface((sw, sh), SRCALPHA)
            dimmer.fill((10, 14, 22, 195))
            blurred.blit(dimmer, (0, 0))
            self.cached_blurred_bg = blurred

        screen.blit(self.cached_blurred_bg, (0, 0))

    # ----------------------------------------------------------------------- #
    # TAB 1: Visualisasi Pohon CSP & Pruning (Orientasi Horizontal: Kiri ke Kanan)
    # ----------------------------------------------------------------------- #
    def _draw_csp_tree_view(self, screen: pygame.Surface, font_sm: pygame.font.Font, font_bubble: pygame.font.Font, font_tiny: pygame.font.Font):
        if not self.csp_tree:
            no_data = font_bubble.render("Belum ada data pohon CSP. Tekan R di Pre-Battle untuk memulai.", True, COLOR_TEXT_SECONDARY)
            screen.blit(no_data, no_data.get_rect(center=self.rect_canvas.center))
            return

        cx = self.rect_canvas.x + self.pan_x
        cy = self.rect_canvas.y + self.pan_y
        node_w_base = 310
        node_h_base = 86
        node_w = int(node_w_base * self.zoom)
        node_h = int(node_h_base * self.zoom)

        visible_nids = self._get_visible_csp_node_ids()
        current_step_info = self.csp_timeline[self.csp_current_step] if self.csp_timeline else {}
        active_nid = current_step_info.get("node_id")

        # 1. Gambar Garis Bezier Kurva Mulus Parent -> Child Horizontal (Kiri ke Kanan)
        for nid in visible_nids:
            nd = self.csp_tree[nid]
            pid = nd.get("parent_id")
            if pid is not None and pid in visible_nids:
                p_node = self.csp_tree[pid]
                p0 = (cx + (p_node["x"] + node_w_base) * self.zoom, cy + (p_node["y"] + node_h_base / 2.0) * self.zoom)
                p3 = (cx + nd["x"] * self.zoom, cy + (nd["y"] + node_h_base / 2.0) * self.zoom)

                is_sol = (nid in self.solution_path_ids and pid in self.solution_path_ids and nd["status"] == "SOLUTION")
                is_prun = (nd["status"] == "PRUNED")
                is_back = (nd["status"] == "BACKTRACK")

                line_col = COLOR_LINE_SOLUTION if is_sol else (COLOR_LINE_PRUNED if is_prun else (COLOR_LINE_BACKTRACK if is_back else COLOR_LINE_NORMAL))
                _draw_smooth_curve(screen, line_col, p0, p3, is_solution=is_sol, is_pruned=is_prun, width=max(1, int(2 * self.zoom)))

        # Fungsi pembantu untuk memotong teks secara presisi berdasarkan piksel
        def fit_text(font_obj: pygame.font.Font, text: str, max_w: int) -> str:
            if font_obj.size(text)[0] <= max_w:
                return text
            for i in range(len(text), 0, -1):
                sub = text[:i] + ".."
                if font_obj.size(sub)[0] <= max_w:
                    return sub
            return ""

        # 2. Gambar Node Rounded Box Horizontal Berisi 3 Baris Detail Lega
        font_node_title = font_bubble if self.zoom >= 0.85 else (font_sm if self.zoom >= 0.65 else font_tiny)
        font_node_sub = font_sm if self.zoom >= 0.80 else font_tiny
        font_node_detail = font_sm if self.zoom >= 0.85 else font_tiny

        for nid in visible_nids:
            nd = self.csp_tree[nid]
            nx = cx + nd["x"] * self.zoom
            ny = cy + nd["y"] * self.zoom
            node_rect = pygame.Rect(int(nx), int(ny), node_w, node_h)

            status = nd.get("status", "ASSIGN")
            is_active = (nid == active_nid)
            is_selected = (nid == self.selected_node_id)
            is_hovered = (nid == self.hovered_node_id or is_selected)

            reason_str = nd.get("reason") or ""

            # Penentuan Warna & Label Berdasarkan Status
            if status == "ROOT":
                bg_col, border_col = COLOR_NODE_ROOT, COLOR_NODE_ROOT_BORDER
                badge_txt = "ROOT (Inisialisasi CSP)"
                badge_col = (130, 175, 240)
                detail_txt = "Persiapan domain AC-3 & MRV"
                detail_col = (175, 195, 225)
            elif status == "SOLUTION" or nid in self.solution_path_ids:
                bg_col, border_col = COLOR_NODE_SOLUTION, COLOR_NODE_SOLUTION_BORDER
                badge_txt = "✓ SOLUSI LENGKAP"
                badge_col = (85, 245, 140)
                detail_txt = "Lolos seluruh aturan C1-C8!"
                detail_col = (160, 245, 195)
            elif status == "PRUNED":
                bg_col, border_col = COLOR_NODE_PRUNED, COLOR_NODE_PRUNED_BORDER
                badge_txt = "✕ DIPANGKAS (PRUNED)"
                badge_col = (255, 115, 125)
                detail_txt = reason_str if reason_str else "Melanggar batasan constraint"
                detail_col = (255, 180, 185)
            elif status == "BACKTRACK":
                bg_col, border_col = COLOR_NODE_BACKTRACK, COLOR_NODE_BACKTRACK_BORDER
                badge_txt = "↩ JALAN BUNTU (BACKTRACK)"
                badge_col = (255, 185, 80)
                detail_txt = "Cabang anak gagal -> mundur"
                detail_col = (255, 210, 150)
            else:
                bg_col, border_col = COLOR_NODE_ASSIGN, COLOR_NODE_ASSIGN_BORDER
                badge_txt = "▶ DIPILIH (MRV & LCV)"
                badge_col = (100, 200, 255)
                detail_txt = reason_str if reason_str else "Konsisten C1-C8 (LCV 0 konflik)"
                detail_col = (170, 215, 255)

            # Highlight Glow jika sedang aktif diproses di timeline atau dipilih
            if is_selected:
                glow_rect = node_rect.inflate(int(10 * self.zoom), int(10 * self.zoom))
                pygame.draw.rect(screen, (80, 200, 255), glow_rect, border_radius=10)
            elif is_active:
                glow_rect = node_rect.inflate(int(8 * self.zoom), int(8 * self.zoom))
                pygame.draw.rect(screen, (255, 230, 80), glow_rect, border_radius=9)
            elif is_hovered:
                glow_rect = node_rect.inflate(int(6 * self.zoom), int(6 * self.zoom))
                pygame.draw.rect(screen, (100, 160, 230), glow_rect, border_radius=8)

            # Gambar Kotak Node
            pygame.draw.rect(screen, bg_col, node_rect, border_radius=8)
            pygame.draw.rect(screen, border_col, node_rect, max(1, int(2 * self.zoom)), border_radius=8)

            # Teks Node Berisi 3 Baris Rinci (Dilindungi clipping agar tidak keluar kotak)
            if self.zoom >= 0.40:
                clip_node = node_rect.clip(self.rect_canvas)
                screen.set_clip(clip_node)

                max_txt_w = max(10, node_rect.width - int(18 * self.zoom))
                var_name = nd.get("var", "")
                val_str = str(nd.get("val", ""))

                # Baris 1: Variabel & Nilai Eksplisit
                header_raw = f"{var_name} = {val_str}" if var_name != "ROOT" else "START CSP (ROOT)"
                lbl_top = fit_text(font_node_title, header_raw, max_txt_w)
                if lbl_top:
                    s_top = font_node_title.render(lbl_top, True, (255, 255, 255))
                    screen.blit(s_top, (node_rect.x + (node_rect.width - s_top.get_width()) // 2, node_rect.y + int(8 * self.zoom)))

                # Baris 2: Badge Status & Keputusan Algoritma
                lbl_mid = fit_text(font_node_sub, badge_txt, max_txt_w)
                if lbl_mid:
                    s_mid = font_node_sub.render(lbl_mid, True, badge_col)
                    screen.blit(s_mid, (node_rect.x + (node_rect.width - s_mid.get_width()) // 2, node_rect.y + int(33 * self.zoom)))

                # Baris 3: Alasan Pruning / Kondisi Konsistensi LCV
                lbl_bot = fit_text(font_node_detail, detail_txt, max_txt_w)
                if lbl_bot:
                    s_bot = font_node_detail.render(lbl_bot, True, detail_col)
                    screen.blit(s_bot, (node_rect.x + (node_rect.width - s_bot.get_width()) // 2, node_rect.y + int(57 * self.zoom)))

                screen.set_clip(self.rect_canvas)

    def _draw_csp_theory_sidebar(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        font_sm: pygame.font.Font,
        font_bubble: pygame.font.Font,
        font_tiny: pygame.font.Font,
        font_title: pygame.font.Font
    ):
        """Menampilkan kolom penjelasan teori akademis CSP dan analisis node di samping kanan canvas."""
        self.rect_sidebar = rect

        s = pygame.Surface((rect.width, rect.height), SRCALPHA)
        s.fill((16, 20, 30, 245))
        screen.blit(s, (rect.x, rect.y))
        pygame.draw.rect(screen, COLOR_CARD_BORDER, rect, 1, border_radius=6)

        old_clip_sb = screen.get_clip()
        screen.set_clip(rect.clip(old_clip_sb))

        # Header Utama (tanpa emoji, antislop R-04)
        t_hdr = font_title.render("PANDUAN TEORI CSP", True, COLOR_TEXT_HEADING)
        screen.blit(t_hdr, (rect.x + 12, rect.y + 8))
        t_sub_str = "Russell & Norvig: Backtracking, MRV, LCV & FC"
        if font_tiny.size(t_sub_str)[0] > (rect.width - 24):
            t_sub_str = "Russell & Norvig: Backtracking & CSP"
        t_sub = font_tiny.render(t_sub_str, True, COLOR_TEXT_SECONDARY)
        screen.blit(t_sub, (rect.x + 12, rect.y + 27))

        # Card 1: Formulasi Formal Masalah (X, D, C) - Compact 58px
        c1_y = rect.y + 44
        c1_h = 58
        c1_rect = pygame.Rect(rect.x + 6, c1_y, rect.width - 12, c1_h)
        pygame.draw.rect(screen, COLOR_CARD_BG, c1_rect, border_radius=4)
        pygame.draw.rect(screen, COLOR_CARD_BORDER, c1_rect, 1, border_radius=4)

        screen.blit(font_bubble.render("1. Formulasi Masalah (X, D, C)", True, COLOR_TEXT_ACCENT), (c1_rect.x + 8, c1_rect.y + 4))
        screen.blit(font_tiny.render("X: 5 Variabel (Role, HP, Potion, ATK, Profile)", True, COLOR_TEXT_PRIMARY), (c1_rect.x + 8, c1_rect.y + 21))
        screen.blit(font_tiny.render("D: Domain Stat Game  |  C: Aturan C1-C8 (Tab Atas)", True, COLOR_TEXT_SECONDARY), (c1_rect.x + 8, c1_rect.y + 37))

        # Card 2: Heuristic & Kamus Warna Tree - Compact 56px (2 Kolom)
        c2_y = c1_rect.bottom + 5
        c2_h = 56
        c2_rect = pygame.Rect(rect.x + 6, c2_y, rect.width - 12, c2_h)
        pygame.draw.rect(screen, COLOR_CARD_BG, c2_rect, border_radius=4)
        pygame.draw.rect(screen, COLOR_CARD_BORDER, c2_rect, 1, border_radius=4)

        screen.blit(font_bubble.render("2. Heuristik & Status Simpul", True, COLOR_TEXT_ACCENT), (c2_rect.x + 8, c2_rect.y + 4))
        half_w = (c2_rect.width - 16) // 2
        col1_x = c2_rect.x + 8
        col2_x = c2_rect.x + 8 + half_w
        screen.blit(font_tiny.render("[ASSIGN] MRV & LCV", True, (85, 175, 235)), (col1_x, c2_rect.y + 21))
        screen.blit(font_tiny.render("[PRUNED] Pangkas C1-C8", True, (225, 95, 110)), (col2_x, c2_rect.y + 21))
        screen.blit(font_tiny.render("[BACKTRACK] Dead-End", True, (225, 165, 65)), (col1_x, c2_rect.y + 37))
        screen.blit(font_tiny.render("[SOLUSI] Skuad Legal", True, (75, 215, 125)), (col2_x, c2_rect.y + 37))

        # Card 3: Analisis Langkah & Simpul Terpilih (Sisa Tinggi Layar)
        c3_y = c2_rect.bottom + 5
        c3_h = rect.bottom - c3_y - 6
        c3_rect = pygame.Rect(rect.x + 6, c3_y, rect.width - 12, max(180, c3_h))
        pygame.draw.rect(screen, (14, 18, 28), c3_rect, border_radius=4)
        pygame.draw.rect(screen, COLOR_CARD_BORDER, c3_rect, 1, border_radius=4)

        # Ekstraksi Data Simpul Fokus
        current_step_info = self.csp_timeline[self.csp_current_step] if self.csp_timeline else {}
        focus_info = current_step_info
        is_node_clicked = False
        if self.selected_node_id is not None and self.selected_node_id in self.csp_tree:
            sel_nd = self.csp_tree[self.selected_node_id]
            is_node_clicked = True
            focus_info = {
                "step": current_step_info.get("step", 0),
                "type": sel_nd.get("status", "ASSIGN"),
                "node_id": self.selected_node_id,
                "var": sel_nd.get("var"),
                "val": sel_nd.get("val"),
                "reason": sel_nd.get("reason", ""),
            }

        nid = focus_info.get("node_id")
        nd = self.csp_tree.get(nid, {}) if nid is not None else {}
        st_type = focus_info.get("type", nd.get("status", "ASSIGN"))
        st_reason = focus_info.get("reason", nd.get("reason", ""))
        var_name = focus_info.get("var", nd.get("var", ""))
        val_name = focus_info.get("val", nd.get("val", ""))
        cur_step_num = focus_info.get("step", 0) + 1
        parent_id = nd.get("parent_id")

        # Pinned Header Card 3 (64px)
        c3_hdr_h = 64
        c3_hdr_rect = pygame.Rect(c3_rect.x, c3_rect.y, c3_rect.width, c3_hdr_h)
        pygame.draw.rect(screen, (20, 26, 40), c3_hdr_rect, border_top_left_radius=4, border_top_right_radius=4)
        pygame.draw.line(screen, (38, 52, 74), (c3_hdr_rect.x, c3_hdr_rect.bottom), (c3_hdr_rect.right, c3_hdr_rect.bottom), 1)

        max_hdr_w = c3_rect.width - 16

        # Judul Pinned Header (anti-overflow)
        t_card3_title = f"3. Simpul #{nid} (Langkah {cur_step_num})" if nid is not None else "3. Analisis Langkah CSP"
        if font_bubble.size(t_card3_title)[0] > max_hdr_w:
            while len(t_card3_title) > 4 and font_bubble.size(t_card3_title + "...")[0] > max_hdr_w:
                t_card3_title = t_card3_title[:-1]
            t_card3_title += "..."
        screen.blit(font_bubble.render(t_card3_title, True, COLOR_TEXT_HEADING), (c3_rect.x + 8, c3_rect.y + 4))

        # Status Badge & Color
        if st_type in ("ASSIGN", "NODE"):
            badge_txt = "STATUS: [DIPILIH / MRV & LCV]"
            col_type = (85, 185, 245)
        elif st_type in ("PRUNE", "PRUNED"):
            badge_txt = "STATUS: [DIPANGKAS / FORWARD CHECKING]"
            col_type = (235, 95, 110)
        elif st_type == "BACKTRACK":
            badge_txt = "STATUS: [MUNDUR / DEAD-END BACKTRACK]"
            col_type = (235, 175, 75)
        elif st_type == "SOLUTION":
            badge_txt = "STATUS: [SOLUSI LENGKAP KONSISTEN]"
            col_type = (75, 230, 135)
        else:
            badge_txt = "STATUS: [START / INISIALISASI ROOT]"
            col_type = (160, 180, 210)

        badge_fnt = font_bubble if font_sm.size(badge_txt)[0] > max_hdr_w else font_sm
        screen.blit(badge_fnt.render(badge_txt, True, col_type), (c3_rect.x + 8, c3_rect.y + 22))

        # Sub-info Variabel (anti-overflow dengan pemotongan rapi)
        if var_name and var_name != "ROOT":
            lbl_var = f"Variabel: {var_name}  |  Nilai: {val_name}"
        elif var_name == "ROOT":
            lbl_var = "Inisialisasi Pohon Pencarian CSP (Root)"
        else:
            lbl_var = "Pilih simpul pada kanvas pohon untuk analisis rinci"
        if font_tiny.size(lbl_var)[0] > max_hdr_w:
            while len(lbl_var) > 4 and font_tiny.size(lbl_var + "...")[0] > max_hdr_w:
                lbl_var = lbl_var[:-1]
            lbl_var += "..."
        screen.blit(font_tiny.render(lbl_var, True, COLOR_TEXT_ACCENT), (c3_rect.x + 8, c3_rect.y + 43))

        # Body Scrollable Content
        body_rect = pygame.Rect(c3_rect.x + 6, c3_hdr_rect.bottom + 4, c3_rect.width - 12, c3_rect.height - c3_hdr_h - 8)
        old_clip_body = screen.get_clip()
        screen.set_clip(body_rect.clip(old_clip_body))

        draw_y = body_rect.y + 4 - int(self.sidebar_scroll_y)
        max_txt_w = body_rect.width - 18

        # Ekstraksi Saudara (Siblings) dan Anakan (Children)
        siblings_pruned = []
        siblings_assigned = []
        if parent_id is not None and parent_id in self.csp_tree:
            p_node = self.csp_tree[parent_id]
            for sid in p_node.get("children", []):
                s_nd = self.csp_tree.get(sid, {})
                s_status = s_nd.get("status", "")
                s_val = s_nd.get("val")
                s_reason = s_nd.get("reason", "")
                if sid != nid:
                    if s_status == "PRUNED":
                        siblings_pruned.append((s_val, s_reason))
                    elif s_status in ("ASSIGN", "SOLUTION"):
                        siblings_assigned.append((s_val, s_status))

        children_pruned = []
        children_assigned = []
        for cid in nd.get("children", []):
            c_nd = self.csp_tree.get(cid, {})
            c_status = c_nd.get("status", "")
            c_val = c_nd.get("val")
            c_reason = c_nd.get("reason", "")
            if c_status == "PRUNED":
                children_pruned.append((c_val, c_reason))
            elif c_status in ("ASSIGN", "SOLUTION"):
                children_assigned.append((c_val, c_status))

        # Konten Narasi Penjelasan Akademis Terstruktur
        if st_type in ("ASSIGN", "SOLUTION"):
            # ----------------- SECTION A: MENGAPA ANAKAN INI DIPILIH ----------------- #
            draw_y = self._draw_multiline_text(screen, "A. MENGAPA ANAKAN INI DIPILIH:", body_rect.x, draw_y, max_txt_w, font_bubble, (100, 205, 255))
            draw_y += 2

            mrv_txt = (
                f"1. Variabel '{var_name}' Dipilih (MRV Heuristic):\n"
                f"Algoritma menerapkan Minimum Remaining Values (fail-first). Variabel ini dipilih terlebih dahulu karena memiliki domain legal tersisa paling sedikit/kritis di antara variabel yang belum terisi. Menetapkan variabel paling restriktif lebih dini meminimalkan cabang pohon dan mendeteksi jalan buntu lebih cepat."
            )
            draw_y = self._draw_multiline_text(screen, mrv_txt, body_rect.x + 4, draw_y, max_txt_w - 4, font_tiny, COLOR_TEXT_PRIMARY)
            draw_y += 3

            lcv_txt = (
                f"2. Nilai '{val_name}' Dipilih (LCV Heuristic):\n"
                f"Heuristik Least Constraining Value mengurutkan nilai domain dan memprioritaskan '{val_name}' karena membatasi paling sedikit nilai variabel anggota skuad berikutnya (0 konflik batasan)."
            )
            draw_y = self._draw_multiline_text(screen, lcv_txt, body_rect.x + 4, draw_y, max_txt_w - 4, font_tiny, COLOR_TEXT_PRIMARY)
            draw_y += 3

            # Alasan Batasan Konkret
            c_detail = "Mematuhi seluruh batasan C1-C8."
            if "char_type" in str(var_name):
                c_detail = f"Mematuhi aturan C5 (Keunikan Role): Tidak ada duplikasi tipe '{val_name}' dalam skuad. Sinergi peran tim seimbang."
            elif "hp" in str(var_name):
                c_detail = f"Mematuhi aturan C1 (Budget HP Skuad <= 200): Nilai HP {val_name} menjaga total darah akumulatif skuad tetap legal."
            elif "potions" in str(var_name):
                c_detail = f"Mematuhi aturan C2 (Budget Potion <= 2): Alokasi ramuan {val_name} tidak melampaui kuota inventaris skuad."
            elif "atk_bonus" in str(var_name):
                c_detail = f"Mematuhi aturan C3 (Budget Bonus ATK <= 12): Alokasi +{val_name} ATK berada dalam batas regulasi kekuatan."
            elif "def_bonus" in str(var_name):
                c_detail = f"Mematuhi aturan C4 (Budget Bonus DEF <= 8): Alokasi +{val_name} DEF berada dalam batas legal pertahanan."
            elif "eval_profile" in str(var_name):
                c_detail = f"Mematuhi aturan C6-C8 (Sinergi Archetype): Profil AI '{val_name}' cocok dengan peran taktis NPC di tim."

            c_txt = f"3. Validasi Konsistensi Batasan C1-C8:\n{c_detail}"
            draw_y = self._draw_multiline_text(screen, c_txt, body_rect.x + 4, draw_y, max_txt_w - 4, font_tiny, (140, 235, 175))
            draw_y += 6

            # ----------------- SECTION B: MENGAPA ANAKAN LAIN DI-PRUNE ----------------- #
            draw_y = self._draw_multiline_text(screen, "B. MENGAPA ANAKAN LAIN DI-PRUNE:", body_rect.x, draw_y, max_txt_w, font_bubble, (255, 130, 140))
            draw_y += 2

            if siblings_pruned:
                draw_y = self._draw_multiline_text(
                    screen,
                    "Forward Checking menguji alternatif nilai domain lain pada variabel ini dan memotong cabang-cabang yang melanggar batasan:",
                    body_rect.x + 4, draw_y, max_txt_w - 4, font_tiny, COLOR_TEXT_SECONDARY
                )
                draw_y += 2
                for p_val, p_reason in siblings_pruned:
                    p_line = f"• Nilai '{p_val}': Dipangkas karena {p_reason}"
                    draw_y = self._draw_multiline_text(screen, p_line, body_rect.x + 8, draw_y, max_txt_w - 8, font_tiny, (255, 165, 170))
                    draw_y += 1
                draw_y += 2
                ff_txt = "Prinsip Fail-First: Cabang-cabang di atas langsung dipangkas tanpa dieksplorasi lebih jauh, menghemat pencarian secara eksponensial."
                draw_y = self._draw_multiline_text(screen, ff_txt, body_rect.x + 4, draw_y, max_txt_w - 4, font_tiny, (200, 215, 235))
            else:
                no_p_txt = f"Tidak ada anakan saudara yang di-prune pada tahap ini. Nilai '{val_name}' merupakan kandidat pertama dari heuristik LCV yang langsung lolos uji konsistensi C1-C8."
                draw_y = self._draw_multiline_text(screen, no_p_txt, body_rect.x + 4, draw_y, max_txt_w - 4, font_tiny, COLOR_TEXT_PRIMARY)

            if children_pruned:
                draw_y += 4
                cp_header = f"Eksplorasi Anakan Lanjutan: Ditemukan {len(children_pruned)} anakan cabang di bawah simpul ini yang dipangkas:"
                draw_y = self._draw_multiline_text(screen, cp_header, body_rect.x + 4, draw_y, max_txt_w - 4, font_tiny, (245, 190, 120))
                for cp_val, cp_reason in children_pruned[:4]:
                    cp_line = f"• Cabang '{cp_val}': {cp_reason}"
                    draw_y = self._draw_multiline_text(screen, cp_line, body_rect.x + 8, draw_y, max_txt_w - 8, font_tiny, (255, 185, 185))
                    draw_y += 1
                if len(children_pruned) > 4:
                    draw_y = self._draw_multiline_text(screen, f"• ... dan {len(children_pruned) - 4} nilai domain lainnya.", body_rect.x + 8, draw_y, max_txt_w - 8, font_tiny, COLOR_TEXT_SECONDARY)

            draw_y += 6

        elif st_type in ("PRUNE", "PRUNED"):
            # ----------------- SECTION A: MENGAPA ANAKAN INI DI-PRUNE ----------------- #
            draw_y = self._draw_multiline_text(screen, "A. MENGAPA ANAKAN INI DI-PRUNE:", body_rect.x, draw_y, max_txt_w, font_bubble, (255, 115, 125))
            draw_y += 2

            p_main_txt = (
                f"1. Pelanggaran Batasan Spesifik:\n"
                f"Nilai '{val_name}' untuk variabel '{var_name}' ditolak karena: {st_reason if st_reason else 'Melanggar aturan batasan CSP'}."
            )
            draw_y = self._draw_multiline_text(screen, p_main_txt, body_rect.x + 4, draw_y, max_txt_w - 4, font_tiny, (255, 175, 180))
            draw_y += 3

            p_fc_txt = (
                f"2. Mekanisme Forward Checking (Fail-First):\n"
                f"Sebelum melakukan penugasan mendalam, Forward Checking mendeteksi bahwa nilai '{val_name}' menghasilkan inkonsistensi terhadap variabel yang telah diisi sebelumnya. Cabang ini langsung diputus (pruned) seketika tanpa membentuk sub-pohon, mencegah pemborosan komputasi (state space explosion)."
            )
            draw_y = self._draw_multiline_text(screen, p_fc_txt, body_rect.x + 4, draw_y, max_txt_w - 4, font_tiny, COLOR_TEXT_PRIMARY)
            draw_y += 6

            # ----------------- SECTION B: ALTERNATIF YANG DIPILIH ----------------- #
            draw_y = self._draw_multiline_text(screen, "B. ANAKAN LAIN YANG DIPILIH / KONSISTEN:", body_rect.x, draw_y, max_txt_w, font_bubble, (100, 205, 255))
            draw_y += 2

            if siblings_assigned:
                draw_y = self._draw_multiline_text(screen, "Sebagai pengganti cabang yang gagal ini, algoritma memilih anakan berikut:", body_rect.x + 4, draw_y, max_txt_w - 4, font_tiny, COLOR_TEXT_SECONDARY)
                for a_val, a_stat in siblings_assigned:
                    a_line = f"• Nilai '{a_val}' [DIPILIH]: Lolos konsistensi batasan C1-C8 dan meminimalkan konflik domain ke depan (LCV)."
                    draw_y = self._draw_multiline_text(screen, a_line, body_rect.x + 8, draw_y, max_txt_w - 8, font_tiny, (130, 230, 170))
                    draw_y += 1
            else:
                draw_y = self._draw_multiline_text(screen, "Belum ada anakan saudara lain yang lolos pada langkah ini. Algoritma melanjutkan evaluasi nilai domain tersisa.", body_rect.x + 4, draw_y, max_txt_w - 4, font_tiny, COLOR_TEXT_PRIMARY)

            if siblings_pruned:
                draw_y += 3
                draw_y = self._draw_multiline_text(screen, "Alternatif nilai saudara lain yang juga dipangkas:", body_rect.x + 4, draw_y, max_txt_w - 4, font_tiny, COLOR_TEXT_SECONDARY)
                for sp_val, sp_reason in siblings_pruned[:3]:
                    sp_line = f"• Nilai '{sp_val}': {sp_reason}"
                    draw_y = self._draw_multiline_text(screen, sp_line, body_rect.x + 8, draw_y, max_txt_w - 8, font_tiny, (255, 170, 170))
                    draw_y += 1

            draw_y += 6

        elif st_type == "BACKTRACK":
            # ----------------- SECTION A: MENGAPA TERJADI BACKTRACK ----------------- #
            draw_y = self._draw_multiline_text(screen, "A. MENGAPA TERJADI BACKTRACK (MUNDUR):", body_rect.x, draw_y, max_txt_w, font_bubble, (255, 180, 80))
            draw_y += 2

            bt_txt = (
                f"1. Kondisi Dead-End (Jalan Buntu):\n"
                f"Penugasan '{var_name} = {val_name}' sempat dicoba karena lolos batasan lokal. Namun saat algoritma melangkah mengeksplorasi variabel berikutnya, seluruh nilai domain anak di bawahnya mengalami kegagalan / ter-prune habis (domain wipeout).\n\n"
                f"2. Pembatalan Penugasan (Undo Assignment):\n"
                f"Karena tidak ada anakan di bawah cabang ini yang mampu membentuk skuad legal lengkap, cabang ini terbukti jalan buntu. Algoritma membatalkan penugasan '{var_name} = {val_name}', mengembalikan domain, dan mundur (backtrack) ke simpul induk untuk mencoba nilai alternatif berikutnya."
            )
            draw_y = self._draw_multiline_text(screen, bt_txt, body_rect.x + 4, draw_y, max_txt_w - 4, font_tiny, COLOR_TEXT_PRIMARY)
            draw_y += 6

        else:
            # ROOT atau status inisialisasi
            draw_y = self._draw_multiline_text(screen, "A. INISIALISASI POHON PENCARIAN CSP:", body_rect.x, draw_y, max_txt_w, font_bubble, COLOR_TEXT_HEADING)
            draw_y += 2
            root_txt = (
                "Pencarian dimulai dari simpul ROOT.\n"
                "1. Arc Consistency (AC-3): Domain awal seluruh variabel disaring terlebih dahulu agar nilai yang mustahil dibuang sebelum pencarian dimulai.\n"
                "2. Pemilihan Variabel Pertama (MRV): Algoritma menghitung ukuran domain setiap variabel yang belum terisi dan memilih variabel dengan opsi legal paling sedikit untuk dieksplorasi."
            )
            draw_y = self._draw_multiline_text(screen, root_txt, body_rect.x + 4, draw_y, max_txt_w - 4, font_tiny, COLOR_TEXT_PRIMARY)
            draw_y += 6

        # ----------------- SECTION C / PETUNJUK INTERAKSI ----------------- #
        draw_y = self._draw_multiline_text(screen, "PETUNJUK INTERAKSI:", body_rect.x, draw_y, max_txt_w, font_bubble, COLOR_TEXT_SECONDARY)
        draw_y += 2
        hint_text = (
            "• Scroll/Touchpad: Gerakkan 2 jari atau putar mouse wheel di atas panel ini untuk menggulir teks.\n"
            "• Klik Simpul: Klik simpul mana saja pada kanvas pohon untuk mengunci analisis simpul tersebut.\n"
            "• Klik Kanvas Kosong: Untuk melepaskan kunci dan kembali mengikuti langkah timeline otomatis."
        )
        draw_y = self._draw_multiline_text(screen, hint_text, body_rect.x + 4, draw_y, max_txt_w - 4, font_tiny, (160, 175, 195))
        draw_y += 8

        # Hitung Total Tinggi Konten & Max Scroll
        total_content_height = (draw_y + int(self.sidebar_scroll_y)) - (body_rect.y + 4)
        self.max_sidebar_scroll = max(0.0, float(total_content_height - body_rect.height + 12))

        # Kembalikan clipping layar
        screen.set_clip(old_clip_body)

        # Gambar Scrollbar Tipis di Sisi Kanan Body jika konten melebihi area
        if total_content_height > body_rect.height:
            sb_track = pygame.Rect(body_rect.right - 4, body_rect.y, 4, body_rect.height)
            pygame.draw.rect(screen, (22, 28, 40), sb_track, border_radius=2)

            thumb_ratio = max(0.12, min(1.0, body_rect.height / float(total_content_height)))
            thumb_h = max(18, int(body_rect.height * thumb_ratio))
            max_travel = body_rect.height - thumb_h
            scroll_pct = self.sidebar_scroll_y / max(1.0, self.max_sidebar_scroll)
            thumb_y = body_rect.y + int(scroll_pct * max_travel)
            sb_thumb = pygame.Rect(body_rect.right - 4, thumb_y, 4, thumb_h)
            pygame.draw.rect(screen, (70, 140, 195), sb_thumb, border_radius=2)

        screen.set_clip(old_clip_sb)

    # ----------------------------------------------------------------------- #
    # TAB 2: Visualisasi Local Search Trajectory & Konvergensi
    # ----------------------------------------------------------------------- #
    def _draw_local_search_view(self, screen: pygame.Surface, font_sm: pygame.font.Font, font_bubble: pygame.font.Font, font_title: pygame.font.Font, font_tiny: pygame.font.Font):
        if not self.ls_history:
            no_data = font_bubble.render("Belum ada data riwayat Local Search.", True, COLOR_TEXT_SECONDARY)
            screen.blit(no_data, no_data.get_rect(center=self.rect_canvas.center))
            return

        rc = self.rect_canvas
        total_steps = len(self.ls_history)
        cur_idx = min(self.ls_current_step, total_steps - 1)
        cur_frame = self.ls_history[cur_idx]

        # Layout Split: Kiri (Grafik Konvergensi 53%), Kanan (Kolom Penjelasan Teori & Live Skuad 47%)
        split_x = rc.x + int(rc.width * 0.53)
        graph_rect = pygame.Rect(rc.x + 14, rc.y + 12, (split_x - rc.x) - 20, rc.height - 24)
        right_panel_rect = pygame.Rect(split_x + 6, rc.y + 12, rc.right - split_x - 20, rc.height - 24)

        # 1. GAMBAR GRAFIK KONVERGENSI LENGKAP DENGAN SKALA & LEGEND
        self._draw_convergence_graph(screen, graph_rect, cur_idx, font_sm, font_bubble, font_tiny, font_title)

        # 2. GAMBAR KOLOM PENJELASAN TEORI & SKUAD LIVE DI SAMPING KANAN
        self._draw_local_search_right_panel(screen, right_panel_rect, cur_frame, cur_idx, total_steps, font_sm, font_bubble, font_tiny, font_title)

    def _draw_convergence_graph(self, screen: pygame.Surface, rect: pygame.Rect, cur_idx: int, font_sm: pygame.font.Font, font_bubble: pygame.font.Font, font_tiny: pygame.font.Font, font_title: pygame.font.Font):
        """Menggambar grafik 2D konvergensi Fitness & Difficulty terhadap langkah iterasi."""
        # Box background
        pygame.draw.rect(screen, (14, 18, 28), rect, border_radius=6)
        pygame.draw.rect(screen, COLOR_CARD_BORDER, rect, 1, border_radius=6)

        # Judul & Subjudul Grafik (tanpa emoji)
        t_g = font_title.render(f"Konvergensi: {self.ls_algo_name}", True, COLOR_TEXT_HEADING)
        screen.blit(t_g, (rect.x + 16, rect.y + 12))
        t_sub = font_tiny.render("Y: Difficulty  |  X: Iterasi", True, COLOR_TEXT_SECONDARY)
        screen.blit(t_sub, (rect.x + 16, rect.y + 34))

        # Margin sumbu
        margin_l = 62
        margin_r = 20
        margin_t = 56
        margin_b = 64
        plot_w = rect.width - margin_l - margin_r
        plot_h = rect.height - margin_t - margin_b

        origin_x = rect.x + margin_l
        origin_y = rect.y + margin_t + plot_h

        # Garis Sumbu X dan Y
        pygame.draw.line(screen, (70, 85, 115), (origin_x, origin_y), (origin_x + plot_w, origin_y), 2)
        pygame.draw.line(screen, (70, 85, 115), (origin_x, origin_y), (origin_x, origin_y - plot_h), 2)

        # Skala Angka Sumbu Y Vertikal
        ticks_y = [
            (1.00, "1.00", COLOR_TEXT_SECONDARY),
            (0.75, "0.75", COLOR_TEXT_SECONDARY),
            (self.target_difficulty, f"{self.target_difficulty:.2f}", (210, 165, 50)),
            (0.25, "0.25", COLOR_TEXT_SECONDARY),
            (0.00, "0.00", COLOR_TEXT_SECONDARY),
        ]
        for val, lbl_str, col_tick in ticks_y:
            ty = origin_y - int(plot_h * val)
            # Garis grid horizontal tipis
            pygame.draw.line(screen, (32, 42, 58), (origin_x + 1, ty), (origin_x + plot_w, ty), 1)
            # Tanda tick kecil di sumbu
            pygame.draw.line(screen, col_tick, (origin_x - 4, ty), (origin_x, ty), 2)
            s_lbl = font_tiny.render(lbl_str, True, col_tick)
            screen.blit(s_lbl, (origin_x - s_lbl.get_width() - 8, ty - s_lbl.get_height() // 2))

        # Garis Target Ideal 0.55
        target_y = origin_y - int(plot_h * self.target_difficulty)
        pygame.draw.line(screen, (210, 165, 50), (origin_x, target_y), (origin_x + plot_w, target_y), 2)
        lbl_target = font_tiny.render(f"Target ({self.target_difficulty:.2f})", True, (210, 165, 50))
        screen.blit(lbl_target, (origin_x + plot_w - lbl_target.get_width() - 6, target_y - 14))

        # Label Sumbu X
        lbl_x = font_tiny.render("Iterasi / Generasi -->", True, COLOR_TEXT_SECONDARY)
        screen.blit(lbl_x, (origin_x + (plot_w - lbl_x.get_width()) // 2, origin_y + 8))

        # Plot Garis Konvergensi
        total_steps = len(self.ls_history)
        if total_steps > 1:
            points = []
            for i in range(cur_idx + 1):
                frame = self.ls_history[i]
                diff = frame.get("diff", 0.55)
                px = origin_x + int((i / float(max(1, total_steps - 1))) * plot_w)
                py = origin_y - int(max(0.0, min(1.0, diff)) * plot_h)
                points.append((px, py))

            # Gambar kurva halus
            if len(points) >= 2:
                pygame.draw.lines(screen, (45, 150, 245), False, points, 3)
                pygame.draw.aalines(screen, (120, 205, 255), False, points)

            # Titik-titik event khusus
            for i, pt in enumerate(points):
                ev = self.ls_history[i].get("event", "")
                if ev in ("LOCAL_MAXIMUM", "PLATEAU_STOP"):
                    pygame.draw.circle(screen, (255, 60, 70), pt, 6)
                    pygame.draw.circle(screen, (255, 255, 255), pt, 2)
                elif ev == "SIDEWAYS":
                    pygame.draw.rect(screen, (245, 180, 40), (pt[0] - 4, pt[1] - 4, 8, 8))
                elif ev == "SA_ACCEPT_WORSE":
                    pygame.draw.circle(screen, (200, 90, 245), pt, 5)
                elif i == cur_idx:
                    pygame.draw.circle(screen, (255, 230, 80), pt, 7)
                    pygame.draw.circle(screen, (30, 30, 30), pt, 3)

        # Legend Visual di Bawah Grafik (tanpa emoji, wrap jika sempit)
        leg_y = origin_y + 26
        leg_items = [
            ((45, 150, 245), "- Trajektori"),
            ((210, 165, 50), "- Target"),
            ((210, 165, 40), "= Sideways"),
            ((225, 60, 70), "o Optimum"),
        ]
        lx = origin_x
        ly = leg_y
        for col, l_text in leg_items:
            s_leg = font_tiny.render(l_text, True, col)
            if lx + s_leg.get_width() > rect.right - 10:
                lx = origin_x
                ly += 16
            screen.blit(s_leg, (lx, ly))
            lx += s_leg.get_width() + 14

    def _draw_local_search_right_panel(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        cur_frame: Dict[str, Any],
        cur_idx: int,
        total_steps: int,
        font_sm: pygame.font.Font,
        font_bubble: pygame.font.Font,
        font_tiny: pygame.font.Font,
        font_title: pygame.font.Font
    ):
        """Menampilkan kolom penjelasan teori & analisis tim di sebelah kanan grafik."""
        pygame.draw.rect(screen, (16, 20, 30), rect, border_radius=6)
        pygame.draw.rect(screen, COLOR_CARD_BORDER, rect, 1, border_radius=6)

        old_clip_ls = screen.get_clip()
        screen.set_clip(rect.clip(old_clip_ls))

        # Bagi vertikal: Atas (Panel Teori & Logika Langkah 48%), Bawah (Live Skuad 50%)
        th_h = int(rect.height * 0.48)
        th_rect = pygame.Rect(rect.x + 8, rect.y + 8, rect.width - 16, th_h)
        sq_rect = pygame.Rect(rect.x + 8, th_rect.bottom + 6, rect.width - 16, rect.bottom - th_rect.bottom - 14)

        # ----------------- PANEL 1: TEORI & LOGIKA LANGKAH ----------------- #
        pygame.draw.rect(screen, COLOR_CARD_BG, th_rect, border_radius=4)
        pygame.draw.rect(screen, COLOR_CARD_BORDER, th_rect, 1, border_radius=4)

        old_clip_th = screen.get_clip()
        screen.set_clip(th_rect.clip(old_clip_th))

        t_header = font_bubble.render(f"Teori & Analisis (Step {cur_idx + 1}/{total_steps})", True, COLOR_TEXT_HEADING)
        screen.blit(t_header, (th_rect.x + 10, th_rect.y + 6))

        diff_score = cur_frame.get("diff", 0.55)
        fit_score = cur_frame.get("fitness", 0.0)
        ev_name = cur_frame.get("event", "OPTIMIZING")
        ev_detail = cur_frame.get("detail", "")

        col_ev = (210, 165, 40) if ev_name == "SIDEWAYS" else ((225, 70, 80) if ev_name in ("PLATEAU_STOP", "LOCAL_MAXIMUM") else ((80, 210, 130) if ev_name == "IMPROVE" else COLOR_TEXT_ACCENT))
        badge_ev = font_sm.render(f"EVENT: [{ev_name}]", True, col_ev)
        screen.blit(badge_ev, (th_rect.x + 10, th_rect.y + 26))

        ty_th = th_rect.y + 45
        stat_txt = f"Difficulty: {diff_score:.4f} | Fitness: {fit_score:+.4f}"
        ty_th = self._draw_multiline_text(screen, stat_txt, th_rect.x + 10, ty_th, th_rect.width - 20, font_tiny, COLOR_TEXT_PRIMARY)

        # Formula Fungsi Objektif
        rumus_txt = "Fitness = -|Difficulty - 0.55| (Target=0.00)"
        ty_th = self._draw_multiline_text(screen, rumus_txt, th_rect.x + 10, ty_th, th_rect.width - 20, font_tiny, COLOR_TEXT_ACCENT)
        ty_th += 2

        # Penjelasan Teori Akademis Event
        if ev_name == "PLATEAU_STOP":
            teori_txt = "Plateau: Batas Sideways Move (15 langkah) tercapai. Algoritma berhenti dan menetapkan konfigurasi sebagai Optimum Lokal."
            col_teori = (225, 140, 145)
        elif ev_name == "SIDEWAYS":
            teori_txt = "Sideways Move: langkah mendatar pada plateau (fitness sama). Mencegah agen berhenti terlalu dini di shoulder."
            col_teori = (225, 195, 120)
        elif ev_name == "IMPROVE":
            teori_txt = "Ascent: konfigurasi tetangga menaikkan fitness. Difficulty mendekati target 0.55."
            col_teori = (130, 220, 165)
        elif ev_name == "LOCAL_MAXIMUM":
            teori_txt = "Local Optimum: seluruh tetangga fitness lebih rendah. Hill climbing berhenti di puncak lokal."
            col_teori = (225, 120, 130)
        elif ev_name == "SA_ACCEPT_WORSE":
            teori_txt = "Simulated Annealing: menerima tetangga lebih buruk berdasarkan P=exp(dE/T) untuk melompati lembah lokal."
            col_teori = (195, 145, 230)
        else:
            teori_txt = "Inisialisasi: state awal dari konfigurasi legal hasil CSP."
            col_teori = COLOR_TEXT_PRIMARY

        ty_th = self._draw_multiline_text(screen, teori_txt, th_rect.x + 10, ty_th, th_rect.width - 20, font_tiny, col_teori)

        # Uraian Aksi
        if ev_detail and ty_th + 14 < th_rect.bottom:
            ty_th += 2
            self._draw_multiline_text(screen, f"Aksi: {ev_detail}", th_rect.x + 10, ty_th, th_rect.width - 20, font_tiny, COLOR_TEXT_PRIMARY)

        screen.set_clip(old_clip_th)

        # ----------------- PANEL 2: LIVE SKUAD NPC ----------------- #
        pygame.draw.rect(screen, (18, 22, 34), sq_rect, border_radius=4)
        pygame.draw.rect(screen, COLOR_CARD_BORDER, sq_rect, 1, border_radius=4)

        old_clip_sq = screen.get_clip()
        screen.set_clip(sq_rect.clip(old_clip_sq))

        screen.blit(font_bubble.render("Skuad Teroptimasi", True, COLOR_TEXT_ACCENT), (sq_rect.x + 10, sq_rect.y + 6))

        state = cur_frame.get("state", {})
        members = state.get("members", [])
        m_y = sq_rect.y + 28
        avail_h = sq_rect.height - 34
        card_h = min(52, max(42, avail_h // max(1, len(members))))

        for idx, m in enumerate(members):
            if m_y + card_h > sq_rect.bottom:
                break
            m_card = pygame.Rect(sq_rect.x + 8, m_y, sq_rect.width - 16, card_h - 4)
            pygame.draw.rect(screen, COLOR_CARD_BG, m_card, border_radius=4)
            pygame.draw.rect(screen, COLOR_CARD_BORDER, m_card, 1, border_radius=4)

            ctype = m.get("char_type", "warrior").upper()
            hp = m.get("hp", 100)
            pot = m.get("potions", 0)
            atk = m.get("atk_bonus", 0)
            prof = m.get("eval_profile", "BALANCED")

            s_name = font_bubble.render(f"NPC {idx+1}: {ctype}", True, COLOR_TEXT_HEADING)
            s_prof = font_tiny.render(f"AI: {prof}", True, COLOR_TEXT_ACCENT)
            screen.blit(s_name, (m_card.x + 8, m_card.y + 4))
            screen.blit(s_prof, (m_card.right - s_prof.get_width() - 8, m_card.y + 5))

            stats_str = f"HP: {hp}   Pot: {pot}   ATK: +{atk}"
            s_stat = font_tiny.render(stats_str, True, COLOR_TEXT_PRIMARY)
            screen.blit(s_stat, (m_card.x + 8, m_card.y + 22))

            m_y += card_h

        screen.set_clip(old_clip_sq)
        screen.set_clip(old_clip_ls)

    # ----------------------------------------------------------------------- #
    # Playback Controls Bar di Dasar Modal
    # ----------------------------------------------------------------------- #
    def _draw_bottom_playback_controls(self, screen: pygame.Surface, mx: int, my: int, mw: int, mh: int, font_sm: pygame.font.Font, font_bubble: pygame.font.Font):
        """Menggambar control bar timeline di bawah modal."""
        ctrl_rect = pygame.Rect(mx, my, mw, mh)
        pygame.draw.rect(screen, COLOR_HEADER_BG, ctrl_rect, border_bottom_left_radius=10, border_bottom_right_radius=10)
        pygame.draw.line(screen, (38, 50, 70), (mx, my), (mx + mw, my), 1)

        # Hitung Step Aktif & Maksimum
        if self.active_tab == "CSP":
            cur_s = self.csp_current_step
            max_s = max(0, len(self.csp_timeline) - 1)
        else:
            cur_s = self.ls_current_step
            max_s = max(0, len(self.ls_history) - 1)

        btn_y = my + 14
        btn_h = 36

        # 1. Tombol [⏮️ Step Back / Previous]
        self.rect_btn_step_back = pygame.Rect(mx + 20, btn_y, 44, btn_h)
        pygame.draw.rect(screen, (30, 40, 58), self.rect_btn_step_back, border_radius=6)
        bx = self.rect_btn_step_back.centerx
        by = self.rect_btn_step_back.centery
        # Garis vertikal kiri tebal + segitiga panah kiri (Previous)
        pygame.draw.line(screen, COLOR_TEXT_PRIMARY, (bx - 7, by - 6), (bx - 7, by + 6), 3)
        pygame.draw.polygon(screen, COLOR_TEXT_PRIMARY, [(bx + 6, by - 7), (bx + 6, by + 7), (bx - 4, by)])

        # 2. Tombol [⏯️ Play / Pause]
        self.rect_btn_play = pygame.Rect(mx + 72, btn_y, 74, btn_h)
        col_play = (35, 120, 90) if self.is_playing else (38, 130, 128)
        pygame.draw.rect(screen, col_play, self.rect_btn_play, border_radius=6)
        t_play = "PAUSE" if self.is_playing else "PLAY"
        screen.blit(font_bubble.render(t_play, True, (255, 255, 255)), (self.rect_btn_play.x + 14, self.rect_btn_play.y + 6))

        # 3. Tombol [Step Forward / Next ⏭️]
        self.rect_btn_step_fwd = pygame.Rect(mx + 154, btn_y, 44, btn_h)
        pygame.draw.rect(screen, (30, 40, 58), self.rect_btn_step_fwd, border_radius=6)
        fx = self.rect_btn_step_fwd.centerx
        fy = self.rect_btn_step_fwd.centery
        # Segitiga panah kanan + garis vertikal kanan tebal (Next)
        pygame.draw.polygon(screen, COLOR_TEXT_PRIMARY, [(fx - 6, fy - 7), (fx - 6, fy + 7), (fx + 4, fy)])
        pygame.draw.line(screen, COLOR_TEXT_PRIMARY, (fx + 7, fy - 6), (fx + 7, fy + 6), 3)

        # 4. Tombol [🔄 Ulang]
        self.rect_btn_reset = pygame.Rect(mx + 206, btn_y, 64, btn_h)
        pygame.draw.rect(screen, (35, 45, 62), self.rect_btn_reset, border_radius=6)
        screen.blit(font_sm.render("RESET", True, COLOR_TEXT_PRIMARY), (self.rect_btn_reset.x + 12, self.rect_btn_reset.y + 8))

        # 5. Tombol Speed
        self.rect_btn_speed = pygame.Rect(mx + 278, btn_y, 60, btn_h)
        pygame.draw.rect(screen, (28, 38, 55), self.rect_btn_speed, border_radius=6)
        sp_text = "MAX" if self.playback_speed > 100 else f"{self.playback_speed}x"
        screen.blit(font_sm.render(sp_text, True, COLOR_TEXT_HEADING), (self.rect_btn_speed.x + 14, self.rect_btn_speed.y + 8))

        # 6. Scrubber Timeline Slider
        track_x = mx + 356
        track_w = mw - 356 - 160
        track_y = my + 26
        track_h = 12
        self.rect_scrubber_track = pygame.Rect(track_x, track_y, track_w, track_h)

        pygame.draw.rect(screen, (22, 28, 42), self.rect_scrubber_track, border_radius=6)
        progress = (cur_s / float(max_s)) if max_s > 0 else 1.0
        fill_w = max(6, int(track_w * progress))
        pygame.draw.rect(screen, COLOR_TAB_ACTIVE_BG, (track_x, track_y, fill_w, track_h), border_radius=6)

        # Pin Handle Knop
        pin_x = track_x + fill_w
        pygame.draw.circle(screen, (235, 240, 245), (pin_x, track_y + track_h // 2), 8)
        pygame.draw.circle(screen, COLOR_TAB_ACTIVE_BG, (pin_x, track_y + track_h // 2), 5)

        # Indikator Teks Langkah
        step_lbl = font_sm.render(f"Step {cur_s + 1}/{max_s + 1}", True, COLOR_TEXT_PRIMARY)
        screen.blit(step_lbl, (track_x + track_w + 16, my + 22))

    # ----------------------------------------------------------------------- #
    # Floating Zoom Controls
    # ----------------------------------------------------------------------- #
    def _draw_zoom_controls(self, screen: pygame.Surface, font_sm: pygame.font.Font):
        rc = self.rect_canvas
        bx = rc.right - 135
        by = rc.y + 12

        self.rect_btn_zoom_in = pygame.Rect(bx, by, 28, 28)
        self.rect_btn_zoom_out = pygame.Rect(bx + 32, by, 28, 28)
        self.rect_btn_zoom_reset = pygame.Rect(bx + 64, by, 60, 28)

        pygame.draw.rect(screen, (22, 30, 45), self.rect_btn_zoom_in, border_radius=4)
        pygame.draw.rect(screen, (22, 30, 45), self.rect_btn_zoom_out, border_radius=4)
        pygame.draw.rect(screen, (22, 30, 45), self.rect_btn_zoom_reset, border_radius=4)

        screen.blit(font_sm.render("+", True, COLOR_TEXT_PRIMARY), (self.rect_btn_zoom_in.x + 9, self.rect_btn_zoom_in.y + 4))
        screen.blit(font_sm.render("-", True, COLOR_TEXT_PRIMARY), (self.rect_btn_zoom_out.x + 11, self.rect_btn_zoom_out.y + 3))
        screen.blit(font_sm.render("Reset", True, COLOR_TEXT_SECONDARY), (self.rect_btn_zoom_reset.x + 12, self.rect_btn_zoom_reset.y + 4))

    # ----------------------------------------------------------------------- #
    # Utility Multi-line Text
    def _draw_multiline_text(
        self,
        screen: pygame.Surface,
        text: str,
        x: int,
        y: int,
        max_w: int,
        font: pygame.font.Font,
        color: Tuple[int, int, int],
        line_spacing: int = 2
    ) -> int:
        """Menggambar teks multiline dengan word-wrap otomatis, newline (\n) support, dan anti-overflow."""
        if not text or max_w <= 10:
            return y
        line_h = font.get_linesize() + line_spacing
        line_y = y
        paragraphs = text.split("\n")
        for para in paragraphs:
            if not para:
                line_y += line_h // 2
                continue
            words = para.split(" ")
            line = ""
            for w in words:
                # Jika kata w sendiri melebihi max_w, pecah kata tersebut
                if font.size(w)[0] > max_w:
                    if line:
                        screen.blit(font.render(line, True, color), (x, line_y))
                        line_y += line_h
                        line = ""
                    sub_w = ""
                    for ch in w:
                        if font.size(sub_w + ch)[0] > max_w:
                            if sub_w:
                                screen.blit(font.render(sub_w, True, color), (x, line_y))
                                line_y += line_h
                            sub_w = ch
                        else:
                            sub_w += ch
                    line = sub_w
                    continue

                test_line = line + (" " if line else "") + w
                if font.size(test_line)[0] > max_w:
                    if line:
                        screen.blit(font.render(line, True, color), (x, line_y))
                        line_y += line_h
                    line = w
                else:
                    line = test_line
            if line:
                screen.blit(font.render(line, True, color), (x, line_y))
                line_y += line_h
        return line_y
