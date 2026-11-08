"""Battle Arena Background (16-bit JRPG Meadow Landscape).

Latar belakang arena pertempuran (Mode Duel Turn-Based):
- Tema '16-bit JRPG Sunlit Green Meadow': Padang rumput hijau berbukit bergaya Studio Ghibli,
  awan kapas putih di langit biru cerah, bunga-bunga liar, dan pelataran tanah melingkar untuk duel.
- Kontras tinggi dan keterbacaan jernih (high readability) untuk sprite karakter petarung,
  bar status, kartu cadangan tim lawan, serta log duel.
- Sistem pre-render cache berkinerja tinggi (tanpa beban komputasi per-frame).
"""

import os
import pygame
from game.core import config


class BattleArenaBackground:
    def __init__(self):
        self.cached_surface = None
        self.cached_size = (0, 0)
        self.blur_radius = 0

        # Path file gambar background arena battle (Pixel Art Forest Landscape)
        self.bg_path = os.path.join(config.ASSET_DIR, "battle_bg_forest.png")
        if not os.path.exists(self.bg_path):
            self.bg_path = os.path.join(config.ASSET_DIR, "battle_bg_meadow.jpg")
        self.raw_bg = None
        if os.path.exists(self.bg_path):
            self.raw_bg = pygame.image.load(self.bg_path).convert()

    def _render_background(self, arena_w, h):
        """Memproses gambar latar: penskalaan mulus, center crop, soft blur & vignette."""
        if self.raw_bg is None:
            # Fallback jika gambar tidak ditemukan
            surf = pygame.Surface((arena_w, h))
            surf.fill((45, 35, 30))
            return surf

        # Skala proporsional mengisi arena_w x h
        scale = max(arena_w / float(self.raw_bg.get_width()), h / float(self.raw_bg.get_height()))
        nw = int(round(self.raw_bg.get_width() * scale))
        nh = int(round(self.raw_bg.get_height() * scale))
        scaled = pygame.transform.smoothscale(self.raw_bg, (nw, nh))

        # Center crop
        cx = (nw - arena_w) // 2
        cy = (nh - h) // 2
        cropped = scaled.subsurface((cx, cy, arena_w, h)).copy()

        # Terapkan soft blur jika radius > 0
        if self.blur_radius > 0:
            result = pygame.transform.gaussian_blur(cropped, self.blur_radius)
        else:
            result = cropped

        # Lapisan vignette & ambient darkening lembut untuk kejelasan teks & UI
        vignette = pygame.Surface((arena_w, h), pygame.SRCALPHA)
        # Penggelapan atas untuk bar judul dan kartu cadangan
        for y in range(100):
            alpha = int(45 * (1.0 - y / 100.0))
            pygame.draw.line(vignette, (15, 20, 30, alpha), (0, y), (arena_w, y))
        # Penggelapan bawah untuk dock tombol aksi dan battle log
        for y in range(h - 150, h):
            alpha = int(60 * ((y - (h - 150)) / 150.0))
            pygame.draw.line(vignette, (15, 20, 30, alpha), (0, y), (arena_w, y))
        result.blit(vignette, (0, 0))

        return result

    def update(self, dt=0.0, wind_timer=0.0, arena_w=980, h=800):
        """Latar statis berkinerja tinggi, tidak memerlukan update per frame."""
        pass

    def draw(self, surface, x_offset, arena_w, h, wind_timer=0.0, water_frame_idx=0):
        """Menggambar latar belakang arena yang sudah di-cache secara instan."""
        if self.cached_surface is None or self.cached_size != (arena_w, h):
            self.cached_surface = self._render_background(arena_w, h)
            self.cached_size = (arena_w, h)

        surface.blit(self.cached_surface, (x_offset, 0))
