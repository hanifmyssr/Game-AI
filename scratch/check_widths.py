import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame
pygame.init()
pygame.display.set_mode((1024, 768))

from game.battle_system import BattleSystem
from game.overlay import DebugOverlay
from game.events import GameManager
from game import config

fonts = {}
try:
    fonts["sm"] = pygame.font.SysFont(["consolas", "segoeui", "arial"], 14)
    fonts["bubble"] = pygame.font.SysFont(["consolas", "segoeui", "arial"], 14, bold=True)
    fonts["title"] = pygame.font.SysFont(["segoeui", "arial"], 17, bold=True)
    fonts["huge"] = pygame.font.SysFont(["segoeui", "arial"], 24, bold=True)
except:
    fonts["sm"] = pygame.font.Font(None, 20)
    fonts["bubble"] = pygame.font.Font(None, 22)
    fonts["title"] = pygame.font.Font(None, 26)
    fonts["huge"] = pygame.font.Font(None, 36)

events = GameManager()
bs = BattleSystem()
overlay = DebugOverlay(events, fonts)

pw = config.DEBUG_PANEL_WIDTH - 24
print(f"Content width pw = {pw}")

font_sm = overlay.fonts['sm']
font_bubble = overlay.fonts.get('bubble', font_sm)
font_title = overlay.fonts.get('title', font_sm)

# Check buttons in Kartu 3:
# Let's inspect self.btn_attack, btn_heavy, btn_defend, btn_potion
print("btn_attack width:", overlay.btn_attack.width)
print("btn_heavy width:", overlay.btn_heavy.width)
print("btn_defend width:", overlay.btn_defend.width)
print("btn_potion width:", overlay.btn_potion.width)

# Also check exploration mode text
# In exploration mode:
lines_exp = [
    "  • Area Rumput  : Cost 2.0 (Normal)",
    "── STATISTIK JALUR ────────────────────",
    "  Node Diekspansi : 100",
    "  Panjang Jalur   : 20 langkah",
    "  Total Cost Rute : 45.0",
    "  Waktu Eksekusi  : 1.234 ms",
    "── PERBANDINGAN RUTE ──────────────────",
    "  UCS (h=0):",
    "    Node: 100 │ Cost: 45.0 │ 1.234 ms",
    "  A* (Manhattan):",
    "    Node: 45 │ Cost: 45.0 │ 0.543 ms",
    "    Heuristik: Manhattan",
    "  A* 2.2x lebih hemat ekspansi",
    "  ⚠ UCS 1.5x lebih hemat",
    "── KONTROL ────────────────────────────",
    "  [WASD / Panah]  : Gerakkan Player",
    "  [Ctrl]          : Tampilkan animasi path",
    "  [Spasi]         : Toggle Kejar NPC",
    "  [Esc]           : Keluar Game",
]

for s in lines_exp:
    w = font_sm.size(s)[0]
    overflow = w > pw
    tag = "OVERFLOW!" if overflow else "OK"
    print(f"EXP text w={w:3d} (max {pw}) -> {tag}: {ascii(s)}")

strings_to_check = [
    ('header', 'DUEL MINIMAX AI', font_title, pw),
    ('sub_algo', 'Algoritma AI NPC:', font_sm, pw),
    ('sub_eval', 'Fungsi Evaluasi:', font_sm, pw),
    ('depth_label', f'Early Stop / Depth: {bs.depth}', font_sm, pw - 116),
    ('mo_label', 'Move Ordering:', font_sm, pw - 128),
    ('turn_text_npc', 'Giliran NPC (AI Berpikir...)', font_bubble, pw - 12),
    ('turn_text_player', 'Giliran Anda (Pilih Aksi)', font_bubble, pw - 12),
    ('btn_attack', 'Attack (18)', font_sm, overlay.btn_attack.width),
    ('btn_heavy_ready', 'Heavy (30)', font_sm, overlay.btn_heavy.width),
    ('btn_heavy_cd', 'Heavy (CD:2)', font_sm, overlay.btn_heavy.width),
    ('btn_defend', 'Defend (-65%)', font_sm, overlay.btn_defend.width),
    ('btn_potion', 'Potion (3)', font_sm, overlay.btn_potion.width),
    ('ts_mtitle', '-- EVALUASI AKSI & NODE COUNT --', font_sm, pw),
    ('comp_title', 'Komparasi Metode (Cutoff d=4):', font_sm, pw - 16),
    ('t_mm', '• Pure Minimax : 172 node', font_sm, pw - 16),
    ('t_ab', '• Alpha-Beta   : 108 node (37.2% hemat)', font_sm, pw - 16),
    ('t_ex', '• Expectimax   : 320 node (stokastik)', font_sm, pw - 16),
    ('best_text', 'Pilihan: HEAVY_ATTACK │ Skor: 0.0', font_sm, pw - 16),
    ('best_text_long', 'Pilihan: HEAVY_ATTACK │ Skor: -1000.0', font_sm, pw - 16),
    ('root_title', 'Perbandingan Skor: Det vs Expectimax', font_sm, pw - 16),
    ('col_hdr_act', 'Aksi Legal', font_sm, 120),
    ('col_hdr_det', 'Det (A-B)', font_sm, 90),
    ('col_hdr_exp', 'Expectimax', font_sm, 100),
    ('col_val_act', '> HEAVY_ATTACK', font_sm, 120),
    ('col_val_det', '  1050.0', font_sm, 90),
    ('col_val_exp', '   849.5 (75%)', font_sm, 115),
    ('btn_tree_title', 'Decision Tree: TAMPIL (ON)', font_bubble, pw - 8),
    ('btn_tree_hint', 'Klik untuk sembunyikan [T]', font_sm, pw - 8),
    ('footer1', '[R] Reset Duel', font_sm, pw),
    ('footer2', '[Tab] Kembali  [T] Tree', font_sm, pw),
    ('footer3', '[1..4] Shortcut Aksi', font_sm, pw),
]

for name, s, f, max_w in strings_to_check:
    w = f.size(s)[0]
    overflow = w > max_w
    tag = "OVERFLOW!" if overflow else "OK"
    print(f"{tag:10} {name:20}: w={w:3d} (max {max_w:3d}) -> {ascii(s)}")

