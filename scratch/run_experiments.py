"""Script Eksperimen Otomatis: Benchmark Minimax vs Alpha-Beta vs Expectimax,
Evaluation Functions, Move Ordering, dan Depth Analysis.
Hasil dapat langsung disertakan dalam laporan Tubes AI Tahap-2.
"""

import sys
import os
import time

# Tambahkan path root agar modul game dapat di-import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.battle_ai import (
    BattleState,
    BattleAISolver,
    EVAL_FUNCTIONS,
    ACTION_ATTACK,
    ACTION_HEAVY,
    ACTION_DEFEND,
    ACTION_POTION,
)


def run_experiment_1_depth_and_pruning():
    print("=" * 80)
    print("EKSPERIMEN 1: PERBANDINGAN PURE MINIMAX VS ALPHA-BETA PRUNING (VARIASI DEPTH)")
    print("=" * 80)
    print(f"{'Depth':<7} | {'Minimax Nodes':<15} | {'Alpha-Beta Nodes':<17} | {'Pruning %':<12} | {'Minimax (ms)':<14} | {'Alpha-Beta (ms)':<16} | {'Sama?'}")
    print("-" * 80)

    solver = BattleAISolver()
    results = []

    for depth in range(1, 7):
        state = BattleState(player_hp=80, npc_hp=80, player_potions=2, npc_potions=2, is_npc_turn=True)

        # 1. Pure Minimax
        t0 = time.perf_counter()
        act_mm, score_mm, stats_mm = solver.select_best_action(state, algorithm="MINIMAX", depth=depth, eval_mode="BALANCED")
        t_mm = (time.perf_counter() - t0) * 1000.0

        # 2. Alpha-Beta Pruning (dengan move ordering)
        t0 = time.perf_counter()
        act_ab, score_ab, stats_ab = solver.select_best_action(state, algorithm="ALPHA_BETA", depth=depth, eval_mode="BALANCED", use_move_ordering=True)
        t_ab = (time.perf_counter() - t0) * 1000.0

        nodes_mm = stats_mm["node_count"]
        nodes_ab = stats_ab["node_count"]
        prune_ratio = ((nodes_mm - nodes_ab) / nodes_mm) * 100.0 if nodes_mm > 0 else 0.0
        same_decision = (act_mm == act_ab) and (abs(score_mm - score_ab) < 1e-4)

        print(f"{depth:<7} | {nodes_mm:<15} | {nodes_ab:<17} | {prune_ratio:>9.1f} %  | {t_mm:>11.2f} ms | {t_ab:>13.2f} ms | {str(same_decision):<5}")
        results.append((depth, nodes_mm, nodes_ab, prune_ratio, t_mm, t_ab, act_mm, act_ab))

    return results


def run_experiment_2_move_ordering():
    print("\n" + "=" * 80)
    print("EKSPERIMEN 2: DAMPAK MOVE ORDERING PADA ALPHA-BETA PRUNING")
    print("=" * 80)
    print(f"{'Depth':<7} | {'Tanpa Move Ordering':<22} | {'Dengan Move Ordering':<22} | {'Peningkatan Reduksi %'}")
    print("-" * 80)

    solver = BattleAISolver()
    results = []

    for depth in range(3, 7):
        state = BattleState(player_hp=80, npc_hp=80, player_potions=2, npc_potions=2, is_npc_turn=True)

        _, _, stats_no_order = solver.select_best_action(state, algorithm="ALPHA_BETA", depth=depth, use_move_ordering=False)
        _, _, stats_ordered = solver.select_best_action(state, algorithm="ALPHA_BETA", depth=depth, use_move_ordering=True)

        n_no = stats_no_order["node_count"]
        n_ord = stats_ordered["node_count"]
        diff_pct = ((n_no - n_ord) / n_no) * 100.0 if n_no > 0 else 0.0

        print(f"{depth:<7} | {n_no:<22} | {n_ord:<22} | {diff_pct:>18.1f} %")
        results.append((depth, n_no, n_ord, diff_pct))

    return results


