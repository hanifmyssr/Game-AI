"""BattleModeMixin: Transisi duel, arena turn-based, tag-in card animation, dan loot modal."""

import math
import os
from typing import Optional, Dict, Any, List, Tuple
import pygame

from ..core import config
from ..ui.components import draw_card
from ..battle.npc_squad import NPCSquad
from ..ai.battle_ai import ACTION_ATTACK, ACTION_HEAVY, ACTION_DEFEND, ACTION_POTION
from ..planning.domain_world_patrol import create_world_patrol_problem
from ..planning.domain_battle_tactics import create_battle_tactics_problem

SRCALPHA = getattr(pygame, "SRCALPHA", 0x00010000)


class BattleModeMixin:
    """Mixin method mode Battle untuk App."""

    def enter_pre_battle(self, leader_npc=None):
        self.current_encounter_npc = leader_npc
        self.game_mode = "PRE_BATTLE"
        self.overlay.set_mode("PRE_BATTLE")
        self.overlay.set_chasing_visualization(False)
        self.overlay.stop_path_animation()
        for n in (getattr(self, "npc", None), getattr(self, "npc_kuro", None), getattr(self, "npc_shiro", None)):
            if n:
                n.chasing = False
                n.investigating = False
        # Jika darah player sebelumnya habis/kalah atau <= 10, pulihkan penuh ke 100
        if getattr(self.player, "persistent_hp", 100) <= 10:
            self.player.persistent_hp = 100
            self.player.persistent_potions = max(2, self.player.persistent_potions)
        self._run_optimization()
        self.pre_battle_anim = {
            "phase": "REVEAL",
            "timer": 0.0,
            "search_dur": 0.0,
            "stagger": 0.13,
            "fade_dur": 0.26,
            "popped": set(),
        }

    def enter_battle(self):
        self.game_mode = "BATTLE"
        self.pre_battle_anim = None
        self.overlay.set_mode("BATTLE")
        self.overlay.set_chasing_visualization(False)
        self.overlay.stop_path_animation()
        for n in (getattr(self, "npc", None), getattr(self, "npc_kuro", None), getattr(self, "npc_shiro", None)):
            if n:
                n.chasing = False
                n.investigating = False
        self.npc_battle_turn_timer = 0.0
        self.battle_log_scroll_offset = 0
        self.card_summon_anim = None
        self.loot_modal = None
        self.battle_result_modal = None
        self.npc_defeat_anim = None
        self.final_loot_shown = False
        if hasattr(self, "vfx") and self.vfx:
            self.vfx.animations.clear()
        if hasattr(self, "overlay") and hasattr(self.overlay, "nav_rail"):
            self.overlay.nav_rail.set_badge(5, active=False)
        # Jika darah player sebelumnya habis/kalah atau <= 10, pulihkan penuh ke 100
        if getattr(self.player, "persistent_hp", 100) <= 10:
            self.player.persistent_hp = 100
            self.player.persistent_potions = max(2, self.player.persistent_potions)
        if self.current_squad:
            self.current_squad.reset()
            self.battle_system.reset_with_squad(self.current_squad, player=self.player)
        else:
            self.battle_system.reset()
        # Hitung preview awal evaluasi AI untuk metrik & skor aksi di panel
        self.battle_system.update_ai_preview()

    def enter_boss_battle(self):
        """Memulai pertarungan langsung menghadapi Boss Kage the Shadow Lord."""
        self.is_boss_battle = True
        self.current_encounter_npc = None
        self.current_squad = NPCSquad.create_boss_squad()
        self.enter_battle()

    def exit_battle(self):
        self.game_mode = "EXPLORATION"
        self.overlay.set_mode("EXPLORATION")
        self.battle_reentry_locked = True
        self.battle_reentry_timer = 2.5
        self.is_boss_battle = False
        self.pre_battle_anim = None
        self.card_summon_anim = None
        self.loot_toast = None
        self.loot_modal = None
        self.battle_result_modal = None
        self.npc_defeat_anim = None
        self.final_loot_shown = False
        if hasattr(self, "vfx") and self.vfx:
            self.vfx.animations.clear()
        if hasattr(self, "overlay") and hasattr(self.overlay, "nav_rail"):
            self.overlay.nav_rail.set_badge(5, active=False)

        # 1. Hentikan status pengejaran (chasing) pada SEMUA NPC tanpa kecuali
        for n in (getattr(self, "npc", None), getattr(self, "npc_kuro", None), getattr(self, "npc_shiro", None)):
            if n:
                n.chasing = False
                n.moving = False
                n.path = []
                n.current_path = []
                n.chase_timer = 0.0

        # 2. Relokasi/respawn NPC yang dihadapi agar kembali ke patroli damai & tidak menumpuk di ubin pemain
        enc_npc = getattr(self, "current_encounter_npc", None) or getattr(self, "npc", None)
        if enc_npc:
            enc_npc._spawn()
            enc_npc.chasing = False
            enc_npc.moving = False
            enc_npc.path = []
            enc_npc.current_path = []
        self.current_encounter_npc = None

        # 3. Matikan visualisasi jalur pengejaran di HUD / NavRail
        if hasattr(self, "overlay"):
            self.overlay.set_chasing_visualization(False)

        # 4. Sinkronkan status Knowledge Base & InterNPCManager: insiden telah diselesaikan
        if hasattr(self, "inter_npc_manager") and self.inter_npc_manager:
            self.inter_npc_manager.chaser_assigned = None
            self.inter_npc_manager.guardians_assigned.clear()
            self.inter_npc_manager.latest_percept_event = "Patroli kondusif kembali setelah duel diselesaikan."
            # Retract status HasLootedItem_Player agar tidak terus-menerus memicu pemburu baru
            self.inter_npc_manager.kb.retract("HasLootedItem_Player")

        # 5. Sinkronkan sisa HP dan Potion player secara persistent
        if hasattr(self.battle_system, "state"):
            if self.battle_system.state.player_hp <= 0 or getattr(self.battle_system, "winner", None) == "NPC":
                # Jika Player kalah/tumbang dalam duel, pulihkan HP kembali PENUH (100) saat kembali ke map!
                self.player.persistent_hp = 100
                self.player.persistent_potions = max(2, self.player.persistent_potions)
            else:
                self.player.persistent_hp = max(10, self.battle_system.state.player_hp)
                self.player.persistent_potions = self.battle_system.state.player_potions

        # 6. Pulihkan visualisasi pathfinding A* / UCS (jalur kuning & biru) di peta eksplorasi
        if hasattr(self, "npc") and hasattr(self, "player"):
            self.npc.find_path(self.player.grid)
        if hasattr(self, "overlay"):
            self.overlay.visualization_active = True
            self.overlay.path_reveal = 1.0
            self.overlay.expanded_reveal = 1.0

    def _get_battle_char_positions(self):
        """Menghitung koordinat posisi pusat Player dan NPC tepat di tengah arena battle."""
        w, h = self.screen.get_size()
        is_dock_open = getattr(self.overlay.dock, "is_open", False) if hasattr(self, "overlay") and hasattr(self.overlay, "dock") else False
        panel_w = self.overlay.dock.rect.right if is_dock_open else config.NAV_RAIL_WIDTH
        has_bench = bool(self.current_squad and len(self.current_squad.members) > 1)
        bench_w = 154 if has_bench else 16
        combat_w = w - panel_w - bench_w
        area_x = panel_w + combat_w // 2
        char_y = int(h * 0.28) if h < 750 else int(h * 0.33)
        spacing = 135
        player_arena_x = area_x - spacing
        npc_arena_x = area_x + spacing
        return (player_arena_x, char_y), (npc_arena_x, char_y)

    def _on_battle_action_executed(self, who: str, action: str):
        """Callback saat aksi pertempuran terjadi untuk memicu Battle VFX prosedural."""
        if not hasattr(self, "vfx") or not self.vfx:
            return
        p_pos, n_pos = self._get_battle_char_positions()
        if who == "PLAYER":
            if action == ACTION_ATTACK:
                self.vfx.trigger_attack(p_pos, n_pos, is_heavy=False, recipient="NPC")
            elif action == ACTION_HEAVY:
                self.vfx.trigger_attack(p_pos, n_pos, is_heavy=True, recipient="NPC")
            elif action == ACTION_DEFEND:
                self.vfx.trigger_defend(p_pos)
            elif action == ACTION_POTION:
                self.vfx.trigger_potion(p_pos, heal_val=config.POTION_HEAL)
            elif action == "SECOND WIND!":
                heal_val = getattr(self.battle_system, "last_second_wind_heal", 45)
                self.vfx.trigger_potion(p_pos, heal_val=heal_val)
        else:
            if action == ACTION_ATTACK:
                self.vfx.trigger_attack(n_pos, p_pos, is_heavy=False, recipient="PLAYER")
            elif action == ACTION_HEAVY:
                self.vfx.trigger_attack(n_pos, p_pos, is_heavy=True, recipient="PLAYER")
            elif action == ACTION_DEFEND:
                self.vfx.trigger_defend(n_pos)
            elif action == ACTION_POTION:
                self.vfx.trigger_potion(n_pos, heal_val=config.POTION_HEAL)

    def _draw_battle_arena(self):
        # Tampilkan arena pertempuran di area kerja kanan
        w, h = self.screen.get_size()
        is_dock_open = getattr(self.overlay.dock, "is_open", False) if hasattr(self, "overlay") and hasattr(self.overlay, "dock") else False
        panel_w = self.overlay.dock.rect.right if is_dock_open else config.TOTAL_COLLAPSED_WIDTH
        arena_w = w - panel_w
        area_x = panel_w + arena_w // 2

        # Latar belakang arena hutan lebat soft-focus (statis & cinematic blur)
        self.battle_bg.draw(self.screen, panel_w, arena_w, h)

        # Posisi Player (Kiri) dan NPC (Kanan) di arena (sinkron dengan target VFX)
        (player_arena_x, char_y), (npc_arena_x, _) = self._get_battle_char_positions()

        # Gambar Karakter Berukuran Besar (Full-Body Battle Sprites)
        target_h = 145
        p_img = self.battle_sprites.get("player", self.player.sprite.current_image)
        p_aspect = p_img.get_width() / float(p_img.get_height())
        big_player = pygame.transform.smoothscale(p_img, (int(round(target_h * p_aspect)), target_h))

        # Sprite NPC aktif (menggunakan full-body battle sprite)
        active_member = self.current_squad.get_active_member() if self.current_squad else None
        if active_member and hasattr(active_member, "battle_sprite") and active_member.battle_sprite:
            n_img = active_member.battle_sprite
        elif active_member and active_member.char_type in self.battle_sprites:
            n_img = self.battle_sprites[active_member.char_type]
        elif active_member and active_member.portrait:
            n_img = active_member.portrait
        else:
            n_img = self.npc.sprite.current_image

        n_aspect = n_img.get_width() / float(n_img.get_height())
        big_npc = pygame.transform.smoothscale(n_img, (int(round(target_h * n_aspect)), target_h))

        p_ox, p_oy = self.vfx.get_shake_offset("PLAYER")
        n_ox, n_oy = self.vfx.get_shake_offset("NPC")
        self.screen.blit(big_player, big_player.get_rect(center=(player_arena_x + p_ox, char_y + p_oy)))

        if self.npc_defeat_anim:
            # Sprite NPC yang tumbang berkedip merah dan sedikit transparan
            npc_dead_surf = big_npc.copy()
            red_tint = pygame.Surface(npc_dead_surf.get_size(), SRCALPHA)
            red_tint.fill((255, 30, 30, 130))
            npc_dead_surf.blit(red_tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(npc_dead_surf, npc_dead_surf.get_rect(center=(npc_arena_x + n_ox, char_y + n_oy)))
            self._draw_defeat_badge(npc_arena_x, char_y - 20, self.npc_defeat_anim["npc"])
        elif self.card_summon_anim:
            self._draw_card_summon_animation(npc_arena_x, char_y, target_h)
        else:
            self.screen.blit(big_npc, big_npc.get_rect(center=(npc_arena_x + n_ox, char_y + n_oy)))

        # ================================================================== #
        # Kartu Skuad NPC Cadangan (Deck Portrait Bertumpuk di Kanan Layar)
        # Menampilkan potret NPC antrian bertumpuk (kartu berikutnya di depan)
        # ================================================================== #
        self._draw_battle_queue_deck(w, h)

        # Floating Action Text di atas karakter
        self._draw_action_text(self.battle_system.player_action_text, player_arena_x, char_y - 75)
        if not self.card_summon_anim and not self.npc_defeat_anim:
            self._draw_action_text(self.battle_system.npc_action_text, npc_arena_x, char_y - 75)

        # Status & Bar HP
        st = self.battle_system.state
        player_cd_text = f"  (Heavy CD: {st.player_heavy_cd})" if st.player_heavy_cd > 0 else ""
        npc_cd_text = f"  (Heavy CD: {st.npc_heavy_cd})" if st.npc_heavy_cd > 0 else ""
        npc_display_name = active_member.name if active_member else "NPC (Minimax AI)"
        npc_max_hp = active_member.max_hp if active_member else 100
        display_npc_hp = 0 if self.npc_defeat_anim else st.npc_hp
        hp_bar_y = char_y + (80 if h < 750 else 88)
        self._draw_hp_bar(player_arena_x, hp_bar_y, "Hero Player", st.player_hp, st.player_defending, st.player_potions, (60, 160, 255), player_cd_text, max_hp=100)
        self._draw_hp_bar(npc_arena_x, hp_bar_y, npc_display_name, display_npc_hp, st.npc_defending, st.npc_potions, (255, 90, 80), npc_cd_text, max_hp=npc_max_hp)

        # Banner Notifikasi Rampasan Perang (Spoils of War)
        if hasattr(self, "loot_toast") and self.loot_toast and self.loot_toast["timer"] > 0:
            self._draw_loot_toast(w, h, (player_arena_x + npc_arena_x) // 2)

        # Banner Notifikasi Taktik PDDL Skuad NPC (Materi 08: Automated Planning)
        if hasattr(self.battle_system, "tactical_banner_timer") and self.battle_system.tactical_banner_timer > 0:
            self._draw_tactical_plan_banner(w, h, (player_arena_x + npc_arena_x) // 2)

        font_bubble = self.fonts.get("bubble", self.fonts["sm"])
        font_sm = self.fonts["sm"]
        font_tiny = self.fonts.get("tiny") or pygame.font.Font(None, 13)

        # ------------------------------------------------------------------ #
        # Layout HUD Arena Bawah: RPG Diamond Action Hub (Tengah) & Battle Log
        # ------------------------------------------------------------------ #
        bench_w = 148
        bench_x = w - bench_w - 12
        combat_w = bench_x - 12 - panel_w
        combat_cx = panel_w + combat_w // 2

        # Dimensi Responsif & Proporsional Sesuai Skala Resolusi Layar
        is_compact = (w < 1180 or h < 750)
        card_w = 208 if is_compact else 230
        card_h = 44 if is_compact else 48
        badge_r = 15 if is_compact else 17
        D_X = 22 if is_compact else 32
        D_Y = 48 if is_compact else 54

        hub_cx = combat_cx
        hub_cy = int(h * 0.69) if h >= 750 else int(h * 0.66)

        m_pos = pygame.mouse.get_pos()
        can_act = (
            not st.is_npc_turn
            and not self.battle_system.is_finished
            and not self.card_summon_anim
            and not getattr(self, "loot_modal", None)
            and not self.npc_defeat_anim
        )

        top_rect = pygame.Rect(hub_cx - card_w // 2, hub_cy - D_Y - card_h, card_w, card_h)
        bot_rect = pygame.Rect(hub_cx - card_w // 2, hub_cy + D_Y, card_w, card_h)
        left_rect = pygame.Rect(hub_cx - D_X - card_w, hub_cy - card_h // 2, card_w, card_h)
        right_rect = pygame.Rect(hub_cx + D_X, hub_cy - card_h // 2, card_w, card_h)

        # Hitbox Tombol Responsif
        self.btn_action_attack = top_rect
        self.btn_action_heavy = left_rect
        self.btn_action_defend = right_rect
        self.btn_action_potion = bot_rect
        self.btn_tree_modal = pygame.Rect(0, 0, 0, 0)

        # ------------------------------------------------------------------ #
        # Tombol Keluar / Exit dari Mode Battle (Pojok Kiri Atas Arena Battle)
        # ------------------------------------------------------------------ #
        btn_exit_w = 118
        btn_exit_h = 30
        self.btn_battle_exit = pygame.Rect(panel_w + 14, 14, btn_exit_w, btn_exit_h)
        is_hov_exit = self.btn_battle_exit.collidepoint(m_pos)
        exit_bg = (68, 36, 32) if is_hov_exit else (46, 26, 24)
        exit_bdr = config.COLOR_ACCENT_GOLD if is_hov_exit else (160, 75, 65)
        draw_card(self.screen, self.btn_battle_exit, exit_bg, border_color=exit_bdr, border_radius=6)

        t_exit = font_tiny.render("[ESC] Keluar", True, (255, 235, 220) if is_hov_exit else (225, 195, 185))
        self.screen.blit(t_exit, (self.btn_battle_exit.centerx - t_exit.get_width() // 2, self.btn_battle_exit.centery - t_exit.get_height() // 2))

        is_hov_atk = can_act and self.btn_action_attack.collidepoint(m_pos)
        heavy_ready = can_act and (st.player_heavy_cd == 0)
        is_hov_hvy = heavy_ready and self.btn_action_heavy.collidepoint(m_pos)
        is_hov_def = can_act and self.btn_action_defend.collidepoint(m_pos)
        pot_ready = can_act and (st.player_potions > 0)
        is_hov_pot = pot_ready and self.btn_action_potion.collidepoint(m_pos)

        # ------------------------------------------------------------------ #
        # 0. Center Ornate Diamond Crest & Gold Connector Lines
        # ------------------------------------------------------------------ #
        crest_size = 24 if is_compact else 28
        pygame.draw.line(self.screen, (205, 160, 50), (hub_cx, hub_cy - crest_size), (hub_cx, top_rect.bottom), 3)
        pygame.draw.line(self.screen, (205, 160, 50), (hub_cx, hub_cy + crest_size), (hub_cx, bot_rect.top), 3)
        pygame.draw.line(self.screen, (205, 160, 50), (hub_cx - crest_size, hub_cy), (left_rect.right, hub_cy), 3)
        pygame.draw.line(self.screen, (205, 160, 50), (hub_cx + crest_size, hub_cy), (right_rect.left, hub_cy), 3)

        diamond_pts = [
            (hub_cx, hub_cy - crest_size),
            (hub_cx + crest_size, hub_cy),
            (hub_cx, hub_cy + crest_size),
            (hub_cx - crest_size, hub_cy),
        ]
        pygame.draw.polygon(self.screen, (26, 20, 16, 245), diamond_pts)
        pygame.draw.polygon(self.screen, (215, 170, 55), diamond_pts, 3)
        inner_dia = [
            (hub_cx, hub_cy - crest_size + 4),
            (hub_cx + crest_size - 4, hub_cy),
            (hub_cx, hub_cy + crest_size - 4),
            (hub_cx - crest_size + 4, hub_cy),
        ]
        pygame.draw.polygon(self.screen, (240, 200, 90, 150), inner_dia, 1)
        pygame.draw.circle(self.screen, config.COLOR_ACCENT_GOLD, (hub_cx, hub_cy), 4)

        tx_off = 42 if is_compact else 48
        max_txt_w = card_w - tx_off - 8

        # ------------------------------------------------------------------ #
        # 1. BAGIAN ATAS: [1] Serang Biasa (Shortcut: 1)
        # ------------------------------------------------------------------ #
        bg_atk = (32, 58, 38, 252) if is_hov_atk else ((22, 44, 28, 245) if can_act else (20, 24, 20, 220))
        bdr_atk = config.COLOR_ACCENT_GOLD if is_hov_atk else ((85, 215, 110) if can_act else (70, 90, 75))
        draw_card(self.screen, top_rect, bg_atk, border_color=bdr_atk, border_radius=8)
        bg1_cx, bg1_cy = top_rect.x + (22 if is_compact else 25), top_rect.centery
        pygame.draw.circle(self.screen, (60, 210, 100) if is_hov_atk else ((45, 185, 80) if can_act else (50, 95, 60)), (bg1_cx, bg1_cy), badge_r)
        pygame.draw.circle(self.screen, (220, 255, 230) if can_act else (110, 140, 120), (bg1_cx, bg1_cy), badge_r, 2)
        txt_1 = font_bubble.render("1", True, (255, 255, 255) if can_act else (180, 190, 180))
        self.screen.blit(txt_1, txt_1.get_rect(center=(bg1_cx, bg1_cy)))
        t_atk = font_bubble.render("Serang Biasa", True, (160, 255, 175) if can_act else config.COLOR_TEXT_MUTED)
        d_atk = font_tiny.render("Dmg: 15-25 • No CD", True, (210, 245, 215) if can_act else config.COLOR_TEXT_MUTED)
        self.screen.blit(t_atk, (top_rect.x + tx_off, top_rect.y + (5 if is_compact else 7)))
        self.screen.blit(d_atk, (top_rect.x + tx_off, top_rect.y + (24 if is_compact else 27)))

        # ------------------------------------------------------------------ #
        # 2. BAGIAN KIRI: [2] Serangan Kuat / Heavy Attack (Shortcut: 2)
        # ------------------------------------------------------------------ #
        bg_hvy = (64, 46, 26, 252) if is_hov_hvy else ((46, 32, 18, 245) if heavy_ready else (26, 22, 18, 220))
        bdr_hvy = config.COLOR_ACCENT_GOLD if is_hov_hvy else ((240, 170, 50) if heavy_ready else (100, 85, 70))
        draw_card(self.screen, left_rect, bg_hvy, border_color=bdr_hvy, border_radius=8)
        bg2_cx, bg2_cy = left_rect.x + (22 if is_compact else 25), left_rect.centery
        pygame.draw.circle(self.screen, (255, 165, 35) if is_hov_hvy else ((235, 145, 25) if heavy_ready else (120, 90, 50)), (bg2_cx, bg2_cy), badge_r)
        pygame.draw.circle(self.screen, (255, 245, 195) if heavy_ready else (140, 110, 70), (bg2_cx, bg2_cy), badge_r, 2)
        txt_2 = font_bubble.render("2", True, (255, 255, 255) if heavy_ready else (180, 170, 160))
        self.screen.blit(txt_2, txt_2.get_rect(center=(bg2_cx, bg2_cy)))
        t_hvy = font_bubble.render("Serangan Kuat", True, (255, 230, 110) if heavy_ready else config.COLOR_TEXT_MUTED)
        d_hvy_txt = "Dmg: 30-45 • Siap" if heavy_ready else f"Jeda CD: {st.player_heavy_cd} Giliran"
        d_hvy = font_tiny.render(d_hvy_txt, True, (245, 225, 200) if heavy_ready else config.COLOR_TEXT_MUTED)
        self.screen.blit(t_hvy, (left_rect.x + tx_off, left_rect.y + (5 if is_compact else 7)))
        self.screen.blit(d_hvy, (left_rect.x + tx_off, left_rect.y + (24 if is_compact else 27)))

        # ------------------------------------------------------------------ #
        # 3. BAGIAN KANAN: [3] Bertahan / Defense (Shortcut: 3)
        # ------------------------------------------------------------------ #
        bg_def = (38, 54, 82, 252) if is_hov_def else ((26, 38, 60, 245) if can_act else (20, 22, 28, 220))
        bdr_def = config.COLOR_ACCENT_GOLD if is_hov_def else ((105, 180, 255) if can_act else (70, 85, 105))
        draw_card(self.screen, right_rect, bg_def, border_color=bdr_def, border_radius=8)
        bg3_cx, bg3_cy = right_rect.x + (22 if is_compact else 25), right_rect.centery
        pygame.draw.circle(self.screen, (75, 145, 245) if is_hov_def else ((55, 125, 225) if can_act else (45, 52, 65)), (bg3_cx, bg3_cy), badge_r)
        pygame.draw.circle(self.screen, (225, 240, 255) if can_act else (110, 120, 140), (bg3_cx, bg3_cy), badge_r, 2)
        txt_3 = font_bubble.render("3", True, (255, 255, 255) if can_act else (175, 180, 190))
        self.screen.blit(txt_3, txt_3.get_rect(center=(bg3_cx, bg3_cy)))
        t_def = font_bubble.render("Bertahan", True, (165, 225, 255) if can_act else config.COLOR_TEXT_MUTED)
        d_def = font_tiny.render("-50% Dmg • Counter", True, (205, 225, 250) if can_act else config.COLOR_TEXT_MUTED)
        self.screen.blit(t_def, (right_rect.x + tx_off, right_rect.y + (5 if is_compact else 7)))
        self.screen.blit(d_def, (right_rect.x + tx_off, right_rect.y + (24 if is_compact else 27)))

        # ------------------------------------------------------------------ #
        # 4. BAGIAN BAWAH: [4] Gunakan Ramuan / Potion (Shortcut: 4)
        # ------------------------------------------------------------------ #
        pot_ready = can_act and (st.player_potions > 0)
        bg_pot = (62, 34, 72, 252) if is_hov_pot else ((44, 24, 52, 245) if pot_ready else (24, 20, 28, 220))
        bdr_pot = config.COLOR_ACCENT_GOLD if is_hov_pot else ((210, 110, 250) if pot_ready else (95, 75, 105))
        draw_card(self.screen, bot_rect, bg_pot, border_color=bdr_pot, border_radius=8)
        bg4_cx, bg4_cy = bot_rect.x + (22 if is_compact else 25), bot_rect.centery
        pygame.draw.circle(self.screen, (185, 90, 235) if is_hov_pot else ((165, 75, 215) if pot_ready else (55, 75, 120)), (bg4_cx, bg4_cy), badge_r)
        pygame.draw.circle(self.screen, (245, 220, 255) if pot_ready else (100, 115, 150), (bg4_cx, bg4_cy), badge_r, 2)
        txt_4 = font_bubble.render("4", True, (255, 255, 255) if pot_ready else (175, 185, 205))
        self.screen.blit(txt_4, txt_4.get_rect(center=(bg4_cx, bg4_cy)))
        t_pot = font_bubble.render("Gunakan Ramuan", True, (245, 185, 255) if pot_ready else config.COLOR_TEXT_MUTED)
        d_pot = font_tiny.render(f"x{st.player_potions} Botol (+25 HP)", True, (235, 210, 250) if pot_ready else config.COLOR_TEXT_MUTED)
        self.screen.blit(t_pot, (bot_rect.x + tx_off, bot_rect.y + (5 if is_compact else 7)))
        self.screen.blit(d_pot, (bot_rect.x + tx_off, bot_rect.y + (24 if is_compact else 27)))

        # ------------------------------------------------------------------ #
        # 2. Battle Log Box (Bagian Paling Bawah Arena, Lebar Penuh & Elegan)
        # ------------------------------------------------------------------ #
        log_h = 92 if h < 750 else 112
        log_y = h - log_h - 10
        log_x = panel_w + 16
        log_w = (bench_x - 12) - log_x

        self.battle_log_rect = pygame.Rect(log_x, log_y, log_w, log_h)
        draw_card(self.screen, self.battle_log_rect, (252, 249, 242, 245), border_color=(208, 196, 178), border_radius=8)

        ltitle = font_bubble.render("RIWAYAT PERTEMPURAN", True, config.COLOR_TEXT_PRIMARY)
        self.screen.blit(ltitle, (self.battle_log_rect.x + 12, self.battle_log_rect.y + 7))

        total_logs = len(self.battle_system.battle_logs)
        max_scroll = max(0, total_logs - 4)
        self.battle_log_scroll_offset = max(0, min(max_scroll, self.battle_log_scroll_offset))

        if total_logs > 4:
            end_idx = total_logs - self.battle_log_scroll_offset
            start_idx = max(0, end_idx - 4)
            display_logs = self.battle_system.battle_logs[start_idx:end_idx]
            pos_info = f"[{start_idx + 1}-{end_idx}/{total_logs}]"
        else:
            display_logs = self.battle_system.battle_logs
            pos_info = f"[{total_logs} aksi]" if total_logs > 0 else "[Awal]"

        info_surf = font_tiny.render(pos_info, True, config.COLOR_TEXT_SECONDARY)
        self.screen.blit(info_surf, (self.battle_log_rect.right - info_surf.get_width() - 58, self.battle_log_rect.y + 8))

        # Tombol panah scroll manual (▲ dan ▼)
        btn_w_scroll, btn_h_scroll = 20, 16
        self.btn_log_up = pygame.Rect(self.battle_log_rect.right - 50, self.battle_log_rect.y + 6, btn_w_scroll, btn_h_scroll)
        self.btn_log_down = pygame.Rect(self.battle_log_rect.right - 26, self.battle_log_rect.y + 6, btn_w_scroll, btn_h_scroll)

        up_col = (238, 230, 218) if self.battle_log_scroll_offset < max_scroll else (248, 245, 240)
        down_col = (238, 230, 218) if self.battle_log_scroll_offset > 0 else (248, 245, 240)

        draw_card(self.screen, self.btn_log_up, up_col, border_color=(205, 195, 180), border_radius=3)
        draw_card(self.screen, self.btn_log_down, down_col, border_color=(205, 195, 180), border_radius=3)

        ts_up = font_tiny.render("▲", True, config.COLOR_TEXT_PRIMARY if self.battle_log_scroll_offset < max_scroll else config.COLOR_TEXT_MUTED)
        ts_dn = font_tiny.render("▼", True, config.COLOR_TEXT_PRIMARY if self.battle_log_scroll_offset > 0 else config.COLOR_TEXT_MUTED)
        self.screen.blit(ts_up, (self.btn_log_up.centerx - ts_up.get_width() // 2, self.btn_log_up.centery - ts_up.get_height() // 2))
        self.screen.blit(ts_dn, (self.btn_log_down.centerx - ts_dn.get_width() // 2, self.btn_log_down.centery - ts_dn.get_height() // 2))

        ly = self.battle_log_rect.y + 28
        if display_logs:
            for log_line in display_logs:
                ts = font_sm.render(f"• {log_line}", True, config.COLOR_TEXT_PRIMARY)
                self.screen.blit(ts, (self.battle_log_rect.x + 12, ly))
                ly += 19
        else:
            ts = font_sm.render("• Pertarungan dimulai. Pilih tombol aksi di sebelah kiri untuk bertarung.", True, config.COLOR_TEXT_SECONDARY)
            self.screen.blit(ts, (self.battle_log_rect.x + 12, ly))

        if total_logs > 4 and max_scroll > 0:
            track_y = self.battle_log_rect.y + 26
            track_h = log_h - 32
            thumb_h = max(10, int(track_h * (4.0 / total_logs)))
            norm_pos = 1.0 - (self.battle_log_scroll_offset / float(max_scroll))
            thumb_y = track_y + int(norm_pos * (track_h - thumb_h))
            pygame.draw.rect(self.screen, (230, 222, 210), pygame.Rect(self.battle_log_rect.right - 5, track_y, 3, track_h), border_radius=1)
            pygame.draw.rect(self.screen, config.COLOR_ACCENT_GOLD, pygame.Rect(self.battle_log_rect.right - 5, thumb_y, 3, thumb_h), border_radius=1)

        # ------------------------------------------------------------------ #
        # Visual Effect Manager (Pedang Bergerak, Perisai, Ramuan, Partikel)
        # ------------------------------------------------------------------ #
        self.vfx.draw(self.screen)

        # ------------------------------------------------------------------ #
        # 3. Decision Tree Fullscreen Modal Overlay (Semi-Transparan Pop-up)
        # ------------------------------------------------------------------ #
        if self.overlay.tree_overlay.visible:
            if self.battle_system.last_ai_stats:
                tree_data = self.battle_system.last_ai_stats.get("tree", None)
                if tree_data is None and hasattr(self.battle_system.ai_solver, "last_tree"):
                    tree_data = self.battle_system.ai_solver.last_tree
                if tree_data is not getattr(self, "_last_rendered_battle_tree", None):
                    self._last_rendered_battle_tree = tree_data
                    self.overlay.tree_overlay.set_tree(tree_data)
            self.overlay.tree_overlay.draw(self.screen)

    def _draw_battle_queue_deck(self, w: int, h: int):
        """Merender antrian kartu NPC cadangan secara vertikal di sebelah kanan layar (Trails of Cold Steel style).
        
        Sesuai referensi gambar:
        - Tersusun vertikal dari atas ke bawah
        - Ukuran compact (lebar ~148px)
        - Potret bulat (circular token) dengan ring warna sesuai kelas
        - Nama karakter, role badge, mini bar HP, dan badge status 'NEXT' atau 'KO'
        """
        if not self.current_squad or len(self.current_squad.members) <= 1:
            return

        bench_w = 148
        bench_x = w - bench_w - 12
        curr_y = 16

        # 1. Header Panel Cadangan
        hdr_rect = pygame.Rect(bench_x, curr_y, bench_w, 28)
        pygame.draw.rect(self.screen, (16, 20, 30, 235), hdr_rect, border_radius=6)
        pygame.draw.rect(self.screen, (65, 80, 110), hdr_rect, 1, border_radius=6)

        queue = [m for i, m in enumerate(self.current_squad.members) if i > self.current_squad.active_index]
        q_count = len(queue)
        hdr_title = f"CADANGAN ({q_count})"
        t_surf = self.fonts.get("bubble", self.fonts["sm"]).render(hdr_title, True, (255, 215, 75))
        self.screen.blit(t_surf, t_surf.get_rect(center=hdr_rect.center))
        curr_y += 34

        # 2. Daftar Petarung Cadangan yang Siap Masuk (Next Challengers)
        if queue:
            for depth, mem in enumerate(queue):
                is_next = (depth == 0)
                card_h = 52
                card_rect = pygame.Rect(bench_x, curr_y, bench_w, card_h)

                ctype_lower = mem.char_type.lower()
                if ctype_lower == "warrior":
                    role_color = (235, 145, 45)
                    role_tag = "WAR"
                elif ctype_lower == "ranger":
                    role_color = (52, 205, 105)
                    role_tag = "RNG"
                elif ctype_lower == "mage":
                    role_color = (70, 165, 255)
                    role_tag = "MAG"
                elif ctype_lower == "assassin":
                    role_color = (205, 75, 240)
                    role_tag = "ASN"
                else:
                    role_color = (190, 190, 200)
                    role_tag = "NPC"

                bg_col = (26, 32, 46, 245) if is_next else (18, 22, 32, 225)
                bdr_col = (255, 205, 60) if is_next else (55, 68, 92)
                pygame.draw.rect(self.screen, bg_col, card_rect, border_radius=8)
                pygame.draw.rect(self.screen, bdr_col, card_rect, 2 if is_next else 1, border_radius=8)

                # Potret bulat (Circular Portrait Token)
                p_radius = 17
                p_cx = bench_x + 8 + p_radius
                p_cy = curr_y + card_h // 2

                pygame.draw.circle(self.screen, (12, 15, 22), (p_cx, p_cy), p_radius)
                if mem.portrait:
                    p_img = pygame.transform.smoothscale(mem.portrait, (p_radius * 2 - 2, p_radius * 2 - 2))
                    self.screen.blit(p_img, (p_cx - p_radius + 1, p_cy - p_radius + 1))
                else:
                    # Gambar avatar kucing minimalis
                    ear_l = [(p_cx - 9, p_cy - 4), (p_cx - 4, p_cy - 13), (p_cx, p_cy - 5)]
                    ear_r = [(p_cx, p_cy - 5), (p_cx + 4, p_cy - 13), (p_cx + 9, p_cy - 4)]
                    pygame.draw.polygon(self.screen, role_color, ear_l)
                    pygame.draw.polygon(self.screen, role_color, ear_r)
                    pygame.draw.circle(self.screen, role_color, (p_cx, p_cy + 1), 9)

                pygame.draw.circle(self.screen, (255, 215, 80) if is_next else role_color, (p_cx, p_cy), p_radius, 2)

                info_x = p_cx + p_radius + 8
                name_short = mem.name.split()[0]
                txt_name = self.fonts["sm"].render(name_short, True, (255, 255, 255) if is_next else (205, 212, 225))
                self.screen.blit(txt_name, (info_x, curr_y + 6))

                if is_next:
                    next_badge = (self.fonts.get("tiny") or pygame.font.Font(None, 13)).render("NEXT", True, (20, 15, 5))
                    nb_w = next_badge.get_width() + 6
                    nb_rect = pygame.Rect(bench_x + bench_w - nb_w - 6, curr_y + 6, nb_w, 14)
                    pygame.draw.rect(self.screen, (255, 215, 75), nb_rect, border_radius=3)
                    self.screen.blit(next_badge, (nb_rect.x + 3, nb_rect.y + 1))
                else:
                    role_lbl = (self.fonts.get("tiny") or pygame.font.Font(None, 13)).render(role_tag, True, role_color)
                    self.screen.blit(role_lbl, (bench_x + bench_w - role_lbl.get_width() - 8, curr_y + 7))

                # Mini HP Bar
                bar_x = info_x
                bar_y = curr_y + 25
                bar_w = bench_x + bench_w - bar_x - 8
                bar_h = 5
                pygame.draw.rect(self.screen, (12, 14, 20), (bar_x, bar_y, bar_w, bar_h), border_radius=2)
                cur_hp = getattr(mem, "current_hp", mem.max_hp)
                hp_ratio = max(0.0, min(1.0, cur_hp / float(max(1, mem.max_hp))))
                fill_w = int(bar_w * hp_ratio)
                if fill_w > 0:
                    hp_col = (65, 205, 100) if hp_ratio > 0.4 else (235, 160, 45) if hp_ratio > 0.2 else (235, 65, 65)
                    pygame.draw.rect(self.screen, hp_col, (bar_x, bar_y, fill_w, bar_h), border_radius=2)

                hp_txt = (self.fonts.get("tiny") or pygame.font.Font(None, 13)).render(f"{cur_hp}/{mem.max_hp} HP", True, (160, 172, 192))
                self.screen.blit(hp_txt, (bar_x, curr_y + 34))

                curr_y += card_h + 8
        else:
            empty_rect = pygame.Rect(bench_x, curr_y, bench_w, 46)
            pygame.draw.rect(self.screen, (20, 24, 34, 220), empty_rect, border_radius=8)
            pygame.draw.rect(self.screen, (65, 78, 105), empty_rect, 1, border_radius=8)
            t_last = self.fonts["sm"].render("Duel Terakhir!", True, (255, 215, 80))
            self.screen.blit(t_last, t_last.get_rect(center=empty_rect.center))
            curr_y += 54

        # 3. Status Petarung yang Telah Gugur (KO)
        defeated = [m for i, m in enumerate(self.current_squad.members) if i < self.current_squad.active_index]
        if defeated:
            for mem in defeated:
                d_rect = pygame.Rect(bench_x, curr_y, bench_w, 24)
                pygame.draw.rect(self.screen, (26, 16, 18, 220), d_rect, border_radius=5)
                pygame.draw.rect(self.screen, (100, 40, 45), d_rect, 1, border_radius=5)
                d_name = mem.name.split()[0]
                d_txt = (self.fonts.get("tiny") or pygame.font.Font(None, 13)).render(f"[KO] {d_name}", True, (225, 110, 110))
                self.screen.blit(d_txt, (bench_x + 8, curr_y + 5))
                curr_y += 28

    def _build_npc_card_surface(self, mem, is_front: bool = True, card_w: int = 188, card_h: int = 248, depth: int = 0) -> pygame.Surface:
        """Membuat surface grafis kartu potret NPC dengan visual JRPG elegan."""
        card_surf = pygame.Surface((card_w, card_h), SRCALPHA)

        ctype_lower = mem.char_type.lower()
        if ctype_lower == "warrior":
            theme_border = (225, 140, 45)
            theme_bg = (32, 26, 24)
        elif ctype_lower == "ranger":
            theme_border = (48, 195, 95)
            theme_bg = (20, 30, 24)
        elif ctype_lower == "mage":
            theme_border = (65, 155, 245)
            theme_bg = (20, 26, 38)
        elif ctype_lower == "assassin":
            theme_border = (195, 65, 230)
            theme_bg = (28, 18, 32)
        else:
            theme_border = (180, 180, 190)
            theme_bg = (24, 24, 28)

        if not is_front:
            dim_bg = tuple(max(10, int(c * 0.58)) for c in theme_bg)
            dim_bdr = tuple(max(35, int(c * 0.55)) for c in theme_border)
            card_surf.fill((*dim_bg, 245))
            pygame.draw.rect(card_surf, dim_bdr, (0, 0, card_w, card_h), 1, border_radius=10)

            # Tab nama di pojok kanan atas yang mencuat
            q_num = (self.current_squad.active_index + 1 + depth + 1) if self.current_squad else (depth + 1)
            peek_lbl = self.fonts["sm"].render(f"#{q_num} {mem.name.split()[0]}", True, theme_border)
            peek_rect = pygame.Rect(card_w - peek_lbl.get_width() - 14, 6, peek_lbl.get_width() + 10, 18)
            pygame.draw.rect(card_surf, (18, 22, 32), peek_rect, border_radius=4)
            pygame.draw.rect(card_surf, dim_bdr, peek_rect, 1, border_radius=4)
            card_surf.blit(peek_lbl, (peek_rect.x + 5, peek_rect.y + 2))
        else:
            card_surf.fill((*theme_bg, 252))
            pygame.draw.rect(card_surf, theme_border, (0, 0, card_w, card_h), 2, border_radius=10)
            pygame.draw.rect(card_surf, (255, 255, 255, 45), (2, 2, card_w - 4, card_h - 4), 1, border_radius=8)

            badge_lbl = self.fonts["sm"].render("NEXT CHALLENGER", True, (255, 225, 90))
            badge_rect = pygame.Rect((card_w - badge_lbl.get_width() - 14) // 2, 7, badge_lbl.get_width() + 14, 18)
            pygame.draw.rect(card_surf, (60, 45, 15), badge_rect, border_radius=4)
            pygame.draw.rect(card_surf, (225, 180, 50), badge_rect, 1, border_radius=4)
            card_surf.blit(badge_lbl, (badge_rect.x + 7, badge_rect.y + 2))

        # Bingkai Portrait Tengah
        p_size = 108
        p_x = (card_w - p_size) // 2
        p_y = 29
        p_rect = pygame.Rect(p_x, p_y, p_size, p_size)
        pygame.draw.rect(card_surf, (12, 14, 20), p_rect, border_radius=8)

        if mem.portrait:
            p_img = pygame.transform.smoothscale(mem.portrait, (p_size - 4, p_size - 4))
            if not is_front:
                dark_tint = pygame.Surface((p_size - 4, p_size - 4), SRCALPHA)
                dark_tint.fill((0, 0, 0, 80))
                card_surf.blit(p_img, (p_x + 2, p_y + 2))
                card_surf.blit(dark_tint, (p_x + 2, p_y + 2))
            else:
                card_surf.blit(p_img, (p_x + 2, p_y + 2))
        else:
            ph = self.fonts.get("bubble", self.fonts["sm"]).render("NPC", True, (255, 255, 255))
            card_surf.blit(ph, ph.get_rect(center=p_rect.center))

        p_bdr_col = theme_border if is_front else tuple(max(30, int(c * 0.55)) for c in theme_border)
        pygame.draw.rect(card_surf, p_bdr_col, p_rect, 2 if is_front else 1, border_radius=8)

        # Footer: Nama, Kelas & Profil
        name_font = self.fonts.get("bubble", self.fonts["sm"])
        txt_name = name_font.render(mem.name, True, (255, 255, 255) if is_front else (170, 175, 185))
        card_surf.blit(txt_name, txt_name.get_rect(center=(card_w // 2, p_y + p_size + 14)))

        job_txt = self.fonts["sm"].render(f"{mem.char_type.capitalize()} • {mem.eval_profile}", True, theme_border if is_front else (135, 140, 155))
        card_surf.blit(job_txt, job_txt.get_rect(center=(card_w // 2, p_y + p_size + 30)))

        # Stat Pill: HP & ATK/DEF
        stat_rect = pygame.Rect(10, p_y + p_size + 44, card_w - 20, 24)
        pygame.draw.rect(card_surf, (16, 18, 26, 230), stat_rect, border_radius=6)
        pygame.draw.rect(card_surf, (50, 60, 80) if is_front else (35, 40, 55), stat_rect, 1, border_radius=6)

        stat_str = f"HP {mem.max_hp}  │ +{mem.atk_bonus}A +{mem.def_bonus}D"
        stat_lbl = self.fonts["sm"].render(stat_str, True, (220, 230, 245) if is_front else (145, 150, 160))
        card_surf.blit(stat_lbl, stat_lbl.get_rect(center=stat_rect.center))

        return card_surf

    def _on_npc_tactical_plan(self, warrior, defender, healer, heal_amount: int, plan_result):
        """Callback saat skuad NPC mengeksekusi rencana darurat PDDL (Materi 08)."""
        self.latest_plan_result = plan_result
        if hasattr(self, "planning_overlay") and self.planning_overlay:
            self.planning_overlay.latest_plan_result = plan_result
        if hasattr(self, "overlay") and hasattr(self.overlay, "nav_rail"):
            # Set badge notifikasi di Nav Rail (Tab 5: Planning)
            self.overlay.nav_rail.set_badge(5, active=True, color=config.COLOR_ACCENT_GOLD)
        (player_arena_x, char_y), (npc_arena_x, _) = self._get_battle_char_positions()
        if hasattr(self, "vfx") and self.vfx:
            # Efek perisai di NPC yang baru maju
            self.vfx.trigger_defend((npc_arena_x, char_y))

    def _draw_tactical_plan_banner(self, w: int, h: int, center_x: int):
        """Menggambar banner notifikasi taktis Automated Planning PDDL saat rotasi darurat skuad terjadi."""
        info = getattr(self.battle_system, "tactical_banner_info", None)
        if not info:
            return

        timer = getattr(self.battle_system, "tactical_banner_timer", 0.0)
        alpha = min(255, int(255 * (timer / 0.5))) if timer < 0.5 else 255

        is_dock_open = getattr(self.overlay.dock, "is_open", False) if hasattr(self, "overlay") and hasattr(self.overlay, "dock") else False
        panel_w = self.overlay.dock.rect.right if is_dock_open else config.TOTAL_COLLAPSED_WIDTH
        usable_w = w - panel_w
        banner_w = min(560, usable_w - 40)
        banner_h = 86
        banner_x = center_x - banner_w // 2
        banner_y = 52

        surf = pygame.Surface((banner_w, banner_h), SRCALPHA)

        # Kartu dasar dengan border ganda & warna perkamen
        bg_color = (252, 248, 238, min(245, alpha))
        bd_color = (205, 145, 45, alpha)
        pygame.draw.rect(surf, bg_color, (0, 0, banner_w, banner_h), border_radius=10)
        pygame.draw.rect(surf, bd_color, (0, 0, banner_w, banner_h), 2, border_radius=10)

        # Header Badge
        font_tiny = self.fonts.get("tiny") or pygame.font.Font(None, 13)

        # Badge pill judul taktik
        pill_rect = pygame.Rect(12, 8, banner_w - 24, 24)
        pygame.draw.rect(surf, (244, 232, 210, alpha), pill_rect, border_radius=12)
        pygame.draw.rect(surf, (215, 165, 75, alpha), pill_rect, 1, border_radius=12)

        hdr_txt = font_tiny.render("[TAKTIK PDDL] MATERI 08: AUTOMATED PLANNING", True, (165, 95, 15))
        surf.blit(hdr_txt, (pill_rect.centerx - hdr_txt.get_width() // 2, pill_rect.y + 4))

        # Konten langkah taktis
        w_name = info.get("warrior", "Warrior")
        d_name = info.get("defender", "Defender")
        h_name = info.get("healer", "Healer")
        h_amt = info.get("heal_amount", 35)

        line1 = f"* SwapRetreat: {w_name} mundur -> {d_name} maju pasang [DEFEND]!"
        line2 = f"* HealTeammate: {h_name} pulihkan {w_name} (+{h_amt} HP di cadangan)!"
        line3 = "Tekan [P] untuk melihat pohon rencana PDDL (Forward Progression A*)"

        s_l1 = font_tiny.render(line1, True, (45, 35, 25))
        s_l2 = font_tiny.render(line2, True, (35, 120, 65))
        s_l3 = font_tiny.render(line3, True, (135, 110, 85))

        surf.blit(s_l1, (18, 36))
        surf.blit(s_l2, (18, 52))
        surf.blit(s_l3, (banner_w - s_l3.get_width() - 16, 68))

        self.screen.blit(surf, (banner_x, banner_y))

    def _on_npc_tag_in(self, old_npc, next_npc, heal_amount: int = 45, loot: Optional[Dict[str, Any]] = None):
        """Callback saat NPC aktif tumbang dan NPC berikutnya maju ke duel arena."""
        self.battle_system.is_locked = True
        self.npc_battle_turn_timer = 0.0

        if loot is None and hasattr(self.battle_system, "last_loot"):
            loot = self.battle_system.last_loot

        # Mulai animasi kekalahan NPC terlebih dahulu (terlihat tulisan kalah) sebelum modal rampasan
        self.npc_defeat_anim = {
            "npc": old_npc,
            "next_npc": next_npc,
            "heal_amount": heal_amount,
            "loot": loot,
            "timer": 1.4,
            "duration": 1.4,
            "is_final": False,
        }

    def _start_card_summon_anim(self, old_npc, next_npc):
        """Memulai animasi peluncuran kartu potret dan transformasi ke karakter NPC."""
        w, h = self.screen.get_size()
        bench_w = 232
        bench_x = w - bench_w - 18
        header_y = 20
        curr_y = header_y + 40
        defeated_count = self.current_squad.active_index if self.current_squad else 1
        if defeated_count > 0:
            curr_y += 30

        remaining_queue_len = len(self.current_squad.members) - 1 - self.current_squad.active_index if self.current_squad else 0
        base_x = bench_x + 4
        base_y = curr_y + 14 + (remaining_queue_len * 18)

        card_w, card_h = 188, 248
        start_center = (base_x + card_w // 2, base_y + card_h // 2)

        (_, _), (npc_arena_x, char_y) = self._get_battle_char_positions()
        target_center = (npc_arena_x, char_y)

        ctype_lower = next_npc.char_type.lower()
        if ctype_lower == "warrior":
            theme_color = (235, 145, 45)
            trail_colors = [(255, 180, 50), (255, 235, 120)]
        elif ctype_lower == "ranger":
            theme_color = (48, 205, 95)
            trail_colors = [(50, 220, 100), (180, 255, 160)]
        elif ctype_lower == "mage":
            theme_color = (65, 165, 255)
            trail_colors = [(70, 175, 255), (195, 230, 255)]
        elif ctype_lower == "assassin":
            theme_color = (195, 65, 230)
            trail_colors = [(210, 70, 245), (245, 150, 255)]
        else:
            theme_color = (200, 200, 210)
            trail_colors = [(220, 220, 230), (255, 255, 255)]

        self.card_summon_anim = {
            "old_npc": old_npc,
            "next_npc": next_npc,
            "start_pos": start_center,
            "target_pos": target_center,
            "timer": 0.0,
            "duration": 1.75,
            "fly_duration": 0.75,
            "theme_color": theme_color,
            "trail_colors": trail_colors,
            "particles": [],
            "burst_particles": [],
            "burst_triggered": False,
        }

    def _dismiss_loot_modal(self):
        """Menutup modal rampasan perang dan melanjutkan pemanggilan kartu NPC berikutnya."""
        if not self.loot_modal:
            return
        modal = self.loot_modal
        self.loot_modal = None

        if modal.get("next_npc") and not modal.get("is_final", False):
            self._start_card_summon_anim(modal["old_npc"], modal["next_npc"])
        else:
            self.battle_system.is_locked = False
            if modal.get("is_final", False):
                self._open_battle_result_modal(is_victory=True)

    def _open_battle_result_modal(self, is_victory: bool):
        """Membuka pop-up hasil duel (Menang/Kalah/Kalahkan Boss) dengan tombol Ulangi & Keluar."""
        is_boss = bool(getattr(self, "is_boss_battle", False))
        self.battle_result_modal = {
            "is_victory": is_victory,
            "is_boss": is_boss,
        }
        self.battle_system.is_locked = True

    def _update_card_summon_anim(self, dt: float):
        """Memperbarui fisika partikel dan timeline animasi pemanggilan kartu."""
        if not self.card_summon_anim:
            return

        import random

        anim = self.card_summon_anim
        anim["timer"] += dt
        t = anim["timer"]
        fly_dur = anim["fly_duration"]

        # 1. Update posisi partikel trail
        for p in anim["particles"]:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt
        anim["particles"] = [p for p in anim["particles"] if p["life"] > 0]

        # 2. Spawn partikel trail selama kartu meluncur (Fase 1: 0.0s s/d 0.75s)
        if t < fly_dur:
            prog = min(1.0, t / fly_dur)
            ease = 1.0 - (1.0 - prog) ** 3
            cur_x = anim["start_pos"][0] + (anim["target_pos"][0] - anim["start_pos"][0]) * ease
            arc_y = -math.sin(prog * math.pi) * 38.0
            cur_y = anim["start_pos"][1] + (anim["target_pos"][1] - anim["start_pos"][1]) * ease + arc_y

            for _ in range(3):
                col = random.choice(anim["trail_colors"])
                anim["particles"].append({
                    "x": cur_x + random.uniform(-16, 16),
                    "y": cur_y + random.uniform(-16, 16),
                    "vx": random.uniform(-25, 25),
                    "vy": random.uniform(-25, 25),
                    "life": random.uniform(0.25, 0.45),
                    "max_life": 0.45,
                    "radius": random.uniform(2.5, 5.0),
                    "color": col,
                })

        # 3. Pemicu Burst Transformasi pada t >= 1.15s (Fase 2B)
        if t >= 1.15 and not anim["burst_triggered"]:
            anim["burst_triggered"] = True
            target_x, target_y = anim["target_pos"]
            self.vfx.trigger_hit_shake("NPC", intensity=8.0, duration=0.25)
            # Spawn 36 partikel ledakan memancar 360 derajat
            for i in range(36):
                angle = (i / 36.0) * math.pi * 2 + random.uniform(-0.1, 0.1)
                spd = random.uniform(140.0, 360.0)
                col = random.choice([(255, 255, 255), (255, 240, 160), *anim["trail_colors"]])
                anim["burst_particles"].append({
                    "x": target_x,
                    "y": target_y,
                    "vx": math.cos(angle) * spd,
                    "vy": math.sin(angle) * spd,
                    "life": random.uniform(0.35, 0.65),
                    "max_life": 0.65,
                    "radius": random.uniform(3.0, 6.5),
                    "color": col,
                })

        # 4. Update partikel burst
        for bp in anim["burst_particles"]:
            bp["x"] += bp["vx"] * dt
            bp["y"] += bp["vy"] * dt
            bp["vx"] *= max(0.0, 1.0 - 2.8 * dt)
            bp["vy"] *= max(0.0, 1.0 - 2.8 * dt)
            bp["life"] -= dt
        anim["burst_particles"] = [bp for bp in anim["burst_particles"] if bp["life"] > 0]

        # 5. Selesai animasi (t >= duration)
        if t >= anim["duration"]:
            self.card_summon_anim = None
            self.battle_system.is_locked = False

    def _draw_card_summon_animation(self, npc_arena_x: int, char_y: int, target_h: int):
        """Merender seluruh rangkaian animasi meluncurnya kartu NPC dan transformasi ke karakter."""
        if not self.card_summon_anim:
            return

        anim = self.card_summon_anim
        t = anim["timer"]
        next_npc = anim["next_npc"]
        old_npc = anim.get("old_npc")
        fly_dur = anim["fly_duration"]
        theme_col = anim["theme_color"]

        card_w, card_h = 188, 248

        # --- A. Efek Karakter Lama Memudar (Fade Out) ---
        if old_npc and t < 0.40:
            old_fade = max(0, int(255 * (1.0 - (t / 0.40))))
            old_img = old_npc.battle_sprite or old_npc.portrait or self.npc.sprite.current_image
            asp = old_img.get_width() / float(old_img.get_height())
            old_scaled = pygame.transform.smoothscale(old_img, (int(round(target_h * asp)), target_h))
            f_surf = old_scaled.copy()
            f_surf.fill((160, 40, 40, 120), special_flags=pygame.BLEND_RGBA_MULT)
            f_surf.set_alpha(old_fade)
            self.screen.blit(f_surf, f_surf.get_rect(center=(npc_arena_x, char_y)))

        # --- B. Partikel Jejak & Trail ---
        for p in anim["particles"]:
            alpha = max(0, min(255, int(255 * (p["life"] / p["max_life"]))))
            rad = max(1, int(p["radius"]))
            p_surf = pygame.Surface((rad * 2 + 4, rad * 2 + 4), SRCALPHA)
            pygame.draw.circle(p_surf, (*p["color"], alpha), (rad + 2, rad + 2), rad)
            self.screen.blit(p_surf, (int(p["x"] - rad - 2), int(p["y"] - rad - 2)))

        # --- C. Lingkaran Sihir Pemanggilan (Magic Summoning Circle di Tanah) ---
        if t >= 0.50:
            circle_prog = min(1.0, (t - 0.50) / 0.35)
            circle_fade = 1.0 if t < 1.45 else max(0.0, 1.0 - (t - 1.45) / 0.30)
            circle_alpha = int(210 * circle_prog * circle_fade)

            if circle_alpha > 0:
                cw, ch = 190, 64
                c_surf = pygame.Surface((cw, ch), SRCALPHA)
                pygame.draw.ellipse(c_surf, (*theme_col, circle_alpha), (4, 4, cw - 8, ch - 8), 2)
                pygame.draw.ellipse(c_surf, (255, 255, 255, int(circle_alpha * 0.8)), (24, 12, cw - 48, ch - 24), 1)
                rot_ang = t * 3.5
                pts = []
                for i in range(6):
                    ang = rot_ang + i * (math.pi / 3.0)
                    rx = (cw // 2) + math.cos(ang) * (cw // 2 - 28)
                    ry = (ch // 2) + math.sin(ang) * (ch // 2 - 14)
                    pts.append((int(rx), int(ry)))
                if len(pts) >= 6:
                    pygame.draw.polygon(c_surf, (*theme_col, int(circle_alpha * 0.45)), [pts[0], pts[2], pts[4]], 1)
                    pygame.draw.polygon(c_surf, (*theme_col, int(circle_alpha * 0.45)), [pts[1], pts[3], pts[5]], 1)

                self.screen.blit(c_surf, c_surf.get_rect(center=(npc_arena_x, char_y + 68)))

        # --- D. FASE 1: Kartu Meluncur Menuju Tengah (0.0s s/d 0.75s) ---
        if t < fly_dur:
            prog = min(1.0, t / fly_dur)
            ease = 1.0 - (1.0 - prog) ** 3
            cur_x = anim["start_pos"][0] + (anim["target_pos"][0] - anim["start_pos"][0]) * ease
            arc_y = -math.sin(prog * math.pi) * 38.0
            cur_y = anim["start_pos"][1] + (anim["target_pos"][1] - anim["start_pos"][1]) * ease + arc_y

            scale = 1.0 + 0.12 * math.sin(prog * math.pi)
            angle = -math.sin(prog * math.pi) * 8.0

            raw_card = self._build_npc_card_surface(next_npc, is_front=True, card_w=card_w, card_h=card_h)
            sc_w = int(card_w * scale)
            sc_h = int(card_h * scale)
            card_scaled = pygame.transform.smoothscale(raw_card, (sc_w, sc_h))

            shadow = pygame.Surface((sc_w, sc_h), SRCALPHA)
            shadow.fill((0, 0, 0, 110))
            if abs(angle) > 0.5:
                card_rot = pygame.transform.rotate(card_scaled, angle)
                shadow_rot = pygame.transform.rotate(shadow, angle)
                self.screen.blit(shadow_rot, shadow_rot.get_rect(center=(int(cur_x + 8), int(cur_y + 12))))
                self.screen.blit(card_rot, card_rot.get_rect(center=(int(cur_x), int(cur_y))))
            else:
                self.screen.blit(shadow, shadow.get_rect(center=(int(cur_x + 8), int(cur_y + 12))))
                self.screen.blit(card_scaled, card_scaled.get_rect(center=(int(cur_x), int(cur_y))))

        # --- E. FASE 2: Transformasi dari Kartu ke Karakter NPC (0.75s s/d 1.75s) ---
        else:
            n_ox, n_oy = self.vfx.get_shake_offset("NPC")
            center_x = npc_arena_x + n_ox
            center_y = char_y + n_oy

            # Sub-fase 2A: Kartu Melayang, Menyerap Energi, dan Flip 3D (0.75s s/d 1.15s)
            if t < 1.15:
                flip_prog = (t - 0.75) / 0.40
                cos_val = max(0.01, math.cos(flip_prog * (math.pi / 2.0)))
                raw_card = self._build_npc_card_surface(next_npc, is_front=True, card_w=card_w, card_h=card_h)
                cur_cw = max(2, int(card_w * 1.12 * cos_val))
                cur_ch = int(card_h * 1.12)
                card_scaled = pygame.transform.smoothscale(raw_card, (cur_cw, cur_ch))

                glow_overlay = pygame.Surface((cur_cw, cur_ch), SRCALPHA)
                glow_alpha = int(220 * flip_prog)
                glow_overlay.fill((255, 255, 255, glow_alpha))
                card_scaled.blit(glow_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

                self.screen.blit(card_scaled, card_scaled.get_rect(center=(center_x, center_y)))

            # Sub-fase 2B & 2C: Flash Ledakan & Karakter Terbentuk (1.15s s/d 1.75s)
            else:
                char_prog = min(1.0, (t - 1.15) / 0.60)
                bounce = 1.0 + 0.32 * math.exp(-char_prog * 5.0) * math.cos(char_prog * math.pi * 2.5)

                n_img = next_npc.battle_sprite
                if not n_img and next_npc.char_type in self.battle_sprites:
                    n_img = self.battle_sprites[next_npc.char_type]
                elif not n_img:
                    n_img = next_npc.portrait or self.npc.sprite.current_image

                asp = n_img.get_width() / float(n_img.get_height())
                final_h = int(target_h * bounce)
                final_w = int(round(final_h * asp))
                char_scaled = pygame.transform.smoothscale(n_img, (max(1, final_w), max(1, final_h)))

                if char_prog < 0.70:
                    aura_alpha = int(180 * (1.0 - char_prog / 0.70))
                    aura_surf = char_scaled.copy()
                    aura_surf.fill((*theme_col, aura_alpha), special_flags=pygame.BLEND_RGBA_MULT)
                    self.screen.blit(aura_surf, aura_surf.get_rect(center=(center_x, center_y)))

                self.screen.blit(char_scaled, char_scaled.get_rect(center=(center_x, center_y)))

                flash_dur = 0.20
                if t < 1.15 + flash_dur:
                    flash_prog = (t - 1.15) / flash_dur
                    flash_alpha = int(240 * (1.0 - flash_prog))
                    beam_w = int(90 * (1.0 - flash_prog))
                    if beam_w > 0:
                        beam_surf = pygame.Surface((beam_w, 280), SRCALPHA)
                        beam_surf.fill((255, 255, 255, flash_alpha))
                        self.screen.blit(beam_surf, beam_surf.get_rect(center=(center_x, center_y)))

                banner_font = self.fonts.get("bubble", self.fonts["sm"])
                badge_txt = banner_font.render(f"TAG-IN: {next_npc.name.upper()}", True, (255, 235, 120))
                b_rect = badge_txt.get_rect(center=(center_x, center_y - 88))
                b_bg = pygame.Rect(b_rect.x - 8, b_rect.y - 4, b_rect.width + 16, b_rect.height + 8)
                pygame.draw.rect(self.screen, (20, 24, 34, 230), b_bg, border_radius=6)
                pygame.draw.rect(self.screen, theme_col, b_bg, 2, border_radius=6)
                self.screen.blit(badge_txt, b_rect)

        # --- F. Partikel Burst Transformasi (360 derajat) ---
        for bp in anim["burst_particles"]:
            alpha = max(0, min(255, int(255 * (bp["life"] / bp["max_life"]))))
            rad = max(1, int(bp["radius"]))
            bp_surf = pygame.Surface((rad * 2 + 4, rad * 2 + 4), SRCALPHA)
            pygame.draw.circle(bp_surf, (*bp["color"], alpha), (rad + 2, rad + 2), rad)
            self.screen.blit(bp_surf, (int(bp["x"] - rad - 2), int(bp["y"] - rad - 2)))

    def _draw_action_text(self, action_data, cx, cy):
        """Gambar teks aksi melayang di atas karakter (floating + fade effect)."""
        if not action_data:
            return

        text = action_data["text"]
        timer = action_data["timer"]
        color = action_data["color"]
        duration = self.battle_system.ACTION_TEXT_DURATION

        # Tahan teks agar terbaca, lalu lakukan fade-out hanya di bagian akhir.
        elapsed = duration - timer
        hold_duration = 1.5
        fade_progress = max(0.0, min(1.0, (elapsed - hold_duration) / (duration - hold_duration)))
        float_offset = min(elapsed, hold_duration) / hold_duration * 8 + fade_progress * 12
        alpha = max(0, min(255, int(255 * (1.0 - fade_progress))))

        # Buat surface teks
        font = self.fonts.get("bubble", self.fonts["sm"])
        text_surf = font.render(text, True, color)

        # Buat surface dengan alpha
        combined = pygame.Surface((text_surf.get_width() + 16, text_surf.get_height() + 8), SRCALPHA)

        # Latar belakang gelap semi-transparan
        bg_alpha = max(0, int(180 * (1.0 - fade_progress)))
        combined.fill((15, 18, 25, bg_alpha))

        # Border berwarna
        border_col = (*color[:3], alpha)
        pygame.draw.rect(combined, border_col, combined.get_rect(), 2, border_radius=6)

        # Teks di tengah
        text_alpha_surf = text_surf.copy()
        text_alpha_surf.set_alpha(alpha)
        combined.blit(text_alpha_surf, (8, 4))

        # Posisi final (naik dari posisi awal)
        final_y = cy - float_offset
        rect = combined.get_rect(center=(cx, int(final_y)))
        self.screen.blit(combined, rect)

    def _draw_hp_bar(self, cx, cy, name, hp, is_defending, potions, col_theme, cd_text="", max_hp=100):
        bar_w = 170
        bar_h = 16
        rect_bg = pygame.Rect(cx - bar_w // 2, cy, bar_w, bar_h)

        # Label Nama & Defend Status dengan badge kontras tinggi
        def_str = " [DEFENDING]" if is_defending else ""
        name_font = self.fonts.get("bubble", self.fonts["sm"])
        name_color = (255, 230, 100) if is_defending else (255, 255, 255)
        name_surf = name_font.render(f"{name}{def_str}", True, name_color)
        name_rect = name_surf.get_rect(midbottom=(cx, cy - 6))
        pill_rect = name_rect.inflate(14, 6)
        pill_surf = pygame.Surface(pill_rect.size, SRCALPHA)
        pill_surf.fill((16, 20, 30, 200))
        pygame.draw.rect(pill_surf, (55, 65, 85, 220), pill_surf.get_rect(), 1, border_radius=4)
        self.screen.blit(pill_surf, pill_rect.topleft)
        self.screen.blit(name_surf, name_rect.topleft)

        # Background bar
        pygame.draw.rect(self.screen, (35, 38, 48), rect_bg, border_radius=4)

        # Fill bar
        fill_w = int((hp / float(max(1, max_hp))) * bar_w)
        if fill_w > 0:
            fill_rect = pygame.Rect(cx - bar_w // 2, cy, fill_w, bar_h)
            # Warna adaptif jika sekarat
            fill_col = col_theme if hp > int(0.3 * max_hp) else (240, 60, 60)
            pygame.draw.rect(self.screen, fill_col, fill_rect, border_radius=4)

        pygame.draw.rect(self.screen, (100, 110, 130), rect_bg, 1, border_radius=4)

        # Teks Angka HP + Cooldown info dengan badge kontras tinggi
        hp_text = f"{hp} / {max_hp} HP  │  Pot: {potions}{cd_text}"
        ts_hp = self.fonts["sm"].render(hp_text, True, (240, 245, 255))
        hp_rect = ts_hp.get_rect(midtop=(cx, cy + bar_h + 5))
        hp_pill = hp_rect.inflate(14, 6)
        hp_pill_surf = pygame.Surface(hp_pill.size, SRCALPHA)
        hp_pill_surf.fill((16, 20, 30, 200))
        pygame.draw.rect(hp_pill_surf, (55, 65, 85, 220), hp_pill_surf.get_rect(), 1, border_radius=4)
        self.screen.blit(hp_pill_surf, hp_pill.topleft)
        self.screen.blit(ts_hp, hp_rect.topleft)

    def _draw_loot_toast(self, w: int, h: int, center_x: int):
        """Merender banner pop-up Rampasan Perang (Spoils of War) di atas duel arena dengan tema Cozy Warm Parchment."""
        if not self.loot_toast or self.loot_toast["timer"] <= 0:
            return

        toast = self.loot_toast
        loot = toast["loot"]
        timer = toast["timer"]
        max_timer = toast["max_timer"]

        # Efek Fade in / Fade out
        if timer > max_timer - 0.25:
            alpha = int(255 * (max_timer - timer) / 0.25)
        elif timer < 0.4:
            alpha = int(255 * (timer / 0.4))
        else:
            alpha = 255
        alpha = max(0, min(255, alpha))

        bw, bh = 480, 56
        by = 28
        banner_rect = pygame.Rect(center_x - bw // 2, by, bw, bh)

        # Drop shadow
        shadow_surf = pygame.Surface((bw, bh), SRCALPHA)
        pygame.draw.rect(shadow_surf, (45, 35, 25, int(35 * (alpha / 255.0))), (0, 0, bw, bh), border_radius=10)
        self.screen.blit(shadow_surf, (banner_rect.x + 2, banner_rect.y + 3))

        banner_surf = pygame.Surface((bw, bh), SRCALPHA)
        bg_alpha = int(246 * (alpha / 255.0))
        banner_surf.fill((255, 253, 248, bg_alpha))

        border_col = (212, 186, 150)
        border_col_alpha = (*border_col[:3], alpha)
        pygame.draw.rect(banner_surf, border_col_alpha, pygame.Rect(0, 0, bw, bh), width=2, border_radius=10)
        pygame.draw.rect(banner_surf, (255, 255, 255, min(200, alpha)), pygame.Rect(1, 1, bw - 2, bh - 2), width=1, border_radius=9)

        accent_col = loot.get("color", (205, 135, 25))
        accent_col_alpha = (*accent_col[:3], alpha)
        glow_bar = pygame.Rect(5, 5, 5, bh - 10)
        pygame.draw.rect(banner_surf, accent_col_alpha, glow_bar, border_radius=3)

        font_bubble = self.fonts.get("bubble", self.fonts["sm"])
        font_sm = self.fonts["sm"]

        title_str = "RAMPASAN PERANG DIPEROLEH!"
        title_txt = font_bubble.render(title_str, True, (165, 80, 15))
        if alpha < 255:
            title_txt.set_alpha(alpha)
        banner_surf.blit(title_txt, (20, 6))

        desc_str = f"Merebut: {loot['name']} ({loot['desc']})"
        desc_txt = font_sm.render(desc_str, True, (65, 48, 36))
        if alpha < 255:
            desc_txt.set_alpha(alpha)
        banner_surf.blit(desc_txt, (20, 31))

        self.screen.blit(banner_surf, banner_rect)

    def _draw_defeat_badge(self, cx: int, cy: int, npc_obj):
        """Merender badge dramatis 'KALAH!' tepat di atas NPC yang baru saja tumbang."""
        font_huge = self.fonts.get("huge", self.fonts["title"])
        font_bubble = self.fonts.get("bubble", self.fonts["sm"])

        bw, bh = 290, 68
        b_rect = pygame.Rect(cx - bw // 2, cy - bh // 2, bw, bh)

        badge_surf = pygame.Surface((bw, bh), SRCALPHA)
        badge_surf.fill((36, 10, 14, 245))
        border_col = (255, 55, 45)
        pygame.draw.rect(badge_surf, border_col, (0, 0, bw, bh), width=2, border_radius=10)
        pygame.draw.rect(badge_surf, (255, 210, 75), (2, 2, bw - 4, bh - 4), width=1, border_radius=8)

        t_main = font_huge.render("KALAH / TUMBANG!", True, (255, 230, 80))
        badge_surf.blit(t_main, t_main.get_rect(center=(bw // 2, 24)))

        name_str = npc_obj.name if hasattr(npc_obj, "name") else "Musuh"
        t_sub = font_bubble.render(f"{name_str} Telah Gugur!", True, (255, 220, 220))
        badge_surf.blit(t_sub, t_sub.get_rect(center=(bw // 2, 50)))

        self.screen.blit(badge_surf, b_rect)

    def _draw_loot_modal(self):
        """Merender modal dialog rampasan perang di tengah arena battle dengan tema Cozy Warm Parchment."""
        if not self.loot_modal:
            return

        from ..ui.components import fit_text_to_width

        modal = self.loot_modal
        loot = modal["loot"]
        old_npc = modal.get("old_npc")
        is_final = modal.get("is_final", False)

        w, h = self.screen.get_size()
        is_dock_open = getattr(self.overlay.dock, "is_open", False) if hasattr(self, "overlay") and hasattr(self.overlay, "dock") else False
        panel_w = self.overlay.dock.rect.right if is_dock_open else config.NAV_RAIL_WIDTH
        has_bench = bool(self.current_squad and len(self.current_squad.members) > 1)
        bench_w = 154 if has_bench else 16
        combat_w = w - panel_w - bench_w
        cx = panel_w + combat_w // 2
        cy = h // 2

        # 1. Background Overlay (Warm Parchment Vignette Backdrop)
        dim_surf = pygame.Surface((w, h), SRCALPHA)
        dim_surf.fill((22, 16, 12, 165))
        self.screen.blit(dim_surf, (0, 0))

        # 2. Dimensi & Posisi Modal Card di Tengah Arena Battle
        mw, mh = 560, 416
        mx, my = cx - mw // 2, cy - mh // 2
        modal_rect = pygame.Rect(mx, my, mw, mh)

        # Shadow
        shadow_surf = pygame.Surface((mw, mh), SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 45), (0, 0, mw, mh), border_radius=14)
        self.screen.blit(shadow_surf, (mx + 3, my + 4))

        # Warm Parchment Card Body
        card_surf = pygame.Surface((mw, mh), SRCALPHA)
        card_surf.fill((252, 248, 240, 253))

        theme_col = loot.get("color", config.COLOR_ACCENT_GOLD)
        pygame.draw.rect(card_surf, (168, 140, 102), (0, 0, mw, mh), 2, border_radius=14)
        pygame.draw.rect(card_surf, (235, 222, 204), (2, 2, mw - 4, mh - 4), 1, border_radius=12)

        font_title = self.fonts.get("title", self.fonts.get("bubble"))
        font_bubble = self.fonts.get("bubble", self.fonts["sm"])
        font_sm = self.fonts["sm"]

        # 3. Header Badge: RAMPASAN PERANG DIPEROLEH!
        badge_w, badge_h = 360, 32
        badge_rect = pygame.Rect((mw - badge_w) // 2, 16, badge_w, badge_h)
        pygame.draw.rect(card_surf, (244, 234, 216), badge_rect, border_radius=6)
        pygame.draw.rect(card_surf, (195, 145, 55), badge_rect, 1, border_radius=6)

        hdr_txt = font_bubble.render("RAMPASAN PERANG DIPEROLEH!", True, (165, 110, 20))
        card_surf.blit(hdr_txt, hdr_txt.get_rect(center=badge_rect.center))

        # 4. Sub-teks Info Lawan Gugur
        if old_npc:
            sub_str = f"Bolu berhasil menumbangkan {old_npc.name}!"
        else:
            sub_str = "Kemenangan gemilang di medan pertempuran!"
        sub_fit = fit_text_to_width(font_sm, sub_str, mw - 40)
        sub_txt = font_sm.render(sub_fit, True, (115, 95, 80))
        card_surf.blit(sub_txt, sub_txt.get_rect(center=(mw // 2, 60)))

        # 5. Bingkai Showcase Item (Icon Frame di Tengah)
        frame_sz = 96
        frame_rect = pygame.Rect((mw - frame_sz) // 2, 78, frame_sz, frame_sz)
        pygame.draw.rect(card_surf, (245, 240, 230), frame_rect, border_radius=12)
        pygame.draw.rect(card_surf, (205, 185, 160), frame_rect, 2, border_radius=12)

        # Gambar Item Besar
        img_key = loot.get("image_key", "item_sword")
        item_img = None
        if hasattr(self, "item_images_large") and img_key in self.item_images_large:
            item_img = self.item_images_large[img_key]
        elif img_key in self.item_images:
            item_img = pygame.transform.smoothscale(self.item_images[img_key], (76, 76))

        if item_img:
            card_surf.blit(item_img, item_img.get_rect(center=frame_rect.center))

        # 6. Nama Item Rampasan
        item_name = loot.get("name", "Artefak Misterius")
        name_fit = fit_text_to_width(font_title, item_name, mw - 40)
        name_txt = font_title.render(name_fit, True, (42, 30, 20))
        card_surf.blit(name_txt, name_txt.get_rect(center=(mw // 2, 196)))

        # 7. Badge Stat Boost (+ATK / +DEF / Pulihkan HP)
        stat_w, stat_h = 360, 32
        stat_rect = pygame.Rect((mw - stat_w) // 2, 222, stat_w, stat_h)
        pygame.draw.rect(card_surf, (235, 248, 238), stat_rect, border_radius=6)
        pygame.draw.rect(card_surf, (135, 205, 160), stat_rect, 1, border_radius=6)

        stat_str = f"BONUS STAT: {loot.get('stat_text', '+Stat')}"
        stat_fit = fit_text_to_width(font_bubble, stat_str, stat_w - 20)
        stat_txt = font_bubble.render(stat_fit, True, (30, 130, 65))
        card_surf.blit(stat_txt, stat_txt.get_rect(center=stat_rect.center))

        # 8. Deskripsi Efek Item (Bebas Overflow & Rapi dengan Multi-line Wrapping)
        desc_str = loot.get("desc", "")
        words = desc_str.split(" ")
        desc_lines = []
        cur_l = []
        max_desc_w = mw - 60
        for w_tok in words:
            cand = " ".join(cur_l + [w_tok])
            if font_sm.size(cand)[0] <= max_desc_w:
                cur_l.append(w_tok)
            else:
                if cur_l:
                    desc_lines.append(" ".join(cur_l))
                cur_l = [w_tok]
        if cur_l:
            desc_lines.append(" ".join(cur_l))

        line_h = 20
        total_desc_h = len(desc_lines) * line_h
        desc_center_y = 282
        start_y = desc_center_y - (total_desc_h // 2) + 10
        for i, line_text in enumerate(desc_lines):
            l_fit = fit_text_to_width(font_sm, line_text, max_desc_w)
            l_txt = font_sm.render(l_fit, True, (65, 52, 42))
            card_surf.blit(l_txt, l_txt.get_rect(center=(mw // 2, start_y + i * line_h)))

        # 9. Tombol Interaktif / Petunjuk Tekan ENTER
        btn_w, btn_h = 480, 38
        btn_rect = pygame.Rect((mw - btn_w) // 2, mh - 54, btn_w, btn_h)

        btn_bg = (42, 138, 76) if not is_final else (38, 110, 185)
        btn_bdr = (115, 210, 150) if not is_final else (120, 190, 250)
        pygame.draw.rect(card_surf, btn_bg, btn_rect, border_radius=8)
        pygame.draw.rect(card_surf, btn_bdr, btn_rect, 1, border_radius=8)

        prompt_str = "Tekan [ENTER] / [SPASI] untuk Lawan Berikutnya" if not is_final else "Tekan [ENTER] / [SPASI] untuk Selesaikan Duel"
        p_fit = fit_text_to_width(font_bubble, prompt_str, btn_w - 20)
        p_txt = font_bubble.render(p_fit, True, (255, 255, 255))
        card_surf.blit(p_txt, p_txt.get_rect(center=btn_rect.center))

        # Blit Modal Card ke Layar
        self.screen.blit(card_surf, modal_rect)

    def _draw_battle_result_modal(self):
        """Merender pop-up hasil duel (Menang, Kalah, & Ucapan Selamat Boss) bergaya Cozy Warm Parchment."""
        modal = getattr(self, "battle_result_modal", None)
        if not modal:
            return
        from ..ui.components import fit_text_to_width, draw_badge_pill

        is_victory = modal.get("is_victory", False)
        is_boss = modal.get("is_boss", False)
        w, h = self.screen.get_size()
        is_dock_open = getattr(self.overlay.dock, "is_open", False) if hasattr(self, "overlay") and hasattr(self.overlay, "dock") else False
        panel_w = self.overlay.dock.rect.right if is_dock_open else config.NAV_RAIL_WIDTH
        cx = panel_w + (w - panel_w) // 2
        cy = h // 2

        dim_surf = pygame.Surface((w, h), SRCALPHA)
        dim_surf.fill((12, 10, 16, 175))
        self.screen.blit(dim_surf, (0, 0))

        mw, mh = min(500, max(360, w - panel_w - 40)), 256
        modal_rect = pygame.Rect(cx - mw // 2, cy - mh // 2, mw, mh)

        # Shadow + Card
        sh_surf = pygame.Surface((mw + 10, mh + 10), SRCALPHA)
        pygame.draw.rect(sh_surf, (0, 0, 0, 95), sh_surf.get_rect(), border_radius=16)
        self.screen.blit(sh_surf, (modal_rect.x - 2, modal_rect.y + 4))

        if is_victory and is_boss:
            bdr_col = (212, 160, 42)
            hdr_bg = (254, 244, 214)
            badge_txt = "BOSS DIKALAHKAN!"
            badge_bg, badge_fg = (252, 236, 190), (165, 95, 12)
            title_str = "SELAMAT! PENJAGA MENARA TAKLUK!"
            sub_str = "Ucapan Selamat untuk Bolu & Para Penjaga Skuad:"
            body_lines = [
                "Pertarungan melawan Kage the Shadow Lord berakhir gemilang!",
                "Terima kasih telah menguji strategi AI & menaklukkan Menara Kuno.",
            ]
        elif is_victory:
            bdr_col = (55, 165, 95)
            hdr_bg = (232, 248, 236)
            badge_txt = "KEMENANGAN"
            badge_bg, badge_fg = (214, 242, 222), (32, 125, 62)
            title_str = "DUEL DIMENANGKAN!"
            sub_str = "Bolu berhasil mengalahkan seluruh skuad lawan."
            body_lines = [
                "Kamu bisa mengulang duel ini untuk menguji strategi AI lagi,",
                "atau kembali ke peta untuk melanjutkan petualangan.",
            ]
        else:
            bdr_col = (195, 68, 68)
            hdr_bg = (254, 236, 236)
            badge_txt = "DEFEAT"
            badge_bg, badge_fg = (248, 214, 214), (168, 42, 42)
            title_str = "BOLU TUMBANG DI ARENA!"
            sub_str = "HP habis — strategi AI lawan berhasil mengungguli giliran ini."
            body_lines = [
                "Pilih 'Ulangi Duel' untuk mencoba lagi dengan formasi sekarang,",
                "atau 'Keluar Battle' untuk memulihkan diri & mencari buff di peta.",
            ]

        pygame.draw.rect(self.screen, (255, 253, 248), modal_rect, border_radius=14)
        hdr_rect = pygame.Rect(modal_rect.x, modal_rect.y, mw, 52)
        pygame.draw.rect(self.screen, hdr_bg, hdr_rect, border_top_left_radius=14, border_top_right_radius=14)
        pygame.draw.line(self.screen, bdr_col, (modal_rect.x, hdr_rect.bottom), (modal_rect.right, hdr_rect.bottom), 1)
        pygame.draw.rect(self.screen, bdr_col, modal_rect, 2, border_radius=14)

        font_title = self.fonts.get("title", self.fonts["sm"])
        font_bubble = self.fonts.get("bubble", self.fonts["sm"])
        font_sm = self.fonts["sm"]
        font_tiny = self.fonts.get("tiny", self.fonts["sm"])

        bw = font_tiny.size(badge_txt)[0] + 18
        draw_badge_pill(
            self.screen,
            pygame.Rect(modal_rect.centerx - bw // 2, modal_rect.y + 8, bw, 18),
            badge_txt, badge_bg, badge_fg, font_tiny, border_color=bdr_col,
        )
        t_fit = fit_text_to_width(font_title, title_str, mw - 28)
        t_surf = font_title.render(t_fit, True, (45, 34, 24))
        self.screen.blit(t_surf, t_surf.get_rect(center=(modal_rect.centerx, modal_rect.y + 37)))

        s_fit = fit_text_to_width(font_sm, sub_str, mw - 32)
        s_surf = font_sm.render(s_fit, True, badge_fg)
        self.screen.blit(s_surf, s_surf.get_rect(center=(modal_rect.centerx, modal_rect.y + 82)))

        by = modal_rect.y + 114
        for ln in body_lines:
            l_fit = fit_text_to_width(font_tiny, ln, mw - 36)
            l_surf = font_tiny.render(l_fit, True, (90, 76, 64))
            self.screen.blit(l_surf, l_surf.get_rect(center=(modal_rect.centerx, by)))
            by += 22

        # Tombol Restart Battle & Keluar Battle
        btn_gap = 14
        btn_w = (mw - 48 - btn_gap) // 2
        btn_h = 40
        btn_y = modal_rect.bottom - btn_h - 18
        self.btn_result_restart = pygame.Rect(modal_rect.x + 24, btn_y, btn_w, btn_h)
        self.btn_result_exit = pygame.Rect(self.btn_result_restart.right + btn_gap, btn_y, btn_w, btn_h)

        # Tombol Ulangi Duel (Aksen Emas/Biru Hangat)
        pygame.draw.rect(self.screen, (242, 230, 202), self.btn_result_restart, border_radius=8)
        pygame.draw.rect(self.screen, (195, 140, 35), self.btn_result_restart, 2, border_radius=8)
        r_txt = font_bubble.render("Ulangi Duel [R]", True, (130, 76, 12))
        self.screen.blit(r_txt, r_txt.get_rect(center=self.btn_result_restart.center))

        # Tombol Keluar Battle
        pygame.draw.rect(self.screen, (48, 122, 185), self.btn_result_exit, border_radius=8)
        pygame.draw.rect(self.screen, (30, 90, 148), self.btn_result_exit, 2, border_radius=8)
        e_lbl = "Kembali ke Peta [ESC]" if is_boss else "Keluar Battle [ESC]"
        e_txt = font_bubble.render(fit_text_to_width(font_bubble, e_lbl, btn_w - 12), True, (255, 255, 255))
        self.screen.blit(e_txt, e_txt.get_rect(center=self.btn_result_exit.center))
