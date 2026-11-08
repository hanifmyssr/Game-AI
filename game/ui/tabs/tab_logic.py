"""Tab 4: Materi 07: Logic & Knowledge Representation (Cozy Adventurer Journal Theme).

Menyajikan fakta sensorik (TELL), aturan logika proposisional CNF,
jejak inferensi pembuktian resolusi refutasi menghasilkan [], dan aksi ASK.
"""

from typing import Dict, Any, Optional
import pygame
from ...core import config
from ..components import draw_card, draw_badge_pill, draw_metric_tile, UIButton, render_fitted_text, fit_text_to_width
from ...logic.kb_rules import clause_to_str

MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1025)


def _clean_cnf_str(raw_s: str) -> str:
    """Format string CNF menjadi ringkas dan mudah dibaca tanpa overflow."""
    replacements = [
        ("AssignChaser_Kuro", "Chaser(K)"),
        ("AssignChaser_Shiro", "Chaser(S)"),
        ("AssignTightGuard_Shiro", "Guard(S)"),
        ("AssignTightGuard_Kuro", "Guard(K)"),
        ("AssignTightGuard_Oyen", "Guard(O)"),
        ("BroadcastAlarm_Shiro", "Alarm(S)"),
        ("BroadcastAlarm_Kuro", "Alarm(K)"),
        ("Alert_Kuro", "Alert(K)"),
        ("Alert_Shiro", "Alert(S)"),
        ("HasLootedItem_Player", "Loot(Bolu)"),
        ("ChestOpened_A", "Open(Peti_A)"),
        ("ChestOpened_B", "Open(Peti_B)"),
        ("ChestOpened_C", "Open(Peti_C)"),
        ("Unopened_A", "Safe(A)"),
        ("Unopened_B", "Safe(B)"),
        ("Unopened_C", "Safe(C)"),
        ("∨", " v "),
    ]
    s = raw_s
    for old, new in replacements:
        s = s.replace(old, new)
    return s


