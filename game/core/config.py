"""Konfigurasi global untuk port Python game BoluKesepian."""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSET_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BASE_DIR, "data")
MAP_FILE = os.path.join(DATA_DIR, "map_tubes.json")

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
FPS = 60

# Collapsible Adventurer Journal Geometri
NAV_RAIL_WIDTH = 64
INSPECTOR_WIDTH = 356                                      # Melebar +60px untuk font +2 & anti-overflow
TOTAL_DOCK_WIDTH = NAV_RAIL_WIDTH + INSPECTOR_WIDTH        # 420 px (saat terbuka)
TOTAL_COLLAPSED_WIDTH = NAV_RAIL_WIDTH                     # 64 px (saat tertutup)
DEBUG_LEFT_PANEL_WIDTH = TOTAL_DOCK_WIDTH                  # 420 px (kompatibilitas)
DEBUG_PANEL_WIDTH = TOTAL_DOCK_WIDTH
TREE_PANEL_WIDTH = 380

GAME_VIEWPORT_X = TOTAL_DOCK_WIDTH                         # 420 px
GAME_VIEWPORT_WIDTH = WINDOW_WIDTH - TOTAL_DOCK_WIDTH      # 860 px
GAME_VIEWPORT_HEIGHT = WINDOW_HEIGHT                       # 800 px
SAFE_CAMERA_FOCUS_X = 850                                  # Pusat pandangan kamera aman (Bolu bebas halangan)

BG_COLOR = (240, 235, 224)
UI_PANEL = (248, 244, 235)
UI_PANEL_BORDER = (208, 192, 172)
UI_TEXT = (38, 30, 24)
UI_ACCENT = (40, 118, 198)
UI_SELECTED = (235, 175, 45)

# Palet Warna Cozy Adventurer Journal (Parchment & Wood RPG Theme)
COLOR_NAV_BG = (46, 35, 25)             # Dark Walnut Wood
COLOR_NAV_HOVER = (68, 52, 38)          # Warm Wood Hover
COLOR_NAV_BORDER = (82, 64, 48)
COLOR_NAV_ACCENT = (235, 175, 45)       # Honey Gold Accent

COLOR_INSPECTOR_BG = (248, 244, 235)    # Warm Parchment Cream
COLOR_INSPECTOR_BORDER = (208, 192, 172)# Leather/Cinnamon Border
COLOR_HEADER_BG = (238, 231, 218)       # Header Pita Perkamen

COLOR_CARD_BG = (255, 255, 255)         # Ivory White Cards
COLOR_CARD_BORDER = (218, 206, 188)     # Soft Cinnamon Card Border
COLOR_CARD_ROW_BG = (250, 246, 240)     # Row Background
COLOR_HOVER = (242, 236, 226)

COLOR_TEXT_PRIMARY = (38, 30, 24)       # Dark Charcoal Espresso (tajam anti-silau)
COLOR_TEXT_SECONDARY = (115, 98, 82)    # Warm Coffee Latte
COLOR_TEXT_MUTED = (160, 145, 130)

COLOR_ACCENT_GOLD = (205, 135, 25)      # Honey Gold
COLOR_ACCENT_BLUE = (40, 118, 198)      # River Azure Blue
COLOR_STATUS_SUCCESS = (42, 138, 62)    # Forest Leaf Green (+Add / Valid)
COLOR_STATUS_DANGER = (195, 48, 48)     # Brick Crimson (Pruned / -Del)

# Parameter Pertarungan
MAX_HP = 100
POTION_HEAL = 25

# Durasi animasi
PLAYER_MOVE_DURATION = 0.12
NPC_STEP_DURATION = 0.2
NPC_CHASE_INTERVAL = 0.35
CALL_BUBBLE_TIME = 1.5

# 1 siklus walk (4 frame) pas 1 langkah ubin
WALK_FRAME_DURATION = PLAYER_MOVE_DURATION / 4
NPC_WALK_FRAME_DURATION = NPC_STEP_DURATION / 4

# Sprite Bolu (player): 1 frame idle + 4 frame walk untuk tiap arah
BOLU_DIR = os.path.join(ASSET_DIR, "bolu")

# Sprite Oyen (NPC): 1 frame idle + 4 frame walk untuk tiap arah
OYEN_DIR = os.path.join(ASSET_DIR, "oyen")

