"""UnifiedGraphModal: Visualizer Pohon AI Universal (Cozy Warm Parchment Theme).

Modul visualizer terpadu untuk:
1. Pohon Minimax / Alpha-Beta Pruning (Materi 04)
2. Pohon Pencarian CSP Backtracking & Local Search (Materi 05-06)
3. Pohon Resolusi Logika Refutasi (Materi 07)
4. Pohon Rencana Tindakan PDDL STRIPS (Materi 08)

Fitur Utama:
- Tema Cozy Warm Parchment seragam dengan seluruh UI game.
- Layout non-overlapping dengan kotak simpul besar, clipping & distribusi baris dinamis.
- Kanvas pohon interaktif di kiri (60%) + Sidebar Inspektor bertab di kanan (40%):
  * Tab 1: Detail Simpul / Cabang Terpilih (Preconditions, Add/Del Effects, State Fluents, g/h/f)
  * Tab 2: Penjelasan Pohon (Ini Pohon Apa & Cara Membacanya)
- Navigasi Pan bebas (drag klik-kiri), Zoom (mouse wheel), serta klik simpul untuk inspeksi.
"""

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
K_1 = getattr(pygame, "K_1", 49)
K_2 = getattr(pygame, "K_2", 50)
SRCALPHA = getattr(pygame, "SRCALPHA", 0x00010000)

# Palet Cozy Warm Parchment (selaras dengan PreBattleVisualizerModal)
COLOR_BACKDROP = (25, 20, 15, 165)
COLOR_MODAL_BG = (248, 244, 235)
COLOR_MODAL_BORDER = (208, 192, 172)
COLOR_HEADER_BG = (238, 231, 218)
COLOR_HEADER_LINE = (208, 192, 172)
COLOR_CANVAS_BG = (250, 246, 238)
COLOR_SIDEBAR_BG = (255, 253, 248)
COLOR_CARD_BG = (255, 255, 255)
COLOR_CARD_BORDER = (218, 206, 188)

COLOR_TEXT_HEADING = (145, 72, 18)
COLOR_TEXT_PRIMARY = (38, 30, 24)
COLOR_TEXT_SECONDARY = (115, 98, 82)
COLOR_TEXT_ACCENT = (40, 118, 198)
COLOR_TEXT_SUCCESS = (38, 128, 58)
COLOR_TEXT_WARNING = (180, 100, 20)
COLOR_TEXT_DANGER = (185, 48, 48)

COLOR_BTN_BG = (242, 235, 222)
COLOR_BTN_HOVER = (255, 252, 245)
COLOR_BTN_ACTIVE = (205, 135, 25)
COLOR_BTN_BORDER = (208, 192, 172)


class GraphNode:
    """Struktur data universal untuk simpul pohon/grafik AI."""

    def __init__(self, node_id: str, label: str, sub_label: str = "",
                 score_str: str = "", node_type: str = "DEFAULT",
                 is_best: bool = False, is_pruned: bool = False):
        self.node_id = node_id
        self.label = label
        self.sub_label = sub_label
        self.score_str = score_str
        self.node_type = node_type  # "MAX", "MIN", "CHANCE", "TERMINAL", "DEFAULT"
        self.is_best = is_best
        self.is_pruned = is_pruned
        self.children: List["GraphNode"] = []
        self.meta: Dict[str, Any] = {}

    def add_child(self, child: "GraphNode") -> "GraphNode":
        self.children.append(child)
        return child


def _wrap_lines(font: pygame.font.Font, text: str, max_w: int) -> List[str]:
    """Memecah teks menjadi beberapa baris agar pas di lebar sidebar."""
    if not text:
        return []
    words = text.split(" ")
    lines: List[str] = []
    cur = ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if font.size(cand)[0] <= max_w:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit_text(font_obj: pygame.font.Font, text: str, max_w: int) -> str:
    """Memotong teks secara presisi berbasis piksel bila melebihi lebar kotak."""
    if not text or max_w <= 8:
        return ""
    if font_obj.size(text)[0] <= max_w:
        return text
    for i in range(len(text), 0, -1):
        sub = text[:i] + ".."
        if font_obj.size(sub)[0] <= max_w:
            return sub
    return ""


