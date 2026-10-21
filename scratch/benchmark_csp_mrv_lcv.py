"""Benchmark CSP Solver: 30 Percobaan Komparatif
Membandingkan Kinerja Backtracking Search:
1. Full Heuristics: Backtracking + MRV + LCV
2. Backtracking + MRV (Tanpa LCV)
3. Backtracking + LCV (Tanpa MRV)
4. Naive Backtracking (Tanpa MRV & Tanpa LCV)

Diuji pada konfigurasi 2 NPC (12 Variabel) dan 3 NPC (18 Variabel).
Serta ekstraksi detail komposisi stat Skenario A, B, C untuk Tabel 4.4.
"""

import sys
import os
import time
import random
import statistics

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.npc_config_csp import NPCConfigCSP
from game.npc_config_optimizer import NPCOptimizer, get_adaptive_target_difficulty


def run_csp_30_trials():
    print("=" * 100)
    print("BENCHMARK CSP SOLVER: 30 PERCOBAAN DENGAN & TANPA HEURISTIK (MRV & LCV)")
    print("=" * 100)

    configs = [
        {"name": "Backtracking + MRV + LCV (Full)", "use_mrv": True, "use_lcv": True},
        {"name": "Backtracking + MRV (Tanpa LCV)", "use_mrv": True, "use_lcv": False},
        {"name": "Backtracking + LCV (Tanpa MRV)", "use_mrv": False, "use_lcv": True},
        {"name": "Naive Backtracking (Tanpa MRV & LCV)", "use_mrv": False, "use_lcv": False},
    ]

    results_table = []

    for npc_count in [2, 3]:
        var_count = npc_count * 6
        print(f"\n>>> PENGUJIAN SQUAD {npc_count} NPC ({var_count} VARIABEL CSP, 30 PERCOBAAN SHUFFLED) <<<")
        print(f"{'Metode Heuristik':<38} | {'Avg Waktu (ms)':<14} | {'Avg Assign':<11} | {'Avg Backtrack':<14} | {'Min/Max BT':<10} | {'Valid C1-C8'}")
        print("-" * 105)

        for cfg in configs:
            times = []
            assigns = []
            backtracks = []
            all_valid = True

            csp = NPCConfigCSP(budget_hp=250, budget_potions=5, budget_atk=25)

            # 30 percobaan dengan seed bervariasi agar eksplorasi domain representatif
            for seed in range(1, 31):
                random.seed(seed * 42)
                t0 = time.perf_counter()
                sols = csp.solve(
                    npc_count=npc_count,
                    max_solutions=1,
                    shuffle=True,
                    use_mrv=cfg["use_mrv"],
                    use_lcv=cfg["use_lcv"],
                )
                dur = (time.perf_counter() - t0) * 1000.0

                times.append(dur)
                assigns.append(csp.stats["assignments_tried"])
                backtracks.append(csp.stats["backtracks"])

                if sols:
                    valid, _ = csp.validate_config(sols[0])
                    if not valid:
                        all_valid = False
                else:
                    all_valid = False

            avg_time = statistics.mean(times)
            std_time = statistics.stdev(times) if len(times) > 1 else 0.0
            avg_assign = statistics.mean(assigns)
            avg_bt = statistics.mean(backtracks)
            min_bt = min(backtracks)
            max_bt = max(backtracks)

            valid_str = "100% (30/30)" if all_valid else "Ada Gagal"

            print(f"{cfg['name']:<38} | {avg_time:>7.3f} ± {std_time:>4.2f} ms | {avg_assign:>11.1f} | {avg_bt:>14.2f} | {f'{min_bt}/{max_bt}':<10} | {valid_str}")

            results_table.append({
                "npc_count": npc_count,
                "vars": var_count,
                "heuristic": cfg["name"],
                "avg_time_ms": avg_time,
                "std_time_ms": std_time,
                "avg_assign": avg_assign,
                "avg_bt": avg_bt,
                "min_bt": min_bt,
                "max_bt": max_bt,
                "valid": valid_str,
            })

    # Deterministic test (shuffle=False)
    print("\n" + "=" * 100)
    print("PENGUJIAN DETERMINISTIK (SHUFFLE = FALSE, URUTAN DOMAIN STANDAR)")
    print("=" * 100)
    print(f"{'Squad':<8} | {'Metode Heuristik':<38} | {'Waktu (ms)':<11} | {'Assign':<8} | {'Backtrack':<10} | {'Status'}")
    print("-" * 100)
    for npc_count in [2, 3]:
        for cfg in configs:
            csp = NPCConfigCSP(budget_hp=250, budget_potions=5, budget_atk=25)
            t0 = time.perf_counter()
            sols = csp.solve(
                npc_count=npc_count,
                max_solutions=1,
                shuffle=False,
                use_mrv=cfg["use_mrv"],
                use_lcv=cfg["use_lcv"],
            )
            dur = (time.perf_counter() - t0) * 1000.0
            bt = csp.stats["backtracks"]
            ass = csp.stats["assignments_tried"]
            status = "VALID" if sols and csp.validate_config(sols[0])[0] else "INVALID"
            print(f"{npc_count} NPC   | {cfg['name']:<38} | {dur:>8.3f} ms | {ass:>8} | {bt:>10} | {status}")


