"""Modul NPC Squad: Mengelola data tim NPC, stat per individu, dan rotasi Tag-Team."""

import os
from typing import Dict, List, Any, Optional
import pygame

from ..core import config


# Pemetaan nama & warna ikon untuk anggota tim NPC
CLASS_DISPLAY_NAMES = {
    "warrior": "Warrior (Oyen - Pendekar)",
    "ranger": "Ranger (Kuro - Pemanah)",
    "mage": "Mage (Shiro - Penyihir)",
    "tank": "Tank (Penahan)",
    "assassin": "Assassin (Shadow - Penyelinap)",
}

DEFAULT_NAMES = ["Oyen", "Kuro", "Shiro", "Shadow"]


class NPCMember:
    """Representasi satu individu petarung NPC dalam squad."""

    def __init__(
        self,
        name: str,
        char_type: str = "warrior",
        max_hp: int = 100,
        potions: int = 2,
        atk_bonus: int = 0,
        def_bonus: int = 0,
        eval_profile: str = "BALANCED",
        current_hp: Optional[int] = None,
        allow_boss_assets: bool = False,
    ):
        self.name = name
        self.char_type = char_type
        self.max_hp = max_hp
        self.current_hp = max_hp if current_hp is None else current_hp
        self.potions = potions
        self.atk_bonus = atk_bonus
        self.def_bonus = def_bonus
        self.eval_profile = eval_profile
        self.allow_boss_assets = allow_boss_assets
        self.portrait: Optional[pygame.Surface] = None
        self.battle_sprite: Optional[pygame.Surface] = None
        self._load_portrait()
        self._load_battle_sprite()

    def _load_portrait(self):
        # 1. Prioritaskan aset spesifik berdasarkan nama NPC (misal: portrait_shiro.png; portrait_kage hanya untuk Boss)
        first_name = self.name.split()[0].lower() if self.name else ""
        if first_name and (self.allow_boss_assets or first_name not in ("kage", "boss")):
            name_path = os.path.join(config.ASSET_DIR, "portraits", f"portrait_{first_name}.png")
            if os.path.exists(name_path):
                try:
                    img = pygame.image.load(name_path).convert_alpha()
                    self.portrait = pygame.transform.smoothscale(img, (96, 96))
                    return
                except Exception:
                    pass

        # 2. Fallback ke tipe role karakter (misal: portrait_ranger.png, portrait_assassin.png)
        portrait_map = {
            "warrior": "portrait_warrior.png",
            "tank": "portrait_warrior.png",
            "assassin": "portrait_assassin.png",
            "mage": "portrait_mage.png",
            "ranger": "portrait_ranger.png",
        }
        filename = portrait_map.get(self.char_type, f"portrait_{self.char_type}.png")
        path = os.path.join(config.ASSET_DIR, "portraits", filename)
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                self.portrait = pygame.transform.smoothscale(img, (96, 96))
            except Exception:
                self.portrait = None

    def _load_battle_sprite(self):
        # 1. Prioritaskan aset spesifik berdasarkan nama NPC (battle_kage.png khusus Boss Menara Kuno)
        first_name = self.name.split()[0].lower() if self.name else ""
        if first_name and (self.allow_boss_assets or first_name not in ("kage", "boss")):
            name_path = os.path.join(config.ASSET_DIR, "battle_sprites", f"battle_{first_name}.png")
            if os.path.exists(name_path):
                try:
                    self.battle_sprite = pygame.image.load(name_path).convert_alpha()
                    return
                except Exception:
                    pass

        # 2. Fallback ke tipe role karakter (misal: battle_ranger.png)
        filename = f"battle_{self.char_type}.png"
        path = os.path.join(config.ASSET_DIR, "battle_sprites", filename)
        if not os.path.exists(path):
            path = os.path.join(config.ASSET_DIR, "battle_sprites", "battle_warrior.png")
        if os.path.exists(path):
            try:
                self.battle_sprite = pygame.image.load(path).convert_alpha()
            except Exception:
                self.battle_sprite = None

    def is_alive(self) -> bool:
        return self.current_hp > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "char_type": self.char_type,
            "hp": self.max_hp,
            "current_hp": self.current_hp,
            "potions": self.potions,
            "atk_bonus": self.atk_bonus,
            "def_bonus": self.def_bonus,
            "eval_profile": self.eval_profile,
        }


