import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from game.battle_ai import BattleState, ACTION_ATTACK, calc_damage, ATTACK_DAMAGE
from game.npc_squad import NPCSquad, NPCMember
from game.battle_system import BattleSystem

def test_spoils_of_war():
    print("=== TEST SPOILS OF WAR (RAMPASAN PERANG) ===")

    # Squad: 1 Warrior (HP 15) and 1 Ranger (HP 60)
    squad = NPCSquad([
        NPCMember("Oyen the Warrior", "warrior", max_hp=15, current_hp=15),
        NPCMember("Kuro the Ranger", "ranger", max_hp=60, current_hp=60),
    ])

    class MockPlayer:
        persistent_hp = 50
        persistent_potions = 1
        atk_bonus = 0
        def_bonus = 0
        inventory = []

    player = MockPlayer()
    bs = BattleSystem()
    bs.reset_with_squad(squad, player_hp=50, player_potions=1, player_atk=0, player_def=0, player=player)

    print(f"Initial Player: ATK Bonus={bs.state.player_atk_bonus}, DEF Bonus={bs.state.player_def_bonus}")
    assert bs.state.player_atk_bonus == 0
    assert bs.state.player_def_bonus == 0

    # Player attacks and kills Warrior (20 HP -> 0 HP)
    bs.execute_player_action(ACTION_ATTACK)

    print("\n--- After Defeating Oyen the Warrior ---")
    print(f"Last Loot: {bs.last_loot}")
    print(f"Player ATK Bonus now: {bs.state.player_atk_bonus}")
    print(f"Player DEF Bonus now: {bs.state.player_def_bonus}")
    print(f"Player Inventory: {player.inventory}")

    # Verify loot from Warrior: +4 ATK, +1 DEF
    assert bs.last_loot is not None
    assert "Pedang Ksatria Oyen" in bs.last_loot["name"]
    assert bs.state.player_atk_bonus == 4
    assert bs.state.player_def_bonus == 1
    assert player.atk_bonus == 4
    assert player.def_bonus == 1
    assert "Pedang Ksatria Oyen" in player.inventory

    # Check damage projection with new weapon vs Kuro the Ranger
    new_dmg = calc_damage(ATTACK_DAMAGE, bs.state.player_atk_bonus, bs.state.npc_def_bonus, is_heavy=False)
    print(f"Projected Attack Damage vs Ranger: {new_dmg} (increased from base 18)")
    assert new_dmg > 18

    # Now defeat Kuro the Ranger (60 HP)
    bs.state.is_npc_turn = False
    bs.state.npc_hp = 10
    bs.execute_player_action(ACTION_ATTACK)

    print("\n--- After Defeating Final Member (Kuro the Ranger) ---")
    print(f"Winner: {bs.winner}")
    print(f"Final Loot: {bs.last_loot}")
    print(f"Total Player ATK Bonus: {bs.state.player_atk_bonus}")
    print(f"Player Inventory: {player.inventory}")

    assert bs.winner == "PLAYER"
    assert "Busur Presisi Kuro" in bs.last_loot["name"]
    # 4 ATK + 3 ATK from Bow = 7 ATK
    assert bs.state.player_atk_bonus == 7
    assert "Busur Presisi Kuro" in player.inventory

    print("\n ALL SPOILS OF WAR TESTS PASSED!")

if __name__ == "__main__":
    test_spoils_of_war()
