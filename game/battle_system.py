"""BattleSystem: Mengatur jalannya duel turn-based antara Player dan NPC.
"""

import time
from typing import List, Dict, Any, Optional

from .battle_ai import (
    BattleState,
    BattleAISolver,
    ACTION_ATTACK,
    ACTION_HEAVY,
    ACTION_DEFEND,
    ACTION_POTION,
    EVAL_FUNCTIONS,
    HEAVY_COOLDOWN_TURNS,
    MAX_POTIONS,
)
from .npc_squad import NPCSquad, NPCMember


# Pemetaan aksi -> teks pendek yang ditampilkan di atas karakter
ACTION_DISPLAY_TEXT = {
    ACTION_ATTACK:  "Menyerang!",
    ACTION_HEAVY:   "Serangan Kuat!!",
    ACTION_DEFEND:  "Bertahan!",
    ACTION_POTION:  "Minum Potion!",
}


class BattleSystem:
    def __init__(self):
        self.state = BattleState()
        self.ai_solver = BattleAISolver()

        # Konfigurasi AI Default untuk Duel
        self.algorithm = "ALPHA_BETA"  # MINIMAX, ALPHA_BETA, EXPECTIMAX
        self.eval_mode = "BALANCED"    # BALANCED, AGGRESSIVE, DEFENSIVE
        self.depth = 4
        self.move_ordering_mode = "HEURISTIC"  # OFF, HEURISTIC, REVERSED
        self.record_tree = True  # Apakah merekam pohon keputusan untuk visualisasi

        # Squad NPC
        self.squad: Optional[NPCSquad] = None

        # Riwayat pertempuran (log)
        self.battle_logs: List[str] = []
        self.last_ai_stats: Dict[str, Any] = {}
        self.is_finished = False
        self.winner: Optional[str] = None  # "PLAYER", "NPC", "DRAW"

        # --- Floating Action Text (teks aksi melayang di atas karakter) ---
        # Format: {"text": str, "timer": float, "color": tuple}
        self.player_action_text: Optional[Dict] = None
        self.npc_action_text: Optional[Dict] = None
        self.ACTION_TEXT_DURATION = 2.5  # Detik teks ditampilkan
        # Callback notifikasi aksi pertempuran untuk modul visual VFX
        self.on_action_callback = None
        # Callback saat NPC berganti (Tag-in summon animation)
        self.on_tag_in = None
        self.is_locked = False
        self.player: Any = None
        self.last_second_wind_heal: int = 45
        self.last_loot: Optional[Dict[str, Any]] = None

        self.reset()

    def reset(self):
        self.squad = NPCSquad([NPCMember("Oyen the Warrior", "warrior", 100, 2, 0, 0, "BALANCED")])
        self.eval_mode = "BALANCED"
        self.state = BattleState(
            player_hp=100,
            npc_hp=100,
            player_potions=2,
            npc_potions=2,
            player_defending=False,
            npc_defending=False,
            is_npc_turn=False,  # Player jalan pertama
            player_heavy_cd=0,
            npc_heavy_cd=0,
        )
        self.battle_logs = ["Duel dimulai! Player berhadapan dengan Kucing Bolu (NPC)!"]
        self.last_ai_stats = {}
        if hasattr(self.ai_solver, "last_tree"):
            self.ai_solver.last_tree = None
        self.is_finished = False
        self.is_locked = False
        self.winner = None
        self.player_action_text = None
        self.npc_action_text = None
        self.last_loot = None

    def _get_spoils_of_war(self, npc_member: Optional[NPCMember]) -> Dict[str, Any]:
        """Menghasilkan hadiah rampasan perang (Spoils of War) berdasarkan kelas NPC yang dikalahkan."""
        ctype = getattr(npc_member, "char_type", "warrior").lower() if npc_member else "warrior"
        if ctype == "warrior":
            return {
                "id": "sword_warrior",
                "image_key": "item_sword",
                "name": "Pedang Ksatria Oyen",
                "icon": "⚔️",
                "atk_bonus": 4,
                "def_bonus": 1,
                "potions": 0,
                "stat_text": "+4 ATK, +1 DEF",
                "desc": "Senjata rampasan dari Warrior. Kekuatan tebasan meningkat!",
                "color": (255, 175, 45),
            }
        elif ctype == "ranger":
            return {
                "id": "bow_ranger",
                "image_key": "item_bow",
                "name": "Busur Presisi Kuro",
                "icon": "🏹",
                "atk_bonus": 3,
                "def_bonus": 0,
                "potions": 1,
                "stat_text": "+3 ATK, +1 Ramuan Cadangan",
                "desc": "Busur lincah dari Ranger. Menembus pertahanan lawan!",
                "color": (50, 215, 100),
            }
        elif ctype == "assassin":
            return {
                "id": "dagger_assassin",
                "image_key": "item_dagger",
                "name": "Belati Bayangan Kage",
                "icon": "🗡️",
                "atk_bonus": 5,
                "def_bonus": 0,
                "potions": 0,
                "stat_text": "+5 ATK Lethal",
                "desc": "Belati beracun dari Assassin. Serangan kritis mematikan!",
                "color": (205, 75, 235),
            }
        elif ctype == "mage":
            return {
                "id": "staff_mage",
                "image_key": "mega_potion",
                "name": "Tongkat Sihir Shiro",
                "icon": "🔮",
                "atk_bonus": 3,
                "def_bonus": 2,
                "potions": 0,
                "stat_text": "+3 ATK, +2 DEF",
                "desc": "Pusaka magis dari Mage. Melindungi dan memperkuat sihir!",
                "color": (70, 175, 255),
            }
        else:
            return {
                "id": "shield_tank",
                "image_key": "item_shield",
                "name": "Perisai Tempur Kucing",
                "icon": "🛡️",
                "atk_bonus": 3,
                "def_bonus": 2,
                "potions": 0,
                "stat_text": "+3 ATK, +2 DEF",
                "desc": "Perisai baja penahan benturan musuh!",
                "color": (255, 215, 60),
            }

    def reset_with_squad(
        self,
        squad: NPCSquad,
        player_hp: int = 100,
        player_potions: int = 2,
        player_atk: int = 0,
        player_def: int = 0,
        player: Any = None,
    ):
        if player is not None:
            p_hp = getattr(player, "persistent_hp", player_hp)
            # Jika player HP <= 0 atau tersisa 10 akibat kalah duel sebelumnya, pulihkan penuh ke 100
            player_hp = 100 if p_hp <= 10 else p_hp
            player_potions = getattr(player, "persistent_potions", player_potions)
            player_atk = getattr(player, "atk_bonus", player_atk)
            player_def = getattr(player, "def_bonus", player_def)

        if hasattr(squad, "reset"):
            squad.reset()
        self.squad = squad
        self.player = player
        active = squad.get_active_member()
        npc_hp = active.max_hp if active else 100
        npc_pots = active.potions if active else 2
        npc_atk = active.atk_bonus if active else 0
        npc_def = active.def_bonus if active else 0
        self.eval_mode = active.eval_profile if active else "BALANCED"

        self.state = BattleState(
            player_hp=player_hp,
            npc_hp=npc_hp,
            player_potions=player_potions,
            npc_potions=npc_pots,
            player_defending=False,
            npc_defending=False,
            is_npc_turn=False,
            player_heavy_cd=0,
            npc_heavy_cd=0,
            player_atk_bonus=player_atk,
            npc_atk_bonus=npc_atk,
            player_def_bonus=player_def,
            npc_def_bonus=npc_def,
            player_max_hp=100,
            npc_max_hp=npc_hp,
        )

        name_str = active.name if active else "NPC"
        self.battle_logs = [f"Duel dimulai! Player berhadapan dengan {name_str}!"]
        self.last_ai_stats = {}
        if hasattr(self.ai_solver, "last_tree"):
            self.ai_solver.last_tree = None
        self.is_finished = False
        self.is_locked = False
        self.winner = None
        self.last_loot = None
        self.player_action_text = None
        self.npc_action_text = None

    def reset_with_config(
        self,
        config_dict: Dict[str, Any],
        player_hp: int = 100,
        player_potions: int = 2,
        player_atk: int = 0,
        player_def: int = 0,
    ):
        """Reset duel langsung dari dictionary konfigurasi CSP / Local Search."""
        squad = NPCSquad.from_config(config_dict)
        self.reset_with_squad(squad, player_hp, player_potions, player_atk, player_def)

    def update_ai_preview(self):
        """Kalkulasi ulang preview AI stats untuk tampilan debug overlay saat pengaturan diubah."""
        if self.is_finished or not self.last_ai_stats:
            return
        calc_state = self.state.clone()
        calc_state.is_npc_turn = True
        _, _, stats = self.ai_solver.select_best_action(
            calc_state,
            algorithm=self.algorithm,
            eval_mode=self.eval_mode,
            depth=self.depth,
            move_ordering_mode=self.move_ordering_mode,
            record_tree=self.record_tree,
        )
        self.last_ai_stats = stats

    def log(self, msg: str):
        self.battle_logs.append(msg)
        if len(self.battle_logs) > 8:
            self.battle_logs.pop(0)

    def _set_action_text(self, who: str, action: str, extra: str = ""):
        """Pasang teks aksi melayang di atas karakter."""
        base_text = ACTION_DISPLAY_TEXT.get(action, action)
        text = f"{base_text} {extra}".strip() if extra else base_text

        # Warna berdasarkan tipe aksi
        color_map = {
            ACTION_ATTACK:  (255, 200, 80),
            ACTION_HEAVY:   (255, 100, 50),
            ACTION_DEFEND:  (100, 180, 255),
            ACTION_POTION:  (80, 255, 120),
            "SECOND WIND!": (80, 255, 160),
            "TAG-IN!":      (255, 215, 60),
        }
        color = color_map.get(action, (255, 255, 255))

        entry = {"text": text, "timer": self.ACTION_TEXT_DURATION, "color": color}
        if who == "PLAYER":
            self.player_action_text = entry
        else:
            self.npc_action_text = entry

        if self.on_action_callback:
            self.on_action_callback(who, action)

    def update_action_texts(self, dt: float):
        """Update timer teks aksi melayang, hilangkan saat habis."""
        if self.player_action_text:
            self.player_action_text["timer"] -= dt
            if self.player_action_text["timer"] <= 0:
                self.player_action_text = None
        if self.npc_action_text:
            self.npc_action_text["timer"] -= dt
            if self.npc_action_text["timer"] <= 0:
                self.npc_action_text = None

    def execute_player_action(self, action: str) -> bool:
        """Mengeksekusi aksi giliran Player."""
        if self.is_finished or self.state.is_npc_turn or self.is_locked:
            return False

        legal = self.state.get_legal_actions()
        if action not in legal:
            return False

        # Hitung log sebelum perubahan
        old_npc_hp = self.state.npc_hp
        old_player_hp = self.state.player_hp

        # Terapkan aksi
        self.state = self.state.apply_action(action)

        if action == ACTION_ATTACK:
            dmg = old_npc_hp - self.state.npc_hp
            def_str = f" (DEF -{self.state.npc_def_bonus})" if self.state.npc_def_bonus > 0 else ""
            self.log(f"Player: Menyerang! Berhasil memberi {dmg} damage{def_str}.")
            self._set_action_text("PLAYER", ACTION_ATTACK, f"(-{dmg} HP)")
        elif action == ACTION_HEAVY:
            dmg = old_npc_hp - self.state.npc_hp
            def_str = f" (DEF -{self.state.npc_def_bonus})" if self.state.npc_def_bonus > 0 else ""
            self.log(f"Player: Serangan Kuat! Memberi {dmg} damage{def_str}!")
            self._set_action_text("PLAYER", ACTION_HEAVY, f"(-{dmg} HP)")
        elif action == ACTION_DEFEND:
            self.log("Player: Memasang kuda-kuda bertahan!")
            self._set_action_text("PLAYER", ACTION_DEFEND)
        elif action == ACTION_POTION:
            heal = self.state.player_hp - old_player_hp
            self.log(f"Player: Minum Potion (+{heal} HP).")
            self._set_action_text("PLAYER", ACTION_POTION, f"(+{heal} HP)")

        self._check_game_over()
        return True

    def execute_npc_turn(self) -> Optional[str]:
        """Mengeksekusi giliran NPC menggunakan AI Solver."""
        if self.is_finished or not self.state.is_npc_turn or self.is_locked:
            return None

        best_action, best_score, stats = self.ai_solver.select_best_action(
            self.state,
            algorithm=self.algorithm,
            eval_mode=self.eval_mode,
            depth=self.depth,
            move_ordering_mode=self.move_ordering_mode,
            record_tree=self.record_tree,
        )

        self.last_ai_stats = stats

        if not best_action:
            return None

        old_player_hp = self.state.player_hp
        old_npc_hp = self.state.npc_hp

        # Terapkan aksi AI
        self.state = self.state.apply_action(best_action)

        if best_action == ACTION_ATTACK:
            dmg = old_player_hp - self.state.player_hp
            def_str = f" (DEF -{self.state.player_def_bonus})" if self.state.player_def_bonus > 0 else ""
            self.log(f"NPC: Menyerang biasa! Memberi {dmg} damage{def_str}.")
            self._set_action_text("NPC", ACTION_ATTACK, f"(-{dmg} HP)")
        elif best_action == ACTION_HEAVY:
            dmg = old_player_hp - self.state.player_hp
            def_str = f" (DEF -{self.state.player_def_bonus})" if self.state.player_def_bonus > 0 else ""
            self.log(f"NPC: Serangan Telak! Memberi {dmg} damage{def_str}!")
            self._set_action_text("NPC", ACTION_HEAVY, f"(-{dmg} HP)")
        elif best_action == ACTION_DEFEND:
            self.log("NPC: Bersiap bertahan menangkis serangan!")
            self._set_action_text("NPC", ACTION_DEFEND)
        elif best_action == ACTION_POTION:
            heal = self.state.npc_hp - old_npc_hp
            self.log(f"NPC: Meminum Potion (+{heal} HP).")
            self._set_action_text("NPC", ACTION_POTION, f"(+{heal} HP)")

        self._check_game_over()
        return best_action

    def _check_game_over(self):
        # 1. Jika NPC tumbang tetapi masih ada anggota cadangan di squad
        if self.state.npc_hp <= 0 and self.squad and self.squad.has_next():
            active = self.squad.get_active_member()
            if active:
                active.current_hp = 0
            next_npc = self.squad.advance_to_next()
            if next_npc:
                # Opsi A: Second Wind / Tag-In Reward untuk Player
                heal_amount = min(45, self.state.player_max_hp - self.state.player_hp)
                self.state.player_hp += heal_amount
                self.state.player_potions = min(MAX_POTIONS, self.state.player_potions + 1)
                self.state.player_heavy_cd = 0
                self.last_second_wind_heal = heal_amount

                # Sistem Rampasan Perang (Spoils of War): Dapatkan item dari musuh yang tumbang!
                loot = self._get_spoils_of_war(active)
                self.state.player_atk_bonus += loot["atk_bonus"]
                self.state.player_def_bonus += loot["def_bonus"]
                if loot.get("potions", 0) > 0:
                    self.state.player_potions = min(MAX_POTIONS, self.state.player_potions + loot["potions"])
                self.last_loot = loot

                if hasattr(self, "player") and self.player:
                    self.player.persistent_hp = self.state.player_hp
                    self.player.persistent_potions = self.state.player_potions
                    self.player.atk_bonus = self.state.player_atk_bonus
                    self.player.def_bonus = self.state.player_def_bonus
                    if hasattr(self.player, "inventory") and isinstance(self.player.inventory, list):
                        if loot["name"] not in self.player.inventory:
                            self.player.inventory.append(loot["name"])

                self.log(f"💥 {active.name if active else 'NPC'} Tumbang! {next_npc.name} masuk ke arena duel!")
                self.log(f"✨ SECOND WIND! Player pulih +{heal_amount} HP, +1 Potion, Cooldown Heavy Attack siap!")
                self.log(f"🎁 RAMPASAN PERANG: Merebut {loot['name']}! ({loot['desc']})")
                self._set_action_text("PLAYER", "SECOND WIND!", f"(+{heal_amount} HP, +1 Pot)")
                self._set_action_text("NPC", "TAG-IN!", next_npc.name)

                # Sinkronisasi state duel ke karakter NPC baru
                self.state.npc_hp = next_npc.current_hp
                self.state.npc_max_hp = next_npc.max_hp
                self.state.npc_potions = next_npc.potions
                self.state.npc_atk_bonus = next_npc.atk_bonus
                self.state.npc_def_bonus = next_npc.def_bonus
                self.state.npc_defending = False
                self.state.npc_heavy_cd = 0
                self.eval_mode = next_npc.eval_profile

                # Panggil hook / callback animasi tag-in summon
                if hasattr(self, "on_tag_in") and callable(self.on_tag_in):
                    self.on_tag_in(active, next_npc, heal_amount, loot)
                return

        # 2. Kondisi duel benar-benar berakhir
        if self.state.is_terminal():
            self.is_finished = True
            if self.squad:
                active = self.squad.get_active_member()
                if active and self.state.npc_hp <= 0:
                    active.current_hp = 0

            if self.state.player_hp <= 0 and self.state.npc_hp <= 0:
                self.winner = "DRAW"
                self.log("Pertarungan Sengit berakhir SERI!")
            elif self.state.player_hp <= 0:
                self.winner = "NPC"
                self.log("Player Tumbang! Tim NPC (AI) Memenangkan Duel!")
            else:
                self.winner = "PLAYER"
                self.log("🏆 Selamat! Seluruh tim NPC berhasil dikalahkan!")
                final_active = self.squad.get_active_member() if self.squad else None
                if final_active:
                    final_loot = self._get_spoils_of_war(final_active)
                    self.state.player_atk_bonus += final_loot["atk_bonus"]
                    self.state.player_def_bonus += final_loot["def_bonus"]
                    if hasattr(self, "player") and self.player:
                        self.player.atk_bonus = self.state.player_atk_bonus
                        self.player.def_bonus = self.state.player_def_bonus
                        if hasattr(self.player, "inventory") and isinstance(self.player.inventory, list):
                            if final_loot["name"] not in self.player.inventory:
                                self.player.inventory.append(final_loot["name"])
                    self.log(f"🏆 RAMPASAN FINAL: Merebut {final_loot['name']}! ({final_loot['desc']})")
                    self.last_loot = final_loot
