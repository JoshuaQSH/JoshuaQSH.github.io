#!/usr/bin/env python3
"""Build a static, explicitly sampled OpenAlex conference snapshot for Hugo."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
VENUES = ROOT / "data/ai_research_observatory/venues.json"
REVIEWS = ROOT / "data/ai_research_observatory/reviews.json"
MANUAL = ROOT / "data/ai_research_observatory/manual_works.json"
OUTPUT = ROOT / "static/data/ai-research-observatory.json"
CACHE = ROOT / ".cache/ai-research-observatory"
API = "https://api.openalex.org/works"
AI_WORDS = re.compile(r"\b(?:ai|ml|llm|llms|machine learning|deep learning|neural|inference|training|transformer|attention|generative|foundation model|language model|reinforcement learning|model serving|gpu accelerat|tensor|diffusion model|vision model|agentic|large model|model parallel|cuda|triton|pytorch|object detection|neural network|graph learning|data parallel|gradient)\b", re.I)
TOPICS = [("LLMs / NLP", re.compile(r"\b(?:llm|language model|transformer|tokeni[sz]|text generation|instruction tuning|retrieval.augmented)\b", re.I)),
          ("Systems", re.compile(r"\b(?:inference serv|gpu kernel|gpu schedul|distributed training|model parallel|accelerator|compiler|memory management)\b", re.I)),
          ("Computer Vision", re.compile(r"\b(?:computer vision|image classif|object detect|segmentation|vision.language)\b", re.I))]
REVIEW_FIELDS = {"first_author_sector", "countries", "area", "leadership", "award", "code_available", "resources", "funding", "compute", "compute_evidence", "review_note"}


def classify_sector(institutions):
    types = {x.get("type") for x in institutions if x.get("type")}
    if "company" in types and "education" in types:
        return "Mixed"
    if "company" in types:
        return "Industry"
    if "education" in types:
        return "University"
    if types and types <= {"nonprofit", "government", "facility", "healthcare", "other", "archive"}:
        return "Research Institute"
    return "Unknown"


def score_components(paper):
    return {key: value for key, value in (("citation", paper.get("citation_percentile")),
                                          ("venue", paper.get("prestige")),
                                          ("award", paper.get("award")),
                                          ("code", paper.get("code_available"))) if value is not None}


def abstract_text(inverted):
    if not isinstance(inverted, dict):
        return None
    words = [None] * (min(1200, 1 + max((max(pos) for pos in inverted.values() if pos), default=-1)))
    for word, positions in inverted.items():
        for pos in positions:
            if 0 <= pos < len(words):
                words[pos] = word
    return " ".join(word or "" for word in words).strip() or None


def normalize_work(work, venue):
    if not work.get("id") or not work.get("title") or work.get("type") != "conference-paper" and work.get("type") is not None:
        return None
    title = work["title"]
    if re.search(r"\b(?:workshop|tutorial|demo(?:nstration)?|poster|challenge|student research)\b", title, re.I):
        return None
    keywords = " ".join(x.get("display_name", "") for x in (work.get("keywords") or [])[:12])
    topic_text = " ".join(x.get("display_name", "") for x in (work.get("topics") or [])[:4])
    if not venue["ai_native"] and not AI_WORDS.search(" ".join((title, keywords, topic_text))):
        return None
    topic_rule = "native-venue" if venue["ai_native"] else ("title-keyword" if AI_WORDS.search(title) else "metadata-keyword")
    authors = work.get("authorships") or []
    first = next((a for a in authors if a.get("author_position") == "first"), authors[0] if authors else {})
    institutions = first.get("institutions") or []
    all_institutions = list({(i.get("id") or i.get("display_name")): i.get("display_name") for a in authors for i in a.get("institutions", []) if i.get("display_name")}.values())
    countries = list(dict.fromkeys([i.get("country_code") for i in institutions if i.get("country_code")] + (first.get("countries") or [])))
    all_types = {i.get("type") for a in authors for i in a.get("institutions", [])}
    team = "Joint" if "company" in all_types and "education" in all_types else "Industry" if "company" in all_types else "University" if "education" in all_types else "Research Institute" if all_types & {"nonprofit", "government", "facility", "healthcare"} else "Unknown"
    area = next((name for name, pattern in TOPICS if pattern.search(title)), venue["area"])
    normalized = (work.get("citation_normalized_percentile") or {}).get("value")
    try:
        normalized = max(0, min(1, float(normalized))) if normalized is not None else None
    except (TypeError, ValueError):
        normalized = None
    prestige = 1 if venue["rank"] in ("A*", "A") else .75 if venue["rank"] == "B" else None
    corresponding = [a for a in authors if a.get("is_corresponding")]
    last = next((a for a in reversed(authors) if a.get("author_position") == "last"), None)
    return {"id": work["id"], "doi": work.get("doi"), "url": work.get("doi") or (work.get("primary_location") or {}).get("landing_page_url") or work["id"],
            "title": title, "abstract": abstract_text(work.get("abstract_inverted_index")), "year": work.get("publication_year"), "date": work.get("publication_date"),
            "venue": venue["name"], "venue_id": venue["id"], "area": area, "topic_rule": topic_rule,
            "first_author": (first.get("author") or {}).get("display_name") or first.get("raw_author_name") or "Unknown",
            "first_author_id": (first.get("author") or {}).get("id"), "first_author_sector": classify_sector(institutions),
            "first_author_affiliations": [i.get("display_name") for i in institutions if i.get("display_name")], "countries": countries,
            "all_institutions": all_institutions, "team_sector": team,
            "corresponding_authors": [{"name": (a.get("author") or {}).get("display_name"), "institutions": [i.get("display_name") for i in a.get("institutions", [])]} for a in corresponding],
            "senior_author": (last.get("author") or {}).get("display_name") if last else None,
            "senior_author_affiliations": [i.get("display_name") for i in last.get("institutions", [])] if last else [],
            "leadership": "Unknown", "award": None, "code_available": None, "resources": None, "funding": None,
            "compute": {"gpu_type": None, "gpu_count": None, "gpu_hours": None, "accelerator_type": None,
                        "training_flops": None, "model_parameters": None, "training_cost": None}, "compute_evidence": None,
            "citations": int(work.get("cited_by_count") or 0), "citation_percentile": normalized, "fwci": work.get("fwci"), "prestige": prestige,
            "ranking": {k: venue[k] for k in ("ranking_scheme", "edition", "rank", "rank_url")},
            "source": "OpenAlex", "source_id": venue["source_id"], "checked_at": datetime.now(timezone.utc).isoformat()}


def deduplicate(papers):
    by_id, doi_owner = {}, {}
    for paper in papers:
        pid = paper.get("id")
        if not pid:
            continue
        doi = (paper.get("doi") or "").lower().removeprefix("https://doi.org/")
        if doi and doi in doi_owner:
            previous = by_id[doi_owner[doi]]
            if paper.get("citations", 0) > previous.get("citations", 0):
                by_id[doi_owner[doi]] = paper
            continue
        by_id[pid] = paper
        if doi:
            doi_owner[doi] = pid
    return list(by_id.values())


def validate_review(review):
    if not isinstance(review, dict) or not str(review.get("evidence_url", "")).startswith("https://"):
        raise ValueError("Every review needs an HTTPS evidence URL")
    if review.get("leadership", "Unknown") not in {"Unknown", "Industry-led", "Academia-led", "Joint"}:
        raise ValueError("Invalid leadership classification")
    if review.get("first_author_sector", "Unknown") not in {"Unknown", "Industry", "University", "Research Institute", "Mixed"}:
        raise ValueError("Invalid first-author sector")
    for field in ("award", "code_available"):
        if field in review and review[field] is not None and type(review[field]) is not bool:
            raise ValueError(f"{field} must be true, false, or null")
    if "compute" in review and not isinstance(review["compute"], dict):
        raise ValueError("compute must be an object")
    if "countries" in review and (not isinstance(review["countries"], list) or any(not isinstance(code, str) or not re.fullmatch(r"[A-Z]{2}", code) for code in review["countries"])):
        raise ValueError("countries must be a list of uppercase two-letter codes")
    if "exclude" in review and type(review["exclude"]) is not bool:
        raise ValueError("exclude must be a boolean")
    if review.get("exclude") and not review.get("review_note"):
        raise ValueError("An exclusion needs a reason in review_note")


def fetch_work_by_id(work_id, key):
    if not re.fullmatch(r"https://openalex.org/W\d+", work_id):
        raise ValueError("Manual work needs an OpenAlex work ID")
    url = API + "/" + work_id.rsplit("/", 1)[-1]
    if key:
        url += "?" + urlencode({"api_key": key})
    request = Request(url, headers={"User-Agent": "JoshuaQSH-AIResearchObservatory/1.0", "Accept": "application/json"})
    with urlopen(request, timeout=40) as response:
        return json.load(response)


def fetch_works(venue, year, cap, key):
    params = {"filter": f"publication_year:{year},primary_location.source.id:{venue['source_id']},type:conference-paper",
              "per_page": min(cap, 100), "sort": "publication_date:asc"}
    cache_key = hashlib.sha256(urlencode(params).encode()).hexdigest()
    cache_path = CACHE / f"{cache_key}.json"
    if cache_path.exists() and time.time() - cache_path.stat().st_mtime < 6 * 3600:
        cached = json.loads(cache_path.read_text())
        return cached.get("results", []), (cached.get("meta") or {}).get("count", 0), datetime.fromtimestamp(cache_path.stat().st_mtime, timezone.utc).isoformat(), True
    if key:
        params["api_key"] = key
    url = API + "?" + urlencode(params)
    for attempt in range(4):
        try:
            request = Request(url, headers={"User-Agent": "JoshuaQSH-AIResearchObservatory/1.0 (academic metadata dashboard)", "Accept": "application/json"})
            with urlopen(request, timeout=40) as response:
                payload = json.load(response)
            CACHE.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(payload, separators=(",", ":")))
            return payload.get("results", []), (payload.get("meta") or {}).get("count", 0), datetime.now(timezone.utc).isoformat(), False
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            if attempt == 3:
                raise RuntimeError(f"OpenAlex request failed: {exc}") from exc
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def refresh(start, end, cap, selected=None):
    venues = json.loads(VENUES.read_text())
    reviews = json.loads(REVIEWS.read_text())
    manual = json.loads(MANUAL.read_text()) if MANUAL.exists() else []
    for review in reviews.values():
        validate_review(review)
    previous = json.loads(OUTPUT.read_text()) if OUTPUT.exists() else {"papers": [], "coverage": []}
    papers = {(p["id"]): p for p in previous.get("papers", [])}
    coverage = {(c["venue_id"], c["year"]): c for c in previous.get("coverage", [])}
    key = os.getenv("OPENALEX_API_KEY", "").strip()
    for venue in venues:
        if selected and venue["id"] not in selected:
            continue
        for year in range(start, end + 1):
            print(f"Fetching {venue['name']} {year}", flush=True)
            try:
                works, total, fetched_at, cached = fetch_works(venue, year, cap, key)
                for paper_id, previous_paper in list(papers.items()):
                    if previous_paper.get("venue_id") == venue["id"] and previous_paper.get("year") == year:
                        del papers[paper_id]
                accepted = []
                for work in works:
                    paper = normalize_work(work, venue)
                    if paper:
                        paper["checked_at"] = fetched_at
                        accepted.append(paper)
                        papers[paper["id"]] = paper
                coverage[(venue["id"], year)] = {"venue_id": venue["id"], "venue": venue["name"], "year": year,
                    "source_total": total, "scanned": len(works), "included": len(accepted), "partial": not total or len(works) < total,
                    "source_id": venue["source_id"], "status": "no-source-matches" if not total else "sample" if len(works) < total else "source-scan",
                    "checked_at": fetched_at, "cache_hit": cached}
            except Exception as exc:
                print(f"WARNING: {venue['name']} {year}: {exc}", file=sys.stderr)
                coverage[(venue["id"], year)] = {"venue_id": venue["id"], "venue": venue["name"], "year": year,
                    "source_total": None, "scanned": 0, "included": 0, "partial": True, "status": "error", "error": str(exc),
                    "checked_at": datetime.now(timezone.utc).isoformat()}
            time.sleep(.12)
    venue_by_id = {venue["id"]: venue for venue in venues}
    for item in manual:
        if not isinstance(item, dict) or not str(item.get("evidence_url", "")).startswith("https://"):
            raise ValueError("Manual work needs an HTTPS proceedings evidence URL")
        venue = venue_by_id.get(item.get("venue_id"))
        if not venue or not isinstance(item.get("year"), int) or not 2020 <= item["year"] <= datetime.now().year:
            raise ValueError("Manual work needs a known venue and valid year")
        if selected and venue["id"] not in selected:
            continue
        try:
            work = fetch_work_by_id(item["id"], key)
            source = ((work.get("primary_location") or {}).get("source") or {}).get("id")
            if work.get("id") != item["id"] or work.get("publication_year") != item["year"] or work.get("type") != "conference-paper" or source != venue["source_id"]:
                raise ValueError("Manual work does not match its verified venue, year, and source")
            paper = normalize_work(work, venue)
            if not paper:
                raise ValueError("Manual work fails the conference-paper and topic filters")
            paper["manual_evidence_url"] = item["evidence_url"]
            papers[paper["id"]] = paper
        except Exception as exc:
            print(f"WARNING: manual work {item.get('id')}: {exc}", file=sys.stderr)
            if item.get("id") not in papers:
                raise RuntimeError(f"Cannot add unverified manual work {item.get('id')}") from exc
    result = []
    for paper in deduplicate(papers.values()):
        review = reviews.get(paper["id"]) or reviews.get((paper.get("doi") or "").lower())
        if review:
            validate_review(review)
            if review.get("exclude"):
                continue
            for field in REVIEW_FIELDS:
                if field in review:
                    paper[field] = review[field]
            paper["review"] = {"evidence_url": review["evidence_url"], "reviewer": review.get("reviewer"), "date": review.get("date"), "note": review.get("review_note")}
        result.append(paper)
    result.sort(key=lambda p: (p.get("year") or 0, p.get("citations") or 0), reverse=True)
    snapshot = {"generated_at": datetime.now(timezone.utc).isoformat(), "source": "OpenAlex", "scope": "Capped venue-year sample; not complete conference output", "cap_per_venue_year": cap,
                "venues": venues, "coverage": sorted(coverage.values(), key=lambda c: (c["year"], c["venue_id"])), "papers": result}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"Wrote {len(result)} real records to {OUTPUT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-year", type=int, default=max(2020, datetime.now().year - 1))
    parser.add_argument("--to-year", type=int, default=datetime.now().year)
    parser.add_argument("--cap", type=int, default=25)
    parser.add_argument("--venues", nargs="*", help="Optional venue IDs")
    args = parser.parse_args()
    if not 2020 <= args.from_year <= args.to_year <= datetime.now().year or not 1 <= args.cap <= 100:
        parser.error("years must be 2020..current and cap must be 1..100")
    refresh(args.from_year, args.to_year, args.cap, args.venues)
