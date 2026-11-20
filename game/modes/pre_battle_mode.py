"""PreBattleModeMixin: Optimasi CSP & Local Search serta render arena Pre-Battle."""

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


class PreBattleModeMixin:
    """Mixin method mode Pre-Battle untuk App."""

    def _on_ls_algo_changed(self, algo_code):
        self.selected_ls_algo = algo_code
        if self.game_mode == "PRE_BATTLE":
            self._run_optimization()

    def _run_optimization(self, randomize=False):
        """Menjalankan Local Search untuk menyeimbangkan squad NPC sesuai kondisi player."""
        player_ctx = {
            "player_hp": self.player.persistent_hp,
            "player_potions": self.player.persistent_potions,
            "player_atk_bonus": self.player.atk_bonus,
            "player_def_bonus": self.player.def_bonus,
        }
        manual_diff = getattr(self, "manual_target_difficulty", None)
        if getattr(self, "is_boss_battle", False):
            if manual_diff is not None:
                td = manual_diff
            else:
                # Mode adaptif Boss memperhitungkan bonus item Bolu (sampai 0.88)
                item_adj = min(0.28, (player_ctx["player_atk_bonus"] * 0.009 + player_ctx["player_def_bonus"] * 0.008))
                hp_adj = (player_ctx["player_hp"] - 100) / 300.0
                td = max(0.50, min(0.88, 0.62 + item_adj + hp_adj))
            self.optimizer.target_difficulty = td
            squad = NPCSquad.create_boss_squad(target_difficulty=td, player_context=player_ctx, randomize=randomize)
            self.current_squad = squad
            tot_hp = sum(m.max_hp for m in squad.members)
            tot_pot = sum(m.potions for m in squad.members)
            tot_atk = sum(m.atk_bonus for m in squad.members)
            cfg = {
                "npc_count": len(squad.members),
                "total_hp": tot_hp,
                "total_potions": tot_pot,
                "total_atk": tot_atk,
                "members": [
                    {
                        "name": m.name,
                        "char_type": m.char_type,
                        "hp": m.max_hp,
                        "potions": m.potions,
                        "atk_bonus": m.atk_bonus,
                        "def_bonus": m.def_bonus,
                        "eval_profile": m.eval_profile,
                    }
                    for m in squad.members
                ],
            }
            stats = {
                "algorithm": self.selected_ls_algo,
                "final_difficulty": round(td, 4),
                "final_fitness": 0.0,
                "iterations": 1,
                "time_ms": 0.05,
            }
            self.current_squad_config = cfg
            self.current_optimizer_stats = stats
            self.overlay.set_pre_battle_data(cfg, stats, self.selected_ls_algo)
            dock = getattr(self.overlay, "dock", None)
            tab_csp = dock.tabs.get(3) if dock and hasattr(dock, "tabs") else None
            if tab_csp and hasattr(tab_csp, "slider_diff") and not tab_csp.slider_diff.is_dragging:
                tab_csp.slider_diff.value = max(tab_csp.slider_diff.min_val, min(tab_csp.slider_diff.max_val, td))
            if randomize:
                if hasattr(self, "audio") and self.audio:
                    self.audio.play_reroll()
            return

        if manual_diff is not None:
            self.optimizer.target_difficulty = manual_diff
            ctx_for_opt = None
        else:
            ctx_for_opt = player_ctx

        init_state = None if randomize else getattr(self.optimizer, "last_csp_initial_state", None)
        cfg, stats = self.optimizer.optimize(
            self.selected_ls_algo, initial_state=init_state, player_context=ctx_for_opt, randomize_start=randomize
        )
        self.current_squad_config = cfg
        self.current_optimizer_stats = stats
        self.current_squad = NPCSquad.from_config(cfg)
        self.overlay.set_pre_battle_data(cfg, stats, self.selected_ls_algo)

        # Sinkronkan nilai slider CSP agar mencerminkan target_difficulty aktif (adaptif/manual)
        dock = getattr(self.overlay, "dock", None)
        tab_csp = dock.tabs.get(3) if dock and hasattr(dock, "tabs") else None
        if tab_csp and hasattr(tab_csp, "slider_diff") and not tab_csp.slider_diff.is_dragging:
            tab_csp.slider_diff.value = max(
                tab_csp.slider_diff.min_val,
                min(tab_csp.slider_diff.max_val, self.optimizer.target_difficulty),
            )

        # Sinkronisasi data ke modal visualizer AI
        csp_solver = self.optimizer.csp
        if randomize or not self.pre_battle_visualizer.csp_tree:
            self.pre_battle_visualizer.set_csp_data(
                csp_solver.search_tree,
                csp_solver.timeline_steps,
                csp_solver.solution_path_ids,
                csp_solver.tree_width,
                csp_solver.tree_height,
            )
        self.pre_battle_visualizer.set_ls_data(
            self.optimizer.history,
            self.selected_ls_algo,
            self.optimizer.target_difficulty,
        )

        if randomize:
            if hasattr(self, "audio") and self.audio:
                self.audio.play_reroll()
            self.reroll_toast_timer = 0.0
            self.pre_battle_anim = {
                "phase": "SEARCHING",
                "timer": 0.0,
                "search_dur": 0.42,
                "stagger": 0.14,
                "fade_dur": 0.28,
                "popped": set(),
            }

    def _get_scaled_ui_sprite(self, surf, max_w: int, max_h: int):
        """Skala proporsional sprite agar muat ketat dalam kotak batas & di-cache untuk performa 60 FPS."""
        sw = max(1, surf.get_width())
        sh = max(1, surf.get_height())
        scale = min(max(1, max_w) / float(sw), max(1, max_h) / float(sh))
        tw = max(1, int(round(sw * scale)))
        th = max(1, int(round(sh * scale)))

        cache = getattr(self, "_pre_battle_scale_cache", None)
        if cache is None:
            cache = {}
            self._pre_battle_scale_cache = cache
        key = (id(surf), tw, th)
        cached = cache.get(key)
        if cached is not None:
            return cached
        if len(cache) > 64:
            cache.clear()
        scaled = pygame.transform.smoothscale(surf, (tw, th))
        cache[key] = scaled
        return scaled

    def _draw_pre_battle_hero_card(self, p_card_rect, fonts):
        """Render kartu Hero Utama (Player) dengan proporsi dinamis & gambar besar dalam batas kotak."""
        font_title, font_bubble, font_sm, font_tiny = fonts
        draw_card(self.screen, p_card_rect, (255, 255, 255, 245), border_color=(218, 206, 188), border_radius=10)

        px, py, pw, ph = p_card_rect.x, p_card_rect.y, p_card_rect.width, p_card_rect.height
        p_header = font_title.render("Hero Utama (Player)", True, config.COLOR_TEXT_PRIMARY)
        self.screen.blit(p_header, (px + 14, py + 12))

        p_stats = [
            f"• Ramuan    : {self.player.persistent_potions} Botol (+25 HP)",
            f"• Serangan  : +{self.player.atk_bonus} ATK",
            f"• Ketahanan : +{self.player.def_bonus} DEF Flat",
            "• Karakter  : Petualang Tangguh",
        ]
        f_pstat = font_sm if (pw >= 295 and font_sm.size(p_stats[0])[0] <= pw - 28) else font_tiny
        line_step = 19 if f_pstat == font_tiny else 21
        stats_block_h = 16 + 10 + len(p_stats) * line_step + 6 + 22 + 38

        # Kotak showcase karakter mengisi sisa ruang vertikal secara dinamis
        showcase_top = py + 40
        showcase_h = max(110, ph - 40 - stats_block_h - 10)
        showcase_rect = pygame.Rect(px + 14, showcase_top, pw - 28, showcase_h)
        draw_card(self.screen, showcase_rect, (250, 246, 238), border_color=(232, 222, 206), border_radius=8)

        p_img = self.battle_sprites.get("player", self.player.sprite.current_image)
        p_big = self._get_scaled_ui_sprite(p_img, showcase_rect.width - 14, showcase_rect.height - 10)
        self.screen.blit(p_big, p_big.get_rect(center=showcase_rect.center))

        # Mini Bar HP Player
        hp_bar_y = showcase_rect.bottom + 10
        hp_bar_w = pw - 28
        hp_bar_h = 16
        pygame.draw.rect(self.screen, (235, 226, 215), (px + 14, hp_bar_y, hp_bar_w, hp_bar_h), border_radius=4)
        hp_fill = int((self.player.persistent_hp / 100.0) * hp_bar_w)
        if hp_fill > 0:
            pygame.draw.rect(self.screen, (42, 138, 62), (px + 14, hp_bar_y, hp_fill, hp_bar_h), border_radius=4)
        pygame.draw.rect(self.screen, (190, 178, 160), (px + 14, hp_bar_y, hp_bar_w, hp_bar_h), 1, border_radius=4)
        hp_lbl = font_sm.render(f"HP: {self.player.persistent_hp} / 100", True, (255, 255, 255))
        self.screen.blit(hp_lbl, (px + 14 + (hp_bar_w - hp_lbl.get_width()) // 2, hp_bar_y + 1))

        py_stat = hp_bar_y + hp_bar_h + 10
        for s in p_stats:
            self.screen.blit(f_pstat.render(s, True, config.COLOR_TEXT_PRIMARY), (px + 14, py_stat))
            py_stat += line_step

        # Rincian Inventori Barang
        py_stat += 6
        self.screen.blit(font_bubble.render("Artefak & Perlengkapan:", True, config.COLOR_ACCENT_GOLD), (px + 14, py_stat))
        ix, iy = px + 14, py_stat + 22
        max_ix = p_card_rect.right - 44
        name_to_key = {
            "Pedang Ksatria Oyen": "item_sword",
            "Busur Presisi Kuro": "item_bow",
            "Belati Bayangan Kage": "item_dagger",
            "Tongkat Sihir Shiro": "mega_potion",
        }
        for it in (self.player.inventory or ["item_sword"]):
            img_key = name_to_key.get(it, it)
            if img_key in self.item_images:
                if ix > max_ix:
                    ix = px + 14
                    iy += 36
                if iy + 32 <= p_card_rect.bottom - 6:
                    icon = self._get_scaled_ui_sprite(self.item_images[img_key], 32, 32)
                    self.screen.blit(icon, (ix, iy))
                    ix += 38

    def _draw_pre_battle_member_searching(self, m_rect, idx: int, anim_t: float, search_dur: float, fonts):
        """Render placeholder kartu saat animasi pencarian / pengacakan skuad sedang berlangsung."""
        _, font_bubble, font_sm, font_tiny = fonts
        role_cycle = [
            ("WARRIOR", (254, 242, 225), (225, 150, 50), (185, 100, 20)),
            ("RANGER", (232, 248, 235), (65, 160, 85), (35, 125, 55)),
            ("MAGE", (230, 242, 255), (75, 145, 220), (25, 100, 180)),
            ("ASSASSIN", (250, 235, 252), (175, 85, 195), (135, 50, 155)),
        ]
        step_idx = (int(anim_t * 14) + idx) % len(role_cycle)
        r_lbl, r_bg, r_bd, r_txt = role_cycle[step_idx]

        draw_card(self.screen, m_rect, (255, 253, 248, 245), border_color=(215, 168, 82), border_radius=8)

        # Sapuan kilau horizontal (scan shimmer) halus
        prog = min(1.0, (anim_t + idx * 0.08) / max(0.01, search_dur))
        scan_x = m_rect.x + int((m_rect.width - 70) * (prog % 1.0))
        scan_surf = pygame.Surface((70, m_rect.height - 4), SRCALPHA)
        scan_surf.fill((255, 232, 165, 55))
        self.screen.blit(scan_surf, (scan_x, m_rect.y + 2))

        portrait_w = max(76, min(m_rect.height - 14, int(m_rect.width * 0.28)))
        p_box = pygame.Rect(m_rect.x + 8, m_rect.y + 7, portrait_w, m_rect.height - 14)
        draw_card(self.screen, p_box, r_bg, border_color=r_bd, border_radius=7)
        q_lbl = font_bubble.render("?", True, r_txt)
        self.screen.blit(q_lbl, q_lbl.get_rect(center=p_box.center))

        tx = p_box.right + 14
        dots = "." * (int(anim_t * 10 + idx) % 3 + 1)
        s1 = font_bubble.render(f"Slot {idx + 1}: Mengoptimasi Skuad{dots}", True, config.COLOR_ACCENT_GOLD)
        s2 = font_sm.render(f"Menguji kandidat: [{r_lbl}] via CSP + Local Search", True, config.COLOR_TEXT_SECONDARY)
        self.screen.blit(s1, (tx, m_rect.centery - 20))
        self.screen.blit(s2, (tx, m_rect.centery + 4))

    def _draw_pre_battle_member_card(self, m_rect, idx: int, m, fonts, alpha: int = 255):
        """Render 1 kartu anggota skuad NPC lawan dengan gambar besar proporsional & dukungan fade-in."""
        font_title, font_bubble, font_sm, font_tiny = fonts
        role_styles = {
            "warrior": ("WARRIOR", (254, 242, 225), (225, 150, 50), (185, 100, 20), "Ketahanan tinggi & seimbang"),
            "ranger": ("RANGER", (232, 248, 235), (65, 160, 85), (35, 125, 55), "Pemanah lincah & akurat"),
            "mage": ("MAGE", (230, 242, 255), (75, 145, 220), (25, 100, 180), "Spesialis sihir kehancuran"),
            "assassin": ("ASSASSIN", (250, 235, 252), (175, 85, 195), (135, 50, 155), "Penyelinap & serangan kritis"),
        }
        ctype_lower = m.char_type.lower()
        job_label, pill_bg, pill_border, pill_text_col, trait_desc = role_styles.get(
            ctype_lower,
            (ctype_lower.upper(), (242, 238, 230), (170, 155, 138), (115, 98, 82), "Petarung tangguh tim AI"),
        )

        # Render ke surface terpisah hanya ketika fade-in aktif (alpha < 255) agar hemat CPU
        if alpha < 255:
            target = pygame.Surface((m_rect.width, m_rect.height), SRCALPHA)
            card_rect = pygame.Rect(0, 0, m_rect.width, m_rect.height)
        else:
            target = self.screen
            card_rect = m_rect

        draw_card(target, card_rect, (255, 255, 255, 245), border_color=(218, 206, 188), border_radius=8)

        # Area portrait proporsional agar karakter tampil besar & tegas namun tetap di dalam kotak
        portrait_w = max(84, min(card_rect.height - 14, int(card_rect.width * 0.29)))
        portrait_box = pygame.Rect(card_rect.x + 8, card_rect.y + 7, portrait_w, card_rect.height - 14)
        draw_card(target, portrait_box, (250, 246, 238), border_color=(232, 222, 206), border_radius=7)

        npc_thumb = m.battle_sprite or m.portrait
        if npc_thumb:
            p_icon = self._get_scaled_ui_sprite(npc_thumb, portrait_box.width - 8, portrait_box.height - 8)
            target.blit(p_icon, p_icon.get_rect(center=portrait_box.center))

        # Kolom Teks di kanan portrait box
        tx = portrait_box.right + 14
        ty = card_rect.y + max(10, (card_rect.height - 84) // 2)
        max_txt_w = card_rect.right - tx - 12

        # Baris 1: Nama di kiri, Pill Badge Job di kanan
        pill_txt = font_tiny.render(job_label, True, pill_text_col)
        pill_w = pill_txt.get_width() + 12
        pill_h = 19
        pill_rect = pygame.Rect(card_rect.right - pill_w - 12, ty + 1, pill_w, pill_h)
        draw_card(target, pill_rect, pill_bg, border_color=pill_border, border_radius=4)
        target.blit(pill_txt, pill_txt.get_rect(center=pill_rect.center))

        name_avail_w = pill_rect.left - tx - 8
        full_name = f"{idx + 1}. {m.name}"
        if font_title.size(full_name)[0] <= name_avail_w:
            t_name = font_title.render(full_name, True, config.COLOR_TEXT_PRIMARY)
        elif font_bubble.size(full_name)[0] <= name_avail_w:
            t_name = font_bubble.render(full_name, True, config.COLOR_TEXT_PRIMARY)
        else:
            short_name = f"{idx + 1}. {m.name.split()[0]}"
            t_name = font_bubble.render(short_name, True, config.COLOR_TEXT_PRIMARY)
        target.blit(t_name, (tx, ty))

        # Baris 2: Mini HP Bar (Coral) & Potions
        txt_hp = font_tiny.render(f"{m.max_hp} HP │ {m.potions} Potion", True, config.COLOR_TEXT_PRIMARY)
        m_hp_w = min(110, max(50, max_txt_w - txt_hp.get_width() - 12))
        m_hp_y = ty + 25
        pygame.draw.rect(target, (235, 226, 215), (tx, m_hp_y, m_hp_w, 12), border_radius=3)
        m_fill = max(0, min(m_hp_w, int((m.max_hp / 120.0) * m_hp_w)))
        pygame.draw.rect(target, (215, 65, 55), (tx, m_hp_y, m_fill, 12), border_radius=3)
        target.blit(txt_hp, (tx + m_hp_w + 8, m_hp_y - 2))

        # Baris 3 & 4: ATK, DEF, AI Profile & Deskripsi Trait
        line3 = f"+{m.atk_bonus} ATK │ +{m.def_bonus} DEF │ {m.eval_profile}"
        target.blit(font_sm.render(line3, True, config.COLOR_TEXT_SECONDARY), (tx, ty + 43))
        target.blit(font_tiny.render(trait_desc, True, (135, 118, 102)), (tx, ty + 64))

        if alpha < 255:
            target.set_alpha(alpha)
            self.screen.blit(target, m_rect.topleft)

    def _draw_pre_battle_arena(self):
        w, h = self.screen.get_size()
        is_dock_open = getattr(self.overlay.dock, "is_open", False) if hasattr(self, "overlay") and hasattr(self.overlay, "dock") else False
        panel_w = self.overlay.dock.rect.right if is_dock_open else config.TOTAL_COLLAPSED_WIDTH
        arena_w = w - panel_w
        area_cx = panel_w + arena_w // 2

        # Latar belakang arena hangat bertema Cozy Adventurer Journal
        self.battle_bg.draw(self.screen, panel_w, arena_w, h)
        warm_surf = pygame.Surface((arena_w, h), SRCALPHA)
        warm_surf.fill((46, 35, 25, 140))
        self.screen.blit(warm_surf, (panel_w, 0))

        font_huge = self.fonts.get("huge", self.fonts["title"])
        font_title = self.fonts.get("title", self.fonts["sm"])
        font_bubble = self.fonts.get("bubble", self.fonts["sm"])
        font_sm = self.fonts["sm"]
        font_tiny = self.fonts.get("tiny", font_sm)
        ui_fonts = (font_title, font_bubble, font_sm, font_tiny)

        # Header Title + bayangan lembut agar tajam terbaca
        is_boss = bool(getattr(self, "is_boss_battle", False))
        title_str = "PERSIAPAN DUEL BOSS: MENARA KUNO" if is_boss else "PERSIAPAN PERTEMPURAN (PRE-BATTLE)"
        t_shadow = font_huge.render(title_str, True, (28, 20, 14))
        t_surf = font_huge.render(title_str, True, (255, 224, 110))
        tx_hdr = area_cx - t_surf.get_width() // 2
        self.screen.blit(t_shadow, (tx_hdr + 1, 24))
        self.screen.blit(t_surf, (tx_hdr, 22))

        sub_txt = (
            "Kekuatan Kage & pengawalnya menyesuaikan Target Difficulty & item Bolu (Tab 05-06)"
            if is_boss
            else "Keseimbangan komposisi skuad lawan dioptimasi via CSP (MRV+LCV+AC-3) & Local Search"
        )
        f_sub = font_sm if font_sm.size(sub_txt)[0] <= arena_w - 40 else font_tiny
        if f_sub.size(sub_txt)[0] > arena_w - 40:
            sub_txt = "Komposisi skuad lawan dioptimasi via CSP & Local Search"
            f_sub = font_tiny
        sub_surf = f_sub.render(sub_txt, True, (245, 236, 218))
        self.screen.blit(sub_surf, (area_cx - sub_surf.get_width() // 2, 56))

        # Geometri Area Kartu Kiri & Kanan
        btn_h = 44
        btn_y = h - 68
        available_h = max(380, btn_y - 20 - 92)
        avail_w = arena_w - 44

        p_card_w = min(345, max(230, int(avail_w * 0.37)))
        p_card_x = panel_w + 16
        p_card_y = 90
        p_card_rect = pygame.Rect(p_card_x, p_card_y, p_card_w, available_h)
        self._draw_pre_battle_hero_card(p_card_rect, ui_fonts)

        # Sisi Kanan: Profil Squad NPC Lawan
        squad_area_x = p_card_rect.right + 14
        squad_area_w = avail_w - p_card_w - 2

        sq_hdr_txt = "Skuad Lawan (CSP & Local Search)"
        self.screen.blit(font_title.render(sq_hdr_txt, True, (28, 20, 14)), (squad_area_x + 1, p_card_y))
        self.screen.blit(font_title.render(sq_hdr_txt, True, (255, 224, 110)), (squad_area_x, p_card_y - 2))

        members = self.current_squad.members if self.current_squad else []
        num_m = max(1, len(members))
        gap = 10
        list_top = p_card_y + 28
        list_h = p_card_rect.bottom - list_top
        member_card_h = max(92, (list_h - (num_m - 1) * gap) // num_m)
        m_y = list_top

        anim = getattr(self, "pre_battle_anim", None)
        for idx, m in enumerate(members):
            # Pastikan kartu terakhir rata bawah tepat sejajar kartu Hero Utama
            cur_h = (p_card_rect.bottom - m_y) if (idx == num_m - 1 and (p_card_rect.bottom - m_y) >= 92) else member_card_h
            m_rect = pygame.Rect(squad_area_x, m_y, squad_area_w, cur_h)

            if anim and anim.get("phase") == "SEARCHING":
                self._draw_pre_battle_member_searching(m_rect, idx, anim["timer"], anim["search_dur"], ui_fonts)
            elif anim and anim.get("phase") == "REVEAL":
                raw_p = (anim["timer"] - idx * anim["stagger"]) / max(0.01, anim["fade_dur"])
                if raw_p <= 0.0:
                    # Slot menanti giliran fade-in
                    draw_card(self.screen, m_rect, (255, 253, 248, 80), border_color=(218, 206, 188), border_radius=8)
                else:
                    prog = min(1.0, raw_p)
                    ease = 1.0 - (1.0 - prog) ** 3
                    card_alpha = max(1, min(255, int(round(255 * ease))))
                    y_off = int(round((1.0 - ease) * 12))
                    self._draw_pre_battle_member_card(m_rect.move(0, y_off), idx, m, ui_fonts, alpha=card_alpha)
            else:
                self._draw_pre_battle_member_card(m_rect, idx, m, ui_fonts, alpha=255)

            m_y += cur_h + gap

        # Bagian Bawah: 4 Tombol CTA Interaktif di Dasar Layar
        avail_btn_w = arena_w - 40
        btn_gap = 10
        btn_w = max(110, min(185, (avail_btn_w - 3 * btn_gap) // 4))
        total_w = 4 * btn_w + 3 * btn_gap
        start_x = panel_w + (arena_w - total_w) // 2

        self.btn_pre_battle_inspect = pygame.Rect(start_x, btn_y, btn_w, btn_h)
        self.btn_pre_battle_start = pygame.Rect(start_x + (btn_w + btn_gap), btn_y, btn_w, btn_h)
        self.btn_pre_battle_reroll = pygame.Rect(start_x + 2 * (btn_w + btn_gap), btn_y, btn_w, btn_h)
        self.btn_pre_battle_cancel = pygame.Rect(start_x + 3 * (btn_w + btn_gap), btn_y, btn_w, btn_h)

        t_inspect_txt = "[T] Pohon CSP & LS" if btn_w >= 145 else "[T] Pohon CSP"
        cta_specs = [
            (self.btn_pre_battle_inspect, (244, 248, 255), (70, 130, 210), t_inspect_txt, (25, 85, 160)),
            (self.btn_pre_battle_start, (42, 138, 62), (30, 110, 48), "[SPASI] Mulai Duel", (255, 255, 255)),
            (self.btn_pre_battle_reroll, (205, 135, 25), (175, 110, 15), "[R] Acak Ulang", (255, 255, 255)),
            (self.btn_pre_battle_cancel, (115, 98, 82), (88, 72, 60), "[ESC] Kembali", (255, 255, 255)),
        ]
        m_pos = pygame.mouse.get_pos()
        for b_rect, b_bg, b_bd, b_label, b_txt_col in cta_specs:
            hovered = b_rect.collidepoint(m_pos)
            draw_r = b_rect.move(0, -2) if hovered else b_rect
            draw_card(self.screen, draw_r, b_bg, border_color=b_bd, border_radius=7)
            lbl_s = font_bubble.render(b_label, True, b_txt_col)
            self.screen.blit(lbl_s, lbl_s.get_rect(center=draw_r.center))

        # Notifikasi visual saat Re-Roll selesai dijalankan
        if self.reroll_toast_timer > 0:
            toast_text = "Skuad NPC berhasil diacak & dioptimasi!"
            toast_surf = font_bubble.render(toast_text, True, (255, 255, 255))
            tw = toast_surf.get_width() + 28
            th = 28
            toast_rect = pygame.Rect(area_cx - tw // 2, btn_y - 36, tw, th)
            draw_card(self.screen, toast_rect, (42, 138, 62), border_color=(30, 110, 48), border_radius=6)
            self.screen.blit(toast_surf, toast_surf.get_rect(center=toast_rect.center))
