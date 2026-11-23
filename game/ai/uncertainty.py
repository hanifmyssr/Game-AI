"""Materi 09: Decision Under Uncertainty — Jembatan Antarpulau Ambruk & Bayesian Belief Update.

Mengimplementasikan:
1. Hidden State (RAPUH vs KOKOH) untuk 3 jembatan pintas antarpulau (Atas, Kiri, Bawah);
   jembatan pulau tengah tetap aman 0% ambruk (anti soft-lock).
2. Sequential Bayesian Belief Update melalui aksi 'Cek Jembatan' (sensor ber-noise).
3. Perhitungan Shannon Entropy H(S) dan Expected Cost / Decision Theory.
"""

import math
import random
from typing import Dict, List, Any, Tuple, Optional

WEATHER_CERAH = "CERAH"
WEATHER_HUJAN = "HUJAN"

OBS_CRACK = "DERIT_RETAK"
OBS_SOLID = "TERLIHAT_KOKOH"

OBS_LABELS: Dict[str, str] = {
    OBS_CRACK: "Derit Retak (Bahaya)",
    OBS_SOLID: "Terlihat Kokoh",
}

BRIDGE_KEYS: Tuple[str, ...] = ("atas", "kiri", "bawah")
BRIDGE_NAMES: Dict[str, str] = {
    "atas": "Jembatan Atas",
    "kiri": "Jembatan Kiri",
    "bawah": "Jembatan Bawah",
}


