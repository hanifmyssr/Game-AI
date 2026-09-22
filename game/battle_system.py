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
)


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
        self.use_move_ordering = True

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

        self.reset()

    def reset(self):
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
        self.battle_logs = ["Duel dimulai! Bolu (Player) berhadapan dengan Kucing Hitam (NPC)!"]
        self.last_ai_stats = {}
        self.is_finished = False
        self.winner = None
        self.player_action_text = None
        self.npc_action_text = None

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
        }
        color = color_map.get(action, (255, 255, 255))

        entry = {"text": text, "timer": self.ACTION_TEXT_DURATION, "color": color}
        if who == "PLAYER":
            self.player_action_text = entry
        else:
            self.npc_action_text = entry

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
        if self.is_finished or self.state.is_npc_turn:
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
            self.log(f"Player: Menyerang! Berhasil memberi {dmg} damage.")
            self._set_action_text("PLAYER", ACTION_ATTACK, f"(-{dmg} HP)")
        elif action == ACTION_HEAVY:
            dmg = old_npc_hp - self.state.npc_hp
            self.log(f"Player: Serangan Kuat! Memberi {dmg} damage!")
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
        if self.is_finished or not self.state.is_npc_turn:
            return None

        best_action, best_score, stats = self.ai_solver.select_best_action(
            self.state,
            algorithm=self.algorithm,
            eval_mode=self.eval_mode,
            depth=self.depth,
            use_move_ordering=self.use_move_ordering,
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
            self.log(f"NPC: Menyerang biasa! Memberi {dmg} damage.")
            self._set_action_text("NPC", ACTION_ATTACK, f"(-{dmg} HP)")
        elif best_action == ACTION_HEAVY:
            dmg = old_player_hp - self.state.player_hp
            self.log(f"NPC: Serangan Telak! Memberi {dmg} damage!")
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
        if self.state.is_terminal():
            self.is_finished = True
            if self.state.player_hp <= 0 and self.state.npc_hp <= 0:
                self.winner = "DRAW"
                self.log("Pertarungan Sengit berakhir SERI!")
            elif self.state.player_hp <= 0:
                self.winner = "NPC"
                self.log("Player Tumbang! NPC (AI) Memenangkan Duel!")
            else:
                self.winner = "PLAYER"
                self.log("Selamat! Player berhasil mengalahkan NPC!")
