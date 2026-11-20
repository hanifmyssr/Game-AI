"""Test & Capture: Integrasi Plan Dev (Stealth, Whistle, Rune Keys KB, Abandoned Tower Boss Battle).
"""

import os
import sys

# Ensure root Game-AI directory is in sys.path
sys.path.insert(0, os.path.abspath("."))

# Set dummy video driver for headless execution
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

from game.core import config
from game.app import App
from game.battle.npc_squad import NPCSquad

def run_tests():
    print("=" * 65)
    print("MENGUJI INTEGRASI PLAN DEV (STEALTH, WHISTLE, BOSS PORTAL)")
    print("=" * 65)

    pygame.init()
    app = App()
    app.screen = pygame.display.set_mode((1024, 600))
    app._on_window_resized(1024, 600)

    # 1. Uji Semak & Stealth
    print("\n1. Menguji Sistem Stealth Semak-Semak:")
    # Temukan ubin semak
    bush_cells = list(app.map.bush_set)
    assert len(bush_cells) > 0, "Harus ada ubin semak di map!"
    sample_bush = bush_cells[0]
    app.player.grid = sample_bush
    app.player.update(0.016)
    assert app.player.is_hidden, "Player di semak harus memiliki is_hidden == True!"
    print(f"   [PASS] Pemain berada di semak {sample_bush} -> is_hidden: {app.player.is_hidden}")

    # Uji sensor deteksi NPC terhadap pemain yang bersembunyi
    # Letakkan NPC pada jarak 3 ubin dari pemain
    app.npc.grid = (sample_bush[0] + 3, sample_bush[1])
    assert not app.npc.can_detect_player(app.player), "NPC jarak 3 ubin TIDAK boleh mendeteksi pemain yang sembunyi!"
    print("   [PASS] NPC jarak 3 ubin tidak dapat melihat pemain di semak.")

    # Letakkan NPC pada jarak 1 ubin
    app.npc.grid = (sample_bush[0] + 1, sample_bush[1])
    assert app.npc.can_detect_player(app.player), "NPC jarak 1 ubin HARUS mendeteksi pemain (kontak fisik)!"
    print("   [PASS] NPC jarak 1 ubin berhasil mendeteksi pemain (kontak fisik).")

    # 2. Uji Peluit & Respon Suara (Whistle Mechanic)
    print("\n2. Menguji Mekanisme Peluit [SPASI]:")
    app.player.grid = (20, 20)
    app.player.px, app.player.py = app.map.world_to_px(app.player.grid)
    app.npc.grid = (23, 20)  # Jarak 3 ubin (dalam jangkauan 7 ubin)
    app.npc.investigating = False
    app.whistle_waves.clear()

    app._trigger_whistle()
    assert len(app.whistle_waves) > 0, "Gelombang peluit harus tercipta!"
    assert app.npc.investigating, "NPC dalam jarak 3 ubin harus beralih ke state investigating!"
    assert app.npc.investigate_target == (20, 20), "Target investigasi NPC harus koordinat pemain!"
    assert app.ai_ticker_info is not None, "AI Ticker banner harus aktif mengabarkan persepsi suara!"
    print("   [PASS] Siulan Bolu menghasilkan gelombang visual & memicu investigasi NPC.")

    # 3. Uji Kunci Rune & Pembuktian Logika KB
    print("\n3. Menguji Sistem Kunci Rune & Aturan KB Portal Kuno:")
    app.player.rune_keys.clear()
    portal_pos = getattr(app.map, "boss_portal", {"x": 38, "y": 5})
    app.player.grid = (portal_pos["x"], portal_pos["y"])

    # Sebelum 3 kunci
    app._interact_tower_portal()
    assert not app.is_boss_battle, "Portal tidak boleh terbuka sebelum 3 kunci terkumpul!"
    print("   [PASS] Percobaan masuk gerbang sebelum 3 kunci -> Ditolak (Gerbang Tersegel).")

    # Buka 3 Peti Harta (A, B, C)
    for i, ch in enumerate(app.chests[:3]):
        app.gacha_active = False
        app.gacha_showcase = None
        app._open_chest(ch)
    assert len(app.player.rune_keys) >= 3, f"Pemain harus mengantongi 3 kunci rune! Real: {app.player.rune_keys}"
    print(f"   [PASS] 3 Kunci Rune berhasil diperoleh: {app.player.rune_keys}")

    # Uji Pembuktian Resolusi Refutasi PortalActive
    proved, steps, summary = app.inter_npc_manager.can_open_portal()
    assert proved, "Klausa PortalActive HARUS terbukti benar (empty clause contradiction)!"
    print("   [PASS] Pembuktian Logika KB Resolution Refutation: PortalActive [] TERBUKTI!")

    # 4. Uji Interaksi Portal Menara Kuno -> Boss Pre-Battle -> Boss Battle
    print("\n4. Menguji Masuk Menara Kuno & Pertarungan Boss Kage:")
    app._interact_tower_portal()
    assert app.game_mode == "PRE_BATTLE", "Game harus masuk ke fase PRE_BATTLE Boss dulu!"
    assert app.is_boss_battle, "Status is_boss_battle harus True!"
    app._draw()
    app.enter_boss_battle()
    assert app.game_mode == "BATTLE", "Game harus bertransisi ke mode BATTLE saat duel dimulai!"
    active_boss = app.current_squad.get_active_member()
    assert active_boss.name == "Kage the Shadow Lord", f"Boss aktif harus Kage! Real: {active_boss.name}"
    assert active_boss.max_hp >= 160, f"HP Boss Kage harus >= 160, real: {active_boss.max_hp}"
    assert active_boss.battle_sprite is not None, "Sprite battle Kage harus berhasil dimuat!"
    print(f"   [PASS] Berhasil masuk Boss Pre-Battle lalu Battle melawan {active_boss.name} (HP: {active_boss.max_hp})!")

    # Uji render satu frame battle untuk memastikan grafis tanpa crash
    app._draw()
    print("   [PASS] Rendering frame arena Boss Battle berhasil tanpa kendala!")

    print("\n" + "=" * 65)
    print("SEMUA PENGUJIAN INTEGRASI PLAN DEV SUKSES 100%!")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
