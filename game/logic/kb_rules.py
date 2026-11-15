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
        """Memuat aturan-aturan CNF koordinasi 3 NPC menjaga 3 peti di seluruh peta."""
        # Rule 1A: Jika Peti A dibuka, maka Shiro bersiaga (sektor utara / tebing kiri atas)
        self.add_rule(
            rule_id="R1A",
            name="Deteksi Peti A Terbuka",
            fol_str="ChestOpened(A) => Alert(Shiro)",
            clause=frozenset({"~ChestOpened_A", "Alert_Shiro"}),
            description="Shiro bersiaga jika Peti A (sektor utara) dijarah"
        )

        # Rule 1B: Jika Peti B dibuka, maka Oyen bersiaga (sektor padang kiri bawah)
        self.add_rule(
            rule_id="R1B",
            name="Deteksi Peti B Terbuka",
            fol_str="ChestOpened(B) => Alert(Oyen)",
            clause=frozenset({"~ChestOpened_B", "Alert_Oyen"}),
            description="Oyen bersiaga jika Peti B (sektor kiri bawah) dijarah"
        )

        # Rule 1C: Jika Peti C dibuka, maka Kuro bersiaga (sektor jembatan timur / kanan)
        self.add_rule(
            rule_id="R1C",
            name="Deteksi Peti C Terbuka",
            fol_str="ChestOpened(C) => Alert(Kuro)",
            clause=frozenset({"~ChestOpened_C", "Alert_Kuro"}),
            description="Kuro bersiaga jika Peti C (sektor timur/kanan) dijarah"
        )

        # Rule 2A: Jika Shiro siaga dan Player mengambil jarahan, tugaskan Shiro mengejar Player
        self.add_rule(
            rule_id="R2A",
            name="Penugasan Pemburu Shiro",
            fol_str="Alert(Shiro) ∧ HasLootedItem(Player) => AssignChaser(Shiro)",
            clause=frozenset({"~Alert_Shiro", "~HasLootedItem_Player", "AssignChaser_Shiro"}),
            description="Shiro beralih menjadi pemburu aktif menjaga sektor utara"
        )

        # Rule 2B: Jika Oyen siaga dan Player mengambil jarahan, tugaskan Oyen mengejar Player
        self.add_rule(
            rule_id="R2B",
            name="Penugasan Pemburu Oyen",
            fol_str="Alert(Oyen) ∧ HasLootedItem(Player) => AssignChaser(Oyen)",
            clause=frozenset({"~Alert_Oyen", "~HasLootedItem_Player", "AssignChaser_Oyen"}),
            description="Oyen beralih menjadi pemburu aktif menjaga sektor kiri bawah"
        )

        # Rule 2C: Jika Kuro siaga dan Player mengambil jarahan, tugaskan Kuro mengejar Player
        self.add_rule(
            rule_id="R2C",
            name="Penugasan Pemburu Kuro",
            fol_str="Alert(Kuro) ∧ HasLootedItem(Player) => AssignChaser(Kuro)",
            clause=frozenset({"~Alert_Kuro", "~HasLootedItem_Player", "AssignChaser_Kuro"}),
            description="Kuro beralih menjadi pemburu aktif menjaga sektor timur/kanan"
        )

        # Rule 3A: Jika Shiro mengejar, kirim alarm ke Kuro & Oyen
        self.add_rule(
            rule_id="R3A1",
            name="Alarm dari Shiro ke Kuro",
            fol_str="AssignChaser(Shiro) => BroadcastAlarm(Kuro)",
            clause=frozenset({"~AssignChaser_Shiro", "BroadcastAlarm_Kuro"}),
            description="Shiro mengabari Kuro untuk memperketat pertahanan timur"
        )
        self.add_rule(
            rule_id="R3A2",
            name="Alarm dari Shiro ke Oyen",
            fol_str="AssignChaser(Shiro) => BroadcastAlarm(Oyen)",
            clause=frozenset({"~AssignChaser_Shiro", "BroadcastAlarm_Oyen"}),
            description="Shiro mengabari Oyen untuk memperketat pertahanan selatan"
        )

        # Rule 3B: Jika Oyen mengejar, kirim alarm ke Shiro & Kuro
        self.add_rule(
            rule_id="R3B1",
            name="Alarm dari Oyen ke Shiro",
            fol_str="AssignChaser(Oyen) => BroadcastAlarm(Shiro)",
            clause=frozenset({"~AssignChaser_Oyen", "BroadcastAlarm_Shiro"}),
            description="Oyen mengabari Shiro untuk memperketat pertahanan utara"
        )
        self.add_rule(
            rule_id="R3B2",
            name="Alarm dari Oyen ke Kuro",
            fol_str="AssignChaser(Oyen) => BroadcastAlarm(Kuro)",
            clause=frozenset({"~AssignChaser_Oyen", "BroadcastAlarm_Kuro"}),
            description="Oyen mengabari Kuro untuk memperketat pertahanan timur"
        )

        # Rule 3C: Jika Kuro mengejar, kirim alarm ke Shiro & Oyen
        self.add_rule(
            rule_id="R3C1",
            name="Alarm dari Kuro ke Shiro",
            fol_str="AssignChaser(Kuro) => BroadcastAlarm(Shiro)",
            clause=frozenset({"~AssignChaser_Kuro", "BroadcastAlarm_Shiro"}),
            description="Kuro mengabari Shiro untuk memperketat pertahanan utara"
        )
        self.add_rule(
            rule_id="R3C2",
            name="Alarm dari Kuro ke Oyen",
            fol_str="AssignChaser(Kuro) => BroadcastAlarm(Oyen)",
            clause=frozenset({"~AssignChaser_Kuro", "BroadcastAlarm_Oyen"}),
            description="Kuro mengabari Oyen untuk memperketat pertahanan selatan"
        )

        # Rule 4: Kunci sektor peti yang belum dibuka
        self.add_rule(
            rule_id="R4A",
            name="Kunci Sektor Peti A oleh Shiro",
            fol_str="BroadcastAlarm(Shiro) ∧ Unopened(A) => AssignTightGuard(Shiro)",
            clause=frozenset({"~BroadcastAlarm_Shiro", "~Unopened_A", "AssignTightGuard_Shiro"}),
            description="Shiro siaga mengunci perimeter Peti A utara"
        )
        self.add_rule(
            rule_id="R4B",
            name="Kunci Sektor Peti B oleh Oyen",
            fol_str="BroadcastAlarm(Oyen) ∧ Unopened(B) => AssignTightGuard(Oyen)",
            clause=frozenset({"~BroadcastAlarm_Oyen", "~Unopened_B", "AssignTightGuard_Oyen"}),
            description="Oyen siaga mengunci perimeter Peti B kiri bawah"
        )
        self.add_rule(
            rule_id="R4C",
            name="Kunci Sektor Peti C oleh Kuro",
            fol_str="BroadcastAlarm(Kuro) ∧ Unopened(C) => AssignTightGuard(Kuro)",
            clause=frozenset({"~BroadcastAlarm_Kuro", "~Unopened_C", "AssignTightGuard_Kuro"}),
            description="Kuro siaga mengunci perimeter Peti C timur/kanan"
        )

        # Rule 6: Portal Kuno Menara Ditinggalkan Membutuhkan 3 Kunci Rune (plan_dev.md)
        # FOL: HasKey(A) ∧ HasKey(B) ∧ HasKey(C) => PortalActive
        # CNF: ~HasKey_A ∨ ~HasKey_B ∨ ~HasKey_C ∨ PortalActive
        self.add_rule(
            rule_id="R6_PORTAL",
            name="Aktivasi Portal Menara Kuno",
            fol_str="HasKey(A) ∧ HasKey(B) ∧ HasKey(C) => PortalActive",
            clause=frozenset({"~HasKey_A", "~HasKey_B", "~HasKey_C", "PortalActive"}),
            description="Portal Menara Kuno (Abandoned Tower) terbuka jika Bolu telah mengumpulkan 3 Kunci Rune dari peti"
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

