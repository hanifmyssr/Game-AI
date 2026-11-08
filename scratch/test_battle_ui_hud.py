"""Test and prototype enlarged, centered Diamond Combat Hub without [T] button."""
import os
import sys
import pygame
from pygame.constants import SRCALPHA

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1, 1))

sys.path.insert(0, os.path.abspath("Game-AI"))
from game.core import config
from game.battle.npc_squad import NPCSquad, NPCMember
from game.battle.battle_background import BattleArenaBackground

def draw_test_battle_screen(w=1024, h=668, is_dock_open=False):
    screen = pygame.Surface((w, h))
    fonts = {
        "title": pygame.font.Font(None, 24),
        "bubble": pygame.font.Font(None, 20),
        "sm": pygame.font.Font(None, 17),
        "tiny": pygame.font.Font(None, 14),
    }

    # 1. Background
    bg = BattleArenaBackground()
    panel_w = config.TOTAL_DOCK_WIDTH if is_dock_open else config.TOTAL_COLLAPSED_WIDTH
    bench_w = 148
    arena_w = w - panel_w
    bg.draw(screen, panel_w, arena_w, h)

    # Mock Squad
    squad = NPCSquad()
    m1 = NPCMember(name="Oyen the Warrior", char_type="warrior", max_hp=60, atk_bonus=15, def_bonus=6)
    m2 = NPCMember(name="Kuro the Ranger", char_type="ranger", max_hp=60, atk_bonus=5, def_bonus=6)
    m3 = NPCMember(name="Shiro the Mage", char_type="mage", max_hp=60, atk_bonus=0, def_bonus=0)
    squad.members.append(m1)
    squad.members.append(m2)
    squad.members.append(m3)
    squad.active_index = 0

    # 2. Characters Centered
    bench_x = w - bench_w - 12
    combat_w = bench_x - 12 - panel_w
    combat_cx = panel_w + combat_w // 2
    player_arena_x = combat_cx - 135
    npc_arena_x = combat_cx + 135
    char_y = int(h * 0.35)

    # Draw dummy characters
    pygame.draw.circle(screen, (80, 160, 240), (player_arena_x, char_y), 36)
    p_lbl = fonts["sm"].render("Hero Bolu", True, (255, 255, 255))
    screen.blit(p_lbl, p_lbl.get_rect(center=(player_arena_x, char_y)))

    pygame.draw.circle(screen, (240, 90, 80), (npc_arena_x, char_y), 36)
    n_lbl = fonts["sm"].render("Oyen", True, (255, 255, 255))
    screen.blit(n_lbl, n_lbl.get_rect(center=(npc_arena_x, char_y)))

    # HP bars
    for cx, col, name, hp, max_hp in [
        (player_arena_x, (60, 160, 255), "Hero Player", 85, 100),
        (npc_arena_x, (255, 90, 80), "Oyen the Warrior", 45, 60),
    ]:
        bar_y = char_y + 54
        bg_bar = pygame.Rect(cx - 65, bar_y, 130, 16)
        pygame.draw.rect(screen, (20, 22, 28, 220), bg_bar, border_radius=4)
        fill_w = int(126 * (hp / max_hp))
        pygame.draw.rect(screen, col, (cx - 63, bar_y + 2, fill_w, 12), border_radius=3)
        txt = fonts["tiny"].render(f"{name}: {hp}/{max_hp}", True, (255, 255, 255))
        screen.blit(txt, txt.get_rect(center=bg_bar.center))

    # 3. Vertical Squad Queue on Right
    queue = [m for i, m in enumerate(squad.members) if i > squad.active_index]
    curr_y = 16
    hdr_rect = pygame.Rect(bench_x, curr_y, bench_w, 28)
    pygame.draw.rect(screen, (16, 20, 30, 235), hdr_rect, border_radius=6)
    pygame.draw.rect(screen, (65, 80, 110), hdr_rect, 1, border_radius=6)
    t_hdr = fonts["bubble"].render(f"CADANGAN ({len(queue)})", True, (255, 215, 75))
    screen.blit(t_hdr, t_hdr.get_rect(center=hdr_rect.center))
    curr_y += 34

    for depth, mem in enumerate(queue):
        is_next = (depth == 0)
        card_h = 52
        card_rect = pygame.Rect(bench_x, curr_y, bench_w, card_h)
        role_color = (52, 205, 105) if mem.char_type == "ranger" else (70, 165, 255)
        role_tag = "RNG" if mem.char_type == "ranger" else "MAG"

        bg_col = (26, 32, 46, 245) if is_next else (18, 22, 32, 225)
        bdr_col = (255, 205, 60) if is_next else (55, 68, 92)
        pygame.draw.rect(screen, bg_col, card_rect, border_radius=8)
        pygame.draw.rect(screen, bdr_col, card_rect, 2 if is_next else 1, border_radius=8)

        p_radius = 17
        p_cx = bench_x + 8 + p_radius
        p_cy = curr_y + card_h // 2
        pygame.draw.circle(screen, (12, 15, 22), (p_cx, p_cy), p_radius)
        ear_l = [(p_cx - 9, p_cy - 4), (p_cx - 4, p_cy - 13), (p_cx, p_cy - 5)]
        ear_r = [(p_cx, p_cy - 5), (p_cx + 4, p_cy - 13), (p_cx + 9, p_cy - 4)]
        pygame.draw.polygon(screen, role_color, ear_l)
        pygame.draw.polygon(screen, role_color, ear_r)
        pygame.draw.circle(screen, role_color, (p_cx, p_cy + 1), 9)
        pygame.draw.circle(screen, (255, 215, 80) if is_next else role_color, (p_cx, p_cy), p_radius, 2)

        info_x = p_cx + p_radius + 8
        txt_name = fonts["sm"].render(mem.name.split()[0], True, (255, 255, 255) if is_next else (205, 212, 225))
        screen.blit(txt_name, (info_x, curr_y + 6))
        if is_next:
            nb_rect = pygame.Rect(bench_x + bench_w - 38, curr_y + 6, 32, 14)
            pygame.draw.rect(screen, (255, 215, 75), nb_rect, border_radius=3)
            next_badge = fonts["tiny"].render("NEXT", True, (20, 15, 5))
            screen.blit(next_badge, (nb_rect.x + 3, nb_rect.y + 1))
        else:
            role_lbl = fonts["tiny"].render(role_tag, True, role_color)
            screen.blit(role_lbl, (bench_x + bench_w - role_lbl.get_width() - 8, curr_y + 7))

        bar_x = info_x
        bar_y = curr_y + 25
        bar_w = bench_x + bench_w - bar_x - 8
        pygame.draw.rect(screen, (12, 14, 20), (bar_x, bar_y, bar_w, 5), border_radius=2)
        pygame.draw.rect(screen, (65, 205, 100), (bar_x, bar_y, bar_w, 5), border_radius=2)
        hp_txt = fonts["tiny"].render(f"{mem.max_hp}/{mem.max_hp} HP", True, (160, 172, 192))
        screen.blit(hp_txt, (bar_x, curr_y + 34))
        curr_y += card_h + 8

    # ------------------------------------------------------------------ #
    # 4. ENLARGED & CENTERED RPG DIAMOND CROSS ACTION HUB
    # ------------------------------------------------------------------ #
    # Sizing parameters
    D = 38           # Radius from hub center to buttons
    btn_r = 17       # Circle button radius (was 13)
    ribbon_w = 172   # Ribbon width (was 142)
    ribbon_h = 32    # Ribbon height (was 24)
    guard_w = 155    # Guard ribbon width
    pot_w = 78       # Potion pill width (was 54)

    # Horizontally centered below the two fighting characters (combat_cx)
    # Calculate offset so the entire visual bounding box is centered at combat_cx
    left_span = D + pot_w
    right_span = D + max(ribbon_w, guard_w)
    hub_cx = combat_cx - (right_span - left_span) // 2

    # Vertical position: below characters and above battle log
    # For h=668, hub_cy ≈ 490. For h=800, hub_cy ≈ 530.
    hub_cy = int(h * 0.72)

    top_y = hub_cy - D
    bot_y = hub_cy + D
    right_x = hub_cx + D
    left_x = hub_cx - D

    # Hitboxes
    btn_action_heavy = pygame.Rect(hub_cx - btn_r, top_y - ribbon_h // 2, btn_r + 16 + ribbon_w, ribbon_h)
    btn_action_attack = pygame.Rect(hub_cx - btn_r, bot_y - ribbon_h // 2, btn_r + 16 + ribbon_w, ribbon_h)
    btn_action_defend = pygame.Rect(right_x - btn_r, hub_cy - ribbon_h // 2, btn_r + 16 + guard_w, ribbon_h)
    btn_action_potion = pygame.Rect(left_x - pot_w, hub_cy - ribbon_h // 2, pot_w + btn_r, ribbon_h)

    # Decorative Diamond Cross Background
    diamond_pad = 22
    diamond_pts = [
        (hub_cx, hub_cy - D - diamond_pad),
        (hub_cx + D + diamond_pad, hub_cy),
        (hub_cx, hub_cy + D + diamond_pad),
        (hub_cx - D - diamond_pad, hub_cy),
    ]
    pygame.draw.polygon(screen, (30, 24, 18, 240), diamond_pts)
    pygame.draw.polygon(screen, (205, 160, 55), diamond_pts, 3)
    inner_diamond = [
        (hub_cx, hub_cy - D + 4),
        (hub_cx + D - 4, hub_cy),
        (hub_cx, hub_cy + D - 4),
        (hub_cx - D + 4, hub_cy),
    ]
    pygame.draw.polygon(screen, (230, 185, 70, 130), inner_diamond, 1)

    # ------------------
    # TOP: (Y) 2. Kuat
    # ------------------
    ribbon_heavy_rect = pygame.Rect(hub_cx + 16, top_y - ribbon_h // 2, ribbon_w, ribbon_h)
    pygame.draw.rect(screen, (42, 30, 20, 245), ribbon_heavy_rect, border_radius=6)
    pygame.draw.rect(screen, (215, 160, 45), ribbon_heavy_rect, 2, border_radius=6)
    t_heavy = fonts["bubble"].render("2. Kuat", True, (255, 220, 90))
    screen.blit(t_heavy, (ribbon_heavy_rect.x + 10, ribbon_heavy_rect.y + 6))
    s_heavy = fonts["tiny"].render("Dmg: 30-45", True, (220, 205, 180))
    screen.blit(s_heavy, (ribbon_heavy_rect.right - s_heavy.get_width() - 10, ribbon_heavy_rect.y + 10))

    pygame.draw.circle(screen, (235, 145, 25), (hub_cx, top_y), btn_r)
    pygame.draw.circle(screen, (255, 245, 190), (hub_cx, top_y), btn_r, 2)
    txt_y = fonts["bubble"].render("Y", True, (255, 255, 255))
    screen.blit(txt_y, txt_y.get_rect(center=(hub_cx, top_y)))

    # ------------------
    # BOTTOM: (A) 1. Serang
    # ------------------
    ribbon_atk_rect = pygame.Rect(hub_cx + 16, bot_y - ribbon_h // 2, ribbon_w, ribbon_h)
    pygame.draw.rect(screen, (22, 38, 26, 245), ribbon_atk_rect, border_radius=6)
    pygame.draw.rect(screen, (75, 195, 95), ribbon_atk_rect, 2, border_radius=6)
    t_atk = fonts["bubble"].render("1. Serang", True, (140, 245, 155))
    screen.blit(t_atk, (ribbon_atk_rect.x + 10, ribbon_atk_rect.y + 6))
    s_atk = fonts["tiny"].render("Dmg: 15-25", True, (190, 225, 195))
    screen.blit(s_atk, (ribbon_atk_rect.right - s_atk.get_width() - 10, ribbon_atk_rect.y + 10))

    pygame.draw.circle(screen, (42, 170, 70), (hub_cx, bot_y), btn_r)
    pygame.draw.circle(screen, (200, 255, 215), (hub_cx, bot_y), btn_r, 2)
    txt_a = fonts["bubble"].render("A", True, (255, 255, 255))
    screen.blit(txt_a, txt_a.get_rect(center=(hub_cx, bot_y)))

    # ------------------
    # RIGHT: (B) 3. Bertahan
    # ------------------
    ribbon_def_rect = pygame.Rect(right_x + 16, hub_cy - ribbon_h // 2, guard_w, ribbon_h)
    pygame.draw.rect(screen, (28, 36, 50, 245), ribbon_def_rect, border_radius=6)
    pygame.draw.rect(screen, (95, 165, 245), ribbon_def_rect, 2, border_radius=6)
    t_def = fonts["bubble"].render("3. Bertahan", True, (150, 215, 255))
    screen.blit(t_def, (ribbon_def_rect.x + 10, ribbon_def_rect.y + 6))
    s_def = fonts["tiny"].render("-50% Ctr", True, (185, 205, 230))
    screen.blit(s_def, (ribbon_def_rect.right - s_def.get_width() - 8, ribbon_def_rect.y + 10))

    pygame.draw.circle(screen, (60, 75, 98), (right_x, hub_cy), btn_r)
    pygame.draw.circle(screen, (220, 235, 255), (right_x, hub_cy), btn_r, 2)
    txt_b = fonts["bubble"].render("B", True, (255, 255, 255))
    screen.blit(txt_b, txt_b.get_rect(center=(right_x, hub_cy)))

    # ------------------
    # LEFT: (X) Potion
    # ------------------
    pot_pill = pygame.Rect(left_x - pot_w, hub_cy - ribbon_h // 2, pot_w - 2, ribbon_h)
    pygame.draw.rect(screen, (38, 26, 46, 245), pot_pill, border_radius=6)
    pygame.draw.rect(screen, (195, 95, 235), pot_pill, 2, border_radius=6)
    t_pot = fonts["bubble"].render("x2 Ramuan", True, (240, 170, 255))
    screen.blit(t_pot, t_pot.get_rect(center=pot_pill.center))

    pygame.draw.circle(screen, (50, 105, 225), (left_x, hub_cy), btn_r)
    pygame.draw.circle(screen, (205, 230, 255), (left_x, hub_cy), btn_r, 2)
    txt_x = fonts["bubble"].render("X", True, (255, 255, 255))
    screen.blit(txt_x, txt_x.get_rect(center=(left_x, hub_cy)))

    # ------------------------------------------------------------------ #
    # 5. BATTLE LOG BOX (Positioned below the action hub or full bottom)
    # ------------------------------------------------------------------ #
    log_h = 78
    log_y = h - log_h - 10
    log_x = panel_w + 16
    log_w = (bench_x - 12) - log_x

    log_rect = pygame.Rect(log_x, log_y, log_w, log_h)
    pygame.draw.rect(screen, (252, 249, 242, 245), log_rect, border_radius=8)
    pygame.draw.rect(screen, (208, 196, 178), log_rect, 1, border_radius=8)

    ltitle = fonts["sm"].render("RIWAYAT PERTEMPURAN", True, config.COLOR_TEXT_PRIMARY)
    screen.blit(ltitle, (log_rect.x + 12, log_rect.y + 6))

    dummy_logs = [
        "Pertarungan dimulai! Player berhadapan dengan Oyen the Warrior.",
        "Player menggunakan Serangan Kuat (Dmg: 38)!",
        "Giliran Player. Pilih perintah bertarung di atas.",
    ]
    ly = log_rect.y + 24
    for line in dummy_logs:
        ts = fonts["tiny"].render(f"• {line}", True, config.COLOR_TEXT_PRIMARY)
        screen.blit(ts, (log_rect.x + 12, ly))
        ly += 17

    return screen

img_closed = draw_test_battle_screen(1024, 668, is_dock_open=False)
out_path = "C:/Users/Pavilion/.gemini/antigravity/brain/38f4bb8b-a421-4acf-b988-2e6d2a7fae0d/test_enlarged_centered_hub_1024x668.png"
pygame.image.save(img_closed, out_path)

img_open = draw_test_battle_screen(1024, 668, is_dock_open=True)
out_path_open = "C:/Users/Pavilion/.gemini/antigravity/brain/38f4bb8b-a421-4acf-b988-2e6d2a7fae0d/test_enlarged_centered_hub_dock_open.png"
pygame.image.save(img_open, out_path_open)

img_full = draw_test_battle_screen(1280, 800, is_dock_open=True)
out_path_full = "C:/Users/Pavilion/.gemini/antigravity/brain/38f4bb8b-a421-4acf-b988-2e6d2a7fae0d/test_enlarged_centered_hub_1280x800.png"
pygame.image.save(img_full, out_path_full)

print("Saved enlarged centered hub prototypes.")
