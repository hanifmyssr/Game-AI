"""UnifiedGraphModal: Visualizer Pohon AI Universal Bebas Bug (Pan & Zoom).

Modul visualizer terpadu untuk:
1. Pohon Minimax / Alpha-Beta Pruning (Materi 04)
2. Pohon Pencarian CSP Backtracking & Local Search (Materi 05-06)
3. Pohon Resolusi Logika Refutasi (Materi 07)
4. Pohon Rencana Tindakan PDDL STRIPS (Materi 08)

Fitur Utama:
- Non-overlapping hierarchical layout (algoritma recursive bottom-up subtree bounding).
- Navigasi Pan bebas (klik-kiri dan drag layar).
- Navigasi Zoom bebas (mouse-wheel smooth scaling 0.4x s.d. 2.5x).
- Tombol kontrol kamera: Reset View, Depth Limit [-] / [+], dan Tutup [ESC / T].
"""

import math
from typing import Dict, Any, Optional, List, Tuple
import pygame
from ..core import config

MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1025)
MOUSEBUTTONUP = getattr(pygame, "MOUSEBUTTONUP", 1026)
MOUSEMOTION = getattr(pygame, "MOUSEMOTION", 1024)
MOUSEWHEEL = getattr(pygame, "MOUSEWHEEL", 1027)
KEYDOWN = getattr(pygame, "KEYDOWN", 768)
K_ESCAPE = getattr(pygame, "K_ESCAPE", 27)
K_t = getattr(pygame, "K_t", 116)
K_LEFT = getattr(pygame, "K_LEFT", 1073741904)
K_RIGHT = getattr(pygame, "K_RIGHT", 1073741903)
K_UP = getattr(pygame, "K_UP", 1073741906)
K_DOWN = getattr(pygame, "K_DOWN", 1073741905)
K_a = getattr(pygame, "K_a", 97)
K_d = getattr(pygame, "K_d", 100)
K_w = getattr(pygame, "K_w", 119)
K_s = getattr(pygame, "K_s", 115)
K_r = getattr(pygame, "K_r", 114)
SRCALPHA = getattr(pygame, "SRCALPHA", 0x00010000)

NODE_BASE_W = 90
NODE_BASE_H = 38
NODE_PAD_X = 18
NODE_PAD_Y = 64


class GraphNode:
    """Struktur data universal untuk simpul pohon/grafik AI."""

    def __init__(self, node_id: str, label: str, sub_label: str = "",
                 score_str: str = "", node_type: str = "DEFAULT",
                 is_best: bool = False, is_pruned: bool = False):
        self.node_id = node_id
        self.label = label
        self.sub_label = sub_label
        self.score_str = score_str
        self.node_type = node_type  # "MAX", "MIN", "CHANCE", "CSP", "LOGIC", "PDDL", "DEFAULT"
        self.is_best = is_best
        self.is_pruned = is_pruned
        self.children: List["GraphNode"] = []
        self.meta: Dict[str, Any] = {}

    def add_child(self, child: "GraphNode") -> "GraphNode":
        self.children.append(child)
        return child


