"""Basis Pengetahuan (Knowledge Base) Proposisional & Aturan CNF.

Mendefinisikan representasi klausa bentuk konjungtif normal (CNF)
sebagai frozenset literal bertanda (signed literals), operasi penambahan
fakta (TELL), penarikan kesimpulan (ASK), serta kumpulan aturan deklaratif
koordinasi patroli 3 NPC sesuai standar akademis perkuliahan AI.
"""

from typing import Set, List, Tuple, Dict, Optional, FrozenSet, Union


def is_negative(literal: str) -> bool:
    """Mengembalikan True jika literal merupakan negasi (~P)."""
    return literal.startswith("~")


def negate_literal(literal: str) -> str:
    """Membalik tanda literal: P -> ~P, dan ~P -> P."""
    if is_negative(literal):
        return literal[1:]
    return f"~{literal}"


def complement(lit1: str, lit2: str) -> bool:
    """Mengembalikan True jika lit1 dan lit2 saling berkomplemen (misal P dan ~P)."""
    return lit1 == negate_literal(lit2)


def clause_to_str(clause: FrozenSet[str]) -> str:
    """Format klausa frozenset ke representasi string terbaca, misal: (~A | B)."""
    if not clause:
        return "[]"  # Klausa kosong (kontradiksi)
    sorted_lits = sorted(list(clause), key=lambda x: (x.lstrip("~"), x))
    return f"({' ∨ '.join(sorted_lits)})"


