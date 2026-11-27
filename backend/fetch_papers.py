"""
Fetch real academic papers from the OpenAlex API (no API key required).
Queries 6 university department topics, reconstructs abstracts from
abstract_inverted_index, extracts referenced_works for citation graph
analytics, and saves raw and normalized JSON datasets.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_OUTPUT_PATH = BASE_DIR / "data" / "raw" / "papers_raw.json"
PROCESSED_OUTPUT_PATH = BASE_DIR / "data" / "processed" / "papers.json"

OPENALEX_WORKS_URL = "https://api.openalex.org/works"
HEADERS = {
    "User-Agent": "ResearchCommons/1.0 (mailto:research-commons@chanakyauniversity.edu.in)"
}

TOPICS = [
    "computer science",
    "artificial intelligence",
    "data mining",
    "bioinformatics",
    "cloud computing",
    "machine learning",
]

TARGET_MIN_PAPERS = 550
PER_PAGE = 120


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """Reconstruct plain-text abstract from OpenAlex abstract_inverted_index."""
    if not inverted_index or not isinstance(inverted_index, dict):
        return ""
    max_pos = max(
        (pos for positions in inverted_index.values() for pos in positions),
        default=-1,
    )
    if max_pos < 0:
        return ""
    tokens = [""] * (max_pos + 1)
    for word, positions in inverted_index.items():
        for pos in positions:
            if 0 <= pos <= max_pos:
                tokens[pos] = word
    return " ".join(tok for tok in tokens if tok).strip()


def extract_short_id(openalex_id: str | None) -> str:
    """Convert an OpenAlex URI like https://openalex.org/W12345 to W12345."""
    if not openalex_id:
        return ""
    return openalex_id.rstrip("/").split("/")[-1]


def clean_doi(raw_doi: str | None) -> str | None:
    if not raw_doi:
        return None
    prefix = "https://doi.org/"
    if raw_doi.lower().startswith(prefix):
        return raw_doi[len(prefix) :]
    return raw_doi


def extract_arxiv_id(work: dict[str, Any]) -> str | None:
    ids = work.get("ids") or {}
    arxiv_url = ids.get("arxiv")
    if arxiv_url:
        return arxiv_url.rstrip("/").split("/")[-1]
    for loc in work.get("locations") or []:
        landing = (loc.get("landing_page_url") or "").lower()
        if "arxiv.org/abs/" in landing:
            return landing.split("arxiv.org/abs/")[-1].split("?")[0].strip("/")
    return None


