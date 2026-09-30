"""Tree Overlay: Visualisasi pohon keputusan AI (Decision Tree) secara real-time.

Menampilkan pohon pencarian Minimax / Alpha-Beta di bagian bawah battle log
dengan navigasi horizontal & vertikal (scroll kanan-kiri & atas-bawah),
tanpa ada node yang menumpuk bahkan hingga depth 8.
"""

import math
import pygame
from . import config
from .battle_ai import TreeNode

SRCALPHA = getattr(pygame, "SRCALPHA", 0x00010000)

# Palet warna node
COLOR_MAX_BG = (255, 165, 50)        # Oranye untuk MAX node
COLOR_MAX_BORDER = (210, 120, 20)
COLOR_MIN_BG = (60, 140, 220)        # Biru untuk MIN node
COLOR_MIN_BORDER = (30, 100, 180)
COLOR_CHANCE_BG = (170, 85, 215)     # Ungu untuk CHANCE node (Expectimax)
COLOR_CHANCE_BORDER = (130, 50, 175)
COLOR_PRUNED_BG = (180, 180, 185)    # Abu-abu untuk pruned
COLOR_PRUNED_BORDER = (140, 140, 145)
COLOR_BEST_GLOW = (50, 205, 80)      # Hijau terang untuk jalur terbaik
COLOR_LINE = (160, 165, 175)         # Garis koneksi normal
COLOR_LINE_BEST = (50, 200, 80)      # Garis koneksi jalur terbaik
COLOR_LINE_PRUNED = (220, 70, 60)    # Garis putus-putus merah pruned
COLOR_PANEL_BG = (250, 250, 247, 245)
COLOR_PANEL_BORDER = (75, 85, 105, 230)
COLOR_TOGGLE_ON = (45, 160, 85)
COLOR_TOGGLE_OFF = (190, 60, 60)

# Ukuran node kompak & proporsional
NODE_W = 66
NODE_H = 26
NODE_PAD_X = 10      # Jarak horizontal antar node di level yang sama
NODE_PAD_Y = 36      # Jarak vertikal antar level (depth)
LABEL_SHORT = {
    "ATTACK": "ATK",
    "HEAVY_ATTACK": "H.ATK",
    "DEFEND": "DEF",
    "POTION": "POT",
}


def _draw_rounded_rect(surface, rect, color, border_radius=5, border_color=None, border_width=1):
    """Gambar rounded rectangle dengan opsi border."""
    pygame.draw.rect(surface, color, rect, border_radius=border_radius)
    if border_color:
        pygame.draw.rect(surface, border_color, rect, border_width, border_radius=border_radius)


