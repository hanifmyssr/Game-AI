"""Konfigurasi global untuk port Python game BoluKesepian."""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BASE_DIR, "data")
MAP_FILE = os.path.join(DATA_DIR, "map_tubes.json")

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
FPS = 60

BG_COLOR = (28, 30, 34)
UI_PANEL = (38, 40, 46)
UI_PANEL_BORDER = (70, 72, 80)
UI_TEXT = (230, 230, 235)
UI_ACCENT = (30, 144, 255)
UI_SELECTED = (45, 100, 170)

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
COLOR_EXPANDED_FILL = (51, 153, 255, 90)
COLOR_EXPANDED_BORDER = (51, 153, 255)
COLOR_PATH = (255, 217, 26)
COLOR_PATH_NODE = (255, 230, 90)