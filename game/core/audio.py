"""Audio and Sound Manager for Bakekok.

Mengelola pemutaran musik latar (BGM) dan efek suara (SFX) seperti:
- Langkah kaki (dirt & grass footsteps)
- Prompt peti ([E] Buka Peti pop-up chime)
- Kemenangan/item didapat dari peti (win fanfare)
"""

import os
import random
import time
import pygame
from game.core import config


class AudioManager:
    def __init__(self):
        self.enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.enabled = True
        except Exception as e:
            # Fallback aman jika tidak ada audio device (misal headless test)
            self.enabled = False

        self.sounds_dir = os.path.join(config.ASSET_DIR, "sounds")

        # Channels terpisah agar langkah kaki dan SFX tidak saling menimpa
        self.footstep_channel = None
        self.sfx_channel = None
        if self.enabled:
            try:
                self.footstep_channel = pygame.mixer.Channel(1)
                self.sfx_channel = pygame.mixer.Channel(2)
            except Exception:
                pass

        # Cooldown pergerakan langkah
        self.last_step_time = 0.0
        self.step_cooldown = 0.18

        # Cache SFX
        self.dirt_sounds = []
        self.grass_sounds = []
        self.stone_sounds = []
        self.win_sound = None
        self.chest_prompt_sound = None
        self.reroll_sound = None
        self.card_reveal_sound = None

        self._load_sounds()

    def _load_sound_file(self, *filenames):
        """Mencoba memuat salah satu berkas dari kandidat nama yang diberikan."""
        if not self.enabled:
            return None
        for fn in filenames:
            p = os.path.join(self.sounds_dir, fn)
            if os.path.exists(p):
                try:
                    snd = pygame.mixer.Sound(p)
                    return snd
                except Exception as e:
                    pass
        return None

    def _load_sounds(self):
        if not self.enabled:
            return

        # 1. Suara langkah di tanah (dirt)
        for fn in ["dirt1.wav", "dirt2.wav", "dirt4.wav", "dirt.wav"]:
            snd = self._load_sound_file(fn)
            if snd:
                snd.set_volume(0.38)
                self.dirt_sounds.append(snd)

        # 2. Suara langkah di rumput (grass)
        for fn in ["grass1.wav", "grass2.wav", "grass3.wav", "grass.wav"]:
            snd = self._load_sound_file(fn)
            if snd:
                snd.set_volume(0.32)
                self.grass_sounds.append(snd)

        # 3. Suara langkah di batu/jembatan kayu (stone)
        for fn in ["stone1.wav", "stone2.wav", "stone3.wav"]:
            snd = self._load_sound_file(fn)
            if snd:
                snd.set_volume(0.35)
                self.stone_sounds.append(snd)

        # 4. Suara menang / item didapat dari peti (12_win.mp3 / 15_win.mp3)
        self.win_sound = self._load_sound_file("12_win.mp3", "15_win.mp3")
        if self.win_sound:
            self.win_sound.set_volume(0.55)

        # 5. Suara prompt peti muncul (PURBLES_SHAKEBUTTON / PURBLES_SHAKERBUTTON)
        self.chest_prompt_sound = self._load_sound_file(
            "PURBLES_SHAKEBUTTON.wav", "PURBLES_SHAKERBUTTON.wav"
        )
        if self.chest_prompt_sound:
            self.chest_prompt_sound.set_volume(0.45)

        # 6. Suara acak ulang / reroll skuad (shuffle efek) & kemunculan kartu skuad
        self.reroll_sound = self._load_sound_file("PURBLES_SHAKERBUTTON.wav", "PURBLES_SHAKEBUTTON.wav")
        if self.reroll_sound:
            self.reroll_sound.set_volume(0.40)

        self.card_reveal_sound = self._load_sound_file("PURBLES_LEFTARROWBUTTON.wav")
        if self.card_reveal_sound:
            self.card_reveal_sound.set_volume(0.24)

    def play_bgm(self, loop=-1, volume=0.30):
        """Memutar lagu latar (BGM) Rise.mp3 / Rise.mpga."""
        if not self.enabled:
            return
        bgm_candidates = ["Rise.mp3", "Rise.mpga"]
        for fn in bgm_candidates:
            p = os.path.join(self.sounds_dir, fn)
            if os.path.exists(p):
                try:
                    pygame.mixer.music.load(p)
                    pygame.mixer.music.set_volume(volume)
                    pygame.mixer.music.play(loop)
                    return
                except Exception as e:
                    pass

    def set_bgm_volume(self, volume=0.20):
        """Mengatur tingkat volume BGM (0.0 sampai 1.0)."""
        if self.enabled:
            try:
                pygame.mixer.music.set_volume(volume)
            except Exception:
                pass

    def stop_bgm(self):
        if self.enabled:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def play_step(self, surface_type="grass"):
        """Memutar suara langkah kaki sesuai tipe permukaan (dirt/grass/bridge)."""
        if not self.enabled:
            return
        now = time.time()
        if now - self.last_step_time < self.step_cooldown:
            return
        self.last_step_time = now

        snd = None
        if surface_type == "dirt" and self.dirt_sounds:
            snd = random.choice(self.dirt_sounds)
        elif surface_type in ("bridge", "stone") and self.stone_sounds:
            snd = random.choice(self.stone_sounds)
        elif self.grass_sounds:
            snd = random.choice(self.grass_sounds)
        elif self.dirt_sounds:
            snd = random.choice(self.dirt_sounds)

        if snd:
            if self.footstep_channel:
                self.footstep_channel.play(snd)
            else:
                snd.play()

    def _play_sfx(self, sound):
        """Putar satu SFX via channel khusus agar tidak menimpa suara langkah kaki."""
        if not self.enabled or not sound:
            return
        if self.sfx_channel:
            self.sfx_channel.play(sound)
        else:
            sound.play()

    def play_chest_prompt(self):
        """Memutar suara denting saat prompt [E] Buka Peti muncul."""
        self._play_sfx(self.chest_prompt_sound)

    def play_chest_win(self):
        """Memutar musik kemenangan/fanfare saat item didapat dari peti harta."""
        self._play_sfx(self.win_sound)

    def play_reroll(self):
        """Memutar efek suara kocokan/shuffle saat mengacak ulang skuad Pre-Battle."""
        self._play_sfx(self.reroll_sound)

    def play_card_reveal(self):
        """Memutar efek suara pop halus saat kartu anggota skuad muncul."""
        self._play_sfx(self.card_reveal_sound)

