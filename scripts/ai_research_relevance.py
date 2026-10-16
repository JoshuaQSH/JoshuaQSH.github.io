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
_PRIMARY_AI_TOPICS = {"artificial intelligence", "machine learning", "deep learning",
                      "natural language processing", "computer vision", "reinforcement learning",
                      "large language models", "generative artificial intelligence", "ml systems"}
_OWN_AI_ACTION = re.compile(r"\b(?:we|our (?:system|method|approach|compiler|framework|model|"
                            r"scheduler|pipeline|implementation)|this (?:paper|work|study|system))"
                            r"\s+(?:\w+ly\s+)?(?:train\w*|serv\w*|deploy\w*|optimi[sz]\w*|"
                            r"accelerat\w*|compil\w*|infer\w*|fine.tun\w*|evaluat\w*|"
                            r"benchmark\w*|appl\w*|use[ds]?|build\w*)\b", re.I)
_NEGATIVE_CONTEXT = re.compile(r"\b(?:not|never|without|excluded|unrelated|"
                               r"outside (?:the )?scope|out of scope|beyond (?:the )?scope|"
                               r"rather than|future work|avoid\w*|"
                               r"only as (?:a )?(?:baseline|example|comparison))\b", re.I)
_SCOPE_EXCLUSION = re.compile(r"\b(?:outside (?:the )?scope|out of scope|beyond (?:the )?scope|"
                              r"unrelated|future work)\b", re.I)
_SHORT_AI_REFERENCE = re.compile(r"\b(?:ai|ml)\b", re.I)


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


def _metadata_match(metadata: dict) -> str | None:
    negated_ai = False
    scope_exclusion = False
    positive_label = None
    abstract = re.sub(r"[-_/]+", " ", _abstract(metadata))
    for clause in re.split(r"[.!?;,]+|\b(?:but|while|whereas|although|however|and)\b", abstract, flags=re.I):
        labels = [label for label, pattern in _EXPLICIT if pattern.search(clause)]
        if labels or _SHORT_AI_REFERENCE.search(clause):
            if _SCOPE_EXCLUSION.search(clause):
                scope_exclusion = True
            elif _NEGATIVE_CONTEXT.search(clause):
                negated_ai = True
            elif labels and _OWN_AI_ACTION.search(clause) and positive_label is None:
                positive_label = f"abstract-{labels[0]}"
    if scope_exclusion:
        return None
    if positive_label:
        return positive_label
    if negated_ai:
        return None
    primary_topic = metadata.get("primary_topic")
    if isinstance(primary_topic, dict):
        name = primary_topic.get("display_name")
        if isinstance(name, str) and name.casefold().strip() in _PRIMARY_AI_TOPICS:
            return "primary-topic"
    return None


def classify_ai_work(row: dict, metadata: dict | None, review: dict | None) -> tuple[str, str]:
    """Classify one eligible bibliography row; review decisions override the rule."""
    if not isinstance(row, dict) or not row.get("title") or not row.get("track_evidence"):
        raise ValueError("An eligible bibliography row needs title and track evidence")
    if review and ("ai_relevance" in review or "include" in review):
        validate_review(review)
        relevance = review.get("ai_relevance") or ("include" if review.get("include") else None)
        if relevance == "exclude":
            return "not-ai", f"{RULE_VERSION}:review-exclude"
        if relevance == "include":
            return "matched", f"{RULE_VERSION}:review-include"
    title = re.sub(r"[-_/]+", " ", row["title"])
    for label, pattern in _EXPLICIT:
        if pattern.search(title):
            return "matched", f"{RULE_VERSION}:title-{label}"
    if metadata:
        evidence = _metadata_match(metadata)
        if evidence:
            return "matched", f"{RULE_VERSION}:metadata-{evidence}"
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
    by_url = defaultdict(list)
    by_doi = defaultdict(list)
    for review in reviews.values():
        validate_review(review)
        if review.get("ai_relevance") or review.get("include"):
            url = review.get("bibliography_url")
            if url:
                by_url[url].append(review)
            doi = _doi(review.get("bibliography_doi"))
            if doi:
                by_doi[doi].append(review)
    decisions = []
    for row, metadata in zip(rows, linked):
        source_urls = [row.get("url"), *row.get("source_urls", [])]
        candidates = [review for url in source_urls for review in by_url.get(url, ())]
        candidates.extend(by_doi.get(_doi(row.get("doi")), ()))
        review = next((candidate for candidate in candidates
                       if candidate.get("ai_relevance") == "exclude"), None)
        if review is None:
            review = next((candidate for candidate in candidates
                           if candidate.get("ai_relevance") == "include" or candidate.get("include")), None)
        decisions.append(classify_ai_work(row, metadata, review))
    return decisions, summarize_ai_scan(rows, decisions)
