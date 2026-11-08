"""Modul Materi 08: Automated Classical Planning (PDDL / STRIPS).

Menyediakan representasi formal PDDL (Predikat, State Fluents, Skema Aksi STRIPS),
serta dua mesin perencana pencarian ruang keadaan:
1. Forward State-Space Search (Progression via A*)
2. Backward Search (Regression via Sub-Goal Decomposition)
"""

from .pddl_types import Predicate, State, ActionSchema
from .planner_engine import ForwardProgressionPlanner, BackwardRegressionPlanner, PlanningResult
from .domain_world_patrol import create_world_patrol_problem
from .domain_battle_tactics import create_battle_tactics_problem

__all__ = [
    "Predicate",
    "State",
    "ActionSchema",
    "ForwardProgressionPlanner",
    "BackwardRegressionPlanner",
    "PlanningResult",
    "create_world_patrol_problem",
    "create_battle_tactics_problem",
]