def run_experiment_3_evaluation_functions():
    print("\n" + "=" * 80)
    print("EKSPERIMEN 3: PERBANDINGAN PERILAKU NPC TERHADAP 3 FUNGSI EVALUASI")
    print("=" * 80)

    solver = BattleAISolver()
    scenarios = [
        ("Skenario 1 (Kondisi Awal / Netral)", BattleState(player_hp=100, npc_hp=100, player_potions=2, npc_potions=2)),
        ("Skenario 2 (NPC Sekarat, Player Kuat)", BattleState(player_hp=75, npc_hp=25, player_potions=2, npc_potions=2)),
        ("Skenario 3 (Player Sekarat, NPC Kuat)", BattleState(player_hp=20, npc_hp=70, player_potions=1, npc_potions=2)),
    ]

    results = []

    for title, state in scenarios:
        print(f"\n[{title}]")
        print(f"State: Player HP={state.player_hp}, NPC HP={state.npc_hp}, NPC Potions={state.npc_potions}")
        print(f"{'Fungsi Evaluasi':<25} | {'Aksi Terpilih':<15} | {'Skor Evaluasi':<15} | {'Skor Semua Aksi (Root)'}")
        print("-" * 80)

        for eval_name, (label, _) in EVAL_FUNCTIONS.items():
            act, score, stats = solver.select_best_action(state, algorithm="ALPHA_BETA", eval_mode=eval_name, depth=4)
            scores_str = ", ".join([f"{a}: {v:.1f}" for a, v in stats['action_scores'].items()])
            print(f"{label:<25} | {act:<15} | {score:<15.1f} | {scores_str}")
            results.append((title, eval_name, act, score, stats['action_scores']))

    return results


def run_experiment_4_expectimax():
    print("\n" + "=" * 80)
    print("EKSPERIMEN 4: EXPECTIMAX (STOKASTIK DENGAN PROBABILITAS HEAVY ATTACK)")
    print("=" * 80)
    print("Karakteristik: Heavy Attack memiliki 75% akurasi (damage 30) dan 25% meleset (damage 0).")

    solver = BattleAISolver()
    state = BattleState(player_hp=60, npc_hp=60, player_potions=1, npc_potions=1)

    act_ab, score_ab, stats_ab = solver.select_best_action(state, algorithm="ALPHA_BETA", depth=4, eval_mode="BALANCED")
    act_ex, score_ex, stats_ex = solver.select_best_action(state, algorithm="EXPECTIMAX", depth=4, eval_mode="BALANCED")

    print("\nHasil Root Action Scoring:")
    print(f"{'Aksi':<15} | {'Skor Alpha-Beta (Deterministik)':<32} | {'Skor Expectimax (75% Chance)':<30}")
    print("-" * 80)
    for act in [ACTION_ATTACK, ACTION_HEAVY, ACTION_DEFEND, ACTION_POTION]:
        s_ab = stats_ab['action_scores'].get(act, "N/A")
        s_ex = stats_ex['action_scores'].get(act, "N/A")
        print(f"{act:<15} | {s_ab!s:<32} | {s_ex!s:<30}")

    print(f"\nAksi Terpilih Alpha-Beta : {act_ab}")
    print(f"Aksi Terpilih Expectimax : {act_ex}")
    return stats_ab, stats_ex


if __name__ == "__main__":
    print("\nMENJALANKAN SERI EKSPERIMEN AI TUBES TAHAP-2 (MINIMAX & GAME THEORY)...\n")
    exp1 = run_experiment_1_depth_and_pruning()
    exp2 = run_experiment_2_move_ordering()
    exp3 = run_experiment_3_evaluation_functions()
    exp4 = run_experiment_4_expectimax()
    print("\n" + "=" * 80)
    print("SELURUH EKSPERIMEN BERHASIL DISELESAIKAN!")
    print("=" * 80)
