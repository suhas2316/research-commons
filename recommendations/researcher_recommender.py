"""
Researcher & Faculty Collaboration Recommender for Research Commons.

Matches students and researchers with faculty (and peers) across departments
based on shared research interest tags, publication/post history, and saved
library concept overlap.
"""

from __future__ import annotations

from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from recommendations.data_loader import ResearchCommonsData, load_data


class ResearcherRecommender:
    """Cross-department researcher and faculty matching engine."""

    def __init__(self, data: ResearchCommonsData | None = None) -> None:
        self.data = data if data is not None else load_data()
        self._user_profiles: dict[int, dict[str, Any]] = {}
        self._user_ids: list[int] = []
        self._tfidf_matrix: Any = None
        self._build_profiles()

    def _build_profiles(self) -> None:
        # Pre-index saved library concepts & authored/attached post concepts per user
        saved_concepts: dict[int, list[str]] = {}
        for entry in self.data.library:
            uid = int(entry["user_id"])
            paper = self.data.papers_by_id.get(str(entry["paper_id"]))
            if paper:
                saved_concepts.setdefault(uid, []).extend(
                    str(c).lower() for c in (paper.get("concepts") or [])
                )

        post_topics: dict[int, list[str]] = {}
        post_counts: dict[int, int] = {}
        for post in self.data.posts:
            uid = int(post["user_id"])
            post_counts[uid] = post_counts.get(uid, 0) + 1
            for tag in post.get("tags") or []:
                post_topics.setdefault(uid, []).append(str(tag).lower())
            attached = post.get("attached_paper_id")
            if attached and str(attached) in self.data.papers_by_id:
                paper = self.data.papers_by_id[str(attached)]
                post_topics.setdefault(uid, []).extend(
                    str(c).lower() for c in (paper.get("concepts") or [])
                )

        # Check authored papers if user name appears in paper authors
        authored_concepts: dict[int, list[str]] = {}
        authored_counts: dict[int, int] = {}
        name_to_uid = {
            str(u.get("name", "")).strip().lower(): int(u["id"])
            for u in self.data.users
            if u.get("name")
        }
        for paper in self.data.papers:
            for author in paper.get("authors") or []:
                uid = name_to_uid.get(str(author).strip().lower())
                if uid is not None:
                    authored_counts[uid] = authored_counts.get(uid, 0) + 1
                    authored_concepts.setdefault(uid, []).extend(
                        str(c).lower() for c in (paper.get("concepts") or [])
                    )

        corpus: list[str] = []
        self._user_ids = []
        for user in self.data.users:
            uid = int(user["id"])
            interests = [t.lower() for t in self.data.interests_by_user.get(uid, [])]
            pub_terms = (
                saved_concepts.get(uid, [])
                + post_topics.get(uid, [])
                + authored_concepts.get(uid, [])
            )
            profile_text = " ".join(
                interests * 3
                + pub_terms
                + [str(user.get("department") or ""), str(user.get("bio") or "")]
            ).strip()
            self._user_profiles[uid] = {
                "user": user,
                "interests": set(interests),
                "pub_terms": set(pub_terms),
                "publication_activity": authored_counts.get(uid, 0) + post_counts.get(uid, 0),
                "text": profile_text or str(user.get("department") or "research"),
            }
            self._user_ids.append(uid)
            corpus.append(self._user_profiles[uid]["text"])

        if corpus:
            vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
            self._tfidf_matrix = vectorizer.fit_transform(corpus)
        else:
            self._tfidf_matrix = None

    def recommend_colleagues(
        self,
        user_id: int,
        top_k: int = 5,
        prefer_faculty: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Recommend top-K faculty and researchers matching a user's interests
        and publication/discussion history across departments.
        """
        uid = int(user_id)
        if top_k <= 0 or uid not in self._user_profiles or self._tfidf_matrix is None:
            return []

        user_idx = self._user_ids.index(uid)
        target_profile = self._user_profiles[uid]
        target_user = target_profile["user"]
        target_dept = str(target_user.get("department") or "")
        target_interests = target_profile["interests"]
        target_terms = target_interests | target_profile["pub_terms"]

        already_following = {
            int(f["following_id"])
            for f in self.data.follows
            if int(f["follower_id"]) == uid
        }

        sims = cosine_similarity(
            self._tfidf_matrix[user_idx : user_idx + 1], self._tfidf_matrix
        ).flatten()

        candidates: list[tuple[float, dict[str, Any]]] = []
        for idx, cand_id in enumerate(self._user_ids):
            if cand_id == uid:
                continue
            cand_profile = self._user_profiles[cand_id]
            cand_user = cand_profile["user"]

            # Skip obvious spam-like external profiles with no academic overlap
            if str(cand_user.get("email", "")).endswith("@external-mail.org"):
                continue

            cand_interests = cand_profile["interests"]
            cand_terms = cand_interests | cand_profile["pub_terms"]

            shared_interests = sorted(target_interests & cand_interests)
            shared_pub_terms = sorted((target_terms & cand_terms) - set(shared_interests))

            union_size = len(target_terms | cand_terms) or 1
            jaccard = len(target_terms & cand_terms) / union_size
            tfidf_sim = float(sims[idx])

            role = str(cand_user.get("role") or "student").lower()
            role_bonus = 0.0
            if prefer_faculty:
                if role == "faculty":
                    role_bonus = 0.15
                elif role == "researcher":
                    role_bonus = 0.08

            cross_dept = str(cand_user.get("department") or "") != target_dept
            cross_dept_bonus = 0.05 if cross_dept and (shared_interests or shared_pub_terms) else 0.0

            score = 0.55 * tfidf_sim + 0.30 * jaccard + role_bonus + cross_dept_bonus

            reasons: list[str] = []
            if shared_interests:
                reasons.append(f"shared interests: {', '.join(shared_interests[:3])}")
            if shared_pub_terms:
                reasons.append(f"publication/reading overlap: {', '.join(shared_pub_terms[:3])}")
            if cross_dept:
                reasons.append(f"cross-department ({cand_user.get('department')})")
            if not reasons:
                reasons.append(f"related {cand_user.get('department')} research profile")

            candidates.append(
                (
                    score,
                    {
                        "user_id": cand_id,
                        "name": cand_user.get("name", ""),
                        "role": cand_user.get("role", ""),
                        "department": cand_user.get("department", ""),
                        "shared_interests": shared_interests,
                        "shared_publication_topics": shared_pub_terms[:5],
                        "cross_department": cross_dept,
                        "already_following": cand_id in already_following,
                        "similarity_score": round(float(score), 4),
                        "reason": "; ".join(reasons),
                    },
                )
            )

        candidates.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in candidates[:top_k]]


_DEFAULT_RESEARCHER_RECOMMENDER: ResearcherRecommender | None = None


def recommend_colleagues(user_id: int, top_k: int = 5) -> list[dict[str, Any]]:
    """Module-level helper delegating to a cached ResearcherRecommender instance."""
    global _DEFAULT_RESEARCHER_RECOMMENDER
    if _DEFAULT_RESEARCHER_RECOMMENDER is None:
        _DEFAULT_RESEARCHER_RECOMMENDER = ResearcherRecommender()
    return _DEFAULT_RESEARCHER_RECOMMENDER.recommend_colleagues(user_id=user_id, top_k=top_k)
