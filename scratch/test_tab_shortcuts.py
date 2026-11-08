import os
import sys
import pygame

# Set dummy video driver for headless testing
os.environ["SDL_VIDEODRIVER"] = "dummy"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from game.app import App, K_TAB

def test_tab_shortcuts():
    print("=== TESTING TAB & ALT+TAB SHORTCUTS ===")
    app = App()
    
    # Inisialisasi awal
    assert hasattr(app, "overlay"), "App harus memiliki overlay"
    assert hasattr(app.overlay, "dock"), "Overlay harus memiliki dock"
    
    print(f"Status awal dock is_open: {app.overlay.dock.is_open}")
    print(f"Tab awal: {app.overlay.nav_rail.active_tab} ({app.overlay.dock.tabs[app.overlay.nav_rail.active_tab].__class__.__name__})")
    
    # -------------------------------------------------------------
    # 1. Test Tab biasa (Toggle Open / Close Dock) di mode EXPLORATION
    # -------------------------------------------------------------
    app.overlay.dock.open()
    assert app.overlay.dock.is_open == True
    
    # Simulasikan tekan TAB (tanpa Alt)
    ev_tab = pygame.event.Event(pygame.KEYDOWN, key=K_TAB, mod=0)
    pygame.event.post(ev_tab)
    app._handle_events()
    assert app.overlay.dock.is_open == False, "Menekan TAB saat panel buka harus menutup panel"
    print("1. [PASS] Tekan TAB saat terbuka -> Panel berhasil ditutup (collapsed)!")

    # Tekan TAB lagi saat tertutup
    ev_tab2 = pygame.event.Event(pygame.KEYDOWN, key=K_TAB, mod=0)
    pygame.event.post(ev_tab2)
    app._handle_events()
    assert app.overlay.dock.is_open == True, "Menekan TAB saat panel tutup harus membuka panel"
    print("2. [PASS] Tekan TAB saat tertutup -> Panel berhasil dibuka kembali (expanded)!")

    # -------------------------------------------------------------
    # 2. Test Alt+Tab untuk ganti-ganti Tab/Panel
    # -------------------------------------------------------------
    app.overlay.nav_rail.set_active_tab(0)
    assert app.overlay.nav_rail.active_tab == 0
    
    # Tekan ALT + TAB (mod = KMOD_ALT)
    alt_mod = getattr(pygame, "KMOD_ALT", 0x0300)
    
    expected_sequence = [1, 2, 3, 4, 5, 6, 0]
    for expected_tab in expected_sequence:
        ev_alt_tab = pygame.event.Event(pygame.KEYDOWN, key=K_TAB, mod=alt_mod)
        pygame.event.post(ev_alt_tab)
        app._handle_events()
        
        cur_tab = app.overlay.nav_rail.active_tab
        dock_tab = app.overlay.dock.active_tab_id
        assert cur_tab == expected_tab, f"Expected tab {expected_tab}, got {cur_tab}"
        assert dock_tab == expected_tab, f"Dock tab harus sinkron {expected_tab}, got {dock_tab}"
        assert app.overlay.dock.is_open == True, "Alt+Tab harus memastikan dock panel terbuka"
        tab_name = app.overlay.nav_rail.tabs[cur_tab].label
        print(f"   Alt+Tab -> Berhasil beralih ke Tab {cur_tab}: '{tab_name}'")
        
    print("3. [PASS] Alt+Tab berhasil berpindah 7 tab secara siklis (0 -> 1 -> ... -> 6 -> 0)!")

    # -------------------------------------------------------------
    # 3. Test Alt + Shift + Tab (Reverse cycle)
    # -------------------------------------------------------------
    shift_mod = getattr(pygame, "KMOD_SHIFT", 0x0003)
    ev_rev = pygame.event.Event(pygame.KEYDOWN, key=K_TAB, mod=alt_mod | shift_mod)
    pygame.event.post(ev_rev)
    app._handle_events()
    assert app.overlay.nav_rail.active_tab == 6, f"Reverse tab dari 0 harusnya 6, got {app.overlay.nav_rail.active_tab}"
    print("4. [PASS] Alt+Shift+Tab berhasil beralih mundur ke tab sebelumnya (6: Settings)!")

    # -------------------------------------------------------------
    # 4. Test Ctrl+Tab alias
    # -------------------------------------------------------------
    ctrl_mod = getattr(pygame, "KMOD_CTRL", 0x00c0)
    ev_ctrl_tab = pygame.event.Event(pygame.KEYDOWN, key=K_TAB, mod=ctrl_mod)
    pygame.event.post(ev_ctrl_tab)
    app._handle_events()
    assert app.overlay.nav_rail.active_tab == 0, f"Ctrl+Tab dari 6 harusnya maju ke 0, got {app.overlay.nav_rail.active_tab}"
    print("5. [PASS] Ctrl+Tab alias juga berhasil ganti tab ke depan (0: Hero)!")

    # -------------------------------------------------------------
    # 5. Test di mode PRE_BATTLE & BATTLE
    # -------------------------------------------------------------
    # PRE_BATTLE
    app.game_mode = "PRE_BATTLE"
    app.overlay.dock.close()
    assert app.overlay.dock.is_open == False
    
    ev_tab_pb = pygame.event.Event(pygame.KEYDOWN, key=K_TAB, mod=0)
    pygame.event.post(ev_tab_pb)
    app._handle_events()
    assert app.overlay.dock.is_open == True, "TAB di PRE_BATTLE harus membuka panel, bukan exit battle"
    assert app.game_mode == "PRE_BATTLE", "Game mode harus tetap PRE_BATTLE"
    print("6. [PASS] TAB di PRE_BATTLE berhasil membuka panel tanpa menutup mode duel!")

    # BATTLE
    app.game_mode = "BATTLE"
    ev_alt_tab_bt = pygame.event.Event(pygame.KEYDOWN, key=K_TAB, mod=alt_mod)
    pygame.event.post(ev_alt_tab_bt)
    app._handle_events()
    assert app.overlay.nav_rail.active_tab == 1, "Alt+Tab di Battle harus mengganti tab"
    print("7. [PASS] Alt+Tab di mode BATTLE berhasil berpindah tab!")

    print("\n>>> ALL TESTS PASSED 100%! SHORTCUT TAB & ALT+TAB BERFUNGSI SEMPURNA! <<<")

if __name__ == "__main__":
    test_tab_shortcuts()
