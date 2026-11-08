"""Overlay GUI Visualizer Modul 08: Automated Classical Planning (Shortcut [P]).

Menyajikan transparansi perumusan rencana aksi STRIPS secara akademis:
1. Status Fluents Awal (s0) vs Sasaran Kondisi Akhir (Goal)
2. Pemilih Mesin Perencana: Forward Progression (A*) vs Backward Regression (STRIPS)
3. Metrik Pencarian Ruang Keadaan (Waktu ms, Simpul Dievaluasi, Panjang Rencana)
4. Sekuens Rencana Aksi Terbentuk dengan Preconditions, Add-List, dan Delete-List
5. Tombol Pohon Pencarian Rencana [T]
"""

from typing import Dict, Any, Optional, List
import pygame
from ..core import config
from .components import draw_card, draw_badge_pill, UIDropdown, UIButton, render_fitted_text, fit_text_to_width
from ..planning.planner_engine import ForwardProgressionPlanner, BackwardRegressionPlanner, PlanningResult
from ..planning.domain_world_patrol import create_world_patrol_problem
from ..planning.domain_battle_tactics import create_battle_tactics_problem


def _clean_pred(p_obj: Any) -> str:
    if hasattr(p_obj, "name") and hasattr(p_obj, "args"):
        args_str = ", ".join(str(a).replace("Waypoint_", "W_").replace("Peti_", "P_") for a in p_obj.args)
        prefix = "~" if getattr(p_obj, "is_negated", False) else ""
        return f"{prefix}{p_obj.name}({args_str})"
    s = repr(p_obj)
    return s.replace("Waypoint_", "W_").replace("Peti_", "P_")


