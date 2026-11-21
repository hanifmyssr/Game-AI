"""GuideModal: Panduan Awal (Mission Briefing) & Buku Panduan 3-Tab (Cozy Warm Parchment).

Menyajikan panduan dengan tampilan ringkas di grid dan fitur Cue-Card Zoom saat kartu diklik:
1. Tab 1: Misi Utama, Kontrol Dasar, & Taktik Stealth/Peluit (otomatis tampil di awal game).
2. Tab 2: Panduan seluruh tab Inspektor (NavRail) & shortcut visualisasi pohon AI.
3. Tab 3: Ringkasan Metode AI (Materi 01-09) lengkap dengan lokasi fitur di dalam game.
"""

import math
import time
from typing import Dict, List, Tuple, Optional, TypedDict, Any
import pygame
from .components import draw_card, draw_badge_pill

MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1025)
MOUSEWHEEL = getattr(pygame, "MOUSEWHEEL", 1027)
KEYDOWN = getattr(pygame, "KEYDOWN", 768)
K_ESCAPE = getattr(pygame, "K_ESCAPE", 27)
K_RETURN = getattr(pygame, "K_RETURN", 13)
K_KP_ENTER = getattr(pygame, "K_KP_ENTER", 1073741912)
K_SPACE = getattr(pygame, "K_SPACE", 32)
K_LEFT = getattr(pygame, "K_LEFT", 1073741904)
K_RIGHT = getattr(pygame, "K_RIGHT", 1073741903)
K_h = getattr(pygame, "K_h", 104)
K_1 = getattr(pygame, "K_1", 49)
K_2 = getattr(pygame, "K_2", 50)
K_3 = getattr(pygame, "K_3", 51)
SRCALPHA = getattr(pygame, "SRCALPHA", 0x00010000)

# Palet Cozy Warm Parchment (harmonis, hangat, kontras nyaman di mata)
COLOR_BACKDROP = (25, 20, 15, 165)
COLOR_CUE_BACKDROP = (18, 14, 10, 155)
COLOR_MODAL_BG = (248, 244, 235)
COLOR_MODAL_BORDER = (206, 190, 168)
COLOR_HEADER_BG = (239, 232, 219)
COLOR_HEADER_LINE = (206, 190, 168)
COLOR_BODY_BG = (250, 246, 238)
COLOR_CARD_BG = (255, 253, 249)
COLOR_CARD_HOVER_BG = (255, 249, 238)
COLOR_CARD_BORDER = (216, 204, 186)
COLOR_CARD_SHADOW = (228, 220, 206)

COLOR_HEADING = (142, 70, 18)
COLOR_TEXT = (42, 34, 28)
COLOR_TEXT_SUB = (104, 90, 76)
COLOR_BLUE = (38, 108, 178)
COLOR_GREEN = (38, 122, 62)
COLOR_GOLD = (178, 102, 18)
COLOR_PURPLE = (126, 58, 156)

COLOR_BTN_BG = (242, 235, 222)
COLOR_BTN_HOVER = (255, 252, 245)
COLOR_BTN_ACTIVE = (202, 132, 24)

READABLE_FONT_FAMILIES = ["segoeui", "arial", "calibri", "dejavusans", "liberationsans"]


class _CardSpec(TypedDict):
    title: str
    badge: str
    accent: Tuple[int, int, int]
    badge_bg: Tuple[int, int, int]
    summary: str
    bullets: List[Tuple[str, Tuple[int, int, int]]]
    full_width: bool


