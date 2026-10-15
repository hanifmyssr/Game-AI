import sys
sys.path.insert(0, ".")
from game.battle_system import BattleSystem
from game.battle_ai import ACTION_ATTACK, ACTION_HEAVY, ACTION_DEFEND, ACTION_POTION
from game.npc_squad import NPCSquad, NPCMember

bs = BattleSystem()
# Create squad with Ranger
member = NPCMember("Kuro the Ranger", "ranger", max_hp=80, potions=1, atk_bonus=10, def_bonus=0, eval_profile="AGGRESSIVE")
squad = NPCSquad([member])
bs.reset_with_squad(squad, player_hp=100, player_atk=0, player_def=0)

print("Initial legal actions for NPC (calc):")
bs.state.is_npc_turn = True
print("NPC legal actions:", bs.state.get_legal_actions())
bs.state.is_npc_turn = False

# Turn 1: Player attacks
print("\n--- Turn 1: Player attacks ---")
bs.execute_player_action(ACTION_ATTACK)
print("Logs:", bs.battle_logs[-1])
print("Player HP:", bs.state.player_hp, "NPC HP:", bs.state.npc_hp)
print("is_npc_turn:", bs.state.is_npc_turn, "npc_heavy_cd:", bs.state.npc_heavy_cd)

# Turn 1: NPC acts
print("\n--- Turn 1: NPC acts ---")
act = bs.execute_npc_turn()
print("NPC action:", act)
print("Logs:", bs.battle_logs[-1])
print("Player HP:", bs.state.player_hp, "NPC HP:", bs.state.npc_hp)
print("is_npc_turn:", bs.state.is_npc_turn, "npc_heavy_cd:", bs.state.npc_heavy_cd)

# Turn 2: Player attacks
print("\n--- Turn 2: Player attacks ---")
bs.execute_player_action(ACTION_ATTACK)
print("Logs:", bs.battle_logs[-1])
print("Player HP:", bs.state.player_hp, "NPC HP:", bs.state.npc_hp)
print("is_npc_turn:", bs.state.is_npc_turn, "npc_heavy_cd:", bs.state.npc_heavy_cd)

# Turn 2: NPC acts
print("\n--- Turn 2: NPC acts ---")
act2 = bs.execute_npc_turn()
print("NPC action:", act2)
print("Logs:", bs.battle_logs[-1])
print("Player HP:", bs.state.player_hp, "NPC HP:", bs.state.npc_hp)
print("is_npc_turn:", bs.state.is_npc_turn, "npc_heavy_cd:", bs.state.npc_heavy_cd)

# Turn 3: Player attacks
print("\n--- Turn 3: Player attacks ---")
bs.execute_player_action(ACTION_ATTACK)
print("Logs:", bs.battle_logs[-1])
print("Player HP:", bs.state.player_hp, "NPC HP:", bs.state.npc_hp)
print("is_npc_turn:", bs.state.is_npc_turn, "npc_heavy_cd:", bs.state.npc_heavy_cd)

# Turn 3: NPC acts
print("\n--- Turn 3: NPC acts ---")
act3 = bs.execute_npc_turn()
print("NPC action:", act3)
print("Logs:", bs.battle_logs[-1])
print("Player HP:", bs.state.player_hp, "NPC HP:", bs.state.npc_hp)
print("is_npc_turn:", bs.state.is_npc_turn, "npc_heavy_cd:", bs.state.npc_heavy_cd)
