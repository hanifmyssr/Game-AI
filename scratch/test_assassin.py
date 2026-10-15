"""Test script untuk memverifikasi integrasi kelas Assassin (Kage)."""

import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

import sys
sys.path.insert(0, os.path.abspath("."))

from game import config
from game.npc_config_csp import NPCConfigCSP
from game.npc_config_optimizer import NPCOptimizer
from game.npc_squad import NPCSquad, NPCMember

print("=== 1. VERIFIKASI CONFIG ===")
print("CHAR_TYPES:", config.CHAR_TYPES)
assert "assassin" in config.CHAR_TYPES, "assassin harus ada di CHAR_TYPES"

print("\n=== 2. VERIFIKASI ASET SPRITE & PORTRAIT ASSASSIN ===")
portrait_path = os.path.join(config.ASSET_DIR, "portraits", "portrait_assassin.png")
battle_path = os.path.join(config.ASSET_DIR, "battle_sprites", "battle_assassin.png")
print("Portrait exists:", os.path.exists(portrait_path))
print("Battle sprite exists:", os.path.exists(battle_path))
assert os.path.exists(portrait_path), "portrait_assassin.png tidak ditemukan!"
assert os.path.exists(battle_path), "battle_assassin.png tidak ditemukan!"

member = NPCMember(
    name="Kage the Assassin",
    char_type="assassin",
    max_hp=80,
    potions=1,
    atk_bonus=10,
    def_bonus=0,
    eval_profile="AGGRESSIVE",
)
print("Loaded member:", member.name)
print("Portrait surface loaded:", member.portrait is not None)
print("Battle sprite surface loaded:", member.battle_sprite is not None)
assert member.portrait is not None, "Gagal me-load portrait assassin"
assert member.battle_sprite is not None, "Gagal me-load battle sprite assassin"

print("\n=== 3. VERIFIKASI CSP DENGAN ASSASSIN ===")
csp = NPCConfigCSP()
# Uji konfigurasi sah dengan Assassin
valid_cfg = {
    "npc_count": 3,
    "members": [
        {"char_type": "warrior", "hp": 100, "potions": 1, "atk_bonus": 0, "def_bonus": 2, "eval_profile": "BALANCED"},
        {"char_type": "ranger", "hp": 80, "potions": 1, "atk_bonus": 5, "def_bonus": 0, "eval_profile": "BALANCED"},
        {"char_type": "assassin", "hp": 70, "potions": 1, "atk_bonus": 10, "def_bonus": 0, "eval_profile": "AGGRESSIVE"},
    ],
}
is_valid, violations = csp.validate_config(valid_cfg)
print("Valid config test:", is_valid, violations)
assert is_valid, f"Konfigurasi seharusnya valid tapi gagal: {violations}"

# Uji pelanggaran khusus Assassin: atk < 10
invalid_atk_cfg = {
    "npc_count": 1,
    "members": [
        {"char_type": "assassin", "hp": 70, "potions": 1, "atk_bonus": 5, "def_bonus": 0, "eval_profile": "AGGRESSIVE"},
    ],
}
is_valid_inv, violations_inv = csp.validate_config(invalid_atk_cfg)
print("Invalid ATK (<10) detected:", not is_valid_inv, violations_inv)
assert not is_valid_inv, "Assassin dengan atk < 10 seharusnya ditolak!"

# Uji pelanggaran khusus Assassin: hp > 90
invalid_hp_cfg = {
    "npc_count": 1,
    "members": [
        {"char_type": "assassin", "hp": 100, "potions": 1, "atk_bonus": 10, "def_bonus": 0, "eval_profile": "AGGRESSIVE"},
    ],
}
is_valid_inv_hp, violations_inv_hp = csp.validate_config(invalid_hp_cfg)
print("Invalid HP (>90) detected:", not is_valid_inv_hp, violations_inv_hp)
assert not is_valid_inv_hp, "Assassin dengan hp > 90 seharusnya ditolak!"

print("\n=== 4. SOLVER CSP CARI SOLUSI (BACKTRACKING + AC-3) ===")
solutions = csp.solve(npc_count=3, max_solutions=15, shuffle=True)
print(f"Ditemukan {len(solutions)} solusi CSP untuk squad 3 NPC!")
assassin_solutions = [s for s in solutions if any(m["char_type"] == "assassin" for m in s["members"])]
print(f"Solusi yang menyertakan Assassin: {len(assassin_solutions)}")
if assassin_solutions:
    sample = assassin_solutions[0]
    print("Contoh solusi dengan Assassin:", [(m["char_type"], m["hp"], m["atk_bonus"], m["eval_profile"]) for m in sample["members"]])

print("\n=== 5. LOCAL SEARCH OPTIMIZER DENGAN ASSASSIN ===")
optimizer = NPCOptimizer()
# Skenario pemain ber-stat tinggi sehingga memicu squad AI yang kuat
best_cfg, history = optimizer.optimize(
    algorithm="SIMULATED_ANNEALING",
    player_context={"player_hp": 100, "player_atk_bonus": 10, "player_def_bonus": 4},
    randomize_start=True,
)
print("Best config found diff error:", history.get("best_error", None))
squad = NPCSquad.from_config(best_cfg)
print("Hasil Squad dari Optimizer:")
for m in squad.members:
    print(f" - {m.name} ({m.char_type}): HP={m.max_hp}, ATK=+{m.atk_bonus}, DEF=+{m.def_bonus}, Profile={m.eval_profile}")

print("\n>>> SEMUA VERIFIKASI BERHASIL! <<<")
