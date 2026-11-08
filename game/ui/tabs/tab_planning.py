"""Tab 5: Materi 08: Automated Classical Planning (Cozy Adventurer Journal Theme).

Menyajikan state fluents awal (s0), sasaran goal state, perumusan sekuens aksi
melalui Forward Progression A* Search atau Backward Regression dengan proteksi anti-overflow.
"""

from typing import Dict, Any, Optional
import pygame
from ...core import config
from ..components import draw_card, draw_badge_pill, draw_metric_tile, UIDropdown, UIButton, render_fitted_text, fit_text_to_width
from ...planning.domain_world_patrol import create_world_patrol_problem
from ...planning.domain_battle_tactics import create_battle_tactics_problem

MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1025)


def _clean_pred_str(p_obj: Any) -> str:
    """Format predikat PDDL ringkas dan mudah dibaca."""
    if hasattr(p_obj, "name") and hasattr(p_obj, "args"):
        args_str = ", ".join(str(a).replace("Waypoint_", "W_").replace("Peti_", "P_") for a in p_obj.args)
        prefix = "~" if getattr(p_obj, "is_negated", False) else ""
        return f"{prefix}{p_obj.name}({args_str})"
    s = repr(p_obj)
    return s.replace("Waypoint_", "W_").replace("Peti_", "P_")


