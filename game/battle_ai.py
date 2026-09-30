"""Modul AI Duel: State, Action, Terminal Test, Utility, Evaluation Function,
Minimax, Alpha-Beta Pruning, dan Expectimax.

Termasuk TreeNode untuk merekam pohon keputusan AI secara real-time.
"""

import time
from typing import Dict, List, Tuple, Any, Optional


# --------------------------------------------------------------------------- #
# Move Ordering Modes
# --------------------------------------------------------------------------- #
MOVE_ORDERING_OFF = "OFF"
MOVE_ORDERING_HEURISTIC = "HEURISTIC"
MOVE_ORDERING_REVERSED = "REVERSED"
MOVE_ORDERING_MODES = [MOVE_ORDERING_OFF, MOVE_ORDERING_HEURISTIC, MOVE_ORDERING_REVERSED]


# --------------------------------------------------------------------------- #
# TreeNode: Struktur data untuk merekam pohon keputusan AI
# --------------------------------------------------------------------------- #
class TreeNode:
    """Node dalam pohon pencarian AI, digunakan untuk visualisasi Decision Tree Overlay."""
    __slots__ = (
        "action", "score", "alpha", "beta",
        "is_max", "depth", "pruned", "is_best",
        "children", "node_type",
    )

    def __init__(
        self,
        action: Optional[str] = None,
        score: Optional[float] = None,
        alpha: float = -float("inf"),
        beta: float = float("inf"),
        is_max: bool = True,
        depth: int = 0,
        pruned: bool = False,
        is_best: bool = False,
        node_type: str = "MAX",  # "MAX", "MIN", "CHANCE"
    ):
        self.action = action
        self.score = score
        self.alpha = alpha
        self.beta = beta
        self.is_max = is_max
        self.depth = depth
        self.pruned = pruned
        self.is_best = is_best
        self.children: List["TreeNode"] = []
        self.node_type = node_type

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
        self.last_tree: Optional[TreeNode] = None  # Root tree dari pencarian terakhir

    # ------------------------------------------------------------------ #
    # Helper: Urutkan aksi berdasarkan mode move ordering
    # ------------------------------------------------------------------ #
    @staticmethod
    def _order_actions(actions: List[str], is_max: bool, mode: str) -> List[str]:
        """Mengurutkan aksi berdasarkan mode move ordering."""
        if mode == MOVE_ORDERING_OFF:
            return actions  # Tidak diurutkan

        if mode == MOVE_ORDERING_HEURISTIC:
            # Urutan heuristik: aksi ofensif/kritis lebih dahulu
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
        elif mode == MOVE_ORDERING_REVERSED:
            # Urutan terbalik: aksi defensif/pasif lebih dahulu
            if is_max:
                actions.sort(
                    key=lambda a: (
                        3 if a == ACTION_DEFEND else (2 if a == ACTION_POTION else (1 if a == ACTION_ATTACK else 0))
                    ),
                    reverse=True,
                )
            else:
                actions.sort(
                    key=lambda a: (
                        3 if a == ACTION_POTION else (2 if a == ACTION_DEFEND else (1 if a == ACTION_ATTACK else 0))
                    ),
                    reverse=True,
                )
        return actions

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

    # 2. ALPHA-BETA PRUNING (dengan tree recording untuk visualisasi)
    def alpha_beta(
        self,
        state: BattleState,
        depth: int,
        alpha: float,
        beta: float,
        is_max: bool,
        eval_fn,
        move_ordering_mode: str = MOVE_ORDERING_HEURISTIC,
        record_tree: bool = False,
        parent_node: Optional[TreeNode] = None,
    ) -> float:
        self.node_count += 1

        if depth == 0 or state.is_terminal():
            score = state.utility() if state.is_terminal() else eval_fn(state)
            if record_tree and parent_node is not None:
                parent_node.score = round(score, 2)
            return score

        actions = state.get_legal_actions()
        actions = self._order_actions(actions, is_max, move_ordering_mode)

        if is_max:
            max_eval = -float("inf")
            best_child_idx = -1
            for i, action in enumerate(actions):
                child_node = None
                if record_tree and parent_node is not None:
                    child_node = TreeNode(
                        action=action, alpha=alpha, beta=beta,
                        is_max=False, depth=parent_node.depth + 1,
                        node_type="MIN",
                    )
                    parent_node.children.append(child_node)

                next_state = state.apply_action(action)
                val = self.alpha_beta(
                    next_state, depth - 1, alpha, beta, False, eval_fn,
                    move_ordering_mode, record_tree, child_node,
                )

                if child_node is not None:
                    child_node.score = round(val, 2)

                if val > max_eval:
                    max_eval = val
                    best_child_idx = i
                alpha = max(alpha, val)
                if beta <= alpha:
                    self.pruned_count += 1
                    # Tandai sisa aksi sebagai pruned
                    if record_tree and parent_node is not None:
                        for remaining_action in actions[i + 1:]:
                            pruned_child = TreeNode(
                                action=remaining_action, alpha=alpha, beta=beta,
                                is_max=False, depth=parent_node.depth + 1,
                                pruned=True, node_type="MIN",
                            )
                            parent_node.children.append(pruned_child)
                    break

            if record_tree and parent_node is not None:
                parent_node.score = round(max_eval, 2)
                if best_child_idx >= 0 and best_child_idx < len(parent_node.children):
                    parent_node.children[best_child_idx].is_best = True
            return max_eval
        else:
            min_eval = float("inf")
            best_child_idx = -1
            for i, action in enumerate(actions):
                child_node = None
                if record_tree and parent_node is not None:
                    child_node = TreeNode(
                        action=action, alpha=alpha, beta=beta,
                        is_max=True, depth=parent_node.depth + 1,
                        node_type="MAX",
                    )
                    parent_node.children.append(child_node)

                next_state = state.apply_action(action)
                val = self.alpha_beta(
                    next_state, depth - 1, alpha, beta, True, eval_fn,
                    move_ordering_mode, record_tree, child_node,
                )

                if child_node is not None:
                    child_node.score = round(val, 2)

                if val < min_eval:
                    min_eval = val
                    best_child_idx = i
                beta = min(beta, val)
                if beta <= alpha:
                    self.pruned_count += 1
                    if record_tree and parent_node is not None:
                        for remaining_action in actions[i + 1:]:
                            pruned_child = TreeNode(
                                action=remaining_action, alpha=alpha, beta=beta,
                                is_max=True, depth=parent_node.depth + 1,
                                pruned=True, node_type="MAX",
                            )
                            parent_node.children.append(pruned_child)
                    break

            if record_tree and parent_node is not None:
                parent_node.score = round(min_eval, 2)
                if best_child_idx >= 0 and best_child_idx < len(parent_node.children):
                    parent_node.children[best_child_idx].is_best = True
            return min_eval

    # 3. EXPECTIMAX (Stokastik pada Heavy Attack: 75% Kena, 25% Meleset)
    def expectimax(
        self,
        state: BattleState,
        depth: int,
        is_max: bool,
        eval_fn,
        record_tree: bool = False,
        parent_node: Optional[TreeNode] = None,
    ) -> float:
        self.node_count += 1

        if depth == 0 or state.is_terminal():
            score = state.utility() if state.is_terminal() else eval_fn(state)
            if record_tree and parent_node is not None:
                parent_node.score = round(score, 2)
            return score

        actions = state.get_legal_actions()

        if is_max:
            max_eval = -float("inf")
            best_child_idx = -1
            for i, action in enumerate(actions):
                child_node = None
                if record_tree and parent_node is not None:
                    child_node = TreeNode(
                        action=action, alpha=-float("inf"), beta=float("inf"),
                        is_max=False, depth=parent_node.depth + 1,
                        node_type="MIN",
                    )
                    parent_node.children.append(child_node)

                if action == ACTION_HEAVY:
                    state_hit = state.apply_action(action, heavy_hits=True)
                    state_miss = state.apply_action(action, heavy_hits=False)
                    hit_node = None
                    miss_node = None
                    if record_tree and child_node is not None:
                        hit_node = TreeNode(action="HIT (75%)", depth=child_node.depth + 1, node_type="CHANCE")
                        miss_node = TreeNode(action="MISS (25%)", depth=child_node.depth + 1, node_type="CHANCE")
                        child_node.children.extend([hit_node, miss_node])

                    v_hit = self.expectimax(state_hit, depth - 1, False, eval_fn, record_tree, hit_node)
                    v_miss = self.expectimax(state_miss, depth - 1, False, eval_fn, record_tree, miss_node)
                    if hit_node is not None:
                        hit_node.score = round(v_hit, 2)
                    if miss_node is not None:
                        miss_node.score = round(v_miss, 2)
                    val = 0.75 * v_hit + 0.25 * v_miss
                else:
                    next_state = state.apply_action(action)
                    val = self.expectimax(next_state, depth - 1, False, eval_fn, record_tree, child_node)

                if child_node is not None:
                    child_node.score = round(val, 2)

                if val > max_eval:
                    max_eval = val
                    best_child_idx = i

            if record_tree and parent_node is not None:
                parent_node.score = round(max_eval, 2)
                if 0 <= best_child_idx < len(parent_node.children):
                    parent_node.children[best_child_idx].is_best = True
            return max_eval
        else:
            min_eval = float("inf")
            best_child_idx = -1
            for i, action in enumerate(actions):
                child_node = None
                if record_tree and parent_node is not None:
                    child_node = TreeNode(
                        action=action, alpha=-float("inf"), beta=float("inf"),
                        is_max=True, depth=parent_node.depth + 1,
                        node_type="MAX",
                    )
                    parent_node.children.append(child_node)

                if action == ACTION_HEAVY:
                    state_hit = state.apply_action(action, heavy_hits=True)
                    state_miss = state.apply_action(action, heavy_hits=False)
                    hit_node = None
                    miss_node = None
                    if record_tree and child_node is not None:
                        hit_node = TreeNode(action="HIT (75%)", depth=child_node.depth + 1, node_type="CHANCE")
                        miss_node = TreeNode(action="MISS (25%)", depth=child_node.depth + 1, node_type="CHANCE")
                        child_node.children.extend([hit_node, miss_node])

                    v_hit = self.expectimax(state_hit, depth - 1, True, eval_fn, record_tree, hit_node)
                    v_miss = self.expectimax(state_miss, depth - 1, True, eval_fn, record_tree, miss_node)
                    if hit_node is not None:
                        hit_node.score = round(v_hit, 2)
                    if miss_node is not None:
                        miss_node.score = round(v_miss, 2)
                    val = 0.75 * v_hit + 0.25 * v_miss
                else:
                    next_state = state.apply_action(action)
                    val = self.expectimax(next_state, depth - 1, True, eval_fn, record_tree, child_node)

                if child_node is not None:
                    child_node.score = round(val, 2)

                if val < min_eval:
                    min_eval = val
                    best_child_idx = i

            if record_tree and parent_node is not None:
                parent_node.score = round(min_eval, 2)
                if 0 <= best_child_idx < len(parent_node.children):
                    parent_node.children[best_child_idx].is_best = True
            return min_eval

    def select_best_action(
        self,
        state: BattleState,
        algorithm: str = "ALPHA_BETA",
        eval_mode: str = "BALANCED",
        depth: int = 4,
        move_ordering_mode: Any = MOVE_ORDERING_HEURISTIC,
        record_tree: bool = False,
        use_move_ordering: Optional[bool] = None,
    ) -> Tuple[Optional[str], float, Dict[str, Any]]:
        """Mengevaluasi setiap aksi legal di root node dan memilih aksi terbaik untuk NPC."""
        # Backward compatibility jika dipanggil dengan boolean use_move_ordering
        if use_move_ordering is not None:
            move_ordering_mode = MOVE_ORDERING_HEURISTIC if use_move_ordering else MOVE_ORDERING_OFF
        elif isinstance(move_ordering_mode, bool):
            move_ordering_mode = MOVE_ORDERING_HEURISTIC if move_ordering_mode else MOVE_ORDERING_OFF

        legal_actions = state.get_legal_actions()
        if not legal_actions:
            return None, 0.0, {}

        _, eval_fn = EVAL_FUNCTIONS.get(eval_mode, EVAL_FUNCTIONS["BALANCED"])
        self.node_count = 0
        self.pruned_count = 0

        # Bangun root tree node (untuk visualisasi Decision Tree)
        root_tree = TreeNode(
            action=None, is_max=True, depth=0, node_type="MAX",
            alpha=-float("inf"), beta=float("inf"),
        ) if record_tree else None

        action_scores: Dict[str, float] = {}
        best_action = None
        best_score = -float("inf")

        start_time = time.perf_counter()

        for action in legal_actions:
            child_node = None
            if record_tree and root_tree is not None:
                child_node = TreeNode(
                    action=action, is_max=False, depth=1, node_type="MIN",
                    alpha=-float("inf"), beta=float("inf"),
                )
                root_tree.children.append(child_node)

            if algorithm == "MINIMAX":
                next_state = state.apply_action(action)
                score = self.minimax(next_state, depth - 1, False, eval_fn)
            elif algorithm == "EXPECTIMAX":
                if action == ACTION_HEAVY:
                    state_hit = state.apply_action(action, heavy_hits=True)
                    state_miss = state.apply_action(action, heavy_hits=False)
                    hit_node = None
                    miss_node = None
                    if record_tree and child_node is not None:
                        hit_node = TreeNode(action="HIT (75%)", depth=2, node_type="CHANCE")
                        miss_node = TreeNode(action="MISS (25%)", depth=2, node_type="CHANCE")
                        child_node.children.extend([hit_node, miss_node])

                    v_hit = self.expectimax(state_hit, depth - 1, False, eval_fn, record_tree, hit_node)
                    v_miss = self.expectimax(state_miss, depth - 1, False, eval_fn, record_tree, miss_node)
                    if hit_node is not None:
                        hit_node.score = round(v_hit, 2)
                    if miss_node is not None:
                        miss_node.score = round(v_miss, 2)
                    score = 0.75 * v_hit + 0.25 * v_miss
                else:
                    next_state = state.apply_action(action)
                    score = self.expectimax(next_state, depth - 1, False, eval_fn, record_tree, child_node)
            else:  # Default: ALPHA_BETA
                next_state = state.apply_action(action)
                score = self.alpha_beta(
                    next_state,
                    depth - 1,
                    -float("inf"),
                    float("inf"),
                    False,
                    eval_fn,
                    move_ordering_mode=move_ordering_mode,
                    record_tree=record_tree,
                    parent_node=child_node,
                )

            if child_node is not None:
                child_node.score = round(score, 2)

            action_scores[action] = round(score, 2)
            if score > best_score:
                best_score = score
                best_action = action

        # Tandai jalur terbaik di root tree
        if record_tree and root_tree is not None:
            root_tree.score = round(best_score, 2)
            for child in root_tree.children:
                if child.action == best_action:
                    child.is_best = True

        self.last_tree = root_tree

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Hitung komparasi komprehensif: Pure Minimax vs Alpha-Beta vs Expectimax
        deterministic_scores: Dict[str, float] = {}
        expectimax_scores: Dict[str, float] = {}
        minimax_nodes = None
        alphabeta_nodes = None
        expectimax_nodes = None

        if algorithm == "ALPHA_BETA":
            alphabeta_nodes = self.node_count
            deterministic_scores = action_scores.copy()

            mm_solver = BattleAISolver()
            for act in legal_actions:
                ns = state.apply_action(act)
                mm_solver.minimax(ns, depth - 1, False, eval_fn)
            minimax_nodes = mm_solver.node_count

            ex_solver = BattleAISolver()
            for act in legal_actions:
                if act == ACTION_HEAVY:
                    sh = state.apply_action(act, heavy_hits=True)
                    sm = state.apply_action(act, heavy_hits=False)
                    sc = 0.75 * ex_solver.expectimax(sh, depth - 1, False, eval_fn) + \
                         0.25 * ex_solver.expectimax(sm, depth - 1, False, eval_fn)
                else:
                    ns = state.apply_action(act)
                    sc = ex_solver.expectimax(ns, depth - 1, False, eval_fn)
                expectimax_scores[act] = round(sc, 2)
            expectimax_nodes = ex_solver.node_count

        elif algorithm == "MINIMAX":
            minimax_nodes = self.node_count
            deterministic_scores = action_scores.copy()

            ab_solver = BattleAISolver()
            for act in legal_actions:
                ns = state.apply_action(act)
                ab_solver.alpha_beta(
                    ns, depth - 1, -float("inf"), float("inf"), False,
                    eval_fn, move_ordering_mode=move_ordering_mode
                )
            alphabeta_nodes = ab_solver.node_count

            ex_solver = BattleAISolver()
            for act in legal_actions:
                if act == ACTION_HEAVY:
                    sh = state.apply_action(act, heavy_hits=True)
                    sm = state.apply_action(act, heavy_hits=False)
                    sc = 0.75 * ex_solver.expectimax(sh, depth - 1, False, eval_fn) + \
                         0.25 * ex_solver.expectimax(sm, depth - 1, False, eval_fn)
                else:
                    ns = state.apply_action(act)
                    sc = ex_solver.expectimax(ns, depth - 1, False, eval_fn)
                expectimax_scores[act] = round(sc, 2)
            expectimax_nodes = ex_solver.node_count

        elif algorithm == "EXPECTIMAX":
            expectimax_nodes = self.node_count
            expectimax_scores = action_scores.copy()

            ab_solver = BattleAISolver()
            for act in legal_actions:
                ns = state.apply_action(act)
                sc = ab_solver.alpha_beta(
                    ns, depth - 1, -float("inf"), float("inf"), False,
                    eval_fn, move_ordering_mode=move_ordering_mode
                )
                deterministic_scores[act] = round(sc, 2)
            alphabeta_nodes = ab_solver.node_count

            mm_solver = BattleAISolver()
            for act in legal_actions:
                ns = state.apply_action(act)
                mm_solver.minimax(ns, depth - 1, False, eval_fn)
            minimax_nodes = mm_solver.node_count

        savings_pct = 0.0
        if minimax_nodes and alphabeta_nodes and minimax_nodes > 0:
            savings_pct = max(0.0, ((minimax_nodes - alphabeta_nodes) / float(minimax_nodes)) * 100.0)

        stats = {
            "algorithm": algorithm,
            "eval_mode": eval_mode,
            "depth": depth,
            "move_ordering": move_ordering_mode,
            "node_count": self.node_count,
            "pruned_count": self.pruned_count,
            "time_ms": elapsed_ms,
            "action_scores": action_scores,
            "best_action": best_action,
            "best_score": round(best_score, 2),
            "tree": root_tree,
            "comparison": {
                "minimax_nodes": minimax_nodes,
                "alphabeta_nodes": alphabeta_nodes,
                "expectimax_nodes": expectimax_nodes,
                "savings_pct": savings_pct,
                "depth": depth,
                "deterministic_scores": deterministic_scores,
                "expectimax_scores": expectimax_scores,
            },
        }

        return best_action, best_score, stats