def run_scenario_details():
    print("\n" + "=" * 100)
    print("DETAIL RINCIAN ATRIBUT KOMPOSISI SQUAD SKENARIO A, B, DAN C (UNTUK TABEL 4.4)")
    print("=" * 100)

    csp = NPCConfigCSP(budget_hp=250, budget_potions=5, budget_atk=25)
    opt = NPCOptimizer(target_difficulty=0.55, csp_solver=csp)

    scenarios = [
        (
            "Skenario A: Pemain Bugar (Standard Fresh Player)",
            {"player_hp": 100, "player_potions": 2, "player_atk_bonus": 0, "player_def_bonus": 0},
            "Kondisi awal seimbang ideal",
        ),
        (
            "Skenario B: Pemain Sekarat / Terluka (Wounded Player)",
            {"player_hp": 35, "player_potions": 0, "player_atk_bonus": 0, "player_def_bonus": 0},
            "Kompensasi: musuh lebih sedikit & stat rendah",
        ),
        (
            "Skenario C: Pemain Buff Peti / Overpowered (Buffed Player)",
            {"player_hp": 100, "player_potions": 4, "player_atk_bonus": 6, "player_def_bonus": 4},
            "Eskalasi: musuh lebih tebal, agresif, dan kuat",
        ),
    ]

    for title, ctx, desc in scenarios:
        expected_target = get_adaptive_target_difficulty(ctx)
        # Gunakan seed stabil untuk hasil reprodusibel
        random.seed(42)
        cfg, stats = opt.optimize("SIDEWAYS", player_context=ctx)
        actual_diff = stats["final_difficulty"]
        actual_fit = stats["final_fitness"]
        members = cfg["members"]

        print(f"\n>>> {title} <<<")
        print(f"Kondisi Player  : HP = {ctx['player_hp']}, Potion = {ctx['player_potions']}, ATK Bonus = +{ctx['player_atk_bonus']}, DEF Bonus = +{ctx['player_def_bonus']}")
        print(f"Target Diff     : {expected_target:.4f} | Diff Tercapai: {actual_diff:.4f} | Fitness: {actual_fit:.4f}")
        print(f"Jumlah Anggota  : {len(members)} NPC")
        print("-" * 95)
        print(f"  {'No':<3} | {'Role / Class':<14} | {'HP':<8} | {'Potion':<8} | {'ATK Bonus':<11} | {'DEF Bonus':<11} | {'AI Profile'}")
        print("-" * 95)
        for i, m in enumerate(members):
            print(f"  {i+1:<3} | {m['char_type'].title():<14} | {m['hp']:<8} | {m['potions']:<8} | +{m['atk_bonus']:<10} | +{m['def_bonus']:<10} | {m['eval_profile']}")
        print("-" * 95)
        tot_hp = sum(m['hp'] for m in members)
        tot_pot = sum(m['potions'] for m in members)
        tot_atk = sum(m['atk_bonus'] for m in members)
        tot_def = sum(m['def_bonus'] for m in members)
        print(f"  TOTAL AGREGAT SQUAD: HP = {tot_hp} | Potion = {tot_pot} | ATK Bonus = +{tot_atk} | DEF Bonus = +{tot_def}")


if __name__ == "__main__":
    run_csp_30_trials()
    run_scenario_details()
