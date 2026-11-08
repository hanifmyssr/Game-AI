"""Tipe Data Formal Classical Planning PDDL / STRIPS.

Mendefinisikan Predikat relasional, State fluents (himpunan predikat),
dan Skema Aksi STRIPS (Preconditions, Add-List, Delete-List)
sesuai kaidah perkuliahan AI dan silabus dosen.
"""

from typing import Tuple, Set, FrozenSet, Dict, Any, Optional, List


class Predicate:
    """Predikat formal PDDL dengan nama dan daftar argumen objek.
    
    Contoh: Predicate("at-npc", ("kuro", "jembatan"))
    """

    def __init__(self, name: str, args: Tuple[str, ...] = ()):
        self.name = name.strip()
        self.args = tuple(str(a).strip() for a in args)
        self._hash = hash((self.name, self.args))

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Predicate):
            return False
        return self.name == other.name and self.args == other.args

    def __repr__(self) -> str:
        if not self.args:
            return self.name
        return f"{self.name}({', '.join(self.args)})"

    @classmethod
    def from_str(cls, s: str) -> "Predicate":
        """Parsing string seperti 'At(kuro, jembatan)' menjadi objek Predicate."""
        s = s.strip()
        if "(" not in s or not s.endswith(")"):
            return cls(s, ())
        name, rest = s.split("(", 1)
        args_str = rest[:-1]
        args = tuple(a.strip() for a in args_str.split(",") if a.strip())
        return cls(name.strip(), args)


class State:
    """Himpunan predikat yang mendeskripsikan keadaan dunia (State Fluents)."""

    def __init__(self, predicates: Optional[Set[Predicate]] = None):
        self.predicates: FrozenSet[Predicate] = frozenset(predicates or set())
        self._hash = hash(self.predicates)

    def satisfies(self, conditions: Set[Predicate]) -> bool:
        """Mengecek apakah state saat ini memenuhi himpunan prekondisi."""
        return conditions.issubset(self.predicates)

    def apply(self, action: "ActionSchema") -> "State":
        r"""Menerapkan aksi ke state saat ini: Result(s, a) = (s \ del) U add."""
        new_preds = set(self.predicates)
        new_preds.difference_update(action.del_list)
        new_preds.update(action.add_list)
        return State(new_preds)

    def __contains__(self, predicate: Predicate) -> bool:
        return predicate in self.predicates

    def __len__(self) -> int:
        return len(self.predicates)

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, State):
            return False
        return self.predicates == other.predicates

    def __repr__(self) -> str:
        sorted_preds = sorted(list(self.predicates), key=lambda p: repr(p))
        return f"State({{{', '.join(repr(p) for p in sorted_preds)}}})"


class ActionSchema:
    """Operator Aksi STRIPS dengan Preconditions, Add-List, dan Delete-List."""

    def __init__(self, name: str,
                 parameters: Tuple[str, ...] = (),
                 preconditions: Optional[Set[Predicate]] = None,
                 add_list: Optional[Set[Predicate]] = None,
                 del_list: Optional[Set[Predicate]] = None,
                 cost: float = 1.0,
                 description: str = ""):
        self.name = name.strip()
        self.parameters = tuple(parameters)
        self.preconditions: Set[Predicate] = set(preconditions or set())
        self.add_list: Set[Predicate] = set(add_list or set())
        self.del_list: Set[Predicate] = set(del_list or set())
        self.cost = cost
        self.description = description
        self._hash = hash((self.name, self.parameters))

    def is_applicable(self, state: State) -> bool:
        """Aksi berlaku jika prekondisi merupakan subset dari state (pre(a) ⊆ s)."""
        return self.preconditions.issubset(state.predicates)

    def is_relevant(self, goal_set: Set[Predicate]) -> bool:
        """Aksi relevan untuk regresi mundur jika menambahkan setidaknya 1 sasaran (add(a) ∩ g != ∅)."""
        return bool(self.add_list & goal_set)

    def is_consistent(self, goal_set: Set[Predicate]) -> bool:
        """Aksi konsisten jika tidak menghapus sasaran yang dibutuhkan (del(a) ∩ g == ∅)."""
        return not bool(self.del_list & goal_set)

    def regress(self, goal_set: Set[Predicate]) -> Set[Predicate]:
        r"""Menghitung sub-goal baru melalui regresi: g' = (g \ add(a)) U pre(a)."""
        new_goal = set(goal_set)
        new_goal.difference_update(self.add_list)
        new_goal.update(self.preconditions)
        return new_goal

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ActionSchema):
            return False
        return self.name == other.name and self.parameters == other.parameters

    def __repr__(self) -> str:
        if not self.parameters:
            return self.name
        return f"{self.name}({', '.join(self.parameters)})"
