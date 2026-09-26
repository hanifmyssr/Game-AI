"""Sistem animasi sprite 2D: arah hadap + state idle/walk.

Modul ini terpisah dari logika movement supaya bisa dipakai ulang oleh
player maupun NPC. Tanggung jawabnya hanya:

- memuat frame PNG yang sudah ada (tidak menggambar ulang sprite),
- menormalkan framing antar frame (margin transparan dibuang, tinggi
  diseragamkan, kaki disejajarkan ke bawah) supaya tidak ikut "bergoyang",
- memilih frame aktif dari kombinasi (state, direction).

Sprite tidak pernah di-resize saat render: filter yang dipakai hanya
nearest-neighbor / point sampling, tanpa bilinear, blur, atau anti-alias.
"""

import os
from enum import Enum

import pygame

from . import config


class Direction(Enum):
    """Arah hadap karakter."""

    SOUTH = "south"   # bawah
    NORTH = "north"   # atas
    EAST = "east"     # kanan
    WEST = "west"     # kiri


class AnimationState(Enum):
    """State animasi karakter."""

    IDLE = "idle"
    WALK = "walk"


# (delta grid x, delta grid y) -> arah, mengikuti config.DIRS.
DELTA_TO_DIRECTION = {
    (0, 1): Direction.SOUTH,
    (0, -1): Direction.NORTH,
    (1, 0): Direction.EAST,
    (-1, 0): Direction.WEST,
}

# Frame PNG per (state, direction), urutan kiri -> kanan = urutan animasi.
FRAME_FILES = {
    (AnimationState.IDLE, Direction.SOUTH): ("idle_south.png",),
    (AnimationState.IDLE, Direction.NORTH): ("idle_north.png",),
    (AnimationState.IDLE, Direction.EAST): ("idle_east.png",),
    (AnimationState.IDLE, Direction.WEST): ("idle_west.png",),
    (AnimationState.WALK, Direction.SOUTH): (
        "walk_south_1.png",
        "walk_south_2.png",
        "walk_south_3.png",
        "walk_south_4.png",
    ),
    (AnimationState.WALK, Direction.NORTH): (
        "walk_north_1.png",
        "walk_north_2.png",
        "walk_north_3.png",
        "walk_north_4.png",
    ),
    (AnimationState.WALK, Direction.EAST): (
        "walk_east_1.png",
        "walk_east_2.png",
        "walk_east_3.png",
        "walk_east_4.png",
    ),
    (AnimationState.WALK, Direction.WEST): (
        "walk_west_1.png",
        "walk_west_2.png",
        "walk_west_3.png",
        "walk_west_4.png",
    ),
}

DEFAULT_DIRECTION = Direction.SOUTH


def direction_from_delta(dx, dy):
    """Ubah arah movement grid (Vector2i) menjadi Direction.

    Movement diagonal tidak ada di game ini; sel fallback memakai arah
    terakhir agar karakter tidak kehilangan facing.
    """
    return DELTA_TO_DIRECTION.get((int(dx), int(dy)))


# --------------------------------------------------------------------------- #
# Pemuatan & normalisasi frame
# --------------------------------------------------------------------------- #
# Ambang alpha untuk membedakan isi sprite dari derau semi-transparan tipis.
ALPHA_CONTENT_THRESHOLD = 128

# Kalau bbox longgar (alpha > 0) jauh lebih besar dari bbox berambang, canvas
# itu punya derau alpha di luar sprite. Rasio 1.25 supaya set yang bersih
# (mis. Bolu, yang tepi halusnya memang bagian gambar) tidak ikut terpotong.
ALPHA_NOISE_RATIO = 1.25

# Deteksi pita artefak: komponen yang melebar >= 85% canvas, tipis, dan
# hanya ada di bagian atas frame.
BAND_WIDTH_RATIO = 0.85
BAND_MAX_HEIGHT_RATIO = 0.08
BAND_TOP_REGION_RATIO = 0.25


