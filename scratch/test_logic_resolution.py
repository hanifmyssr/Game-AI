"""Unit Test Mandiri: Modul 07 Logic & Knowledge Representation."""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.logic.kb_rules import KnowledgeBase
from game.logic.inference_engine import ResolutionRefutationEngine
from game.logic.inter_npc_manager import InterNPCManager


def test_kb_and_resolution():
    print("=== MENGUJI KNOWLEDGE BASE & RESOLUSI REFUTASI (MODUL 07) ===")
    
    # 1. Inisialisasi KB
    kb = KnowledgeBase()
    engine = ResolutionRefutationEngine()
    
    print(f"Total aturan awal KB: {len(kb.rules_meta)}")
    for r in kb.rules_meta:
        print(f"  [{r['id']}] {r['name']}: {r['cnf_str']}")

    # 2. Kondisi Damai (Belum ada Peti Terbuka)
    # Query: Apakah Kuro ditugaskan mengejar? Harusnya False (tidak terbukti)
    proved, steps, summary = engine.prove(kb, "AssignChaser_Kuro")
    print(f"\nUji Kondisi Damai -> Proved: {proved} (Langkah: {len(steps)})")
    assert not proved, "Kuro seharusnya belum mengejar sebelum ada peti dibuka!"

    # 3. Simulasi Bolu Membuka Peti A (TELL)
    print("\n--- Simulasi: Bolu Membuka Peti A ---")
    kb.tell("ChestOpened_A")
    kb.tell("HasLootedItem_Player")
    print("Fakta TELL ditambahkan: ChestOpened_A, HasLootedItem_Player")

    # 4. Inferensi ASK: AssignChaser_Kuro
    proved_chaser, steps_chaser, summary_chaser = engine.prove(kb, "AssignChaser_Kuro")
    print(f"Hasil Pembuktian AssignChaser(Kuro): {proved_chaser}")
    print(f"Jumlah langkah resolusi: {len(steps_chaser)}")
    for st in summary_chaser["proof_trace"]:
        print(f"  {st}")
    assert proved_chaser, "Kuro WAJIB terbukti menjadi pemburu via refutasi []!"

    # 5. Inferensi ASK Sinyal Sekutu: BroadcastAlarm_Shiro & AssignTightGuard_Shiro
    kb.tell("AssignChaser_Kuro")
    kb.tell("Unopened_B")
    proved_guard, steps_guard, _ = engine.prove(kb, "AssignTightGuard_Shiro")
    print(f"\nHasil Pembuktian AssignTightGuard(Shiro): {proved_guard}")
    assert proved_guard, "Shiro WAJIB terbukti menjadi Tight Guard via refutasi []!"

    # 6. Uji InterNPCManager
    print("\n--- Uji InterNPCManager End-to-End ---")
    mgr = InterNPCManager()
    res = mgr.on_chest_opened(0, "Pedang Ksatria")
    print(f"Percept: {res['percept']}")
    print(f"Chaser: {res['chaser']}")
    print(f"Guardians: {res['guardians']}")
    print(f"Proved: {res['proved']}")
    assert res["chaser"] == "Kuro"
    assert "Shiro" in res["guardians"]

    print("\n==================================================")
    print("SEMUA PENGUJIAN LOGIC & RESOLUTION 100% LULUS!")
    print("==================================================")


if __name__ == "__main__":
    test_kb_and_resolution()

