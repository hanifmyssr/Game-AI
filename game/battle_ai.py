"""Modul AI Duel: State, Action, Terminal Test, Utility, Evaluation Function,
Minimax, Alpha-Beta Pruning, dan Expectimax.
"""

import time
from typing import Dict, List, Tuple, Any, Optional

# Definisi Aksi (Branching Factor <= 4)
ACTION_ATTACK = "ATTACK"
ACTION_HEAVY = "HEAVY_ATTACK"
ACTION_DEFEND = "DEFEND"
ACTION_POTION = "POTION"

ACTIONS = [ACTION_ATTACK, ACTION_HEAVY, ACTION_DEFEND, ACTION_POTION]

# Konstanta Nilai Stat Duel
MAX_HP = 100
MAX_POTIONS = 3
POTION_HEAL = 25

# Kerusakan Dasar
ATTACK_DAMAGE = 18
ATTACK_DEFENDED_DAMAGE = 6

HEAVY_DAMAGE = 30
HEAVY_DEFENDED_DAMAGE = 10
HEAVY_ACCURACY = 0.75  # Digunakan dalam Expectimax

DEFEND_REDUCTION = 0.65  # ~65% reduksi


# Cooldown Heavy Attack: jumlah giliran SENDIRI yang harus ditunggu sebelum bisa pakai lagi
HEAVY_COOLDOWN_TURNS = 2


