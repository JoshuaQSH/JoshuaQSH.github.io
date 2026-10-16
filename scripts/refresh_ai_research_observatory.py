#!/usr/bin/env python3
"""Build a sourced, explicitly sampled conference snapshot for Hugo."""
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
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from ai_research_sources import (ANTHOLOGY_VOLUMES, PMLR_VOLUMES, PMLR_OTHER, merge_official, normalize_official,
                                 official_source, parse_acl, parse_cvf, parse_neurips, parse_pmlr,
                                 repo_slug, select_records, title_key)

ROOT = Path(__file__).resolve().parents[1]
VENUES = ROOT / "data/ai_research_observatory/venues.json"
REVIEWS = ROOT / "data/ai_research_observatory/reviews.json"
MANUAL = ROOT / "data/ai_research_observatory/manual_works.json"
FEATURED = ROOT / "data/ai_research_observatory/featured_proceedings.json"
OUTPUT = ROOT / "static/data/ai-research-observatory.json"
CACHE = ROOT / ".cache/ai-research-observatory"
API = "https://api.openalex.org/works"


class RateLimited(RuntimeError):
    """The provider exhausted its request budget; stop further API attempts."""


class AuthenticationFailed(RuntimeError):
    """The OpenAlex credential is unavailable or invalid; abort the refresh."""


AI_WORDS = re.compile(r"\b(?:ai|ml|llm|llms|machine learning|deep learning|neural|inference|training|transformer|attention|generative|foundation model|language model|reinforcement learning|model serving|gpu accelerat|tensor|diffusion model|vision model|agentic|large model|model parallel|cuda|triton|pytorch|object detection|neural network|graph learning|data parallel|gradient)\b", re.I)
TOPICS = [("LLMs / NLP", re.compile(r"\b(?:llm|language model|transformer|tokeni[sz]|text generation|instruction tuning|retrieval.augmented)\b", re.I)),
          ("Systems", re.compile(r"\b(?:inference serv|gpu kernel|gpu schedul|distributed training|model parallel|accelerator|compiler|memory management)\b", re.I)),
          ("Computer Vision", re.compile(r"\b(?:computer vision|image classif|object detect|segmentation|vision.language)\b", re.I))]
REVIEW_FIELDS = {"first_author_sector", "countries", "area", "leadership", "award", "code_available", "resources", "funding", "compute", "compute_evidence", "review_note",
                 "repository_url", "repository_evidence_url", "adoption_status", "adoption_evidence_url", "maintenance_status", "maintenance_evidence_url"}


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
    if not work.get("id") or not work.get("title") or work.get("type") not in (None, "conference-paper", "article"):
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
            "leadership": "Unknown", "award": None, "code_available": None, "code_url": None, "code_evidence_url": None,
            "repository_url": None, "repository_evidence_url": None,
            "repository_association_status": "unknown", "repository_access_status": "unknown", "github": None,
            "adoption_status": "Unknown", "adoption_evidence_url": None,
            "maintenance_status": "Unknown", "maintenance_evidence_url": None,
            "resources": None, "funding": None,
            "compute": {"gpu_type": None, "gpu_count": None, "gpu_hours": None, "accelerator_type": None,
                        "training_flops": None, "model_parameters": None, "training_cost": None}, "compute_evidence": None,
            "citations": int(work.get("cited_by_count") or 0), "citation_percentile": normalized, "fwci": work.get("fwci"), "prestige": prestige,
            "ranking": {k: venue[k] for k in ("ranking_scheme", "edition", "rank", "rank_url")},
            "source": "OpenAlex", "sources": [{"provider": "OpenAlex", "url": work["id"]}],
            "source_id": venue["source_id"], "checked_at": datetime.now(timezone.utc).isoformat()}


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
    if "include" in review and type(review["include"]) is not bool:
        raise ValueError("include must be a boolean")
    if review.get("include") and review.get("exclude"):
        raise ValueError("A review cannot include and exclude the same work")
    if review.get("include") and not review.get("review_note"):
        raise ValueError("An inclusion needs a reason in review_note")
    if review.get("exclude") and not review.get("review_note"):
        raise ValueError("An exclusion needs a reason in review_note")
    if "bibliography_doi" in review:
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", str(review["bibliography_doi"]), flags=re.I)
        if not re.fullmatch(r"10\.\d{4,9}/\S+", doi):
            raise ValueError("bibliography_doi must be a DOI")
    if "bibliography_url" in review:
        parsed = urlparse(str(review["bibliography_url"]))
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("bibliography_url must be an HTTPS paper URL")
    if "repository_url" in review:
        if not repo_slug(review["repository_url"]) or not str(review.get("repository_evidence_url", "")).startswith("https://"):
            raise ValueError("A reviewed repository needs a GitHub URL and HTTPS association evidence")
    for field, options in (("adoption_status", {"Unknown", "integration", "pilot", "production"}),
                           ("maintenance_status", {"Unknown", "active", "inactive"})):
        if field in review and review[field] not in options:
            raise ValueError(f"Invalid {field}")
        if field in review and review[field] != "Unknown" and not str(review.get(field.replace("_status", "_evidence_url"), "")).startswith("https://"):
            raise ValueError(f"{field} needs a specific HTTPS evidence URL")
    if review.get("maintenance_status", "Unknown") != "Unknown":
        try:
            reviewed_at = datetime.fromisoformat(review["date"])
            if reviewed_at.date() > datetime.now(timezone.utc).date():
                raise ValueError("Maintenance review date is in the future")
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Maintenance review needs a valid, non-future ISO date") from exc


