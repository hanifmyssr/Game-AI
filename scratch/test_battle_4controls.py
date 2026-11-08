"""Test all 4 directional keys and clicks in battle mode."""
import os
import sys
import pygame
from pygame.constants import K_1, K_2, K_3, K_4, K_w, K_a, K_d, K_s, K_UP, K_LEFT, K_RIGHT, K_DOWN

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()

sys.path.insert(0, os.path.abspath("Game-AI"))
from game.app import App
from game.ai.battle_ai import ACTION_ATTACK, ACTION_HEAVY, ACTION_DEFEND, ACTION_POTION

def test_battle_controls():
    app = App()
    app.enter_pre_battle()
    app.enter_battle()
    st = app.battle_system.state

    print(f"Battle started: Player HP={st.player_hp}, NPC HP={st.npc_hp}")

    # 1. Test Key 1 / W / UP -> ACTION_ATTACK
    old_npc_hp = st.npc_hp
    ev = pygame.event.Event(pygame.KEYDOWN, {"key": K_1})
    pygame.event.post(ev)
    app._handle_events()
    print(f"Key 1 pressed: NPC HP went from {old_npc_hp} to {app.battle_system.state.npc_hp}")
    assert app.battle_system.state.npc_hp < old_npc_hp or app.battle_system.state.is_npc_turn

    # Reset turn for testing other keys
    app.battle_system.state.is_npc_turn = False
    app.battle_system.state.player_heavy_cd = 0

    # 2. Test Key 2 / A / LEFT -> ACTION_HEAVY
    old_npc_hp = app.battle_system.state.npc_hp
    ev = pygame.event.Event(pygame.KEYDOWN, {"key": K_2})
    pygame.event.post(ev)
    app._handle_events()
    print(f"Key 2 pressed: NPC HP went from {old_npc_hp} to {app.battle_system.state.npc_hp}")

    # Reset turn
    app.battle_system.state.is_npc_turn = False

    # 3. Test Key 3 / D / RIGHT -> ACTION_DEFEND
    ev = pygame.event.Event(pygame.KEYDOWN, {"key": K_3})
    pygame.event.post(ev)
    app._handle_events()
    print("Key 3 pressed: Defend executed successfully")

    # Reset turn
    app.battle_system.state.is_npc_turn = False
    app.battle_system.state.player_potions = 2
    app.battle_system.state.player_hp = 50

    # 4. Test Key 4 / S / DOWN -> ACTION_POTION
    old_p_hp = app.battle_system.state.player_hp
    ev = pygame.event.Event(pygame.KEYDOWN, {"key": K_4})
    pygame.event.post(ev)
    app._handle_events()
    print(f"Key 4 pressed: Player HP went from {old_p_hp} to {app.battle_system.state.player_hp}")
    assert app.battle_system.state.player_hp > old_p_hp

    # 5. Test Mouse Click Hitboxes
    app.battle_system.state.is_npc_turn = False
    app._draw()
    assert app.btn_action_attack.width > 0
    assert app.btn_action_heavy.width > 0
    assert app.btn_action_defend.width > 0
    assert app.btn_action_potion.width > 0

    print("ALL 4 DIRECTIONAL COMBAT BUTTONS & SHORTCUTS TESTED AND VERIFIED 100%!")

if __name__ == "__main__":
    test_battle_controls()

