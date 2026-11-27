"""
Recommendations, Trends, Spam Detection, and AI Research Assistant module
for Research Commons (Chanakya University Mini-Project).
"""

from recommendations.fpgrowth_cosaved import FPGrowthCosavedRecommender, get_cosaved_recommendations
from recommendations.paper_recommender import PaperRecommender, recommend_papers
from recommendations.rag_assistant import RAGAssistant, ask_assistant
from recommendations.recommendation_service import RecommendationService
from recommendations.researcher_recommender import ResearcherRecommender, recommend_colleagues
from recommendations.spam_detector import SpamDetector, detect_spam_accounts
from recommendations.trend_detector import TrendDetector, detect_topic_spikes, get_trending_topics

__all__ = [
    "PaperRecommender",
    "ResearcherRecommender",
    "FPGrowthCosavedRecommender",
    "TrendDetector",
    "SpamDetector",
    "RAGAssistant",
    "RecommendationService",
    "recommend_papers",
    "recommend_colleagues",
    "get_cosaved_recommendations",
    "get_trending_topics",
    "detect_topic_spikes",
    "detect_spam_accounts",
    "ask_assistant",
]
