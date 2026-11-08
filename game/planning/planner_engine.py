"""Mesin Perencana Classical Planning: Forward Progression & Backward Regression.

Menerapkan dua metode pencarian ruang keadaan STRIPS:
1. Forward Progression State-Space Search menggunakan A* Search
2. Backward Regression Search dari sasaran Goal menuju State Awal (s0)
"""

import time
import heapq
from typing import List, Set, Dict, Any, Optional, Tuple, FrozenSet
from .pddl_types import Predicate, State, ActionSchema


class PlanningResult:
    """Hasil luaran proses perencanaan PDDL."""

    def __init__(self, plan: List[ActionSchema], cost: float,
                 nodes_expanded: int, time_ms: float, engine_name: str,
                 success: bool = True, s0: Optional[State] = None,
                 goal: Optional[Set[Predicate]] = None,
                 search_tree_root: Optional[Any] = None):
        self.plan = plan
        self.cost = cost
        self.nodes_expanded = nodes_expanded
        self.time_ms = time_ms
        self.engine_name = engine_name
        self.success = success
        self.s0 = s0
        self.goal = goal or set()
        self.search_tree_root = search_tree_root

    def __repr__(self) -> str:
        status = "SUKSES" if self.success else "GAGAL"
        plan_str = " -> ".join(repr(a) for a in self.plan) if self.plan else "(Rencana Kosong)"
        return (f"[{self.engine_name} - {status}] Panjang: {len(self.plan)}, "
                f"Simpul: {self.nodes_expanded}, Waktu: {self.time_ms:.2f}ms\n"
                f"Rencana: {plan_str}")


class ForwardProgressionPlanner:
    """Mesin perencana Forward State-Space Search (A*)."""

    def __init__(self):
        self.name = "Forward Progression (A*)"

    def heuristic(self, current_state: State, goal_predicates: Set[Predicate]) -> float:
        """Heuristik santai: menghitung jumlah sasaran gol yang belum terpenuhi di state saat ini."""
        unsatisfied = goal_predicates - current_state.predicates
        return float(len(unsatisfied))

    def plan(self, s0: State, goal: Set[Predicate], actions: List[ActionSchema],
             max_expansions: int = 500) -> PlanningResult:
        """Mencari sekuens aksi dari s0 menuju goal secara maju (Forward Search)."""
        t_start = time.perf_counter()

        # Priority Queue: (f_score, g_score, counter, current_state, path)
        counter = 0
        h0 = self.heuristic(s0, goal)
        frontier = [(h0, 0.0, counter, s0, [])]
        visited_costs: Dict[State, float] = {s0: 0.0}

        nodes_expanded = 0
        best_plan: Optional[List[ActionSchema]] = None
        final_cost = 0.0
        success = False

        while frontier and nodes_expanded < max_expansions:
            f, g, _, current_state, path = heapq.heappop(frontier)
            nodes_expanded += 1

            # Uji Sasaran (Goal Test): g ⊆ current_state
            if current_state.satisfies(goal):
                best_plan = path
                final_cost = g
                success = True
                break

            # Eksplorasi aksi-aksi yang berlaku (pre(a) ⊆ s)
            for act in actions:
                if act.is_applicable(current_state):
                    next_state = current_state.apply(act)
                    next_g = g + act.cost

                    if next_state not in visited_costs or next_g < visited_costs[next_state]:
                        visited_costs[next_state] = next_g
                        next_h = self.heuristic(next_state, goal)
                        counter += 1
                        heapq.heappush(frontier, (next_g + next_h, next_g, counter, next_state, path + [act]))

        t_elapsed = (time.perf_counter() - t_start) * 1000.0
        return PlanningResult(
            plan=best_plan or [],
            cost=final_cost,
            nodes_expanded=nodes_expanded,
            time_ms=t_elapsed,
            engine_name=self.name,
            success=success,
            s0=s0,
            goal=goal
        )


