"""Penerjemah Rencana PDDL ke Eksekusi Perilaku NPC di Dunia Nyata & Battle.

Membaca sekuens aksi STRIPS yang dihasilkan oleh Forward atau Backward Planner,
kemudian menginstruksikan modul AI dunia/battle untuk mengeksekusinya secara teratur.
"""

from typing import List, Optional, Any
from .pddl_types import ActionSchema
from .planner_engine import PlanningResult


class TaskExecutor:
    """Eksekutor rencana tugas PDDL."""

    def __init__(self, app_ref: Any = None):
        self.app = app_ref
        self.current_plan: List[ActionSchema] = []
        self.current_step_idx: int = 0
        self.is_executing: bool = False
        self.latest_result: Optional[PlanningResult] = None

    def set_plan(self, plan_result: PlanningResult) -> None:
        """Menetapkan rencana baru untuk dieksekusi."""
        self.latest_result = plan_result
        self.current_plan = list(plan_result.plan)
        self.current_step_idx = 0
        self.is_executing = bool(self.current_plan)

    def step(self) -> Optional[ActionSchema]:
        """Menjalankan satu langkah rencana berikutnya."""
        if not self.is_executing or self.current_step_idx >= len(self.current_plan):
            self.is_executing = False
            return None

        act = self.current_plan[self.current_step_idx]
        self.current_step_idx += 1

        # Sinkronkan ke app jika ada
        if self.app:
            self._dispatch_action(act)

        if self.current_step_idx >= len(self.current_plan):
            self.is_executing = False

        return act

    def _dispatch_action(self, action: ActionSchema) -> None:
        """Mengirimkan instruksi aksi ke sistem game."""
        act_name = action.name

        if act_name in ("MoveToChokePoint", "InterceptPlayer"):
            if hasattr(self.app, "npc_kuro"):
                self.app.npc_kuro.chasing = True

        elif act_name == "ReinforceGuard":
            if hasattr(self.app, "npc_shiro"):
                self.app.npc_shiro.chasing = False

        elif act_name == "SwapRetreat":
            pass

        elif act_name == "CastDefend":
            pass

        elif act_name == "HealTeammate":
            pass

