"""Modul Battle VFX: Animasi prosedural (tweening & partikel) untuk pertarungan turn-based.

Memanfaatkan aset item yang ada (item_sword, item_shield, health_potion):
1. Serangan (Attack & Heavy): Pedang meluncur cepat (lerp) dan berputar (rotate) ke arah target + efek guncangan (hit shake).
2. Bertahan (Defend): Perisai melayang di depan karakter dengan efek denyut lembut (pulse).
3. Ramuan (Potion): Botol ramuan muncul di atas kepala, miring menuang + angka HP hijau melayang ke atas (+HP).
4. Reaksi Terkena Serangan (Hit Flash/Shake): Karakter bergetar singkat saat menerima damage.
"""

import math
import os
import pygame
from typing import List, Dict, Any, Optional, Tuple

from . import config

SRCALPHA = getattr(pygame, "SRCALPHA", 0x00010000)


class BattleVFXManager:
    """Manajer efek visual pertempuran dengan programmatic tweening."""

    def __init__(self, fonts: Dict[str, pygame.font.Font]):
        self.fonts = fonts
        self.animations: List[Dict[str, Any]] = []

        # Muat ikon aset untuk VFX
        self.sword_img: Optional[pygame.Surface] = None
        self.shield_img: Optional[pygame.Surface] = None
        self.potion_img: Optional[pygame.Surface] = None
        self._load_sprites()

        # Shake offset untuk karakter: "PLAYER": (ox, oy), "NPC": (ox, oy)
        self.shake_offsets = {"PLAYER": (0, 0), "NPC": (0, 0)}
        self.shake_timers = {"PLAYER": 0.0, "NPC": 0.0}

    def _load_sprites(self):
        items_dir = os.path.join(config.ASSET_DIR, "items")
        try:
            sw_path = os.path.join(items_dir, "item_sword.png")
            if os.path.exists(sw_path):
                raw = pygame.image.load(sw_path).convert_alpha()
                self.sword_img = pygame.transform.smoothscale(raw, (44, 44))

            sh_path = os.path.join(items_dir, "item_shield.png")
            if os.path.exists(sh_path):
                raw = pygame.image.load(sh_path).convert_alpha()
                self.shield_img = pygame.transform.smoothscale(raw, (48, 48))

            pot_path = os.path.join(items_dir, "health_potion.png")
            if os.path.exists(pot_path):
                raw = pygame.image.load(pot_path).convert_alpha()
                self.potion_img = pygame.transform.smoothscale(raw, (40, 40))
        except Exception:
            pass

    # ----------------------------------------------------------------------- #
    # Pemicu Animasi
    # ----------------------------------------------------------------------- #
    def trigger_attack(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int], is_heavy: bool = False, recipient: str = "NPC"):
        """Memicu pedang terbang ke target + getar saat tiba."""
        duration = 0.32 if not is_heavy else 0.40
        self.animations.append({
            "type": "SWORD_SLASH",
            "from_pos": from_pos,
            "to_pos": to_pos,
            "timer": 0.0,
            "duration": duration,
            "is_heavy": is_heavy,
            "recipient": recipient,
            "hit_triggered": False,
        })

    def trigger_defend(self, pos: Tuple[int, int]):
        """Memicu perisai melayang dengan pulsing aura."""
        self.animations.append({
            "type": "SHIELD_AURA",
            "pos": pos,
            "timer": 0.0,
            "duration": 0.60,
        })

    def trigger_potion(self, pos: Tuple[int, int], heal_val: int = 30):
        """Memicu botol menuang ramuan dan angka +HP hijau melayang."""
        self.animations.append({
            "type": "POTION_HEAL",
            "pos": pos,
            "timer": 0.0,
            "duration": 0.75,
            "heal_val": heal_val,
        })

    def trigger_hit_shake(self, who: str, intensity: float = 8.0, duration: float = 0.18):
        """Memicu getaran karakter saat terkena pukulan."""
        self.shake_timers[who] = duration

    # ----------------------------------------------------------------------- #
    # Update Siklus
    # ----------------------------------------------------------------------- #
    def update(self, dt: float):
        # Update shake karakter
        for who in ["PLAYER", "NPC"]:
            if self.shake_timers[who] > 0.0:
                self.shake_timers[who] -= dt
                if self.shake_timers[who] <= 0.0:
                    self.shake_offsets[who] = (0, 0)
                else:
                    # Guncangan horizontal acak
                    prog = self.shake_timers[who] / 0.18
                    ox = int(math.sin(pygame.time.get_ticks() * 0.08) * (7.0 * prog))
                    self.shake_offsets[who] = (ox, 0)

        # Update animasi aktif
        remains = []
        for anim in self.animations:
            anim["timer"] += dt
            t = anim["timer"]
            dur = anim["duration"]

            # Trigger hit shake saat pedang tiba di tengah jalan (>= 75% durasi)
            if anim["type"] == "SWORD_SLASH" and not anim["hit_triggered"]:
                if t >= dur * 0.75:
                    anim["hit_triggered"] = True
                    recip = anim.get("recipient", "NPC")
                    heavy = anim.get("is_heavy", False)
                    self.trigger_hit_shake(recip, intensity=10.0 if heavy else 6.0)

            if t < dur:
                remains.append(anim)
        self.animations = remains

    def get_shake_offset(self, who: str) -> Tuple[int, int]:
        return self.shake_offsets.get(who, (0, 0))

    # ----------------------------------------------------------------------- #
    # Rendering VFX
    # ----------------------------------------------------------------------- #
    def draw(self, surface: pygame.Surface):
        for anim in self.animations:
            atype = anim["type"]
            t = anim["timer"]
            dur = anim["duration"]
            prog = min(1.0, max(0.0, t / dur))

            if atype == "SWORD_SLASH":
                self._draw_sword_slash(surface, anim, prog)
            elif atype == "SHIELD_AURA":
                self._draw_shield_aura(surface, anim, prog)
            elif atype == "POTION_HEAL":
                self._draw_potion_heal(surface, anim, prog)

    def _draw_sword_slash(self, surface: pygame.Surface, anim: Dict[str, Any], prog: float):
        if not self.sword_img:
            return
        x1, y1 = anim["from_pos"]
        x2, y2 = anim["to_pos"]

        # Easing cubic-out untuk luncuran pedang
        ease = 1.0 - math.pow(1.0 - prog, 3)
        cur_x = x1 + (x2 - x1) * ease
        cur_y = y1 + (y2 - y1) * ease

        # Sudut rotasi berputar
        base_angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        rot_angle = base_angle + prog * 180.0
        if anim["is_heavy"]:
            rot_angle += prog * 180.0

        rotated = pygame.transform.rotate(self.sword_img, -rot_angle)

        # Jejak kilauan (sword trail)
        trail_surf = pygame.Surface((32, 32), SRCALPHA)
        alpha = int(180 * (1.0 - prog))
        pygame.draw.circle(trail_surf, (255, 220, 100, alpha), (16, 16), 12)
        surface.blit(trail_surf, trail_surf.get_rect(center=(int(cur_x), int(cur_y))))

        rect = rotated.get_rect(center=(int(cur_x), int(cur_y)))
        surface.blit(rotated, rect)

    def _draw_shield_aura(self, surface: pygame.Surface, anim: Dict[str, Any], prog: float):
        if not self.shield_img:
            return
        cx, cy = anim["pos"]

        # Pulse denyut
        pulse = 1.0 + 0.15 * math.sin(prog * math.pi * 3)
        alpha = int(240 * (1.0 - prog))

        # Aura cahaya pelindung biru
        aura_r = int(36 * pulse)
        aura_surf = pygame.Surface((aura_r * 2 + 10, aura_r * 2 + 10), SRCALPHA)
        pygame.draw.circle(aura_surf, (80, 170, 255, int(alpha * 0.45)), (aura_r + 5, aura_r + 5), aura_r)
        pygame.draw.circle(aura_surf, (150, 220, 255, int(alpha * 0.75)), (aura_r + 5, aura_r + 5), aura_r, 2)
        surface.blit(aura_surf, aura_surf.get_rect(center=(cx, cy)))

        scaled = pygame.transform.smoothscale(self.shield_img, (int(48 * pulse), int(48 * pulse)))
        surface.blit(scaled, scaled.get_rect(center=(cx, cy)))

    def _draw_potion_heal(self, surface: pygame.Surface, anim: Dict[str, Any], prog: float):
        cx, cy = anim["pos"]

        # 1. Botol ramuan miring
        if self.potion_img:
            # Botol melayang di atas kepala dan miring 35 derajat
            tilt_angle = -35.0 * math.sin(prog * math.pi)
            rotated_pot = pygame.transform.rotate(self.potion_img, tilt_angle)
            pot_y = cy - 40 - int(math.sin(prog * math.pi) * 8)
            surface.blit(rotated_pot, rotated_pot.get_rect(center=(cx, pot_y)))

        # 2. Angka +HP melayang ke atas
        float_y = cy - 20 - int(prog * 45.0)
        alpha = int(255 * (1.0 - prog * 0.7))
        font_bubble = self.fonts.get("bubble", self.fonts["sm"])

        heal_text = f"+{anim.get('heal_val', 30)} HP"
        txt_surf = font_bubble.render(heal_text, True, (60, 235, 120))
        txt_alpha = txt_surf.copy()
        txt_alpha.set_alpha(alpha)

        # Latar belakang teks pemulihan
        bg_card = pygame.Surface((txt_surf.get_width() + 12, txt_surf.get_height() + 6), SRCALPHA)
        bg_card.fill((15, 25, 20, int(180 * (alpha / 255.0))))
        pygame.draw.rect(bg_card, (80, 230, 120, alpha), bg_card.get_rect(), 1, border_radius=4)

        surface.blit(bg_card, bg_card.get_rect(center=(cx, int(float_y))))
        surface.blit(txt_alpha, txt_alpha.get_rect(center=(cx, int(float_y))))
