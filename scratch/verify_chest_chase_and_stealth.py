import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.abspath("."))

import pygame
from game.app import App
from game import config

print("=== 1. INISIALISASI GAME APP ===")
pygame.init()
app = App()

# -------------------------------------------------------------
# 1. VERIFIKASI SEMAK-SEMAK KIRI ATAS
# -------------------------------------------------------------
print("\n=== 2. VERIFIKASI SEMAK KIRI ATAS ===")
top_left_bushes = [(12, 4), (11, 5), (12, 5), (9, 9), (9, 10), (10, 10), (9, 16), (10, 16)]
for b in top_left_bushes:
    assert app.map.is_bush(b), f"Semak {b} harus terdaftar di bush_set!"
    assert app.map.is_walkable(b), f"Semak {b} harus walkable!"

# Uji Bolu masuk ke semak (12, 4)
app.player.grid = (12, 4)
app.player.x = 12 * 16
app.player.y = 4 * 16
app.player.moving = False
app.player.update(0.1)
assert app.player.is_hidden, "Player di (12, 4) harus is_hidden == True!"
print(f"Bolu di (12, 4): is_hidden={app.player.is_hidden} -> [BERHASIL SEMBUNYI]")

# -------------------------------------------------------------
# 2. VERIFIKASI PEMBUKAAN PETI A (KIRI ATAS)
# -------------------------------------------------------------
print("\n=== 3. VERIFIKASI PEMBUKAAN PETI A (KIRI ATAS) ===")
# Peti A ada di app.chests[0] pada pos (9, 3)
chest_a = app.chests[0]
print(f"Peti A pos: {chest_a['pos']}")
app._open_chest(chest_a)

# Shiro (Mage utara) harus mengejar
print(f"Status Chaser assigned: {app.inter_npc_manager.chaser_assigned}")
print(f"Shiro chasing: {app.npc_shiro.chasing}")
print(f"Oyen chasing: {app.npc.chasing}")
print(f"Kuro chasing: {app.npc_kuro.chasing}")

assert app.inter_npc_manager.chaser_assigned == "Shiro", "Peti A dibuka -> Shiro wajib jadi chaser!"
assert app.npc_shiro.chasing == True, "Shiro WAJIB chasing == True saat Peti A dibuka!"
assert app.npc_kuro.chasing == False, "Kuro di kanan TIDAK BOLEH ikut mengejar Peti A di utara!"
print("[BERHASIL] Peti A dibuka: Shiro mengejar, Kuro & Oyen tetap menjaga pos!")

# -------------------------------------------------------------
# 3. VERIFIKASI PEMBUKAAN PETI B (KIRI BAWAH)
# -------------------------------------------------------------
print("\n=== 4. VERIFIKASI PEMBUKAAN PETI B (KIRI BAWAH) ===")
# Selesaikan gacha timer dari peti A
app.gacha_active = False
app.gacha_showcase = None

# Peti B ada di app.chests[1] pada pos (5, 24)
chest_b = app.chests[1]
print(f"Peti B pos: {chest_b['pos']}")
app._open_chest(chest_b)

print(f"Status Chaser assigned: {app.inter_npc_manager.chaser_assigned}")
print(f"Shiro chasing: {app.npc_shiro.chasing}")
print(f"Oyen chasing: {app.npc.chasing}")
print(f"Kuro chasing: {app.npc_kuro.chasing}")

assert app.inter_npc_manager.chaser_assigned == "Oyen", "Peti B dibuka -> Oyen wajib jadi chaser!"
assert app.npc.chasing == True, "Oyen WAJIB chasing == True saat Peti B dibuka!"
assert app.npc_kuro.chasing == False, "Kuro di kanan TIDAK BOLEH mengejar saat Peti B dibuka!"
print("[BERHASIL] Peti B dibuka: Oyen mengejar, Kuro tetap di jembatan kanan!")

# -------------------------------------------------------------
# 4. VERIFIKASI PEMBUKAAN PETI C (KANAN / TIMUR)
# -------------------------------------------------------------
print("\n=== 5. VERIFIKASI PEMBUKAAN PETI C (KANAN / TIMUR) ===")
app.gacha_active = False
app.gacha_showcase = None

chest_c = app.chests[2]
print(f"Peti C pos: {chest_c['pos']}")
app._open_chest(chest_c)

