"""Manajer Koordinasi Sensor & Komunikasi Antar-NPC (Percept -> TELL -> ASK).

Menghubungkan kejadian di dunia permainan (Bolu membuka peti) dengan
penalaran logika KnowledgeBase dan penugasan peran adaptif ke NPC.
"""

from typing import Dict, Any, List, Optional, Tuple
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
        self.kb.tell(f"HasKey_{chest_tag}")

        # Tandai peti-peti lainnya yang masih unopened
        for t in chest_tags:
            if t != chest_tag:
                self.kb.tell(f"Unopened_{t}")
            else:
                self.kb.retract(f"Unopened_{t}")

        # 2. ASK: Tentukan siapa pemburu aktif
        # Peti A di sektor utara -> Shiro adalah penjaga lokal
        # Peti B di sektor kiri bawah -> Oyen adalah penjaga lokal
        # Peti C di sektor timur/kanan -> Kuro adalah penjaga lokal
        if chest_tag == "A":
            preferred_chaser = "Shiro"
        elif chest_tag == "B":
            preferred_chaser = "Oyen"
        else:
            preferred_chaser = "Kuro"

        query_chaser = f"AssignChaser_{preferred_chaser}"
        success_chaser, steps_chaser, summary_chaser = self.engine.prove(self.kb, query_chaser)

        if success_chaser:
            self.chaser_assigned = preferred_chaser
            self.latest_steps = steps_chaser
            self.latest_proof_summary = summary_chaser
        else:
            self.chaser_assigned = preferred_chaser

        # 3. ASK: Buktikan penugasan sekutu menjaga sisa peti
        self.guardians_assigned = []
        for candidate in ("Shiro", "Oyen", "Kuro"):
            if candidate != self.chaser_assigned:
                success_guard, _, _ = self.engine.prove(self.kb, f"AssignTightGuard_{candidate}")
                if success_guard:
                    self.guardians_assigned.append(candidate)

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
        specs = [
            ("Shiro", getattr(self.app, "npc_shiro", None), "Peti A dijarah! Berhenti!"),
            ("Oyen", getattr(self.app, "npc", None), "Peti B dicuri! Serang!"),
            ("Kuro", getattr(self.app, "npc_kuro", None), "Peti C dibobol! Kejar!"),
        ]
        for npc_name, npc_obj, alert_msg in specs:
            if not npc_obj:
                continue
            if self.chaser_assigned == npc_name:
                npc_obj.chasing = True
                npc_obj.forced_chase_timer = 2.5
                npc_obj.investigating = False
                npc_obj.investigate_target = None
                npc_obj.is_returning_to_patrol = False
                npc_obj.speech_bubble = alert_msg
                npc_obj.speech_timer = 2.5
                if hasattr(self.app, "player"):
                    npc_obj.find_path(self.app.player.grid)
            else:
                npc_obj.chasing = False
                npc_obj.forced_chase_timer = 0.0

    def can_open_portal(self) -> Tuple[bool, List[ResolutionStep], Optional[Dict[str, Any]]]:
        """Mengevaluasi pembuktian resolusi refutasi klausa PortalActive (Materi 07: Logic KB)."""
        return self.engine.prove(self.kb, "PortalActive")

    def query_active_roles(self) -> Dict[str, Any]:
        """Mengambil status peran aktif saat ini dari KB."""
        return {
            "chaser": self.chaser_assigned,
            "guardians": list(self.guardians_assigned),
            "percept": self.latest_percept_event,
            "facts": list(self.kb.facts),
            "proof_summary": self.latest_proof_summary,
        }

