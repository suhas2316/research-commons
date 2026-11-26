"""
Content-Based Paper Recommendation Engine for Research Commons.

Matches a user's research interests, department, and prior library/activity
history against paper titles, concepts, and abstracts using TF-IDF cosine
similarity. Includes a cold-start fallback recommending the highest-cited
foundational papers in the user's department when history is empty.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from recommendations.data_loader import (
    DEPARTMENT_TOPIC_KEYWORDS,
    ResearchCommonsData,
    load_data,
)


class PaperRecommender:
    """Content-based paper recommender with department cold-start fallback."""

    def __init__(self, data: ResearchCommonsData | None = None) -> None:
        self.data = data if data is not None else load_data()
        self._vectorizer: TfidfVectorizer | None = None
        self._paper_matrix: Any = None
        self._paper_ids: list[str] = []
        self._build_index()

    def _paper_text(self, paper: dict[str, Any]) -> str:
        title = str(paper.get("title") or "")
        concepts = " ".join(str(c) for c in (paper.get("concepts") or []))
        dept_topic = str(paper.get("department_topic") or "")
        abstract = str(paper.get("abstract") or "")
        # Weight title and concepts higher than raw abstract terms
        return f"{title} {title} {concepts} {concepts} {dept_topic} {abstract}".strip()

    def _build_index(self) -> None:
        # Exclude deliberate duplicate test records if present so recommendations stay clean
        valid_papers = [
            p for p in self.data.papers if not str(p.get("id", "")).startswith("W_DUP_")
        ]
        self._paper_ids = [str(p["id"]) for p in valid_papers]
        if not valid_papers:
            self._vectorizer = None
            self._paper_matrix = None
            return

        corpus = [self._paper_text(p) for p in valid_papers]
        self._vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=8000,
            ngram_range=(1, 2),
        )
        self._paper_matrix = self._vectorizer.fit_transform(corpus)

    def _get_user_saved_ids(self, user_id: int) -> set[str]:
        saved = {
            str(entry["paper_id"])
            for entry in self.data.library
            if int(entry["user_id"]) == user_id
        }
        for ev in self.data.activity_events:
            if int(ev["user_id"]) == user_id and ev.get("event_type") == "save" and ev.get("target_id"):
                saved.add(str(ev["target_id"]))
        return saved

    def _get_user_history_ids(self, user_id: int) -> list[str]:
        history: list[str] = []
        for entry in self.data.library:
            if int(entry["user_id"]) == user_id:
                history.append(str(entry["paper_id"]))
        for ev in self.data.activity_events:
            if (
                int(ev["user_id"]) == user_id
                and ev.get("event_type") in ("view", "save")
                and ev.get("target_id") in self.data.papers_by_id
            ):
                history.append(str(ev["target_id"]))
        return history

    def _department_keywords(self, department: str) -> list[str]:
        if department in DEPARTMENT_TOPIC_KEYWORDS:
            return DEPARTMENT_TOPIC_KEYWORDS[department]
        dept_lower = department.lower()
        for key, kws in DEPARTMENT_TOPIC_KEYWORDS.items():
            if key.lower() == dept_lower or dept_lower in key.lower():
                return kws
        return [dept_lower] if dept_lower else []

    def _cold_start_recommendations(
        self,
        department: str,
        top_k: int,
        exclude_ids: set[str],
    ) -> list[dict[str, Any]]:
        """Recommend highest-cited foundational papers matching the user's department."""
        dept_kws = [kw.lower() for kw in self._department_keywords(department)]
        dept_matches: list[tuple[int, int, dict[str, Any]]] = []
        fallback_all: list[tuple[int, dict[str, Any]]] = []

        for pid in self._paper_ids:
            if pid in exclude_ids:
                continue
            paper = self.data.papers_by_id[pid]
            citations = int(paper.get("citation_count") or 0)
            searchable = " ".join(
                [
                    str(paper.get("department_topic") or ""),
                    str(paper.get("title") or ""),
                    " ".join(str(c) for c in (paper.get("concepts") or [])),
                ]
            ).lower()
            kw_hits = sum(1 for kw in dept_kws if kw in searchable)
            if kw_hits > 0:
                dept_matches.append((kw_hits, citations, paper))
            fallback_all.append((citations, paper))

        dept_matches.sort(key=lambda item: (item[1], item[0]), reverse=True)
        chosen: list[tuple[dict[str, Any], float, str]] = []
        seen: set[str] = set()

        for kw_hits, citations, paper in dept_matches[:top_k]:
            pid = str(paper["id"])
            seen.add(pid)
            chosen.append(
                (
                    paper,
                    round(float(np.log1p(citations)), 4),
                    f"Cold-start foundational paper in {department} ({citations} citations)",
                )
            )

        if len(chosen) < top_k:
            fallback_all.sort(key=lambda item: item[0], reverse=True)
            for citations, paper in fallback_all:
                pid = str(paper["id"])
                if pid in seen:
                    continue
                seen.add(pid)
                chosen.append(
                    (
                        paper,
                        round(float(np.log1p(citations)), 4),
                        f"Cold-start high-citation foundational paper ({citations} citations)",
                    )
                )
                if len(chosen) >= top_k:
                    break

        return [
            self._format_result(paper, score, cold_start=True, reason=reason)
            for paper, score, reason in chosen
        ]

    @staticmethod
    def _format_result(
        paper: dict[str, Any],
        score: float,
        cold_start: bool,
        reason: str,
    ) -> dict[str, Any]:
        return {
            "paper_id": str(paper["id"]),
            "title": paper.get("title", ""),
            "authors": paper.get("authors", []),
            "publication_year": paper.get("publication_year"),
            "citation_count": int(paper.get("citation_count") or 0),
            "concepts": paper.get("concepts", []),
            "department_topic": paper.get("department_topic"),
            "score": round(float(score), 4),
            "cold_start": cold_start,
            "reason": reason,
        }

    def recommend_papers(self, user_id: int, top_k: int = 10) -> list[dict[str, Any]]:
        """
        Recommend top-K papers for a given user_id.

        Uses TF-IDF cosine similarity over user profile interests + interaction history;
        falls back to highest-cited department papers for cold-start users with zero history.
        """
        if top_k <= 0 or not self._paper_ids or self._vectorizer is None:
            return []

        user = self.data.users_by_id.get(int(user_id))
        if user is None:
            return self._cold_start_recommendations("Computer Science", top_k, set())

        saved_ids = self._get_user_saved_ids(int(user_id))
        history_ids = self._get_user_history_ids(int(user_id))
        interests = self.data.interests_by_user.get(int(user_id), [])
        department = str(user.get("department") or "Computer Science")

        # Cold-start: user has no saved/viewed paper history and no search queries
        user_searches = [
            str(ev.get("query_text") or "").strip()
            for ev in self.data.activity_events
            if int(ev["user_id"]) == int(user_id)
            and ev.get("event_type") == "search"
            and ev.get("query_text")
        ]
        if not history_ids and not user_searches:
            return self._cold_start_recommendations(department, top_k, saved_ids)

        profile_parts: list[str] = []
        if interests:
            # Repeat interests to anchor recommendations on stated topics
            profile_parts.extend(interests * 3)
        profile_parts.extend(self._department_keywords(department))
        if user.get("bio"):
            profile_parts.append(str(user["bio"]))
        if user_searches:
            profile_parts.extend(user_searches[-15:])

        for pid in history_ids[:20]:
            paper = self.data.papers_by_id.get(pid)
            if paper:
                profile_parts.append(str(paper.get("title") or ""))
                profile_parts.extend(str(c) for c in (paper.get("concepts") or []))

        profile_text = " ".join(profile_parts).strip()
        if not profile_text:
            return self._cold_start_recommendations(department, top_k, saved_ids)

        profile_vec = self._vectorizer.transform([profile_text])
        sims = cosine_similarity(profile_vec, self._paper_matrix).flatten()

        # Blend content similarity with mild citation popularity boost
        max_log_cite = max(
            (float(np.log1p(int(self.data.papers_by_id[pid].get("citation_count") or 0))) for pid in self._paper_ids),
            default=1.0,
        ) or 1.0

        scored: list[tuple[float, float, dict[str, Any]]] = []
        for idx, pid in enumerate(self._paper_ids):
            if pid in saved_ids:
                continue
            paper = self.data.papers_by_id[pid]
            content_sim = float(sims[idx])
            cite_norm = float(np.log1p(int(paper.get("citation_count") or 0))) / max_log_cite
            final_score = 0.85 * content_sim + 0.15 * cite_norm
            scored.append((final_score, content_sim, paper))

        scored.sort(key=lambda item: item[0], reverse=True)
        interest_set = {tag.lower() for tag in interests}

        results: list[dict[str, Any]] = []
        for final_score, content_sim, paper in scored[:top_k]:
            matched_concepts = [
                c for c in (paper.get("concepts") or [])
                if any(tag in str(c).lower() or str(c).lower() in tag for tag in interest_set)
            ]
            if matched_concepts:
                reason = f"Matches your interests ({', '.join(matched_concepts[:3])})"
            else:
                reason = f"Content similarity ({content_sim:.2f}) to your {department} profile"
            results.append(
                self._format_result(paper, final_score, cold_start=False, reason=reason)
            )
        return results


_DEFAULT_RECOMMENDER: PaperRecommender | None = None


def recommend_papers(user_id: int, top_k: int = 10) -> list[dict[str, Any]]:
    """Module-level helper delegating to a cached PaperRecommender instance."""
    global _DEFAULT_RECOMMENDER
    if _DEFAULT_RECOMMENDER is None:
        _DEFAULT_RECOMMENDER = PaperRecommender()
    return _DEFAULT_RECOMMENDER.recommend_papers(user_id=user_id, top_k=top_k)
