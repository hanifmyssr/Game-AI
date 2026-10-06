"""Modul Evaluasi Tingkat Kesulitan (Difficulty Evaluator) untuk Tahap 3 & 4.

Menyediakan fungsi objektif untuk menghitung estimated difficulty score
dari konfigurasi tim NPC, serta fitness function untuk Local Search.
"""

from typing import Dict, Any, Optional
from . import config


def get_default_weights() -> Dict[str, float]:
    return dict(config.DEFAULT_DIFFICULTY_WEIGHTS)


def calculate_difficulty_breakdown(npc_config: Dict[str, Any]) -> Dict[str, float]:
    """Menghitung nilai ternormalisasi [0.0, 1.0] dari setiap komponen penyusun difficulty."""
    members = npc_config.get("members", [])
    count = len(members)
    if count == 0:
        return {
            "norm_hp": 0.0,
            "norm_pot": 0.0,
            "norm_atk": 0.0,
            "norm_def": 0.0,
            "norm_count": 0.0,
            "norm_aggro": 0.0,
        }

    # Nilai maksimum teoretis untuk normalisasi (berdasarkan 3 NPC x nilai max domain)
    MAX_TOTAL_HP = 360.0       # 3 x 120
    MAX_TOTAL_POT = 9.0        # 3 x 3
    MAX_TOTAL_ATK = 45.0       # 3 x 15
    MAX_TOTAL_DEF = 18.0       # 3 x 6

    total_hp = sum(m.get("hp", 100) for m in members)
    total_pot = sum(m.get("potions", 2) for m in members)
    total_atk = sum(m.get("atk_bonus", 0) for m in members)
    total_def = sum(m.get("def_bonus", 0) for m in members)

    # Bobot agresivitas profil evaluasi
    aggro_map = {
        "AGGRESSIVE": 1.0,
        "BALANCED": 0.5,
        "DEFENSIVE": 0.2,
    }
    avg_aggro = sum(aggro_map.get(m.get("eval_profile", "BALANCED"), 0.5) for m in members) / count

    return {
        "norm_hp": min(1.0, total_hp / MAX_TOTAL_HP),
        "norm_pot": min(1.0, total_pot / MAX_TOTAL_POT),
        "norm_atk": min(1.0, total_atk / MAX_TOTAL_ATK),
        "norm_def": min(1.0, total_def / MAX_TOTAL_DEF),
        "norm_count": min(1.0, count / 3.0),
        "norm_aggro": avg_aggro,
    }


def calculate_difficulty_score(
    npc_config: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None
) -> float:
    """Menghitung skor kesulitan (skala 0.0 - 1.0) dari sebuah konfigurasi tim NPC.
    
    0.0 = Sangat Mudah (1 NPC lemah, tanpa potion, pasif)
    0.55 = Target "Fun Zone" (Tantangan seimbang, adil)
    1.0 = Sangat Sulit (3 NPC stat maksimum, agresif)
    """
    if weights is None:
        weights = get_default_weights()

    bd = calculate_difficulty_breakdown(npc_config)

    score = (
        weights.get("w_hp", 0.25) * bd["norm_hp"]
        + weights.get("w_pot", 0.15) * bd["norm_pot"]
        + weights.get("w_atk", 0.20) * bd["norm_atk"]
        + weights.get("w_def", 0.10) * bd["norm_def"]
        + weights.get("w_count", 0.20) * bd["norm_count"]
        + weights.get("w_aggro", 0.10) * bd["norm_aggro"]
    )
    return round(max(0.0, min(1.0, score)), 4)


def calculate_fitness(
    npc_config: Dict[str, Any],
    target: float = config.TARGET_DIFFICULTY_DEFAULT,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """Fitness function untuk Local Search.
    
    Nilai fitness = -|difficulty_score - target_difficulty|
    Nilai tertinggi adalah 0.0 (persis di target difficulty).
    """
    diff_score = calculate_difficulty_score(npc_config, weights)
    return -abs(diff_score - target)
