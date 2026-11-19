"""TabGlossary: Panel Glosarium & Bantuan Kontekstual (?) untuk setiap tab InspectorDock."""

from typing import Dict, List, Tuple
import pygame

from ..core import config
from .components import draw_card, draw_badge_pill

TAB_GLOSSARY_DATA: Dict[int, Dict[str, object]] = {
    0: {
        "title": "PANDUAN: HERO COMPANION",
        "phase": "SEMUA FASE",
        "purpose": "Memantau status Hero (Bolu), progres kunci menara, dan isi tas inventaris selama petualangan.",
        "cards": [
            ("INFORMASI DI TAB INI", config.COLOR_ACCENT_BLUE, [
                ("Kartu Hero", "Menampilkan HP, batas maksimum HP, bonus ATK/DEF, dan sisa ramuan."),
                ("Lencana Progres", "Menghitung peti terbuka, Kunci Rune (target 3), dan jumlah ayam."),
                ("Tas Inventaris", "Daftar item yang didapat; gunakan tombol < dan > untuk menggeser slot."),
            ]),
            ("KONTROL & ISTILAH", config.COLOR_ACCENT_GOLD, [
                ("Peluit [SPACE]", "Memanggil atau memancing NPC agar mengecek posisi suara Bolu."),
                ("Kunci Rune", "Didapat dari peti harta; butuh 3 kunci untuk membuka Portal Menara Kuno."),
            ]),
        ],
    },
    1: {
        "title": "PANDUAN: 01-03 PATHFINDING",
        "phase": "AKTIF DI EXPLORATION",
        "purpose": "Mengatur dan membandingkan algoritma pencarian jalur terpendek NPC saat berpatroli maupun mengejar.",
        "cards": [
            ("INFORMASI DI TAB INI", config.COLOR_ACCENT_BLUE, [
                ("Algoritma & Fokus", "Memilih metode search dan NPC yang rute pencariannya ingin diinspeksi."),
                ("Metrik Jalur", "Node Diekspansi, Panjang Jalur, Total Bobot medan, dan Waktu Solver (ms)."),
                ("Komparasi vs UCS", "Menunjukkan berapa persen simpul yang berhasil dihemat oleh heuristik A*."),
            ]),
            ("PENGERTIAN ALGORITMA", config.COLOR_ACCENT_GOLD, [
                ("UCS (h=0)", "Uniform Cost Search: menjamin rute termurah tanpa heuristik, namun mengecek paling banyak node."),
                ("A* Manhattan", "Memakai f(n) = g(n) + h(n) dengan jarak grid |dx| + |dy|; cepat dan terarah."),
                ("A* Euclidean / Chebyshev", "Alternatif heuristik jarak garis lurus atau diagonal untuk membandingkan efisiensi."),
                ("Bobot Medan", "Jalan Tanah = 1.0 (lebih disukai NPC), Rumput Liar = 2.0 (lebih lambat)."),
            ]),
        ],
    },
    2: {
        "title": "PANDUAN: 04 ADVERSARIAL",
        "phase": "AKTIF DI BATTLE",
        "purpose": "Mengatur kecerdasan taktis AI lawan saat pertarungan turn-based berlangsung.",
        "cards": [
            ("INFORMASI DI TAB INI", config.COLOR_ACCENT_BLUE, [
                ("Depth (1-8)", "Kedalaman langkah ke depan yang disimulasikan AI sebelum memilih aksi."),
                ("Move Ordering", "Urutan evaluasi cabang: Heuristic memaksimalkan pemangkasan Alpha-Beta."),
                ("Statistik Duel", "Jumlah node dievaluasi, cabang dipangkas (pruned), waktu berpikir, dan skor tiap aksi."),
            ]),
            ("PENGERTIAN ALGORITMA", config.COLOR_ACCENT_GOLD, [
                ("Minimax", "AI (MAX) memilih skor tertinggi dengan asumsi pemain (MIN) selalu membalas optimal."),
                ("Alpha-Beta Pruning", "Memangkas cabang pohon yang tidak memengaruhi keputusan akhir agar komputasi jauh lebih cepat."),
                ("Expectimax", "Memodelkan elemen peluang/stokastik melalui Chance Node."),
                ("Fungsi Evaluasi", "Balanced, Aggressive, atau Defensive mengubah bobot penilaian HP dan damage."),
            ]),
        ],
    },
    3: {
        "title": "PANDUAN: 05-06 CSP & LOCAL SEARCH",
        "phase": "AKTIF DI PRE_BATTLE",
        "purpose": "Membentuk tim musuh yang legal (bebas pelanggaran aturan) dan seimbang sebelum duel dimulai.",
        "cards": [
            ("INFORMASI DI TAB INI", config.COLOR_ACCENT_BLUE, [
                ("Target Kesulitan", "Slider target 'Fun Zone'; mode Adaptif mengikuti HP/buff Hero, atau geser untuk Manual (+ tombol Auto)."),
                ("Metrik Optimasi", "Difficulty aktual skuad, Fitness (-|diff - target|), jumlah Iterasi, dan Waktu AI."),
                ("Validasi C1-C4", "Menjamin total HP, Ramuan, ATK, dan keunikan job memenuhi batasan CSP."),
            ]),
            ("PENGERTIAN ALGORITMA", config.COLOR_ACCENT_GOLD, [
                ("CSP (MRV, LCV, AC-3)", "Constraint Satisfaction: menyaring domain nilai agar konfigurasi awal tim 100% legal."),
                ("Hill Climbing / Sideways", "Memperbaiki state ke tetangga terbaik hingga puncak lokal tercapai."),
                ("Random Restart", "Mengulang pencarian dari titik acak baru agar tidak terjebak local optimum."),
                ("Simulated Annealing", "Sesekali menerima langkah lebih buruk di awal untuk keluar dari jebakan lokal."),
                ("Genetic Algorithm", "Mengembangkan populasi skuad lewat seleksi, crossover, dan mutasi."),
            ]),
        ],
    },
    4: {
        "title": "PANDUAN: 07 LOGIC & REASONING",
        "phase": "AKTIF SAAT PERCEPT",
        "purpose": "Menampilkan penalaran Knowledge Base proposisional saat peti dibuka atau kunci portal diverifikasi.",
        "cards": [
            ("INFORMASI DI TAB INI", config.COLOR_ACCENT_BLUE, [
                ("Persepsi Sensorik (TELL)", "Kejadian terbaru di dunia game yang langsung dicatat sebagai fakta KB."),
                ("Fakta & Aturan CNF", "Aturan implikasi yang sudah diubah menjadi bentuk klausa disjungsi."),
                ("Jejak Resolusi & ASK", "Urutan eliminasi literal hingga Kontradiksi dan keputusan siapa yang mengejar."),
            ]),
            ("PENGERTIAN ISTILAH", config.COLOR_ACCENT_GOLD, [
                ("TELL & ASK", "TELL memasukkan fakta baru ke KB; ASK menguji apakah suatu Query bernilai benar."),
                ("CNF", "Conjunctive Normal Form: format standar klausa logika (mis. ~Open(A) v Alarm(K))."),
                ("Resolusi Refutasi", "Menegasi target (~Query) lalu menggabungkan klausa hingga muncul Klausa Kosong (kontradiksi) sebagai bukti sah."),
            ]),
        ],
    },
    5: {
        "title": "PANDUAN: 08 AUTOMATED PLANNING",
        "phase": "EXPLORATION & BATTLE",
        "purpose": "Menyusun rencana aksi PDDL/STRIPS untuk patroli pulau dan rotasi darurat tim saat duel.",
        "cards": [
            ("INFORMASI DI TAB INI", config.COLOR_ACCENT_BLUE, [
                ("Mesin Perencana", "Memilih Forward Progression (A*) atau Backward Regression (STRIPS)."),
                ("State Fluents", "Membandingkan kondisi awal dunia (s0) dengan kondisi sasaran (Goal)."),
                ("Sekuens Rencana", "Urutan aksi terpilih beserta syarat (Pre) dan hasil efeknya (Add)."),
            ]),
            ("PENGERTIAN ALGORITMA & ISTILAH", config.COLOR_ACCENT_GOLD, [
                ("Forward Progression (A*)", "Mencari maju dari s0 menuju Goal dipandu skor f(n) = g(n) + h(n)."),
                ("Backward Regression (STRIPS)", "Mencari mundur dari Goal ke s0 hanya lewat aksi yang relevan dan konsisten."),
                ("Preconditions & Effects", "Syarat agar aksi legal dijalankan, serta fakta baru (+Add) dan fakta terhapus (-Del)."),
            ]),
        ],
    },
    6: {
        "title": "PANDUAN: PENGATURAN & AUDIO",
        "phase": "SEMUA FASE",
        "purpose": "Mengontrol audio permainan, mereset sesi petualangan, dan melihat informasi proyek.",
        "cards": [
            ("INFORMASI DI TAB INI", config.COLOR_ACCENT_BLUE, [
                ("Slider BGM & SFX", "Mengatur volume musik latar dan efek suara langkah/pertempuran secara langsung."),
                ("Reset Status", "Mengembalikan posisi Hero, peti harta, inventaris, dan target adaptif CSP ke awal."),
                ("Tentang Aplikasi", "Ringkasan daftar materi kecerdasan buatan yang diimplementasikan di Bakekok."),
            ]),
        ],
    },
}