class TabLogic:
    """Tab 4: Knowledge Base & Propositional Logic Reasoning."""

    def __init__(self, rect: pygame.Rect, fonts: Dict[str, pygame.font.Font], app_ref: Any):
        self.rect = pygame.Rect(rect)
        self.fonts = fonts
        self.app = app_ref

        btn_w = self.rect.width - 24
        self.btn_proof_modal = UIButton(
            pygame.Rect(self.rect.x + 12, self.rect.y + 540, btn_w, 38),
            "Buka Pembuktian Resolusi [T]",
            fonts.get("sm", pygame.font.Font(None, 16)),
            on_click=self._on_open_proof,
            bg_color=(242, 235, 222),
            hover_color=(255, 252, 245),
            active_color=(230, 220, 205),
            border_color=config.COLOR_CARD_BORDER,
            icon=None,
        )

    def resize(self, rect: pygame.Rect) -> None:
        self.rect = pygame.Rect(rect)

    def _on_open_proof(self) -> None:
        if hasattr(self.app, "open_graph_modal"):
            self.app.open_graph_modal("LOGIC")

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.btn_proof_modal.handle_event(event):
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

        # 1. KARTU PERSEPSI SENSORIK (TELL)
        card_tell_h = 108
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_tell_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        lbl_tell = font_tiny.render("PERSEPSI SENSORIK TERBARU (TELL):", True, config.COLOR_ACCENT_GOLD)
        surface.blit(lbl_tell, (cx + 12, cy + 8))

        mgr = getattr(self.app, "inter_npc_manager", None)
        opened = [f"Peti-{i+1}" for i, c in enumerate(getattr(self.app, "chests", [])) if c.get("opened", False)]
        if mgr and mgr.latest_percept_event and "membuka" in mgr.latest_percept_event.lower():
            tell_event = mgr.latest_percept_event
            tell_badge = "EVENT BARU TERDETEKSI"
            b_col = config.COLOR_STATUS_DANGER
            b_bg = (255, 240, 240)
        elif opened:
            tell_event = f"Bolu membuka: {', '.join(opened)}"
            tell_badge = "EVENT BARU TERDETEKSI"
            b_col = config.COLOR_STATUS_DANGER
            b_bg = (255, 240, 240)
        else:
            tell_event = "Semua 3 Peti Harta masih aman tersegel."
            tell_badge = "PATROLI STANDBY"
            b_col = config.COLOR_STATUS_SUCCESS
            b_bg = (235, 248, 238)

        badge_rect = pygame.Rect(cx + 12, cy + 28, card_w - 24, 24)
        draw_badge_pill(surface, badge_rect, tell_badge, b_bg, b_col, font_tiny)

        render_fitted_text(surface, font_tiny, tell_event, config.COLOR_TEXT_PRIMARY, (cx + 14, cy + 60), card_w - 28)

        kb_fact = f"Fakta TELL: ChestOpened({opened[-1] if opened else 'None'})"
        render_fitted_text(surface, font_tiny, kb_fact, config.COLOR_TEXT_SECONDARY, (cx + 14, cy + 82), card_w - 28)

        # 2. KARTU BASIS ATURAN LOGIKA (CNF RULES)
        cy += card_tell_h + 12
        card_cnf_h = 135
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_cnf_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        cnf_title = font_tiny.render("── BASIS ATURAN LOGIKA (CNF KB) ──", True, config.COLOR_TEXT_SECONDARY)
        surface.blit(cnf_title, (cx + (card_w - cnf_title.get_width()) // 2, cy + 6))

        if mgr and mgr.kb.rules_meta:
            cnf_rules = [(_clean_cnf_str(r["cnf_str"]), r["desc"]) for r in mgr.kb.rules_meta[:3]]
        else:
            cnf_rules = [
                ("R1: ~Open(A) v Alert(K)", "Kuro bertindak saat Peti A terusik"),
                ("R2: ~Alert(K) v Chaser(K)", "Penugasan mode pengejar agresif"),
                ("R3: ~Alert(K) v Guard(S)", "Shiro siaga menjaga peti tersisa"),
            ]

        ry = cy + 28
        inner_w = card_w - 20
        for rule_text, rule_desc in cnf_rules:
            r_rect = pygame.Rect(cx + 10, ry, inner_w, 30)
            draw_card(surface, r_rect, (250, 246, 238), border_color=(226, 216, 202), border_radius=4)
            render_fitted_text(surface, font_tiny, rule_text, config.COLOR_ACCENT_BLUE, (r_rect.x + 8, r_rect.y + 7), inner_w - 16)
            ry += 34

        # 3. KARTU INFERENSI RESOLUSI REFUTASI
        cy += card_cnf_h + 12
        card_res_h = 120
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_res_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        res_title = font_tiny.render("── JEJAK RESOLUSI REFUTASI ──", True, config.COLOR_TEXT_SECONDARY)
        surface.blit(res_title, (cx + (card_w - res_title.get_width()) // 2, cy + 6))

        if mgr and mgr.latest_steps:
            steps = []
            for idx, st in enumerate(mgr.latest_steps[-4:], start=1):
                lit = _clean_cnf_str(st.resolved_literal)
                res = "[] (KONTRADIKSI)" if len(st.resolvent) == 0 else _clean_cnf_str(clause_to_str(st.resolvent))
                steps.append((f"{idx}. {lit} ➔ {res}", "[]" in res))
        else:
            steps = [
                ("1. Query: ~Chaser(K) (Asumsi)", False),
                ("2. Resolusi R2: ~Alert(K)", False),
                ("3. Resolusi R1: ~Open(Peti_A)", False),
                ("4. Fakta TELL: [] (KONTRADIKSI)", True),
            ]

        sy = cy + 26
        for step_text, is_contra in steps:
            col = config.COLOR_STATUS_SUCCESS if is_contra else config.COLOR_TEXT_PRIMARY
            render_fitted_text(surface, font_tiny, step_text, col, (cx + 14, sy), card_w - 28)
            sy += 21

        # 4. KARTU KESIMPULAN AKSI (ASK RESULTS)
        cy += card_res_h + 12
        card_ask_h = 92
        draw_card(surface, pygame.Rect(cx, cy, card_w, card_ask_h), config.COLOR_CARD_BG,
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)

        ask_title = font_tiny.render("KESIMPULAN AKSI (ASK):", True, config.COLOR_ACCENT_GOLD)
        surface.blit(ask_title, (cx + 12, cy + 8))

        if mgr:
            kuro_role = "• Kuro -> MODE CHASER (Kejar Bolu)" if mgr.chaser_assigned else "• Kuro -> PATROLI TEBING UTARA"
            shiro_role = "• Shiro -> TIGHT GUARD (Jaga Peti 2)" if "Shiro" in mgr.guardians_assigned else "• Shiro -> PATROLI DERMAGA"
            oyen_role = "• Oyen -> TIGHT GUARD (Jaga Peti 3)" if "Oyen" in mgr.guardians_assigned else "• Oyen -> PATROLI HUTAN"
        else:
            kuro_role = "• Kuro -> MODE CHASER (Kejar Bolu)" if opened else "• Kuro -> PATROLI TEBING UTARA"
            shiro_role = "• Shiro -> TIGHT GUARD (Jaga Peti 2)" if opened else "• Shiro -> PATROLI DERMAGA"
            oyen_role = "• Oyen -> TIGHT GUARD (Jaga Peti 3)" if opened else "• Oyen -> PATROLI HUTAN"

        render_fitted_text(surface, font_tiny, kuro_role, config.COLOR_STATUS_DANGER if opened else config.COLOR_TEXT_PRIMARY, (cx + 14, cy + 28), card_w - 28)
        render_fitted_text(surface, font_tiny, shiro_role, config.COLOR_ACCENT_BLUE, (cx + 14, cy + 46), card_w - 28)
        render_fitted_text(surface, font_tiny, oyen_role, config.COLOR_ACCENT_GOLD, (cx + 14, cy + 64), card_w - 28)

        cy += card_ask_h + 12
        self.btn_proof_modal.rect = pygame.Rect(cx, cy, card_w, 38)
        self.btn_proof_modal.draw(surface)

    def draw_popups(self, surface: pygame.Surface) -> None:
        pass
