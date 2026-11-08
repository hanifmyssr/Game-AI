"""Pengujian End-to-End: Materi 08 Automated Planning pada Pertarungan (Tag-Team Tactical Rotation & Bench Heal)."""

import os
import sys
import pygame

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()

from game.app import App
from game.battle.battle_system import ACTION_ATTACK, ACTION_HEAVY


def test_battle_planning_rotation():
    print("==================================================================")
    print("MENGUJI MATERI 08 AUTOMATED PLANNING DI ARENA BATTLE")
    print("==================================================================")

    app = App()
    print("1. Inisialisasi App berhasil.")

    # 1. Masuk ke Pre-Battle & Bangun Skuad
    app.enter_pre_battle()
    assert app.current_squad is not None, "Squad harus terbentuk di Pre-Battle!"
    assert len(app.current_squad.members) >= 2, "Squad harus memiliki minimal 2 petarung!"
    print(f"2. Skuad terbentuk: {[m.name for m in app.current_squad.members]}")

    # 2. Masuk ke Arena Battle
    app.enter_battle()
    bs = app.battle_system
    assert app.game_mode == "BATTLE", "Mode harus BATTLE!"
    assert not bs.tactical_plan_executed, "Taktik belum boleh dieksekusi di awal duel!"

    active_init = bs.squad.get_active_member()
    print(f"3. Petarung awal di garis depan: {active_init.name} (HP: {bs.state.npc_hp}/{bs.state.npc_max_hp})")

    # 3. Bolu menyerang NPC hingga HP sekarat (<= 35%)
    # Kita set HP NPC secara terukur agar memasuki rentang sekarat
    print("4. Player menyerang petarung garis depan hingga sekarat...")
    bs.state.npc_hp = 25  # Simulasi HP mencapai 25% (di bawah batas 35%)
    bs.state.is_npc_turn = True

    # 4. Giliran NPC dieksekusi -> Mesin Automated Planning PDDL harus aktif!
    action_taken = bs.execute_npc_turn()
    print(f"5. Aksi yang diputuskan oleh AI Skuad: {action_taken}")
    assert action_taken == "TACTICAL_ROTATION", "NPC harus mengeksekusi TACTICAL_ROTATION!"
    assert bs.tactical_plan_executed, "tactical_plan_executed HARUS True!"
    assert bs.last_tactical_plan is not None, "last_tactical_plan HARUS tersimpan!"
    assert bs.last_tactical_plan.success, "Perencanaan PDDL HARUS sukses menemukan rencana!"

    plan_names = [a.name for a in bs.last_tactical_plan.plan]
    print(f"6. Rencana PDDL STRIPS yang dihasilkan: {plan_names}")
    assert plan_names == ["SwapRetreat", "CastDefend", "HealTeammate"], "Urutan 3 aksi PDDL harus sesuai!"

    # 5. Verifikasi Efek Aksi pada Game State
    active_now = bs.squad.get_active_member()
    print(f"7. Petarung garis depan baru: {active_now.name} (Status Defending: {bs.state.npc_defending})")
    assert active_now.name != active_init.name, "Petarung aktif harus berganti ke Defender!"
    assert bs.state.npc_defending, "Defender baru harus berada dalam status DEFENDING!"

    # Cek petarung lama yang mundur ke bangku cadangan: HP harus bertambah pulih
    assert active_init.current_hp > 25, f"Petarung lama harus dipulihkan (HP sekarang: {active_init.current_hp})!"
    print(f"8. Petarung lama ({active_init.name}) di bangku cadangan berhasil dipulihkan: {active_init.current_hp} HP!")

    # 6. Verifikasi Notifikasi Banner Visual & Sinkronisasi Visualizer
    assert bs.tactical_banner_timer > 0, "Banner notifikasi taktis harus aktif!"
    assert bs.tactical_banner_info is not None, "Informasi banner harus terisi!"
    assert app.latest_plan_result is not None, "app.latest_plan_result harus sinkron dengan PDDL duel!"
    print("9. Sinkronisasi HUD Banner dan Visualizer PDDL: BERHASIL!")

    # 7. Render screenshot headless untuk verifikasi visual
    surf = pygame.Surface((1024, 668))
    app._draw_battle_arena()
    artifact_path = r"C:\Users\Pavilion\.gemini\antigravity\brain\38f4bb8b-a421-4acf-b988-2e6d2a7fae0d\battle_pddl_tactical_rotation.png"
    pygame.image.save(app.screen, artifact_path)
    print(f"10. Screenshot visual tersimpan di: {artifact_path}")

    # 8. Buka Graph Modal PLANNING dan render
    app.open_graph_modal("PLANNING")
    assert app.overlay.graph_modal.visible, "Graph modal PLANNING harus terbuka!"
    app.overlay.graph_modal.draw(app.screen)
    artifact_modal_path = r"C:\Users\Pavilion\.gemini\antigravity\brain\38f4bb8b-a421-4acf-b988-2e6d2a7fae0d\battle_pddl_graph_modal.png"
    pygame.image.save(app.screen, artifact_modal_path)
    print(f"11. Screenshot Graph Modal PDDL tersimpan di: {artifact_modal_path}")

    print("\n==================================================================")
    print("HASIL PENGUJIAN MATERI 08 BATTLE TACTICS: 100% SUKSES SEMPURNA!")
    print("==================================================================")


if __name__ == "__main__":
    test_battle_planning_rotation()

