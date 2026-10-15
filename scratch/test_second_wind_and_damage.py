import sys
import os

# Set root repo to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.battle_ai import (
    BattleState,
    ACTION_ATTACK,
    ACTION_HEAVY,
    ACTION_DEFEND,
    ACTION_POTION,
    ATTACK_DAMAGE,
    HEAVY_DAMAGE,
    NPC_ATTACK_DAMAGE,
    NPC_HEAVY_DAMAGE,
    NPC_ATTACK_DEFENDED_DAMAGE,
    NPC_HEAVY_DEFENDED_DAMAGE,
    calc_damage,
)
from game.npc_squad import NPCSquad, NPCMember
from game.battle_system import BattleSystem

def test_damage_values():
    print("--- 1. Testing Damage Reduction for NPC ---")
    # Verify player base damage remains full
    assert ATTACK_DAMAGE == 18, f"Player attack base should be 18, got {ATTACK_DAMAGE}"
    assert HEAVY_DAMAGE == 30, f"Player heavy base should be 30, got {HEAVY_DAMAGE}"

    # Verify NPC base damage is reduced
    assert NPC_ATTACK_DAMAGE == 14, f"NPC attack base should be 14, got {NPC_ATTACK_DAMAGE}"
    assert NPC_HEAVY_DAMAGE == 24, f"NPC heavy base should be 24, got {NPC_HEAVY_DAMAGE}"
    assert NPC_ATTACK_DEFENDED_DAMAGE == 5, f"NPC attack defended should be 5, got {NPC_ATTACK_DEFENDED_DAMAGE}"
    assert NPC_HEAVY_DEFENDED_DAMAGE == 8, f"NPC heavy defended should be 8, got {NPC_HEAVY_DEFENDED_DAMAGE}"

    # Test Player turn dealing damage to NPC
    s = BattleState(player_hp=100, npc_hp=100, is_npc_turn=False)
    next_s = s.apply_action(ACTION_ATTACK)
    dmg_to_npc = s.npc_hp - next_s.npc_hp
    print(f"Player Attack deals: {dmg_to_npc} damage (expected 18)")
    assert dmg_to_npc == 18, f"Expected 18, got {dmg_to_npc}"

    next_s_heavy = s.apply_action(ACTION_HEAVY)
    dmg_to_npc_heavy = s.npc_hp - next_s_heavy.npc_hp
    print(f"Player Heavy deals: {dmg_to_npc_heavy} damage (expected 30)")
    assert dmg_to_npc_heavy == 30, f"Expected 30, got {dmg_to_npc_heavy}"

    # Test NPC turn dealing damage to Player
    s_npc = BattleState(player_hp=100, npc_hp=100, is_npc_turn=True)
    next_s_npc = s_npc.apply_action(ACTION_ATTACK)
    dmg_to_player = s_npc.player_hp - next_s_npc.player_hp
    print(f"NPC Attack deals: {dmg_to_player} damage (expected 14, reduced from 18)")
    assert dmg_to_player == 14, f"Expected 14, got {dmg_to_player}"

    next_s_npc_heavy = s_npc.apply_action(ACTION_HEAVY)
    dmg_to_player_heavy = s_npc.player_hp - next_s_npc_heavy.player_hp
    print(f"NPC Heavy deals: {dmg_to_player_heavy} damage (expected 24, reduced from 30)")
    assert dmg_to_player_heavy == 24, f"Expected 24, got {dmg_to_player_heavy}"

    # Test Player defending against NPC Attack & Heavy
    s_player_def = BattleState(player_hp=100, npc_hp=100, player_defending=True, is_npc_turn=True)
    next_def = s_player_def.apply_action(ACTION_ATTACK)
    dmg_def = s_player_def.player_hp - next_def.player_hp
    print(f"NPC Attack vs Defending Player deals: {dmg_def} damage (expected 5)")
    assert dmg_def == 5, f"Expected 5, got {dmg_def}"

    next_def_heavy = s_player_def.apply_action(ACTION_HEAVY)
    dmg_def_heavy = s_player_def.player_hp - next_def_heavy.player_hp
    print(f"NPC Heavy vs Defending Player deals: {dmg_def_heavy} damage (expected 8)")
    assert dmg_def_heavy == 8, f"Expected 8, got {dmg_def_heavy}"

    print(" Damage values verified successfully!")

def test_second_wind():
    print("\n--- 2. Testing Option A: Second Wind on Squad Tag-in ---")
    squad = NPCSquad([
        NPCMember("Oyen the Warrior", "warrior", max_hp=50, current_hp=50),
        NPCMember("Kuro the Ranger", "ranger", max_hp=60, current_hp=60),
    ])

    class MockPlayer:
        persistent_hp = 30
        persistent_potions = 1
        atk_bonus = 0
        def_bonus = 0

    player = MockPlayer()
    bs = BattleSystem()
    bs.reset_with_squad(squad, player_hp=30, player_potions=1, player=player)

    # Put heavy on cooldown
    bs.state.player_heavy_cd = 2
    bs.state.player_hp = 35
    bs.state.player_potions = 1
    player.persistent_hp = 35
    player.persistent_potions = 1

    # Now reduce first NPC's HP to 0 by Player attack
    print(f"Initial Player HP: {bs.state.player_hp}, Potions: {bs.state.player_potions}, Heavy CD: {bs.state.player_heavy_cd}")
    bs.state.npc_hp = 10
    bs.execute_player_action(ACTION_ATTACK) # deals 18 damage -> NPC hp <= 0

    print(f"After defeating NPC 1:")
    print(f"Player HP: {bs.state.player_hp} (Expected 35 + 45 = 80)")
    print(f"Player Potions: {bs.state.player_potions} (Expected 1 + 1 = 2)")
    print(f"Player Heavy CD: {bs.state.player_heavy_cd} (Expected 0)")
    print(f"Persistent HP on Player object: {player.persistent_hp}")
    print(f"Persistent Potions on Player object: {player.persistent_potions}")
    print(f"Action text above Player: {bs.player_action_text}")
    print(f"Action text above NPC: {bs.npc_action_text}")

    assert bs.state.player_hp == 80, f"Expected 80 HP, got {bs.state.player_hp}"
    assert bs.state.player_potions == 2, f"Expected 2 potions, got {bs.state.player_potions}"
    assert bs.state.player_heavy_cd == 0, f"Expected heavy CD 0, got {bs.state.player_heavy_cd}"
    assert player.persistent_hp == 80
    assert player.persistent_potions == 2
    assert bs.player_action_text is not None
    assert "SECOND WIND!" in bs.player_action_text["text"]
    assert bs.npc_action_text is not None
    assert "TAG-IN!" in bs.npc_action_text["text"]

    print(" Second Wind reward logic verified successfully!")

if __name__ == "__main__":
    test_damage_values()
    test_second_wind()
    print("\n ALL TESTS PASSED!")
