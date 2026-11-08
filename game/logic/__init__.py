"""Modul Materi 07: Logic & Knowledge Representation.

Berisi representasi basis pengetahuan proposisional formal (CNF clauses),
mesin inferensi resolusi refutasi mandiri (first-principles),
serta manajer koordinasi sensor-inferensi antar-NPC.
"""

from .kb_rules import KnowledgeBase, negate_literal, is_negative, complement
from .inference_engine import ResolutionRefutationEngine, ResolutionStep
from .inter_npc_manager import InterNPCManager

__all__ = [
    "KnowledgeBase",
    "negate_literal",
    "is_negative",
    "complement",
    "ResolutionRefutationEngine",
    "ResolutionStep",
    "InterNPCManager",
]