class BattleState:
    """State representasi formal dari duel turn-based."""

    __slots__ = (
        "player_hp",
        "npc_hp",
        "player_potions",
        "npc_potions",
        "player_defending",
        "npc_defending",
        "is_npc_turn",  # True: NPC (MAX), False: Player (MIN)
        "player_heavy_cd",  # Sisa cooldown heavy attack Player (0 = siap)
        "npc_heavy_cd",     # Sisa cooldown heavy attack NPC (0 = siap)
    )

    def __init__(
        self,
        player_hp: int = 100,
        npc_hp: int = 100,
        player_potions: int = 2,
        npc_potions: int = 2,
        player_defending: bool = False,
        npc_defending: bool = False,
        is_npc_turn: bool = True,
        player_heavy_cd: int = 0,
        npc_heavy_cd: int = 0,
    ):
        self.player_hp = max(0, min(MAX_HP, player_hp))
        self.npc_hp = max(0, min(MAX_HP, npc_hp))
        self.player_potions = max(0, min(MAX_POTIONS, player_potions))
        self.npc_potions = max(0, min(MAX_POTIONS, npc_potions))
        self.player_defending = player_defending
        self.npc_defending = npc_defending
        self.is_npc_turn = is_npc_turn
        self.player_heavy_cd = max(0, player_heavy_cd)
        self.npc_heavy_cd = max(0, npc_heavy_cd)

    def is_terminal(self) -> bool:
        """Terminal Test: Duel berakhir jika salah satu atau kedua petarung HP <= 0."""
        return self.player_hp <= 0 or self.npc_hp <= 0

    def utility(self) -> float:
        """Utility function pada terminal state:
        NPC menang (Player kalah): +1000
        Player menang (NPC kalah): -1000
        Draw (keduanya 0): 0
        """
        if self.player_hp <= 0 and self.npc_hp > 0:
            return 1000.0 + self.npc_hp
        elif self.npc_hp <= 0 and self.player_hp > 0:
            return -1000.0 - self.player_hp
        return 0.0

    def get_legal_actions(self) -> List[str]:
        """Mengembalikan aksi valid dari pemain giliran aktif (maksimal 4 aksi)."""
        if self.is_terminal():
            return []

        legal = [ACTION_ATTACK]

        # Heavy Attack hanya legal jika cooldown == 0
        heavy_cd = self.npc_heavy_cd if self.is_npc_turn else self.player_heavy_cd
        if heavy_cd <= 0:
            legal.append(ACTION_HEAVY)

        legal.append(ACTION_DEFEND)

        # Potion hanya bisa digunakan jika masih memiliki persediaan dan HP belum penuh
        current_hp = self.npc_hp if self.is_npc_turn else self.player_hp
        current_pots = self.npc_potions if self.is_npc_turn else self.player_potions
        if current_pots > 0 and current_hp < MAX_HP:
            legal.append(ACTION_POTION)

        return legal

    def clone(self) -> "BattleState":
        return BattleState(
            player_hp=self.player_hp,
            npc_hp=self.npc_hp,
            player_potions=self.player_potions,
            npc_potions=self.npc_potions,
            player_defending=self.player_defending,
            npc_defending=self.npc_defending,
            is_npc_turn=self.is_npc_turn,
            player_heavy_cd=self.player_heavy_cd,
            npc_heavy_cd=self.npc_heavy_cd,
        )

    def apply_action(self, action: str, heavy_hits: bool = True) -> "BattleState":
        """Transisi deterministik dari State s dengan Aksi a menghasilkan State s'."""
        next_state = self.clone()

        if self.is_npc_turn:
            # NPC melakukan aksi terhadap Player
            next_state.npc_defending = False  # Reset defend lama sebelum aksi baru

            # Kurangi cooldown heavy NPC setiap giliran NPC (sebelum cek aksi)
            if next_state.npc_heavy_cd > 0:
                next_state.npc_heavy_cd -= 1

            if action == ACTION_ATTACK:
                dmg = ATTACK_DEFENDED_DAMAGE if next_state.player_defending else ATTACK_DAMAGE
                next_state.player_hp = max(0, next_state.player_hp - dmg)
            elif action == ACTION_HEAVY:
                if heavy_hits:
                    dmg = HEAVY_DEFENDED_DAMAGE if next_state.player_defending else HEAVY_DAMAGE
                    next_state.player_hp = max(0, next_state.player_hp - dmg)
                next_state.npc_heavy_cd = HEAVY_COOLDOWN_TURNS  # Set cooldown
            elif action == ACTION_DEFEND:
                next_state.npc_defending = True
            elif action == ACTION_POTION:
                if next_state.npc_potions > 0:
                    next_state.npc_potions -= 1
                    next_state.npc_hp = min(MAX_HP, next_state.npc_hp + POTION_HEAL)

            next_state.is_npc_turn = False
        else:
            # Player melakukan aksi terhadap NPC
            next_state.player_defending = False

            # Kurangi cooldown heavy Player setiap giliran Player
            if next_state.player_heavy_cd > 0:
                next_state.player_heavy_cd -= 1

            if action == ACTION_ATTACK:
                dmg = ATTACK_DEFENDED_DAMAGE if next_state.npc_defending else ATTACK_DAMAGE
                next_state.npc_hp = max(0, next_state.npc_hp - dmg)
            elif action == ACTION_HEAVY:
                if heavy_hits:
                    dmg = HEAVY_DEFENDED_DAMAGE if next_state.npc_defending else HEAVY_DAMAGE
                    next_state.npc_hp = max(0, next_state.npc_hp - dmg)
                next_state.player_heavy_cd = HEAVY_COOLDOWN_TURNS  # Set cooldown
            elif action == ACTION_DEFEND:
                next_state.player_defending = True
            elif action == ACTION_POTION:
                if next_state.player_potions > 0:
                    next_state.player_potions -= 1
                    next_state.player_hp = min(MAX_HP, next_state.player_hp + POTION_HEAL)

            next_state.is_npc_turn = True

        return next_state


# --------------------------------------------------------------------------- #
# Evaluation Functions
# --------------------------------------------------------------------------- #
def eval_balanced(state: BattleState) -> float:
    """Fungsi Evaluasi Seimbang:
    Mempertimbangkan selisih HP dan simpanan Potion secara proporsional.
    """
    hp_diff = state.npc_hp - state.player_hp
    pot_diff = state.npc_potions - state.player_potions
    score = (hp_diff * 2.0) + (pot_diff * 12.0)
    if state.npc_defending and state.player_hp > 20:
        score += 5.0
    return score


