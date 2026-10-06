"""Unit test untuk menguji 5 algoritma Local Search Optimizer (Tahap 3)."""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.npc_config_csp import NPCConfigCSP
from game.npc_config_optimizer import NPCOptimizer
from game.difficulty import calculate_difficulty_score, calculate_fitness


def test_optimizer():
    print("==================================================")
    print("MENJALANKAN PENGUJIAN 5 ALGORITMA LOCAL SEARCH...")
    print("Target Difficulty: 0.55 ('Fun Zone')")
    print("==================================================")

    csp = NPCConfigCSP(budget_hp=250, budget_potions=5, budget_atk=25)
    optimizer = NPCOptimizer(target_difficulty=0.55, csp_solver=csp)

    algorithms = [
        "HILL_CLIMBING",
        "SIDEWAYS",
        "RANDOM_RESTART",
        "SIMULATED_ANNEALING",
        "GENETIC_ALGORITHM",
    ]

    for algo in algorithms:
        best_cfg, stats = optimizer.optimize(algorithm=algo)
        is_valid, violations = csp.validate_config(best_cfg)
        diff = stats["final_difficulty"]
        dist = stats["distance_to_target"]
        t_ms = stats["time_ms"]
        iters = stats["iterations"]

        print(f"\n[{algo}]")
        print(f"  Valid menurut CSP: {is_valid} (Violations: {violations})")
        print(f"  Final Difficulty : {diff:.4f} (Selisih ke 0.55: {dist:.4f})")
        print(f"  Waktu Eksekusi   : {t_ms:.2f} ms ({iters} iterasi/evaluasi)")
        print(f"  Jumlah Anggota   : {best_cfg['npc_count']} NPC")
        for idx, m in enumerate(best_cfg["members"]):
            print(f"    - NPC {idx+1}: {m['char_type']:8s} | HP:{m['hp']:3d} | Pot:{m['potions']} | Atk+:{m['atk_bonus']:2d} | Def+:{m['def_bonus']} | {m['eval_profile']}")

        assert is_valid, f"{algo} menghasilkan konfigurasi yang melanggar constraint: {violations}"
        assert dist <= 0.20, f"{algo} gagal mendekati target difficulty (selisih {dist} terlalu jauh)!"

    print("\n==================================================")
    print("SELURUH 5 ALGORITMA LOCAL SEARCH LULUS 100%!")
    print("==================================================")


if __name__ == "__main__":
    test_optimizer()
