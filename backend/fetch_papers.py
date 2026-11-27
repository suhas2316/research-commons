"""
Fetch real academic papers from BOTH the OpenAlex API and the arXiv API
(no API keys required). Queries 6 university department topics, reconstructs
OpenAlex abstracts from abstract_inverted_index, parses arXiv Atom XML feeds,
extracts referenced_works for citation graph analytics, and saves raw and
normalized JSON datasets.
"""

from __future__ import annotations

import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_OUTPUT_PATH = BASE_DIR / "data" / "raw" / "papers_raw.json"
PROCESSED_OUTPUT_PATH = BASE_DIR / "data" / "processed" / "papers.json"

OPENALEX_WORKS_URL = "https://api.openalex.org/works"
ARXIV_API_URL = "https://export.arxiv.org/api/query"
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

ARXIV_CATEGORY_MAP = {
    "cs.AI": "Artificial Intelligence",
    "cs.LG": "Machine Learning",
    "cs.CL": "Natural Language Processing",
    "cs.CV": "Computer Vision",
    "cs.DB": "Databases",
    "cs.DC": "Distributed & Cloud Computing",
    "cs.IR": "Information Retrieval",
    "cs.SE": "Software Engineering",
    "cs.NE": "Neural & Evolutionary Computing",
    "stat.ML": "Statistical Machine Learning",
    "q-bio.GN": "Genomics",
    "q-bio.QM": "Quantitative Bioinformatics",
    "q-bio.BM": "Biomolecules",
}

TARGET_MIN_OPENALEX = 550
PER_PAGE = 120
ARXIV_PER_TOPIC = 35


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