class NPCSquad:
    """Manajer tim petarung NPC yang mengatur frontline aktif dan cadangan (bench)."""

    def __init__(self, members: Optional[List[NPCMember]] = None):
        self.members: List[NPCMember] = members or []
        self.active_index: int = 0

    @classmethod
    def from_config(cls, cfg: Dict[str, Any]) -> "NPCSquad":
        """Membangun NPCSquad dari output dictionary CSP / Local Search."""
        raw_members = cfg.get("members", [])
        members = []
        for i, rm in enumerate(raw_members):
            ctype = rm.get("char_type", "warrior")
            if ctype == "warrior":
                base_name = "Oyen"
            elif ctype == "ranger":
                base_name = "Kuro"
            elif ctype == "mage":
                base_name = "Shiro"
            elif ctype == "tank":
                base_name = "Oyen"
            elif ctype == "assassin":
                base_name = "Shadow"
            else:
                base_name = DEFAULT_NAMES[i % len(DEFAULT_NAMES)]
            member_name = f"{base_name} the {ctype.capitalize()}"
            member = NPCMember(
                name=member_name,
                char_type=ctype,
                max_hp=rm.get("hp", 100),
                potions=rm.get("potions", 2),
                atk_bonus=rm.get("atk_bonus", 0),
                def_bonus=rm.get("def_bonus", 0),
                eval_profile=rm.get("eval_profile", "BALANCED"),
            )
            members.append(member)

        if not members:
            # Fallback 1 default member
            members = [NPCMember("Oyen the Warrior", "warrior", 100, 2, 0, 0, "BALANCED")]

        return cls(members)

    @classmethod
    def create_boss_squad(
        cls,
        target_difficulty: Optional[float] = None,
        player_context: Optional[Dict[str, Any]] = None,
        randomize: bool = False,
    ) -> "NPCSquad":
        """Membangun squad Boss Kage (Kucing Hitam Menara Kuno / Abandoned Tower)."""
        import random

        if target_difficulty is None and player_context is None:
            scale = 1.0
            boss_potions = 3
            m1_pot = 1
            m2_pot = 2
            m1_prof = "BALANCED"
            m2_prof = "BALANCED"
        else:
            td = float(target_difficulty if target_difficulty is not None else 0.65)
            pctx = player_context or {}
            patk = pctx.get("player_atk_bonus", 0)
            pdef = pctx.get("player_def_bonus", 0)
            # Skala kesulitan: 0.20 -> ~0.65x, 0.55 -> ~1.0x, 0.90 -> ~1.45x + penyesuaian item player
            item_boost = min(0.50, patk * 0.015 + pdef * 0.012) if td >= 0.45 else 0.0
            scale = max(0.65, min(1.85, 0.95 + (td - 0.55) * 1.25 + item_boost))
            boss_potions = 2 if td < 0.40 else (3 if td < 0.72 else 4)
            m1_pot = 1 if td < 0.70 else 2
            m2_pot = 1 if td < 0.45 else (2 if td < 0.75 else 3)
            profiles = ["BALANCED", "AGGRESSIVE", "DEFENSIVE"]
            m1_prof = random.choice(profiles) if randomize else ("AGGRESSIVE" if td >= 0.70 else "BALANCED")
            m2_prof = random.choice(profiles) if randomize else ("DEFENSIVE" if td >= 0.65 else "BALANCED")

        boss = NPCMember(
            name="Kage the Shadow Lord",
            char_type="assassin",
            max_hp=int(round(160 * scale)),
            potions=boss_potions,
            atk_bonus=int(round(8 * scale)),
            def_bonus=int(round(5 * scale)),
            eval_profile="AGGRESSIVE",
            allow_boss_assets=True,
        )
        minion_1 = NPCMember(
            name="Shadow Ranger",
            char_type="ranger",
            max_hp=int(round(80 * scale)),
            potions=m1_pot,
            atk_bonus=int(round(4 * scale)),
            def_bonus=int(round(2 * scale)),
            eval_profile=m1_prof,
        )
        minion_2 = NPCMember(
            name="Shadow Mage",
            char_type="mage",
            max_hp=int(round(80 * scale)),
            potions=m2_pot,
            atk_bonus=int(round(5 * scale)),
            def_bonus=int(round(1 * scale)),
            eval_profile=m2_prof,
        )
        return cls([boss, minion_1, minion_2])

    def reset(self):
        """Memulihkan seluruh anggota squad ke kondisi awal (HP maksimal & frontline awal)."""
        self.active_index = 0
        for m in self.members:
            m.current_hp = m.max_hp

    def get_active_member(self) -> Optional[NPCMember]:
        if 0 <= self.active_index < len(self.members):
            return self.members[self.active_index]
        return None

    def has_next(self) -> bool:
        """Cek apakah masih ada anggota cadangan berikutnya yang masih hidup."""
        for idx in range(self.active_index + 1, len(self.members)):
            if self.members[idx].is_alive():
                return True
        return False

    def advance_to_next(self) -> Optional[NPCMember]:
        """Ganti petarung frontline aktif ke anggota cadangan berikutnya yang masih hidup."""
        for idx in range(self.active_index + 1, len(self.members)):
            if self.members[idx].is_alive():
                self.active_index = idx
                return self.members[idx]
        return None

    def has_alive_members(self) -> bool:
        return any(m.is_alive() for m in self.members)

    def get_remaining_count(self) -> int:
        return sum(1 for m in self.members if m.is_alive())

    def get_total_count(self) -> int:
        return len(self.members)