def _alpha_bbox(image, threshold=ALPHA_CONTENT_THRESHOLD):
    """Bounding box piksel dengan alpha >= threshold, atau None.

    Surface.get_bounding_rect() memakai alpha > 0, jadi derau alpha 1-2 di
    tepi canvas ikut terhitung. Mask pygame-ce memakai ambang alpha nyata,
    sehingga hasilnya konsisten antar frame.
    """
    rects = pygame.mask.from_surface(image, threshold).get_bounding_rects()
    if not rects:
        return None

    left = min(rect.x for rect in rects)
    top = min(rect.y for rect in rects)
    right = max(rect.right for rect in rects)
    bottom = max(rect.bottom for rect in rects)
    return pygame.Rect(left, top, right - left, bottom - top)


def _has_alpha_noise(image):
    """True kalau bbox alpha > 0 jauh lebih besar dari bbox berambang."""
    strict = _alpha_bbox(image)
    if strict is None:
        return False

    loose = image.get_bounding_rect()
    return (
        loose.width > strict.width * ALPHA_NOISE_RATIO
        or loose.height > strict.height * ALPHA_NOISE_RATIO
    )


def _strip_artifact_bands(image):
    """Buat garis horizontal full-width di bagian atas frame.

    Sebagian PNG sumber punya pita semi-transparan yang membentang dari tepi
    ke tepi dan sama sekali bukan bagian sprite. Pita ini dibuang dengan
    memotong baris di atasnya -- piksel karakter tidak dimodifikasi.
    """
    width, height = image.get_size()
    cut = 0
    mask = pygame.mask.from_surface(image, ALPHA_CONTENT_THRESHOLD)
    for rect in mask.get_bounding_rects():
        if (
            rect.width >= width * BAND_WIDTH_RATIO
            and rect.height <= height * BAND_MAX_HEIGHT_RATIO
            and rect.y < height * BAND_TOP_REGION_RATIO
        ):
            cut = max(cut, rect.bottom)

    if cut <= 0:
        return image
    return image.subsurface((0, cut, width, height - cut)).copy()


def _normalize_frame(image, target_height, strict_alpha):
    """Potong margin transparan, lalu seragamkan tinggi ke target_height.

    Frame sumber punya ukuran berbeda-beda (idle ~210px, walk ~150-190px)
    dan margin transparan yang tidak sama, sehingga akan terlihat "loncat"
    kalau dipakai mentah. Steps ini hanya memotong margin dan menskala
    (nearest-neighbor) -- tidak mengubah warna atau isi gambar.
    """
    bbox = _alpha_bbox(image) if strict_alpha else image.get_bounding_rect()
    if bbox is not None and bbox.width > 0 and bbox.height > 0:
        image = image.subsurface(bbox).copy()

    width, height = image.get_size()
    if height != target_height:
        scaled_width = max(1, int(round(width * target_height / float(height))))
        # pygame.transform.scale = point sampling (nearest-neighbor).
        image = pygame.transform.scale(image, (scaled_width, target_height))
    return image


def _load_frame(path, target_height, strict_alpha=False):
    """Muat satu PNG transparan lalu seragamkan ukuran framing-nya."""
    image = pygame.image.load(path).convert_alpha()
    return _normalize_frame(
        _strip_artifact_bands(image), target_height, strict_alpha
    )


def _compose_on_canvas(frames, target_height):
    """Tempel semua frame ke kanvas sama besar, kaki rata-rata di bawah.

    Kanvas yang sama untuk semua frame menjaga posisi sprite tetap stabil
    saat state/arah berpindah.
    """
    canvas_width = max(frame.get_width() for frame in frames)

    composed = []
    for frame in frames:
        canvas = pygame.Surface((canvas_width, target_height), pygame.SRCALPHA)
        canvas.fill((0, 0, 0, 0))
        canvas.blit(
            frame,
            (
                (canvas_width - frame.get_width()) // 2,
                target_height - frame.get_height(),
            ),
        )
        composed.append(canvas.convert_alpha())
    return composed


