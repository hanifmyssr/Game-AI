"""GuideModal: Panduan Awal (Mission Briefing) & Buku Panduan 3-Tab (Cozy Warm Parchment).

Menyajikan panduan lengkap yang menyatu dengan tema jurnal petualang:
1. Tab 1: Misi Utama, Kontrol Dasar, & Taktik Stealth/Peluit (otomatis tampil di awal game).
2. Tab 2: Panduan seluruh tab Inspektor (NavRail) & shortcut visualisasi pohon AI.
3. Tab 3: Ringkasan Metode AI (Materi 01-08) lengkap dengan lokasi fitur di dalam game.
"""

from typing import Dict, List, Tuple, Any
import pygame
from ..core import config
from .components import draw_card, draw_badge_pill

MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1025)
MOUSEWHEEL = getattr(pygame, "MOUSEWHEEL", 1027)
KEYDOWN = getattr(pygame, "KEYDOWN", 768)
K_ESCAPE = getattr(pygame, "K_ESCAPE", 27)
K_RETURN = getattr(pygame, "K_RETURN", 13)
K_KP_ENTER = getattr(pygame, "K_KP_ENTER", 1073741912)
K_SPACE = getattr(pygame, "K_SPACE", 32)
K_h = getattr(pygame, "K_h", 104)
K_1 = getattr(pygame, "K_1", 49)
K_2 = getattr(pygame, "K_2", 50)
K_3 = getattr(pygame, "K_3", 51)
SRCALPHA = getattr(pygame, "SRCALPHA", 0x00010000)

# Palet Cozy Warm Parchment
COLOR_BACKDROP = (25, 20, 15, 165)
COLOR_MODAL_BG = (248, 244, 235)
COLOR_MODAL_BORDER = (208, 192, 172)
COLOR_HEADER_BG = (238, 231, 218)
COLOR_HEADER_LINE = (208, 192, 172)
COLOR_BODY_BG = (250, 246, 238)
COLOR_CARD_BG = (255, 255, 255)
COLOR_CARD_BORDER = (218, 206, 188)

COLOR_HEADING = (145, 72, 18)
COLOR_TEXT = (38, 30, 24)
COLOR_TEXT_SUB = (115, 98, 82)
COLOR_BLUE = (40, 118, 198)
COLOR_GREEN = (38, 128, 58)
COLOR_GOLD = (185, 108, 20)
COLOR_PURPLE = (135, 62, 165)

COLOR_BTN_BG = (242, 235, 222)
COLOR_BTN_HOVER = (255, 252, 245)
COLOR_BTN_ACTIVE = (205, 135, 25)


def _wrap_text(font: pygame.font.Font, text: str, max_w: int) -> List[str]:
    """Memecah kalimat panjang ke baris-baris yang pas di lebar kartu."""
    if not text or max_w <= 12:
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


