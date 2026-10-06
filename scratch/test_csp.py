import sys
import os
import time

# Tambahkan path root agar modul game dapat di-import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.npc_config_csp import NPCConfigCSP
from game.difficulty import calculate_difficulty_score, calculate_fitness, calculate_difficulty_breakdown


def test_csp():
    print("==================================================")
    print("MENJALANKAN PENGUJIAN CSP SOLVER & DIFFICULTY...")
    print("==================================================")

    csp = NPCConfigCSP(budget_hp=250, budget_potions=5, budget_atk=25)

    # 1. Tes pencarian solusi untuk 1, 2, dan 3 NPC
    for count in [1, 2, 3]:
        t0 = time.perf_counter()
        solutions = csp.solve(npc_count=count, max_solutions=1)
        dur = (time.perf_counter() - t0) * 1000.0

        assert len(solutions) > 0, f"Gagal menemukan solusi untuk {count} NPC!"
        sol = solutions[0]
        is_valid, violations = csp.validate_config(sol)

        diff_score = calculate_difficulty_score(sol)
        fitness = calculate_fitness(sol)
        bd = calculate_difficulty_breakdown(sol)

        print(f"\n[NPC Count = {count}] Solusi ditemukan dalam {dur:.2f} ms ({csp.stats['assignments_tried']} assignments, {csp.stats['backtracks']} backtracks):")
        print(f"  Valid: {is_valid} (Violations: {violations})")
        print(f"  Difficulty Score: {diff_score} | Fitness vs 0.55: {fitness:.4f}")
        for idx, m in enumerate(sol["members"]):
            print(f"    - NPC {idx+1}: {m['char_type']} | HP: {m['hp']} | Pot: {m['potions']} | Atk+: {m['atk_bonus']} | Def+: {m['def_bonus']} | Eval: {m['eval_profile']}")

        assert is_valid, f"Solusi tidak valid: {violations}"

    # 2. Tes deteksi pelanggaran constraint (Negative Tests)
    print("\n[Pengujian Deteksi Pelanggaran Constraint]")
    # C1 violation: HP overload
    bad_config_hp = {
        "npc_count": 2,
        "members": [
            {"char_type": "warrior", "hp": 150, "potions": 1, "atk_bonus": 5, "def_bonus": 2, "eval_profile": "BALANCED"},
            {"char_type": "tank", "hp": 120, "potions": 1, "atk_bonus": 0, "def_bonus": 4, "eval_profile": "DEFENSIVE"},
        ]
    }
    is_valid, violations = csp.validate_config(bad_config_hp)
    print(f"  Tes C1 (Over HP 270 > 250): Valid={is_valid}, Violations={violations}")
    assert not is_valid and any("C1" in v for v in violations)

    # C5 violation: Duplicate class
    bad_config_dup = {
        "npc_count": 2,
        "members": [
            {"char_type": "warrior", "hp": 80, "potions": 1, "atk_bonus": 5, "def_bonus": 2, "eval_profile": "BALANCED"},
            {"char_type": "warrior", "hp": 80, "potions": 1, "atk_bonus": 5, "def_bonus": 2, "eval_profile": "BALANCED"},
        ]
    }
    is_valid, violations = csp.validate_config(bad_config_dup)
    print(f"  Tes C5 (Duplicate Class): Valid={is_valid}, Violations={violations}")
    assert not is_valid and any("C5" in v for v in violations)

    # C3 violation: Tank HP < 90
    bad_config_tank = {
        "npc_count": 1,
        "members": [
            {"char_type": "tank", "hp": 70, "potions": 1, "atk_bonus": 0, "def_bonus": 4, "eval_profile": "DEFENSIVE"},
        ]
    }
    is_valid, violations = csp.validate_config(bad_config_tank)
    print(f"  Tes C3 (Tank HP < 90): Valid={is_valid}, Violations={violations}")
    assert not is_valid and any("C3" in v for v in violations)

    print("\n==================================================")
    print("SEMUA UNIT TEST CSP & DIFFICULTY LULUS 100%!")
    print("==================================================")


if __name__ == "__main__":
    test_csp()