# Sprite Kuro & Shiro (NPC patroli / aset kustom terdedikasi)
KURO_DIR = os.path.join(ASSET_DIR, "kuro")
SHIRO_DIR = os.path.join(ASSET_DIR, "shiro")

# Tinggi karakter dalam piksel dunia (2 ubin x 16px)
CHARACTER_HEIGHT = 32

# daftar algoritma: (nama internal, label dropdown)
ALGORITHMS = [
    ("UCS", "UCS (h = 0)"),
    ("A_STAR_MANHATTAN", "A* (Heuristik Manhattan)"),
    ("A_STAR_EUCLIDEAN", "A* (Heuristik Euclidean)"),
    ("A_STAR_CHEBYSHEV", "A* (Heuristik Chebyshev)"),
]

# Arah gerakan 4 arah: Atas, Bawah, Kiri, Kanan (sesuai Vector2i.UP/DOWN/LEFT/RIGHT)
DIRS = [(0, -1), (0, 1), (-1, 0), (1, 0)]

# Warna visualisasi pathfinding
COLOR_EXPANDED_FILL = (245, 205, 45, 120)
COLOR_EXPANDED_BORDER = (255, 230, 90, 210)
COLOR_PATH = (40, 110, 255, 135)
COLOR_PATH_BORDER = (90, 165, 255, 210)

# Warna panel debug overlay (tema light modern - clean white background)
DEBUG_PANEL_BG = (255, 255, 255, 250)
DEBUG_PANEL_BORDER = (200, 212, 228, 230)
DEBUG_CARD_BG = (248, 250, 254, 245)
DEBUG_CARD_BORDER = (215, 225, 238, 220)
DEBUG_CARD_HEADER_BG = (238, 245, 255, 245)
DEBUG_CARD_HEADER_BORDER = (195, 215, 245, 220)
DEBUG_CARD_ROW_BG = (255, 255, 255, 240)
DEBUG_CARD_ROW_BORDER = (225, 232, 242, 220)
DEBUG_TEXT_PRIMARY = (25, 32, 45)
DEBUG_TEXT_SECONDARY = (95, 108, 125)
DEBUG_TEXT_HIGHLIGHT = (16, 95, 195)
DEBUG_TEXT_WARN = (190, 85, 15)
DEBUG_DROPDOWN_BG = (255, 255, 255, 255)
DEBUG_DROPDOWN_HOVER = (235, 243, 255, 255)
DEBUG_DROPDOWN_SELECTED = (35, 110, 215, 255)

# --------------------------------------------------------------------------- #
# Konstanta Tahap 3 & 4: CSP & Local Search Optimizer
# --------------------------------------------------------------------------- #
CHAR_TYPES = ["warrior", "ranger", "mage", "assassin"]
EVAL_PROFILES = ["BALANCED", "AGGRESSIVE", "DEFENSIVE"]

DOMAIN_NPC_COUNT = [1, 2, 3]
DOMAIN_HP = [60, 70, 80, 90, 100, 110, 120]
DOMAIN_POTIONS = [0, 1, 2, 3]
DOMAIN_ATK_BONUS = [0, 5, 10, 15]
DOMAIN_DEF_BONUS = [0, 2, 4, 6]  # Pengurang damage flat

# Budget Standar Tim NPC
BUDGET_HP_DEFAULT = 250
BUDGET_POTIONS_DEFAULT = 5
BUDGET_ATK_DEFAULT = 25

# Target Difficulty & Bobot Heuristik
TARGET_DIFFICULTY_DEFAULT = 0.55
DEFAULT_DIFFICULTY_WEIGHTS = {
    "w_hp": 0.25,
    "w_pot": 0.15,
    "w_atk": 0.20,
    "w_def": 0.10,
    "w_count": 0.20,
    "w_aggro": 0.10,
}

# Algoritma Local Search
LS_ALGORITHMS = [
    ("HILL_CLIMBING", "Hill Climbing"),
    ("SIDEWAYS", "HC + Sideways Move"),
    ("RANDOM_RESTART", "HC + Random Restart"),
    ("SIMULATED_ANNEALING", "Simulated Annealing"),
    ("GENETIC_ALGORITHM", "Genetic Algorithm"),
]

# Parameter Local Search
SA_INITIAL_TEMP = 100.0
SA_COOLING_RATE = 0.95
SA_MIN_TEMP = 0.1
GA_POPULATION_SIZE = 20
GA_GENERATIONS = 30
GA_MUTATION_RATE = 0.15
GA_CROSSOVER_RATE = 0.80