def _wrap_text(font: pygame.font.Font, text: str, max_w: int) -> List[str]:
    """Memecah kalimat panjang ke baris-baris yang pas di lebar kartu."""
    if not text or max_w <= 16:
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
    """Modal Buku Panduan 3-Tab dengan kartu grid ringkas & Cue-Card Zoom."""

    def __init__(self, fonts: Dict[str, pygame.font.Font], audio: Optional[Any] = None):
        self.fonts = fonts
        self.audio = audio
        self.is_open: bool = False
        self.welcome_mode: bool = False
        self.active_tab: int = 0  # 0: Misi & Kontrol, 1: Tab Inspektor, 2: Metode AI
        self.scroll_y: float = 0.0
        self.max_scroll: float = 0.0
        self.zoomed_card_idx: Optional[int] = None

        # Animasi pertukaran Cue Card & cache tumpukan kartu belakang
        self._anim_start: float = 0.0
        self._anim_duration: float = 0.24
        self._anim_dir: int = 1
        self._anim_prev_idx: Optional[int] = None
        self._stack_cache: Dict[Tuple[int, int], List[Tuple[pygame.Surface, int, int]]] = {}

        self.rect_modal = pygame.Rect(0, 0, 1080, 680)
        self.rect_body = pygame.Rect(0, 0, 1040, 500)
        self.btn_close = pygame.Rect(0, 0, 34, 34)
        self.btn_start = pygame.Rect(0, 0, 220, 38)
        self.btn_to_tabs = pygame.Rect(0, 0, 220, 38)
        self.tab_rects: List[pygame.Rect] = [pygame.Rect(0, 0, 0, 0) for _ in range(3)]

        # Hitbox kartu grid & kontrol Cue Card
        self._card_hitboxes: List[Tuple[pygame.Rect, int]] = []
        self.rect_cue = pygame.Rect(0, 0, 740, 420)
        self.btn_cue_close = pygame.Rect(0, 0, 32, 32)
        self.btn_cue_prev = pygame.Rect(0, 0, 130, 34)
        self.btn_cue_next = pygame.Rect(0, 0, 148, 34)
        self.btn_cue_done = pygame.Rect(0, 0, 96, 34)
        self.btn_cue_tab_prev = pygame.Rect(0, 0, 86, 24)
        self.btn_cue_tab_next = pygame.Rect(0, 0, 86, 24)

        self._ui_fonts: Optional[Dict[str, pygame.font.Font]] = None

    def _get_ui_fonts(self) -> Dict[str, pygame.font.Font]:
        """Menyiapkan font sans-serif yang bersih dan mudah dibaca (di-cache sekali)."""
        if self._ui_fonts is not None:
            return self._ui_fonts

        fallback_tiny = self.fonts.get("tiny") or pygame.font.Font(None, 13)
        fallback_sm = self.fonts.get("sm") or pygame.font.Font(None, 15)
        fallback_title = self.fonts.get("title") or fallback_sm

        def make_font(size: int, bold: bool, fallback: pygame.font.Font) -> pygame.font.Font:
            try:
                return pygame.font.SysFont(READABLE_FONT_FAMILIES, size, bold=bold)
            except Exception:
                return fallback

        self._ui_fonts = {
            "card_title": make_font(15, True, fallback_sm),
            "card_summary": make_font(13, False, fallback_sm),
            "card_action": make_font(11, True, fallback_tiny),
            "cue_title": make_font(20, True, fallback_title),
            "cue_sub": make_font(13, False, fallback_sm),
            "cue_body": make_font(15, False, fallback_sm),
            "cue_pill": make_font(12, True, fallback_tiny),
            "modal_title": make_font(18, True, fallback_title),
            "modal_sub": make_font(12, False, fallback_tiny),
            "btn": make_font(13, True, fallback_sm),
        }
        return self._ui_fonts

    def open(self, tab_idx: int = 0) -> None:
        self.is_open = True
        self.welcome_mode = False
        self.active_tab = max(0, min(2, tab_idx))
        self.scroll_y = 0.0
        self.zoomed_card_idx = None

    def open_welcome(self) -> None:
        self.is_open = True
        self.welcome_mode = True
        self.active_tab = 0
        self.scroll_y = 0.0
        self.zoomed_card_idx = None

    def close(self) -> None:
        self.is_open = False
        self.welcome_mode = False
        self.zoomed_card_idx = None

    def toggle(self) -> None:
        if self.is_open:
            self.close()
        else:
            self.open(self.active_tab)

    def _get_tab_specs(self) -> List[_CardSpec]:
        """Daftar kartu untuk tab yang sedang aktif (ringkas di grid, detail di cue card)."""
        if self.active_tab == 0:
            return [
                {
                    "title": "TUJUAN UTAMA PETUALANGAN",
                    "badge": "3 KUNCI -> BOSS",
                    "accent": COLOR_GOLD,
                    "badge_bg": (253, 243, 219),
                    "summary": "Kumpulkan 3 Kunci Rune dari peti harta di pulau, lalu hadapi Boss Kage di Portal Menara Kuno.",
                    "full_width": True,
                    "bullets": [
                        ("1. Jelajahi pulau untuk membuka 3 Peti Harta dan kumpulkan 3 Kunci Rune.", COLOR_TEXT),
                        ("2. Hindari atau kalahkan para penjaga (Shiro, Oyen, Kuro) — setiap peti & kemenangan duel memberi buff perlengkapan.", COLOR_BLUE),
                        ("3. Setelah 3 Kunci Rune terkumpul, datangi Portal Menara Kuno lalu tekan [E] untuk masuk Pre-Battle Boss & tantang Boss Kage!", COLOR_GREEN),
                    ],
                },
                {
                    "title": "Kontrol Eksplorasi",
                    "badge": "PETA",
                    "accent": COLOR_BLUE,
                    "badge_bg": (233, 243, 253),
                    "summary": "Gerak Bolu (WASD), interaksi peti/portal [E], peluit pemancing [SPASI], & inspeksi peta.",
                    "full_width": False,
                    "bullets": [
                        ("W A S D / Panah: Gerakkan karakter Bolu menjelajahi pulau.", COLOR_TEXT),
                        ("E: Buka Peti Harta atau masuk ke Portal Menara Kuno.", COLOR_TEXT),
                        ("SPASI: Tiup Peluit untuk memancing perhatian NPC hingga radius 12 ubin.", COLOR_BLUE),
                        ("Klik Peta: Inspeksi Pohon, Bangunan, Batu, atau jenis Terrain.", COLOR_TEXT_SUB),
                        ("TAB / Scroll: Buka-tutup Panel Inspektor & Zoom kamera peta.", COLOR_TEXT_SUB),
                    ],
                },
                {
                    "title": "Stealth, Jembatan & Panel",
                    "badge": "TIPS",
                    "accent": COLOR_GREEN,
                    "badge_bg": (232, 246, 236),
                    "summary": "Sembunyi di semak, waspadai 3 jembatan rawan saat hujan, & lebarkan panel inspektor.",
                    "full_width": False,
                    "bullets": [
                        ("Bersembunyi di Semak: Masuk ke ubin semak-semak agar tidak terdeteksi penjaga (aman kecuali jarak 1 ubin).", COLOR_TEXT),
                        ("Jembatan Saat Hujan (M9): Jembatan Atas, Kiri, & Bawah berisiko ambruk (hilang 1 item non-kunci); cek di Tab 7 atau memutar lewat Pulau Tengah.", COLOR_GREEN),
                        ("Panel Inspektor Fleksibel: Geser garis tepi kanan panel untuk memperlebar tab, dan klik [?] untuk glosarium istilah.", COLOR_TEXT_SUB),
                    ],
                },
                {
                    "title": "Kontrol Pre-Battle & Duel",
                    "badge": "DUEL",
                    "accent": COLOR_PURPLE,
                    "badge_bg": (246, 234, 251),
                    "summary": "Acak skuad [R], visualizer CSP [T], mulai duel [SPASI], pilih aksi [1-4], serta shortcut pohon AI.",
                    "full_width": False,
                    "bullets": [
                        ("R (Pre-Battle): Acak ulang komposisi skuad lawan via CSP & Local Search.", COLOR_TEXT),
                        ("T (Pre-Battle): Buka Visualizer animasi langkah Backtracking CSP.", COLOR_TEXT),
                        ("SPASI (Pre-Battle): Mulai pertarungan duel (termasuk melawan Boss Kage).", COLOR_TEXT),
                        ("1 / 2 / 3 / 4 (Duel): Serang, Heavy Attack, Bertahan, atau gunakan Potion.", COLOR_TEXT_SUB),
                        ("Akhir Duel: Pop-up Ulangi Duel [R] atau Keluar ke Pulau [ESC].", COLOR_PURPLE),
                        ("H / K / P: Buka Panduan / Pohon Resolusi Logic / Pohon Rencana PDDL.", COLOR_TEXT_SUB),
                    ],
                },
            ]

        if self.active_tab == 1:
            return [
                {
                    "title": "Tab 1: Hero Companion (*)",
                    "badge": "GAME",
                    "accent": COLOR_GOLD,
                    "badge_bg": (253, 243, 219),
                    "summary": "Pantau HP Bolu, Kunci Rune (0/3), Peti Terbuka, Tas Inventaris, dan tombol panggil NPC.",
                    "full_width": False,
                    "bullets": [
                        ("Status Hero: Memantau HP Bolu, jumlah Kunci Rune (0/3), dan progres Peti Terbuka.", COLOR_TEXT),
                        ("Tas Inventaris: Klik item di tas untuk membaca detail efek buff atau kegunaannya.", COLOR_TEXT),
                        ("Kontrol Cepat: Tersedia tombol geser < > untuk tas dan tombol Panggil NPC [SPACE].", COLOR_TEXT_SUB),
                    ],
                },
                {
                    "title": "Tab 2: Search (Pathfinding)",
                    "badge": "MATERI 01-03",
                    "accent": COLOR_BLUE,
                    "badge_bg": (233, 243, 253),
                    "summary": "Atur algoritma UCS atau A*, heuristik jarak, fokus NPC, dan lihat jalur + area ekspansi di peta.",
                    "full_width": False,
                    "bullets": [
                        ("Pilihan Algoritma: Bandingkan UCS dengan A* (Manhattan, Euclidean, atau Chebyshev).", COLOR_TEXT),
                        ("Fokus & Visual: Pilih Target NPC Fokus dan toggle Jalur di Peta (atau tekan Ctrl).", COLOR_TEXT),
                        ("Metrik Pencarian: Menampilkan jalur biru, ekspansi kuning, Total Bobot medan, & penghematan simpul vs UCS.", COLOR_TEXT_SUB),
                    ],
                },
                {
                    "title": "Tab 3: Minimax (Duel AI)",
                    "badge": "MATERI 04",
                    "accent": COLOR_PURPLE,
                    "badge_bg": (246, 234, 251),
                    "summary": "Konfigurasi Minimax, Alpha-Beta, Expectimax, kedalaman (Depth 1-8), dan Pohon Keputusan [T].",
                    "full_width": False,
                    "bullets": [
                        ("Mode Duel AI: Ubah algoritma (Minimax, Alpha-Beta, Expectimax), Depth (1-8), Evaluasi, & Move Ordering.", COLOR_TEXT),
                        ("Pohon Keputusan [T]: Lihat cabang simpul MAX, MIN, CHANCE, skor utilitas, dan jumlah pemangkasan (pruning).", COLOR_TEXT_SUB),
                    ],
                },
                {
                    "title": "Tab 4: CSP & Local Search",
                    "badge": "MATERI 05-06",
                    "accent": COLOR_GREEN,
                    "badge_bg": (232, 246, 236),
                    "summary": "Pilih 5 optimizer Local Search, atur Target Difficulty, acak skuad [R], & validasi aturan C1-C8.",
                    "full_width": False,
                    "bullets": [
                        ("Optimizer & Difficulty: Pilih 5 optimizer Local Search, geser Target Difficulty (Manual/Adaptif + tombol Auto), & Acak Ulang [R].", COLOR_TEXT),
                        ("Validasi & Visualizer: Memeriksa legalitas tim C1-C8 dan menyediakan Visualizer [T] untuk animasi langkah CSP.", COLOR_TEXT_SUB),
                    ],
                },
                {
                    "title": "Tab 5: Logic KB (TELL -> ASK)",
                    "badge": "MATERI 07",
                    "accent": COLOR_GOLD,
                    "badge_bg": (253, 243, 219),
                    "summary": "Pantau Percept sensorik, fakta FOL/CNF aktif, pembagian Chaser/Guardian, & Pohon Resolusi [K].",
                    "full_width": False,
                    "bullets": [
                        ("Knowledge Base Aktif: Menampilkan kejadian sensorik (Percept) saat peti dibuka, fakta FOL/CNF, & pembagian tugas penjaga.", COLOR_TEXT),
                        ("Pohon Resolusi [K]: Klik tombol atau tekan [K] untuk melihat pembuktian Resolution Refutation hingga Klausa Kosong.", COLOR_TEXT_SUB),
                    ],
                },
                {
                    "title": "Tab 6: Planning (PDDL)",
                    "badge": "MATERI 08",
                    "accent": COLOR_BLUE,
                    "badge_bg": (233, 243, 253),
                    "summary": "Bandingkan Forward Progression A* vs Backward Regression STRIPS untuk taktik pulau & rotasi duel.",
                    "full_width": False,
                    "bullets": [
                        ("Mode Perencanaan: Pilih Forward Progression A* atau Backward Regression STRIPS untuk taktik pulau & rotasi duel.", COLOR_TEXT),
                        ("Inspeksi STRIPS [P]: Klik tombol atau tekan [P] untuk memeriksa aksi, Preconditions, Effects, dan State Fluents.", COLOR_TEXT_SUB),
                    ],
                },
                {
                    "title": "Tab 7: Uncertainty (M9)",
                    "badge": "MATERI 09",
                    "accent": COLOR_GREEN,
                    "badge_bg": (232, 246, 236),
                    "summary": "Pilih Jembatan (Atas/Kiri/Bawah), Cek Jembatan (Bayes), Expected Cost, & kontrol cuaca hujan.",
                    "full_width": False,
                    "bullets": [
                        ("Pilih & Cek Jembatan: Pilih jembatan berisiko (Atas/Kiri/Bawah) lalu tekan Cek Jembatan untuk memperbarui Posterior P(Ambruk) & Entropi.", COLOR_TEXT),
                        ("Expected Cost & Cuaca: Bandingkan biaya jembatan berisiko vs memutar lewat Pulau Tengah (0% ambruk), atur Prior Hujan & Akurasi Sensor.", COLOR_TEXT_SUB),
                    ],
                },
                {
                    "title": "Tab 8: Settings, [?] & Panduan",
                    "badge": "KONTROL",
                    "accent": COLOR_TEXT_SUB,
                    "badge_bg": (239, 234, 224),
                    "summary": "Atur volume BGM/SFX, reset status peti/hero, serta akses glosarium [?] dan Buku Panduan [H].",
                    "full_width": False,
                    "bullets": [
                        ("Settings (ikon gir kiri bawah): Mengatur volume BGM/SFX dan tombol Reset Status Peti Harta & Hero.", COLOR_TEXT),
                        ("Glosarium & Panduan: Tombol [?] di header tiap tab membuka glosarium istilah; [H] membuka Buku Panduan ini.", COLOR_TEXT_SUB),
                    ],
                },
            ]

        return [
            {
                "title": "Materi 01-03: Search & Pathfinding",
                "badge": "PETA & KEJAR",
                "accent": COLOR_BLUE,
                "badge_bg": (233, 243, 253),
                "summary": "Uniform Cost Search (UCS) & A* (Manhattan, Euclidean, Chebyshev) untuk navigasi penjaga di pulau.",
                "full_width": False,
                "bullets": [
                    ("Metode: Uniform Cost Search (UCS) dan A* Search dengan 3 pilihan fungsi heuristik (Manhattan, Euclidean, Chebyshev).", COLOR_TEXT),
                    ("Implementasi: Patroli dan pengejaran Oyen, Kuro, dan Shiro dengan bobot medan Jalan Tanah (1.0) vs Rumput (2.0).", COLOR_TEXT_SUB),
                ],
            },
            {
                "title": "Materi 04: Adversarial Search",
                "badge": "ARENA DUEL",
                "accent": COLOR_PURPLE,
                "badge_bg": (246, 234, 251),
                "summary": "Minimax, Alpha-Beta Pruning (+ Move Ordering), dan Expectimax untuk keputusan duel tiap giliran.",
                "full_width": False,
                "bullets": [
                    ("Metode: Minimax, Alpha-Beta Pruning (+ Move Ordering), dan Expectimax (Chance Node untuk peluang kritikal/miss).", COLOR_TEXT),
                    ("Implementasi: AI petarung lawan memilih Attack, Heavy Attack, Defend, atau Potion secara optimal tiap giliran.", COLOR_TEXT_SUB),
                ],
            },
            {
                "title": "Materi 05: Local Search",
                "badge": "OPTIMASI TIM",
                "accent": COLOR_GOLD,
                "badge_bg": (253, 243, 219),
                "summary": "Hill Climbing, Sideways, Random Restart, Simulated Annealing, & Genetic Algorithm untuk 'Fun Zone'.",
                "full_width": False,
                "bullets": [
                    ("Metode: Hill Climbing, Sideways Move, Random Restart, Simulated Annealing, & Genetic Algorithm.", COLOR_TEXT),
                    ("Implementasi: Menyeimbangkan skor kesulitan skuad lawan mendekati Target Difficulty ('Fun Zone').", COLOR_TEXT_SUB),
                ],
            },
            {
                "title": "Materi 06: Constraint Satisfaction (CSP)",
                "badge": "ATURAN C1-C8",
                "accent": COLOR_GREEN,
                "badge_bg": (232, 246, 236),
                "summary": "Backtracking Search dengan MRV, LCV, Forward Checking, & AC-3 untuk validasi 8 aturan keras skuad.",
                "full_width": False,
                "bullets": [
                    ("Metode: Backtracking Search dengan MRV, LCV, Forward Checking, & AC-3.", COLOR_TEXT),
                    ("Implementasi: Menjamin komposisi kelas, HP, ATK, DEF, & Potion skuad legal sesuai 8 batasan keras C1-C8.", COLOR_TEXT_SUB),
                ],
            },
            {
                "title": "Materi 07: Logical Agents & KB",
                "badge": "KOORDINASI & SEGEL",
                "accent": COLOR_GOLD,
                "badge_bg": (253, 243, 219),
                "summary": "Propositional CNF & Resolution Refutation (TELL -> ASK) untuk koordinasi penjaga & segel portal.",
                "full_width": False,
                "bullets": [
                    ("Metode: Propositional CNF & Resolution Refutation (TELL -> ASK -> bukti kontradiksi Klausa Kosong).", COLOR_TEXT),
                    ("Implementasi: Menentukan penjaga pengejar saat peti dibuka & memverifikasi syarat 3 Kunci Rune Portal Menara Kuno.", COLOR_TEXT_SUB),
                ],
            },
            {
                "title": "Materi 08: Classical Planning (PDDL)",
                "badge": "TAKTIK STRIPS",
                "accent": COLOR_BLUE,
                "badge_bg": (233, 243, 253),
                "summary": "Forward Progression (A*) & Backward Regression STRIPS untuk taktik pulau dan rotasi darurat duel.",
                "full_width": False,
                "bullets": [
                    ("Metode: Forward State-Space Progression (A*) & Backward Regression STRIPS.", COLOR_TEXT),
                    ("Implementasi: Rencana pengamanan pulau saat peti dicuri & rotasi darurat tim (SwapRetreat -> CastDefend -> HealTeammate).", COLOR_TEXT_SUB),
                ],
            },
            {
                "title": "Materi 09: Decision Under Uncertainty",
                "badge": "JEMBATAN BAYES",
                "accent": COLOR_GREEN,
                "badge_bg": (232, 246, 236),
                "summary": "Bayesian Belief Update (Cek Jembatan), Entropi, & Expected Cost pada 3 jembatan antarpulau.",
                "full_width": False,
                "bullets": [
                    ("Metode: Hidden State (RAPUH/KOKOH), Bayes' Rule via Cek Jembatan, Shannon Entropy, & Expected Cost.", COLOR_TEXT),
                    ("Implementasi: Jembatan Atas, Kiri, & Bawah berisiko ambruk saat hujan (hilang 1 item non-kunci; Kunci Rune aman), sedangkan Pulau Tengah aman 0%.", COLOR_TEXT_SUB),
                ],
            },
        ]

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.is_open:
            return False

        specs = self._get_tab_specs()
        total_cards = len(specs)

        # Saat Cue Card sedang terbuka (zoomed)
        if self.zoomed_card_idx is not None:
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.zoomed_card_idx = None
                    self._anim_prev_idx = None
                    return True
                if event.key == K_h:
                    self.close()
                    return True
                if event.key == K_LEFT and total_cards > 0:
                    self._step_cue_prev()
                    return True
                if event.key == K_RIGHT and total_cards > 0:
                    self._step_cue_next(total_cards)
                    return True
                return True

            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                if self.btn_cue_close.collidepoint(event.pos) or self.btn_cue_done.collidepoint(event.pos):
                    self.zoomed_card_idx = None
                    self._anim_prev_idx = None
                    return True
                if self.btn_cue_tab_prev.collidepoint(event.pos) and self.active_tab > 0:
                    self._switch_cue_tab(self.active_tab - 1, -1)
                    return True
                if self.btn_cue_tab_next.collidepoint(event.pos) and self.active_tab < 2:
                    self._switch_cue_tab(self.active_tab + 1, 1)
                    return True
                if self.btn_cue_prev.collidepoint(event.pos) and total_cards > 0:
                    self._step_cue_prev()
                    return True
                if self.btn_cue_next.collidepoint(event.pos) and total_cards > 0:
                    self._step_cue_next(total_cards)
                    return True
                if not self.rect_cue.collidepoint(event.pos):
                    self.zoomed_card_idx = None
                    self._anim_prev_idx = None
                    return True
                return True

            return True

        # Mode Grid Normal
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
                self.zoomed_card_idx = None
                return True
            if event.key == K_2:
                self.active_tab = 1
                self.scroll_y = 0.0
                self.zoomed_card_idx = None
                return True
            if event.key == K_3:
                self.active_tab = 2
                self.scroll_y = 0.0
                self.zoomed_card_idx = None
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
                self.zoomed_card_idx = None
                return True
            for idx, tr in enumerate(self.tab_rects):
                if tr.collidepoint(event.pos):
                    self.active_tab = idx
                    self.scroll_y = 0.0
                    self.zoomed_card_idx = None
                    return True
            if self.rect_body.collidepoint(event.pos):
                for card_rect, card_idx in self._card_hitboxes:
                    if card_rect.collidepoint(event.pos):
                        self._open_cue_card(card_idx)
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

    def _compute_grid_card_height(
        self,
        card_w: int,
        summary: str,
        font_summary: pygame.font.Font,
        font_action: pygame.font.Font,
    ) -> Tuple[int, List[str]]:
        inner_w = card_w - 28
        wrapped = _wrap_text(font_summary, summary, inner_w)
        line_h = font_summary.get_height() + 4
        footer_h = font_action.get_height() + 10
        # 34px header + 10px top pad + wrapped lines + footer + 6px bottom pad
        h = 34 + 10 + max(1, len(wrapped)) * line_h + footer_h + 6
        return h, wrapped

    def _draw_grid_card(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        spec: _CardSpec,
        wrapped_summary: List[str],
        is_hovered: bool,
        ui_fonts: Dict[str, pygame.font.Font],
    ) -> None:
        accent = spec["accent"]
        card_bg = COLOR_CARD_HOVER_BG if is_hovered else COLOR_CARD_BG
        border_col = accent if is_hovered else COLOR_CARD_BORDER

        # Bayangan halus di bawah kartu agar terasa seperti cue card terangkat
        shadow_r = rect.move(0, 2)
        pygame.draw.rect(surface, COLOR_CARD_SHADOW, shadow_r, border_radius=9)

        draw_card(surface, rect, card_bg, border_color=border_col, border_radius=9)

        # Header kartu
        hdr = pygame.Rect(rect.x + 1, rect.y + 1, rect.width - 2, 34)
        pygame.draw.rect(surface, COLOR_HEADER_BG, hdr, border_top_left_radius=8, border_top_right_radius=8)
        pygame.draw.line(surface, COLOR_CARD_BORDER, (rect.x + 1, rect.y + 35), (rect.right - 1, rect.y + 35), 1)
        pygame.draw.rect(surface, accent, pygame.Rect(rect.x + 7, rect.y + 8, 4, 18), border_radius=2)

        f_title = ui_fonts["card_title"]
        f_summary = ui_fonts["card_summary"]
        f_action = ui_fonts["card_action"]

        badge = spec["badge"]
        pw = max(62, f_action.size(badge)[0] + 16) if badge else 0
        title_max_w = rect.width - 28 - (pw + 10 if badge else 0)
        title_str = spec["title"]
        while f_title.size(title_str)[0] > title_max_w and len(title_str) > 8:
            title_str = title_str[:-4].rstrip() + "..."
        surface.blit(f_title.render(title_str, True, COLOR_TEXT), (rect.x + 17, rect.y + 8))

        if badge:
            pill_r = pygame.Rect(rect.right - pw - 10, rect.y + 7, pw, 20)
            draw_badge_pill(surface, pill_r, badge, spec["badge_bg"], accent, f_action, border_color=accent)

        # Ringkasan singkat (mudah dipindai)
        line_h = f_summary.get_height() + 4
        cy = rect.y + 43
        for ln in wrapped_summary:
            surface.blit(f_summary.render(ln, True, COLOR_TEXT), (rect.x + 14, cy))
            cy += line_h

        # Micro-action di pojok kanan bawah kartu
        action_txt = "Klik untuk baca detail ->"
        action_col = accent if is_hovered else COLOR_TEXT_SUB
        act_surf = f_action.render(action_txt, True, action_col)
        surface.blit(act_surf, (rect.right - act_surf.get_width() - 14, rect.bottom - act_surf.get_height() - 8))

    def _play_card_sfx(self) -> None:
        """Memutar efek suara kartu saat Cue Card dibuka atau digeser."""
        if self.audio is not None and hasattr(self.audio, "play_card_reveal"):
            try:
                self.audio.play_card_reveal()
            except Exception:
                pass

    def _open_cue_card(self, card_idx: int) -> None:
        self.zoomed_card_idx = card_idx
        self._anim_prev_idx = None
        self._anim_dir = 1
        self._anim_start = time.perf_counter()
        self._play_card_sfx()

    def _switch_cue_card(self, new_idx: int, direction: int) -> None:
        if new_idx == self.zoomed_card_idx:
            return
        self._anim_prev_idx = self.zoomed_card_idx
        self.zoomed_card_idx = new_idx
        self._anim_dir = direction
        self._anim_start = time.perf_counter()
        self._play_card_sfx()

    def _switch_cue_tab(self, new_tab: int, direction: int) -> None:
        new_tab = max(0, min(2, new_tab))
        if new_tab == self.active_tab:
            return
        self.active_tab = new_tab
        self.scroll_y = 0.0
        self._anim_prev_idx = None
        self.zoomed_card_idx = 0
        self._anim_dir = direction
        self._anim_start = time.perf_counter()
        self._play_card_sfx()

    def _step_cue_prev(self) -> None:
        if self.zoomed_card_idx is None:
            return
        if self.zoomed_card_idx > 0:
            self._switch_cue_card(self.zoomed_card_idx - 1, -1)

    def _step_cue_next(self, total_cards: int) -> None:
        if self.zoomed_card_idx is None:
            return
        if self.zoomed_card_idx < total_cards - 1:
            self._switch_cue_card(self.zoomed_card_idx + 1, 1)
        elif self.active_tab < 2:
            self._switch_cue_tab(self.active_tab + 1, 1)

    def _get_cue_stack_layers(self, cw: int, ch: int) -> List[Tuple[pygame.Surface, int, int]]:
        """Membuat & men-cache 2 kartu tumpukan belakang (miring halus) untuk efek flashcard deck."""
        key = (cw, ch)
        if key in self._stack_cache:
            return self._stack_cache[key]

        layers: List[Tuple[pygame.Surface, int, int]] = []
        configs = [
            (-2.4, (232, 224, 209), (192, 178, 158), -6, 10),
            (1.9, (243, 237, 224), (204, 190, 170), 6, 5),
        ]
        for angle, bg_col, border_col, off_x, off_y in configs:
            base = pygame.Surface((cw, ch), SRCALPHA)
            pygame.draw.rect(base, bg_col, pygame.Rect(0, 0, cw, ch), border_radius=14)
            pygame.draw.rect(base, border_col, pygame.Rect(0, 0, cw, ch), 2, border_radius=14)
            try:
                rot = pygame.transform.rotozoom(base, angle, 1.0)
            except Exception:
                rot = base
            layers.append((rot, off_x, off_y))

        self._stack_cache[key] = layers
        return layers

    def _render_cue_card_surface(
        self,
        cw: int,
        ch: int,
        idx: int,
        total_cards: int,
        spec: _CardSpec,
        ui_fonts: Dict[str, pygame.font.Font],
        mx_cur: int,
        my_cur: int,
        card_top_left: Tuple[int, int],
        update_hitboxes: bool,
    ) -> pygame.Surface:
        """Merender satu Cue Card berukuran seragam (cw x ch) ke surface tersendiri."""
        card_surf = pygame.Surface((cw, ch), SRCALPHA)
        accent = spec["accent"]

        f_title = ui_fonts["cue_title"]
        f_sub = ui_fonts["cue_sub"]
        f_body = ui_fonts["cue_body"]
        f_pill = ui_fonts["cue_pill"]
        f_btn = ui_fonts["btn"]

        pad_x = 28
        inner_w = cw - pad_x * 2 - 18
        sub_lines = _wrap_text(f_sub, spec["summary"], cw - pad_x * 2)
        sub_line_h = f_sub.get_height() + 4
        hdr_h = 62 + len(sub_lines) * sub_line_h + 12
        footer_h = 56

        # Badan kartu utama
        pygame.draw.rect(card_surf, COLOR_CARD_BG, pygame.Rect(0, 0, cw, ch), border_radius=14)
        pygame.draw.rect(card_surf, accent, pygame.Rect(0, 0, cw, ch), 2, border_radius=14)

        # Header Cue Card
        hdr_rect = pygame.Rect(2, 2, cw - 4, hdr_h)
        pygame.draw.rect(card_surf, COLOR_HEADER_BG, hdr_rect, border_top_left_radius=12, border_top_right_radius=12)
        pygame.draw.rect(card_surf, accent, pygame.Rect(2, 2, cw - 4, 6), border_top_left_radius=12, border_top_right_radius=12)
        pygame.draw.line(card_surf, COLOR_CARD_BORDER, (2, hdr_h), (cw - 2, hdr_h), 1)

        # Badge & Nomor Kartu + Tombol Lompat Tab Sebelum/Sesudah
        pill_y = 16
        cur_x = pad_x
        if spec["badge"]:
            pw = max(72, f_pill.size(spec["badge"])[0] + 18)
            draw_badge_pill(card_surf, pygame.Rect(cur_x, pill_y, pw, 22), spec["badge"], spec["badge_bg"], accent, f_pill, border_color=accent)
            cur_x += pw + 8

        counter_txt = f"Tab {self.active_tab + 1} · Kartu {idx + 1} / {total_cards}"
        cnt_w = f_pill.size(counter_txt)[0] + 18
        draw_badge_pill(card_surf, pygame.Rect(cur_x, pill_y, cnt_w, 22), counter_txt, COLOR_CARD_BG, COLOR_TEXT_SUB, f_pill, border_color=COLOR_CARD_BORDER)

        # Tombol X Cue Card (posisi tetap!)
        cx0, cy0 = card_top_left
        local_close = pygame.Rect(cw - 46, 16, 30, 30)
        abs_close = local_close.move(cx0, cy0)
        if update_hitboxes:
            self.btn_cue_close = abs_close
        hov_c = abs_close.collidepoint((mx_cur, my_cur))
        pygame.draw.rect(card_surf, (212, 70, 62) if hov_c else (188, 62, 54), local_close, border_radius=6)
        x_s = f_btn.render("X", True, (255, 255, 255))
        card_surf.blit(x_s, x_s.get_rect(center=local_close.center))

        # Tombol Tab Sebelum & Tab Sesudah di sebelah kiri tombol X
        local_tab_next = pygame.Rect(local_close.x - 94, 15, 84, 24)
        local_tab_prev = pygame.Rect(local_tab_next.x - 90, 15, 84, 24)
        if update_hitboxes:
            self.btn_cue_tab_prev = local_tab_prev.move(cx0, cy0)
            self.btn_cue_tab_next = local_tab_next.move(cx0, cy0)

        tab_prev_enabled = self.active_tab > 0
        tab_next_enabled = self.active_tab < 2
        tab_prev_lbl = f"< Tab {self.active_tab}" if tab_prev_enabled else "< Tab -"
        tab_next_lbl = f"Tab {self.active_tab + 2} >" if tab_next_enabled else "Tab - >"

        for r_loc, lbl, enabled in (
            (local_tab_prev, tab_prev_lbl, tab_prev_enabled),
            (local_tab_next, tab_next_lbl, tab_next_enabled),
        ):
            hov_tb = enabled and r_loc.move(cx0, cy0).collidepoint((mx_cur, my_cur))
            bg_tb = (COLOR_BTN_HOVER if hov_tb else COLOR_CARD_BG) if enabled else (233, 227, 215)
            fg_tb = COLOR_TEXT if enabled else (168, 158, 146)
            bd_tb = COLOR_MODAL_BORDER if enabled else (214, 204, 188)
            pygame.draw.rect(card_surf, bg_tb, r_loc, border_radius=6)
            pygame.draw.rect(card_surf, bd_tb, r_loc, 1, border_radius=6)
            ts_tb = f_pill.render(lbl, True, fg_tb)
            card_surf.blit(ts_tb, ts_tb.get_rect(center=r_loc.center))

        # Judul & Ringkasan
        title_y = 44
        card_surf.blit(f_title.render(spec["title"], True, COLOR_HEADING), (pad_x, title_y))
        sub_y = title_y + f_title.get_height() + 4
        for sln in sub_lines:
            card_surf.blit(f_sub.render(sln, True, COLOR_TEXT_SUB), (pad_x, sub_y))
            sub_y += sub_line_h

        # Isi Detail Bullet (tetap rapi dalam tinggi seragam)
        body_line_h = f_body.get_height() + 6
        body_pad_y = 20
        bullet_gap = 10
        body_area = pygame.Rect(4, hdr_h + 2, cw - 8, ch - hdr_h - footer_h - 4)
        old_clip = card_surf.get_clip()
        card_surf.set_clip(body_area)
        by = hdr_h + body_pad_y
        for txt, col in spec["bullets"]:
            wlines = _wrap_text(f_body, txt, inner_w)
            if wlines:
                dot_y = by + f_body.get_height() // 2
                pygame.draw.circle(card_surf, accent if col == COLOR_TEXT else col, (pad_x + 5, dot_y), 4)
            for ln in wlines:
                card_surf.blit(f_body.render(ln, True, col), (pad_x + 18, by))
                by += body_line_h
            by += bullet_gap
        card_surf.set_clip(old_clip)

        # Footer Navigasi Cue Card (posisi tombol selalu tetap!)
        fy = ch - footer_h
        pygame.draw.rect(card_surf, COLOR_HEADER_BG, (2, fy, cw - 4, footer_h - 2), border_bottom_left_radius=12, border_bottom_right_radius=12)
        pygame.draw.line(card_surf, COLOR_CARD_BORDER, (2, fy), (cw - 2, fy), 1)

        local_prev = pygame.Rect(pad_x, fy + 11, 130, 34)
        local_next = pygame.Rect(local_prev.right + 10, fy + 11, 152, 34)
        local_done = pygame.Rect(cw - pad_x - 100, fy + 11, 100, 34)

        if update_hitboxes:
            self.btn_cue_prev = local_prev.move(cx0, cy0)
            self.btn_cue_next = local_next.move(cx0, cy0)
            self.btn_cue_done = local_done.move(cx0, cy0)

        # Tombol < Sebelumnya (non-aktif di kartu pertama)
        prev_enabled = idx > 0
        hov_prev = prev_enabled and local_prev.move(cx0, cy0).collidepoint((mx_cur, my_cur))
        bg_prev = (COLOR_BTN_HOVER if hov_prev else COLOR_CARD_BG) if prev_enabled else (233, 227, 215)
        bd_prev = COLOR_MODAL_BORDER if prev_enabled else (214, 204, 188)
        fg_prev = COLOR_TEXT if prev_enabled else (168, 158, 146)
        pygame.draw.rect(card_surf, bg_prev, local_prev, border_radius=7)
        pygame.draw.rect(card_surf, bd_prev, local_prev, 1, border_radius=7)
        ps = f_btn.render("< Sebelumnya", True, fg_prev)
        card_surf.blit(ps, ps.get_rect(center=local_prev.center))

        # Tombol Berikutnya > / Lanjut ke Tab X > (HIJAU saat aktif, non-aktif di kartu terakhir Tab 3)
        is_last_in_tab = (idx >= total_cards - 1)
        next_enabled = (not is_last_in_tab) or (self.active_tab < 2)
        if is_last_in_tab and self.active_tab < 2:
            next_lbl = f"Lanjut ke Tab {self.active_tab + 2} >"
        else:
            next_lbl = "Berikutnya >"

        hov_next = next_enabled and local_next.move(cx0, cy0).collidepoint((mx_cur, my_cur))
        if next_enabled:
            bg_next = (52, 152, 74) if hov_next else COLOR_GREEN
            fg_next = (255, 255, 255)
            pygame.draw.rect(card_surf, bg_next, local_next, border_radius=7)
        else:
            pygame.draw.rect(card_surf, (233, 227, 215), local_next, border_radius=7)
            pygame.draw.rect(card_surf, (214, 204, 188), local_next, 1, border_radius=7)
            fg_next = (168, 158, 146)
        ns = f_btn.render(next_lbl, True, fg_next)
        card_surf.blit(ns, ns.get_rect(center=local_next.center))

        hint_s = f_sub.render("[<- / ->] Geser  |  [ESC] Kembali", True, COLOR_TEXT_SUB)
        hint_x = local_next.right + 14
        if hint_x + hint_s.get_width() < local_done.x - 10:
            card_surf.blit(hint_s, (hint_x, fy + (footer_h - hint_s.get_height()) // 2))

        # Tombol Tutup (MERAH)
        hov_done = local_done.move(cx0, cy0).collidepoint((mx_cur, my_cur))
        pygame.draw.rect(card_surf, (212, 70, 62) if hov_done else (188, 62, 54), local_done, border_radius=7)
        ds = f_btn.render("Tutup", True, (255, 255, 255))
        card_surf.blit(ds, ds.get_rect(center=local_done.center))

        return card_surf

    def _draw_cue_card_overlay(
        self,
        surface: pygame.Surface,
        specs: List[_CardSpec],
        ui_fonts: Dict[str, pygame.font.Font],
    ) -> None:
        if self.zoomed_card_idx is None or not specs:
            return
        total_cards = len(specs)
        idx = max(0, min(total_cards - 1, self.zoomed_card_idx))
        self.zoomed_card_idx = idx
        spec = specs[idx]

        sw, sh = surface.get_size()
        dim = pygame.Surface((sw, sh), SRCALPHA)
        dim.fill(COLOR_CUE_BACKDROP)
        surface.blit(dim, (0, 0))

        # Ukuran seragam untuk semua Cue Card agar posisi tombol selalu konsisten
        cw = min(760, int(sw * 0.80))
        ch = min(480, int(sh * 0.72))
        cx = (sw - cw) // 2
        cy = (sh - ch) // 2
        self.rect_cue = pygame.Rect(cx, cy, cw, ch)
        center_x = cx + cw // 2
        center_y = cy + ch // 2

        # 1. Gambar tumpukan kartu di belakang (jika jumlah kartu > 1)
        if total_cards > 1:
            stack_layers = self._get_cue_stack_layers(cw, ch)
            visible_layers = stack_layers if total_cards > 2 else stack_layers[1:]
            for layer_surf, off_x, off_y in visible_layers:
                lr = layer_surf.get_rect(center=(center_x + off_x, center_y + off_y))
                surface.blit(layer_surf, lr)

        # 2. Progres animasi pertukaran kartu
        elapsed = max(0.0, time.perf_counter() - self._anim_start)
        progress = min(1.0, elapsed / self._anim_duration) if self._anim_duration > 0 else 1.0
        ease = 1.0 - (1.0 - progress) ** 3

        mx_cur, my_cur = pygame.mouse.get_pos()

        # 3. Kartu aktif (sedikit naik dari tumpukan saat masuk)
        in_off_y = int((1.0 - ease) * 10) if progress < 1.0 else 0
        shadow_surf = pygame.Surface((cw + 12, ch + 14), SRCALPHA)
        pygame.draw.rect(shadow_surf, (15, 11, 8, 72), pygame.Rect(6, 8, cw, ch), border_radius=14)
        surface.blit(shadow_surf, (cx - 6, cy - 2 + in_off_y))

        active_surf = self._render_cue_card_surface(
            cw, ch, idx, total_cards, spec, ui_fonts, mx_cur, my_cur, (cx, cy), update_hitboxes=True
        )
        surface.blit(active_surf, (cx, cy + in_off_y))

        # 4. Kartu sebelumnya meluncur & miring keluar saat transisi bertukar
        if self._anim_prev_idx is not None and progress < 1.0 and 0 <= self._anim_prev_idx < total_cards:
            prev_spec = specs[self._anim_prev_idx]
            prev_surf = self._render_cue_card_surface(
                cw, ch, self._anim_prev_idx, total_cards, prev_spec, ui_fonts, -999, -999, (cx, cy), update_hitboxes=False
            )
            angle = -self._anim_dir * 7.5 * ease
            dx = int(self._anim_dir * 230 * ease)
            dy = int(-16 * math.sin(math.pi * progress))
            try:
                rot_prev = pygame.transform.rotozoom(prev_surf, angle, 1.0)
            except Exception:
                rot_prev = prev_surf
            rot_prev.set_alpha(max(0, int(255 * (1.0 - progress))))
            pr = rot_prev.get_rect(center=(center_x + dx, center_y + dy))
            surface.blit(rot_prev, pr)
        elif progress >= 1.0:
            self._anim_prev_idx = None

    def draw(self, surface: pygame.Surface) -> None:
        if not self.is_open:
            return

        ui_fonts = self._get_ui_fonts()
        f_modal_title = ui_fonts["modal_title"]
        f_modal_sub = ui_fonts["modal_sub"]
        f_btn = ui_fonts["btn"]
        f_summary = ui_fonts["card_summary"]
        f_action = ui_fonts["card_action"]

        sw, sh = surface.get_size()

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
        sub_str = "Klik kartu mana saja untuk memperbesar Cue Card agar lebih jelas dibaca"
        surface.blit(f_modal_title.render(title_str, True, COLOR_HEADING), (mx + 20, my + 10))
        surface.blit(f_modal_sub.render(sub_str, True, COLOR_TEXT_SUB), (mx + 20, my + 36))

        mx_cur, my_cur = pygame.mouse.get_pos()
        self.btn_close = pygame.Rect(mx + mw - 48, my + 13, 34, 34)
        hov_close = self.btn_close.collidepoint((mx_cur, my_cur))
        pygame.draw.rect(surface, (212, 70, 62) if hov_close else (190, 56, 50), self.btn_close, border_radius=6)
        x_lbl = f_modal_title.render("X", True, (255, 255, 255))
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
            is_hov = (self.zoomed_card_idx is None) and tr.collidepoint((mx_cur, my_cur))
            bg = COLOR_BTN_ACTIVE if is_act else (COLOR_BTN_HOVER if is_hov else COLOR_BTN_BG)
            fg = (255, 255, 255) if is_act else COLOR_TEXT
            pygame.draw.rect(surface, bg, tr, border_radius=7)
            if not is_act:
                pygame.draw.rect(surface, COLOR_MODAL_BORDER, tr, 1, border_radius=7)
            t_s = f_btn.render(lbl, True, fg)
            surface.blit(t_s, t_s.get_rect(center=tr.center))

        # 5. Area Konten Scrollable (Grid Kartu Ringkas)
        footer_h = 58
        body_x = mx + 20
        body_y = tab_y + tab_h + 12
        body_w = mw - 40
        body_h = (my + mh - footer_h) - body_y - 8
        self.rect_body = pygame.Rect(body_x, body_y, body_w, body_h)

        pygame.draw.rect(surface, COLOR_BODY_BG, self.rect_body, border_radius=8)
        pygame.draw.rect(surface, COLOR_CARD_BORDER, self.rect_body, 1, border_radius=8)

        specs = self._get_tab_specs()
        x0 = body_x + 14
        y0 = body_y + 12
        w = body_w - 32
        gap = 11
        cy = y0
        cols = 3 if self.active_tab == 0 else 2

        layout_cards: List[Tuple[pygame.Rect, int, _CardSpec, List[str]]] = []
        grid_buffer: List[Tuple[int, _CardSpec]] = []

        def flush_grid_row() -> None:
            nonlocal cy
            if not grid_buffer:
                return
            col_w = (w - gap * (cols - 1)) // cols
            for i in range(0, len(grid_buffer), cols):
                row = grid_buffer[i:i + cols]
                computed = []
                max_h = 0
                for c_idx, sp in row:
                    ch_card, wr = self._compute_grid_card_height(col_w, sp["summary"], f_summary, f_action)
                    max_h = max(max_h, ch_card)
                    computed.append((c_idx, sp, wr))
                for j, (c_idx, sp, wr) in enumerate(computed):
                    rc = pygame.Rect(x0 + j * (col_w + gap), cy, col_w, max_h)
                    layout_cards.append((rc, c_idx, sp, wr))
                cy += max_h + gap
            grid_buffer.clear()

        for c_idx, sp in enumerate(specs):
            if sp["full_width"]:
                flush_grid_row()
                ch_card, wr = self._compute_grid_card_height(w, sp["summary"], f_summary, f_action)
                rc = pygame.Rect(x0, cy, w, ch_card)
                layout_cards.append((rc, c_idx, sp, wr))
                cy += ch_card + gap
            else:
                grid_buffer.append((c_idx, sp))
        flush_grid_row()

        content_bottom = max((r.bottom for (r, _, _, _) in layout_cards), default=body_y + 20)
        total_h = content_bottom - body_y + 14
        self.max_scroll = max(0.0, float(total_h - body_h))
        self.scroll_y = max(0.0, min(self.max_scroll, self.scroll_y))
        scroll_off = int(self.scroll_y)

        self._card_hitboxes = []
        body_hovered = (self.zoomed_card_idx is None) and self.rect_body.collidepoint((mx_cur, my_cur))
        old_clip = surface.get_clip()
        surface.set_clip(self.rect_body)
        for rect_item, c_idx, sp, wr in layout_cards:
            shifted = rect_item.move(0, -scroll_off)
            if shifted.bottom >= self.rect_body.y and shifted.y <= self.rect_body.bottom:
                clipped_hit = shifted.clip(self.rect_body)
                if clipped_hit.width > 0 and clipped_hit.height > 0:
                    self._card_hitboxes.append((clipped_hit, c_idx))
                is_hov = body_hovered and shifted.collidepoint((mx_cur, my_cur))
                self._draw_grid_card(surface, shifted, sp, wr, is_hov, ui_fonts)
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
        hint = "Tekan [H] buka/tutup Panduan  |  [1][2][3] Ganti Tab  |  Klik kartu untuk Cue Card"
        surface.blit(f_modal_sub.render(hint, True, COLOR_TEXT_SUB), (mx + 22, footer_y + 20))

        btn_w = 215
        self.btn_start = pygame.Rect(mx + mw - btn_w - 20, footer_y + 10, btn_w, 38)
        hov_start = (self.zoomed_card_idx is None) and self.btn_start.collidepoint((mx_cur, my_cur))
        pygame.draw.rect(surface, (52, 152, 74) if hov_start else COLOR_GREEN, self.btn_start, border_radius=8)
        start_lbl = f_btn.render("[ENTER] Mulai Petualangan!" if self.welcome_mode else "[ESC] Tutup Panduan", True, (255, 255, 255))
        surface.blit(start_lbl, start_lbl.get_rect(center=self.btn_start.center))

        if self.active_tab == 0:
            self.btn_to_tabs = pygame.Rect(self.btn_start.x - 210, footer_y + 10, 198, 38)
            hov_t = (self.zoomed_card_idx is None) and self.btn_to_tabs.collidepoint((mx_cur, my_cur))
            pygame.draw.rect(surface, COLOR_BTN_HOVER if hov_t else COLOR_BTN_BG, self.btn_to_tabs, border_radius=8)
            pygame.draw.rect(surface, COLOR_MODAL_BORDER, self.btn_to_tabs, 1, border_radius=8)
            tl = f_btn.render("Lihat Panduan Tab ->", True, COLOR_TEXT)
            surface.blit(tl, tl.get_rect(center=self.btn_to_tabs.center))
        else:
            self.btn_to_tabs = pygame.Rect(0, 0, 0, 0)

        # 7. Cue Card Zoom Overlay (jika ada kartu yang diklik)
        if self.zoomed_card_idx is not None:
            self._draw_cue_card_overlay(surface, specs, ui_fonts)