def eval_aggressive(state: BattleState) -> float:
    """Fungsi Evaluasi Agresif:
    Sangat memprioritaskan pengurangan HP Player daripada menjaga HP sendiri.
    """
    score = (100 - state.player_hp) * 4.0 - (100 - state.npc_hp) * 1.2
    score += state.npc_potions * 4.0
    if state.player_hp <= 30:
        score += 35.0  # Dorongan kuat untuk eksekusi lawan
    return score


def eval_defensive(state: BattleState) -> float:
    """Fungsi Evaluasi Defensif / Taktis:
    Menjaga kelangsungan hidup NPC, menghargai pertahanan dan pemulihan HP.
    """
    score = (state.npc_hp * 3.0) - (state.player_hp * 1.5) + (state.npc_potions * 20.0)
    if state.npc_defending:
        score += 15.0
    if state.npc_hp < 40 and state.npc_potions > 0:
        score -= 25.0  # Penalti jika belum menggunakan potion saat sekarat
    return score


EVAL_FUNCTIONS = {
    "BALANCED": ("Balanced (Standar)", eval_balanced),
    "AGGRESSIVE": ("Aggressive (Penyerang)", eval_aggressive),
    "DEFENSIVE": ("Defensive (Bertahan)", eval_defensive),
}


# --------------------------------------------------------------------------- #
# Mesin Pencarian: Minimax, Alpha-Beta, Expectimax
# --------------------------------------------------------------------------- #
class BattleAISolver:
    def __init__(self):
        self.node_count = 0
        self.pruned_count = 0

    # 1. PURE MINIMAX (Tanpa Pruning)
    def minimax(
        self,
        state: BattleState,
        depth: int,
        is_max: bool,
        eval_fn,
    ) -> float:
        self.node_count += 1

        if depth == 0 or state.is_terminal():
            if state.is_terminal():
                return state.utility()
            return eval_fn(state)

        actions = state.get_legal_actions()
        if is_max:
            max_eval = -float("inf")
            for action in actions:
                next_state = state.apply_action(action)
                val = self.minimax(next_state, depth - 1, False, eval_fn)
                if val > max_eval:
                    max_eval = val
            return max_eval
        else:
            min_eval = float("inf")
            for action in actions:
                next_state = state.apply_action(action)
                val = self.minimax(next_state, depth - 1, True, eval_fn)
                if val < min_eval:
                    min_eval = val
            return min_eval

    # 2. ALPHA-BETA PRUNING
    def alpha_beta(
        self,
        state: BattleState,
        depth: int,
        alpha: float,
        beta: float,
        is_max: bool,
        eval_fn,
        use_move_ordering: bool = True,
    ) -> float:
        self.node_count += 1

        if depth == 0 or state.is_terminal():
            if state.is_terminal():
                return state.utility()
            return eval_fn(state)

        actions = state.get_legal_actions()

        # Heuristic Move Ordering: mengurutkan aksi menjanjikan lebih awal
        if use_move_ordering:
            if is_max:
                actions.sort(
                    key=lambda a: (
                        3 if a == ACTION_HEAVY else (2 if a == ACTION_ATTACK else (1 if a == ACTION_POTION else 0))
                    ),
                    reverse=True,
                )
            else:
                actions.sort(
                    key=lambda a: (
                        3 if a == ACTION_HEAVY else (2 if a == ACTION_ATTACK else (1 if a == ACTION_DEFEND else 0))
                    ),
                    reverse=True,
                )

        if is_max:
            max_eval = -float("inf")
            for action in actions:
                next_state = state.apply_action(action)
                val = self.alpha_beta(
                    next_state, depth - 1, alpha, beta, False, eval_fn, use_move_ordering
                )
                if val > max_eval:
                    max_eval = val
                alpha = max(alpha, val)
                if beta <= alpha:
                    self.pruned_count += 1
                    break
            return max_eval
        else:
            min_eval = float("inf")
            for action in actions:
                next_state = state.apply_action(action)
                val = self.alpha_beta(
                    next_state, depth - 1, alpha, beta, True, eval_fn, use_move_ordering
                )
                if val < min_eval:
                    min_eval = val
                beta = min(beta, val)
                if beta <= alpha:
                    self.pruned_count += 1
                    break
            return min_eval

    # 3. EXPECTIMAX (Stokastik pada Heavy Attack: 75% Kena, 25% Meleset)
    def expectimax(
        self,
        state: BattleState,
        depth: int,
        is_max: bool,
        eval_fn,
    ) -> float:
        self.node_count += 1

        if depth == 0 or state.is_terminal():
            if state.is_terminal():
                return state.utility()
            return eval_fn(state)

        actions = state.get_legal_actions()

        if is_max:
            max_eval = -float("inf")
            for action in actions:
                if action == ACTION_HEAVY:
                    state_hit = state.apply_action(action, heavy_hits=True)
                    state_miss = state.apply_action(action, heavy_hits=False)
                    val = 0.75 * self.expectimax(state_hit, depth - 1, False, eval_fn) + \
                          0.25 * self.expectimax(state_miss, depth - 1, False, eval_fn)
                else:
                    next_state = state.apply_action(action)
                    val = self.expectimax(next_state, depth - 1, False, eval_fn)

                if val > max_eval:
                    max_eval = val
            return max_eval
        else:
            min_eval = float("inf")
            for action in actions:
                if action == ACTION_HEAVY:
                    state_hit = state.apply_action(action, heavy_hits=True)
                    state_miss = state.apply_action(action, heavy_hits=False)
                    val = 0.75 * self.expectimax(state_hit, depth - 1, True, eval_fn) + \
                          0.25 * self.expectimax(state_miss, depth - 1, True, eval_fn)
                else:
                    next_state = state.apply_action(action)
                    val = self.expectimax(next_state, depth - 1, True, eval_fn)

                if val < min_eval:
                    min_eval = val
            return min_eval

    # Root Decision Maker untuk NPC
    def select_best_action(
        self,
        state: BattleState,
        algorithm: str = "ALPHA_BETA",
        eval_mode: str = "BALANCED",
        depth: int = 4,
        use_move_ordering: bool = True,
    ) -> Tuple[Optional[str], float, Dict[str, Any]]:
        """Mengevaluasi setiap aksi legal di root node dan memilih aksi terbaik untuk NPC."""
        legal_actions = state.get_legal_actions()
        if not legal_actions:
            return None, 0.0, {}

        _, eval_fn = EVAL_FUNCTIONS.get(eval_mode, EVAL_FUNCTIONS["BALANCED"])
        self.node_count = 0
        self.pruned_count = 0

        action_scores: Dict[str, float] = {}
        best_action = None
        best_score = -float("inf")

        start_time = time.perf_counter()

        for action in legal_actions:
            if algorithm == "MINIMAX":
                next_state = state.apply_action(action)
                score = self.minimax(next_state, depth - 1, False, eval_fn)
            elif algorithm == "EXPECTIMAX":
                if action == ACTION_HEAVY:
                    state_hit = state.apply_action(action, heavy_hits=True)
                    state_miss = state.apply_action(action, heavy_hits=False)
                    score = 0.75 * self.expectimax(state_hit, depth - 1, False, eval_fn) + \
                            0.25 * self.expectimax(state_miss, depth - 1, False, eval_fn)
                else:
                    next_state = state.apply_action(action)
                    score = self.expectimax(next_state, depth - 1, False, eval_fn)
            else:  # Default: ALPHA_BETA
                next_state = state.apply_action(action)
                score = self.alpha_beta(
                    next_state,
                    depth - 1,
                    -float("inf"),
                    float("inf"),
                    False,
                    eval_fn,
                    use_move_ordering=use_move_ordering,
                )

            action_scores[action] = round(score, 2)
            if score > best_score:
                best_score = score
                best_action = action

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        stats = {
            "algorithm": algorithm,
            "eval_mode": eval_mode,
            "depth": depth,
            "move_ordering": use_move_ordering,
            "node_count": self.node_count,
            "pruned_count": self.pruned_count,
            "time_ms": elapsed_ms,
            "action_scores": action_scores,
            "best_action": best_action,
            "best_score": round(best_score, 2),
        }

        return best_action, best_score, stats
