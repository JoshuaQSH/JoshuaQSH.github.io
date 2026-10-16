"""Conservative AI selection over eligible venue-year bibliography rows."""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from refresh_ai_research_observatory import validate_review


RULE_VERSION = "ai-relevance-v1"
_EXPLICIT = (
    ("llm", re.compile(r"\b(?:llms?|large language models?|language models?|foundation models?)\b", re.I)),
    ("machine-learning", re.compile(r"\b(?:machine learning|deep learning|neural networks?|"
                                     r"reinforcement learning|generative ai|artificial intelligence|"
                                     r"ai assisted|(?:ai|ml) compilers?|ml systems?|computer vision|"
                                     r"diffusion models?|transformer models?)\b", re.I)),
    ("model-workload", re.compile(r"\b(?:model training|model inference|model serving|"
                                   r"distributed training|neural inference|gpu inference for ai)\b", re.I)),
)
_AMBIGUOUS = re.compile(r"\b(?:gpus?|compilers?|accelerators?|inference|training|"
                        r"kernels?|tensor|scheduling|optimization)\b", re.I)


def _title_key(value: str) -> str:
    return re.sub(r"[^\w]+", "", unicodedata.normalize("NFKC", value).casefold())


def _doi(value: str | None) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value.strip(), flags=re.I).lower()


def _abstract(metadata: dict) -> str:
    abstract = metadata.get("abstract")
    if isinstance(abstract, str):
        return abstract
    inverted = metadata.get("abstract_inverted_index")
    if not isinstance(inverted, dict):
        return ""
    positions = [(position, word) for word, indexes in inverted.items()
                 if isinstance(word, str) and isinstance(indexes, list)
                 for position in indexes if isinstance(position, int) and 0 <= position < 1200]
    return " ".join(word for _, word in sorted(positions))


def _metadata_text(metadata: dict) -> str:
    names = []
    primary_topic = metadata.get("primary_topic")
    if isinstance(primary_topic, dict) and isinstance(primary_topic.get("display_name"), str):
        names.append(primary_topic["display_name"])
    for key in ("topics", "keywords"):
        for item in metadata.get(key) or []:
            if isinstance(item, dict) and isinstance(item.get("display_name"), str):
                names.append(item["display_name"])
    return " ".join([_abstract(metadata), *names])


def classify_ai_work(row: dict, metadata: dict | None, review: dict | None) -> tuple[str, str]:
    """Classify one eligible bibliography row; review decisions override the rule."""
    if not isinstance(row, dict) or not row.get("title") or not row.get("track_evidence"):
        raise ValueError("An eligible bibliography row needs title and track evidence")
    if review and ("include" in review or "exclude" in review):
        validate_review(review)
        if review.get("exclude"):
            return "not-ai", f"{RULE_VERSION}:review-exclude"
        if review.get("include"):
            return "matched", f"{RULE_VERSION}:review-include"
    title = re.sub(r"[-_/]+", " ", row["title"])
    for label, pattern in _EXPLICIT:
        if pattern.search(title):
            return "matched", f"{RULE_VERSION}:title-{label}"
    if metadata:
        evidence = re.sub(r"[-_/]+", " ", _metadata_text(metadata))
        for label, pattern in _EXPLICIT:
            if pattern.search(evidence):
                return "matched", f"{RULE_VERSION}:metadata-{label}"
    if _AMBIGUOUS.search(title):
        return "unresolved", f"{RULE_VERSION}:generic-systems"
    return "not-ai", f"{RULE_VERSION}:no-evidence"


def link_openalex_metadata(rows: list[dict], works: list[dict]) -> list[dict | None]:
    """Attach only unambiguous DOI/title metadata; rows remain the denominator."""
    by_doi = defaultdict(list)
    by_title = defaultdict(list)
    for work in works:
        if not isinstance(work, dict):
            continue
        doi = _doi(work.get("doi"))
        title = work.get("title")
        if doi:
            by_doi[doi].append(work)
        if isinstance(title, str) and title:
            by_title[_title_key(title)].append(work)
    result = []
    for row in rows:
        doi = _doi(row.get("doi"))
        candidates = by_doi.get(doi, []) if doi else []
        if len(candidates) == 1:
            result.append(candidates[0])
            continue
        if candidates:
            result.append(None)
            continue
        candidates = [work for work in by_title.get(_title_key(row["title"]), [])
                      if (not doi or not _doi(work.get("doi")))
                      and (not work.get("venue_id") or work["venue_id"] == row.get("venue_id"))
                      and work.get("publication_year") in (row.get("event_year"), row.get("event_year", 0) + 1)]
        result.append(candidates[0] if len(candidates) == 1 else None)
    return result


def summarize_ai_scan(rows: list[dict], classifications: list[tuple[str, str]]) -> dict:
    """Count reviewed and unresolved decisions without treating a partial scan as complete."""
    if len(classifications) > len(rows):
        raise ValueError("More classifications than eligible bibliography rows")
    if any(decision not in {"matched", "unresolved", "not-ai"} or
           not label.startswith(f"{RULE_VERSION}:") for decision, label in classifications):
        raise ValueError("Invalid or unversioned AI classification")
    unresolved_count = (sum(decision == "unresolved" for decision, _ in classifications)
                        + len(rows) - len(classifications))
    return {"ai_matched_count": sum(decision == "matched" for decision, _ in classifications),
            "ai_reviewed_count": sum(label.startswith(f"{RULE_VERSION}:review-") for _, label in classifications),
            "ai_unresolved_count": unresolved_count,
            "scanned_count": len(classifications), "eligible_count": len(rows),
            "status": "complete" if rows and len(classifications) == len(rows) and not unresolved_count else "partial",
            "classification_rule": RULE_VERSION}


def scan_ai_bibliography(rows: list[dict], works: list[dict], reviews: dict) -> tuple[list[tuple[str, str]], dict]:
    """Scan every eligible row before a caller chooses any public sample."""
    linked = link_openalex_metadata(rows, works)
    by_doi = {_doi(key): review for key, review in reviews.items() if _doi(key)}
    decisions = []
    for row, metadata in zip(rows, linked):
        source_urls = [row.get("url"), *row.get("source_urls", [])]
        review = (reviews.get(metadata.get("id")) if metadata else None)
        if review is None:
            review = next((reviews[url] for url in source_urls if url in reviews), None)
        if review is None:
            review = by_doi.get(_doi(row.get("doi")))
        decisions.append(classify_ai_work(row, metadata, review))
    return decisions, summarize_ai_scan(rows, decisions)