def _load_animation_frames(directory, target_height):
    """(state, direction) -> list surface, semua memakai kanvas yang sama.

    Pita artefak dibuang per frame. Pemotongan margin memakai bbox berambang
    hanya kalau asset set-nya terdeteksi punya derau alpha di luar sprite;
    set yang bersih (mis. Bolu) tetap memakai bbox alpha > 0 supaya tepi
    halus sprite tidak ikut terpotong.
    """
    stripped = {}
    for key, filenames in FRAME_FILES.items():
        stripped[key] = [
            _strip_artifact_bands(
                pygame.image.load(os.path.join(directory, name)).convert_alpha()
            )
            for name in filenames
        ]

    strict_alpha = any(
        _has_alpha_noise(image)
        for images in stripped.values()
        for image in images
    )

    frames = {}
    for key, images in stripped.items():
        loaded = [
            _normalize_frame(image, target_height, strict_alpha)
            for image in images
        ]
        frames[key] = _compose_on_canvas(loaded, target_height)
    return frames


# --------------------------------------------------------------------------- #
# Sprite animasi
# --------------------------------------------------------------------------- #
class AnimatedSprite:
    """Karakter 2D dengan state idle/walk dan 4 arah hadap.

    Pemakaian:
        sprite.update_direction(dx, dy)   # dipanggil saat movement
        sprite.update(dt, moving)         # dipanggil tiap frame
        sprite.current_image              # surface siap blit
    """

    def __init__(self, directory, target_height=None, frame_duration=None):
        self.target_height = target_height or config.CHARACTER_HEIGHT
        self.frame_duration = (
            frame_duration if frame_duration is not None
            else config.WALK_FRAME_DURATION
        )

        self.frames = _load_animation_frames(directory, self.target_height)

        self.direction = DEFAULT_DIRECTION
        self.state = AnimationState.IDLE
        self.frame_index = 0
        self.frame_timer = 0.0
        self.moving = False

    # ------------------------------------------------------------------ #
    # Arah hadap
    # ------------------------------------------------------------------ #
    def update_direction(self, dx, dy):
        """Simpan arah hadap terakhir dari vektor movement.

        Arah hanya berubah kalau ada delta valid, sehingga saat berhenti
        karakter tetap menghadap arah terakhirnya.
        """
        direction = direction_from_delta(dx, dy)
        if direction is not None:
            self.direction = direction
        return self.direction

    def set_direction(self, direction):
        self.direction = direction

    # ------------------------------------------------------------------ #
    # State animasi
    # ------------------------------------------------------------------ #
    def update_state(self, moving):
        """Pindah state otomatis: idle saat diam, walk saat bergerak."""
        if moving:
            self.play_walk_animation()
        else:
            self.play_idle_animation()
        self.moving = bool(moving)

    def play_idle_animation(self):
        """Diam: satu frame sesuai arah terakhir."""
        self.state = AnimationState.IDLE
        self.frame_index = 0
        self.frame_timer = 0.0

    def play_walk_animation(self):
        """Berjalan: 4 frame berputar tanpa henti selama bergerak."""
        if self.state != AnimationState.WALK:
            self.state = AnimationState.WALK
            self.frame_index = 0
            self.frame_timer = 0.0

    # ------------------------------------------------------------------ #
    # Timer frame
    # ------------------------------------------------------------------ #
    def update_animation(self, dt):
        """Majukan frame walk; animasi idle bersifat statis."""
        if self.state != AnimationState.WALK:
            return

        total = len(self.frames[(self.state, self.direction)])
        if total <= 1:
            return

        self.frame_timer += dt
        while self.frame_timer >= self.frame_duration:
            self.frame_timer -= self.frame_duration
            self.frame_index = (self.frame_index + 1) % total

    def update(self, dt, moving):
        """Entry point per frame: update state lalu majukan animasi."""
        self.update_state(moving)
        self.update_animation(dt)

    # ------------------------------------------------------------------ #
    # Query untuk rendering
    # ------------------------------------------------------------------ #
    @property
    def current_image(self):
        """Surface frame yang sedang aktif (siap blit, ukuran tetap)."""
        sequence = self.frames[(self.state, self.direction)]
        return sequence[self.frame_index % len(sequence)]

    @property
    def size(self):
        return self.current_image.get_size()