class BackwardRegressionPlanner:
    """Mesin perencana Backward Search (Regression dari Goal ke s0)."""

    def __init__(self):
        self.name = "Backward Regression (STRIPS)"

    def heuristic(self, current_goal: Set[Predicate], s0: State) -> float:
        """Heuristik: jumlah sub-goal yang belum dipenuhi oleh initial state s0."""
        unsatisfied = current_goal - s0.predicates
        return float(len(unsatisfied))

    def plan(self, s0: State, goal: Set[Predicate], actions: List[ActionSchema],
             max_expansions: int = 500) -> PlanningResult:
        """Mencari sekuens aksi dari goal mundur ke s0 (Backward Regression)."""
        t_start = time.perf_counter()

        counter = 0
        initial_goal_frozen = frozenset(goal)
        h0 = self.heuristic(goal, s0)

        # Priority queue: (f_score, g_score, counter, current_goal_frozenset, reversed_path)
        frontier = [(h0, 0.0, counter, initial_goal_frozen, [])]
        visited_costs: Dict[FrozenSet[Predicate], float] = {initial_goal_frozen: 0.0}

        nodes_expanded = 0
        best_plan: Optional[List[ActionSchema]] = None
        final_cost = 0.0
        success = False

        while frontier and nodes_expanded < max_expansions:
            f, g, _, current_goal, rev_path = heapq.heappop(frontier)
            nodes_expanded += 1

            # Uji Berhenti: jika seluruh sub-goal saat ini sudah ada di s0 (current_goal ⊆ s0)
            if current_goal.issubset(s0.predicates):
                # Balik urutan aksi mundur menjadi urutan eksekusi maju
                best_plan = list(reversed(rev_path))
                final_cost = g
                success = True
                break

            current_goal_set = set(current_goal)

            # Cari aksi yang Relevant dan Consistent untuk regresi
            for act in actions:
                if act.is_relevant(current_goal_set) and act.is_consistent(current_goal_set):
                    # Hitung sub-goal baru: g' = (g \ add) U pre
                    next_goal_set = act.regress(current_goal_set)
                    next_goal_frozen = frozenset(next_goal_set)
                    next_g = g + act.cost

                    if next_goal_frozen not in visited_costs or next_g < visited_costs[next_goal_frozen]:
                        visited_costs[next_goal_frozen] = next_g
                        next_h = self.heuristic(next_goal_set, s0)
                        counter += 1
                        heapq.heappush(frontier, (next_g + next_h, next_g, counter, next_goal_frozen, rev_path + [act]))

        t_elapsed = (time.perf_counter() - t_start) * 1000.0
        return PlanningResult(
            plan=best_plan or [],
            cost=final_cost,
            nodes_expanded=nodes_expanded,
            time_ms=t_elapsed,
            engine_name=self.name,
            success=success,
            s0=s0,
            goal=goal
        )


def build_planning_graph_nodes(plan_result: PlanningResult) -> Any:
    """Membangun visualisasi simpul GraphNode untuk pohon rencana PDDL di graph_modal.py."""
    from ..ui.graph_modal import GraphNode

    title = f"PDDL PLAN: {plan_result.engine_name}"
    status_label = f"Total Aksi: {len(plan_result.plan)} │ Simpul: {plan_result.nodes_expanded}"
    root = GraphNode(
        node_id="root_plan",
        label=title,
        sub_label=status_label,
        score_str=f"{plan_result.time_ms:.1f}ms",
        node_type="MAX" if plan_result.success else "DEFAULT",
        is_best=plan_result.success
    )

    curr_parent = root
    for idx, act in enumerate(plan_result.plan, start=1):
        pre_str = ", ".join(repr(p) for p in act.preconditions) or "None"
        add_str = ", ".join(repr(p) for p in act.add_list)
        is_last = (idx == len(plan_result.plan))

        act_node = curr_parent.add_child(GraphNode(
            node_id=f"act_{idx}",
            label=f"{idx}. {repr(act)}",
            sub_label=f"Pre: {pre_str} │ Add: {add_str}",
            score_str="GOAL REACHED" if is_last else f"Step {idx}",
            node_type="TERMINAL" if is_last else "DEFAULT",
            is_best=is_last
        ))
        curr_parent = act_node

    return root

