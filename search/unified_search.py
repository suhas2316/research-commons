"""
Unified 4-in-1 Search Coordinator for Research Commons (F5)
Coordinates federated search across four result panels:
1. External & Scholarly Papers (Hybrid BM25 + Semantic + PageRank, Deduplicated)
2. Chanakya University Saved Library Items
3. University Members & Faculty (matching research interests and departments)
4. Community Forum Posts & Discussions
"""

from __future__ import annotations

import re
from typing import Any

from .hybrid_search import HybridSearchEngine


def simple_match_score(text: str, query_tokens: list[str]) -> float:
    """Lightweight token matching score for library, people, and posts."""
    if not text or not query_tokens:
        return 0.0
    text_lower = text.lower()
    score = 0.0
    for tok in query_tokens:
        if tok in text_lower:
            # Exact word boundary match gets higher weight
            if re.search(r"\b" + re.escape(tok) + r"\b", text_lower):
                score += 2.0
            else:
                score += 1.0
    return score


class UnifiedSearchService:
    """
    Core implementation of F5 Unified Search.
    Fulfills the course requirement to return four distinct panels from a single search box.
    """

    def __init__(self) -> None:
        self.hybrid_engine = HybridSearchEngine()
        self.papers: list[dict[str, Any]] = []
        self.library_items: list[dict[str, Any]] = []
        self.users: list[dict[str, Any]] = []
        self.posts: list[dict[str, Any]] = []

    def fit(
        self,
        papers: list[dict[str, Any]],
        users: list[dict[str, Any]] | None = None,
        posts: list[dict[str, Any]] | None = None,
        library: list[dict[str, Any]] | None = None,
        citation_edges: list[tuple[str, str]] | None = None,
    ) -> UnifiedSearchService:
        """Indexes all four entity collections."""
        self.papers = papers
        self.users = users or []
        self.posts = posts or []
        self.library_items = library or []

        # Fit hybrid search engine over academic papers
        self.hybrid_engine.fit(papers, citation_edges)
        return self

    def search(
        self,
        query: str,
        limit_per_panel: int = 10,
    ) -> dict[str, Any]:
        """
        Executes unified search and returns results structured in 4 panels:
        - papers
        - library
        - people
        - posts
        """
        query_str = query.strip()
        if not query_str:
            return {
                "query": query,
                "total_results": 0,
                "panels": {"papers": [], "library": [], "people": [], "posts": []},
            }

        tokens = [t.lower() for t in re.findall(r"[a-z0-9]+", query_str) if len(t) > 1]

        # 1. Panel 1: Papers (Hybrid BM25 + Semantic + PageRank)
        paper_results = self.hybrid_engine.search(
            query=query_str,
            top_k=limit_per_panel,
            enable_pagerank=True,
            enable_dedup=True,
        )

        # 2. Panel 2: Chanakya Saved Library Items
        paper_lookup = {p["id"]: p for p in self.papers}
        library_matches = []
        for item in self.library_items:
            pid = item.get("paper_id")
            linked_paper = paper_lookup.get(pid, {})
            search_text = (
                f"{linked_paper.get('title', '')} {item.get('notes', '')} "
                f"{item.get('collection_name', '')}"
            )
            score = simple_match_score(search_text, tokens)
            if score > 0:
                library_matches.append({
                    "library_id": item.get("id"),
                    "paper_id": pid,
                    "title": linked_paper.get("title", f"Paper {pid}"),
                    "authors": linked_paper.get("authors", []),
                    "notes": item.get("notes", ""),
                    "collection_name": item.get("collection_name", "General"),
                    "match_score": score,
                })
        library_matches.sort(key=lambda x: x["match_score"], reverse=True)

        # 3. Panel 3: University Members (People)
        people_matches = []
        for user in self.users:
            interests_str = " ".join(user.get("interests", []))
            search_text = f"{user.get('name', '')} {user.get('department', '')} {user.get('bio', '')} {interests_str}"
            score = simple_match_score(search_text, tokens)
            if score > 0:
                people_matches.append({
                    "user_id": user.get("id"),
                    "name": user.get("name"),
                    "department": user.get("department"),
                    "role": user.get("role"),
                    "interests": user.get("interests", []),
                    "bio": user.get("bio", ""),
                    "match_score": score,
                })
        people_matches.sort(key=lambda x: x["match_score"], reverse=True)

        # 4. Panel 4: Related Posts & Discussions
        post_matches = []
        for post in self.posts:
            tags_str = " ".join(post.get("tags", []))
            search_text = f"{post.get('title', '')} {post.get('content', '')} {tags_str}"
            score = simple_match_score(search_text, tokens)
            if score > 0:
                post_matches.append({
                    "post_id": post.get("id"),
                    "title": post.get("title"),
                    "content_snippet": post.get("content", "")[:200] + "...",
                    "tags": post.get("tags", []),
                    "user_id": post.get("user_id"),
                    "attached_paper_id": post.get("attached_paper_id"),
                    "created_at": post.get("created_at"),
                    "match_score": score,
                })
        post_matches.sort(key=lambda x: x["match_score"], reverse=True)

        total_count = (
            len(paper_results)
            + len(library_matches[:limit_per_panel])
            + len(people_matches[:limit_per_panel])
            + len(post_matches[:limit_per_panel])
        )

        return {
            "query": query_str,
            "total_results": total_count,
            "panels": {
                "papers": paper_results,
                "library": library_matches[:limit_per_panel],
                "people": people_matches[:limit_per_panel],
                "posts": post_matches[:limit_per_panel],
            },
        }
