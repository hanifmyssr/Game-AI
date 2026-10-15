"""Test visual rendering kartu antrian bertumpuk (deck of cards) tanpa kartu lama."""

import os
import pygame
from pygame.constants import SRCALPHA

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
screen = pygame.display.set_mode((1200, 800))

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.app import App
from game.npc_squad import NPCSquad, NPCMember

app = App()

squad = NPCSquad([
    NPCMember(name="Oyen the Warrior", char_type="warrior", max_hp=100, current_hp=100, potions=1, atk_bonus=5, def_bonus=5, eval_profile="BALANCED"),
    NPCMember(name="Kuro the Ranger", char_type="ranger", max_hp=80, current_hp=80, potions=1, atk_bonus=10, def_bonus=0, eval_profile="BALANCED"),
    NPCMember(name="Kage the Assassin", char_type="assassin", max_hp=70, current_hp=70, potions=0, atk_bonus=15, def_bonus=0, eval_profile="AGGRESSIVE"),
])

app.current_squad = squad
app.battle_system.reset_with_squad(squad, player=app.player)
app.game_mode = "BATTLE"

def render_queue_deck(surface, squad, fonts):
    w, h = surface.get_size()
    bench_w = 230
    bench_x = w - bench_w - 18
    header_y = 20

    # 1. Header Antrian Cadangan
    hdr_rect = pygame.Rect(bench_x, header_y, bench_w, 34)
    pygame.draw.rect(surface, (16, 20, 30, 240), hdr_rect, border_radius=8)
    pygame.draw.rect(surface, (65, 80, 110), hdr_rect, 1, border_radius=8)

    q_count = len([m for i, m in enumerate(squad.members) if i > squad.active_index])
    hdr_title = f"🎴 ANTRIAN CADANGAN ({q_count})"
    t_surf = fonts.get("bubble", fonts["sm"]).render(hdr_title, True, (255, 215, 75))
    surface.blit(t_surf, (hdr_rect.x + (bench_w - t_surf.get_width()) // 2, hdr_rect.y + 7))

    curr_y = header_y + 40

    # 2. Status Petarung Gugur
    defeated = [m for i, m in enumerate(squad.members) if i < squad.active_index]
    if defeated:
        d_h = 24
        d_rect = pygame.Rect(bench_x, curr_y, bench_w, d_h)
        pygame.draw.rect(surface, (28, 16, 18, 220), d_rect, border_radius=6)
        pygame.draw.rect(surface, (110, 45, 45), d_rect, 1, border_radius=6)
        d_txt = fonts["sm"].render("✕ Gugur: " + ", ".join(m.name.split()[0] for m in defeated), True, (235, 110, 110))
        surface.blit(d_txt, (bench_x + 8, curr_y + 4))
        curr_y += 30

    queue = [m for i, m in enumerate(squad.members) if i > squad.active_index]

    if not queue:
        # Jika tidak ada cadangan lagi (Duel Terakhir)
        empty_rect = pygame.Rect(bench_x, curr_y + 10, bench_w, 140)
        pygame.draw.rect(surface, (18, 20, 28, 225), empty_rect, border_radius=10)
        pygame.draw.rect(surface, (70, 80, 105), empty_rect, 1, border_radius=10)
        
        t1 = fonts.get("bubble", fonts["sm"]).render("⚡ DUEL TERAKHIR!", True, (255, 215, 80))
        t2 = fonts["sm"].render("Tidak ada cadangan tersisa.", True, (160, 175, 195))
        t3 = fonts["sm"].render("Habisi petarung di arena ini", True, (130, 145, 165))
        t4 = fonts["sm"].render("untuk meraih kemenangan!", True, (130, 145, 165))
        
        surface.blit(t1, t1.get_rect(center=(empty_rect.centerx, empty_rect.y + 30)))
        surface.blit(t2, t2.get_rect(center=(empty_rect.centerx, empty_rect.y + 60)))
        surface.blit(t3, t3.get_rect(center=(empty_rect.centerx, empty_rect.y + 88)))
        surface.blit(t4, t4.get_rect(center=(empty_rect.centerx, empty_rect.y + 108)))
        return

    # Ukuran kartu portrait deck
    card_w = 186
    card_h = 246
    
    # Base position untuk kartu paling depan (depth 0)
    # Jika ada 2 kartu di antrian, kita geser base sedikit ke kiri bawah agar tumpukan di belakang terlihat jelas
    max_depth = len(queue) - 1
    base_x = bench_x + 6
    base_y = curr_y + 16 + (max_depth * 14)

    # Gambar dari kedalaman terdalam (belakang) ke 0 (paling depan)
    for depth in range(len(queue) - 1, -1, -1):
        mem = queue[depth]
        is_front = (depth == 0)

        # Kartu di belakang bergeser ke kanan dan atas (+18 X, -16 Y per tingkat)
        offset_x = depth * 18
        offset_y = -depth * 16
        c_x = base_x + offset_x
        c_y = base_y + offset_y
        c_rect = pygame.Rect(c_x, c_y, card_w, card_h)

        ctype_lower = mem.char_type.lower()
        if ctype_lower == "warrior":
            theme_border = (225, 140, 45)
            theme_bg = (32, 26, 24)
            badge_text_class = "WARRIOR"
        elif ctype_lower == "ranger":
            theme_border = (48, 195, 95)
            theme_bg = (20, 30, 24)
            badge_text_class = "RANGER"
        elif ctype_lower == "mage":
            theme_border = (65, 155, 245)
            theme_bg = (20, 26, 38)
            badge_text_class = "MAGE"
        elif ctype_lower == "assassin":
            theme_border = (195, 65, 230)
            theme_bg = (28, 18, 32)
            badge_text_class = "ASSASSIN"
        else:
            theme_border = (180, 180, 190)
            theme_bg = (24, 24, 28)
            badge_text_class = "NPC"

        # 1. Bayangan kartu (Soft Drop Shadow)
        shadow_surf = pygame.Surface((card_w, card_h), SRCALPHA)
        shadow_alpha = 130 if is_front else 80
        shadow_surf.fill((0, 0, 0, shadow_alpha))
        surface.blit(shadow_surf, (c_x + 6, c_y + 8))

        # 2. Permukaan Kartu Utama
        card_surf = pygame.Surface((card_w, card_h), SRCALPHA)

        if not is_front:
            # Efek pencahayaan kartu belakang: lebih gelap dan kontras lebih redup
            dim_bg = tuple(max(10, int(c * 0.60)) for c in theme_bg)
            dim_bdr = tuple(max(35, int(c * 0.55)) for c in theme_border)
            card_surf.fill((*dim_bg, 245))
            pygame.draw.rect(card_surf, dim_bdr, (0, 0, card_w, card_h), 1, border_radius=10)

            # Tab / Badge pembeda di pojok kanan atas kartu belakang yang mencuat keluar
            peek_lbl = fonts["sm"].render(f"#{depth+1} {mem.name.split()[0]}", True, theme_border)
            peek_rect = pygame.Rect(card_w - peek_lbl.get_width() - 14, 6, peek_lbl.get_width() + 10, 18)
            pygame.draw.rect(card_surf, (20, 24, 34), peek_rect, border_radius=4)
            pygame.draw.rect(card_surf, dim_bdr, peek_rect, 1, border_radius=4)
            card_surf.blit(peek_lbl, (peek_rect.x + 5, peek_rect.y + 2))
        else:
            # Kartu paling depan: Terang, megah, border ganda
            card_surf.fill((*theme_bg, 252))
            pygame.draw.rect(card_surf, theme_border, (0, 0, card_w, card_h), 2, border_radius=10)
            pygame.draw.rect(card_surf, (255, 255, 255, 45), (2, 2, card_w - 4, card_h - 4), 1, border_radius=8)

            # Badge Utama: NEXT CHALLENGER
            badge_lbl = fonts["sm"].render("NEXT CHALLENGER ⏳", True, (255, 225, 90))
            badge_rect = pygame.Rect((card_w - badge_lbl.get_width() - 14) // 2, 7, badge_lbl.get_width() + 14, 18)
            pygame.draw.rect(card_surf, (60, 45, 15), badge_rect, border_radius=4)
            pygame.draw.rect(card_surf, (225, 180, 50), badge_rect, 1, border_radius=4)
            card_surf.blit(badge_lbl, (badge_rect.x + 7, badge_rect.y + 2))

        # 3. Bingkai Portrait Tengah
        p_size = 108
        p_x = (card_w - p_size) // 2
        p_y = 29
        p_rect = pygame.Rect(p_x, p_y, p_size, p_size)
        pygame.draw.rect(card_surf, (12, 14, 20), p_rect, border_radius=8)

        if mem.portrait:
            p_img = pygame.transform.smoothscale(mem.portrait, (p_size - 4, p_size - 4))
            if not is_front:
                # Sedikit beri bayangan transparan pada gambar portrait di belakang
                dark_tint = pygame.Surface((p_size - 4, p_size - 4), SRCALPHA)
                dark_tint.fill((0, 0, 0, 75))
                card_surf.blit(p_img, (p_x + 2, p_y + 2))
                card_surf.blit(dark_tint, (p_x + 2, p_y + 2))
            else:
                card_surf.blit(p_img, (p_x + 2, p_y + 2))
        else:
            ph = fonts.get("bubble", fonts["sm"]).render("🐱", True, (255, 255, 255))
            card_surf.blit(ph, ph.get_rect(center=p_rect.center))

        p_bdr_col = theme_border if is_front else tuple(max(30, int(c * 0.55)) for c in theme_border)
        pygame.draw.rect(card_surf, p_bdr_col, p_rect, 2 if is_front else 1, border_radius=8)

        # 4. Info Nama & Role (Footer Kartu)
        name_font = fonts.get("bubble", fonts["sm"])
        txt_name = name_font.render(mem.name, True, (255, 255, 255) if is_front else (170, 175, 185))
        card_surf.blit(txt_name, txt_name.get_rect(center=(card_w // 2, p_y + p_size + 14)))

        # Sub-info Job & AI Profile
        job_txt = fonts["sm"].render(f"{mem.char_type.capitalize()} • {mem.eval_profile}", True, theme_border if is_front else (135, 140, 155))
        card_surf.blit(job_txt, job_txt.get_rect(center=(card_w // 2, p_y + p_size + 30)))

        # 5. Baris Stat Pill: HP & ATK/DEF
        stat_rect = pygame.Rect(10, p_y + p_size + 44, card_w - 20, 24)
        pygame.draw.rect(card_surf, (16, 18, 26, 230), stat_rect, border_radius=6)
        pygame.draw.rect(card_surf, (50, 60, 80) if is_front else (35, 40, 55), stat_rect, 1, border_radius=6)

        stat_str = f"HP {mem.max_hp}  │ +{mem.atk_bonus}A +{mem.def_bonus}D"
        stat_lbl = fonts["sm"].render(stat_str, True, (220, 230, 245) if is_front else (145, 150, 160))
        card_surf.blit(stat_lbl, stat_lbl.get_rect(center=stat_rect.center))

        # Blit kartu ke layar
        surface.blit(card_surf, (c_x, c_y))


# Render arena tanpa kartu lama
# Kita bisa hack sementara _draw_battle_arena atau panggil bagian karakternya saja
screen.fill((10, 12, 18))
# Buat arena dasar
w, h = screen.get_size()
panel_w = 260
arena_w = w - panel_w
(p_pos, n_pos) = app._get_battle_char_positions()

# Player & NPC
target_h = 145
p_img = app.battle_sprites.get("player")
big_player = pygame.transform.smoothscale(p_img, (int(round(target_h * (p_img.get_width() / p_img.get_height()))), target_h))
n_img = squad.members[0].battle_sprite
big_npc = pygame.transform.smoothscale(n_img, (int(round(target_h * (n_img.get_width() / n_img.get_height()))), target_h))
screen.blit(big_player, big_player.get_rect(center=p_pos))
screen.blit(big_npc, big_npc.get_rect(center=n_pos))

# HP Bar
app._draw_hp_bar(p_pos[0], p_pos[1] + 98, "Bolu (Player)", 100, False, 2, (60, 160, 255), "", max_hp=100)
app._draw_hp_bar(n_pos[0], n_pos[1] + 98, "Oyen the Warrior", 100, False, 1, (255, 90, 80), "", max_hp=100)

# Render Deck of Queue Cards!
render_queue_deck(screen, squad, app.fonts)

out_file = "scratch/test_deck_preview.png"
pygame.image.save(screen, out_file)
print("Saved clean preview to:", out_file)
