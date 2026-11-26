"""
Grounded AI Research Assistant (RAG) for Research Commons.

Retrieves relevant academic papers via TF-IDF similarity, formats prompt context
with strict `[Author, Year] - "Title"` citations, and queries local Ollama
(`http://localhost:11434/api/generate`) with an automatic extractive summarizer
fallback when Ollama is offline.
"""

from __future__ import annotations

import os
import re
from typing import Any

import numpy as np
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from recommendations.data_loader import ResearchCommonsData, load_data

DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")


def format_citation(paper: dict[str, Any]) -> str:
    """Format a paper strictly as `[Author, Year] - "Title"`."""
    authors = paper.get("authors") or []
    first_author = str(authors[0]).strip() if authors else "Unknown Author"
    year = paper.get("publication_year") or "n.d."
    title = str(paper.get("title") or "Untitled Paper").strip()
    return f'[{first_author}, {year}] - "{title}"'


class RAGAssistant:
    """Retrieval-Augmented Generation assistant backed by local Ollama or fallback."""

    def __init__(
        self,
        data: ResearchCommonsData | None = None,
        ollama_url: str = DEFAULT_OLLAMA_URL,
        model: str = DEFAULT_OLLAMA_MODEL,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.data = data if data is not None else load_data()
        self.ollama_url = ollama_url
        self.model = model
        self.timeout_seconds = timeout_seconds

        self._valid_papers: list[dict[str, Any]] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix: Any = None
        self._build_retriever()

    def _build_retriever(self) -> None:
        self._valid_papers = [
            p for p in self.data.papers if not str(p.get("id", "")).startswith("W_DUP_")
        ]
        if not self._valid_papers:
            self._vectorizer = None
            self._matrix = None
            return

        corpus = [
            " ".join(
                [
                    str(p.get("title") or ""),
                    str(p.get("title") or ""),
                    " ".join(str(c) for c in (p.get("concepts") or [])),
                    str(p.get("abstract") or ""),
                ]
            )
            for p in self._valid_papers
        ]
        self._vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=10000,
            ngram_range=(1, 2),
        )
        self._matrix = self._vectorizer.fit_transform(corpus)

    def retrieve_papers(self, question: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Retrieve top-K relevant papers for a research question."""
        if not question.strip() or not self._valid_papers or self._vectorizer is None:
            return []

        q_vec = self._vectorizer.transform([question])
        sims = cosine_similarity(q_vec, self._matrix).flatten()

        # Mildly break ties using log citation count
        scored: list[tuple[float, float, dict[str, Any]]] = []
        for idx, paper in enumerate(self._valid_papers):
            sim = float(sims[idx])
            cite_boost = float(np.log1p(int(paper.get("citation_count") or 0))) * 0.01
            scored.append((sim + cite_boost, sim, paper))

        scored.sort(key=lambda item: item[0], reverse=True)
        results: list[dict[str, Any]] = []
        for _, sim, paper in scored[:top_k]:
            results.append(
                {
                    "paper_id": str(paper["id"]),
                    "title": paper.get("title", ""),
                    "authors": paper.get("authors", []),
                    "publication_year": paper.get("publication_year"),
                    "citation_count": int(paper.get("citation_count") or 0),
                    "concepts": paper.get("concepts", []),
                    "abstract": paper.get("abstract", ""),
                    "citation": format_citation(paper),
                    "relevance_score": round(sim, 4),
                }
            )
        return results

    @staticmethod
    def _build_prompt(question: str, sources: list[dict[str, Any]]) -> str:
        context_blocks: list[str] = []
        for idx, src in enumerate(sources, start=1):
            abstract_snippet = str(src.get("abstract") or "")[:900]
            concepts = ", ".join(str(c) for c in (src.get("concepts") or [])[:6])
            context_blocks.append(
                f"Source {idx}: {src['citation']}\n"
                f"Concepts: {concepts}\n"
                f"Abstract: {abstract_snippet}"
            )
        joined_context = "\n\n".join(context_blocks)
        return (
            "You are the Research Commons AI Research Assistant for Chanakya University.\n"
            "Answer the user's question strictly using the provided academic paper contexts.\n"
            'Every claim MUST include an inline citation formatted exactly as [Author, Year] - "Title".\n'
            "Do not invent papers, authors, or findings not present in the context.\n\n"
            f"Retrieved Papers:\n{joined_context}\n\n"
            f"Question: {question}\n\n"
            "Grounded Answer:"
        )

    def _query_ollama(self, prompt: str) -> tuple[str | None, str]:
        """Try calling local Ollama /api/generate; fallback to mistral if llama3 missing."""
        models_to_try = [self.model]
        if self.model != "mistral":
            models_to_try.append("mistral")

        for candidate_model in models_to_try:
            try:
                resp = requests.post(
                    self.ollama_url,
                    json={
                        "model": candidate_model,
                        "prompt": prompt,
                        "stream": False,
                    },
                    timeout=(1.5, self.timeout_seconds),
                )
                if resp.status_code == 200:
                    payload = resp.json()
                    text = str(payload.get("response") or "").strip()
                    if text:
                        return text, candidate_model
            except requests.RequestException:
                # Ollama service offline or unreachable; fall back immediately
                break
        return None, "extractive_fallback"

    @staticmethod
    def _extractive_fallback_answer(
        question: str, sources: list[dict[str, Any]]
    ) -> str:
        """Produce a grounded extractive summary citing each source strictly."""
        if not sources:
            return (
                "No matching papers were found in the current Research Commons corpus "
                f"for '{question}'."
            )

        q_terms = {
            tok for tok in re.findall(r"[a-zA-Z0-9]{3,}", question.lower())
        }
        lines = [
            f'Based on the retrieved literature for "{question}", here are the key grounded findings:'
        ]
        for src in sources:
            abstract = str(src.get("abstract") or "").strip()
            sentences = [
                s.strip()
                for s in re.split(r"(?<=[.!?])\s+", abstract)
                if len(s.strip()) > 20
            ]
            if sentences:
                # Pick the sentence with highest keyword overlap with the question
                best_sentence = max(
                    sentences,
                    key=lambda s: sum(1 for t in q_terms if t in s.lower()),
                )
            else:
                concepts = ", ".join(str(c) for c in (src.get("concepts") or [])[:4])
                best_sentence = f"Focuses on {concepts or 'related academic research'}."

            lines.append(f"- {src['citation']}: {best_sentence}")

        return "\n".join(lines)

    def ask_assistant(
        self, question: str, top_k_sources: int = 3
    ) -> dict[str, Any]:
        """
        Answer a research question grounded in `top_k_sources` retrieved papers.

        Returns:
            {
                "question": str,
                "answer": str,
                "sources": list[dict],
                "model_used": str,
                "ollama_available": bool,
            }
        """
        sources = self.retrieve_papers(question, top_k=top_k_sources)
        if not sources:
            return {
                "question": question,
                "answer": self._extractive_fallback_answer(question, []),
                "sources": [],
                "model_used": "extractive_fallback",
                "ollama_available": False,
            }

        prompt = self._build_prompt(question, sources)
        ollama_answer, model_used = self._query_ollama(prompt)
        ollama_available = ollama_answer is not None

        if ollama_answer is not None:
            answer = ollama_answer
            # Ensure required citation strings appear in the returned answer
            missing_citations = [
                src["citation"] for src in sources if src["citation"] not in answer
            ]
            if missing_citations:
                answer = (
                    f"{answer}\n\nReferences:\n"
                    + "\n".join(f"- {c}" for c in missing_citations)
                )
        else:
            answer = self._extractive_fallback_answer(question, sources)

        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "model_used": model_used,
            "ollama_available": ollama_available,
        }


_DEFAULT_ASSISTANT: RAGAssistant | None = None


def ask_assistant(question: str, top_k_sources: int = 3) -> dict[str, Any]:
    """Module-level helper delegating to a cached RAGAssistant."""
    global _DEFAULT_ASSISTANT
    if _DEFAULT_ASSISTANT is None:
        _DEFAULT_ASSISTANT = RAGAssistant()
    return _DEFAULT_ASSISTANT.ask_assistant(question=question, top_k_sources=top_k_sources)