class TabPlanning:
    """Tab 5: Automated Planning (PDDL) Control & Timeline."""

    def __init__(self, rect: pygame.Rect, fonts: Dict[str, pygame.font.Font], app_ref: Any):
        self.rect = pygame.Rect(rect)
        self.fonts = fonts
        self.app = app_ref

        engine_options = [
            ("FORWARD_A_STAR", "Forward Progression (A*)"),
            ("BACKWARD_REGRESSION", "Backward Regression (STRIPS)"),
        ]
        self.dropdown_engine = UIDropdown(
            pygame.Rect(self.rect.x + 12, self.rect.y + 60, self.rect.width - 24, 32),
            engine_options,
            on_select=self._on_engine_selected,
            initial_idx=0,
            font=fonts.get("sm", pygame.font.Font(None, 16)),
        )

        btn_w = self.rect.width - 24
        self.btn_plan_tree = UIButton(
            pygame.Rect(self.rect.x + 12, self.rect.y + 480, btn_w, 38),
            "Buka Pohon Rencana PDDL [T]",
            fonts.get("sm", pygame.font.Font(None, 16)),
            on_click=self._on_open_plan_tree,
            bg_color=(242, 235, 222),
            hover_color=(255, 252, 245),
            active_color=(230, 220, 205),
            border_color=config.COLOR_CARD_BORDER,
            icon=None,
        )

    def resize(self, rect: pygame.Rect) -> None:
        self.rect = pygame.Rect(rect)

    def _on_engine_selected(self, index: int, key: str) -> None:
        if self.app and hasattr(self.app, "forward_planner") and hasattr(self.app, "backward_planner"):
            mode = getattr(self.app, "game_mode", "EXPLORATION")
            if mode == "BATTLE":
                warrior = "Oyen the Warrior"
                tank = "Kuro the Ranger"
                healer = "Shiro the Mage"
                if hasattr(self.app, "current_squad") and self.app.current_squad and len(self.app.current_squad.members) >= 2:
                    m = self.app.current_squad.members
                    warrior = m[0].name
                    tank = m[1].name
                    healer = m[2].name if len(m) > 2 else m[1].name
                s0, goal, actions = create_battle_tactics_problem(warrior, tank, healer)
            else:
                chest_tag = "A"
                if hasattr(self.app, "chests") and self.app.chests and self.app.chests[0].get("opened", False):
                    chest_tag = "A"
                s0, goal, actions = create_world_patrol_problem(chest_tag)

            if index == 0:
                self.app.latest_plan_result = self.app.forward_planner.plan(s0, goal, actions)
            else:
                self.app.latest_plan_result = self.app.backward_planner.plan(s0, goal, actions)

    def _on_open_plan_tree(self) -> None:
        if hasattr(self.app, "open_graph_modal"):
            self.app.open_graph_modal("PLANNING")

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.dropdown_engine.handle_event(event):
            return True
        if self.btn_plan_tree.handle_event(event):
            return True
        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        font_tiny = self.fonts.get("tiny", pygame.font.Font(None, 13))
        font_sm = self.fonts.get("sm", pygame.font.Font(None, 16))
        font_title = self.fonts.get("title", pygame.font.Font(None, 19))

        cx = self.rect.x + 12
        cy = self.rect.y + 12
        card_w = self.rect.width - 24

        # 1. KARTU MESIN PERENCANA (PLANNING ENGINE)
        card_eng_h = 78
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_eng_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        lbl_eng = font_tiny.render("Mesin Perencana PDDL:", True, config.COLOR_TEXT_SECONDARY)
        surface.blit(lbl_eng, (cx + 12, cy + 8))
        self.dropdown_engine.rect = pygame.Rect(cx + 10, cy + 28, card_w - 20, 32)
        self.dropdown_engine.draw(surface)

        # 2. KARTU FLUENTS AWAL & SASARAN (S0 vs GOAL) - DENGAN PROTEKSI MULTI-LINE ANTI-OVERFLOW
        cy += card_eng_h + 12
        card_fluents_h = 138
        fl_rect = pygame.Rect(cx, cy, card_w, card_fluents_h)
        draw_card(surface, fl_rect, config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        fl_title = font_tiny.render("── STATE FLUENTS (s0 vs Goal) ──", True, config.COLOR_TEXT_SECONDARY)
        surface.blit(fl_title, (cx + (card_w - fl_title.get_width()) // 2, cy + 6))

        mode_str = getattr(self.app, "game_mode", "EXPLORATION")
        plan_res = getattr(self.app, "latest_plan_result", None)

        if plan_res and plan_res.s0:
            s0_lines = [f"• {_clean_pred_str(p)}" for p in list(plan_res.s0.predicates)[:2]]
            goal_lines = [f"* {_clean_pred_str(p)}" for p in list(plan_res.goal)[:2]]
        elif mode_str == "BATTLE":
            s0_lines = [
                "• Skuad: Warrior HP rendah (28 HP)",
                "• Tank: Siaga Defend │ Mage: Siaga Heal",
            ]
            goal_lines = [
                "* Goal: Amankan Skuad & Kalahkan Bolu",
            ]
        else:
            s0_lines = [
                "• Peti A: Terjarah (Looted by Bolu)",
                "• Kuro: Tebing Barat │ Shiro: Dermaga",
            ]
            goal_lines = [
                "* Goal: Hadang Bolu & Amankan Peti B, C",
            ]

        # Render s0
        surface.blit(font_tiny.render("State Awal (s0):", True, config.COLOR_ACCENT_BLUE), (cx + 12, cy + 26))
        fy = cy + 44
        for line in s0_lines:
            render_fitted_text(surface, font_tiny, line, config.COLOR_TEXT_PRIMARY, (cx + 14, fy), card_w - 28)
            fy += 18

        # Render Goal
        surface.blit(font_tiny.render("Sasaran (Goal):", True, config.COLOR_ACCENT_GOLD), (cx + 12, fy + 4))
        fy += 22
        for line in goal_lines:
            render_fitted_text(surface, font_tiny, line, config.COLOR_STATUS_SUCCESS, (cx + 14, fy), card_w - 28)
            fy += 18

        # 3. KARTU SEKUENS RENCANA STRIPS TERBENTUK
        cy += card_fluents_h + 12
        card_plan_h = 175
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_plan_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        pl_title = font_tiny.render("── SEKUENS RENCANA STRIPS TERBENTUK ──", True, config.COLOR_TEXT_SECONDARY)
        surface.blit(pl_title, (cx + (card_w - pl_title.get_width()) // 2, cy + 6))

        if plan_res and plan_res.plan:
            plan_steps = []
            for idx, act in enumerate(plan_res.plan[:3], start=1):
                pre_list = [_clean_pred_str(p) for p in act.preconditions]
                add_list = [_clean_pred_str(p) for p in act.add_list]
                pre_txt = ", ".join(pre_list) if pre_list else "None"
                add_txt = ", ".join(add_list) if add_list else "None"
                plan_steps.append((f"{idx}. {act.name}()", f"Pre: {pre_txt[:15]} │ Add: {add_txt[:15]}"))
        elif mode_str == "BATTLE":
            plan_steps = [
                ("1. SwapToTank()", "Pre: LowHP │ Add: TankActive"),
                ("2. CastDefendShield()", "Pre: TankActive │ Add: Defended"),
                ("3. CastHealPotion()", "Pre: Defended │ Add: Healed"),
            ]
        else:
            plan_steps = [
                ("1. MoveToChokePoint()", "Pre: At(Tebing) │ Add: At(Jembatan)"),
                ("2. InterceptPlayer()", "Pre: At(Jembatan) │ Add: InCombat"),
                ("3. ReinforceGuard()", "Pre: InCombat │ Add: IslandSecure"),
            ]

        sy = cy + 28
        inner_w = card_w - 20
        for act, eff in plan_steps:
            s_rect = pygame.Rect(cx + 10, sy, inner_w, 44)
            draw_card(surface, s_rect, (250, 246, 238), border_color=(226, 216, 202), border_radius=5)
            render_fitted_text(surface, font_sm, act, config.COLOR_ACCENT_GOLD, (s_rect.x + 8, s_rect.y + 4), inner_w - 16)
            render_fitted_text(surface, font_tiny, eff, config.COLOR_TEXT_SECONDARY, (s_rect.x + 8, s_rect.y + 24), inner_w - 16)
            sy += 48

        cy += card_plan_h + 12
        self.btn_plan_tree.rect = pygame.Rect(cx, cy, card_w, 38)
        self.btn_plan_tree.draw(surface)

    def draw_popups(self, surface: pygame.Surface) -> None:
        self.dropdown_engine.draw_menu(surface)
