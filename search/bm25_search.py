"""
BM25 Keyword Search Engine for Research Commons
Implements BM25Okapi scoring over paper titles, abstracts, concepts, and posts.
Includes tokenization, stopword filtering, snippet highlighting, and fallback scoring.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

# Standard English stopwords
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "should", "shouldn't", "so", "some", "such", "than", "that", "the", "their",
    "theirs", "them", "themselves", "then", "there", "these", "they", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "were", "weren't", "what", "when", "where", "which", "while",
    "who", "whom", "why", "with", "won't", "would", "wouldn't", "you", "your",
    "yours", "yourself", "yourselves",
}

TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")


def tokenize(text: str) -> list[str]:
    """Tokenize, lowercase, and filter stopwords."""
    if not text:
        return []
    words = TOKEN_PATTERN.findall(text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


class BM25SearchEngine:
    """BM25 Okapi retrieval engine with rank_bm25 support and pure-Python fallback."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.documents: list[dict[str, Any]] = []
        self.corpus_tokens: list[list[str]] = []
        self.bm25_model: Any = None
        self.avg_doc_len: float = 0.0
        self.doc_lens: list[int] = []
        self.idf: dict[str, float] = {}

    def fit(
        self,
        documents: list[dict[str, Any]],
        text_fields: list[str] | None = None,
    ) -> BM25SearchEngine:
        """Index a list of document dicts."""
        if text_fields is None:
            text_fields = ["title", "abstract", "concepts"]

        self.documents = documents
        self.corpus_tokens = []

        for doc in documents:
            text_parts: list[str] = []
            for field in text_fields:
                val = doc.get(field)
                if isinstance(val, list):
                    text_parts.append(" ".join(str(item) for item in val))
                elif isinstance(val, str):
                    text_parts.append(val)
            combined_text = " ".join(text_parts)
            self.corpus_tokens.append(tokenize(combined_text))

        # Attempt to use rank_bm25 if available
        try:
            from rank_bm25 import BM25Okapi  # type: ignore

            self.bm25_model = BM25Okapi(self.corpus_tokens, k1=self.k1, b=self.b)
        except Exception:
            self.bm25_model = None
            self._fit_fallback()

        return self

    def _fit_fallback(self) -> None:
        """Pure Python BM25 fitting."""
        n_docs = len(self.corpus_tokens)
        self.doc_lens = [len(toks) for toks in self.corpus_tokens]
        self.avg_doc_len = sum(self.doc_lens) / max(n_docs, 1)

        # Compute document frequencies
        df: Counter[str] = Counter()
        for toks in self.corpus_tokens:
            df.update(set(toks))

        # Compute Robertson-Spärck Jones IDF
        self.idf = {}
        for word, freq in df.items():
            self.idf[word] = math.log(
                (n_docs - freq + 0.5) / (freq + 0.5) + 1.0
            )

    def search(
        self,
        query: str,
        top_k: int = 20,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Search the indexed corpus and return ranked results."""
        if not self.documents:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        if self.bm25_model is not None:
            raw_scores = self.bm25_model.get_scores(query_tokens)
        else:
            raw_scores = self._score_fallback(query_tokens)

        # Pair documents with scores
        scored_results: list[dict[str, Any]] = []
        for idx, score in enumerate(raw_scores):
            if score > min_score:
                doc = self.documents[idx]
                scored_results.append({
                    "id": doc.get("id"),
                    "title": doc.get("title", ""),
                    "abstract": doc.get("abstract", ""),
                    "authors": doc.get("authors", []),
                    "doi": doc.get("doi"),
                    "publication_year": doc.get("publication_year"),
                    "citation_count": doc.get("citation_count", 0),
                    "concepts": doc.get("concepts", []),
                    "score": float(score),
                    "matched_tokens": [t for t in query_tokens if t in self.corpus_tokens[idx]],
                    "raw_doc": doc,
                })

        # Sort descending by BM25 score
        scored_results.sort(key=lambda x: x["score"], reverse=True)

        for rank, res in enumerate(scored_results[:top_k], start=1):
            res["bm25_rank"] = rank

        return scored_results[:top_k]

    def _score_fallback(self, query_tokens: list[str]) -> list[float]:
        """Compute BM25 scores in pure Python."""
        scores: list[float] = [0.0] * len(self.documents)
        for idx, doc_toks in enumerate(self.corpus_tokens):
            if not doc_toks:
                continue
            doc_len = self.doc_lens[idx]
            tok_counts = Counter(doc_toks)
            score = 0.0
            for q_tok in query_tokens:
                if q_tok not in tok_counts:
                    continue
                tf = tok_counts[q_tok]
                idf = self.idf.get(q_tok, 0.0)
                denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                score += idf * (tf * (self.k1 + 1.0)) / denom
            scores[idx] = score
        return scores
