"""Unit Test Mandiri: Modul 08 Classical Automated Planning (PDDL / STRIPS)."""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.planning.planner_engine import ForwardProgressionPlanner, BackwardRegressionPlanner
from game.planning.domain_world_patrol import create_world_patrol_problem
from game.planning.domain_battle_tactics import create_battle_tactics_problem
from game.planning.task_executor import TaskExecutor


def test_automated_planning():
    print("=== MENGUJI AUTOMATED PLANNING STRIPS (MODUL 08) ===")
    
    forward_planner = ForwardProgressionPlanner()
    backward_planner = BackwardRegressionPlanner()

    # 1. PENGUJIAN DOMAIN 1: PATROLI DUNIA & CEGAT PETI
    print("\n--- Domain 1: Patroli Dunia & Pertahanan Peti ---")
    s0, goal, actions = create_world_patrol_problem(looted_chest="A")
    print(f"State Awal (s0): {s0}")
    print(f"Goal State: {goal}")
    print(f"Total Operator Aksi: {len(actions)}")

    # Forward Progression A*
    res_fwd = forward_planner.plan(s0, goal, actions)
    print(f"\n1. {res_fwd}")
    assert res_fwd.success, "Forward Progression HARUS menemukan rencana patroli!"
    assert len(res_fwd.plan) >= 3, "Rencana minimal 3 langkah aksi!"

    # Backward Regression STRIPS
    res_bwd = backward_planner.plan(s0, goal, actions)
    print(f"\n2. {res_bwd}")
    assert res_bwd.success, "Backward Regression HARUS menemukan rencana patroli!"
    assert len(res_bwd.plan) == len(res_fwd.plan), "Panjang rencana Forward & Backward harus konsisten!"

    # Verifikasi eksekusi langkah demi langkah pada State
    curr_s = s0
    for act in res_fwd.plan:
        assert act.is_applicable(curr_s), f"Aksi {act} harus berlaku pada state {curr_s}!"
        curr_s = curr_s.apply(act)
    assert curr_s.satisfies(goal), "State akhir harus memenuhi semua predikat Goal!"
    print("Verifikasi transisi state maju (State Transition Validation): VALID 100%!")

    # 2. PENGUJIAN DOMAIN 2: BATTLE TAG-TEAM ROTATION & HEAL
    print("\n--- Domain 2: Taktik Rotasi & Pemulihan Battle Tag-Team ---")
    s0_bat, goal_bat, actions_bat = create_battle_tactics_problem("Oyen", "Kage", "Shiro")
    print(f"State Awal Battle (s0): {s0_bat}")
    print(f"Goal State Battle: {goal_bat}")

    res_bat_fwd = forward_planner.plan(s0_bat, goal_bat, actions_bat)
    print(f"\n1. {res_bat_fwd}")
    assert res_bat_fwd.success, "Forward Planner HARUS menemukan taktik battle!"

    res_bat_bwd = backward_planner.plan(s0_bat, goal_bat, actions_bat)
    print(f"\n2. {res_bat_bwd}")
    assert res_bat_bwd.success, "Backward Planner HARUS menemukan taktik battle!"

    # 3. PENGUJIAN TASK EXECUTOR
    print("\n--- Uji Task Executor ---")
    executor = TaskExecutor()
    executor.set_plan(res_fwd)
    step_count = 0
    while executor.is_executing:
        act = executor.step()
        if act:
            step_count += 1
            print(f"  Step {step_count}: Eksekusi {act.name}")
    assert step_count == len(res_fwd.plan)

    print("\n==================================================")
    print("SEMUA PENGUJIAN AUTOMATED PLANNING 100% LULUS!")
    print("==================================================")


if __name__ == "__main__":
    test_automated_planning()

