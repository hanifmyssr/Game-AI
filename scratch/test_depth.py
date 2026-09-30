import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game.battle_ai import BattleState, BattleAISolver

solver = BattleAISolver()

print("=" * 80)
print("PENGUJIAN KEDALAMAN (DEPTH LIMIT) PADA MINIMAX / ALPHA-BETA")
print("=" * 80)

# Skenario 1: Trap / Counter-Attack (Mencegah Kekalahan di Giliran Lawan)
# NPC HP 20, Player HP 50 (Heavy CD 0).
# Jika NPC ATTACK (dmg 18), Player HP sisa 32. Di giliran Player, Player pakai HEAVY_ATTACK (dmg 30) -> NPC HP 0 (NPC MATI!).
# Di Depth 1: NPC belum lihat giliran Player balasan.
# Di Depth 2+: NPC melihat giliran Player balasan yang mematikan, jadi NPC memilih POTION / DEFEND.
state1 = BattleState(player_hp=50, npc_hp=20, player_potions=1, npc_potions=1, player_heavy_cd=0)
print("\n[SKENARIO 1: NPC HP 20, Player HP 50 (Player bisa counter heavy 30 dmg)]")
print(f"{'Depth':<7} | {'Aksi Terpilih':<15} | {'Skor Evaluasi':<15} | {'Node Count':<12} | {'Penjelasan Keputusan'}")
print("-" * 80)
for d in range(1, 5):
    act, score, stats = solver.select_best_action(state1, algorithm="ALPHA_BETA", depth=d)
    explanation = "Hanya lihat aksi sendiri" if d == 1 else "Melihat ancaman balasan Player!"
    print(f"{d:<7} | {act:<15} | {score:<15.1f} | {stats['node_count']:<12} | {explanation}")

# Skenario 2: Multi-Turn Lethal Check (Kemenangan 2 Turn Jarak Jauh)
# Player HP 30, NPC HP 80, Heavy CD 2 (hanya bisa ATTACK 18 dmg).
# Turn 1 NPC ATTACK (Player HP 12). Turn 1 Player ATTACK (NPC HP 62). Turn 2 NPC ATTACK (Player HP 0 -> MATI).
# Di Depth 1-2: NPC belum sampai giliran ke-2 (Turn 2 NPC).
# Di Depth 3+: NPC sampai di giliran ke-2 NPC dan melihat kemenangan (+1000).
state2 = BattleState(player_hp=30, npc_hp=80, player_potions=0, npc_potions=0, npc_heavy_cd=2)
print("\n\n[SKENARIO 2: Player HP 30, NPC HP 80 (Bisa dibunuh dalam 2x ATTACK biasa)]")
print(f"{'Depth':<7} | {'Aksi Terpilih':<15} | {'Skor Evaluasi':<15} | {'Node Count':<12} | {'Penjelasan Keputusan'}")
print("-" * 80)
for d in range(1, 5):
    act, score, stats = solver.select_best_action(state2, algorithm="ALPHA_BETA", depth=d)
    explanation = "Skor evaluasi biasa" if d < 3 else "Melacak Kemenangan Terminal (+1000)!"
    print(f"{d:<7} | {act:<15} | {score:<15.1f} | {stats['node_count']:<12} | {explanation}")