def fetch_official_index(venue, year):
    provider, url = official_source(venue["id"], year)
    pages = ([f"https://aclanthology.org/{year}.{venue['id']}-{track}/"
              for track in ANTHOLOGY_VOLUMES[venue["id"]][year]] if provider == "ACL Anthology" else (
             [f"https://openaccess.thecvf.com/CVPR2020.py?day={day}" for day in ("2020-06-16", "2020-06-17", "2020-06-18")]
             if venue["id"] == "cvpr" and year == 2020 else [url]))
    rows, timestamps = [], []
    for page_url in pages:
        cache_path = CACHE / ("official-" + hashlib.sha256(page_url.encode()).hexdigest() + ".html")
        if cache_path.exists() and time.time() - cache_path.stat().st_mtime < 24 * 3600:
            content = cache_path.read_text()
            checked_at = datetime.fromtimestamp(cache_path.stat().st_mtime, timezone.utc).isoformat()
        else:
            request = Request(page_url, headers={"User-Agent": "JoshuaQSH-AIResearchObservatory/1.0", "Accept": "text/html"})
            with urlopen(request, timeout=60) as response:
                content = response.read().decode("utf-8", "replace")
            CACHE.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(content)
            checked_at = datetime.now(timezone.utc).isoformat()
        timestamps.append(checked_at)
        if venue["id"] == "neurips":
            rows.extend(parse_neurips(content, year))
        elif provider == "PMLR":
            volume = PMLR_VOLUMES[year] if venue["id"] == "icml" else PMLR_OTHER[venue["id"]][year]
            rows.extend(parse_pmlr(content, year, volume))
        elif provider == "ACL Anthology":
            rows.extend(parse_acl(content, year, venue["id"]))
        else:
            rows.extend(parse_cvf(content, venue["id"], year))
    if not rows:
        raise ValueError(f"No main-track paper entries in {url}; source format may have changed")
    return list({row["url"]: row for row in rows}.values()), min(timestamps)


def fetch_github_metadata(repository_url, token):
    slug = repo_slug(repository_url)
    if not slug:
        raise ValueError("Invalid GitHub repository URL")
    headers = {"User-Agent": "JoshuaQSH-AIResearchObservatory/1.0", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"https://api.github.com/repos/{slug}", headers=headers)
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if not isinstance(payload.get("stargazers_count"), int):
        raise ValueError("GitHub response has no star count")
    return {"url": payload.get("html_url") or repository_url, "stars": payload["stargazers_count"],
            "pushed_at": payload.get("pushed_at"), "archived": payload.get("archived"),
            "fork": payload.get("fork"), "checked_at": datetime.now(timezone.utc).isoformat()}