print(f"Status Chaser assigned: {app.inter_npc_manager.chaser_assigned}")
print(f"Shiro chasing: {app.npc_shiro.chasing}")
print(f"Oyen chasing: {app.npc.chasing}")
print(f"Kuro chasing: {app.npc_kuro.chasing}")

assert app.inter_npc_manager.chaser_assigned == "Kuro", "Peti C dibuka -> Kuro wajib jadi chaser!"
assert app.npc_kuro.chasing == True, "Kuro WAJIB chasing == True saat Peti C dibuka!"
assert app.npc.chasing == False, "Oyen TIDAK BOLEH mengejar saat Peti C dibuka!"
assert app.npc_shiro.chasing == False, "Shiro TIDAK BOLEH mengejar saat Peti C dibuka!"
print("[BERHASIL] Peti C dibuka: Kuro mengejar, Shiro & Oyen menjaga pos!")

# -------------------------------------------------------------
# 5. VERIFIKASI MEKANIK STEALTH & QUICK RETURN TO PATROL
# -------------------------------------------------------------
print("\n=== 6. VERIFIKASI STEALTH & QUICK RETURN TO PATROL ===")
# Simulasikan Kuro sedang mengejar Bolu dari pos (20, 20)
app.npc_kuro.grid = (20, 20)
app.npc_kuro.px = 20 * 16
app.npc_kuro.py = 20 * 16
app.npc_kuro.chasing = True
app.npc_kuro.moving = False
app.npc_kuro.is_returning_to_patrol = False

# Bolu bersembunyi di semak pada jarak 3 tile: (17, 20)
app.player.grid = (17, 20)
app.player.is_hidden = True

# Update Kuro: harus kehilangan jejak karena player tersembunyi
app.npc_kuro.update(0.1)
print(f"Kuro chasing: {app.npc_kuro.chasing}")
print(f"Kuro is_returning_to_patrol: {app.npc_kuro.is_returning_to_patrol}")
print(f"Kuro speech: {app.npc_kuro.speech_bubble}")

assert app.npc_kuro.chasing == False, "Kuro harus berhenti mengejar saat pemain bersembunyi di semak!"
assert app.npc_kuro.is_returning_to_patrol == True, "Kuro harus mengaktifkan mode kembali cepat ke pos!"
assert app.npc_kuro.speech_bubble == "Kehilangan jejak...", "Kuro harus berkata 'Kehilangan jejak...'"

# Simulasikan gerakan kembali cepat Kuro selama beberapa langkah menuju waypoint pos dekat Peti C
start_dist = abs(app.npc_kuro.grid[0] - 33) + abs(app.npc_kuro.grid[1] - 27)
for _ in range(40):
    app.npc_kuro.update(0.1)

end_dist = abs(app.npc_kuro.grid[0] - 33) + abs(app.npc_kuro.grid[1] - 27)
print(f"Kuro bergerak kembali: posisi sekarang {app.npc_kuro.grid}, jarak ke waypoint (33, 27): {end_dist} (dari awal {start_dist})")
assert end_dist < start_dist, "Kuro harus bergerak mendekat kembali ke rute patrolinya!"

print("\n=======================================================")
print(">>> SEMUA 3 POIN PERBAIKAN BERHASIL TERVERIFIKASI 100%! <<<")
print("=======================================================")

# Simpan tangkapan layar verifikasi visual
artifact_dir = r"C:\Users\Pavilion\.gemini\antigravity\brain\38f4bb8b-a421-4acf-b988-2e6d2a7fae0d"

# 1. Bolu sembunyi di semak kiri atas (12, 4)
app.player.grid = (12, 4)
app.player.x = 12 * 16
app.player.y = 4 * 16
app.player.moving = False
app.player.update(0.1)
app.camera.follow((app.player.x, app.player.y))
app.screen.fill((0, 0, 0))
app._draw()
shot1 = os.path.join(artifact_dir, "verify_top_left_bush_stealth.png")
pygame.image.save(app.screen, shot1)
print(f"Saved {shot1}")

# 2. Shiro mengejar Bolu dari sektor utara
app.npc_shiro.chasing = True
app.npc_shiro.speech_bubble = "Peti A dijarah! Berhenti!"
app.npc_shiro.speech_timer = 3.0
app.camera.follow((app.npc_shiro.px, app.npc_shiro.py))
app.screen.fill((0, 0, 0))
app._draw()
shot2 = os.path.join(artifact_dir, "verify_shiro_chase.png")
pygame.image.save(app.screen, shot2)
print(f"Saved {shot2}")
