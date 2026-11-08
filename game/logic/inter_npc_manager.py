"""Manajer Koordinasi Sensor & Komunikasi Antar-NPC (Percept -> TELL -> ASK).

Menghubungkan kejadian di dunia permainan (Bolu membuka peti) dengan
penalaran logika KnowledgeBase dan penugasan peran adaptif ke NPC.
"""

from typing import Dict, Any, List, Optional
from .kb_rules import KnowledgeBase
from .inference_engine import ResolutionRefutationEngine, ResolutionStep


class InterNPCManager:
    """Koordinator penalaran logika antar-NPC."""

    def __init__(self, app_ref: Any = None):
        self.app = app_ref
        self.kb = KnowledgeBase()
        self.engine = ResolutionRefutationEngine()

        # Status aktif peran NPC hasil inferensi ASK
        self.chaser_assigned: Optional[str] = None
        self.guardians_assigned: List[str] = []
        self.latest_percept_event: str = "Semua 3 Peti Harta masih aman tersegel."
        self.latest_proof_summary: Optional[Dict[str, Any]] = None
        self.latest_steps: List[ResolutionStep] = []

        # Inisialisasi fakta dasar
        self.reset()

    def reset(self) -> None:
        """Mereset kondisi ke awal permainan."""
        self.kb.reset_facts()
        self.chaser_assigned = None
        self.guardians_assigned = []
        self.latest_percept_event = "Semua 3 Peti Harta masih aman tersegel."
        self.latest_proof_summary = None
        self.latest_steps = []

        # Jalankan ASK awal untuk verifikasi kondisi damai
        self.query_active_roles()

    def on_chest_opened(self, chest_index: int, item_name: str = "health_potion") -> Dict[str, Any]:
        """Dipanggil saat pemain (Bolu) membuka peti di peta.
        
        Melakukan:
        1. Sensor deteksi -> TELL(ChestOpened_{tag})
        2. Sensor jarahan -> TELL(HasLootedItem_Player)
        3. Inferensi refutasi -> ASK(AssignChaser_{NPC})
        4. Inferensi sinyal -> ASK(AssignTightGuard_{NPC})
        """
        chest_tags = ["A", "B", "C", "D"]
        chest_tag = chest_tags[chest_index] if 0 <= chest_index < len(chest_tags) else "A"
        self.latest_percept_event = f"Bolu membuka Peti {chest_tag} dan mengambil {item_name}!"

        # 1. TELL fakta baru ke KB
        self.kb.tell(f"ChestOpened_{chest_tag}")
        self.kb.tell("HasLootedItem_Player")

        # Tandai peti-peti lainnya yang masih unopened
        for t in chest_tags:
            if t != chest_tag:
                self.kb.tell(f"Unopened_{t}")
            else:
                self.kb.retract(f"Unopened_{t}")

        # 2. ASK: Tentukan siapa pemburu aktif
        # Peti A/B di sektor utara/barat -> Kuro adalah pemburu tercepat
        # Peti C/D di sektor selatan/timur -> Shiro adalah pemburu tercepat
        preferred_chaser = "Kuro" if chest_tag in ("A", "B") else "Shiro"
        query_chaser = f"AssignChaser_{preferred_chaser}"
        success_chaser, steps_chaser, summary_chaser = self.engine.prove(self.kb, query_chaser)

        if success_chaser:
            self.chaser_assigned = preferred_chaser
            self.latest_steps = steps_chaser
            self.latest_proof_summary = summary_chaser
        else:
            # Fallback jika query kedua berhasil
            alt_chaser = "Shiro" if preferred_chaser == "Kuro" else "Kuro"
            success_alt, steps_alt, summary_alt = self.engine.prove(self.kb, f"AssignChaser_{alt_chaser}")
            if success_alt:
                self.chaser_assigned = alt_chaser
                self.latest_steps = steps_alt
                self.latest_proof_summary = summary_alt
            else:
                self.chaser_assigned = "Kuro"

        # 3. ASK: Buktikan penugasan sekutu menjaga sisa peti
        other_guard = "Shiro" if self.chaser_assigned == "Kuro" else "Kuro"
        success_guard, _, _ = self.engine.prove(self.kb, f"AssignTightGuard_{other_guard}")
        if success_guard and other_guard not in self.guardians_assigned:
            self.guardians_assigned.append(other_guard)

        # 4. ASK: Buktikan penugasan Oyen mengamankan markas
        success_oyen, _, _ = self.engine.prove(self.kb, "AssignTightGuard_Oyen")
        if success_oyen and "Oyen" not in self.guardians_assigned:
            self.guardians_assigned.append("Oyen")

        # 5. Sinkronkan perilaku NPC di dunia game jika referensi app ada
        if self.app:
            self._apply_npc_behaviors()

        return {
            "percept": self.latest_percept_event,
            "chaser": self.chaser_assigned,
            "guardians": self.guardians_assigned,
            "proved": success_chaser,
            "steps_count": len(self.latest_steps),
        }

    def _apply_npc_behaviors(self) -> None:
        """Menerapkan hasil inferensi logika ke objek NPC nyata di game/app.py."""
        # 1. Jika Kuro ditugaskan mengejar: aktifkan pengejaran & arahkan rute ke Bolu
        if hasattr(self.app, "npc_kuro"):
            if self.chaser_assigned == "Kuro":
                self.app.npc_kuro.chasing = True
                if hasattr(self.app, "player"):
                    self.app.npc_kuro.find_path(self.app.player.grid)
            else:
                self.app.npc_kuro.chasing = False

        # 2. Jika Shiro ditugaskan mengejar: aktifkan pengejaran & arahkan rute ke Bolu
        if hasattr(self.app, "npc_shiro"):
            if self.chaser_assigned == "Shiro":
                self.app.npc_shiro.chasing = True
                if hasattr(self.app, "player"):
                    self.app.npc_shiro.find_path(self.app.player.grid)
            else:
                self.app.npc_shiro.chasing = False

        # 3. Pengejar utama (Oyen) juga ikut memburu untuk mempersempit pergerakan
        if hasattr(self.app, "npc") and not self.app.npc.chasing:
            self.app.npc.chasing = True
            if hasattr(self.app, "player"):
                self.app.npc.find_path(self.app.player.grid)

    def query_active_roles(self) -> Dict[str, Any]:
        """Mengambil status peran aktif saat ini dari KB."""
        return {
            "chaser": self.chaser_assigned,
            "guardians": list(self.guardians_assigned),
            "percept": self.latest_percept_event,
            "facts": list(self.kb.facts),
            "proof_summary": self.latest_proof_summary,
        }