class GuideModal:
    """Modal Buku Panduan 3-Tab & Briefing Awal Permainan."""

    def __init__(self, fonts: Dict[str, pygame.font.Font]):
        self.fonts = fonts
        self.is_open: bool = False
        self.welcome_mode: bool = False
        self.active_tab: int = 0  # 0: Misi & Kontrol, 1: Tab Inspektor, 2: Metode AI
        self.scroll_y: float = 0.0
        self.max_scroll: float = 0.0

        self.rect_modal = pygame.Rect(0, 0, 1080, 680)
        self.rect_body = pygame.Rect(0, 0, 1040, 500)
        self.btn_close = pygame.Rect(0, 0, 34, 34)
        self.btn_start = pygame.Rect(0, 0, 220, 38)
        self.btn_to_tabs = pygame.Rect(0, 0, 220, 38)
        self.tab_rects: List[pygame.Rect] = [pygame.Rect(0, 0, 0, 0) for _ in range(3)]

    def open(self, tab_idx: int = 0) -> None:
        self.is_open = True
        self.welcome_mode = False
        self.active_tab = max(0, min(2, tab_idx))
        self.scroll_y = 0.0

    def open_welcome(self) -> None:
        self.is_open = True
        self.welcome_mode = True
        self.active_tab = 0
        self.scroll_y = 0.0

    def close(self) -> None:
        self.is_open = False
        self.welcome_mode = False

    def toggle(self) -> None:
        if self.is_open:
            self.close()
        else:
            self.open(self.active_tab)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.is_open:
            return False

        if event.type == KEYDOWN:
            if event.key in (K_ESCAPE, K_h):
                self.close()
                return True
            if event.key in (K_RETURN, K_KP_ENTER, K_SPACE) and self.active_tab == 0:
                self.close()
                return True
            if event.key == K_1:
                self.active_tab = 0
                self.scroll_y = 0.0
                return True
            if event.key == K_2:
                self.active_tab = 1
                self.scroll_y = 0.0
                return True
            if event.key == K_3:
                self.active_tab = 2
                self.scroll_y = 0.0
                return True
            return True

        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_close.collidepoint(event.pos):
                self.close()
                return True
            if self.btn_start.collidepoint(event.pos):
                self.close()
                return True
            if self.active_tab == 0 and self.btn_to_tabs.collidepoint(event.pos):
                self.active_tab = 1
                self.scroll_y = 0.0
                return True
            for idx, tr in enumerate(self.tab_rects):
                if tr.collidepoint(event.pos):
                    self.active_tab = idx
                    self.scroll_y = 0.0
                    return True
            if not self.rect_modal.collidepoint(event.pos):
                self.close()
                return True
            return True

        if event.type == MOUSEWHEEL:
            if self.rect_body.collidepoint(pygame.mouse.get_pos()):
                self.scroll_y = max(0.0, min(self.max_scroll, self.scroll_y - event.y * 28.0))
            return True

        return True

    def _compute_card_height(self, card_w: int, bullets: List[Tuple[str, Tuple[int, int, int]]],
                             font_sm: pygame.font.Font, font_tiny: pygame.font.Font) -> Tuple[int, List[Tuple[str, Tuple[int, int, int]]]]:
        inner_w = card_w - 24
        wrapped: List[Tuple[str, Tuple[int, int, int]]] = []
        for txt, col in bullets:
            for ln in _wrap_text(font_tiny, txt, inner_w):
                wrapped.append((ln, col))
        line_h = font_tiny.get_height() + 4
        h = 40 + max(1, len(wrapped)) * line_h + 10
        return h, wrapped

    def _draw_info_card(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        title: str,
        badge: str,
        accent_col: Tuple[int, int, int],
        badge_bg: Tuple[int, int, int],
        wrapped_lines: List[Tuple[str, Tuple[int, int, int]]],
        font_sm: pygame.font.Font,
        font_tiny: pygame.font.Font,
    ) -> None:
        draw_card(surface, rect, COLOR_CARD_BG, border_color=COLOR_CARD_BORDER, border_radius=8)
        hdr = pygame.Rect(rect.x + 1, rect.y + 1, rect.width - 2, 30)
        pygame.draw.rect(surface, COLOR_HEADER_BG, hdr, border_top_left_radius=7, border_top_right_radius=7)
        pygame.draw.line(surface, COLOR_CARD_BORDER, (rect.x, rect.y + 31), (rect.right, rect.y + 31), 1)
        pygame.draw.rect(surface, accent_col, pygame.Rect(rect.x + 5, rect.y + 7, 4, 18), border_radius=2)

        surface.blit(font_sm.render(title, True, COLOR_TEXT), (rect.x + 15, rect.y + 7))
        if badge:
            pw = max(62, font_tiny.size(badge)[0] + 16)
            pill_r = pygame.Rect(rect.right - pw - 8, rect.y + 5, pw, 20)
            draw_badge_pill(surface, pill_r, badge, badge_bg, accent_col, font_tiny, border_color=accent_col)

        line_h = font_tiny.get_height() + 4
        cy = rect.y + 38
        for ln, col in wrapped_lines:
            surface.blit(font_tiny.render(ln, True, col), (rect.x + 12, cy))
            cy += line_h

    def draw(self, surface: pygame.Surface) -> None:
        if not self.is_open:
            return

        sw, sh = surface.get_size()
        font_tiny = self.fonts.get("tiny", pygame.font.Font(None, 13))
        font_sm = self.fonts.get("sm", pygame.font.Font(None, 15))
        font_bubble = self.fonts.get("bubble", font_sm)
        font_title = self.fonts.get("title", font_sm)

        # 1. Backdrop redup hangat
        backdrop = pygame.Surface((sw, sh), SRCALPHA)
        backdrop.fill(COLOR_BACKDROP)
        surface.blit(backdrop, (0, 0))

        # 2. Kontainer Modal Utama
        mw = min(1100, int(sw * 0.90))
        mh = min(700, int(sh * 0.88))
        mx = (sw - mw) // 2
        my = (sh - mh) // 2
        self.rect_modal = pygame.Rect(mx, my, mw, mh)

        pygame.draw.rect(surface, COLOR_MODAL_BG, self.rect_modal, border_radius=12)
        pygame.draw.rect(surface, COLOR_MODAL_BORDER, self.rect_modal, 2, border_radius=12)

        # 3. Header Bar
        hdr_h = 60
        pygame.draw.rect(surface, COLOR_HEADER_BG, (mx, my, mw, hdr_h), border_top_left_radius=12, border_top_right_radius=12)
        pygame.draw.line(surface, COLOR_HEADER_LINE, (mx, my + hdr_h), (mx + mw, my + hdr_h), 1)

        title_str = "SELAMAT DATANG DI BAKEKOK — MISI & PANDUAN" if self.welcome_mode else "BUKU PANDUAN PETUALANG & INSPEKTOR AI"
        sub_str = "Baca alur misi, kontrol dasar, fungsi tab sebelah kiri, serta ringkasan metode AI"
        surface.blit(font_title.render(title_str, True, COLOR_HEADING), (mx + 20, my + 10))
        surface.blit(font_tiny.render(sub_str, True, COLOR_TEXT_SUB), (mx + 20, my + 36))

        mx_cur, my_cur = pygame.mouse.get_pos()
        self.btn_close = pygame.Rect(mx + mw - 48, my + 13, 34, 34)
        hov_close = self.btn_close.collidepoint((mx_cur, my_cur))
        pygame.draw.rect(surface, (212, 70, 62) if hov_close else (190, 56, 50), self.btn_close, border_radius=6)
        x_lbl = font_title.render("X", True, (255, 255, 255))
        surface.blit(x_lbl, x_lbl.get_rect(center=self.btn_close.center))

        # 4. Tab Switcher (3 Tab)
        tab_y = my + hdr_h + 10
        tab_h = 34
        tab_gap = 10
        tab_w = (mw - 40 - tab_gap * 2) // 3
        tab_labels = ["1. Misi & Cara Main", "2. Panduan Tab Inspektor", "3. Metode AI yang Dipakai"]
        for i, lbl in enumerate(tab_labels):
            tr = pygame.Rect(mx + 20 + i * (tab_w + tab_gap), tab_y, tab_w, tab_h)
            self.tab_rects[i] = tr
            is_act = (self.active_tab == i)
            is_hov = tr.collidepoint((mx_cur, my_cur))
            bg = COLOR_BTN_ACTIVE if is_act else (COLOR_BTN_HOVER if is_hov else COLOR_BTN_BG)
            fg = (255, 255, 255) if is_act else COLOR_TEXT
            pygame.draw.rect(surface, bg, tr, border_radius=7)
            if not is_act:
                pygame.draw.rect(surface, COLOR_MODAL_BORDER, tr, 1, border_radius=7)
            t_s = font_sm.render(lbl, True, fg)
            surface.blit(t_s, t_s.get_rect(center=tr.center))

        # 5. Area Konten Scrollable & Footer Bar
        footer_h = 58
        body_x = mx + 20
        body_y = tab_y + tab_h + 12
        body_w = mw - 40
        body_h = (my + mh - footer_h) - body_y - 8
        self.rect_body = pygame.Rect(body_x, body_y, body_w, body_h)

        pygame.draw.rect(surface, COLOR_BODY_BG, self.rect_body, border_radius=8)
        pygame.draw.rect(surface, COLOR_CARD_BORDER, self.rect_body, 1, border_radius=8)

        draw_items = self._build_tab_cards(body_x + 12, body_y + 12, body_w - 28, font_bubble, font_sm, font_tiny)
        content_bottom = max((r.bottom for (r, _) in draw_items), default=body_y + 20)
        total_h = content_bottom - body_y + 12
        self.max_scroll = max(0.0, float(total_h - body_h))
        self.scroll_y = max(0.0, min(self.max_scroll, self.scroll_y))
        scroll_off = int(self.scroll_y)

        old_clip = surface.get_clip()
        surface.set_clip(self.rect_body)
        for rect_item, draw_fn in draw_items:
            shifted = rect_item.move(0, -scroll_off)
            if shifted.bottom >= self.rect_body.y and shifted.y <= self.rect_body.bottom:
                draw_fn(surface, shifted)
        surface.set_clip(old_clip)

        if self.max_scroll > 0:
            track = pygame.Rect(self.rect_body.right - 8, self.rect_body.y + 6, 4, self.rect_body.height - 12)
            pygame.draw.rect(surface, (230, 222, 210), track, border_radius=2)
            ratio = body_h / float(max(1, total_h))
            thumb_h = max(24, int(track.height * ratio))
            thumb_y = track.y + int((track.height - thumb_h) * (self.scroll_y / self.max_scroll))
            pygame.draw.rect(surface, (185, 165, 140), (track.x, thumb_y, 4, thumb_h), border_radius=2)

        # 6. Footer Bar (Tombol Aksi Bawah)
        footer_y = my + mh - footer_h
        pygame.draw.line(surface, COLOR_HEADER_LINE, (mx + 16, footer_y), (mx + mw - 16, footer_y), 1)
        hint = "Tekan [H] kapan saja untuk membuka Buku Panduan ini  |  [1][2][3] Ganti Tab"
        surface.blit(font_tiny.render(hint, True, COLOR_TEXT_SUB), (mx + 22, footer_y + 20))

        btn_w = 215
        self.btn_start = pygame.Rect(mx + mw - btn_w - 20, footer_y + 10, btn_w, 38)
        hov_start = self.btn_start.collidepoint((mx_cur, my_cur))
        pygame.draw.rect(surface, (52, 152, 74) if hov_start else COLOR_GREEN, self.btn_start, border_radius=8)
        start_lbl = font_sm.render("[ENTER] Mulai Petualangan!" if self.welcome_mode else "[ESC] Tutup Panduan", True, (255, 255, 255))
        surface.blit(start_lbl, start_lbl.get_rect(center=self.btn_start.center))

        if self.active_tab == 0:
            self.btn_to_tabs = pygame.Rect(self.btn_start.x - 210, footer_y + 10, 198, 38)
            hov_t = self.btn_to_tabs.collidepoint((mx_cur, my_cur))
            pygame.draw.rect(surface, COLOR_BTN_HOVER if hov_t else COLOR_BTN_BG, self.btn_to_tabs, border_radius=8)
            pygame.draw.rect(surface, COLOR_MODAL_BORDER, self.btn_to_tabs, 1, border_radius=8)
            tl = font_sm.render("Lihat Panduan Tab ->", True, COLOR_TEXT)
            surface.blit(tl, tl.get_rect(center=self.btn_to_tabs.center))
        else:
            self.btn_to_tabs = pygame.Rect(0, 0, 0, 0)

    def _build_tab_cards(
        self, x0: int, y0: int, w: int,
        font_bubble: pygame.font.Font, font_sm: pygame.font.Font, font_tiny: pygame.font.Font
    ) -> List[Tuple[pygame.Rect, Any]]:
        items: List[Tuple[pygame.Rect, Any]] = []
        gap = 12
        cy = y0

        def add_grid_rows(specs: List[Tuple[str, str, Tuple[int, int, int], Tuple[int, int, int], List[Tuple[str, Tuple[int, int, int]]]]], cols: int):
            nonlocal cy
            col_w = (w - gap * (cols - 1)) // cols
            for i in range(0, len(specs), cols):
                row = specs[i:i + cols]
                computed = []
                max_h = 0
                for (title, badge, ac, bbg, bullets) in row:
                    h, wr = self._compute_card_height(col_w, bullets, font_sm, font_tiny)
                    max_h = max(max_h, h)
                    computed.append((title, badge, ac, bbg, wr))
                for j, (title, badge, ac, bbg, wr) in enumerate(computed):
                    rc = pygame.Rect(x0 + j * (col_w + gap), cy, col_w, max_h)
                    items.append((
                        rc,
                        lambda s, r, t=title, b=badge, a=ac, bg=bbg, w_l=wr: self._draw_info_card(
                            s, r, t, b, a, bg, w_l, font_sm, font_tiny
                        ),
                    ))
                cy += max_h + gap

        if self.active_tab == 0:
            # Banner Tujuan Utama (Full width)
            hero_bullets = [
                ("1. Jelajahi pulau untuk membuka 3 Peti Harta (Kiri Atas, Kiri Bawah, Kanan Bawah) dan dapatkan 3 Kunci Rune.", COLOR_TEXT),
                ("2. Hindari atau kalahkan para penjaga (Shiro, Oyen, Kuro) — setiap peti yang dibuka memberi buff perlengkapan bertarung.", COLOR_BLUE),
                ("3. Setelah 3 Kunci Rune terkumpul, pergi ke gerbang Menara Kuno di timur laut lalu tekan [E] untuk menantang Boss Kage!", COLOR_GREEN),
            ]
            h_hero, wr_hero = self._compute_card_height(w, hero_bullets, font_sm, font_tiny)
            rc_hero = pygame.Rect(x0, cy, w, h_hero)
            items.append((
                rc_hero,
                lambda s, r, w_l=wr_hero: self._draw_info_card(
                    s, r, "TUJUAN UTAMA PETUALANGAN", "3 KUNCI -> BOSS", COLOR_GOLD, (252, 243, 218), w_l, font_sm, font_tiny
                ),
            ))
            cy += h_hero + gap

            # Grid 3 Kolom: Cara Bermain, Stealth & Peluit, Kontrol Penting
            row_specs = [
                ("Kontrol Eksplorasi", "PETA", COLOR_BLUE, (235, 245, 255), [
                    ("• W A S D / Panah: Gerakkan Bolu", COLOR_TEXT),
                    ("• E: Buka Peti / Masuk Menara Kuno", COLOR_TEXT),
                    ("• SPASI: Tiup Peluit (pancing NPC 12 ubin)", COLOR_BLUE),
                    ("• TAB: Buka / tutup panel Inspektor AI", COLOR_TEXT_SUB),
                    ("• Scroll / +/-: Zoom kamera peta", COLOR_TEXT_SUB),
                ]),
                ("Taktik Stealth & Peluit", "TIPS", COLOR_GREEN, (232, 248, 236), [
                    ("• Masuk ke ubin semak-semak untuk bersembunyi (NPC kehilangan jejak jika tidak menempel).", COLOR_TEXT),
                    ("• Tiup peluit [SPASI] dari jarak aman untuk menarik NPC menjauh dari peti!", COLOR_GREEN),
                    ("• Saat peti dibuka, penjaga sektor itu langsung menyergap selama beberapa detik sebelum kembali waspada.", COLOR_TEXT_SUB),
                ]),
                ("Kontrol Pre-Battle & Duel", "DUEL", COLOR_PURPLE, (248, 235, 252), [
                    ("• R (Pre-Battle): Acak ulang skuad lawan", COLOR_TEXT),
                    ("• T (Pre-Battle): Buka Pohon CSP & Local Search", COLOR_PURPLE),
                    ("• SPASI (Pre-Battle): Mulai pertarungan", COLOR_TEXT),
                    ("• 1 / 2 / 3 / 4 (Duel): Serang, Heavy, Bertahan, Potion", COLOR_TEXT_SUB),
                    ("• H / K / P: Buka Panduan / Pohon Logic / Pohon PDDL", COLOR_TEXT_SUB),
                ]),
            ]
            add_grid_rows(row_specs, cols=3)

        elif self.active_tab == 1:
            tab_specs = [
                ("Tab 1: Hero Companion (*)", "GAME", COLOR_GOLD, (252, 243, 218), [
                    ("• Memantau HP Bolu, jumlah Kunci Rune (0/3), Peti Terbuka, serta isi Tas Inventaris.", COLOR_TEXT),
                    ("• Tersedia tombol cepat Panggil NPC [SPACE].", COLOR_TEXT_SUB),
                ]),
                ("Tab 2: Search (Pathfinding)", "MATERI 01-03", COLOR_BLUE, (235, 245, 255), [
                    ("• Pilih algoritma UCS atau A* (Manhattan, Euclidean, Chebyshev) serta Target NPC Fokus (Auto / Oyen / Kuro / Shiro).", COLOR_TEXT),
                    ("• Menampilkan jalur biru, area ekspansi kuning, Total Bobot medan, dan penghematan simpul vs UCS.", COLOR_TEXT_SUB),
                ]),
                ("Tab 3: Minimax (Duel AI)", "MATERI 04", COLOR_PURPLE, (248, 235, 252), [
                    ("• Aktif saat duel: ubah algoritma (Minimax, Alpha-Beta Pruning, Expectimax), Depth (2-6), Evaluasi, & Move Ordering.", COLOR_TEXT),
                    ("• Tekan tombol Pohon Keputusan untuk melihat cabang MAX/MIN/CHANCE & pemangkasan.", COLOR_TEXT_SUB),
                ]),
                ("Tab 4: CSP & Local Search", "MATERI 05-06", COLOR_GREEN, (232, 248, 236), [
                    ("• Memilih optimizer Local Search (Hill Climbing, Sideways, Random Restart, SA, GA) & slider Target Difficulty.", COLOR_TEXT),
                    ("• Memvalidasi aturan legalitas tim C1-C8 & tombol Visualizer [T] animasi langkah CSP.", COLOR_TEXT_SUB),
                ]),
                ("Tab 5: Logic KB (TELL -> ASK)", "MATERI 07", COLOR_GOLD, (252, 243, 218), [
                    ("• Menampilkan kejadian sensorik (Percept) saat peti dibuka, fakta FOL/CNF aktif, & pembagian tugas Chaser/Guardian.", COLOR_TEXT),
                    ("• Klik tombol / tekan [K] untuk melihat Pohon Resolusi Refutasi [].", COLOR_TEXT_SUB),
                ]),
                ("Tab 6: Planning (PDDL)", "MATERI 08", COLOR_BLUE, (235, 245, 255), [
                    ("• Memilih mesin perencana (Forward Progression A* vs Backward Regression STRIPS) untuk taktik pulau & rotasi duel.", COLOR_TEXT),
                    ("• Klik tombol / tekan [P] untuk inspeksi aksi STRIPS, Preconditions, Effects, dan State Fluents.", COLOR_TEXT_SUB),
                ]),
                ("Tab 7: Settings & ? Panduan", "KONTROL", COLOR_TEXT_SUB, (240, 235, 224), [
                    ("• Settings (gir di pojok kiri bawah): mengatur volume musik latar (BGM) & melihat informasi proyek.", COLOR_TEXT),
                    ("• Tombol (?) di NavRail kiri atau [H] membuka Buku Panduan ini kapan saja.", COLOR_TEXT_SUB),
                ]),
                ("Pintasan Visualizer Pohon", "SHORTCUT", COLOR_PURPLE, (248, 235, 252), [
                    ("• [T] di Pre-Battle -> Visualizer Pohon Backtracking CSP & Grafik Local Search.", COLOR_TEXT),
                    ("• [K] -> Pohon Resolusi Refutasi Logic KB.", COLOR_TEXT),
                    ("• [P] -> Pohon Perencanaan PDDL STRIPS (klik simpul untuk detail).", COLOR_TEXT),
                ]),
            ]
            add_grid_rows(tab_specs, cols=2)

        else:
            ai_specs = [
                ("Materi 01-03: Search & Pathfinding", "PETA & KEJAR", COLOR_BLUE, (235, 245, 255), [
                    ("• Metode: Uniform Cost Search (UCS) & A* (Manhattan, Euclidean, Chebyshev).", COLOR_TEXT),
                    ("• Implementasi: Patroli dan pengejaran Oyen, Kuro, dan Shiro dengan bobot medan Jalan Tanah (1.0) vs Rumput (2.0).", COLOR_TEXT_SUB),
                ]),
                ("Materi 04: Adversarial Search", "ARENA DUEL", COLOR_PURPLE, (248, 235, 252), [
                    ("• Metode: Minimax, Alpha-Beta Pruning (+ Move Ordering), dan Expectimax (Chance Node).", COLOR_TEXT),
                    ("• Implementasi: AI petarung lawan memilih Attack, Heavy Attack, Defend, atau Potion secara optimal tiap giliran.", COLOR_TEXT_SUB),
                ]),
                ("Materi 05: Local Search", "OPTIMASI TIM", COLOR_GOLD, (252, 243, 218), [
                    ("• Metode: Hill Climbing, Sideways Move, Random Restart, Simulated Annealing, & Genetic Algorithm.", COLOR_TEXT),
                    ("• Implementasi: Menyeimbangkan skor kesulitan skuad lawan mendekati Target Difficulty ('Fun Zone').", COLOR_TEXT_SUB),
                ]),
                ("Materi 06: Constraint Satisfaction (CSP)", "ATURAN C1-C8", COLOR_GREEN, (232, 248, 236), [
                    ("• Metode: Backtracking Search dengan MRV, LCV, Forward Checking, & AC-3.", COLOR_TEXT),
                    ("• Implementasi: Menjamin komposisi kelas, HP, ATK, DEF, & Potion skuad legal sesuai 8 batasan keras C1-C8.", COLOR_TEXT_SUB),
                ]),
                ("Materi 07: Logical Agents & KB", "KOORDINASI & SEGEL", COLOR_GOLD, (252, 243, 218), [
                    ("• Metode: Propositional CNF & Resolution Refutation (TELL -> ASK -> bukti kontradiksi []).", COLOR_TEXT),
                    ("• Implementasi: Menentukan penjaga pengejar saat peti dibuka & memverifikasi syarat 3 Kunci Rune Portal Menara Kuno.", COLOR_TEXT_SUB),
                ]),
                ("Materi 08: Classical Planning (PDDL)", "TAKTIK STRIPS", COLOR_BLUE, (235, 245, 255), [
                    ("• Metode: Forward State-Space Progression (A*) & Backward Regression STRIPS.", COLOR_TEXT),
                    ("• Implementasi: Rencana pengamanan pulau saat peti dicuri & rotasi darurat tim (SwapRetreat -> CastDefend -> HealTeammate) saat HP kritis.", COLOR_TEXT_SUB),
                ]),
            ]
            add_grid_rows(ai_specs, cols=2)

        return items