class PlanningOverlay:
    """Layar overlay visualizer automated classical planning PDDL."""

    def __init__(self, fonts: Dict[str, pygame.font.Font], app_ref: Any = None):
        self.fonts = fonts
        self.app = app_ref
        self.visible = False

        self.forward_planner = ForwardProgressionPlanner()
        self.backward_planner = BackwardRegressionPlanner()
        self.current_engine_idx = 0  # 0: Forward A*, 1: Backward Regression

        self.latest_plan_result: Optional[PlanningResult] = None
        self._solve_active_domain()

        # Dropdown Pemilih Mesin Perencana
        engine_options = [
            ("FORWARD_A_STAR", "Forward Progression (A*)"),
            ("BACKWARD_REGRESSION", "Backward Regression (STRIPS)"),
        ]
        self.dropdown_engine = UIDropdown(
            pygame.Rect(0, 0, 240, 32),
            engine_options,
            on_select=self._on_engine_selected,
            initial_idx=0,
            font=fonts.get("sm", pygame.font.Font(None, 16)),
        )

        # Tombol Buka Pohon Rencana
        self.btn_tree = UIButton(
            pygame.Rect(0, 0, 260, 36),
            "Buka Pohon Rencana PDDL [T]",
            fonts.get("sm", pygame.font.Font(None, 16)),
            on_click=self._on_open_tree,
            bg_color=(242, 235, 222),
            hover_color=(255, 252, 245),
            active_color=(230, 220, 205),
            border_color=config.COLOR_CARD_BORDER,
            icon=None,
        )

        # Tombol Tutup [ESC]
        self.btn_close = UIButton(
            pygame.Rect(0, 0, 110, 36),
            "Tutup [ESC]",
            fonts.get("sm", pygame.font.Font(None, 16)),
            on_click=self.toggle,
            bg_color=(242, 235, 222),
            hover_color=(255, 240, 240),
            active_color=(230, 215, 215),
            border_color=config.COLOR_CARD_BORDER,
            icon=None,
        )

    def _on_engine_selected(self, index: int, key: str) -> None:
        self.current_engine_idx = index
        self._solve_active_domain()

    def _solve_active_domain(self) -> None:
        """Menjalankan pemecahan domain aktif (Eksplorasi vs Battle)."""
        mode = getattr(self.app, "game_mode", "EXPLORATION") if self.app else "EXPLORATION"

        if mode == "BATTLE":
            warrior = "Oyen the Warrior"
            tank = "Kuro the Ranger"
            healer = "Shiro the Mage"
            if self.app and getattr(self.app, "current_squad", None) and len(self.app.current_squad.members) >= 2:
                m = self.app.current_squad.members
                warrior = m[0].name
                tank = m[1].name
                healer = m[2].name if len(m) > 2 else m[1].name
            s0, goal, actions = create_battle_tactics_problem(warrior, tank, healer)
        else:
            s0, goal, actions = create_world_patrol_problem("A")

        if self.current_engine_idx == 0:
            self.latest_plan_result = self.forward_planner.plan(s0, goal, actions)
        else:
            self.latest_plan_result = self.backward_planner.plan(s0, goal, actions)

    def toggle(self) -> None:
        """Membuka atau menutup overlay visualizer planning."""
        self.visible = not self.visible
        if self.visible:
            self._solve_active_domain()

    def _on_open_tree(self) -> None:
        if self.app and hasattr(self.app, "open_graph_modal"):
            self.visible = False
            self.app.open_graph_modal("PLANNING")

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.visible:
            return False

        if self.dropdown_engine.handle_event(event):
            return True

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.visible = False
                return True
            elif event.key == pygame.K_t:
                self._on_open_tree()
                return True

        if self.btn_tree.handle_event(event):
            return True
        if self.btn_close.handle_event(event):
            return True

        return True

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        w, h = surface.get_size()

        # 1. Dim Backdrop
        dim_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        dim_surf.fill((10, 8, 6, 120))
        surface.blit(dim_surf, (0, 0))

        # 2. Main Modal Card (Cozy Adventurer Journal)
        mw, mh = min(880, w - 80), min(660, h - 60)
        mx, my = (w - mw) // 2, (h - mh) // 2
        modal_rect = pygame.Rect(mx, my, mw, mh)

        # Shadow
        shadow_surf = pygame.Surface((mw, mh), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 45), (0, 0, mw, mh), border_radius=14)
        surface.blit(shadow_surf, (mx + 4, my + 4))

        # Card body
        card_surf = pygame.Surface((mw, mh), pygame.SRCALPHA)
        card_surf.fill((255, 253, 248, 252))
        pygame.draw.rect(card_surf, config.COLOR_CARD_BORDER, (0, 0, mw, mh), 2, border_radius=14)
        surface.blit(card_surf, modal_rect)

        font_tiny = self.fonts.get("tiny", self.fonts.get("sm"))
        font_sm = self.fonts.get("sm", font_tiny)
        font_bubble = self.fonts.get("bubble", font_sm)
        font_title = self.fonts.get("title", font_bubble)

        # Header Bar
        hdr_rect = pygame.Rect(mx + 20, my + 16, mw - 40, 42)
        draw_card(surface, hdr_rect, (246, 238, 224), border_color=(218, 195, 160), border_radius=8)
        title_surf = font_title.render("MATERI 08: AUTOMATED CLASSICAL PLANNING (PDDL)", True, (45, 32, 22))
        surface.blit(title_surf, (hdr_rect.x + 14, hdr_rect.y + 9))

        res = self.latest_plan_result
        time_str = f"Waktu: {res.time_ms:.2f} ms | Simpul: {res.nodes_expanded}" if res else ""
        badge_sub = font_tiny.render(time_str, True, config.COLOR_ACCENT_GOLD)
        surface.blit(badge_sub, (hdr_rect.right - badge_sub.get_width() - 14, hdr_rect.y + 13))

        # 3. KONTEN KIRI: STATE FLUENTS (s0 vs GOAL) & PILIH MESIN
        left_w = (mw - 56) // 2
        col1_x = mx + 20
        col2_x = col1_x + left_w + 16
        content_y = my + 72

        # A. Mesin Perencana Card
        eng_card_h = 76
        draw_card(surface, pygame.Rect(col1_x, content_y, left_w, eng_card_h), (255, 255, 255),
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)
        surface.blit(font_tiny.render("Mesin Perencana Ruang Keadaan:", True, config.COLOR_TEXT_SECONDARY), (col1_x + 12, content_y + 8))
        self.dropdown_engine.rect = pygame.Rect(col1_x + 12, content_y + 30, left_w - 24, 32)
        self.dropdown_engine.draw(surface)

        # B. State Fluents (s0 vs Goal)
        fl_card_y = content_y + eng_card_h + 12
        fl_card_h = mh - (fl_card_y - my) - 64
        draw_card(surface, pygame.Rect(col1_x, fl_card_y, left_w, fl_card_h), (255, 255, 255),
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)
        surface.blit(font_bubble.render("Status Keadaan Awal (s0) & Goal", True, config.COLOR_ACCENT_GOLD), (col1_x + 12, fl_card_y + 8))

        mode_str = getattr(self.app, "game_mode", "EXPLORATION") if self.app else "EXPLORATION"
        draw_badge_pill(surface, pygame.Rect(col1_x + 12, fl_card_y + 32, left_w - 24, 22),
                        f"DOMAIN: {'BATTLE TAG-TEAM' if mode_str == 'BATTLE' else 'WORLD PATROL DEFENSE'}",
                        (244, 238, 226), config.COLOR_ACCENT_GOLD, font_tiny)

        # List s0
        surface.blit(font_tiny.render("Fluents Keadaan Awal (s0):", True, config.COLOR_ACCENT_BLUE), (col1_x + 14, fl_card_y + 60))
        s0_preds = [_clean_pred(p) for p in res.s0.predicates] if res and res.s0 else []
        fy = fl_card_y + 78
        for p_str in s0_preds[:5]:
            render_fitted_text(surface, font_tiny, f"• {p_str}", config.COLOR_TEXT_PRIMARY, (col1_x + 16, fy), left_w - 32)
            fy += 17

        # List Goal
        surface.blit(font_tiny.render("Sasaran Kondisi Akhir (Goal):", True, config.COLOR_STATUS_SUCCESS), (col1_x + 14, fy + 8))
        goal_preds = [_clean_pred(p) for p in res.goal] if res and res.goal else []
        gy = fy + 26
        for g_str in goal_preds[:3]:
            render_fitted_text(surface, font_tiny, f"* {g_str}", config.COLOR_STATUS_SUCCESS, (col1_x + 16, gy), left_w - 32)
            gy += 17

        # 4. KONTEN KANAN: SEKUENS RENCANA STRIPS TERBENTUK
        right_w = left_w
        plan_card_h = mh - (content_y - my) - 64
        draw_card(surface, pygame.Rect(col2_x, content_y, right_w, plan_card_h), (255, 255, 255),
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)
        surface.blit(font_bubble.render("Sekuens Rencana Aksi STRIPS Terbentuk", True, config.COLOR_TEXT_PRIMARY), (col2_x + 12, content_y + 8))

        plan_len_str = f"Panjang Rencana: {len(res.plan)} Aksi Optimal" if res and res.success else "Tidak ada rencana"
        surface.blit(font_tiny.render(plan_len_str, True, config.COLOR_ACCENT_GOLD), (col2_x + 14, content_y + 32))

        # Action Cards Timeline
        ay = content_y + 54
        inner_box_w = right_w - 20
        if res and res.plan:
            for idx, act in enumerate(res.plan, start=1):
                a_rect = pygame.Rect(col2_x + 10, ay, inner_box_w, 68)
                draw_card(surface, a_rect, (250, 246, 238), border_color=(226, 216, 202), border_radius=6)

                # Header Aksi
                render_fitted_text(surface, font_sm, f"{idx}. {act.name}", config.COLOR_ACCENT_GOLD, (a_rect.x + 8, a_rect.y + 4), inner_box_w - 16)

                # Preconditions
                pre_str = ", ".join(_clean_pred(p) for p in act.preconditions) or "None"
                render_fitted_text(surface, font_tiny, f"Pre: {pre_str}", config.COLOR_TEXT_SECONDARY, (a_rect.x + 8, a_rect.y + 24), inner_box_w - 16)

                # Add / Del
                add_str = f"+Add: {', '.join(_clean_pred(p) for p in act.add_list)}"
                render_fitted_text(surface, font_tiny, add_str, config.COLOR_STATUS_SUCCESS, (a_rect.x + 8, a_rect.y + 42), inner_box_w - 16)

                ay += 74
                if ay + 70 > my + mh - 60:
                    break
        else:
            render_fitted_text(surface, font_tiny, "Pencarian rencana belum dijalankan.", config.COLOR_TEXT_SECONDARY, (col2_x + 14, ay + 20), inner_box_w)

        # 5. Bottom Action Ribbon
        btn_y = my + mh - 48
        self.btn_tree.rect = pygame.Rect(mx + 20, btn_y, 260, 36)
        self.btn_tree.draw(surface)

        self.btn_close.rect = pygame.Rect(mx + mw - 130, btn_y, 110, 36)
        self.btn_close.draw(surface)

        # Popup dropdown menu
        self.dropdown_engine.draw_menu(surface)