def fetch_work_by_id(work_id, key):
    if not re.fullmatch(r"https://openalex.org/W\d+", work_id):
        raise ValueError("Manual work needs an OpenAlex work ID")
    url = API + "/" + work_id.rsplit("/", 1)[-1]
    headers = {"User-Agent": "JoshuaQSH-AIResearchObservatory/1.0", "Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=40) as response:
        return json.load(response)


def fetch_works(venue, year, cap, key):
    params = {"filter": f"publication_year:{year},primary_location.source.id:{venue['source_id']}",
              "per_page": min(cap, 100), "sort": "publication_date:asc"}
    cache_key = hashlib.sha256(urlencode(params).encode()).hexdigest()
    cache_path = CACHE / f"{cache_key}.json"
    if cache_path.exists() and time.time() - cache_path.stat().st_mtime < 6 * 3600:
        cached = json.loads(cache_path.read_text())
        return cached.get("results", []), (cached.get("meta") or {}).get("count", 0), datetime.fromtimestamp(cache_path.stat().st_mtime, timezone.utc).isoformat(), True
    url = API + "?" + urlencode(params)
    headers = {"User-Agent": "JoshuaQSH-AIResearchObservatory/1.0 (academic metadata dashboard)",
               "Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    for attempt in range(4):
        try:
            request = Request(url, headers=headers)
            with urlopen(request, timeout=40) as response:
                payload = json.load(response)
            CACHE.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(payload, separators=(",", ":")))
            return payload.get("results", []), (payload.get("meta") or {}).get("count", 0), datetime.now(timezone.utc).isoformat(), False
        except HTTPError as exc:
            if exc.code == 429:
                raise RateLimited("OpenAlex request budget exhausted (HTTP 429)") from exc
            if exc.code in (401, 403):
                raise AuthenticationFailed("OpenAlex authentication failed; check the activated API key") from exc
            if attempt == 3:
                raise RuntimeError(f"OpenAlex request failed: {exc}") from exc
            time.sleep(2 ** attempt)
        except (URLError, TimeoutError, ValueError) as exc:
            if attempt == 3:
                raise RuntimeError(f"OpenAlex request failed: {exc}") from exc
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def cached_works(venue, year, cap):
    params = {"filter": f"publication_year:{year},primary_location.source.id:{venue['source_id']}",
              "per_page": min(cap, 100), "sort": "publication_date:asc"}
    path = CACHE / (hashlib.sha256(urlencode(params).encode()).hexdigest() + ".json")
    if not path.exists():
        return None
    payload = json.loads(path.read_text())
    return payload.get("results", []), (payload.get("meta") or {}).get("count", 0), datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(), True


def refresh(start, end, cap, selected=None, official_cap=250, github_cap=30, skip_openalex=False, cached_only=False):
    venues = json.loads(VENUES.read_text())
    reviews = json.loads(REVIEWS.read_text())
    manual = json.loads(MANUAL.read_text()) if MANUAL.exists() else []
    featured = json.loads(FEATURED.read_text()) if FEATURED.exists() else []
    for review in reviews.values():
        validate_review(review)
    previous = json.loads(OUTPUT.read_text()) if OUTPUT.exists() else {"papers": [], "coverage": []}
    venue_ids = {venue["id"] for venue in venues}
    papers = {p["id"]: p for p in previous.get("papers", []) if p.get("venue_id") in venue_ids}
    previous_by_title = {title_key(p): p for p in previous.get("papers", [])}
    coverage = {(c["venue_id"], c["year"]): c for c in previous.get("coverage", []) if c.get("venue_id") in venue_ids}
    key = os.getenv("OPENALEX_API_KEY", "").strip()
    openalex_blocked = False
    for venue in venues:
        if selected and venue["id"] not in selected:
            continue
        for year in range(start, end + 1):
            print(f"Fetching {venue['name']} {year}", flush=True)
            prior = [p for p in papers.values() if p.get("venue_id") == venue["id"] and p.get("year") == year]
            row = dict(coverage.get((venue["id"], year), {"venue_id": venue["id"], "venue": venue["name"], "year": year}))
            row.setdefault("source_total", None)
            row.setdefault("scanned", 0)
            row.setdefault("included", 0)
            row.setdefault("source_id", venue.get("source_id"))
            row.setdefault("status", "unmapped" if not venue.get("source_id") else "pending")
            source = official_source(venue["id"], year) if official_cap else None
            openalex_ok, official_ok = False, False
            openalex_papers, official_papers = [], []
            if not skip_openalex and venue.get("source_id") and not openalex_blocked:
                try:
                    fetched = cached_works(venue, year, cap) if cached_only else fetch_works(venue, year, cap, key)
                    if fetched is None:
                        row.update({"status": "not-refreshed", "partial": True})
                    else:
                        works, total, fetched_at, cached = fetched
                        openalex_papers = [p for work in works if (p := normalize_work(work, venue))]
                        for paper in openalex_papers:
                            paper["checked_at"] = fetched_at
                        row.update({"source_total": total, "scanned": len(works), "included": len(openalex_papers),
                            "partial": not total or len(works) < total, "source_id": venue["source_id"],
                            "status": "no-index-records" if not total else "sample" if len(works) < total else "source-scan",
                            "checked_at": fetched_at, "cache_hit": cached})
                        row.pop("error", None)
                        openalex_ok = True
                except RateLimited as exc:
                    print(f"WARNING: {exc}; remaining OpenAlex calls skipped", file=sys.stderr)
                    openalex_blocked = True
                    row.update({"status": "rate-limited", "partial": True, "error": str(exc)})
                except AuthenticationFailed:
                    raise
                except Exception as exc:
                    print(f"WARNING: OpenAlex {venue['name']} {year}: {exc}", file=sys.stderr)
                    row.update({"partial": True, "status": "error", "error": str(exc),
                        "checked_at": datetime.now(timezone.utc).isoformat()})
                if not cached_only:
                    time.sleep(.12)
            elif openalex_blocked and venue.get("source_id"):
                row.update({"status": "rate-limited", "partial": True,
                            "error": "OpenAlex request budget exhausted earlier in this refresh"})
            elif not venue.get("source_id"):
                row.update({"source_total": None, "status": "unmapped", "partial": True,
                            "source_id": None})
            if source:
                try:
                    raw, checked_at = fetch_official_index(venue, year)
                    forced = {item["url"] for item in featured if item.get("venue_id") == venue["id"] and item.get("year") == year}
                    available_urls = {item["url"] for item in raw}
                    if not forced <= available_urls:
                        raise ValueError("A featured paper is absent from its official proceedings index")
                    sampled = select_records(raw, official_cap, forced)
                    official_papers = [normalize_official(item, venue, year, source[0]) for item in sampled]
                    row.update({"official_provider": source[0], "official_url": source[1], "official_total": len(raw),
                        "official_sampled": len(sampled), "official_checked_at": checked_at, "official_status": "sample" if len(sampled) < len(raw) else "full-index"})
                    row.pop("official_error", None)
                    official_ok = True
                except Exception as exc:
                    print(f"WARNING: proceedings {venue['name']} {year}: {exc}", file=sys.stderr)
                    row.update({"official_provider": source[0], "official_url": source[1], "official_status": "error", "official_error": str(exc)})
            if openalex_ok or official_ok:
                if openalex_ok:
                    base = openalex_papers
                    if not official_ok:
                        base = merge_official(base, [p for p in prior if p.get("source") != "OpenAlex" or p.get("proceedings_url")])
                else:
                    base = [p for p in prior if p.get("source") == "OpenAlex"]
                combined = merge_official(base, official_papers) if official_ok else base
                for paper in prior:
                    papers.pop(paper["id"], None)
                for paper in combined:
                    papers[paper["id"]] = paper
            coverage[(venue["id"], year)] = row
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
            if (work.get("id") != item["id"] or work.get("publication_year") != item["year"]
                    or work.get("type") not in ("conference-paper", "article") or source != venue["source_id"]):
                raise ValueError("Manual work does not match its verified venue, year, and source")
            paper = normalize_work(work, venue)
            if not paper:
                raise ValueError("Manual work fails the conference-source work and topic filters")
            paper["manual_evidence_url"] = item["evidence_url"]
            papers[paper["id"]] = paper
        except Exception as exc:
            print(f"WARNING: manual work {item.get('id')}: {exc}", file=sys.stderr)
            if item.get("id") not in papers:
                raise RuntimeError(f"Cannot add unverified manual work {item.get('id')}") from exc
    result = []
    for paper in deduplicate(papers.values()):
        previous_paper = previous_by_title.get(title_key(paper))
        review = (reviews.get(paper["id"]) or reviews.get(paper.get("proceedings_url"))
                  or reviews.get((paper.get("doi") or "").lower()))
        if review:
            validate_review(review)
            if review.get("exclude"):
                continue
            for field in REVIEW_FIELDS:
                if field in review:
                    paper[field] = review[field]
            if review.get("repository_url"):
                paper["code_available"] = True
                paper["code_url"] = review["repository_url"]
                paper["code_evidence_url"] = review["repository_evidence_url"]
                paper["repository_association_status"] = "reviewed"
            paper["review"] = {"evidence_url": review["evidence_url"], "reviewer": review.get("reviewer"), "date": review.get("date"), "note": review.get("review_note")}
        if previous_paper and paper.get("repository_url") == previous_paper.get("repository_url") and not paper.get("github"):
            paper["github"] = previous_paper.get("github")
        result.append(paper)
    token = os.getenv("GITHUB_TOKEN", "").strip()
    checked = {}
    failed_slugs = set()
    verified_slugs = set()
    fetched = 0
    for paper in sorted(result, key=lambda p: (not bool(p.get("review") and p.get("repository_url")), p.get("github") is not None, -(p.get("year") or 0))):
        paper["repository_access_status"] = "unknown"
        slug = repo_slug(paper.get("repository_url"))
        if not slug:
            continue
        if slug in failed_slugs:
            paper["github"] = None
            continue
        if slug in checked:
            paper["github"] = checked[slug]
            if slug in verified_slugs:
                paper["repository_access_status"] = "accessible"
            continue
        prior_info = paper.get("github")
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(prior_info["checked_at"])).days if prior_info else 9999
        except (KeyError, ValueError, TypeError):
            age = 9999
        if age >= 14 and fetched < github_cap:
            try:
                paper["github"] = fetch_github_metadata(paper["repository_url"], token)
                paper["repository_access_status"] = "accessible"
                verified_slugs.add(slug)
                fetched += 1
            except Exception as exc:
                print(f"WARNING: GitHub {slug}: {exc}", file=sys.stderr)
                paper["github"] = None
                failed_slugs.add(slug)
                fetched += 1
        if paper.get("github"):
            checked[slug] = paper["github"]
    result.sort(key=lambda p: (p.get("year") or 0, p.get("citations") or 0), reverse=True)
    snapshot = {"generated_at": datetime.now(timezone.utc).isoformat(), "source": "OpenAlex and official proceedings", "scope": "Capped, merged venue-year sample; not complete conference output", "cap_per_venue_year": cap, "official_cap_per_venue_year": official_cap,
                "venues": venues, "coverage": sorted(coverage.values(), key=lambda c: (c["year"], c["venue_id"])), "papers": result}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"Wrote {len(result)} real records to {OUTPUT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-year", type=int, default=max(2020, datetime.now().year - 1))
    parser.add_argument("--to-year", type=int, default=datetime.now().year)
    parser.add_argument("--cap", type=int, default=25)
    parser.add_argument("--official-cap", type=int, default=250)
    parser.add_argument("--github-cap", type=int, default=30)
    parser.add_argument("--skip-openalex", action="store_true", help="Backfill official proceedings while retaining earlier OpenAlex records")
    parser.add_argument("--cached-only", action="store_true", help="Use cached OpenAlex responses, make no OpenAlex network requests")
    parser.add_argument("--venues", nargs="*", help="Optional venue IDs")
    args = parser.parse_args()
    if not 2020 <= args.from_year <= args.to_year <= datetime.now().year or not 1 <= args.cap <= 100 or args.official_cap < 0 or args.github_cap < 0:
        parser.error("years must be 2020..current, OpenAlex cap 1..100, and other caps non-negative")
    refresh(args.from_year, args.to_year, args.cap, args.venues, args.official_cap, args.github_cap, args.skip_openalex, args.cached_only)
