"""Test responsive scaling of the 4-direction action hub on 1280x800 and 1024x668."""
import os
import sys
import pygame
from pygame.constants import SRCALPHA, RESIZABLE

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()

sys.path.insert(0, os.path.abspath("Game-AI"))
from game.app import App
from game import config
from game.ui.components import draw_card

def draw_responsive_hub(self, hover_action="ATTACK"):
    w, h = self.screen.get_size()
    is_dock_open = getattr(self.overlay.dock, "is_open", False) if hasattr(self, "overlay") and hasattr(self.overlay, "dock") else False
    panel_w = config.TOTAL_DOCK_WIDTH if is_dock_open else config.TOTAL_COLLAPSED_WIDTH
    bench_w = 148
    bench_x = w - bench_w - 12
    combat_w = bench_x - 12 - panel_w
    combat_cx = panel_w + combat_w // 2

    # Responsive dimensions
    is_compact = (w < 1180 or h < 750)
    card_w = 196 if is_compact else 222
    card_h = 44 if is_compact else 48
    badge_r = 16 if is_compact else 18
    D_X = 26 if is_compact else 34
    D_Y = 48 if is_compact else 54

    hub_cx = combat_cx
    hub_cy = int(h * 0.69) if h >= 750 else int(h * 0.66)

    st = self.battle_system.state
    can_act = (
        not st.is_npc_turn
        and not self.battle_system.is_finished
        and not self.card_summon_anim
        and not getattr(self, "loot_modal", None)
        and not self.npc_defeat_anim
    )

    font_bubble = self.fonts.get("bubble", self.fonts["sm"])
    font_sm = self.fonts["sm"]
    font_tiny = self.fonts["tiny"]
    surf = self.screen

    top_rect = pygame.Rect(hub_cx - card_w // 2, hub_cy - D_Y - card_h, card_w, card_h)
    bot_rect = pygame.Rect(hub_cx - card_w // 2, hub_cy + D_Y, card_w, card_h)
    left_rect = pygame.Rect(hub_cx - D_X - card_w, hub_cy - card_h // 2, card_w, card_h)
    right_rect = pygame.Rect(hub_cx + D_X, hub_cy - card_h // 2, card_w, card_h)

    # Hover flags
    is_hov_atk = (hover_action == "ATTACK")
    is_hov_hvy = (hover_action == "HEAVY")
    is_hov_def = (hover_action == "DEFEND")
    is_hov_pot = (hover_action == "POTION")

    # Center Emblem: Ornate Diamond Crest with Gold Connectors
    crest_size = 24 if is_compact else 28
    pygame.draw.line(surf, (205, 160, 50), (hub_cx, hub_cy - crest_size), (hub_cx, top_rect.bottom), 3)
    pygame.draw.line(surf, (205, 160, 50), (hub_cx, hub_cy + crest_size), (hub_cx, bot_rect.top), 3)
    pygame.draw.line(surf, (205, 160, 50), (hub_cx - crest_size, hub_cy), (left_rect.right, hub_cy), 3)
    pygame.draw.line(surf, (205, 160, 50), (hub_cx + crest_size, hub_cy), (right_rect.left, hub_cy), 3)

    diamond_pts = [
        (hub_cx, hub_cy - crest_size),
        (hub_cx + crest_size, hub_cy),
        (hub_cx, hub_cy + crest_size),
        (hub_cx - crest_size, hub_cy),
    ]
    pygame.draw.polygon(surf, (26, 20, 16, 245), diamond_pts)
    pygame.draw.polygon(surf, (215, 170, 55), diamond_pts, 3)
    inner_dia = [
        (hub_cx, hub_cy - crest_size + 4),
        (hub_cx + crest_size - 4, hub_cy),
        (hub_cx, hub_cy + crest_size - 4),
        (hub_cx - crest_size + 4, hub_cy),
    ]
    pygame.draw.polygon(surf, (240, 200, 90, 150), inner_dia, 1)
    pygame.draw.circle(surf, config.COLOR_ACCENT_GOLD, (hub_cx, hub_cy), 4)

    # 1. TOP: Serang Biasa (Shortcut: 1)
    bg_atk = (32, 58, 38, 252) if is_hov_atk else ((22, 44, 28, 245) if can_act else (20, 24, 20, 220))
    bdr_atk = config.COLOR_ACCENT_GOLD if is_hov_atk else ((85, 215, 110) if can_act else (70, 90, 75))
    draw_card(surf, top_rect, bg_atk, border_color=bdr_atk, border_radius=8)
    bg1_cx, bg1_cy = top_rect.x + (24 if is_compact else 28), top_rect.centery
    pygame.draw.circle(surf, (60, 210, 100) if is_hov_atk else ((45, 185, 80) if can_act else (50, 95, 60)), (bg1_cx, bg1_cy), badge_r)
    pygame.draw.circle(surf, (220, 255, 230) if can_act else (110, 140, 120), (bg1_cx, bg1_cy), badge_r, 2)
    txt_1 = font_bubble.render("1", True, (255, 255, 255) if can_act else (180, 190, 180))
    surf.blit(txt_1, txt_1.get_rect(center=(bg1_cx, bg1_cy)))
    tx_off = 46 if is_compact else 54
    t_atk = font_bubble.render("Serang Biasa", True, (160, 255, 175) if can_act else config.COLOR_TEXT_MUTED)
    d_atk = font_tiny.render("Dmg: 15-25  │  Tanpa CD", True, (210, 245, 215) if can_act else config.COLOR_TEXT_MUTED)
    surf.blit(t_atk, (top_rect.x + tx_off, top_rect.y + (5 if is_compact else 7)))
    surf.blit(d_atk, (top_rect.x + tx_off, top_rect.y + (24 if is_compact else 27)))

    # 2. LEFT: Heavy Attack (Shortcut: 2)
    heavy_ready = can_act and (st.player_heavy_cd == 0)
    bg_hvy = (64, 46, 26, 252) if is_hov_hvy else ((46, 32, 18, 245) if heavy_ready else (26, 22, 18, 220))
    bdr_hvy = config.COLOR_ACCENT_GOLD if is_hov_hvy else ((240, 170, 50) if heavy_ready else (100, 85, 70))
    draw_card(surf, left_rect, bg_hvy, border_color=bdr_hvy, border_radius=8)
    bg2_cx, bg2_cy = left_rect.x + (24 if is_compact else 28), left_rect.centery
    pygame.draw.circle(surf, (255, 165, 35) if is_hov_hvy else ((235, 145, 25) if heavy_ready else (120, 90, 50)), (bg2_cx, bg2_cy), badge_r)
    pygame.draw.circle(surf, (255, 245, 195) if heavy_ready else (140, 110, 70), (bg2_cx, bg2_cy), badge_r, 2)
    txt_2 = font_bubble.render("2", True, (255, 255, 255) if heavy_ready else (180, 170, 160))
    surf.blit(txt_2, txt_2.get_rect(center=(bg2_cx, bg2_cy)))
    t_hvy = font_bubble.render("Serangan Kuat", True, (255, 230, 110) if heavy_ready else config.COLOR_TEXT_MUTED)
    d_hvy_txt = "Dmg: 30-45  │  Siap Pakai" if heavy_ready else f"Sedang Jeda  │  CD: {st.player_heavy_cd}"
    d_hvy = font_tiny.render(d_hvy_txt, True, (245, 225, 200) if heavy_ready else config.COLOR_TEXT_MUTED)
    surf.blit(t_hvy, (left_rect.x + tx_off, left_rect.y + (5 if is_compact else 7)))
    surf.blit(d_hvy, (left_rect.x + tx_off, left_rect.y + (24 if is_compact else 27)))

    # 3. RIGHT: Defense (Shortcut: 3)
    bg_def = (38, 54, 82, 252) if is_hov_def else ((26, 38, 60, 245) if can_act else (20, 22, 28, 220))
    bdr_def = config.COLOR_ACCENT_GOLD if is_hov_def else ((105, 180, 255) if can_act else (70, 85, 105))
    draw_card(surf, right_rect, bg_def, border_color=bdr_def, border_radius=8)
    bg3_cx, bg3_cy = right_rect.x + (24 if is_compact else 28), right_rect.centery
    pygame.draw.circle(surf, (75, 145, 245) if is_hov_def else ((55, 125, 225) if can_act else (45, 52, 65)), (bg3_cx, bg3_cy), badge_r)
    pygame.draw.circle(surf, (225, 240, 255) if can_act else (110, 120, 140), (bg3_cx, bg3_cy), badge_r, 2)
    txt_3 = font_bubble.render("3", True, (255, 255, 255) if can_act else (175, 180, 190))
    surf.blit(txt_3, txt_3.get_rect(center=(bg3_cx, bg3_cy)))
    t_def = font_bubble.render("Bertahan", True, (165, 225, 255) if can_act else config.COLOR_TEXT_MUTED)
    d_def = font_tiny.render("-50% Dmg  │  Balas Serang", True, (205, 225, 250) if can_act else config.COLOR_TEXT_MUTED)
    surf.blit(t_def, (right_rect.x + tx_off, right_rect.y + (5 if is_compact else 7)))
    surf.blit(d_def, (right_rect.x + tx_off, right_rect.y + (24 if is_compact else 27)))

    # 4. BOTTOM: Ramuan (Shortcut: 4)
    pot_ready = can_act and (st.player_potions > 0)
    bg_pot = (62, 34, 72, 252) if is_hov_pot else ((44, 24, 52, 245) if pot_ready else (24, 20, 28, 220))
    bdr_pot = config.COLOR_ACCENT_GOLD if is_hov_pot else ((210, 110, 250) if pot_ready else (95, 75, 105))
    draw_card(surf, bot_rect, bg_pot, border_color=bdr_pot, border_radius=8)
    bg4_cx, bg4_cy = bot_rect.x + (24 if is_compact else 28), bot_rect.centery
    pygame.draw.circle(surf, (185, 90, 235) if is_hov_pot else ((165, 75, 215) if pot_ready else (55, 75, 120)), (bg4_cx, bg4_cy), badge_r)
    pygame.draw.circle(surf, (245, 220, 255) if pot_ready else (100, 115, 150), (bg4_cx, bg4_cy), badge_r, 2)
    txt_4 = font_bubble.render("4", True, (255, 255, 255) if pot_ready else (175, 185, 205))
    surf.blit(txt_4, txt_4.get_rect(center=(bg4_cx, bg4_cy)))
    t_pot = font_bubble.render("Gunakan Ramuan", True, (245, 185, 255) if pot_ready else config.COLOR_TEXT_MUTED)
    d_pot = font_tiny.render(f"x{st.player_potions} Botol  │  Pulihkan +25 HP", True, (235, 210, 250) if pot_ready else config.COLOR_TEXT_MUTED)
    surf.blit(t_pot, (bot_rect.x + tx_off, bot_rect.y + (5 if is_compact else 7)))
    surf.blit(d_pot, (bot_rect.x + tx_off, bot_rect.y + (24 if is_compact else 27)))

    # Battle log
    log_h = 92 if h < 750 else 112
    log_y = h - log_h - 10
    log_x = panel_w + 16
    log_w = (bench_x - 12) - log_x
    self.battle_log_rect = pygame.Rect(log_x, log_y, log_w, log_h)
    draw_card(self.screen, self.battle_log_rect, (252, 249, 242, 245), border_color=(208, 196, 178), border_radius=8)
    ltitle = font_bubble.render("RIWAYAT PERTEMPURAN", True, config.COLOR_TEXT_PRIMARY)
    self.screen.blit(ltitle, (self.battle_log_rect.x + 12, self.battle_log_rect.y + 7))
    ts = font_sm.render("• Giliran Player! Tekan [1] Serang, [2] Serangan Kuat, [3] Bertahan, [4] Ramuan.", True, config.COLOR_TEXT_SECONDARY)
    self.screen.blit(ts, (self.battle_log_rect.x + 12, self.battle_log_rect.y + 28))

    # Dock panel
    self.overlay.dock.draw(self.screen)

def run_test():
    app = App()
    app.enter_pre_battle()
    app.enter_battle()

    # 1024x668 Dock Open
    app.screen = pygame.display.set_mode((1024, 668), RESIZABLE)
    app._on_window_resized(1024, 668)
    panel_w = config.TOTAL_DOCK_WIDTH
    arena_w_compact = 1024 - panel_w
    app.battle_bg.draw(app.screen, panel_w, arena_w_compact, 668)
    pos_p, pos_n = app._get_battle_char_positions()
    p_img = app.battle_sprites.get("player", app.player.sprite.current_image)
    target_h = 135
    p_aspect = p_img.get_width() / float(p_img.get_height())
    big_player = pygame.transform.smoothscale(p_img, (int(round(target_h * p_aspect)), target_h))
    app.screen.blit(big_player, big_player.get_rect(center=pos_p))

    active_member = app.current_squad.get_active_member() if app.current_squad else None
    n_img = active_member.battle_sprite if active_member and active_member.battle_sprite else app.npc.sprite.current_image
    n_aspect = n_img.get_width() / float(n_img.get_height())
    big_npc = pygame.transform.smoothscale(n_img, (int(round(target_h * n_aspect)), target_h))
    app.screen.blit(big_npc, big_npc.get_rect(center=pos_n))

    st = app.battle_system.state
    # Place HP bar with good clearance
    app._draw_hp_bar(pos_p[0], pos_p[1] + 82, "Hero Player", st.player_hp, False, st.player_potions, (60, 160, 255), max_hp=100)
    app._draw_hp_bar(pos_n[0], pos_n[1] + 82, active_member.name if active_member else "Oyen", st.npc_hp, False, st.npc_potions, (255, 90, 80), max_hp=70)
    app._draw_battle_queue_deck(1024, 668)

    draw_responsive_hub(app)
    out_1024 = "C:/Users/Pavilion/.gemini/antigravity/brain/38f4bb8b-a421-4acf-b988-2e6d2a7fae0d/eval_responsive_hub_1024x668.png"
    pygame.image.save(app.screen, out_1024)
    print(f"Saved: {out_1024}")

if __name__ == "__main__":
    run_test()
