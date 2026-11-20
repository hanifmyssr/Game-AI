"""Materi 09: Decision Under Uncertainty — Bayesian Belief Filtering (Sonar Relik).

Mengimplementasikan filter probabilistik Bayes pada grid peta untuk melacak
lokasi Relik Tersembunyi menggunakan sinyal jarak ber-noise.
"""

import math
import random
from typing import Dict, List, Optional, Tuple, Any

SIGNAL_VERY_CLOSE = "SANGAT DEKAT"
SIGNAL_NEAR = "DEKAT"
SIGNAL_MEDIUM = "SEDANG"
SIGNAL_FAR = "JAUH"

SIGNALS: Tuple[str, ...] = (
    SIGNAL_VERY_CLOSE,
    SIGNAL_NEAR,
    SIGNAL_MEDIUM,
    SIGNAL_FAR,
)


def manhattan_dist(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def band_for_distance(dist: int) -> str:
    if dist <= 4:
        return SIGNAL_VERY_CLOSE
    if dist <= 10:
        return SIGNAL_NEAR
    if dist <= 18:
        return SIGNAL_MEDIUM
    return SIGNAL_FAR


class BayesianRelicSonar:
    """Bayesian Belief Filter untuk melacak Relik Tersembunyi di grid peta."""

    def __init__(self, walkable_cells: List[Tuple[int, int]], sensor_accuracy: float = 0.82):
        self.walkable_cells: List[Tuple[int, int]] = list(walkable_cells)
        self.sensor_accuracy: float = max(0.55, min(0.98, float(sensor_accuracy)))
        self.belief: Dict[Tuple[int, int], float] = {}
        self.relic_pos: Optional[Tuple[int, int]] = None
        self.scan_count: int = 0
        self.last_signal: Optional[str] = None
        self.last_true_band: Optional[str] = None
        self.last_is_noisy: bool = False
        self.last_player_pos: Optional[Tuple[int, int]] = None
        self.history: List[Dict[str, Any]] = []
        self.found: bool = False
        self.heatmap_visible: bool = True
        self.reset()

    def reset(
        self,
        walkable_cells: Optional[List[Tuple[int, int]]] = None,
        relic_pos: Optional[Tuple[int, int]] = None,
    ) -> None:
        if walkable_cells is not None:
            self.walkable_cells = list(walkable_cells)
        n = len(self.walkable_cells)
        if n > 0:
            uniform_p = 1.0 / float(n)
            self.belief = {cell: uniform_p for cell in self.walkable_cells}
        else:
            self.belief = {}
        self.relic_pos = relic_pos
        self.scan_count = 0
        self.last_signal = None
        self.last_true_band = None
        self.last_is_noisy = False
        self.last_player_pos = None
        self.history.clear()
        self.found = False

    def observation_likelihood(self, signal: str, dist: int) -> float:
        """Model observasi P(Sinyal | Jarak): error sensor hanya bergeser maksimal +-1 band."""
        true_band = band_for_distance(dist)
        idx_sig = SIGNALS.index(signal) if signal in SIGNALS else 0
        idx_true = SIGNALS.index(true_band)
        diff = abs(idx_sig - idx_true)
        acc = self.sensor_accuracy
        err = max(0.02, 1.0 - acc)
        if diff == 0:
            return acc
        if diff == 1:
            return err * 0.50
        return 0.015

    def _sample_noisy_signal(self, player_pos: Tuple[int, int]) -> Tuple[str, str, bool]:
        if not self.relic_pos:
            return SIGNAL_FAR, SIGNAL_FAR, False
        true_d = manhattan_dist(player_pos, self.relic_pos)
        true_band = band_for_distance(true_d)
        idx_true = SIGNALS.index(true_band)
        if random.random() < self.sensor_accuracy:
            return true_band, true_band, False
        neighbors = [i for i in (idx_true - 1, idx_true + 1) if 0 <= i < len(SIGNALS)]
        chosen_idx = random.choice(neighbors) if neighbors else idx_true
        chosen = SIGNALS[chosen_idx]
        return chosen, true_band, (chosen != true_band)

    def scan(self, player_pos: Tuple[int, int]) -> Dict[str, Any]:
        """Memancarkan sonar ber-noise dari player_pos dan memperbarui Belief via Bayes' Rule."""
        signal, true_band, is_noisy = self._sample_noisy_signal(player_pos)
        self.update_belief(player_pos, signal)
        self.scan_count += 1
        self.last_signal = signal
        self.last_true_band = true_band
        self.last_is_noisy = is_noisy
        self.last_player_pos = player_pos

        map_pos, map_prob = self.get_map_estimate()
        entropy = self.get_entropy()
        entry = {
            "scan_num": self.scan_count,
            "player_pos": player_pos,
            "signal": signal,
            "true_band": true_band,
            "is_noisy": is_noisy,
            "map_pos": map_pos,
            "map_prob": map_prob,
            "entropy": entropy,
        }
        self.history.append(entry)
        return entry

    def update_belief(self, player_pos: Tuple[int, int], signal: str) -> None:
        """P(X | e) <- alpha * P(e | X) * P(X) lalu normalisasi."""
        if not self.belief:
            return
        total = 0.0
        updated: Dict[Tuple[int, int], float] = {}
        for cell, prior_p in self.belief.items():
            if prior_p <= 0.0:
                updated[cell] = 0.0
                continue
            d = manhattan_dist(player_pos, cell)
            post = prior_p * self.observation_likelihood(signal, d)
            updated[cell] = post
            total += post

        if total > 0.0:
            inv = 1.0 / total
            for cell in updated:
                updated[cell] *= inv
        else:
            n = len(self.belief)
            inv_n = 1.0 / float(n) if n else 0.0
            for cell in updated:
                updated[cell] = inv_n

        self.belief = updated

    def get_map_estimate(self) -> Tuple[Optional[Tuple[int, int]], float]:
        """Mengembalikan koordinat dan probabilitas tertinggi (Maximum A Posteriori)."""
        if not self.belief:
            return None, 0.0
        best_cell = max(self.belief, key=self.belief.get)  # type: ignore[arg-type]
        return best_cell, self.belief[best_cell]

    def get_top_candidates(self, k: int = 3) -> List[Tuple[Tuple[int, int], float]]:
        if not self.belief:
            return []
        return sorted(self.belief.items(), key=lambda kv: kv[1], reverse=True)[:k]

    def get_entropy(self) -> float:
        """Entropi Shannon (bit): makin kecil berarti keyakinan lokasi Relik makin pasti."""
        if not self.belief:
            return 0.0
        h = 0.0
        for p in self.belief.values():
            if p > 1e-12:
                h -= p * math.log2(p)
        return h