def _draw_dashed_line(surface, color, start, end, dash_len=5, gap_len=3, width=2):
    """Gambar garis putus-putus antara dua titik."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dist = math.hypot(dx, dy)
    if dist < 1:
        return
    ndx = dx / dist
    ndy = dy / dist
    pos = 0.0
    while pos < dist:
        seg_end = min(pos + dash_len, dist)
        p1 = (int(start[0] + ndx * pos), int(start[1] + ndy * pos))
        p2 = (int(start[0] + ndx * seg_end), int(start[1] + ndy * seg_end))
        pygame.draw.line(surface, color, p1, p2, width)
        pos = seg_end + gap_len


class TreeOverlay:
    """Panel overlay di bagian bawah battle log untuk visualisasi Decision Tree AI."""

    def __init__(self, fonts):
        self.fonts = fonts
        self.visible = True         # Aktif secara default di mode duel
        self.tree_root = None       # TreeNode root dari pencarian terakhir
        self.scroll_x = 0           # Offset scroll horizontal (px)
        self.scroll_y = 0           # Offset scroll vertikal (px)
        self.max_render_depth = 3   # Kedalaman maksimum yang dirender (bisa hingga 8)

        self._cached_layout = None  # Cache list of (node, cx, cy, px, py, is_best, depth)
        self._total_tree_w = 0.0    # Total lebar pohon (px)
        self._max_tree_y = 0.0      # Total tinggi pohon (px)
        self._root_cx = 0.0         # Koordinat x root
        self._needs_rebuild = True

        # State interaksi mouse drag (panning)
        self._is_dragging = False
        self._drag_start_pos = (0, 0)
        self._drag_start_scroll_x = 0
        self._drag_start_scroll_y = 0

        # State scrollbar drag
        self._is_dragging_h_thumb = False
        self._is_dragging_v_thumb = False
        self._h_thumb_drag_start_x = 0
        self._v_thumb_drag_start_y = 0
        self._h_thumb_scroll_start_x = 0
        self._v_thumb_scroll_start_y = 0

        # Posisi elemen UI (dihitung saat draw)
        self.panel_rect = pygame.Rect(0, 0, 0, 0)
        self.toggle_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_depth_minus = pygame.Rect(0, 0, 0, 0)
        self.btn_depth_plus = pygame.Rect(0, 0, 0, 0)
        self.btn_focus_root = pygame.Rect(0, 0, 0, 0)
        self._tree_area_rect = pygame.Rect(0, 0, 0, 0)
        self._h_track_rect = pygame.Rect(0, 0, 0, 0)
        self._h_thumb_rect = pygame.Rect(0, 0, 0, 0)
        self._v_track_rect = pygame.Rect(0, 0, 0, 0)
        self._v_thumb_rect = pygame.Rect(0, 0, 0, 0)

    def set_tree(self, tree_root):
        """Update tree data dari AI solver."""
        if tree_root is not self.tree_root:
            self.tree_root = tree_root
            self._needs_rebuild = True

    def toggle(self):
        self.visible = not self.visible

    # ------------------------------------------------------------------ #
    # Layout Non-Overlapping: Algoritma Subtree Width Bottom-Up
    # ------------------------------------------------------------------ #
    def _recompute_layout(self, area_w, area_h):
        """Hitung posisi (x, y) setiap node tanpa tumpang tindih."""
        if self.tree_root is None:
            self._cached_layout = None
            self._total_tree_w = 0.0
            self._max_tree_y = 0.0
            self._root_cx = 0.0
            return

        # Pass 1: Hitung lebar dan pusat relatif tiap subtree bottom-up
        metrics = {}  # id(node) -> (width, rel_cx)

        def _calc_metrics(node, depth):
            nid = id(node)
            if depth >= self.max_render_depth or node.pruned or not node.children:
                w = float(NODE_W + NODE_PAD_X)
                rel_cx = w / 2.0
                metrics[nid] = (w, rel_cx)
                return w, rel_cx

            cur_x = 0.0
            c_centers = []
            for c in node.children:
                cw, crx = _calc_metrics(c, depth + 1)
                c_centers.append(cur_x + crx)
                cur_x += cw

            w = max(float(NODE_W + NODE_PAD_X), cur_x)
            rel_cx = (c_centers[0] + c_centers[-1]) / 2.0
            metrics[nid] = (w, rel_cx)
            return w, rel_cx

        total_w, root_rel_cx = _calc_metrics(self.tree_root, 0)

        # Pass 2: Tetapkan koordinat absolut top-down
        layout = []
        max_y = 0.0

        def _assign_coords(node, depth, x_start, parent_pos, is_best):
            nonlocal max_y
            nid = id(node)
            w, rel_cx = metrics[nid]
            abs_cx = x_start + rel_cx
            abs_cy = 20.0 + depth * NODE_PAD_Y
            if abs_cy > max_y:
                max_y = abs_cy

            px, py = parent_pos if parent_pos else (None, None)
            layout.append((node, abs_cx, abs_cy, px, py, is_best, depth))

            if depth >= self.max_render_depth or node.pruned or not node.children:
                return

            cur_x = x_start
            for c in node.children:
                cw, _ = metrics[id(c)]
                _assign_coords(c, depth + 1, cur_x, (abs_cx, abs_cy), c.is_best)
                cur_x += cw

        # Berikan margin awal 24px
        _assign_coords(self.tree_root, 0, 24.0, None, False)

        self._cached_layout = layout
        self._total_tree_w = total_w + 48.0
        self._max_tree_y = max_y + NODE_H + 20.0
        self._root_cx = 24.0 + root_rel_cx

        # Auto-center scroll horizontal pada Root saat layout pertama kali dibuat
        self.scroll_x = max(0, int(self._root_cx - area_w / 2.0))
        self.scroll_y = 0
        self._needs_rebuild = False

    def _clamp_scroll(self, area_w, area_h):
        """Batasi scroll horizontal dan vertikal agar tetap di batas kanvas."""
        max_scroll_x = max(0, int(self._total_tree_w - area_w))
        max_scroll_y = max(0, int(self._max_tree_y - area_h))
        self.scroll_x = max(0, min(self.scroll_x, max_scroll_x))
        self.scroll_y = max(0, min(self.scroll_y, max_scroll_y))

    # ------------------------------------------------------------------ #
    # Draw Utama
    # ------------------------------------------------------------------ #
    def draw(self, screen, custom_rect=None):
        """Render panel decision tree di bawah battle log arena."""
        if custom_rect is not None:
            panel_x, panel_y, panel_w, panel_h = (
                custom_rect.x, custom_rect.y, custom_rect.width, custom_rect.height
            )
        else:
            w, h = screen.get_size()
            panel_w = config.TREE_PANEL_WIDTH
            panel_x = w - panel_w - 12
            panel_y = 12
            panel_h = h - 24

        font_title = self.fonts.get("title", self.fonts["sm"])
        font_sm = self.fonts["sm"]
        font_bubble = self.fonts.get("bubble", font_sm)

        # Jika sedang nonaktif/OFF, tidak perlu digambar sama sekali (bersih)
        if not self.visible:
            self.panel_rect = pygame.Rect(0, 0, 0, 0)
            self.toggle_rect = pygame.Rect(0, 0, 0, 0)
            return

        self.panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        # Background Panel
        bg_surf = pygame.Surface((panel_w, panel_h), SRCALPHA)
        bg_surf.fill(COLOR_PANEL_BG)
        pygame.draw.rect(bg_surf, COLOR_PANEL_BORDER, bg_surf.get_rect(), 2, border_radius=8)
        screen.blit(bg_surf, (panel_x, panel_y))

        # -------------------------------------------------------------- #
        # Header Bar Kompak
        # -------------------------------------------------------------- #
        header_h = 30
        header_rect = pygame.Rect(panel_x + 6, panel_y + 5, panel_w - 12, header_h)
        pygame.draw.rect(screen, (235, 246, 240, 245), header_rect, border_radius=6)
        pygame.draw.rect(screen, (100, 195, 130, 200), header_rect, 1, border_radius=6)

        # 1. Judul
        title = font_title.render("🌲 DECISION TREE", True, (20, 120, 50))
        screen.blit(title, (header_rect.x + 8, header_rect.centery - title.get_height() // 2))

        # 2. Depth Control [-] [Depth: X] [+]
        dx = header_rect.x + title.get_width() + 16
        depth_label = font_sm.render(f"Depth: {self.max_render_depth}", True, config.DEBUG_TEXT_PRIMARY)
        screen.blit(depth_label, (dx, header_rect.centery - depth_label.get_height() // 2))

        self.btn_depth_minus = pygame.Rect(dx + depth_label.get_width() + 6, header_rect.y + 4, 20, 22)
        self.btn_depth_plus = pygame.Rect(self.btn_depth_minus.right + 3, header_rect.y + 4, 20, 22)

        for btn, text, fill in [
            (self.btn_depth_minus, "-", (210, 75, 75)),
            (self.btn_depth_plus, "+", (50, 160, 85)),
        ]:
            pygame.draw.rect(screen, fill, btn, border_radius=4)
            ts = font_bubble.render(text, True, (255, 255, 255))
            screen.blit(ts, (btn.centerx - ts.get_width() // 2, btn.centery - ts.get_height() // 2))

        # 3. Tombol Fokus Root [🎯 Fokus]
        focus_x = self.btn_depth_plus.right + 10
        focus_w = 64
        self.btn_focus_root = pygame.Rect(focus_x, header_rect.y + 4, focus_w, 22)
        pygame.draw.rect(screen, (70, 130, 200), self.btn_focus_root, border_radius=4)
        focus_ts = font_sm.render("🎯 Fokus", True, (255, 255, 255))
        screen.blit(
            focus_ts,
            (
                self.btn_focus_root.centerx - focus_ts.get_width() // 2,
                self.btn_focus_root.centery - focus_ts.get_height() // 2,
            ),
        )

        # 4. Legend Kompak Horizontal
        leg_x = self.btn_focus_root.right + 16
        leg_y = header_rect.centery

        # Best path
        pygame.draw.line(screen, COLOR_LINE_BEST, (leg_x, leg_y), (leg_x + 14, leg_y), 3)
        bp_txt = font_sm.render("Best Path", True, config.DEBUG_TEXT_PRIMARY)
        screen.blit(bp_txt, (leg_x + 18, leg_y - bp_txt.get_height() // 2))
        leg_x += bp_txt.get_width() + 24

        # Pruned
        _draw_dashed_line(
            screen, COLOR_LINE_PRUNED, (leg_x, leg_y), (leg_x + 14, leg_y), dash_len=4, gap_len=3, width=2
        )
        pr_txt = font_sm.render("Pruned ✂", True, config.DEBUG_TEXT_PRIMARY)
        screen.blit(pr_txt, (leg_x + 18, leg_y - pr_txt.get_height() // 2))
        leg_x += pr_txt.get_width() + 24

        # MAX Node
        pygame.draw.rect(screen, COLOR_MAX_BG, pygame.Rect(leg_x, leg_y - 5, 10, 10), border_radius=2)
        max_txt = font_sm.render("MAX", True, config.DEBUG_TEXT_PRIMARY)
        screen.blit(max_txt, (leg_x + 14, leg_y - max_txt.get_height() // 2))
        leg_x += max_txt.get_width() + 18

        # MIN Node
        pygame.draw.rect(screen, COLOR_MIN_BG, pygame.Rect(leg_x, leg_y - 5, 10, 10), border_radius=2)
        min_txt = font_sm.render("MIN", True, config.DEBUG_TEXT_PRIMARY)
        screen.blit(min_txt, (leg_x + 14, leg_y - min_txt.get_height() // 2))
        leg_x += min_txt.get_width() + 16

        # CHANCE Node
        pygame.draw.rect(screen, COLOR_CHANCE_BG, pygame.Rect(leg_x, leg_y - 5, 10, 10), border_radius=2)
        chance_txt = font_sm.render("CHANCE", True, config.DEBUG_TEXT_PRIMARY)
        screen.blit(chance_txt, (leg_x + 14, leg_y - chance_txt.get_height() // 2))
        leg_x += chance_txt.get_width() + 16

        # Hint navigasi scroll
        hint_nav = font_sm.render("(Drag / Shift+Scroll)", True, (120, 135, 155))
        screen.blit(hint_nav, (leg_x, leg_y - hint_nav.get_height() // 2))

        # 5. Tombol Toggle ON/OFF (Kanan atas)
        toggle_w = 38
        self.toggle_rect = pygame.Rect(header_rect.right - toggle_w - 4, header_rect.y + 4, toggle_w, 22)
        t_fill = COLOR_TOGGLE_ON if self.visible else COLOR_TOGGLE_OFF
        pygame.draw.rect(screen, t_fill, self.toggle_rect, border_radius=8)
        t_text = font_sm.render("ON", True, (255, 255, 255))
        screen.blit(
            t_text,
            (
                self.toggle_rect.centerx - t_text.get_width() // 2,
                self.toggle_rect.centery - t_text.get_height() // 2,
            ),
        )

        # -------------------------------------------------------------- #
        # Area Kanvas Tree (Clipped & Virtual Viewport)
        # -------------------------------------------------------------- #
        tree_area_x = panel_x + 6
        tree_area_y = header_rect.bottom + 4
        # Sisakan 10px di bawah untuk horizontal scrollbar dan 8px di kanan untuk vertical scrollbar
        tree_area_w = panel_w - 12 - 10
        tree_area_h = panel_h - (tree_area_y - panel_y) - 14

        self._tree_area_rect = pygame.Rect(tree_area_x, tree_area_y, tree_area_w, tree_area_h)

        if self.tree_root is not None:
            if self._needs_rebuild or self._cached_layout is None:
                self._recompute_layout(tree_area_w, tree_area_h)

            self._clamp_scroll(tree_area_w, tree_area_h)

            # Viewport boundaries dalam koordinat kanvas
            vp_min_x = self.scroll_x
            vp_max_x = self.scroll_x + tree_area_w
            vp_min_y = self.scroll_y
            vp_max_y = self.scroll_y + tree_area_h

            screen.set_clip(self._tree_area_rect)

            # Background kanvas pohon (lembut)
            pygame.draw.rect(screen, (244, 247, 250), self._tree_area_rect, border_radius=4)

            # 1. Gambar Garis Koneksi (dengan Viewport Culling)
            for node, cx, cy, px, py, is_best_edge, depth in self._cached_layout:
                if px is not None and py is not None:
                    # Skip jika garis berada jauh di luar viewport
                    if (
                        max(px, cx) < vp_min_x - 60
                        or min(px, cx) > vp_max_x + 60
                        or max(py, cy) < vp_min_y - 40
                        or min(py, cy) > vp_max_y + 40
                    ):
                        continue

                    # Konversi ke screen space
                    sx1 = int(px - self.scroll_x + tree_area_x)
                    sy1 = int(py + NODE_H // 2 - self.scroll_y + tree_area_y)
                    sx2 = int(cx - self.scroll_x + tree_area_x)
                    sy2 = int(cy - NODE_H // 2 + 1 - self.scroll_y + tree_area_y)

                    if node.pruned:
                        _draw_dashed_line(
                            screen, COLOR_LINE_PRUNED, (sx1, sy1), (sx2, sy2), dash_len=4, gap_len=3, width=2
                        )
                    elif is_best_edge:
                        pygame.draw.line(screen, COLOR_LINE_BEST, (sx1, sy1), (sx2, sy2), 3)
                    else:
                        pygame.draw.line(screen, COLOR_LINE, (sx1, sy1), (sx2, sy2), 1)

            # 2. Gambar Node (dengan Viewport Culling)
            for node, cx, cy, px, py, is_best_edge, depth in self._cached_layout:
                # Cek apakah node berada di dalam viewport
                if (
                    cx < vp_min_x - NODE_W
                    or cx > vp_max_x + NODE_W
                    or cy < vp_min_y - NODE_H
                    or cy > vp_max_y + NODE_H
                ):
                    continue

                nx = int(cx - NODE_W // 2 - self.scroll_x + tree_area_x)
                ny = int(cy - NODE_H // 2 - self.scroll_y + tree_area_y)
                node_rect = pygame.Rect(nx, ny, NODE_W, NODE_H)

                if node.pruned:
                    bg = COLOR_PRUNED_BG
                    border = COLOR_PRUNED_BORDER
                elif node.node_type == "MAX":
                    bg = COLOR_MAX_BG
                    border = COLOR_MAX_BORDER
                elif node.node_type == "CHANCE":
                    bg = COLOR_CHANCE_BG
                    border = COLOR_CHANCE_BORDER
                else:
                    bg = COLOR_MIN_BG
                    border = COLOR_MIN_BORDER

                # Glow effect untuk best path
                if is_best_edge and not node.pruned:
                    glow_rect = node_rect.inflate(4, 4)
                    pygame.draw.rect(screen, COLOR_BEST_GLOW, glow_rect, border_radius=7, width=2)

                _draw_rounded_rect(screen, node_rect, bg, border_radius=5, border_color=border, border_width=1)

                # Label atas: Tipe Node (MAX / MIN / ✂)
                type_label = node.node_type if not node.pruned else "✂"
                type_surf = font_bubble.render(type_label, True, (255, 255, 255))
                type_rect = pygame.Rect(nx, ny, NODE_W, 11)
                type_bg_color = (*border[:3], 200) if len(border) == 3 else border
                pygame.draw.rect(screen, type_bg_color, type_rect, border_radius=0)
                pygame.draw.rect(screen, type_bg_color, pygame.Rect(nx, ny, NODE_W, 6), border_radius=5)
                screen.blit(
                    type_surf,
                    (
                        type_rect.centerx - type_surf.get_width() // 2,
                        type_rect.y,
                    ),
                )

                # Label bawah: Aksi + Skor
                if node.action:
                    act_short = LABEL_SHORT.get(node.action, node.action[:5])
                else:
                    act_short = "ROOT"

                score_str = f"{node.score}" if node.score is not None else "?"

                if node.pruned:
                    bottom_text = f"{act_short}"
                    text_color = (95, 95, 100)
                else:
                    bottom_text = f"{act_short}:{score_str}"
                    text_color = (255, 255, 255)

                bottom_surf = font_bubble.render(bottom_text, True, text_color)
                screen.blit(
                    bottom_surf,
                    (
                        node_rect.centerx - bottom_surf.get_width() // 2,
                        ny + 12,
                    ),
                )

                # Tanda silang merah untuk pruned
                if node.pruned:
                    x_surf = font_bubble.render("✕", True, (220, 50, 40))
                    screen.blit(x_surf, (node_rect.right - 10, node_rect.top - 2))

            screen.set_clip(None)

            # ---------------------------------------------------------- #
            # 3. Scrollbar Horizontal & Vertikal
            # ---------------------------------------------------------- #
            max_scroll_x = max(0, int(self._total_tree_w - tree_area_w))
            max_scroll_y = max(0, int(self._max_tree_y - tree_area_h))

            # Horizontal Scrollbar (di bagian bawah kanvas)
            self._h_track_rect = pygame.Rect(tree_area_x, tree_area_y + tree_area_h + 2, tree_area_w, 8)
            pygame.draw.rect(screen, (220, 225, 235), self._h_track_rect, border_radius=3)

            if max_scroll_x > 0:
                thumb_w = max(24, int((tree_area_w / self._total_tree_w) * tree_area_w))
                thumb_x = self._h_track_rect.x + int(
                    (self.scroll_x / float(max_scroll_x)) * (self._h_track_rect.width - thumb_w)
                )
                self._h_thumb_rect = pygame.Rect(thumb_x, self._h_track_rect.y, thumb_w, 8)
                thumb_color = (110, 130, 160) if self._is_dragging_h_thumb else (145, 165, 195)
                pygame.draw.rect(screen, thumb_color, self._h_thumb_rect, border_radius=3)
            else:
                self._h_thumb_rect = pygame.Rect(0, 0, 0, 0)

            # Vertical Scrollbar (di sebelah kanan kanvas)
            self._v_track_rect = pygame.Rect(tree_area_x + tree_area_w + 2, tree_area_y, 8, tree_area_h)
            pygame.draw.rect(screen, (220, 225, 235), self._v_track_rect, border_radius=3)

            if max_scroll_y > 0:
                thumb_h = max(20, int((tree_area_h / self._max_tree_y) * tree_area_h))
                thumb_y = self._v_track_rect.y + int(
                    (self.scroll_y / float(max_scroll_y)) * (self._v_track_rect.height - thumb_h)
                )
                self._v_thumb_rect = pygame.Rect(self._v_track_rect.x, thumb_y, 8, thumb_h)
                thumb_color = (110, 130, 160) if self._is_dragging_v_thumb else (145, 165, 195)
                pygame.draw.rect(screen, thumb_color, self._v_thumb_rect, border_radius=3)
            else:
                self._v_thumb_rect = pygame.Rect(0, 0, 0, 0)

        else:
            # Pesan kosong jika belum ada data pohon
            empty_text = font_sm.render(
                "Menunggu input aksi... (Pohon pencarian AI akan direkam otomatis saat giliran NPC)",
                True,
                config.DEBUG_TEXT_SECONDARY,
            )
            screen.blit(empty_text, (panel_x + 20, tree_area_y + 20))

    # ------------------------------------------------------------------ #
    # Event Handling
    # ------------------------------------------------------------------ #
    def handle_event(self, event):
        """Handle mouse clicks, mouse dragging, dan scroll horizontal/vertikal."""
        mousewheel = getattr(pygame, "MOUSEWHEEL", 1027)

        # 1. Mouse Button Down
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            # Tombol toggle ON/OFF
            if self.toggle_rect.collidepoint(pos):
                self.toggle()
                return True

            if not self.visible:
                return False

            # Tombol Depth [-]
            if self.btn_depth_minus.collidepoint(pos):
                if self.max_render_depth > 1:
                    self.max_render_depth -= 1
                    self._needs_rebuild = True
                return True

            # Tombol Depth [+]
            if self.btn_depth_plus.collidepoint(pos):
                if self.max_render_depth < 8:
                    self.max_render_depth += 1
                    self._needs_rebuild = True
                return True

            # Tombol Fokus Root [🎯 Fokus]
            if self.btn_focus_root.collidepoint(pos):
                if self._tree_area_rect.width > 0:
                    self.scroll_x = max(0, int(self._root_cx - self._tree_area_rect.width / 2.0))
                self.scroll_y = 0
                return True

            # Klik pada Horizontal Scrollbar Thumb
            if self._h_thumb_rect.collidepoint(pos):
                self._is_dragging_h_thumb = True
                self._h_thumb_drag_start_x = pos[0]
                self._h_thumb_scroll_start_x = self.scroll_x
                return True

            # Klik pada Horizontal Scrollbar Track (langsung lompat)
            if self._h_track_rect.collidepoint(pos):
                track_w = self._h_track_rect.width - self._h_thumb_rect.width
                if track_w > 0:
                    ratio = (pos[0] - self._h_track_rect.x) / float(self._h_track_rect.width)
                    max_scroll_x = max(0, int(self._total_tree_w - self._tree_area_rect.width))
                    self.scroll_x = max(0, min(max_scroll_x, int(ratio * max_scroll_x)))
                return True

            # Klik pada Vertical Scrollbar Thumb
            if self._v_thumb_rect.collidepoint(pos):
                self._is_dragging_v_thumb = True
                self._v_thumb_drag_start_y = pos[1]
                self._v_thumb_scroll_start_y = self.scroll_y
                return True

            # Klik pada Vertical Scrollbar Track
            if self._v_track_rect.collidepoint(pos):
                track_h = self._v_track_rect.height - self._v_thumb_rect.height
                if track_h > 0:
                    ratio = (pos[1] - self._v_track_rect.y) / float(self._v_track_rect.height)
                    max_scroll_y = max(0, int(self._max_tree_y - self._tree_area_rect.height))
                    self.scroll_y = max(0, min(max_scroll_y, int(ratio * max_scroll_y)))
                return True

            # Klik dan drag langsung pada kanvas pohon untuk panning 2D
            if self._tree_area_rect.collidepoint(pos):
                self._is_dragging = True
                self._drag_start_pos = pos
                self._drag_start_scroll_x = self.scroll_x
                self._drag_start_scroll_y = self.scroll_y
                return True

        # 2. Mouse Button Up (Lepas Drag)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._is_dragging = False
            self._is_dragging_h_thumb = False
            self._is_dragging_v_thumb = False

        # 3. Mouse Motion (Panning & Scrollbar Dragging)
        elif event.type == pygame.MOUSEMOTION:
            pos = event.pos
            # Panning kanvas langsung
            if self._is_dragging:
                dx = pos[0] - self._drag_start_pos[0]
                dy = pos[1] - self._drag_start_pos[1]
                self.scroll_x = self._drag_start_scroll_x - dx
                self.scroll_y = self._drag_start_scroll_y - dy
                self._clamp_scroll(self._tree_area_rect.width, self._tree_area_rect.height)
                return True

            # Drag thumb horizontal
            if self._is_dragging_h_thumb:
                dx = pos[0] - self._h_thumb_drag_start_x
                track_w = self._h_track_rect.width - self._h_thumb_rect.width
                max_scroll_x = max(0, int(self._total_tree_w - self._tree_area_rect.width))
                if track_w > 0 and max_scroll_x > 0:
                    scroll_delta = int((dx / float(track_w)) * max_scroll_x)
                    self.scroll_x = max(0, min(max_scroll_x, self._h_thumb_scroll_start_x + scroll_delta))
                return True

            # Drag thumb vertikal
            if self._is_dragging_v_thumb:
                dy = pos[1] - self._v_thumb_drag_start_y
                track_h = self._v_track_rect.height - self._v_thumb_rect.height
                max_scroll_y = max(0, int(self._max_tree_y - self._tree_area_rect.height))
                if track_h > 0 and max_scroll_y > 0:
                    scroll_delta = int((dy / float(track_h)) * max_scroll_y)
                    self.scroll_y = max(0, min(max_scroll_y, self._v_thumb_scroll_start_y + scroll_delta))
                return True

        # 4. Mouse Wheel Scroll (Vertikal & Horizontal)
        elif event.type == mousewheel:
            if self.visible and self.panel_rect.collidepoint(pygame.mouse.get_pos()):
                # Jika tombol Shift ditekan, scroll roda mouse akan menggeser horizontal (kiri-kanan)
                mods = pygame.key.get_mods()
                if mods & pygame.KMOD_SHIFT:
                    self.scroll_x -= event.y * 60
                else:
                    self.scroll_y -= event.y * 30

                # Scroll horizontal bawaan mouse / trackpad
                wheel_x = getattr(event, "x", 0)
                if wheel_x != 0:
                    self.scroll_x += wheel_x * 50

                self._clamp_scroll(self._tree_area_rect.width, self._tree_area_rect.height)
                return True

        return False
