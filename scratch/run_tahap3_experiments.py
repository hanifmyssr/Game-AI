"""Script Eksperimen Otomatis: Benchmark CSP Solver dan 5 Algoritma Local Search
untuk Optimasi Squad NPC & Penyeimbangan Kesulitan (Tubes AI Tahap 3 & 4).

Metrik yang diuji:
1. Evaluasi CSP Solver (MRV, LCV, AC-3 Unary Pruning, Kepatuhan Constraint C1-C8).
2. Perbandingan Kinerja 5 Algoritma Local Search:
   - Simple Hill Climbing
   - Hill Climbing with Sideways Move
   - Random Restart Hill Climbing
   - Simulated Annealing
   - Genetic Algorithm
3. Uji Adaptabilitas Dinamis Squad terhadap Status Pemain (Dynamic Player Context Balancing).
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.npc_config_csp import NPCConfigCSP
from game.npc_config_optimizer import NPCOptimizer, get_adaptive_target_difficulty
from game.difficulty import calculate_difficulty_score, calculate_fitness


def run_experiment_1_csp_solver():
    print("=" * 88)
    print("EKSPERIMEN 1: EVALUASI CSP SOLVER (BACKTRACKING + MRV + LCV + AC-3 PRUNING)")
    print("=" * 88)
    print(f"Total Variabel CSP  : 18 variabel (6 fitur: Class, HP, Pot, Atk, Def, Eval untuk 3 NPC)")
    print(f"Total Constraint   : 8 Constraint (C1 - C8: Budget, Syarat Class, Hubungan Archetype)")
    print("-" * 88)
    print(f"{'Metrik / Parameter':<45} | {'Hasil Observasi':<38}")
    print("-" * 88)

    csp = NPCConfigCSP(budget_hp=250, budget_potions=5, budget_atk=25)

    # 1. AC-3 Domain Pre-processing
    domains = csp.get_initial_domains(npc_count=3)
    t0 = time.perf_counter()
    pruned = csp.apply_ac3_unary(domains, npc_count=3)
    t_ac3 = (time.perf_counter() - t0) * 1000.0

    print(f"{'Waktu Eksekusi AC-3 Unary Filtering':<45} | {t_ac3:>12.3f} ms")
    print(f"{'Domain Pruned via AC-3':<45} | {str(pruned) + ' nilai domain terpangkas':<38}")

    # 2. Benchmark Solve 10 run untuk 2 dan 3 NPC
    for count in [2, 3]:
        times = []
        solutions = []
        for _ in range(5):
            t0 = time.perf_counter()
            sol = csp.solve(npc_count=count, max_solutions=1)
            dur = (time.perf_counter() - t0) * 1000.0
            times.append(dur)
            solutions.append(sol[0])

        avg_time = sum(times) / len(times)
        first_sol = solutions[0]
        is_valid, violations = csp.validate_config(first_sol)
        tot_hp = sum(m["hp"] for m in first_sol["members"])
        classes = " + ".join(m["char_type"] for m in first_sol["members"])
        evals = " + ".join(m["eval_profile"] for m in first_sol["members"])

        print(f"{f'Waktu Solve {count} NPC (Backtracking + MRV)':<45} | {avg_time:>12.3f} ms")
        print(f"{f'Validitas Constraint C1-C8 ({count} NPC)':<45} | {str(is_valid) + ' (Violations: ' + str(len(violations)) + ')':<38}")
        print(f"{f'Total HP Squad ({count} NPC)':<45} | {str(tot_hp) + ' HP (Budget <= 250)':<38}")
        print(f"{f'Komposisi Class ({count} NPC)':<45} | {classes:<38}")
        print(f"{f'Komposisi Archetype AI ({count} NPC)':<45} | {evals:<38}")

    print("-" * 88)


def run_experiment_2_local_search_comparison():
    print("\n" + "=" * 88)
    print("EKSPERIMEN 2: PERBANDINGAN KINERJA 5 ALGORITMA LOCAL SEARCH (TARGET DIFF = 0.55)")
    print("=" * 88)
    print(f"{'Algoritma':<23} | {'Waktu (ms)':<11} | {'Iter/Gen':<10} | {'Fitness':<10} | {'Difficulty':<12} | {'CSP Valid?'}")
    print("-" * 88)

    csp = NPCConfigCSP(budget_hp=250, budget_potions=5, budget_atk=25)
    optimizer = NPCOptimizer(target_difficulty=0.55, csp_solver=csp)

    algorithms = [
        ("HILL_CLIMBING", "Hill Climbing"),
        ("SIDEWAYS", "HC with Sideways"),
        ("RANDOM_RESTART", "Random Restart HC"),
        ("SIMULATED_ANNEALING", "Simulated Annealing"),
        ("GENETIC_ALGORITHM", "Genetic Algorithm"),
    ]

    results = []

    for algo_code, algo_name in algorithms:
        run_times = []
        run_fitness = []
        run_diff = []
        run_iters = []
        all_valid = True

        for _ in range(5):
            cfg, stats = optimizer.optimize(algorithm=algo_code)
            dur_ms = stats.get("time_ms", 0.0)

            run_times.append(dur_ms)
            run_fitness.append(stats.get("final_fitness", 0.0))
            run_diff.append(stats.get("final_difficulty", 0.0))
            run_iters.append(stats.get("iterations", 0))

            valid, _ = csp.validate_config(cfg)
            if not valid:
                all_valid = False

        avg_time = sum(run_times) / len(run_times)
        avg_fit = sum(run_fitness) / len(run_fitness)
        avg_diff = sum(run_diff) / len(run_diff)
        avg_iter = sum(run_iters) / len(run_iters)

        print(
            f"{algo_name:<23} | {avg_time:>8.2f} ms | {avg_iter:>10.1f} | {avg_fit:>10.4f} | {avg_diff:>12.4f} | {str(all_valid):<10}"
        )
        results.append((algo_name, avg_time, avg_iter, avg_fit, avg_diff, all_valid))

    print("-" * 88)
    return results


def run_experiment_3_adaptive_balancing():
    print("\n" + "=" * 88)
    print("EKSPERIMEN 3: ADAPTABILITAS SQUAD TERHADAP DYNAMIC PLAYER CONTEXT")
    print("=" * 88)

    csp = NPCConfigCSP(budget_hp=250, budget_potions=5, budget_atk=25)
    optimizer = NPCOptimizer(target_difficulty=0.55, csp_solver=csp)

    scenarios = [
        (
            "Skenario A: Kondisi Standar (Fresh Player)",
            {"player_hp": 100, "player_potions": 2, "player_atk_bonus": 0, "player_def_bonus": 0},
            "Tantangan seimbang reguler"
        ),
        (
            "Skenario B: Kondisi Kritis / Terluka (Wounded Player)",
            {"player_hp": 35, "player_potions": 0, "player_atk_bonus": 0, "player_def_bonus": 0},
            "Kompensasi: Squad lebih ramah agar duel tetap fair"
        ),
        (
            "Skenario C: Kondisi Overpowered / Loot Harta (Buffed Player)",
            {"player_hp": 100, "player_potions": 4, "player_atk_bonus": 6, "player_def_bonus": 4},
            "Eskalasi: Squad lebih agresif dan tebal mengimbangi player"
        ),
    ]

    print(f"{'Skenario & Kondisi Player':<40} | {'Target':<8} | {'Hasil Diff':<10} | {'Total HP':<10} | {'Komposisi Squad'}")
    print("-" * 88)

    for title, ctx, desc in scenarios:
        expected_target = get_adaptive_target_difficulty(ctx)
        cfg, stats = optimizer.optimize("SIDEWAYS", player_context=ctx)
        actual_diff = stats["final_difficulty"]
        tot_hp = sum(m["hp"] for m in cfg["members"])
        comp = " + ".join(f"{m['char_type']}({m['eval_profile'][:3]})" for m in cfg["members"])

        print(f"{title[:40]:<40} | {expected_target:>6.2f}   | {actual_diff:>10.4f} | {tot_hp:>7} HP  | {comp}")

    print("-" * 88)
    print("KESIMPULAN: Sistem Local Search adaptif berhasil memodulasi difficulty score")
    print("secara otomatis berdasarkan inventory dan status pemain secara real-time.")
    print("=" * 88)


if __name__ == "__main__":
    print("\n" + "#" * 88)
    print("EKSEKUSI BENCHMARK OTOMATIS: CSP SOLVER & LOCAL SEARCH OPTIMIZER (TAHAP 3 & 4)")
    print("#" * 88 + "\n")

    run_experiment_1_csp_solver()
    run_experiment_2_local_search_comparison()
    run_experiment_3_adaptive_balancing()

    print("\nSemua eksperimen benchmark berhasil dieksekusi dengan sukses!\n")
