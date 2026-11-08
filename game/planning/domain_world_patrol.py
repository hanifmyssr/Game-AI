"""Domain & Problem Formal PDDL: Patroli Dunia & Pertahanan Peti Harta.

Memodelkan skenario koordinasi patroli NPC saat Bolu menjarah salah satu peti:
Kuro beralih mencegat dan mengejar Bolu di jembatan perbatasan,
sementara Shiro mengunci perimeter dan menjaga sisa peti yang belum dijarah.
"""

from typing import Tuple, Set, List
from .pddl_types import Predicate, State, ActionSchema


def create_world_patrol_problem(looted_chest: str = "A") -> Tuple[State, Set[Predicate], List[ActionSchema]]:
    """Membangun Initial State (s0), Goal, dan Aksi STRIPS untuk skenario eksplorasi."""

    # 1. INITIAL STATE (s0)
    s0_preds = {
        Predicate("At", ("Kuro", "Tebing_Utara")),
        Predicate("At", ("Shiro", "Dermaga_Timur")),
        Predicate("ChestLooted", (looted_chest,)),
        Predicate("HasLootedItem", ("Bolu",)),
        Predicate("UnopenedChest", ("B",)),
        Predicate("UnopenedChest", ("C",)),
    }
    s0 = State(s0_preds)

    # 2. GOAL STATE
    # Target: Kuro berhasil menghadang Bolu dan perimeter sisa peti berhasil dikunci aman
    goal = {
        Predicate("InCombat", ("Kuro", "Bolu")),
        Predicate("PerimeterLocked", ("B",)),
        Predicate("IslandSecure", ()),
    }

    # 3. ACTION SCHEMAS
    actions = [
        # Aksi 1: Kuro bergerak dari Tebing Utara ke Jembatan Choke-Point
        ActionSchema(
            name="MoveToChokePoint",
            parameters=("Kuro", "Tebing_Utara", "Jembatan"),
            preconditions={
                Predicate("At", ("Kuro", "Tebing_Utara")),
                Predicate("ChestLooted", (looted_chest,)),
            },
            add_list={
                Predicate("At", ("Kuro", "Jembatan")),
            },
            del_list={
                Predicate("At", ("Kuro", "Tebing_Utara")),
            },
            cost=1.0,
            description="Kuro berlari memotong jalur pelarian Bolu di jembatan"
        ),

        # Aksi 2: Kuro mencegat Bolu yang membawa jarahan di Jembatan
        ActionSchema(
            name="InterceptPlayer",
            parameters=("Kuro", "Bolu", "Jembatan"),
            preconditions={
                Predicate("At", ("Kuro", "Jembatan")),
                Predicate("HasLootedItem", ("Bolu",)),
            },
            add_list={
                Predicate("InCombat", ("Kuro", "Bolu")),
                Predicate("ChasingPlayer", ("Kuro",)),
            },
            del_list=set(),
            cost=1.0,
            description="Kuro menghadang langsung dan memulai perburuan"
        ),

        # Aksi 3: Shiro bergerak merapat ke sektor Peti B
        ActionSchema(
            name="MoveToSector",
            parameters=("Shiro", "Dermaga_Timur", "Peti_B"),
            preconditions={
                Predicate("At", ("Shiro", "Dermaga_Timur")),
                Predicate("ChasingPlayer", ("Kuro",)),
            },
            add_list={
                Predicate("At", ("Shiro", "Peti_B")),
            },
            del_list={
                Predicate("At", ("Shiro", "Dermaga_Timur")),
            },
            cost=1.0,
            description="Shiro merapat ke lokasi peti kedua"
        ),

        # Aksi 4: Shiro memasang barikade siaga menjaga Peti B
        ActionSchema(
            name="ReinforceGuard",
            parameters=("Shiro", "Peti_B"),
            preconditions={
                Predicate("At", ("Shiro", "Peti_B")),
                Predicate("UnopenedChest", ("B",)),
            },
            add_list={
                Predicate("PerimeterLocked", ("B",)),
                Predicate("IslandSecure", ()),
            },
            del_list=set(),
            cost=1.0,
            description="Shiro mengunci akses perimeter pulau sehingga sisa peti aman"
        ),
    ]

    return s0, goal, actions