class UnifiedGraphModal:
    """Modal visualizer fullscreen dengan kontrol kamera pan & zoom bebas."""

    def __init__(self, fonts: Dict[str, pygame.font.Font]):
        self.fonts = fonts
        self.visible = False
        self.modal_title = "VISUALISASI POHON KEPUTUSAN AI"
        self.mode_tag = "MINIMAX"  # "MINIMAX", "CSP", "LOGIC", "PLANNING"
        self.root_node: Optional[GraphNode] = None

        # Parameter Kamera Pan & Zoom
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.zoom = 1.0
        self.min_zoom = 0.4
        self.max_zoom = 2.5
        self.max_depth = 4

        # Drag state
        self.is_dragging = False
        self.drag_start_pos = (0, 0)
        self.drag_start_cam = (0.0, 0.0)

        # Cache layout [(node, abs_cx, abs_cy, parent_cx, parent_cy, is_best, depth), ...]
        self._cached_layout = []
        self._tree_bounds = (0.0, 0.0, 100.0, 100.0)  # min_x, min_y, max_x, max_y
        self._needs_layout = True

        # Tombol-tombol kontrol
        self.btn_close = pygame.Rect(0, 0, 80, 32)
        self.btn_reset_cam = pygame.Rect(0, 0, 100, 32)
        self.btn_depth_minus = pygame.Rect(0, 0, 28, 28)
        self.btn_depth_plus = pygame.Rect(0, 0, 28, 28)

    @property
    def panel_rect(self) -> pygame.Rect:
        """Area rect fullscreen untuk kompatibilitas pengecekan collidepoint."""
        return pygame.Rect(0, 0, 10000, 10000)

    def set_tree(self, tree_data: Any) -> None:
        """Alias kompatibel: menerima root TreeNode atau GraphNode."""
        if tree_data is None:
            self.root_node = None
            self._needs_layout = True
            return
        if hasattr(tree_data, "children") or hasattr(tree_data, "action"):
            self.set_tree_from_minimax(tree_data)
        elif isinstance(tree_data, GraphNode):
            self.set_tree_from_generic(tree_data)

    def set_tree_from_minimax(self, tree_root_any: Any) -> None:
        """Mengonversi TreeNode dari sistem battle minimax ke GraphNode universal."""
        if tree_root_any is None:
            self.root_node = None
            self._needs_layout = True
            return

        def _convert(t_node, depth=0) -> GraphNode:
            action_name = getattr(t_node, "action", "") or "ROOT"
            score = getattr(t_node, "score", None)
            score_str = f"{score:+.1f}" if isinstance(score, (int, float)) else "?"
            is_max = getattr(t_node, "is_max", True)
            is_pruned = getattr(t_node, "pruned", False)
            is_best = getattr(t_node, "is_best", False)

            ntype = "MAX" if is_max else "MIN"
            g_node = GraphNode(
                node_id=str(id(t_node)),
                label=action_name[:10],
                sub_label=f"D:{depth}",
                score_str=score_str,
                node_type=ntype,
                is_best=is_best,
                is_pruned=is_pruned,
            )

            children = getattr(t_node, "children", []) or []
            for c in children:
                g_node.add_child(_convert(c, depth + 1))
            return g_node

        self.root_node = _convert(tree_root_any, 0)
        self.modal_title = "POHON PENCARIAN MINIMAX / ALPHA-BETA"
        self.mode_tag = "MINIMAX"
        self._needs_layout = True
        self._compute_layout()
        self.reset_camera()

    def set_tree_from_generic(self, root: GraphNode, title: str = "POHON KEPUTUSAN AI", mode_tag: str = "GENERIC") -> None:
        self.root_node = root
        self.modal_title = title
        self.mode_tag = mode_tag
        self._needs_layout = True
        self._compute_layout()
        self.reset_camera()

    def toggle(self) -> None:
        self.visible = not self.visible
        if self.visible:
            if self._needs_layout:
                self._compute_layout()
            self.reset_camera()

    def reset_camera(self) -> None:
        """Menempatkan kamera agar root pohon berada persis di tengah atas layar."""
        self.zoom = 1.0
        if self._cached_layout:
            root_cx = self._cached_layout[0][1]
            self.camera_x = 640.0 - root_cx * self.zoom
        else:
            self.camera_x = 640.0
        self.camera_y = 100.0

    # ------------------------------------------------------------------ #
    # Layout Tree: Algoritma Recursive Subtree Bottom-Up
    # ------------------------------------------------------------------ #
    def _compute_layout(self) -> None:
        if not self.root_node:
            self._cached_layout = []
            self._needs_layout = False
            return

        subtree_w: Dict[str, float] = {}
        subtree_center: Dict[str, float] = {}

        # Pass 1: Hitung lebar relatif tiap subtree (bottom-up)
        def _calc_subtree(node: GraphNode, depth: int) -> Tuple[float, float]:
            if depth >= self.max_depth or node.is_pruned or not node.children:
                w = float(NODE_BASE_W + NODE_PAD_X)
                cx = w / 2.0
                subtree_w[node.node_id] = w
                subtree_center[node.node_id] = cx
                return w, cx

            cur_x = 0.0
            centers = []
            for child in node.children:
                cw, ccx = _calc_subtree(child, depth + 1)
                centers.append(cur_x + ccx)
                cur_x += cw

            w = max(float(NODE_BASE_W + NODE_PAD_X), cur_x)
            cx = (centers[0] + centers[-1]) / 2.0
            subtree_w[node.node_id] = w
            subtree_center[node.node_id] = cx
            return w, cx

        _calc_subtree(self.root_node, 0)

        # Pass 2: Tetapkan koordinat absolut (top-down)
        layout = []
        min_x = float("inf")
        max_x = float("-inf")
        min_y = float("inf")
        max_y = float("-inf")

        def _assign_coords(node: GraphNode, depth: int, start_x: float, parent_pos: Optional[Tuple[float, float]], is_best: bool):
            nonlocal min_x, max_x, min_y, max_y
            cx = start_x + subtree_center[node.node_id]
            cy = depth * NODE_PAD_Y

            min_x = min(min_x, cx - NODE_BASE_W / 2.0)
            max_x = max(max_x, cx + NODE_BASE_W / 2.0)
            min_y = min(min_y, cy)
            max_y = max(max_y, cy + NODE_BASE_H)

            px, py = parent_pos if parent_pos else (None, None)
            layout.append((node, cx, cy, px, py, is_best, depth))

            if depth >= self.max_depth or node.is_pruned or not node.children:
                return

            cur_x = start_x
            for child in node.children:
                cw = subtree_w[child.node_id]
                _assign_coords(child, depth + 1, cur_x, (cx, cy), child.is_best)
                cur_x += cw

        _assign_coords(self.root_node, 0, 0.0, None, False)

        self._cached_layout = layout
        self._tree_bounds = (min_x, min_y, max_x, max_y)
        self._needs_layout = False

    # ------------------------------------------------------------------ #
    # Event Handling: Pan, Zoom, Controls
    # ------------------------------------------------------------------ #
    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.visible:
            return False

        if event.type == KEYDOWN:
            if event.key in (K_ESCAPE, K_t):
                self.visible = False
                return True
            elif event.key in (K_LEFT, K_a):
                self.camera_x += 60.0
                return True
            elif event.key in (K_RIGHT, K_d):
                self.camera_x -= 60.0
                return True
            elif event.key in (K_UP, K_w):
                self.camera_y += 60.0
                return True
            elif event.key in (K_DOWN, K_s):
                self.camera_y -= 60.0
                return True
            elif event.key == K_r:
                self.reset_camera()
                return True

        # Mouse Drag Pan
        if event.type == MOUSEBUTTONDOWN:
            if event.button == 1:
                # Cek klik tombol UI kontrol atas
                if self.btn_close.collidepoint(event.pos):
                    self.visible = False
                    return True
                if self.btn_reset_cam.collidepoint(event.pos):
                    self.reset_camera()
                    return True
                if self.btn_depth_minus.collidepoint(event.pos):
                    self.max_depth = max(1, self.max_depth - 1)
                    self._needs_layout = True
                    return True
                if self.btn_depth_plus.collidepoint(event.pos):
                    self.max_depth = min(8, self.max_depth + 1)
                    self._needs_layout = True
                    return True

                # Mulai Drag Pan
                self.is_dragging = True
                self.drag_start_pos = event.pos
                self.drag_start_cam = (self.camera_x, self.camera_y)
                return True

        elif event.type == MOUSEBUTTONUP and event.button == 1:
            if self.is_dragging:
                self.is_dragging = False
                return True

        elif event.type == MOUSEMOTION and self.is_dragging:
            dx = event.pos[0] - self.drag_start_pos[0]
            dy = event.pos[1] - self.drag_start_pos[1]
            self.camera_x = self.drag_start_cam[0] + dx
            self.camera_y = self.drag_start_cam[1] + dy
            return True

        # Mouse Wheel Zoom & Pan
        elif event.type == MOUSEWHEEL:
            # Dukungan gesture slide ke samping (trackpad horizontal swipe)
            if hasattr(event, "x") and event.x != 0:
                self.camera_x += event.x * 40.0

            # Zoom vertikal
            if hasattr(event, "y") and event.y != 0:
                old_zoom = self.zoom
                zoom_factor = 1.15 if event.y > 0 else (1.0 / 1.15)
                new_zoom = max(self.min_zoom, min(self.max_zoom, self.zoom * zoom_factor))

                # Zoom terpusat ke mouse cursor
                mx, my = pygame.mouse.get_pos()
                self.camera_x = mx - (mx - self.camera_x) * (new_zoom / old_zoom)
                self.camera_y = my - (my - self.camera_y) * (new_zoom / old_zoom)
                self.zoom = new_zoom
            return True

        # Telan semua event klik lain saat modal fullscreen aktif
        return True

    # ------------------------------------------------------------------ #
    # Rendering
    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        if self._needs_layout:
            self._compute_layout()

        sw, sh = surface.get_size()

        # 1. Overlay Latar Gelap Semi-Transparan
        backdrop = pygame.Surface((sw, sh), SRCALPHA)
        backdrop.fill((12, 16, 24, 250))
        surface.blit(backdrop, (0, 0))

        # 2. Gambar Koneksi Cabang Antar Node
        nw = NODE_BASE_W * self.zoom
        nh = NODE_BASE_H * self.zoom

        for (node, cx, cy, px, py, is_best, depth) in self._cached_layout:
            if px is not None and py is not None:
                # World to Screen coordinates
                sx1 = int(self.camera_x + px * self.zoom)
                sy1 = int(self.camera_y + (py + NODE_BASE_H) * self.zoom)
                sx2 = int(self.camera_x + cx * self.zoom)
                sy2 = int(self.camera_y + cy * self.zoom)

                # Bezier S-Curve
                dy = sy2 - sy1
                ctrl1 = (sx1, int(sy1 + dy * 0.5))
                ctrl2 = (sx2, int(sy1 + dy * 0.5))

                line_col = config.COLOR_STATUS_DANGER if node.is_pruned else (
                    config.COLOR_STATUS_SUCCESS if is_best else (75, 95, 125)
                )
                line_width = 3 if is_best else 1

                # Gambar garis kurva
                try:
                    pts = [
                        (sx1, sy1),
                        ctrl1,
                        ctrl2,
                        (sx2, sy2)
                    ]
                    # Simple 4-point spline
                    pygame.draw.lines(surface, line_col, False, [(sx1, sy1), (sx1, sy1 + dy//2), (sx2, sy1 + dy//2), (sx2, sy2)], line_width)
                except Exception:
                    pygame.draw.line(surface, line_col, (sx1, sy1), (sx2, sy2), line_width)

        # 3. Gambar Kotak Simpul (Nodes)
        font_tiny = self.fonts.get("tiny", pygame.font.Font(None, 12))
        font_sm = self.fonts.get("sm", pygame.font.Font(None, 14))

        for (node, cx, cy, px, py, is_best, depth) in self._cached_layout:
            sx = int(self.camera_x + (cx - NODE_BASE_W / 2.0) * self.zoom)
            sy = int(self.camera_y + cy * self.zoom)
            node_rect = pygame.Rect(sx, sy, int(nw), int(nh))

            # Jangan gambar jika berada di luar batas layar (frustum culling)
            if node_rect.right < 0 or node_rect.x > sw or node_rect.bottom < 0 or node_rect.y > sh:
                continue

            # Warna Node Berdasarkan Tipe
            if node.is_pruned:
                bg = (40, 25, 28)
                bd = (140, 45, 50)
                txt_col = (180, 120, 125)
            elif is_best:
                bg = (24, 55, 38)
                bd = config.COLOR_STATUS_SUCCESS
                txt_col = (255, 255, 255)
            elif node.node_type == "MAX":
                bg = (45, 35, 22)
                bd = config.COLOR_ACCENT_GOLD
                txt_col = (255, 235, 180)
            elif node.node_type == "MIN":
                bg = (22, 38, 55)
                bd = config.COLOR_ACCENT_BLUE
                txt_col = (190, 225, 255)
            else:
                bg = (25, 32, 45)
                bd = (55, 70, 95)
                txt_col = config.COLOR_TEXT_PRIMARY

            pygame.draw.rect(surface, bg, node_rect, border_radius=max(3, int(5 * self.zoom)))
            pygame.draw.rect(surface, bd, node_rect, width=max(1, int(1.5 * self.zoom)), border_radius=max(3, int(5 * self.zoom)))

            # Teks Node (Hanya render jika zoom tidak terlalu kecil)
            if self.zoom >= 0.5:
                # Label Atas
                lbl_surf = font_tiny.render(node.label, True, txt_col)
                surface.blit(lbl_surf, (node_rect.centerx - lbl_surf.get_width() // 2, node_rect.y + int(3 * self.zoom)))

                # Nilai Skor Bawah
                if node.score_str:
                    sc_col = config.COLOR_ACCENT_GOLD if not node.is_pruned else (140, 120, 120)
                    sc_surf = font_tiny.render(node.score_str, True, sc_col)
                    surface.blit(sc_surf, (node_rect.centerx - sc_surf.get_width() // 2, node_rect.bottom - sc_surf.get_height() - int(3 * self.zoom)))

        # 4. Bilah Header & Kontrol Kamera Atas
        top_bar = pygame.Rect(0, 0, sw, 52)
        top_surf = pygame.Surface((sw, 52), SRCALPHA)
        top_surf.fill((15, 20, 30, 240))
        surface.blit(top_surf, (0, 0))
        pygame.draw.line(surface, config.COLOR_INSPECTOR_BORDER, (0, 51), (sw, 51), 1)

        # Judul Modal
        font_title = self.fonts.get("bubble", self.fonts["title"])
        t_surf = font_title.render(self.modal_title, True, config.COLOR_ACCENT_GOLD)
        surface.blit(t_surf, (20, 14))

        # Kontrol Zoom & Info
        info_str = f"Zoom: {self.zoom:.2f}x  |  Drag: Geser Layar  |  Scroll: Zoom"
        surface.blit(font_tiny.render(info_str, True, config.COLOR_TEXT_SECONDARY), (sw // 2 - 120, 18))

        # Kontrol Depth Limit
        dx = sw - 320
        surface.blit(font_tiny.render("Depth:", True, config.COLOR_TEXT_SECONDARY), (dx, 18))
        self.btn_depth_minus = pygame.Rect(dx + 48, 12, 28, 28)
        self.btn_depth_plus = pygame.Rect(dx + 110, 12, 28, 28)
        pygame.draw.rect(surface, (35, 45, 65), self.btn_depth_minus, border_radius=4)
        pygame.draw.rect(surface, (35, 45, 65), self.btn_depth_plus, border_radius=4)
        surface.blit(font_sm.render("-", True, config.COLOR_STATUS_DANGER), (self.btn_depth_minus.centerx - 4, self.btn_depth_minus.y + 4))
        surface.blit(font_sm.render("+", True, config.COLOR_STATUS_SUCCESS), (self.btn_depth_plus.centerx - 4, self.btn_depth_plus.y + 4))
        surface.blit(font_tiny.render(str(self.max_depth), True, config.COLOR_TEXT_PRIMARY), (dx + 86, 18))

        # Tombol Reset Kamera
        self.btn_reset_cam = pygame.Rect(sw - 160, 12, 68, 28)
        pygame.draw.rect(surface, (35, 48, 70), self.btn_reset_cam, border_radius=4)
        pygame.draw.rect(surface, config.COLOR_INSPECTOR_BORDER, self.btn_reset_cam, width=1, border_radius=4)
        rc_surf = font_tiny.render("Tengahkan", True, (240, 245, 255))
        surface.blit(rc_surf, (self.btn_reset_cam.centerx - rc_surf.get_width() // 2, self.btn_reset_cam.y + 6))

        # Tombol Tutup [ESC]
        self.btn_close = pygame.Rect(sw - 80, 12, 64, 28)
        pygame.draw.rect(surface, (65, 30, 35), self.btn_close, border_radius=4)
        pygame.draw.rect(surface, config.COLOR_STATUS_DANGER, self.btn_close, width=1, border_radius=4)
        cl_surf = font_tiny.render("Tutup", True, (255, 230, 230))
        surface.blit(cl_surf, (self.btn_close.centerx - cl_surf.get_width() // 2, self.btn_close.y + 6))
