"""Overlay GUI Visualizer Modul 07: Logic & Knowledge Representation (Shortcut [K]).

Menyajikan transparansi penalaran logika proposisional secara akademis:
1. Fakta Sensorik Aktif (TELL)
2. Aturan Basis Pengetahuan (CNF Rules)
3. Jejak Inferensi Resolusi Refutasi menghasilkan [] (Kontradiksi)
4. Kesimpulan Aksi (ASK) & Tombol Pohon Resolusi [T]
"""

from typing import Dict, Any, Optional, List
import pygame
from ..core import config
from .components import draw_card, draw_badge_pill, UIButton, render_fitted_text, fit_text_to_width
from ..logic.kb_rules import clause_to_str


def _clean_cnf(raw_s: str) -> str:
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


class LogicOverlay:
    """Layar overlay visualizer logika proposisional formal."""

    def __init__(self, fonts: Dict[str, pygame.font.Font], app_ref: Any = None):
        self.fonts = fonts
        self.app = app_ref
        self.visible = False

        # Tombol Buka Pohon Resolusi
        self.btn_tree = UIButton(
            pygame.Rect(0, 0, 260, 36),
            "Buka Pohon Resolusi [T]",
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

    def toggle(self) -> None:
        """Membuka atau menutup overlay visualizer logika."""
        self.visible = not self.visible

    def _on_open_tree(self) -> None:
        if self.app and hasattr(self.app, "open_graph_modal"):
            self.visible = False
            self.app.open_graph_modal("LOGIC")

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.visible:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_k):
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
        title_surf = font_title.render("MATERI 07: LOGIC & RESOLUSI REFUTASI", True, (45, 32, 22))
        surface.blit(title_surf, (hdr_rect.x + 14, hdr_rect.y + 9))

        badge_sub = font_tiny.render("Membuktikan KB |= Query via Empty Clause []", True, config.COLOR_ACCENT_GOLD)
        surface.blit(badge_sub, (hdr_rect.right - badge_sub.get_width() - 14, hdr_rect.y + 13))

        # Data Sumber
        mgr = getattr(self.app, "inter_npc_manager", None)
        facts = list(mgr.kb.facts) if mgr else ["Unopened_B", "Unopened_C", "HasLootedItem_Player"]
        rules = mgr.kb.rules_meta if mgr else []
        steps = mgr.latest_steps if mgr else []
        proof_sum = mgr.latest_proof_summary if mgr else None

        # 3. KONTEN KIRI: FAKTA SENSORIK (TELL) & BASIS ATURAN (CNF)
        left_w = (mw - 56) // 2
        col1_x = mx + 20
        col2_x = col1_x + left_w + 16
        content_y = my + 72

        # A. Fakta Sensorik (TELL)
        tell_card_h = 145
        draw_card(surface, pygame.Rect(col1_x, content_y, left_w, tell_card_h), (255, 255, 255),
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)
        surface.blit(font_bubble.render("Fakta Sensorik Terkini (TELL)", True, config.COLOR_ACCENT_GOLD), (col1_x + 12, content_y + 8))

        percept_txt = mgr.latest_percept_event if mgr else "Semua 3 Peti Harta masih aman tersegel."
        draw_badge_pill(surface, pygame.Rect(col1_x + 12, content_y + 32, left_w - 24, 24),
                        "EVENT AKTIF" if "membuka" in percept_txt.lower() else "STANDBY PATROLI",
                        (255, 240, 240) if "membuka" in percept_txt.lower() else (235, 248, 238),
                        config.COLOR_STATUS_DANGER if "membuka" in percept_txt.lower() else config.COLOR_STATUS_SUCCESS,
                        font_tiny)

        surface.blit(font_tiny.render(percept_txt, True, config.COLOR_TEXT_PRIMARY), (col1_x + 14, content_y + 64))

        fy = content_y + 88
        facts_preview = [f"• {f}" for f in facts[:3]]
        for f_line in facts_preview:
            render_fitted_text(surface, font_tiny, f_line, config.COLOR_TEXT_SECONDARY, (col1_x + 14, fy), left_w - 28)
            fy += 17

        # B. Aturan CNF (KB Rules)
        cnf_card_y = content_y + tell_card_h + 12
        cnf_card_h = mh - (cnf_card_y - my) - 64
        draw_card(surface, pygame.Rect(col1_x, cnf_card_y, left_w, cnf_card_h), (255, 255, 255),
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)
        surface.blit(font_bubble.render("Aturan Logika Proposisional (CNF KB)", True, config.COLOR_TEXT_PRIMARY), (col1_x + 12, cnf_card_y + 8))

        ry = cnf_card_y + 34
        display_rules = rules[:4] if rules else [
            {"id": "R1", "cnf_str": "(Alert_Kuro v ~ChestOpened_A)", "name": "Deteksi Peti A"},
            {"id": "R2", "cnf_str": "(~Alert_Kuro v AssignChaser_Kuro)", "name": "Tugaskan Pemburu"},
            {"id": "R3", "cnf_str": "(~AssignChaser_Kuro v BroadcastAlarm_Shiro)", "name": "Alarm Sekutu"},
            {"id": "R4", "cnf_str": "(AssignTightGuard_Shiro v ~BroadcastAlarm_Shiro)", "name": "Kunci Peti B"},
        ]
        inner_box_w = left_w - 20
        for r_item in display_rules:
            r_rect = pygame.Rect(col1_x + 10, ry, inner_box_w, 48)
            draw_card(surface, r_rect, (250, 246, 238), border_color=(226, 216, 202), border_radius=6)
            render_fitted_text(surface, font_tiny, f"[{r_item['id']}] {r_item.get('name', '')}", config.COLOR_ACCENT_GOLD, (r_rect.x + 8, r_rect.y + 4), inner_box_w - 16)
            clean_str = _clean_cnf(r_item['cnf_str'])
            render_fitted_text(surface, font_tiny, clean_str, config.COLOR_ACCENT_BLUE, (r_rect.x + 8, r_rect.y + 24), inner_box_w - 16)
            ry += 54

        # 4. KONTEN KANAN: JEJAK RESOLUSI REFUTASI & KESIMPULAN (ASK)
        right_w = left_w
        res_card_h = 240
        draw_card(surface, pygame.Rect(col2_x, content_y, right_w, res_card_h), (255, 255, 255),
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)
        surface.blit(font_bubble.render("Jejak Pembuktian Resolusi Refutasi", True, config.COLOR_STATUS_SUCCESS), (col2_x + 12, content_y + 8))

        q_name = proof_sum.get("query", "AssignChaser_Kuro") if proof_sum else "AssignChaser_Kuro"
        render_fitted_text(surface, font_tiny, f"Query: {_clean_cnf(q_name)} | Asumsi: ~{_clean_cnf(q_name)}", config.COLOR_ACCENT_GOLD, (col2_x + 14, content_y + 32), right_w - 28)

        step_y = content_y + 54
        display_steps = steps[-5:] if steps else []
        if display_steps:
            for s_idx, step in enumerate(display_steps, start=1):
                res_str = "[] (KLAUSA KOSONG)" if len(step.resolvent) == 0 else _clean_cnf(clause_to_str(step.resolvent))
                col_txt = config.COLOR_STATUS_DANGER if "[]" in res_str else config.COLOR_TEXT_PRIMARY
                lit_str = _clean_cnf(step.resolved_literal)
                render_fitted_text(surface, font_tiny, f"• Step {s_idx} ({lit_str}) ➔ {res_str}", col_txt, (col2_x + 14, step_y), right_w - 28)
                desc_str = _clean_cnf(step.description)
                render_fitted_text(surface, font_tiny, f"  ↳ {desc_str}", config.COLOR_TEXT_SECONDARY, (col2_x + 14, step_y + 16), right_w - 28)
                step_y += 34
        else:
            render_fitted_text(surface, font_tiny, "Menunggu pemicu: Buka Peti [E] di map untuk memicu inferensi.", config.COLOR_TEXT_SECONDARY, (col2_x + 14, step_y + 30), right_w - 28)

        # Kotak Kontradiksi / Status Refutasi
        status_box_y = content_y + res_card_h + 12
        status_box_h = 80
        draw_card(surface, pygame.Rect(col2_x, status_box_y, right_w, status_box_h), (242, 248, 242) if steps else (248, 244, 238),
                  border_color=config.COLOR_STATUS_SUCCESS if steps else config.COLOR_CARD_BORDER, border_radius=8)
        surface.blit(font_bubble.render("Status Refutasi:", True, (45, 35, 25)), (col2_x + 12, status_box_y + 8))

        if steps:
            render_fitted_text(surface, font_bubble, "■ KONTRADIKSI DITEMUKAN: [] EMPTY CLAUSE", config.COLOR_STATUS_DANGER, (col2_x + 14, status_box_y + 30), right_w - 28)
            render_fitted_text(surface, font_tiny, "Terbukti formal: KB |= AssignChaser(Kuro) bernilai TRUE", config.COLOR_STATUS_SUCCESS, (col2_x + 14, status_box_y + 54), right_w - 28)
        else:
            render_fitted_text(surface, font_tiny, "Kondisi statis aman. KB konsisten tanpa kontradiksi.", config.COLOR_TEXT_SECONDARY, (col2_x + 14, status_box_y + 34), right_w - 28)

        # Kesimpulan Aksi (ASK)
        ask_card_y = status_box_y + status_box_h + 12
        ask_card_h = mh - (ask_card_y - my) - 64
        draw_card(surface, pygame.Rect(col2_x, ask_card_y, right_w, ask_card_h), (255, 255, 255),
                  border_color=config.COLOR_CARD_BORDER, border_radius=8)
        surface.blit(font_bubble.render("Kesimpulan Aksi NPC (ASK)", True, config.COLOR_ACCENT_GOLD), (col2_x + 12, ask_card_y + 8))

        chaser = mgr.chaser_assigned if mgr else None
        guardians = mgr.guardians_assigned if mgr else []
        kuro_txt = f"• Kuro: MODE CHASER (Kejar Bolu)" if chaser else "• Kuro: Siaga Patroli Tebing"
        shiro_txt = f"• Shiro: TIGHT GUARD (Kunci Peti B)" if "Shiro" in guardians else "• Shiro: Siaga Patroli Dermaga"
        oyen_txt = f"• Oyen: TIGHT GUARD (Kunci Peti C)" if "Oyen" in guardians else "• Oyen: Siaga Patroli Hutan"
        render_fitted_text(surface, font_tiny, kuro_txt, config.COLOR_STATUS_DANGER if chaser else config.COLOR_TEXT_PRIMARY, (col2_x + 14, ask_card_y + 30), right_w - 28)
        render_fitted_text(surface, font_tiny, shiro_txt, config.COLOR_ACCENT_BLUE, (col2_x + 14, ask_card_y + 48), right_w - 28)
        render_fitted_text(surface, font_tiny, oyen_txt, config.COLOR_ACCENT_GOLD, (col2_x + 14, ask_card_y + 66), right_w - 28)

        # 5. Bottom Action Ribbon
        btn_y = my + mh - 48
        self.btn_tree.rect = pygame.Rect(mx + 20, btn_y, 250, 36)
        self.btn_tree.draw(surface)

        self.btn_close.rect = pygame.Rect(mx + mw - 130, btn_y, 110, 36)
        self.btn_close.draw(surface)