def _wrap_text_lines(font: pygame.font.Font, text: str, max_w: int) -> List[str]:
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


def draw_tab_glossary(
    surface: pygame.Surface,
    content_rect: pygame.Rect,
    tab_id: int,
    fonts: Dict[str, pygame.font.Font],
    scroll_y: float,
) -> float:
    """Merender kartu glosarium & penjelasan istilah tab ke dalam content_rect; mengembalikan max_scroll."""
    data = TAB_GLOSSARY_DATA.get(tab_id, TAB_GLOSSARY_DATA[0])
    font_tiny = fonts.get("tiny", pygame.font.Font(None, 13))
    font_sm = fonts.get("sm", pygame.font.Font(None, 16))

    cx = content_rect.x + 12
    card_w = content_rect.width - 28  # sisakan ruang tipis untuk scrollbar
    pad = 10
    line_h_tiny = font_tiny.get_height() + 2
    line_h_sm = font_sm.get_height() + 2

    # Siapkan layout seluruh kartu lebih dulu agar tinggi total & scroll akurat
    draw_ops: List[Tuple[pygame.Rect, object]] = []
    cy = content_rect.y + 12

    # 1. Kartu Kegunaan Tab
    title_lines = _wrap_text_lines(font_sm, str(data["title"]), card_w - pad * 2)
    purpose_lines = _wrap_text_lines(font_tiny, str(data["purpose"]), card_w - pad * 2)
    h1 = 10 + len(title_lines) * line_h_sm + 24 + len(purpose_lines) * line_h_tiny + 10
    r1 = pygame.Rect(cx, cy, card_w, h1)

    def _draw_purpose(surf: pygame.Surface, rc: pygame.Rect, tl=title_lines, pl=purpose_lines, d=data):
        draw_card(surf, rc, (254, 248, 236), border_color=config.COLOR_ACCENT_GOLD, border_radius=8)
        ty = rc.y + 8
        for ln in tl:
            surf.blit(font_sm.render(ln, True, config.COLOR_ACCENT_GOLD), (rc.x + pad, ty))
            ty += line_h_sm
        ty += 2
        badge_txt = str(d["phase"])
        bw = font_tiny.size(badge_txt)[0] + 16
        pill_r = pygame.Rect(rc.x + pad, ty, bw, 18)
        draw_badge_pill(surf, pill_r, badge_txt, (252, 240, 212), (145, 86, 14), font_tiny, border_color=(212, 160, 48))
        ty += 24
        for ln in pl:
            surf.blit(font_tiny.render(ln, True, config.COLOR_TEXT_PRIMARY), (rc.x + pad, ty))
            ty += line_h_tiny

    draw_ops.append((r1, _draw_purpose))
    cy += h1 + 10

    # 2. Kartu-kartu Penjelasan Bagian & Algoritma
    for sec_title, accent_col, entries in data["cards"]:  # type: ignore[attr-defined]
        inner_blocks: List[Tuple[str, List[str]]] = []
        content_h = 28
        for term, desc in entries:
            d_lines = _wrap_text_lines(font_tiny, desc, card_w - pad * 2 - 12)
            inner_blocks.append((term, d_lines))
            content_h += line_h_tiny + len(d_lines) * line_h_tiny + 8

        sec_h = content_h + 6
        r_sec = pygame.Rect(cx, cy, card_w, sec_h)

        def _draw_section(surf: pygame.Surface, rc: pygame.Rect, st=sec_title, ac=accent_col, blocks=inner_blocks):
            draw_card(surf, rc, config.COLOR_CARD_BG, border_color=config.COLOR_CARD_BORDER, border_radius=8)
            hdr = font_tiny.render(f"── {st} ──", True, ac)
            surf.blit(hdr, (rc.x + (rc.width - hdr.get_width()) // 2, rc.y + 7))
            iy = rc.y + 26
            for term, d_lines in blocks:
                sub_h = line_h_tiny + len(d_lines) * line_h_tiny + 4
                sub_r = pygame.Rect(rc.x + 8, iy, rc.width - 16, sub_h)
                draw_card(surf, sub_r, (250, 246, 238), border_color=(226, 216, 202), border_radius=5)
                surf.blit(font_tiny.render(f"• {term}", True, ac), (sub_r.x + 8, sub_r.y + 3))
                dy = sub_r.y + 3 + line_h_tiny
                for ln in d_lines:
                    surf.blit(font_tiny.render(ln, True, config.COLOR_TEXT_PRIMARY), (sub_r.x + 14, dy))
                    dy += line_h_tiny
                iy += sub_h + 4

        draw_ops.append((r_sec, _draw_section))
        cy += sec_h + 10

    # 3. Kartu Catatan Footer
    hint_h = 30
    r_hint = pygame.Rect(cx, cy, card_w, hint_h)

    def _draw_hint(surf: pygame.Surface, rc: pygame.Rect):
        draw_card(surf, rc, (242, 235, 222), border_color=config.COLOR_CARD_BORDER, border_radius=6)
        txt = font_tiny.render("Klik tombol [?] di atas untuk kembali ke kontrol tab.", True, config.COLOR_TEXT_SECONDARY)
        surf.blit(txt, (rc.centerx - txt.get_width() // 2, rc.centery - txt.get_height() // 2))

    draw_ops.append((r_hint, _draw_hint))
    cy += hint_h + 10

    total_h = cy - content_rect.y
    max_scroll = max(0.0, float(total_h - content_rect.height))
    clamped_scroll = max(0.0, min(max_scroll, scroll_y))
    scroll_off = int(clamped_scroll)

    for rc, fn in draw_ops:
        shifted = rc.move(0, -scroll_off)
        if shifted.bottom < content_rect.top or shifted.top > content_rect.bottom:
            continue
        fn(surface, shifted)

    # Scrollbar tipis jika konten melebihi tinggi panel
    if max_scroll > 0:
        track_h = content_rect.height - 16
        thumb_h = max(24, int(track_h * (content_rect.height / float(total_h))))
        thumb_y = content_rect.y + 8 + int((track_h - thumb_h) * (clamped_scroll / max_scroll))
        pygame.draw.rect(surface, (196, 182, 164), pygame.Rect(content_rect.right - 7, thumb_y, 4, thumb_h), border_radius=2)

    return max_scroll
