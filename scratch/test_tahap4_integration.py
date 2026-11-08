"""Pengujian Integrasi Komprehensif: Materi 07 Logic & 08 Classical Planning (Tubes Tahap 4).

Menguji siklus penuh:
1. Eksplorasi (Kondisi Damai)
2. Bolu membuka Peti A -> Trigger Sensor TELL ke KB
3. Inferensi ASK Refutasi [] membuktikan penugasan Kuro (Chaser) & Shiro (Guard)
4. Mesin Planning STRIPS (Forward A* & Backward Regression) menyusun sekuens aksi patroli
5. Visualizer Pohon Resolusi & Pohon Planning di Graph Modal [T]
6. Overlay Akademis Logic [K] dan Planning [P]
7. Transisi mulus ke Pre-Battle & Battle tanpa merusak modul sebelumnya.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from game.app import App


def test_tahap4_full_integration():
    print("==================================================================")
    print("MENGUJI INTEGRASI LENGKAP MATERI 07 & 08 (TUBES TAHAP 4)")
    print("==================================================================")

    # 1. Inisialisasi Game App
    app = App()
    print("1. Inisialisasi App berhasil.")
    assert hasattr(app, "inter_npc_manager"), "App harus memiliki inter_npc_manager!"
    assert hasattr(app, "forward_planner"), "App harus memiliki forward_planner!"
    assert hasattr(app, "backward_planner"), "App harus memiliki backward_planner!"
    assert hasattr(app, "logic_overlay"), "App harus memiliki logic_overlay!"
    assert hasattr(app, "planning_overlay"), "App harus memiliki planning_overlay!"

    # 2. Verifikasi Kondisi Awal (Damai)
    roles = app.inter_npc_manager.query_active_roles()
    print(f"2. Status awal sensorik: {roles['percept']}")
    assert roles["chaser"] is None, "Awalnya belum ada pemburu yang ditugaskan."

    # 3. Interaksi Buka Peti A
    chest_a = app.chests[0]
    app._open_chest(chest_a)
    print(f"3. Bolu membuka Peti A -> Item: {chest_a.get('item', 'health_potion')}")

    # Verifikasi Inferensi Logika (Materi 07)
    roles_after = app.inter_npc_manager.query_active_roles()
    print(f"   - Percept: {roles_after['percept']}")
    print(f"   - ASK Chaser: {roles_after['chaser']} (Kuro terpilih)")
    print(f"   - ASK Guardians: {roles_after['guardians']} (Shiro & Oyen siaga)")
    assert roles_after["chaser"] == "Kuro", "Kuro harus menjadi Chaser via inferensi resolusi refutasi!"
    assert "Shiro" in roles_after["guardians"], "Shiro harus menjadi Tight Guardian!"

    # 4. Verifikasi Automated Planning (Materi 08)
    plan_res = app.latest_plan_result
    print(f"4. Automated Planning tersusun: {plan_res.engine_name}")
    print(f"   - Total Aksi: {len(plan_res.plan)}")
    print(f"   - Waktu Komputasi: {plan_res.time_ms:.2f} ms")
    for idx, act in enumerate(plan_res.plan, start=1):
        print(f"     Aksi {idx}: {repr(act)}")
    assert plan_res.success, "Perencanaan STRIPS harus sukses!"
    assert len(plan_res.plan) >= 3, "Rencana patroli harus berisi aksi yang bermakna!"

    # 5. Uji Backward Regression Planner
    from game.planning.domain_world_patrol import create_world_patrol_problem
    s0, goal, actions = create_world_patrol_problem("A")
    plan_bwd = app.backward_planner.plan(s0, goal, actions)
    print(f"5. Pengujian Backward Regression: {plan_bwd.engine_name}")
    assert plan_bwd.success, "Backward Regression harus sukses menghasilkan rencana!"
    assert len(plan_bwd.plan) == len(plan_res.plan), "Panjang rencana Forward dan Backward harus konsisten!"

    # 6. Uji Modal Pohon Universal [T] untuk LOGIC
    app.open_graph_modal("LOGIC")
    assert app.overlay.graph_modal.visible, "Modal visualizer pohon harus terbuka untuk LOGIC!"
    print(f"6. Graph Modal LOGIC berhasil dibuka (Title: {app.overlay.graph_modal.modal_title})")
    app.open_graph_modal("LOGIC")  # Toggle close

    # 7. Uji Modal Pohon Universal [T] untuk PLANNING
    app.open_graph_modal("PLANNING")
    assert app.overlay.graph_modal.visible, "Modal visualizer pohon harus terbuka untuk PLANNING!"
    print(f"7. Graph Modal PLANNING berhasil dibuka (Title: {app.overlay.graph_modal.modal_title})")
    app.open_graph_modal("PLANNING")  # Toggle close

    # 8. Uji Shortcut Overlay [K] dan [P]
    app._handle_key(pygame.K_k)
    assert app.logic_overlay.visible, "Tombol [K] harus membuka LogicOverlay!"
    app._handle_key(pygame.K_k)
    assert not app.logic_overlay.visible, "Tombol [K] kedua harus menutup LogicOverlay!"

    app._handle_key(pygame.K_p)
    assert app.planning_overlay.visible, "Tombol [P] harus membuka PlanningOverlay!"
    app._handle_key(pygame.K_p)
    assert not app.planning_overlay.visible, "Tombol [P] kedua harus menutup PlanningOverlay!"
    print("8. Shortcut keyboard [K] (Logic) dan [P] (Planning) berfungsi sempurna.")

    # 9. Uji Siklus Transisi Battle & Reset
    app.enter_pre_battle()
    assert app.game_mode == "PRE_BATTLE"
    app.enter_battle()
    assert app.game_mode == "BATTLE"
    app.exit_battle()
    assert app.game_mode == "EXPLORATION"
    print("9. Transisi Pre-Battle dan Battle tetap stabil tanpa regresi.")

    # 10. Uji Reset Game State
    app.reset_game_state()
    roles_reset = app.inter_npc_manager.query_active_roles()
    assert roles_reset["chaser"] is None, "Setelah reset, status chaser harus bersih kembali."
    print("10. Reset game state berhasil membersihkan memori logika & planning.")

    print("\n==================================================================")
    print("HASIL INTEGRASI TUBES TAHAP 4: LULUS 100% SEMPURNA & BEBAS BUG!")
    print("==================================================================")


if __name__ == "__main__":
    test_tahap4_full_integration()

