"""Domain & Problem Formal PDDL: Taktik Rotasi & Pemulihan Skuad Battle Tag-Team.

Memodelkan skenario koordinasi skuad NPC di arena pertarungan:
1. Warrior yang sekarat (HP <= 35%) mundur ke cadangan (Swap-Retreat).
2. Tank maju ke garis depan dan memasang pertahanan kokoh (Cast-Defend).
3. Mage di bangku cadangan merapalkan mantra pemulih HP ke Warrior (Heal-Teammate).
"""

from typing import Tuple, Set, List
from .pddl_types import Predicate, State, ActionSchema


def create_battle_tactics_problem(warrior_name: str = "Oyen",
                                  tank_name: str = "Kage",
                                  healer_name: str = "Shiro") -> Tuple[State, Set[Predicate], List[ActionSchema]]:
    """Membangun Initial State (s0), Goal, dan Aksi STRIPS untuk skenario Battle Tag-Team."""

    # 1. INITIAL STATE (s0)
    s0_preds = {
        Predicate("ActiveFrontline", (warrior_name,)),
        Predicate("InBench", (tank_name,)),
        Predicate("InBench", (healer_name,)),
        Predicate("HPCritical", (warrior_name,)),
        Predicate("IsTank", (tank_name,)),
        Predicate("IsHealer", (healer_name,)),
        Predicate("HasHealCharge", (healer_name,)),
    }
    s0 = State(s0_preds)

    # 2. GOAL STATE
    # Target: Tank aktif bertahan di garis depan dan Warrior telah dipulihkan di bangku cadangan
    goal = {
        Predicate("ActiveFrontline", (tank_name,)),
        Predicate("GuardActive", (tank_name,)),
        Predicate("Healed", (warrior_name,)),
        Predicate("HPHealthy", (warrior_name,)),
    }

    # 3. ACTION SCHEMAS STRIPS
    actions = [
        # Aksi 1: Pertukaran Pejuang (Warrior mundur, Tank maju)
        ActionSchema(
            name="SwapRetreat",
            parameters=(warrior_name, tank_name),
            preconditions={
                Predicate("ActiveFrontline", (warrior_name,)),
                Predicate("InBench", (tank_name,)),
                Predicate("HPCritical", (warrior_name,)),
                Predicate("IsTank", (tank_name,)),
            },
            add_list={
                Predicate("InBench", (warrior_name,)),
                Predicate("ActiveFrontline", (tank_name,)),
            },
            del_list={
                Predicate("ActiveFrontline", (warrior_name,)),
                Predicate("InBench", (tank_name,)),
            },
            cost=1.0,
            description=f"{warrior_name} mundur ke cadangan, digantikan {tank_name} yang maju ke garis depan"
        ),

        # Aksi 2: Tank mengaktifkan perisai pertahanan
        ActionSchema(
            name="CastDefend",
            parameters=(tank_name,),
            preconditions={
                Predicate("ActiveFrontline", (tank_name,)),
                Predicate("IsTank", (tank_name,)),
            },
            add_list={
                Predicate("GuardActive", (tank_name,)),
            },
            del_list=set(),
            cost=1.0,
            description=f"{tank_name} memasang perisai pertahanan menahan serangan Bolu"
        ),

        # Aksi 3: Healer di cadangan memulihkan HP rekan yang sekarat
        ActionSchema(
            name="HealTeammate",
            parameters=(healer_name, warrior_name),
            preconditions={
                Predicate("InBench", (healer_name,)),
                Predicate("IsHealer", (healer_name,)),
                Predicate("HasHealCharge", (healer_name,)),
                Predicate("InBench", (warrior_name,)),
                Predicate("HPCritical", (warrior_name,)),
                Predicate("GuardActive", (tank_name,)),
            },
            add_list={
                Predicate("Healed", (warrior_name,)),
                Predicate("HPHealthy", (warrior_name,)),
            },
            del_list={
                Predicate("HPCritical", (warrior_name,)),
                Predicate("HasHealCharge", (healer_name,)),
            },
            cost=1.0,
            description=f"{healer_name} merapalkan sihir pemulih HP ke {warrior_name} yang terlindung"
        ),
    ]

    return s0, goal, actions