class KnowledgeBase:
    """Knowledge Base Proposisional yang menyimpan aturan CNF dan fakta sensorik."""

    def __init__(self):
        # Himpunan semua klausa CNF (frozenset of signed literals)
        self.clauses: Set[FrozenSet[str]] = set()
        # Riwayat fakta sensorik yang dimasukkan via TELL
        self.facts: Set[str] = set()
        # Metadata aturan formal (ID, deskripsi FOL, bentuk CNF)
        self.rules_meta: List[Dict[str, Any]] = []

        # Inisialisasi aturan-aturan logika koordinasi patroli NPC
        self._load_default_patrol_rules()

    def _load_default_patrol_rules(self) -> None:
        """Memuat aturan-aturan CNF koordinasi 3 NPC menjaga 4 peti di seluruh peta."""
        # Rule 1A: Jika Peti A dibuka, maka Kuro bersiaga
        self.add_rule(
            rule_id="R1A",
            name="Deteksi Peti A Terbuka",
            fol_str="ChestOpened(A) => Alert(Kuro)",
            clause=frozenset({"~ChestOpened_A", "Alert_Kuro"}),
            description="Kuro bersiaga jika Peti A (timur-laut) dijarah"
        )

        # Rule 1B: Jika Peti B dibuka, maka Kuro bersiaga (sektor tebing barat)
        self.add_rule(
            rule_id="R1B",
            name="Deteksi Peti B Terbuka",
            fol_str="ChestOpened(B) => Alert(Kuro)",
            clause=frozenset({"~ChestOpened_B", "Alert_Kuro"}),
            description="Kuro bersiaga jika Peti B (barat-laut) dijarah"
        )

        # Rule 1C: Jika Peti C dibuka, maka Shiro bersiaga (sektor dermaga tenggara)
        self.add_rule(
            rule_id="R1C",
            name="Deteksi Peti C Terbuka",
            fol_str="ChestOpened(C) => Alert(Shiro)",
            clause=frozenset({"~ChestOpened_C", "Alert_Shiro"}),
            description="Shiro bersiaga jika Peti C (dermaga tenggara) dijarah"
        )

        # Rule 1D: Jika Peti D dibuka, maka Shiro bersiaga (sektor selatan)
        self.add_rule(
            rule_id="R1D",
            name="Deteksi Peti D Terbuka",
            fol_str="ChestOpened(D) => Alert(Shiro)",
            clause=frozenset({"~ChestOpened_D", "Alert_Shiro"}),
            description="Shiro bersiaga jika Peti D (selatan) dijarah"
        )

        # Rule 2A: Jika Kuro siaga dan Player mengambil jarahan, tugaskan Kuro mengejar Player
        self.add_rule(
            rule_id="R2A",
            name="Penugasan Pemburu Kuro",
            fol_str="Alert(Kuro) ∧ HasLootedItem(Player) => AssignChaser(Kuro)",
            clause=frozenset({"~Alert_Kuro", "~HasLootedItem_Player", "AssignChaser_Kuro"}),
            description="Kuro beralih menjadi pemburu agresif untuk memotong jalur Bolu"
        )

        # Rule 2B: Jika Shiro siaga dan Player mengambil jarahan, tugaskan Shiro mengejar Player
        self.add_rule(
            rule_id="R2B",
            name="Penugasan Pemburu Shiro",
            fol_str="Alert(Shiro) ∧ HasLootedItem(Player) => AssignChaser(Shiro)",
            clause=frozenset({"~Alert_Shiro", "~HasLootedItem_Player", "AssignChaser_Shiro"}),
            description="Shiro beralih menjadi pemburu agresif untuk memotong jalur Bolu"
        )

        # Rule 3A: Jika Kuro ditugaskan mengejar, kirim alarm ke Shiro
        self.add_rule(
            rule_id="R3A",
            name="Sinyal Bahaya dari Kuro ke Shiro",
            fol_str="AssignChaser(Kuro) => BroadcastAlarm(Shiro)",
            clause=frozenset({"~AssignChaser_Kuro", "BroadcastAlarm_Shiro"}),
            description="Kuro mengabari Shiro untuk memperketat pertahanan pulau"
        )

        # Rule 3B: Jika Shiro ditugaskan mengejar, kirim alarm ke Kuro
        self.add_rule(
            rule_id="R3B",
            name="Sinyal Bahaya dari Shiro ke Kuro",
            fol_str="AssignChaser(Shiro) => BroadcastAlarm(Kuro)",
            clause=frozenset({"~AssignChaser_Shiro", "BroadcastAlarm_Kuro"}),
            description="Shiro mengabari Kuro untuk memperketat pertahanan tebing"
        )

        # Rule 4A: Jika Shiro menerima alarm dan Peti B belum dibuka, kunci sektor Peti B
        self.add_rule(
            rule_id="R4A",
            name="Kunci Sektor Peti B oleh Shiro",
            fol_str="BroadcastAlarm(Shiro) ∧ Unopened(B) => AssignTightGuard(Shiro)",
            clause=frozenset({"~BroadcastAlarm_Shiro", "~Unopened_B", "AssignTightGuard_Shiro"}),
            description="Shiro siaga mengunci perimeter dermaga & jembatan"
        )

        # Rule 4B: Jika Kuro menerima alarm dan Peti A belum dibuka, kunci sektor Peti A
        self.add_rule(
            rule_id="R4B",
            name="Kunci Sektor Peti A oleh Kuro",
            fol_str="BroadcastAlarm(Kuro) ∧ Unopened(A) => AssignTightGuard(Kuro)",
            clause=frozenset({"~BroadcastAlarm_Kuro", "~Unopened_A", "AssignTightGuard_Kuro"}),
            description="Kuro siaga mengunci perimeter tebing utara"
        )

        # Rule 5A: Jika ada alarm Shiro dan Peti C belum dibuka, amankan Peti C oleh Oyen
        self.add_rule(
            rule_id="R5A",
            name="Kunci Sektor Peti C oleh Oyen",
            fol_str="BroadcastAlarm(Shiro) ∧ Unopened(C) => AssignTightGuard(Oyen)",
            clause=frozenset({"~BroadcastAlarm_Shiro", "~Unopened_C", "AssignTightGuard_Oyen"}),
            description="Oyen siaga penuh mengamankan peti di markas utama"
        )

        # Rule 5B: Jika ada alarm Kuro dan Peti C belum dibuka, amankan Peti C oleh Oyen
        self.add_rule(
            rule_id="R5B",
            name="Kunci Sektor Peti C oleh Oyen (dari Kuro)",
            fol_str="BroadcastAlarm(Kuro) ∧ Unopened(C) => AssignTightGuard(Oyen)",
            clause=frozenset({"~BroadcastAlarm_Kuro", "~Unopened_C", "AssignTightGuard_Oyen"}),
            description="Oyen siaga penuh mengamankan peti di markas utama"
        )

    def add_rule(self, rule_id: str, name: str, fol_str: str, clause: FrozenSet[str], description: str = "") -> None:
        """Menambahkan aturan formal ke basis pengetahuan."""
        self.clauses.add(clause)
        self.rules_meta.append({
            "id": rule_id,
            "name": name,
            "fol": fol_str,
            "clause": clause,
            "cnf_str": clause_to_str(clause),
            "desc": description,
        })

    def tell(self, fact_or_clause: Union[str, FrozenSet[str]]) -> None:
        """Memasukkan fakta sensorik baru (TELL) ke dalam Knowledge Base.
        
        Bisa menerima literal tunggal (misal 'ChestOpened_A') atau frozenset klausa.
        """
        if isinstance(fact_or_clause, str):
            fact_lit = fact_or_clause.strip()
            self.facts.add(fact_lit)
            clause = frozenset({fact_lit})
        else:
            clause = frozenset(fact_or_clause)
            if len(clause) == 1:
                self.facts.add(next(iter(clause)))

        self.clauses.add(clause)

    def retract(self, fact_or_clause: Union[str, FrozenSet[str]]) -> None:
        """Menghapus fakta/klausa dari Knowledge Base."""
        if isinstance(fact_or_clause, str):
            fact_lit = fact_or_clause.strip()
            if fact_lit in self.facts:
                self.facts.remove(fact_lit)
            clause = frozenset({fact_lit})
        else:
            clause = frozenset(fact_or_clause)

        if clause in self.clauses:
            self.clauses.remove(clause)

    def reset_facts(self) -> None:
        """Mereset semua fakta sensorik dunia ke kondisi awal (belum ada peti terbuka)."""
        # Hapus semua klausa unit fakta
        fact_clauses = {frozenset({f}) for f in self.facts}
        self.clauses -= fact_clauses
        self.facts.clear()

        # Aturan default tetap ada
        self.tell("Unopened_B")
        self.tell("Unopened_C")
        self.tell("HasLootedItem_Player")

    def get_clauses_copy(self) -> Set[FrozenSet[str]]:
        """Mengembalikan salinan himpunan klausa saat ini."""
        return set(self.clauses)

