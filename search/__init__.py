"""
Research Commons - Search and Analytics Module
Module Owner: Suhas
Features:
- BM25 Keyword Search
- Dense Vector Semantic Search (all-MiniLM-L6-v2)
- Hybrid Search (Reciprocal Rank Fusion)
- Near-Duplicate Paper Detection (MinHash & LSH)
- Citation Graph PageRank
- DuckDB Columnar OLAP Analytics
- Unified 4-in-1 Search Engine (Papers, Library, People, Posts)
"""

from .bm25_search import BM25SearchEngine
from .semantic_search import SemanticSearchEngine
from .hybrid_search import HybridSearchEngine
from .deduplication import DuplicateDetector
from .citation_pagerank import CitationGraphPageRank
from .analytics_duckdb import DuckDBAnalytics
from .unified_search import UnifiedSearchService

__all__ = [
    "BM25SearchEngine",
    "SemanticSearchEngine",
    "HybridSearchEngine",
    "DuplicateDetector",
    "CitationGraphPageRank",
    "DuckDBAnalytics",
    "UnifiedSearchService",
]