def fetch_arxiv_topic(
    session: requests.Session,
    topic: str,
    max_results: int = ARXIV_PER_TOPIC,
) -> tuple[str, list[dict[str, Any]]]:
    """Fetch Atom XML entries from arXiv API for a topic."""
    params = {
        "search_query": f'all:"{topic}"',
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    for attempt in range(3):
        try:
            resp = session.get(
                ARXIV_API_URL,
                params=params,
                headers=HEADERS,
                timeout=30,
            )
            if resp.status_code in {429, 503}:
                time.sleep(3 * (attempt + 1))
                continue
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            entries: list[dict[str, Any]] = []
            for entry in root.findall("atom:entry", ns):
                raw_id = (entry.findtext("atom:id", default="", namespaces=ns) or "").strip()
                title = " ".join(
                    (entry.findtext("atom:title", default="", namespaces=ns) or "").split()
                )
                summary = " ".join(
                    (entry.findtext("atom:summary", default="", namespaces=ns) or "").split()
                )
                published = (
                    entry.findtext("atom:published", default="", namespaces=ns) or ""
                ).strip()
                doi = (entry.findtext("arxiv:doi", default="", namespaces=ns) or "").strip() or None
                authors = [
                    " ".join((a.findtext("atom:name", default="", namespaces=ns) or "").split())
                    for a in entry.findall("atom:author", ns)
                ]
                authors = [a for a in authors if a]
                categories = [
                    c.attrib.get("term", "").strip()
                    for c in entry.findall("atom:category", ns)
                    if c.attrib.get("term", "").strip()
                ]
                entries.append(
                    {
                        "id": raw_id,
                        "title": title,
                        "summary": summary,
                        "published": published,
                        "doi": doi,
                        "authors": authors,
                        "categories": categories,
                    }
                )
            return resp.text, entries
        except (requests.RequestException, ET.ParseError) as exc:
            print(f"[WARN] arXiv attempt {attempt + 1} failed for topic='{topic}': {exc}")
            time.sleep(2.5 * (attempt + 1))
    return "", []


def normalize_arxiv_entry(entry: dict[str, Any], topic: str) -> dict[str, Any] | None:
    """Normalize a parsed arXiv entry into the Research Commons paper schema."""
    raw_url = (entry.get("id") or "").strip()
    title = (entry.get("title") or "").strip()
    abstract = (entry.get("summary") or "").strip()
    if not raw_url or not title or not abstract:
        return None

    arxiv_full = raw_url.rstrip("/").split("/abs/")[-1]
    arxiv_base = re.sub(r"v\d+$", "", arxiv_full)
    paper_id = f"arXiv_{arxiv_base}"

    pub_year: int | None = None
    published = entry.get("published") or ""
    if len(published) >= 4 and published[:4].isdigit():
        pub_year = int(published[:4])

    concepts: list[str] = [topic.title()]
    for cat in entry.get("categories") or []:
        mapped = ARXIV_CATEGORY_MAP.get(cat, cat)
        if mapped not in concepts:
            concepts.append(mapped)

    return {
        "id": paper_id,
        "title": title,
        "abstract": abstract,
        "authors": entry.get("authors") or [],
        "doi": clean_doi(entry.get("doi")),
        "arxiv_id": arxiv_base,
        "source": "arxiv",
        "publication_year": pub_year,
        "citation_count": 0,
        "concepts": concepts[:10],
        "department_topic": topic,
        "referenced_works": [],
        "url": raw_url,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    RAW_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    openalex_raw_by_topic: dict[str, list[dict[str, Any]]] = {}
    arxiv_raw_by_topic: dict[str, list[dict[str, Any]]] = {}
    unique_papers: dict[str, dict[str, Any]] = {}
    seen_arxiv_ids: set[str] = set()
    seen_dois: set[str] = set()
    raw_openalex_count = 0
    raw_arxiv_count = 0

    session = requests.Session()

    # 1. Harvest from OpenAlex API
    for topic in TOPICS:
        print(f"[OpenAlex] Fetching papers for topic: '{topic}'...")
        batch_relevance = fetch_topic_works(session, topic, page=1, per_page=80)
        time.sleep(0.25)
        batch_cited = fetch_topic_works(
            session, topic, page=1, per_page=60, sort="cited_by_count:desc"
        )
        time.sleep(0.25)

        combined = batch_relevance + batch_cited
        openalex_raw_by_topic[topic] = combined
        raw_openalex_count += len(combined)

        added_for_topic = 0
        for work in combined:
            normalized = normalize_work(work, topic)
            if normalized and normalized["id"] not in unique_papers:
                unique_papers[normalized["id"]] = normalized
                if normalized.get("arxiv_id"):
                    seen_arxiv_ids.add(re.sub(r"v\d+$", "", str(normalized["arxiv_id"])))
                if normalized.get("doi"):
                    seen_dois.add(str(normalized["doi"]).lower())
                added_for_topic += 1

        print(
            f"  -> Retrieved {len(combined)} raw records, {added_for_topic} new unique OpenAlex papers "
            f"(total unique: {len(unique_papers)})"
        )

    # Top up OpenAlex if below TARGET_MIN_OPENALEX
    page = 2
    while len(unique_papers) < TARGET_MIN_OPENALEX and page <= 4:
        for topic in TOPICS:
            if len(unique_papers) >= TARGET_MIN_OPENALEX:
                break
            extra = fetch_topic_works(session, topic, page=page, per_page=60)
            time.sleep(0.25)
            openalex_raw_by_topic[topic].extend(extra)
            raw_openalex_count += len(extra)
            for work in extra:
                normalized = normalize_work(work, topic)
                if normalized and normalized["id"] not in unique_papers:
                    unique_papers[normalized["id"]] = normalized
                    if normalized.get("arxiv_id"):
                        seen_arxiv_ids.add(re.sub(r"v\d+$", "", str(normalized["arxiv_id"])))
                    if normalized.get("doi"):
                        seen_dois.add(str(normalized["doi"]).lower())
        page += 1

    # 2. Harvest from arXiv API
    for topic in TOPICS:
        print(f"[arXiv] Fetching preprints for topic: '{topic}'...")
        _, entries = fetch_arxiv_topic(session, topic, max_results=ARXIV_PER_TOPIC)
        arxiv_raw_by_topic[topic] = entries
        raw_arxiv_count += len(entries)

        added_arxiv = 0
        for entry in entries:
            normalized = normalize_arxiv_entry(entry, topic)
            if not normalized:
                continue
            aid = str(normalized.get("arxiv_id") or "")
            doi_lower = str(normalized.get("doi") or "").lower()
            if (
                normalized["id"] in unique_papers
                or (aid and aid in seen_arxiv_ids)
                or (doi_lower and doi_lower in seen_dois)
            ):
                continue
            unique_papers[normalized["id"]] = normalized
            if aid:
                seen_arxiv_ids.add(aid)
            if doi_lower:
                seen_dois.add(doi_lower)
            added_arxiv += 1

        print(
            f"  -> Retrieved {len(entries)} raw entries, {added_arxiv} new unique arXiv papers "
            f"(total unique: {len(unique_papers)})"
        )
        time.sleep(1.2)

    papers_list = list(unique_papers.values())

    # Compute source breakdown & internal citation edges for quick inspection
    openalex_total = sum(1 for p in papers_list if p["source"] == "openalex")
    arxiv_total = sum(1 for p in papers_list if p["source"] == "arxiv")
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
        "sources": ["OpenAlex API", "arXiv API"],
        "topics": TOPICS,
        "total_raw_records": raw_openalex_count + raw_arxiv_count,
        "raw_counts_by_source": {
            "openalex": raw_openalex_count,
            "arxiv": raw_arxiv_count,
        },
        "openalex_results_by_topic": openalex_raw_by_topic,
        "arxiv_results_by_topic": arxiv_raw_by_topic,
    }

    with RAW_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(raw_payload, f, indent=2, ensure_ascii=False)

    with PROCESSED_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(papers_list, f, indent=2, ensure_ascii=False)

    print("\nMulti-source paper harvesting complete!")
    print(f"  Raw records saved to:       {RAW_OUTPUT_PATH} ({raw_openalex_count} OpenAlex + {raw_arxiv_count} arXiv)")
    print(f"  Processed papers saved to:  {PROCESSED_OUTPUT_PATH} ({len(papers_list)} unique: {openalex_total} openalex, {arxiv_total} arxiv)")
    print(f"  Total referenced_works:     {total_refs} (internal edges: {internal_edges})")


if __name__ == "__main__":
    main()
