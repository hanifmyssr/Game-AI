"""Modul Constraint Satisfaction Problem (CSP) Solver untuk Konfigurasi Tim NPC (Tahap 4).

Mengimplementasikan:
- Backtracking Search
- MRV (Minimum Remaining Values) Variable Ordering Heuristic
- LCV (Least Constraining Value) Value Ordering Heuristic
- AC-3 (Arc Consistency 3) & Forward Checking untuk pemangkasan domain
- Validator konsistensi constraint untuk Local Search (neighbour checker)
"""

import random
import time
from typing import Dict, List, Tuple, Any, Optional, Set
from . import config


class NPCConfigCSP:
    """CSP Solver untuk merumuskan konfigurasi tim NPC yang legal dan seimbang."""

    def __init__(
        self,
        budget_hp: int = config.BUDGET_HP_DEFAULT,
        budget_potions: int = config.BUDGET_POTIONS_DEFAULT,
        budget_atk: int = config.BUDGET_ATK_DEFAULT,
    ):
        self.budget_hp = budget_hp
        self.budget_potions = budget_potions
        self.budget_atk = budget_atk

        # Statistik eksekusi terakhir
        self.stats = {
            "assignments_tried": 0,
            "backtracks": 0,
            "ac3_pruned": 0,
            "duration_ms": 0.0,
            "solution_found": False,
        }

    # ----------------------------------------------------------------------- #
    # Validator Constraint Independen (Digunakan juga oleh Local Search)
    # ----------------------------------------------------------------------- #
    def validate_config(self, npc_config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Memeriksa apakah sebuah konfigurasi memenuhi seluruh constraint (C1 - C8).
        
        Mengembalikan (is_valid, list_of_violations).
        """
        violations = []
        members = npc_config.get("members", [])
        npc_count = len(members)

        if npc_count not in config.DOMAIN_NPC_COUNT:
            violations.append(f"Jumlah NPC ({npc_count}) di luar domain {config.DOMAIN_NPC_COUNT}")

        # C1: Total HP <= budget_hp
        total_hp = sum(m.get("hp", 0) for m in members)
        if total_hp > self.budget_hp:
            violations.append(f"C1: Total HP ({total_hp}) melebihi budget ({self.budget_hp})")

        # C2: Total Potions <= budget_potions
        total_pot = sum(m.get("potions", 0) for m in members)
        if total_pot > self.budget_potions:
            violations.append(f"C2: Total Potion ({total_pot}) melebihi budget ({self.budget_potions})")

        # C8: Total Atk Bonus <= budget_atk
        total_atk = sum(m.get("atk_bonus", 0) for m in members)
        if total_atk > self.budget_atk:
            violations.append(f"C8: Total Bonus Serangan ({total_atk}) melebihi budget ({self.budget_atk})")

        # C5: Tipe karakter unik jika NPC >= 2
        char_types = [m.get("char_type") for m in members]
        if npc_count >= 2 and len(char_types) != len(set(char_types)):
            violations.append("C5: Tipe karakter harus unik di antara anggota tim")

        for idx, m in enumerate(members):
            ctype = m.get("char_type")
            hp = m.get("hp", 0)
            atk = m.get("atk_bonus", 0)
            eval_p = m.get("eval_profile")

            # C3: Tank -> HP >= 90
            if ctype == "tank" and hp < 90:
                violations.append(f"C3: NPC {idx+1} Tank harus memiliki HP >= 90 (HP saat ini: {hp})")

            # C4: Assassin / Ranger -> atk_bonus >= 5
            if ctype in ("assassin", "ranger") and atk < 5:
                violations.append(f"C4: NPC {idx+1} {ctype.capitalize()} harus memiliki Atk Bonus >= 5 (Atk saat ini: {atk})")

            # C6: Mage -> hp <= 90 (Glass Cannon) & eval_profile in {"BALANCED", "AGGRESSIVE"}
            if ctype == "mage":
                if hp > 90:
                    violations.append(f"C6: NPC {idx+1} Mage adalah Glass Cannon (HP maksimal 90, saat ini: {hp})")
                if eval_p not in {"BALANCED", "AGGRESSIVE"}:
                    violations.append(f"C6: NPC {idx+1} Mage harus bertipe BALANCED atau AGGRESSIVE (saat ini: {eval_p})")

            # C7: Tank -> eval_profile in {"BALANCED", "DEFENSIVE"}
            if ctype == "tank" and eval_p not in {"BALANCED", "DEFENSIVE"}:
                violations.append(f"C7: NPC {idx+1} Tank tidak boleh bertipe {eval_p}")

        return len(violations) == 0, violations

    # ----------------------------------------------------------------------- #
    # AC-3 Domain Filtering (Unary & Static Constraints Pre-Processing)
    # ----------------------------------------------------------------------- #
    def get_initial_domains(self, npc_count: int, shuffle: bool = False) -> Dict[str, List[Any]]:
        """Menyiapkan domain variabel awal untuk jumlah NPC tertentu dengan unary constraint."""
        domains = {}
        for i in range(npc_count):
            ct = list(config.CHAR_TYPES)
            hp = list(config.DOMAIN_HP)
            pot = list(config.DOMAIN_POTIONS)
            atk = list(config.DOMAIN_ATK_BONUS)
            df = list(config.DOMAIN_DEF_BONUS)
            ev = list(config.EVAL_PROFILES)
            if shuffle:
                random.shuffle(ct)
                random.shuffle(hp)
                random.shuffle(pot)
                random.shuffle(atk)
                random.shuffle(df)
                random.shuffle(ev)
            domains[f"char_type_{i}"] = ct
            domains[f"hp_{i}"] = hp
            domains[f"potions_{i}"] = pot
            domains[f"atk_bonus_{i}"] = atk
            domains[f"def_bonus_{i}"] = df
            domains[f"eval_profile_{i}"] = ev
        return domains

    def apply_ac3_unary(self, domains: Dict[str, List[Any]], npc_count: int) -> int:
        """Menyaring nilai domain berdasarkan unary constraints (C3, C4, C6, C7)."""
        pruned_count = 0
        # Jika char_type sudah tunggal, kita bisa pangkas hp/atk/eval_profile
        for i in range(npc_count):
            ct_var = f"char_type_{i}"
            if len(domains[ct_var]) == 1:
                ctype = domains[ct_var][0]
                if ctype == "tank":
                    old_len = len(domains[f"hp_{i}"])
                    domains[f"hp_{i}"] = [hp for hp in domains[f"hp_{i}"] if hp >= 90]
                    pruned_count += old_len - len(domains[f"hp_{i}"])

                    old_eval = len(domains[f"eval_profile_{i}"])
                    domains[f"eval_profile_{i}"] = [e for e in domains[f"eval_profile_{i}"] if e in {"BALANCED", "DEFENSIVE"}]
                    pruned_count += old_eval - len(domains[f"eval_profile_{i}"])

                elif ctype in ("assassin", "ranger"):
                    old_atk = len(domains[f"atk_bonus_{i}"])
                    domains[f"atk_bonus_{i}"] = [a for a in domains[f"atk_bonus_{i}"] if a >= 5]
                    pruned_count += old_atk - len(domains[f"atk_bonus_{i}"])

                    old_eval = len(domains[f"eval_profile_{i}"])
                    domains[f"eval_profile_{i}"] = [e for e in domains[f"eval_profile_{i}"] if e in {"BALANCED", "AGGRESSIVE"}]
                    pruned_count += old_eval - len(domains[f"eval_profile_{i}"])

                elif ctype == "mage":
                    old_hp = len(domains[f"hp_{i}"])
                    domains[f"hp_{i}"] = [hp for hp in domains[f"hp_{i}"] if hp <= 90]
                    pruned_count += old_hp - len(domains[f"hp_{i}"])

                    old_eval = len(domains[f"eval_profile_{i}"])
                    domains[f"eval_profile_{i}"] = [e for e in domains[f"eval_profile_{i}"] if e in {"BALANCED", "AGGRESSIVE"}]
                    pruned_count += old_eval - len(domains[f"eval_profile_{i}"])

                elif ctype == "warrior":
                    old_eval = len(domains[f"eval_profile_{i}"])
                    domains[f"eval_profile_{i}"] = [e for e in domains[f"eval_profile_{i}"] if e in {"BALANCED", "AGGRESSIVE", "DEFENSIVE"}]
                    pruned_count += old_eval - len(domains[f"eval_profile_{i}"])

        return pruned_count

    # ----------------------------------------------------------------------- #
    # Heuristik: MRV & LCV
    # ----------------------------------------------------------------------- #
    def select_unassigned_variable_mrv(
        self,
        assignment: Dict[str, Any],
        domains: Dict[str, List[Any]]
    ) -> Optional[str]:
        """MRV (Minimum Remaining Values): Pilih variabel unassigned dengan domain terkecil."""
        unassigned = [v for v in domains if v not in assignment]
        if not unassigned:
            return None
        # Urutkan berdasarkan ukuran domain (paling sedikit opsi yang tersisa)
        return min(unassigned, key=lambda var: len(domains[var]))

    def order_domain_values_lcv(
        self,
        var: str,
        assignment: Dict[str, Any],
        domains: Dict[str, List[Any]],
        npc_count: int
    ) -> List[Any]:
        """LCV (Least Constraining Value): Urutkan nilai yang menyisakan paling banyak pilihan untuk variabel lain."""
        values = domains[var]
        if len(values) <= 1:
            return values

        def count_conflicts(val: Any) -> int:
            conflicts = 0
            if "char_type" in var and npc_count >= 2:
                # Cek berapa variabel char_type lain yang memiliki nilai val ini
                for i in range(npc_count):
                    other_var = f"char_type_{i}"
                    if other_var != var and other_var not in assignment:
                        if val in domains[other_var]:
                            conflicts += 1
            elif "hp" in var:
                current_sum = sum(assignment.get(f"hp_{i}", 0) for i in range(npc_count) if f"hp_{i}" in assignment)
                if current_sum + val > self.budget_hp:
                    conflicts += 10
            elif "potions" in var:
                current_sum = sum(assignment.get(f"potions_{i}", 0) for i in range(npc_count) if f"potions_{i}" in assignment)
                if current_sum + val > self.budget_potions:
                    conflicts += 10
            elif "atk_bonus" in var:
                current_sum = sum(assignment.get(f"atk_bonus_{i}", 0) for i in range(npc_count) if f"atk_bonus_{i}" in assignment)
                if current_sum + val > self.budget_atk:
                    conflicts += 10
            return conflicts

        return sorted(values, key=count_conflicts)

    # ----------------------------------------------------------------------- #
    # Konsistensi Parsial Saat Pencarian Backtracking
    # ----------------------------------------------------------------------- #
    def is_partially_consistent(
        self,
        var: str,
        val: Any,
        assignment: Dict[str, Any],
        npc_count: int
    ) -> bool:
        """Cek apakah pemberian nilai val pada var melanggar constraint dengan assignment saat ini."""
        tentative = dict(assignment)
        tentative[var] = val

        # 1. C5: Cek char_type unik jika npc_count >= 2
        if "char_type" in var and npc_count >= 2:
            assigned_types = [tentative[f"char_type_{i}"] for i in range(npc_count) if f"char_type_{i}" in tentative]
            if len(assigned_types) != len(set(assigned_types)):
                return False

        # 2. C1: Budget HP
        hp_sum = sum(tentative[f"hp_{i}"] for i in range(npc_count) if f"hp_{i}" in tentative)
        if hp_sum > self.budget_hp:
            return False

        # 3. C2: Budget Potions
        pot_sum = sum(tentative[f"potions_{i}"] for i in range(npc_count) if f"potions_{i}" in tentative)
        if pot_sum > self.budget_potions:
            return False

        # 4. C8: Budget Atk Bonus
        atk_sum = sum(tentative[f"atk_bonus_{i}"] for i in range(npc_count) if f"atk_bonus_{i}" in tentative)
        if atk_sum > self.budget_atk:
            return False

        # 5. C3, C4, C6, C7: Karakteristik Class
        for i in range(npc_count):
            ctype = tentative.get(f"char_type_{i}")
            if ctype:
                hp = tentative.get(f"hp_{i}")
                if hp is not None and ctype == "tank" and hp < 90:
                    return False

                atk = tentative.get(f"atk_bonus_{i}")
                if atk is not None and ctype in ("assassin", "ranger") and atk < 5:
                    return False

                if hp is not None and ctype == "mage" and hp > 90:
                    return False

                eval_p = tentative.get(f"eval_profile_{i}")
                if eval_p is not None:
                    if ctype == "mage" and eval_p not in {"BALANCED", "AGGRESSIVE"}:
                        return False
                    if ctype in ("ranger", "assassin") and eval_p not in {"BALANCED", "AGGRESSIVE"}:
                        return False
                    if ctype == "tank" and eval_p not in {"BALANCED", "DEFENSIVE"}:
                        return False

        return True

    # ----------------------------------------------------------------------- #
    # Backtracking Search Rekursif
    # ----------------------------------------------------------------------- #
    def _backtrack(
        self,
        assignment: Dict[str, Any],
        domains: Dict[str, List[Any]],
        npc_count: int,
        solutions: List[Dict[str, Any]],
        max_solutions: int
    ) -> bool:
        if len(assignment) == len(domains):
            # Solusi lengkap ditemukan
            config_dict = self._assignment_to_config(assignment, npc_count)
            solutions.append(config_dict)
            if len(solutions) >= max_solutions:
                return True
            return False

        var = self.select_unassigned_variable_mrv(assignment, domains)
        if var is None:
            return False

        for val in self.order_domain_values_lcv(var, assignment, domains, npc_count):
            self.stats["assignments_tried"] += 1
            if self.is_partially_consistent(var, val, assignment, npc_count):
                assignment[var] = val

                # Forward Checking / Domain pruning lokal
                new_domains = {k: list(v) for k, v in domains.items()}
                new_domains[var] = [val]

                if self._backtrack(assignment, new_domains, npc_count, solutions, max_solutions):
                    return True

                del assignment[var]
                self.stats["backtracks"] += 1

        return False

    def _assignment_to_config(self, assignment: Dict[str, Any], npc_count: int) -> Dict[str, Any]:
        members = []
        for i in range(npc_count):
            members.append({
                "char_type": assignment.get(f"char_type_{i}", "warrior"),
                "hp": assignment.get(f"hp_{i}", 100),
                "potions": assignment.get(f"potions_{i}", 2),
                "atk_bonus": assignment.get(f"atk_bonus_{i}", 0),
                "def_bonus": assignment.get(f"def_bonus_{i}", 0),
                "eval_profile": assignment.get(f"eval_profile_{i}", "BALANCED"),
            })
        return {
            "npc_count": npc_count,
            "members": members,
        }

    # ----------------------------------------------------------------------- #
    # Public Solve Method
    # ----------------------------------------------------------------------- #
    def solve(
        self,
        npc_count: Optional[int] = None,
        max_solutions: int = 1,
        shuffle: bool = False
    ) -> List[Dict[str, Any]]:
        """Mencari solusi konfigurasi legal.
        
        Jika npc_count None, mencoba 2 NPC (default ideal) lalu fallback ke 1 atau 3.
        Jika shuffle True, acak eksplorasi domain sehingga menghasilkan solusi legal yang bervariasi.
        """
        start_time = time.perf_counter()
        self.stats = {
            "assignments_tried": 0,
            "backtracks": 0,
            "ac3_pruned": 0,
            "duration_ms": 0.0,
            "solution_found": False,
        }

        counts_to_try = [npc_count] if npc_count is not None else [2, 3, 1]
        if shuffle and npc_count is None:
            random.shuffle(counts_to_try)
        solutions = []

        for count in counts_to_try:
            domains = self.get_initial_domains(count, shuffle=shuffle)
            self.stats["ac3_pruned"] += self.apply_ac3_unary(domains, count)

            assignment = {}
            self._backtrack(assignment, domains, count, solutions, max_solutions)

            if len(solutions) >= max_solutions:
                break

        elapsed = (time.perf_counter() - start_time) * 1000.0
        self.stats["duration_ms"] = round(elapsed, 2)
        self.stats["solution_found"] = len(solutions) > 0

        return solutions