class UnifiedGraphModal:
    """Modal visualizer Cozy Warm Parchment dengan kanvas pohon & sidebar penjelasan bertab."""

    def __init__(self, fonts: Dict[str, pygame.font.Font]):
        self.fonts = fonts
        self.visible = False
        self.modal_title = "VISUALISASI POHON KEPUTUSAN AI"
        self.mode_tag = "MINIMAX"  # "MINIMAX", "CSP", "LOGIC", "PLANNING"
        self.root_node: Optional[GraphNode] = None
        self.selected_node: Optional[GraphNode] = None
        self.hovered_node: Optional[GraphNode] = None

        # Sidebar kanan bertab ("DETAIL" | "THEORY")
        self.sidebar_tab: str = "DETAIL"
        self.sidebar_scroll_y: float = 0.0
        self.sidebar_max_scroll: float = 0.0

        # Parameter Kamera Pan & Zoom
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.zoom = 1.0
        self.min_zoom = 0.35
        self.max_zoom = 2.2
        self.max_depth = 6

        # Drag state
        self.is_dragging = False
        self.drag_moved = False
        self.drag_start_pos = (0, 0)
        self.drag_start_cam = (0.0, 0.0)

        # Layout rects & cache
        self.rect_modal = pygame.Rect(0, 0, 1200, 720)
        self.rect_canvas = pygame.Rect(40, 100, 680, 580)
        self.rect_sidebar = pygame.Rect(732, 100, 440, 580)
        self._cached_layout = []
        self._tree_bounds = (0.0, 0.0, 100.0, 100.0)
        self._needs_layout = True

        # Tombol-tombol kontrol
        self.btn_close = pygame.Rect(0, 0, 34, 34)
        self.btn_reset_cam = pygame.Rect(0, 0, 86, 28)
        self.btn_depth_minus = pygame.Rect(0, 0, 28, 28)
        self.btn_depth_plus = pygame.Rect(0, 0, 28, 28)
        self.btn_tab_detail = pygame.Rect(0, 0, 140, 30)
        self.btn_tab_theory = pygame.Rect(0, 0, 140, 30)

    @property
    def panel_rect(self) -> pygame.Rect:
        """Area rect fullscreen untuk kompatibilitas pengecekan collidepoint."""
        return pygame.Rect(0, 0, 10000, 10000)

    def _node_dims(self) -> Tuple[int, int, int, int]:
        """Mengembalikan (node_w, node_h, pad_x, pad_y) sesuai mode pohon."""
        if self.mode_tag in ("PLANNING", "LOGIC"):
            return (330, 96, 36, 134)
        return (156, 60, 20, 86)

    def _tree_max_depth(self, node: Optional[GraphNode], d: int = 0) -> int:
        if not node or not node.children:
            return d
        return max(self._tree_max_depth(c, d + 1) for c in node.children)

    def set_tree(self, tree_data: Any) -> None:
        if tree_data is None:
            self.root_node = None
            self.selected_node = None
            self._needs_layout = True
            return
        if hasattr(tree_data, "children") or hasattr(tree_data, "action"):
            self.set_tree_from_minimax(tree_data)
        elif isinstance(tree_data, GraphNode):
            self.set_tree_from_generic(tree_data)

    def set_tree_from_minimax(self, tree_root_any: Any) -> None:
        if tree_root_any is None:
            self.root_node = None
            self.selected_node = None
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
                label=action_name,
                sub_label=f"Depth {depth} ({ntype})",
                score_str=score_str,
                node_type=ntype,
                is_best=is_best,
                is_pruned=is_pruned,
            )
            for c in (getattr(t_node, "children", []) or []):
                g_node.add_child(_convert(c, depth + 1))
            return g_node

        self.root_node = _convert(tree_root_any, 0)
        self.selected_node = self.root_node
        self.modal_title = "POHON PENCARIAN MINIMAX / ALPHA-BETA"
        self.mode_tag = "MINIMAX"
        self.max_depth = 4
        self.sidebar_tab = "DETAIL"
        self.sidebar_scroll_y = 0.0
        self._needs_layout = True
        self._compute_layout()
        self.reset_camera()

    def set_tree_from_generic(self, root: GraphNode, title: str = "POHON KEPUTUSAN AI", mode_tag: str = "GENERIC") -> None:
        self.root_node = root
        self.selected_node = root
        self.modal_title = title
        self.mode_tag = mode_tag
        self.max_depth = max(6, self._tree_max_depth(root)) if mode_tag in ("PLANNING", "LOGIC") else 4
        self.sidebar_tab = "DETAIL"
        self.sidebar_scroll_y = 0.0
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
        """Menempatkan pohon tepat di tengah kanvas kiri dengan zoom nyaman."""
        if not self._cached_layout or self.rect_canvas.width <= 0:
            self.zoom = 1.0
            self.camera_x = float(self.rect_canvas.centerx)
            self.camera_y = float(self.rect_canvas.y + 40)
            return

        min_x, min_y, max_x, max_y = self._tree_bounds
        tree_w = max(1.0, max_x - min_x)
        tree_h = max(1.0, max_y - min_y)

        avail_w = max(120.0, self.rect_canvas.width - 70.0)
        avail_h = max(120.0, self.rect_canvas.height - 70.0)
        fit_zoom = min(avail_w / tree_w, avail_h / tree_h)

        if self.mode_tag in ("PLANNING", "LOGIC"):
            self.zoom = max(0.76, min(1.05, fit_zoom))
        else:
            self.zoom = max(0.55, min(1.05, fit_zoom))

        tree_cx = (min_x + max_x) / 2.0
        self.camera_x = self.rect_canvas.centerx - tree_cx * self.zoom
        if tree_h * self.zoom <= avail_h:
            tree_cy = (min_y + max_y) / 2.0
            self.camera_y = self.rect_canvas.centery - tree_cy * self.zoom
        else:
            self.camera_y = float(self.rect_canvas.y + 28) - min_y * self.zoom

    # ------------------------------------------------------------------ #
    # Layout Tree: Algoritma Recursive Subtree Bottom-Up
    # ------------------------------------------------------------------ #
    def _compute_layout(self) -> None:
        if not self.root_node:
            self._cached_layout = []
            self._needs_layout = False
            return

        nw, nh, pad_x, pad_y = self._node_dims()
        subtree_w: Dict[str, float] = {}
        subtree_center: Dict[str, float] = {}

        def _calc_subtree(node: GraphNode, depth: int) -> Tuple[float, float]:
            if depth >= self.max_depth or node.is_pruned or not node.children:
                w = float(nw + pad_x)
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

            w = max(float(nw + pad_x), cur_x)
            cx = (centers[0] + centers[-1]) / 2.0
            subtree_w[node.node_id] = w
            subtree_center[node.node_id] = cx
            return w, cx

        _calc_subtree(self.root_node, 0)

        layout = []
        min_x = float("inf")
        max_x = float("-inf")
        min_y = float("inf")
        max_y = float("-inf")

        def _assign_coords(node: GraphNode, depth: int, start_x: float, parent_pos: Optional[Tuple[float, float]], is_best: bool):
            nonlocal min_x, max_x, min_y, max_y
            cx = start_x + subtree_center[node.node_id]
            cy = depth * pad_y

            min_x = min(min_x, cx - nw / 2.0)
            max_x = max(max_x, cx + nw / 2.0)
            min_y = min(min_y, cy)
            max_y = max(max_y, cy + nh)

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

    def _find_node_at(self, pos: Tuple[int, int]) -> Optional[GraphNode]:
        if not self.rect_canvas.collidepoint(pos):
            return None
        nw_base, nh_base, _, _ = self._node_dims()
        nw = nw_base * self.zoom
        nh = nh_base * self.zoom
        for (node, cx, cy, _, _, _, _) in self._cached_layout:
            sx = self.camera_x + (cx - nw_base / 2.0) * self.zoom
            sy = self.camera_y + cy * self.zoom
            if pygame.Rect(int(sx), int(sy), int(nw), int(nh)).collidepoint(pos):
                return node
        return None

    # ------------------------------------------------------------------ #
    # Event Handling: Pan, Zoom, Click Node, Scroll Sidebar
    # ------------------------------------------------------------------ #
    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.visible:
            return False

        if event.type == KEYDOWN:
            if event.key in (K_ESCAPE, K_t):
                self.visible = False
                return True
            elif event.key == K_1:
                self.sidebar_tab = "DETAIL"
                self.sidebar_scroll_y = 0.0
                return True
            elif event.key == K_2:
                self.sidebar_tab = "THEORY"
                self.sidebar_scroll_y = 0.0
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

        if event.type == MOUSEBUTTONDOWN and event.button == 1:
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
                self.max_depth = min(10, self.max_depth + 1)
                self._needs_layout = True
                return True
            if self.btn_tab_detail.collidepoint(event.pos):
                self.sidebar_tab = "DETAIL"
                self.sidebar_scroll_y = 0.0
                return True
            if self.btn_tab_theory.collidepoint(event.pos):
                self.sidebar_tab = "THEORY"
                self.sidebar_scroll_y = 0.0
                return True

            if self.rect_canvas.collidepoint(event.pos):
                self.is_dragging = True
                self.drag_moved = False
                self.drag_start_pos = event.pos
                self.drag_start_cam = (self.camera_x, self.camera_y)
                return True

        elif event.type == MOUSEBUTTONUP and event.button == 1:
            if self.is_dragging:
                was_click = not self.drag_moved
                self.is_dragging = False
                if was_click:
                    clicked = self._find_node_at(event.pos)
                    if clicked is not None:
                        self.selected_node = clicked
                        self.sidebar_tab = "DETAIL"
                        self.sidebar_scroll_y = 0.0
                return True

        elif event.type == MOUSEMOTION:
            if self.is_dragging:
                dx = event.pos[0] - self.drag_start_pos[0]
                dy = event.pos[1] - self.drag_start_pos[1]
                if abs(dx) > 4 or abs(dy) > 4:
                    self.drag_moved = True
                self.camera_x = self.drag_start_cam[0] + dx
                self.camera_y = self.drag_start_cam[1] + dy
                return True
            self.hovered_node = self._find_node_at(event.pos)

        elif event.type == MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self.rect_sidebar.collidepoint((mx, my)):
                self.sidebar_scroll_y = max(0.0, min(self.sidebar_max_scroll, self.sidebar_scroll_y - event.y * 28.0))
                return True

            if hasattr(event, "x") and event.x != 0:
                self.camera_x += event.x * 40.0
            if hasattr(event, "y") and event.y != 0:
                old_zoom = self.zoom
                zoom_factor = 1.14 if event.y > 0 else (1.0 / 1.14)
                new_zoom = max(self.min_zoom, min(self.max_zoom, self.zoom * zoom_factor))
                self.camera_x = mx - (mx - self.camera_x) * (new_zoom / old_zoom)
                self.camera_y = my - (my - self.camera_y) * (new_zoom / old_zoom)
                self.zoom = new_zoom
            return True

        return True

    # ------------------------------------------------------------------ #
    # Rendering Utama (Cozy Warm Parchment Split View)
    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        if self._needs_layout:
            self._compute_layout()

        sw, sh = surface.get_size()
        font_tiny = self.fonts.get("tiny", pygame.font.Font(None, 13))
        font_sm = self.fonts.get("sm", pygame.font.Font(None, 15))
        font_bubble = self.fonts.get("bubble", font_sm)
        font_title = self.fonts.get("title", font_sm)

        # 1. Backdrop Redup Hangat + Kotak Modal Utama (94% x 90%)
        backdrop = pygame.Surface((sw, sh), SRCALPHA)
        backdrop.fill(COLOR_BACKDROP)
        surface.blit(backdrop, (0, 0))

        mw = int(sw * 0.94)
        mh = int(sh * 0.90)
        mx = (sw - mw) // 2
        my = (sh - mh) // 2
        self.rect_modal = pygame.Rect(mx, my, mw, mh)

        pygame.draw.rect(surface, COLOR_MODAL_BG, self.rect_modal, border_radius=10)
        pygame.draw.rect(surface, COLOR_MODAL_BORDER, self.rect_modal, 2, border_radius=10)

        # 2. Header Bar Atas
        hdr_h = 56
        hdr_rect = pygame.Rect(mx, my, mw, hdr_h)
        pygame.draw.rect(surface, COLOR_HEADER_BG, hdr_rect, border_top_left_radius=10, border_top_right_radius=10)
        pygame.draw.line(surface, COLOR_HEADER_LINE, (mx, my + hdr_h), (mx + mw, my + hdr_h), 1)

        subtitle_map = {
            "PLANNING": "Materi 08: Classical Planning (PDDL STRIPS) — Klik simpul untuk detail aksi",
            "LOGIC": "Materi 07: Penalaran Logika & Resolusi Refutasi CNF",
            "MINIMAX": "Materi 04: Adversarial Search (Minimax / Alpha-Beta Pruning)",
        }
        t_surf = font_title.render(self.modal_title, True, COLOR_TEXT_HEADING)
        sub_surf = font_tiny.render(subtitle_map.get(self.mode_tag, "Visualisasi Pohon AI"), True, COLOR_TEXT_SECONDARY)
        surface.blit(t_surf, (mx + 18, my + 8))
        surface.blit(sub_surf, (mx + 18, my + 33))

        # Kontrol Atas Kanan: Depth, Tengahkan, Tutup [X]
        mx_cur, my_cur = pygame.mouse.get_pos()
        self.btn_close = pygame.Rect(mx + mw - 46, my + 11, 34, 34)
        hov_close = self.btn_close.collidepoint((mx_cur, my_cur))
        pygame.draw.rect(surface, (212, 70, 62) if hov_close else (190, 56, 50), self.btn_close, border_radius=6)
        x_lbl = font_title.render("X", True, (255, 255, 255))
        surface.blit(x_lbl, x_lbl.get_rect(center=self.btn_close.center))

        self.btn_reset_cam = pygame.Rect(self.btn_close.x - 96, my + 14, 86, 28)
        hov_reset = self.btn_reset_cam.collidepoint((mx_cur, my_cur))
        pygame.draw.rect(surface, COLOR_BTN_HOVER if hov_reset else COLOR_BTN_BG, self.btn_reset_cam, border_radius=6)
        pygame.draw.rect(surface, COLOR_BTN_BORDER, self.btn_reset_cam, 1, border_radius=6)
        rc_lbl = font_tiny.render("Tengahkan", True, COLOR_TEXT_PRIMARY)
        surface.blit(rc_lbl, rc_lbl.get_rect(center=self.btn_reset_cam.center))

        dx = self.btn_reset_cam.x - 148
        surface.blit(font_tiny.render("Depth:", True, COLOR_TEXT_SECONDARY), (dx, my + 20))
        self.btn_depth_minus = pygame.Rect(dx + 46, my + 14, 28, 28)
        self.btn_depth_plus = pygame.Rect(dx + 106, my + 14, 28, 28)
        for btn, sym, col in ((self.btn_depth_minus, "-", COLOR_TEXT_DANGER), (self.btn_depth_plus, "+", COLOR_TEXT_SUCCESS)):
            pygame.draw.rect(surface, COLOR_BTN_HOVER if btn.collidepoint((mx_cur, my_cur)) else COLOR_BTN_BG, btn, border_radius=5)
            pygame.draw.rect(surface, COLOR_BTN_BORDER, btn, 1, border_radius=5)
            s_surf = font_sm.render(sym, True, col)
            surface.blit(s_surf, s_surf.get_rect(center=btn.center))
        d_val = font_sm.render(str(self.max_depth), True, COLOR_TEXT_PRIMARY)
        surface.blit(d_val, d_val.get_rect(center=(dx + 90, my + 28)))

        # 3. Area Split: Kiri Kanvas Pohon (58%) & Kanan Sidebar Inspektor (42%)
        content_x = mx + 12
        content_y = my + hdr_h + 10
        content_w = mw - 24
        content_h = mh - hdr_h - 22

        tree_w = int(content_w * 0.58)
        sidebar_w = content_w - tree_w - 12
        new_canvas = pygame.Rect(content_x, content_y, tree_w, content_h)
        was_first = (self.rect_canvas.width != new_canvas.width)
        self.rect_canvas = new_canvas
        self.rect_sidebar = pygame.Rect(content_x + tree_w + 12, content_y, sidebar_w, content_h)
        if was_first and self._cached_layout:
            self.reset_camera()

        # Render Kanvas Pohon Kiri
        self._draw_tree_canvas(surface, font_tiny, font_sm, font_bubble)

        # Render Sidebar Penjelasan & Detail Kanan
        self._draw_sidebar(surface, font_tiny, font_sm, font_bubble, font_title)

    def _draw_tree_canvas(self, surface: pygame.Surface, font_tiny: pygame.font.Font,
                          font_sm: pygame.font.Font, font_bubble: pygame.font.Font) -> None:
        old_clip = surface.get_clip()
        surface.set_clip(self.rect_canvas)
        pygame.draw.rect(surface, COLOR_CANVAS_BG, self.rect_canvas, border_radius=8)

        nw_base, nh_base, _, _ = self._node_dims()
        nw = int(nw_base * self.zoom)
        nh = int(nh_base * self.zoom)

        # 1. Garis Penghubung Antar Simpul
        for (node, cx, cy, px, py, is_best, depth) in self._cached_layout:
            if px is not None and py is not None:
                sx1 = int(self.camera_x + px * self.zoom)
                sy1 = int(self.camera_y + (py + nh_base) * self.zoom)
                sx2 = int(self.camera_x + cx * self.zoom)
                sy2 = int(self.camera_y + cy * self.zoom)
                dy = sy2 - sy1
                line_col = (195, 65, 65) if node.is_pruned else (
                    (46, 152, 78) if is_best else (140, 128, 114)
                )
                lw = max(2, int(2.5 * self.zoom)) if is_best else max(1, int(1.6 * self.zoom))
                pts = [(sx1, sy1), (sx1, sy1 + dy // 2), (sx2, sy1 + dy // 2), (sx2, sy2)]
                pygame.draw.lines(surface, line_col, False, pts, lw)

        # 2. Pemilihan Font Adaptif Sesuai Ukuran Aktual Kotak
        font_l1 = font_bubble if nh >= 78 else (font_sm if nh >= 58 else font_tiny)
        font_l2 = font_sm if nh >= 82 else font_tiny
        font_l3 = font_tiny

        # 3. Kotak Simpul & Teks Terdistribusi Dinamis
        for (node, cx, cy, px, py, is_best, depth) in self._cached_layout:
            sx = int(self.camera_x + (cx - nw_base / 2.0) * self.zoom)
            sy = int(self.camera_y + cy * self.zoom)
            node_rect = pygame.Rect(sx, sy, nw, nh)

            if not node_rect.colliderect(self.rect_canvas):
                continue

            role = node.meta.get("role", "") if node.meta else ""
            if node.is_pruned:
                bg_col, bd_col = (253, 236, 236), (195, 65, 65)
                l1_col, l2_col, l3_col = COLOR_TEXT_DANGER, (145, 70, 70), (155, 60, 60)
            elif is_best or role == "GOAL":
                bg_col, bd_col = (232, 248, 236), (42, 148, 72)
                l1_col, l2_col, l3_col = COLOR_TEXT_PRIMARY, (55, 110, 70), COLOR_TEXT_SUCCESS
            elif node.node_type == "MAX" or role == "ROOT":
                bg_col, bd_col = (252, 243, 218), (205, 145, 35)
                l1_col, l2_col, l3_col = COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_WARNING
            elif node.node_type == "MIN" or role == "STEP":
                bg_col, bd_col = (235, 245, 255), (55, 130, 210)
                l1_col, l2_col, l3_col = COLOR_TEXT_PRIMARY, (72, 102, 138), COLOR_TEXT_ACCENT
            else:
                bg_col, bd_col = (255, 253, 248), (185, 168, 148)
                l1_col, l2_col, l3_col = COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_ACCENT

            is_sel = (node is self.selected_node)
            is_hov = (node is self.hovered_node)
            if is_sel:
                pygame.draw.rect(surface, (65, 145, 225), node_rect.inflate(8, 8), border_radius=10)
            elif is_hov:
                pygame.draw.rect(surface, (165, 195, 228), node_rect.inflate(6, 6), border_radius=9)

            pygame.draw.rect(surface, bg_col, node_rect, border_radius=8)
            pygame.draw.rect(surface, bd_col, node_rect, width=max(1, int(2 * self.zoom)), border_radius=8)

            if self.zoom >= 0.40 and nw >= 48 and nh >= 32:
                surface.set_clip(node_rect.clip(self.rect_canvas))
                max_txt_w = max(14, node_rect.width - 18)
                rows = [(_fit_text(font_l1, node.label, max_txt_w), font_l1, l1_col)]
                if node.sub_label and nh >= 60:
                    rows.append((_fit_text(font_l2, node.sub_label, max_txt_w), font_l2, l2_col))
                if node.score_str:
                    rows.append((_fit_text(font_l3, node.score_str, max_txt_w), font_l3, l3_col))

                rendered = [fnt.render(txt, True, col) for txt, fnt, col in rows if txt]
                if rendered:
                    total_h = sum(s.get_height() for s in rendered)
                    gap_v = max(2, (node_rect.height - total_h) // (len(rendered) + 1))
                    block_h = total_h + gap_v * (len(rendered) - 1)
                    cur_y = node_rect.y + max(3, (node_rect.height - block_h) // 2)
                    for r_surf in rendered:
                        surface.blit(r_surf, (node_rect.x + (node_rect.width - r_surf.get_width()) // 2, cur_y))
                        cur_y += r_surf.get_height() + gap_v
                surface.set_clip(self.rect_canvas)

        # Petunjuk interaksi kecil di pojok kiri bawah kanvas
        hint_surf = font_tiny.render(
            f"Zoom: {self.zoom:.2f}x  |  Klik simpul untuk detail  |  Drag: Geser  |  Scroll: Zoom",
            True,
            COLOR_TEXT_SECONDARY,
        )
        hint_bg = pygame.Surface((hint_surf.get_width() + 14, hint_surf.get_height() + 8), SRCALPHA)
        hint_bg.fill((255, 253, 248, 225))
        surface.blit(hint_bg, (self.rect_canvas.x + 10, self.rect_canvas.bottom - hint_bg.get_height() - 10))
        surface.blit(hint_surf, (self.rect_canvas.x + 17, self.rect_canvas.bottom - hint_bg.get_height() - 6))

        surface.set_clip(old_clip)
        pygame.draw.rect(surface, COLOR_MODAL_BORDER, self.rect_canvas, 1, border_radius=8)

    def _draw_sidebar(self, surface: pygame.Surface, font_tiny: pygame.font.Font,
                      font_sm: pygame.font.Font, font_bubble: pygame.font.Font,
                      font_title: pygame.font.Font) -> None:
        sb = self.rect_sidebar
        pygame.draw.rect(surface, COLOR_SIDEBAR_BG, sb, border_radius=8)
        pygame.draw.rect(surface, COLOR_MODAL_BORDER, sb, 1, border_radius=8)

        # Tab Header di Sidebar Kanan
        pad = 12
        tab_y = sb.y + 10
        tab_w = (sb.width - pad * 2 - 8) // 2
        self.btn_tab_detail = pygame.Rect(sb.x + pad, tab_y, tab_w, 30)
        self.btn_tab_theory = pygame.Rect(self.btn_tab_detail.right + 8, tab_y, tab_w, 30)

        mx_cur, my_cur = pygame.mouse.get_pos()
        for btn, label, key in (
            (self.btn_tab_detail, "1. Detail Simpul", "DETAIL"),
            (self.btn_tab_theory, "2. Penjelasan Pohon", "THEORY"),
        ):
            active = (self.sidebar_tab == key)
            hov = btn.collidepoint((mx_cur, my_cur))
            bg = COLOR_BTN_ACTIVE if active else (COLOR_BTN_HOVER if hov else COLOR_BTN_BG)
            txt_c = (255, 255, 255) if active else COLOR_TEXT_PRIMARY
            pygame.draw.rect(surface, bg, btn, border_radius=6)
            if not active:
                pygame.draw.rect(surface, COLOR_BTN_BORDER, btn, 1, border_radius=6)
            lbl_s = font_sm.render(label, True, txt_c)
            surface.blit(lbl_s, lbl_s.get_rect(center=btn.center))

        # Area Konten Scrollable Sidebar
        body_rect = pygame.Rect(sb.x + pad, tab_y + 38, sb.width - pad * 2, sb.height - 58)
        old_clip = surface.get_clip()
        surface.set_clip(body_rect)

        max_w = body_rect.width - 10
        entries: List[Tuple[str, pygame.font.Font, Tuple[int, int, int], int]] = []

        def add_block(text: str, fnt: pygame.font.Font, col: Tuple[int, int, int], space_after: int = 4):
            for ln in _wrap_lines(fnt, text, max_w):
                entries.append((ln, fnt, col, space_after))

        if self.sidebar_tab == "THEORY":
            self._build_theory_entries(add_block, font_bubble, font_sm, font_tiny)
        else:
            self._build_detail_entries(add_block, font_bubble, font_sm, font_tiny)

        total_h = sum(fnt.get_height() + sp for (_, fnt, _, sp) in entries)
        self.sidebar_max_scroll = max(0.0, float(total_h - body_rect.height + 12))
        self.sidebar_scroll_y = max(0.0, min(self.sidebar_max_scroll, self.sidebar_scroll_y))

        cur_y = body_rect.y - int(self.sidebar_scroll_y)
        for (ln, fnt, col, sp) in entries:
            h_ln = fnt.get_height()
            if cur_y + h_ln >= body_rect.y and cur_y <= body_rect.bottom:
                surface.blit(fnt.render(ln, True, col), (body_rect.x + 2, cur_y))
            cur_y += h_ln + sp

        surface.set_clip(old_clip)

        # Scrollbar indikator jika konten melebihi tinggi panel
        if self.sidebar_max_scroll > 0:
            track = pygame.Rect(sb.right - 7, body_rect.y, 4, body_rect.height)
            pygame.draw.rect(surface, (230, 222, 210), track, border_radius=2)
            ratio = body_rect.height / float(max(1, total_h))
            thumb_h = max(24, int(body_rect.height * ratio))
            thumb_y = body_rect.y + int((body_rect.height - thumb_h) * (self.sidebar_scroll_y / self.sidebar_max_scroll))
            pygame.draw.rect(surface, (185, 165, 140), (track.x, thumb_y, 4, thumb_h), border_radius=2)

    def _build_detail_entries(self, add_block, font_bubble, font_sm, font_tiny) -> None:
        nd = self.selected_node or self.root_node
        if not nd:
            add_block("Belum ada data simpul pohon.", font_sm, COLOR_TEXT_SECONDARY, 4)
            return

        meta = nd.meta or {}
        if self.mode_tag == "PLANNING" and meta:
            role = meta.get("role", "STEP")
            add_block(meta.get("title", nd.label), font_bubble, COLOR_TEXT_HEADING, 4)
            if role == "ROOT":
                add_block(f"Mesin: {meta.get('engine', '-')}", font_sm, COLOR_TEXT_ACCENT, 2)
                add_block(f"Total Aksi: {meta.get('total_actions', 0)}  |  Simpul Diekspansi: {meta.get('nodes_expanded', 0)}  |  Waktu: {meta.get('time_ms', 0.0):.2f} ms", font_tiny, COLOR_TEXT_SECONDARY, 8)
                add_block("Apa arti simpul ini?", font_sm, COLOR_TEXT_PRIMARY, 2)
                add_block(meta.get("description", ""), font_tiny, COLOR_TEXT_SECONDARY, 8)

                add_block("INITIAL STATE (s0) — Fakta Awal:", font_sm, COLOR_TEXT_ACCENT, 3)
                for p in meta.get("state_fluents", []):
                    add_block(f"• {p}", font_tiny, COLOR_TEXT_PRIMARY, 2)
                add_block("", font_tiny, COLOR_TEXT_PRIMARY, 4)
                add_block("GOAL STATE (G) — Sasaran Akhir:", font_sm, COLOR_TEXT_SUCCESS, 3)
                for p in meta.get("goal_fluents", []):
                    add_block(f"• {p}", font_tiny, COLOR_TEXT_SUCCESS, 2)
            else:
                badge = "[GOAL TERCAPAI]" if role == "GOAL" else f"[AKSI LANGKAH #{meta.get('step_idx', '-')}]"
                badge_col = COLOR_TEXT_SUCCESS if role == "GOAL" else COLOR_TEXT_ACCENT
                add_block(badge, font_sm, badge_col, 4)
                add_block(f"Deskripsi: {meta.get('description', '-')}", font_sm, COLOR_TEXT_PRIMARY, 6)
                add_block(
                    f"Metrik A*:  g(n) = {meta.get('g', 0):.0f} (biaya)  |  h(n) = {meta.get('h', 0)} (sisa gol)  |  f(n) = {meta.get('f', 0):.0f}",
                    font_tiny, COLOR_TEXT_WARNING, 8,
                )

                add_block("1. PRECONDITIONS (Syarat Aksi Boleh Jalan):", font_sm, COLOR_TEXT_ACCENT, 3)
                for p in meta.get("preconditions", []) or ["(Tidak ada)"]:
                    add_block(f"• {p}", font_tiny, COLOR_TEXT_PRIMARY, 2)

                add_block("", font_tiny, COLOR_TEXT_PRIMARY, 4)
                add_block("2. EFFECTS (Perubahan Dunia Setelah Aksi):", font_sm, COLOR_TEXT_PRIMARY, 3)
                for p in meta.get("add_list", []):
                    add_block(f"+ ADD: {p}", font_tiny, COLOR_TEXT_SUCCESS, 2)
                for p in meta.get("del_list", []):
                    add_block(f"- DEL: {p}", font_tiny, COLOR_TEXT_DANGER, 2)
                if not meta.get("add_list") and not meta.get("del_list"):
                    add_block("• (Tidak ada perubahan)", font_tiny, COLOR_TEXT_SECONDARY, 2)

                add_block("", font_tiny, COLOR_TEXT_PRIMARY, 4)
                add_block("3. STATE FLUENTS AKTIF SETELAH AKSI INI:", font_sm, COLOR_TEXT_HEADING, 3)
                for p in meta.get("state_fluents", []):
                    add_block(f"• {p}", font_tiny, COLOR_TEXT_PRIMARY, 2)

                rem = meta.get("goal_remaining", [])
                add_block("", font_tiny, COLOR_TEXT_PRIMARY, 4)
                if rem:
                    add_block(f"Sisa Goal Belum Terpenuhi ({len(rem)}):", font_sm, COLOR_TEXT_WARNING, 2)
                    for p in rem:
                        add_block(f"• {p}", font_tiny, COLOR_TEXT_SECONDARY, 2)
                else:
                    add_block("Seluruh Goal PDDL telah terpenuhi (Goal Reached)!", font_sm, COLOR_TEXT_SUCCESS, 4)
        else:
            add_block(nd.label, font_bubble, COLOR_TEXT_HEADING, 4)
            if nd.sub_label:
                add_block(nd.sub_label, font_sm, COLOR_TEXT_ACCENT, 4)
            if nd.score_str:
                add_block(f"Evaluasi / Skor: {nd.score_str}", font_sm, COLOR_TEXT_SUCCESS if nd.is_best else COLOR_TEXT_PRIMARY, 6)
            status_txt = "Cabang Dipangkas (Pruned)" if nd.is_pruned else ("Jalur Terbaik / Terpilih" if nd.is_best else f"Tipe Simpul: {nd.node_type}")
            add_block(status_txt, font_tiny, COLOR_TEXT_SECONDARY, 6)
            add_block(f"Jumlah Cabang Anak Langsung: {len(nd.children)}", font_tiny, COLOR_TEXT_SECONDARY, 4)

    def _build_theory_entries(self, add_block, font_bubble, font_sm, font_tiny) -> None:
        if self.mode_tag == "PLANNING":
            add_block("APA ITU POHON PERENCANAAN PDDL?", font_bubble, COLOR_TEXT_HEADING, 6)
            add_block(
                "Pohon ini memvisualisasikan Classical Planning (Materi 08) berbasis STRIPS/PDDL. "
                "Berbeda dengan Pathfinding di peta (yang mencari koordinat x,y), PDDL Planning mencari "
                "urutan aksi logis tingkat tinggi untuk mengubah kondisi dunia awal (s0) menjadi sasaran (Goal).",
                font_tiny, COLOR_TEXT_PRIMARY, 8,
            )
            add_block("1. Struktur Komponen PDDL:", font_sm, COLOR_TEXT_ACCENT, 3)
            add_block("• Initial State (s0): Kumpulan fakta (predikat) saat peti baru dibuka atau duel krisis terjadi.", font_tiny, COLOR_TEXT_PRIMARY, 2)
            add_block("• Actions (Aksi STRIPS): Tiap aksi memiliki Preconditions (syarat), Add-List (fakta baru), dan Del-List (fakta lama yang dihapus).", font_tiny, COLOR_TEXT_PRIMARY, 2)
            add_block("• Goal State (G): Kondisi akhir yang harus terpenuhi (misal: Kuro mencegat di jembatan & Shiro menjaga peti sisa).", font_tiny, COLOR_TEXT_PRIMARY, 8)

            add_block("2. Forward Progression (A*) vs Backward Regression:", font_sm, COLOR_TEXT_ACCENT, 3)
            add_block("• Forward Progression (A*): Bergerak maju dari s0 ke Goal menggunakan f(n) = g(n) + h(n), di mana h(n) adalah jumlah predikat Goal yang belum terpenuhi.", font_tiny, COLOR_TEXT_PRIMARY, 2)
            add_block("• Backward Regression (STRIPS): Bergerak mundur dari Goal ke s0 dengan memilih aksi yang relevan (Add-List menyentuh sub-goal) dan konsisten.", font_tiny, COLOR_TEXT_PRIMARY, 8)

            add_block("3. Arti Warna Kotak Simpul:", font_sm, COLOR_TEXT_ACCENT, 3)
            add_block("• Emas (State Awal s0): Kondisi awal sebelum aksi dijalankan.", font_tiny, COLOR_TEXT_WARNING, 2)
            add_block("• Biru (Step Aksi): Langkah transisi antar-state beserta nilai g, h, f.", font_tiny, COLOR_TEXT_ACCENT, 2)
            add_block("• Hijau (Goal Reached): Aksi terakhir yang membuat seluruh Goal terpenuhi.", font_tiny, COLOR_TEXT_SUCCESS, 2)
        elif self.mode_tag == "LOGIC":
            add_block("APA ITU POHON RESOLUSI REFUTASI?", font_bubble, COLOR_TEXT_HEADING, 6)
            add_block(
                "Pohon ini memvisualisasikan inferensi Knowledge Base Proposisional (Materi 07). "
                "Untuk membuktikan apakah suatu kesimpulan (Query) bernilai benar, sistem menegasi Query (~Query) "
                "lalu menggabungkan klausa CNF hingga menemukan kontradiksi kosong ([]).",
                font_tiny, COLOR_TEXT_PRIMARY, 6,
            )
        else:
            add_block("APA ITU POHON MINIMAX / ALPHA-BETA?", font_bubble, COLOR_TEXT_HEADING, 6)
            add_block(
                "Pohon keputusan adversarial (Materi 04) yang mengevaluasi langkah terbaik NPC (MAX) "
                "terhadap respon optimal pemain (MIN) hingga kedalaman pencarian tertentu.",
                font_tiny, COLOR_TEXT_PRIMARY, 6,
            )