def normalize_work(work: dict[str, Any], topic: str) -> dict[str, Any] | None:
    """Normalize a raw OpenAlex work record into the Research Commons schema."""
    paper_id = extract_short_id(work.get("id"))
    title = (work.get("title") or work.get("display_name") or "").strip()
    if not paper_id or not title:
        return None

    abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
    if not abstract:
        return None

    authors = []
    for authorship in work.get("authorships") or []:
        author_obj = authorship.get("author") or {}
        name = (author_obj.get("display_name") or "").strip()
        if name:
            authors.append(name)

    concepts = []
    for concept in work.get("concepts") or []:
        cname = (concept.get("display_name") or "").strip()
        if cname:
            concepts.append(cname)
    # Fallback to topics if concepts list is empty (newer OpenAlex schema)
    if not concepts:
        for t in work.get("topics") or []:
            tname = (t.get("display_name") or "").strip()
            if tname:
                concepts.append(tname)

    referenced_works = [
        extract_short_id(ref)
        for ref in (work.get("referenced_works") or [])
        if extract_short_id(ref)
    ]

    return {
        "id": paper_id,
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "doi": clean_doi(work.get("doi")),
        "arxiv_id": extract_arxiv_id(work),
        "source": "openalex",
        "publication_year": work.get("publication_year"),
        "citation_count": int(work.get("cited_by_count") or 0),
        "concepts": concepts[:10],
        "department_topic": topic,
        "referenced_works": referenced_works,
        "url": work.get("id"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def fetch_topic_works(
    session: requests.Session,
    topic: str,
    page: int = 1,
    per_page: int = PER_PAGE,
    sort: str | None = None,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "search": topic,
        "filter": "has_abstract:true",
        "per-page": per_page,
        "page": page,
    }
    if sort:
        params["sort"] = sort

    for attempt in range(3):
        try:
            resp = session.get(
                OPENALEX_WORKS_URL,
                params=params,
                headers=HEADERS,
                timeout=30,
            )
            if resp.status_code == 429:
                time.sleep(2 * (attempt + 1))
                continue
            resp.raise_for_status()
            data = resp.json()
            return data.get("results") or []
        except requests.RequestException as exc:
            print(f"[WARN] Attempt {attempt + 1} failed for topic='{topic}' page={page}: {exc}")
            time.sleep(1.5 * (attempt + 1))
    return []


def main() -> None:
    RAW_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    raw_by_topic: dict[str, list[dict[str, Any]]] = {}
    unique_papers: dict[str, dict[str, Any]] = {}
    raw_records_flat: list[dict[str, Any]] = []

    session = requests.Session()

    for topic in TOPICS:
        print(f"Fetching OpenAlex papers for topic: '{topic}'...")
        # Fetch page 1 by relevance and page 1 of recent/high-citation works to ensure rich citation overlap
        batch_relevance = fetch_topic_works(session, topic, page=1, per_page=80)
        time.sleep(0.25)
        batch_cited = fetch_topic_works(
            session, topic, page=1, per_page=60, sort="cited_by_count:desc"
        )
        time.sleep(0.25)

        combined = batch_relevance + batch_cited
        raw_by_topic[topic] = combined

        added_for_topic = 0
        for work in combined:
            raw_records_flat.append(work)
            normalized = normalize_work(work, topic)
            if normalized and normalized["id"] not in unique_papers:
                unique_papers[normalized["id"]] = normalized
                added_for_topic += 1

        print(
            f"  -> Retrieved {len(combined)} raw records, {added_for_topic} new unique papers "
            f"(total unique: {len(unique_papers)})"
        )

    # Top up with page 2 if unique count is below TARGET_MIN_PAPERS
    page = 2
    while len(unique_papers) < TARGET_MIN_PAPERS and page <= 4:
        for topic in TOPICS:
            if len(unique_papers) >= TARGET_MIN_PAPERS:
                break
            extra = fetch_topic_works(session, topic, page=page, per_page=60)
            time.sleep(0.25)
            raw_by_topic[topic].extend(extra)
            for work in extra:
                raw_records_flat.append(work)
                normalized = normalize_work(work, topic)
                if normalized and normalized["id"] not in unique_papers:
                    unique_papers[normalized["id"]] = normalized
        page += 1

    papers_list = list(unique_papers.values())

    # Compute internal citation edges among collected papers for quick inspection
    paper_id_set = set(unique_papers.keys())
    internal_edges = sum(
        1
        for p in papers_list
        for ref in p["referenced_works"]
        if ref in paper_id_set
    )
    total_refs = sum(len(p["referenced_works"]) for p in papers_list)

    raw_payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "OpenAlex API",
        "topics": TOPICS,
        "total_raw_records": len(raw_records_flat),
        "results_by_topic": raw_by_topic,
    }

    with RAW_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(raw_payload, f, indent=2, ensure_ascii=False)

    with PROCESSED_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(papers_list, f, indent=2, ensure_ascii=False)

    print("\nPaper harvesting complete!")
    print(f"  Raw records saved to:       {RAW_OUTPUT_PATH} ({len(raw_records_flat)} records)")
    print(f"  Processed papers saved to:  {PROCESSED_OUTPUT_PATH} ({len(papers_list)} unique papers)")
    print(f"  Total referenced_works:     {total_refs} (internal edges: {internal_edges})")


if __name__ == "__main__":
    main()
