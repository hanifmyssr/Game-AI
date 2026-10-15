"""Modul Local Search & Optimization untuk Konfigurasi Tim NPC (Tahap 3).

Mengimplementasikan:
1. Hill Climbing (Steepest Ascent)
2. Hill Climbing with Sideways Move
3. Hill Climbing with Random Restart
4. Simulated Annealing (SA)
5. Genetic Algorithm (GA)

Semua metode terintegrasi dengan CSP Solver sebagai filter validasi (hanya menghasilkan state legal).
"""

import copy
import math
import random
import time
from typing import Dict, List, Tuple, Any, Optional

from . import config
from .difficulty import calculate_difficulty_score, calculate_fitness
from .npc_config_csp import NPCConfigCSP


def get_adaptive_target_difficulty(player_context: Dict[str, Any]) -> float:
    """Menghitung target difficulty adaptif berdasarkan HP dan buff player."""
    php = player_context.get("player_hp", 100)
    patk = player_context.get("player_atk_bonus", 0)
    pdef = player_context.get("player_def_bonus", 0)
    hp_adj = (php - 100) / 250.0
    buff_adj = (patk + pdef) / 100.0
    return round(max(0.40, min(0.70, config.TARGET_DIFFICULTY_DEFAULT + hp_adj + buff_adj)), 4)


