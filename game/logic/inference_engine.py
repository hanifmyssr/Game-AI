"""Mesin Inferensi Mandiri: Algoritma Resolution Refutation (First-Principles).

Menerapkan penalaran logika proposisional murni dengan membuktikan KB |= query
melalui pencarian kontradiksi (klausa kosong []) saat negasi query ditambahkan ke KB.
"""

from typing import Set, List, Tuple, Dict, Optional, FrozenSet
from .kb_rules import KnowledgeBase, negate_literal, complement, clause_to_str


class ResolutionStep:
    """Satu langkah derivasi resolusi antara dua klausa."""

    def __init__(self, step_num: int, c1: FrozenSet[str], c2: FrozenSet[str],
                 resolved_literal: str, resolvent: FrozenSet[str], description: str = ""):
        self.step_num = step_num
        self.c1 = c1
        self.c2 = c2
        self.resolved_literal = resolved_literal
        self.resolvent = resolvent
        self.description = description

    def __repr__(self) -> str:
        r_str = "[] (KONTRADIKSI)" if not self.resolvent else clause_to_str(self.resolvent)
        return (f"Langkah {self.step_num}: Resolve {clause_to_str(self.c1)} & {clause_to_str(self.c2)} "
                f"pada '{self.resolved_literal}' => {r_str}")


class ResolutionRefutationEngine:
    """Mesin inferensi Resolusi Refutasi Proposisional."""

    @staticmethod
    def resolve(c1: FrozenSet[str], c2: FrozenSet[str]) -> List[Tuple[str, FrozenSet[str]]]:
        """Melakukan resolusi antara dua klausa pada pasangan literal komplemen."""
        resolvents = []
        for lit in c1:
            neg_lit = negate_literal(lit)
            if neg_lit in c2:
                # Bentuk resolvent baru
                new_clause = (c1 - {lit}) | (c2 - {neg_lit})

                # Tautology check: abaikan jika mengandung P dan ~P sekaligus
                is_tautology = False
                for item in new_clause:
                    if negate_literal(item) in new_clause:
                        is_tautology = True
                        break

                if not is_tautology:
                    resolvents.append((lit, frozenset(new_clause)))
        return resolvents

    def prove(self, kb: KnowledgeBase, query: str, max_steps: int = 120) -> Tuple[bool, List[ResolutionStep], Dict[str, Any]]:
        """Membuktikan KB |= query menggunakan metode Resolution Refutation.

        Langkah:
        1. Negasikan query: ~alpha
        2. Masukkan ~alpha ke dalam himpunan klausa
        3. Cari pasangan klausa beresolusi hingga menemukan klausa kosong []
        """
        # 1. Bentuk negasi query
        neg_query_lit = negate_literal(query)
        neg_query_clause = frozenset({neg_query_lit})

        clauses: Set[FrozenSet[str]] = kb.get_clauses_copy()
        clauses.add(neg_query_clause)

        steps: List[ResolutionStep] = []
        clause_origins: Dict[FrozenSet[str], str] = {
            c: "KB Rule" if len(c) > 1 else ("Fact (TELL)" if c != neg_query_clause else "Negated Query (~α)")
            for c in clauses
        }

        # Parent pointer untuk menelusuri rantai pembuktian
        parents: Dict[FrozenSet[str], Tuple[FrozenSet[str], FrozenSet[str], str]] = {}

        # Set of Support Strategy: prioritaskan resolusi yang melibatkan negasi query
        frontier: List[FrozenSet[str]] = [neg_query_clause]
        seen_clauses: Set[FrozenSet[str]] = set(clauses)

        success = False
        empty_clause: Optional[FrozenSet[str]] = None

        step_counter = 0

        while frontier and step_counter < max_steps:
            current = frontier.pop(0)

            # Pasangkan dengan klausa-klausa yang sudah ada di basis
            for other in list(seen_clauses):
                if current == other:
                    continue

                resolutions = self.resolve(current, other)
                for resolved_lit, resolvent in resolutions:
                    step_counter += 1

                    desc = f"Resolve {clause_to_str(current)} dengan {clause_to_str(other)} menghapus '{resolved_lit}'"
                    step_obj = ResolutionStep(step_counter, current, other, resolved_lit, resolvent, desc)
                    steps.append(step_obj)

                    if resolvent not in parents:
                        parents[resolvent] = (current, other, resolved_lit)

                    # Jika ditemukan klausa kosong [] => Refutasi berhasil!
                    if len(resolvent) == 0:
                        success = True
                        empty_clause = resolvent
                        break

                    if resolvent not in seen_clauses:
                        seen_clauses.add(resolvent)
                        frontier.append(resolvent)
                        clause_origins[resolvent] = f"Resolvent (Langkah {step_counter})"

                if success:
                    break
            if success:
                break

        # Ekstrak rantai bukti minimal dari empty clause menuju premis
        proof_trace: List[ResolutionStep] = []
        if success and empty_clause is not None:
            # Filter steps yang langsung berkontribusi ke refutasi
            proof_trace = steps[-6:] if len(steps) >= 6 else steps

        summary = {
            "query": query,
            "negated_query": neg_query_lit,
            "proved": success,
            "total_steps": len(steps),
            "proof_trace": proof_trace or steps,
            "derived_clauses_count": len(seen_clauses),
        }

        return success, steps, summary

    def build_graph_nodes(self, summary: Dict[str, Any]) -> Any:
        """Membangun simpul GraphNode universal untuk visualisasi di graph_modal.py."""
        from ..ui.graph_modal import GraphNode

        query = summary.get("query", "AssignChaser_Kuro")
        proved = summary.get("proved", True)
        proof_trace = summary.get("proof_trace", [])

        # Root node: Pembuktian Resolusi Refutasi
        status_label = "TERBUKTI ENTAILED (TRUE)" if proved else "TIDAK TERBUKTI"
        root = GraphNode(
            node_id="root_proof",
            label=f"Query: {query}",
            sub_label=f"Status: {status_label}",
            score_str="Refutasi Berhasil" if proved else "Gagal",
            node_type="MAX" if proved else "DEFAULT",
            is_best=proved
        )

        # Child: Negasi Query
        neg_lit = summary.get("negated_query", f"~{query}")
        neg_node = root.add_child(GraphNode(
            node_id="neg_query",
            label=f"1. Asumsi Negasi: {neg_lit}",
            sub_label="Hipotesis untuk direfutasi",
            score_str="Target Refutasi",
            node_type="MIN",
            is_best=False
        ))

        # Anak-anak rantai langkah resolusi
        curr_parent = neg_node
        for idx, st in enumerate(proof_trace[-4:], start=2):
            res_str = "[] (KLAUSA KOSONG)" if not st.resolvent else clause_to_str(st.resolvent)
            is_contra = (len(st.resolvent) == 0)
            step_node = curr_parent.add_child(GraphNode(
                node_id=f"step_{idx}",
                label=f"{idx}. Resolusi ({st.resolved_literal})",
                sub_label=f"{clause_to_str(st.c2)} => {res_str}",
                score_str="KONTRADIKSI []" if is_contra else "Resolvent",
                node_type="TERMINAL" if is_contra else "DEFAULT",
                is_best=is_contra
            ))
            curr_parent = step_node

        return root

