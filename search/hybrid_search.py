"""
Hybrid Search Engine for Research Commons
Fuses BM25 lexical keyword retrieval and Dense Vector Semantic Search using
Reciprocal Rank Fusion (RRF) with Citation Graph PageRank authority boosting.
Automatically eliminates near-duplicates via MinHash/LSH entity resolution.
"""

from __future__ import annotations

from typing import Any

from .bm25_search import BM25SearchEngine
from .semantic_search import SemanticSearchEngine
from .citation_pagerank import CitationGraphPageRank
from .deduplication import DuplicateDetector


class HybridSearchEngine:
    """
    Unified hybrid retrieval engine.
    Combines:
    1. Lexical BM25 ranking (exact terminology matching)
    2. Dense semantic similarity (conceptual understanding)
    3. Citation PageRank authority (scholarly prestige boost)
    4. Real-time duplicate merging (entity resolution)
    """

    def __init__(
        self,
        rrf_k: int = 60,
        bm25_weight: float = 1.0,
        semantic_weight: float = 1.2,
        pagerank_weight: float = 0.3,
    ) -> None:
        self.rrf_k = rrf_k
        self.bm25_weight = bm25_weight
        self.semantic_weight = semantic_weight
        self.pagerank_weight = pagerank_weight

        self.bm25_engine = BM25SearchEngine()
        self.semantic_engine = SemanticSearchEngine()
        self.pagerank_engine = CitationGraphPageRank()
        self.dedup_engine = DuplicateDetector()

        self.papers: list[dict[str, Any]] = []
        self.paper_lookup: dict[str, dict[str, Any]] = {}
        self.duplicate_map: dict[str, str] = {}  # maps dup_id -> canonical_id

    def fit(
        self,
        papers: list[dict[str, Any]],
        citation_edges: list[tuple[str, str]] | None = None,
    ) -> HybridSearchEngine:
        """Indexes the papers across BM25, Semantic Embeddings, PageRank, and Deduplication."""
        self.papers = papers
        self.paper_lookup = {p["id"]: p for p in papers}

        # 1. Run Duplicate Detection & build mapping
        _, merged_audits = self.dedup_engine.deduplicate_and_merge(papers)
        self.duplicate_map = {}
        for audit in merged_audits:
            for dup_id in audit["merged_duplicate_ids"]:
                self.duplicate_map[dup_id] = audit["canonical_id"]

        # 2. Fit BM25
        self.bm25_engine.fit(papers)

        # 3. Fit Dense Semantic Search
        self.semantic_engine.fit(papers)

        # 4. Fit Citation PageRank
        self.pagerank_engine.fit(papers, citation_edges)

        return self

    def search(
        self,
        query: str,
        top_k: int = 20,
        enable_pagerank: bool = True,
        enable_dedup: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Executes hybrid search across lexical and semantic indexes and fuses ranks with RRF.
        """
        if not self.papers or not query.strip():
            return []

        # Retrieve top candidates from both search engines
        candidate_k = max(top_k * 3, 50)
        bm25_results = self.bm25_engine.search(query, top_k=candidate_k)
        semantic_results = self.semantic_engine.search(query, top_k=candidate_k)

        # Reciprocal Rank Fusion aggregation dictionary: id -> score details
        rrf_scores: dict[str, dict[str, Any]] = {}

        # 1. Score BM25 ranks
        for item in bm25_results:
            pid = item["id"]
            if enable_dedup and pid in self.duplicate_map:
                pid = self.duplicate_map[pid]

            rank = item["bm25_rank"]
            score_contribution = self.bm25_weight * (1.0 / (self.rrf_k + rank))

            if pid not in rrf_scores:
                rrf_scores[pid] = {
                    "paper_id": pid,
                    "rrf_score": 0.0,
                    "bm25_rank": rank,
                    "bm25_score": item["score"],
                    "semantic_rank": None,
                    "semantic_score": None,
                    "pagerank_score": 0.0,
                }
            rrf_scores[pid]["rrf_score"] += score_contribution
            rrf_scores[pid]["bm25_rank"] = min(rrf_scores[pid]["bm25_rank"] or rank, rank)

        # 2. Score Semantic ranks
        for item in semantic_results:
            pid = item["id"]
            if enable_dedup and pid in self.duplicate_map:
                pid = self.duplicate_map[pid]

            rank = item["semantic_rank"]
            score_contribution = self.semantic_weight * (1.0 / (self.rrf_k + rank))

            if pid not in rrf_scores:
                rrf_scores[pid] = {
                    "paper_id": pid,
                    "rrf_score": 0.0,
                    "bm25_rank": None,
                    "bm25_score": None,
                    "semantic_rank": rank,
                    "semantic_score": item["similarity"],
                    "pagerank_score": 0.0,
                }
            rrf_scores[pid]["rrf_score"] += score_contribution
            if rrf_scores[pid]["semantic_rank"] is None or rank < rrf_scores[pid]["semantic_rank"]:
                rrf_scores[pid]["semantic_rank"] = rank
                rrf_scores[pid]["semantic_score"] = item["similarity"]

        # 3. Add PageRank Authority boost if enabled
        if enable_pagerank:
            for pid, entry in rrf_scores.items():
                pr_norm = self.pagerank_engine.get_normalized_score(pid)
                pr_boost = self.pagerank_weight * pr_norm
                entry["pagerank_score"] = pr_norm
                entry["rrf_score"] += pr_boost

        # Sort descending by fused RRF score
        ranked_items = sorted(
            rrf_scores.values(),
            key=lambda x: x["rrf_score"],
            reverse=True,
        )

        final_results = []
        for rank, item in enumerate(ranked_items[:top_k], start=1):
            pid = item["paper_id"]
            doc = self.paper_lookup.get(pid, {})
            final_results.append({
                "rank": rank,
                "id": pid,
                "title": doc.get("title", ""),
                "abstract": doc.get("abstract", ""),
                "authors": doc.get("authors", []),
                "doi": doc.get("doi"),
                "publication_year": doc.get("publication_year"),
                "citation_count": doc.get("citation_count", 0),
                "concepts": doc.get("concepts", []),
                "sources": doc.get("sources", [doc.get("source", "openalex")]),
                "rrf_score": round(item["rrf_score"], 5),
                "bm25_rank": item["bm25_rank"],
                "semantic_rank": item["semantic_rank"],
                "pagerank_score": round(item["pagerank_score"], 4),
            })

        return final_results
