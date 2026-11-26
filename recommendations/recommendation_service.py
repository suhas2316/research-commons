"""
Master Coordinator Service for Research Commons Recommendations & AI Module.

Unites:
- Content-based paper recommendations (with department cold-start fallback)
- Cross-department researcher / faculty collaboration matching
- FP-Growth co-saved paper association rules
- Sliding-window Z-score trending topics & spike alerts
- Isolation Forest spam account detection
- Grounded RAG research assistant (Ollama + extractive fallback)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from recommendations.data_loader import ResearchCommonsData, load_data
from recommendations.fpgrowth_cosaved import FPGrowthCosavedRecommender
from recommendations.paper_recommender import PaperRecommender
from recommendations.rag_assistant import RAGAssistant
from recommendations.researcher_recommender import ResearcherRecommender
from recommendations.spam_detector import SpamDetector
from recommendations.trend_detector import TrendDetector


class RecommendationService:
    """Unified facade over all recommendation, trend, spam, and RAG engines."""

    def __init__(
        self,
        data: ResearchCommonsData | None = None,
        papers_path: Path | str | None = None,
        synthetic_path: Path | str | None = None,
        prefer_db: bool = False,
        ollama_model: str = "llama3",
    ) -> None:
        self.data = (
            data
            if data is not None
            else load_data(
                papers_path=papers_path,
                synthetic_path=synthetic_path,
                prefer_db=prefer_db,
            )
        )
        self.paper_recommender = PaperRecommender(self.data)
        self.researcher_recommender = ResearcherRecommender(self.data)
        self.fpgrowth = FPGrowthCosavedRecommender(self.data)
        self.trend_detector = TrendDetector(self.data)
        self.spam_detector = SpamDetector(self.data)
        self.rag_assistant = RAGAssistant(self.data, model=ollama_model)

    def recommend_papers(self, user_id: int, top_k: int = 10) -> list[dict[str, Any]]:
        return self.paper_recommender.recommend_papers(user_id=user_id, top_k=top_k)

    def recommend_colleagues(self, user_id: int, top_k: int = 5) -> list[dict[str, Any]]:
        return self.researcher_recommender.recommend_colleagues(user_id=user_id, top_k=top_k)

    def get_cosaved_recommendations(self, paper_id: str, top_k: int = 5) -> list[dict[str, Any]]:
        return self.fpgrowth.get_cosaved_recommendations(paper_id=paper_id, top_k=top_k)

    def get_trending_topics(self, top_k: int = 10) -> list[dict[str, Any]]:
        return self.trend_detector.get_trending_topics(top_k=top_k)

    def detect_topic_spikes(self, z_threshold: float = 2.5) -> list[dict[str, Any]]:
        return self.trend_detector.detect_topic_spikes(z_threshold=z_threshold)

    def detect_spam_accounts(self, include_all: bool = False) -> list[dict[str, Any]]:
        return self.spam_detector.detect_spam_accounts(include_all=include_all)

    def ask_assistant(self, question: str, top_k_sources: int = 3) -> dict[str, Any]:
        return self.rag_assistant.ask_assistant(question=question, top_k_sources=top_k_sources)

    def get_user_dashboard(self, user_id: int) -> dict[str, Any]:
        """Return personalized papers, colleagues, and trending topics for a member."""
        return {
            "user_id": int(user_id),
            "recommended_papers": self.recommend_papers(user_id=user_id, top_k=10),
            "recommended_colleagues": self.recommend_colleagues(user_id=user_id, top_k=5),
            "trending_topics": self.get_trending_topics(top_k=10),
            "topic_spikes": self.detect_topic_spikes(),
        }

    def get_admin_moderation_report(self) -> dict[str, Any]:
        """Return spam detection and topic surge alerts for administrators."""
        spam_accounts = self.detect_spam_accounts()
        topic_spikes = self.detect_topic_spikes()
        return {
            "total_users_scanned": len(self.data.users),
            "flagged_spam_count": len(spam_accounts),
            "flagged_spam_accounts": spam_accounts,
            "topic_spike_count": len(topic_spikes),
            "topic_spikes": topic_spikes,
        }