def manhattan_dist(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """Menghitung jarak Manhattan antar dua koordinat grid."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class BridgeUncertaintyEngine:
    """Engine Materi 09 untuk 3 Jembatan Pintas Antarpulau (Bayes' Rule + Expected Cost)."""

    def __init__(self, rain_prior: float = 0.40, sensor_accuracy: float = 0.85) -> None:
        self.clear_prior: float = 0.10
        self.rain_prior: float = max(0.05, min(0.95, float(rain_prior)))
        self.sensor_accuracy: float = max(0.65, min(0.95, float(sensor_accuracy)))
        self.max_inspections: int = 4

        self.weather_state: str = WEATHER_CERAH
        self.selected_bridge: str = "atas"
        self.bridges: Dict[str, Dict[str, Any]] = {}
        self.reset()

    @property
    def active_prior(self) -> float:
        return self.rain_prior if self.weather_state == WEATHER_HUJAN else self.clear_prior

    def _cur(self, key: Optional[str] = None) -> Dict[str, Any]:
        k = key if key in self.bridges else self.selected_bridge
        return self.bridges[k]

    @property
    def posterior(self) -> float:
        return self._cur()["posterior"]

    @property
    def true_fragile(self) -> bool:
        return self._cur()["true_fragile"]

    @true_fragile.setter
    def true_fragile(self, val: bool) -> None:
        self._cur()["true_fragile"] = bool(val)

    @property
    def collapsed(self) -> bool:
        return self._cur()["collapsed"]

    @property
    def observations(self) -> List[Dict[str, Any]]:
        return self._cur()["observations"]

    @property
    def last_obs(self) -> str:
        return self._cur()["last_obs"]

    @property
    def bridge_status(self) -> str:
        return self.get_bridge_status(self.selected_bridge)

    def get_bridge_status(self, key: str) -> str:
        b = self._cur(key)
        if b["collapsed"]:
            return "AMBRUK"
        if b["posterior"] >= 0.50:
            return "RAWAN"
        return "UTUH"

    def select_bridge(self, key: str) -> None:
        if key in self.bridges:
            self.selected_bridge = key

    def reset(self) -> None:
        self.weather_state = WEATHER_CERAH
        self.selected_bridge = "atas"
        self.bridges = {k: self._new_bridge_state() for k in BRIDGE_KEYS}

    def _new_bridge_state(self) -> Dict[str, Any]:
        p = self.active_prior
        return {
            "posterior": p,
            "true_fragile": random.random() < p,
            "collapsed": False,
            "observations": [],
            "last_obs": "-",
        }

    def _reset_uncollapsed_beliefs(self) -> None:
        p = self.active_prior
        for k, b in self.bridges.items():
            if not b["collapsed"]:
                b["posterior"] = p
                b["true_fragile"] = random.random() < p
                b["observations"].clear()
                b["last_obs"] = "-"

    def set_weather(self, new_weather: str) -> None:
        if new_weather not in (WEATHER_CERAH, WEATHER_HUJAN):
            return
        self.weather_state = new_weather
        self._reset_uncollapsed_beliefs()

    def toggle_weather(self) -> str:
        nxt = WEATHER_HUJAN if self.weather_state == WEATHER_CERAH else WEATHER_CERAH
        self.set_weather(nxt)
        return nxt

    def set_rain_prior(self, val: float) -> None:
        self.rain_prior = max(0.05, min(0.95, float(val)))
        if self.weather_state == WEATHER_HUJAN:
            self._reset_uncollapsed_beliefs()

    def set_sensor_accuracy(self, val: float) -> None:
        self.sensor_accuracy = max(0.65, min(0.95, float(val)))

    def inspect_bridge(self, key: Optional[str] = None) -> Dict[str, Any]:
        """Melakukan 1 kali observasi ber-noise pada jembatan target & memperbarui Posterior Bayes."""
        k = key if key in self.bridges else self.selected_bridge
        b = self.bridges[k]
        if b["collapsed"]:
            return {
                "updated": False,
                "bridge": k,
                "reason": f"{BRIDGE_NAMES[k]} sudah ambruk.",
                "posterior": 1.0,
                "entropy": 0.0,
                "obs": b["last_obs"],
            }
        if len(b["observations"]) >= self.max_inspections:
            return {
                "updated": False,
                "bridge": k,
                "reason": f"Batas {self.max_inspections}x inspeksi tercapai.",
                "posterior": b["posterior"],
                "entropy": self.get_entropy(k),
                "obs": b["last_obs"],
            }

        acc = self.sensor_accuracy
        if b["true_fragile"]:
            obs = OBS_CRACK if random.random() < acc else OBS_SOLID
        else:
            obs = OBS_SOLID if random.random() < acc else OBS_CRACK

        prior_before = b["posterior"]
        if obs == OBS_CRACK:
            p_e_fragile, p_e_solid = acc, 1.0 - acc
        else:
            p_e_fragile, p_e_solid = 1.0 - acc, acc

        num = p_e_fragile * prior_before
        den = num + p_e_solid * (1.0 - prior_before)
        posterior_after = num / den if den > 1e-12 else prior_before
        b["posterior"] = max(0.001, min(0.999, posterior_after))
        b["last_obs"] = OBS_LABELS.get(obs, obs)

        ent = self.get_entropy(k)
        rec = {
            "step": len(b["observations"]) + 1,
            "obs": obs,
            "obs_label": b["last_obs"],
            "prior_before": prior_before,
            "posterior_after": b["posterior"],
            "entropy": ent,
        }
        b["observations"].append(rec)
        return {
            "updated": True,
            "bridge": k,
            "obs": obs,
            "obs_label": b["last_obs"],
            "prior_before": prior_before,
            "posterior": b["posterior"],
            "entropy": ent,
            "step": rec["step"],
        }

    def try_cross_bridge(self, key: Optional[str] = None) -> Dict[str, Any]:
        """Dipanggil saat Bolu melangkah ke salah satu jembatan berisiko."""
        k = key if key in self.bridges else self.selected_bridge
        b = self.bridges[k]
        if b["collapsed"]:
            return {"collapsed": False, "already_collapsed": True, "bridge": k}
        if b["true_fragile"]:
            b["collapsed"] = True
            b["posterior"] = 1.0
            return {"collapsed": True, "already_collapsed": False, "bridge": k}
        return {"collapsed": False, "already_collapsed": False, "bridge": k}

    def repair_bridge(self, key: Optional[str] = None) -> Dict[str, Any]:
        """Memperbaiki jembatan yang ambruk / mereset kondisi jembatan terpilih untuk demo ulang."""
        k = key if key in self.bridges else self.selected_bridge
        b = self.bridges[k]
        was_collapsed = b["collapsed"]
        b["collapsed"] = False
        b["observations"].clear()
        b["last_obs"] = "-"
        b["posterior"] = self.active_prior
        b["true_fragile"] = random.random() < self.active_prior
        return {"repaired": True, "was_collapsed": was_collapsed, "bridge": k, "posterior": b["posterior"]}

    def get_entropy(self, key: Optional[str] = None) -> float:
        """Menghitung Shannon Entropy H(S) dalam bit."""
        b = self._cur(key)
        if b["collapsed"]:
            return 0.0
        p = max(1e-9, min(1.0 - 1e-9, b["posterior"]))
        return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))

    def get_expected_cost_comparison(
        self,
        key: Optional[str] = None,
        shortcut_cost: float = 12.0,
        safe_detour_cost: float = 28.0,
        item_penalty_cost: float = 20.0,
    ) -> Dict[str, Any]:
        """Menghitung Expected Cost Jalur Jembatan vs Jalur Aman Memutar Lewat Pulau Tengah."""
        b = self._cur(key)
        if b["collapsed"]:
            return {
                "expected_upper": float("inf"),
                "safe_cost": safe_detour_cost,
                "recommend_detour": True,
                "recommend_text": "Wajib Memutar (Ambruk)",
            }
        p_fail = b["posterior"]
        expected_upper = p_fail * (safe_detour_cost + item_penalty_cost) + (1.0 - p_fail) * shortcut_cost
        recommend_detour = expected_upper > safe_detour_cost
        return {
            "expected_upper": expected_upper,
            "safe_cost": safe_detour_cost,
            "recommend_detour": recommend_detour,
            "recommend_text": "Disarankan Memutar" if recommend_detour else "Aman Dilintasi",
        }
