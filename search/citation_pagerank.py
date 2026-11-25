"""
Citation Graph & PageRank Authority Ranking for Research Commons
Builds a directed citation graph from referenced_works and paper_citations links,
and computes PageRank authority weights for scholarly ranking.
"""

from __future__ import annotations

from typing import Any

try:
    import networkx as nx  # type: ignore
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False


class CitationGraphPageRank:
    """
    Constructs a directed citation network and calculates academic PageRank authority.
    Edge definition: Paper A cites Paper B (A -> B). Paper B receives PageRank credit.
    """

    def __init__(self, damping: float = 0.85, max_iter: int = 100, tol: float = 1e-6) -> None:
        self.damping = damping
        self.max_iter = max_iter
        self.tol = tol
        self.pagerank_scores: dict[str, float] = {}
        self.normalized_scores: dict[str, float] = {}
        self.graph: Any = None
        self.total_nodes: int = 0
        self.total_edges: int = 0

    def fit(
        self,
        papers: list[dict[str, Any]],
        citation_edges: list[tuple[str, str]] | None = None,
    ) -> CitationGraphPageRank:
        """
        Builds the citation graph from papers list and computes PageRank.
        citation_edges: optional list of (citing_paper_id, cited_paper_id)
        """
        all_paper_ids = {p["id"] for p in papers}

        if NETWORKX_AVAILABLE:
            self.graph = nx.DiGraph()
            self.graph.add_nodes_from(all_paper_ids)

            # Add edges from paper.referenced_works
            for p in papers:
                citing_id = p["id"]
                refs = p.get("referenced_works") or []
                for ref_id in refs:
                    # If cited paper is in our collection or external node
                    self.graph.add_edge(citing_id, ref_id)

            # Add explicit citation edges if provided from DB
            if citation_edges:
                for src, dst in citation_edges:
                    self.graph.add_edge(src, dst)

            self.total_nodes = self.graph.number_of_nodes()
            self.total_edges = self.graph.number_of_edges()

            try:
                raw_pr = nx.pagerank(
                    self.graph,
                    alpha=self.damping,
                    max_iter=self.max_iter,
                    tol=self.tol,
                    weight=None,
                )
            except Exception:
                # In case of non-convergence, fallback to uniform
                uniform = 1.0 / max(self.total_nodes, 1)
                raw_pr = {node: uniform for node in self.graph.nodes}
        else:
            # Fallback in-memory adjacency PageRank
            adj: dict[str, list[str]] = {pid: [] for pid in all_paper_ids}
            in_degree: dict[str, int] = {pid: 0 for pid in all_paper_ids}

            for p in papers:
                citing = p["id"]
                refs = p.get("referenced_works") or []
                for ref in refs:
                    adj.setdefault(citing, []).append(ref)
                    in_degree[ref] = in_degree.get(ref, 0) + 1

            n = max(len(all_paper_ids), 1)
            raw_pr = {pid: 1.0 / n for pid in all_paper_ids}

            # 20 power iterations
            for _ in range(20):
                new_pr = {pid: (1.0 - self.damping) / n for pid in all_paper_ids}
                for u, neighbors in adj.items():
                    if neighbors:
                        share = (self.damping * raw_pr.get(u, 0)) / len(neighbors)
                        for v in neighbors:
                            new_pr[v] = new_pr.get(v, 0.0) + share
                raw_pr = new_pr

            self.total_nodes = len(all_paper_ids)
            self.total_edges = sum(len(refs) for refs in adj.values())

        self.pagerank_scores = raw_pr

        # Min-max scale scores to [0.0, 1.0] for easy combination with search scores
        corpus_scores = [self.pagerank_scores.get(pid, 0.0) for pid in all_paper_ids]
        min_s = min(corpus_scores) if corpus_scores else 0.0
        max_s = max(corpus_scores) if corpus_scores else 1.0
        diff = max_s - min_s if max_s > min_s else 1.0

        self.normalized_scores = {
            pid: (self.pagerank_scores.get(pid, 0.0) - min_s) / diff
            for pid in all_paper_ids
        }

        return self

    def get_score(self, paper_id: str) -> float:
        """Get raw PageRank score."""
        return self.pagerank_scores.get(paper_id, 0.0)

    def get_normalized_score(self, paper_id: str) -> float:
        """Get normalized PageRank score between 0.0 and 1.0."""
        return self.normalized_scores.get(paper_id, 0.0)

    def get_top_authoritative_papers(
        self,
        top_k: int = 10,
        papers: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Return the top most authoritative papers by PageRank in the collection."""
        paper_lookup = {p["id"]: p for p in papers} if papers else {}
        sorted_nodes = sorted(
            self.normalized_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        top_list = []
        for pid, norm_score in sorted_nodes[:top_k]:
            paper = paper_lookup.get(pid, {})
            top_list.append({
                "id": pid,
                "title": paper.get("title", f"Paper {pid}"),
                "publication_year": paper.get("publication_year"),
                "citation_count": paper.get("citation_count", 0),
                "pagerank_score": self.pagerank_scores.get(pid, 0.0),
                "pagerank_normalized": norm_score,
            })
        return top_list