class NPCOptimizer:
    """Optimizer Konfigurasi Tim NPC berbasis Local Search."""

    def __init__(
        self,
        target_difficulty: float = config.TARGET_DIFFICULTY_DEFAULT,
        weights: Optional[Dict[str, float]] = None,
        csp_solver: Optional[NPCConfigCSP] = None,
    ):
        self.target_difficulty = target_difficulty
        self.weights = weights or config.DEFAULT_DIFFICULTY_WEIGHTS
        self.csp = csp_solver or NPCConfigCSP()

        # Riwayat iterasi & metrik
        self.history: List[Dict[str, Any]] = []
        self.stats = {
            "algorithm": "",
            "iterations": 0,
            "restarts": 0,
            "final_difficulty": 0.0,
            "final_fitness": 0.0,
            "time_ms": 0.0,
            "sideways_count": 0,
        }

    # ----------------------------------------------------------------------- #
    # Evaluasi State
    # ----------------------------------------------------------------------- #
    def evaluate(self, state: Dict[str, Any]) -> float:
        """Menghitung fitness dari state."""
        return calculate_fitness(state, self.target_difficulty, self.weights)

    def get_difficulty(self, state: Dict[str, Any]) -> float:
        return calculate_difficulty_score(state, self.weights)

    # ----------------------------------------------------------------------- #
    # Neighbour Generator (Hanya Menghasilkan State Legal Sesuai CSP)
    # ----------------------------------------------------------------------- #
    def generate_legal_neighbours(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Menghasilkan semua tetangga (neighbour) 1-langkah yang valid menurut CSP."""
        neighbours = []
        members = state.get("members", [])
        npc_count = len(members)

        # 1. Mutasi atribut per anggota
        for idx in range(npc_count):
            m = members[idx]

            # a. Ubah HP (+-10, +-20)
            for delta_hp in [-20, -10, 10, 20]:
                new_hp = m["hp"] + delta_hp
                if new_hp in config.DOMAIN_HP:
                    cand = copy.deepcopy(state)
                    cand["members"][idx]["hp"] = new_hp
                    if self.csp.validate_config(cand)[0]:
                        neighbours.append(cand)

            # b. Ubah Potion (+-1)
            for delta_pot in [-1, 1]:
                new_pot = m["potions"] + delta_pot
                if new_pot in config.DOMAIN_POTIONS:
                    cand = copy.deepcopy(state)
                    cand["members"][idx]["potions"] = new_pot
                    if self.csp.validate_config(cand)[0]:
                        neighbours.append(cand)

            # c. Ubah Atk Bonus
            for new_atk in config.DOMAIN_ATK_BONUS:
                if new_atk != m["atk_bonus"]:
                    cand = copy.deepcopy(state)
                    cand["members"][idx]["atk_bonus"] = new_atk
                    if self.csp.validate_config(cand)[0]:
                        neighbours.append(cand)

            # d. Ubah Def Bonus
            for new_def in config.DOMAIN_DEF_BONUS:
                if new_def != m["def_bonus"]:
                    cand = copy.deepcopy(state)
                    cand["members"][idx]["def_bonus"] = new_def
                    if self.csp.validate_config(cand)[0]:
                        neighbours.append(cand)

            # e. Ubah Eval Profile
            for new_eval in config.EVAL_PROFILES:
                if new_eval != m["eval_profile"]:
                    cand = copy.deepcopy(state)
                    cand["members"][idx]["eval_profile"] = new_eval
                    if self.csp.validate_config(cand)[0]:
                        neighbours.append(cand)

            # f. Ubah Char Type (jika memenuhi variasi unik)
            for new_ctype in config.CHAR_TYPES:
                if new_ctype != m["char_type"]:
                    cand = copy.deepcopy(state)
                    cand["members"][idx]["char_type"] = new_ctype
                    # Otomatis sesuaikan jika unary constraint butuh penyesuaian dasar
                    if new_ctype == "tank" and cand["members"][idx]["hp"] < 90:
                        cand["members"][idx]["hp"] = 90
                    if new_ctype == "ranger" and cand["members"][idx]["atk_bonus"] < 5:
                        cand["members"][idx]["atk_bonus"] = 5
                    if new_ctype == "assassin":
                        if cand["members"][idx]["atk_bonus"] < 10:
                            cand["members"][idx]["atk_bonus"] = 10
                        if cand["members"][idx]["hp"] > 90:
                            cand["members"][idx]["hp"] = 80
                    if new_ctype == "mage" and cand["members"][idx]["hp"] > 90:
                        cand["members"][idx]["hp"] = 80
                    if self.csp.validate_config(cand)[0]:
                        neighbours.append(cand)

        # 2. Mutasi jumlah NPC (+-1)
        if npc_count < 3:
            # Coba tambah 1 NPC
            available_types = [t for t in config.CHAR_TYPES if t not in [m["char_type"] for m in members]]
            if available_types:
                cand = copy.deepcopy(state)
                new_type = available_types[0]
                new_member = {
                    "char_type": new_type,
                    "hp": 90 if new_type == "tank" else (70 if new_type == "assassin" else 60),
                    "potions": 1,
                    "atk_bonus": 10 if new_type == "assassin" else (5 if new_type == "ranger" else 0),
                    "def_bonus": 0,
                    "eval_profile": "DEFENSIVE" if new_type == "tank" else ("AGGRESSIVE" if new_type == "assassin" else "BALANCED"),
                }
                cand["members"].append(new_member)
                cand["npc_count"] = len(cand["members"])
                if self.csp.validate_config(cand)[0]:
                    neighbours.append(cand)

        if npc_count > 1:
            # Coba kurangi 1 NPC
            for rm_idx in range(npc_count):
                cand = copy.deepcopy(state)
                cand["members"].pop(rm_idx)
                cand["npc_count"] = len(cand["members"])
                if self.csp.validate_config(cand)[0]:
                    neighbours.append(cand)

        return neighbours

    # ----------------------------------------------------------------------- #
    # 1. Hill Climbing Standar (Steepest Ascent)
    # ----------------------------------------------------------------------- #
    def hill_climbing(self, initial_state: Dict[str, Any], max_iterations: int = 50) -> Dict[str, Any]:
        """Hill Climbing murni (berhenti jika tidak ada tetangga dengan fitness strictly > current)."""
        current = copy.deepcopy(initial_state)
        current_fit = self.evaluate(current)
        self.history = [{"step": 0, "fitness": current_fit, "diff": self.get_difficulty(current)}]

        for step in range(1, max_iterations + 1):
            neighbours = self.generate_legal_neighbours(current)
            if not neighbours:
                break

            best_neighbour = max(neighbours, key=self.evaluate)
            best_fit = self.evaluate(best_neighbour)

            if best_fit > current_fit:
                current = best_neighbour
                current_fit = best_fit
                self.history.append({"step": step, "fitness": current_fit, "diff": self.get_difficulty(current)})
            else:
                # Local optimum tercapai
                break

        return current

    # ----------------------------------------------------------------------- #
    # 2. Hill Climbing with Sideways Move
    # ----------------------------------------------------------------------- #
    def hill_climbing_sideways(
        self,
        initial_state: Dict[str, Any],
        max_iterations: int = 100,
        max_sideways: int = 15
    ) -> Dict[str, Any]:
        """Hill Climbing dengan toleransi gerakan ke tetangga bernilai sama (mengatasi plateau)."""
        current = copy.deepcopy(initial_state)
        current_fit = self.evaluate(current)
        sideways_count = 0
        self.history = [{"step": 0, "fitness": current_fit, "diff": self.get_difficulty(current)}]

        for step in range(1, max_iterations + 1):
            neighbours = self.generate_legal_neighbours(current)
            if not neighbours:
                break

            # Acak urutan agar tidak stuck di siklus sideways yang sama
            random.shuffle(neighbours)
            best_neighbour = max(neighbours, key=self.evaluate)
            best_fit = self.evaluate(best_neighbour)

            if best_fit > current_fit:
                current = best_neighbour
                current_fit = best_fit
                sideways_count = 0
                self.history.append({"step": step, "fitness": current_fit, "diff": self.get_difficulty(current)})
            elif math.isclose(best_fit, current_fit, abs_tol=1e-5) and sideways_count < max_sideways:
                current = best_neighbour
                sideways_count += 1
                self.history.append({"step": step, "fitness": current_fit, "diff": self.get_difficulty(current), "sideways": True})
            else:
                break

        self.stats["sideways_count"] = sideways_count
        return current

    # ----------------------------------------------------------------------- #
    # 3. Hill Climbing with Random Restart
    # ----------------------------------------------------------------------- #
    def hill_climbing_random_restart(
        self,
        max_restarts: int = 5,
        max_iterations_per_run: int = 30
    ) -> Dict[str, Any]:
        """Hill Climbing dengan restart dari solusi acak legal CSP untuk menghindari local optima."""
        best_overall = None
        best_overall_fit = -float("inf")
        self.history = []

        for r in range(max_restarts):
            # Dapatkan solusi awal legal dari CSP secara acak
            count = random.choice([1, 2, 3])
            candidates = self.csp.solve(npc_count=count, max_solutions=1, shuffle=True)
            if not candidates:
                continue
            init_s = candidates[0]

            sol = self.hill_climbing_sideways(init_s, max_iterations=max_iterations_per_run, max_sideways=5)
            fit = self.evaluate(sol)

            if fit > best_overall_fit:
                best_overall = sol
                best_overall_fit = fit

            self.history.append({"restart": r + 1, "fitness": fit, "diff": self.get_difficulty(sol)})

        self.stats["restarts"] = max_restarts
        return best_overall or candidates[0]

    # ----------------------------------------------------------------------- #
    # 4. Simulated Annealing
    # ----------------------------------------------------------------------- #
    def simulated_annealing(
        self,
        initial_state: Dict[str, Any],
        initial_temp: float = config.SA_INITIAL_TEMP,
        cooling_rate: float = config.SA_COOLING_RATE,
        min_temp: float = config.SA_MIN_TEMP,
        max_iterations: int = 150
    ) -> Dict[str, Any]:
        """Simulated Annealing: Menerima gerakan buruk dengan probabilitas P = exp(delta / T)."""
        current = copy.deepcopy(initial_state)
        current_fit = self.evaluate(current)
        best = copy.deepcopy(current)
        best_fit = current_fit

        T = initial_temp
        step = 0
        self.history = [{"step": 0, "fitness": current_fit, "diff": self.get_difficulty(current), "temp": T}]

        while T > min_temp and step < max_iterations:
            step += 1
            neighbours = self.generate_legal_neighbours(current)
            if not neighbours:
                break

            candidate = random.choice(neighbours)
            candidate_fit = self.evaluate(candidate)
            delta = candidate_fit - current_fit

            # Jika lebih baik, terima selalu. Jika lebih buruk, terima dengan peluang exp(delta / T)
            if delta > 0:
                current = candidate
                current_fit = candidate_fit
            else:
                prob = math.exp(delta / max(0.001, T))
                if random.random() < prob:
                    current = candidate
                    current_fit = candidate_fit

            if current_fit > best_fit:
                best = copy.deepcopy(current)
                best_fit = current_fit

            T *= cooling_rate
            self.history.append({"step": step, "fitness": current_fit, "diff": self.get_difficulty(current), "temp": round(T, 3)})

        return best

    # ----------------------------------------------------------------------- #
    # 5. Genetic Algorithm
    # ----------------------------------------------------------------------- #
    def genetic_algorithm(
        self,
        population_size: int = config.GA_POPULATION_SIZE,
        generations: int = config.GA_GENERATIONS,
        mutation_rate: float = config.GA_MUTATION_RATE,
    ) -> Dict[str, Any]:
        """Algoritma Genetika dengan seleksi turnamen, crossover anggota tim, dan perbaikan CSP."""
        # 1. Inisialisasi populasi acak legal
        population = []
        for _ in range(population_size):
            cnt = random.choice([1, 2, 3])
            sols = self.csp.solve(npc_count=cnt, max_solutions=1)
            if sols:
                # Buat variasi awal dengan mutasi neighbour acak
                indiv = sols[0]
                neighs = self.generate_legal_neighbours(indiv)
                if neighs and random.random() < 0.7:
                    indiv = random.choice(neighs)
                population.append(indiv)

        if not population:
            # Fallback
            population = [self.csp.solve(npc_count=2, max_solutions=1)[0]]

        self.history = []

        for gen in range(generations):
            # Urutkan berdasarkan fitness
            population.sort(key=self.evaluate, reverse=True)
            best_gen = population[0]
            self.history.append({
                "gen": gen + 1,
                "best_fitness": self.evaluate(best_gen),
                "best_diff": self.get_difficulty(best_gen),
            })

            # Buat generasi baru (Elitisme: simpan 2 terbaik)
            new_pop = [copy.deepcopy(population[0]), copy.deepcopy(population[1])]

            while len(new_pop) < population_size:
                # Seleksi Turnamen
                p1 = self._tournament_select(population)
                p2 = self._tournament_select(population)

                # Crossover
                child = self._crossover(p1, p2)

                # Mutasi
                if random.random() < mutation_rate:
                    child = self._mutate(child)

                # Perbaikan/Validasi via CSP
                if self.csp.validate_config(child)[0]:
                    new_pop.append(child)
                else:
                    new_pop.append(copy.deepcopy(p1))

            population = new_pop

        population.sort(key=self.evaluate, reverse=True)
        return population[0]

    def _tournament_select(self, pop: List[Dict[str, Any]], k: int = 3) -> Dict[str, Any]:
        selected = random.sample(pop, min(k, len(pop)))
        return max(selected, key=self.evaluate)

    def _crossover(self, p1: Dict[str, Any], p2: Dict[str, Any]) -> Dict[str, Any]:
        """Crossover seragam pada level konfigurasi anggota tim."""
        m1 = p1.get("members", [])
        m2 = p2.get("members", [])
        child_count = random.choice([p1["npc_count"], p2["npc_count"]])
        child_members = []

        for i in range(child_count):
            gene_pool = []
            if i < len(m1):
                gene_pool.append(m1[i])
            if i < len(m2):
                gene_pool.append(m2[i])

            if gene_pool:
                child_members.append(copy.deepcopy(random.choice(gene_pool)))
            else:
                child_members.append(copy.deepcopy(random.choice(m1 if m1 else m2)))

        return {"npc_count": child_count, "members": child_members}

    def _mutate(self, individual: Dict[str, Any]) -> Dict[str, Any]:
        neighs = self.generate_legal_neighbours(individual)
        if neighs:
            return random.choice(neighs)
        return individual

    # ----------------------------------------------------------------------- #
    # High-Level Orchestrator
    # ----------------------------------------------------------------------- #
    def optimize(
        self,
        algorithm: str = "HILL_CLIMBING",
        initial_state: Optional[Dict[str, Any]] = None,
        player_context: Optional[Dict[str, Any]] = None,
        randomize_start: bool = False,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Menjalankan algoritma Local Search yang dipilih.
        
        Mengembalikan (best_config, stats_dict).
        """
        if player_context:
            php = player_context.get("player_hp", 100)
            patk = player_context.get("player_atk_bonus", 0)
            pdef = player_context.get("player_def_bonus", 0)
            # Adaptasi target difficulty dinamis berdasarkan kondisi player
            hp_adj = (php - 100) / 250.0
            buff_adj = (patk + pdef) / 100.0
            self.target_difficulty = max(0.40, min(0.70, config.TARGET_DIFFICULTY_DEFAULT + hp_adj + buff_adj))

        start_time = time.perf_counter()

        if initial_state is None:
            # Inisialisasi awal legal dari CSP (acak jika tombol re-roll digunakan)
            count_choice = random.choice([2, 3, 1]) if randomize_start else 2
            init_solutions = self.csp.solve(npc_count=count_choice, max_solutions=1, shuffle=randomize_start)
            if not init_solutions:
                init_solutions = self.csp.solve(npc_count=None, max_solutions=1, shuffle=randomize_start)
            initial_state = init_solutions[0] if init_solutions else {
                "npc_count": 1,
                "members": [{"char_type": "warrior", "hp": 100, "potions": 2, "atk_bonus": 0, "def_bonus": 0, "eval_profile": "BALANCED"}]
            }

        algo = algorithm.upper()
        if algo == "HILL_CLIMBING":
            best = self.hill_climbing(initial_state)
        elif algo == "SIDEWAYS":
            best = self.hill_climbing_sideways(initial_state)
        elif algo == "RANDOM_RESTART":
            best = self.hill_climbing_random_restart()
        elif algo == "SIMULATED_ANNEALING":
            best = self.simulated_annealing(initial_state)
        elif algo == "GENETIC_ALGORITHM":
            best = self.genetic_algorithm()
        else:
            best = self.hill_climbing(initial_state)

        elapsed = (time.perf_counter() - start_time) * 1000.0
        final_diff = self.get_difficulty(best)
        final_fit = self.evaluate(best)

        self.stats = {
            "algorithm": algo,
            "iterations": len(self.history),
            "final_difficulty": final_diff,
            "final_fitness": round(final_fit, 4),
            "time_ms": round(elapsed, 2),
            "distance_to_target": round(abs(final_diff - self.target_difficulty), 4),
        }

        return best, self.stats
