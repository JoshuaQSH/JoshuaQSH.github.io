"""Official proceedings indexes and cautious paper/repository normalization."""
from __future__ import annotations

import html
import re
import unicodedata
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

PMLR_VOLUMES = {2020: 119, 2021: 139, 2022: 162, 2023: 202, 2024: 235, 2025: 267, 2026: 306}
PMLR_OTHER = {
    "aistats": {2020: 108, 2021: 130, 2022: 151, 2023: 206, 2024: 238, 2025: 258, 2026: 300},
    "colt": {2020: 125, 2021: 134, 2022: 178, 2023: 195, 2024: 247, 2025: 291, 2026: 336},
    "uai": {2020: 124, 2021: 161, 2022: 180, 2023: 216, 2024: 244, 2025: 286, 2026: 337},
}
ANTHOLOGY_VOLUMES = {
    "acl": {2020: ("main",), **{year: ("long", "short") for year in range(2021, 2027)}},
    "emnlp": {year: ("main",) for year in range(2020, 2026)},
    "naacl": {2021: ("main",), 2022: ("main",), 2024: ("long", "short"), 2025: ("long", "short")},
    "eacl": {2021: ("main",), 2023: ("main",), 2024: ("long", "short"), 2026: ("long", "short")},
    "coling": {2020: ("main",), 2025: ("main",)},
}


def official_source(venue_id, year):
    if venue_id == "neurips" and 2020 <= year <= 2025:
        if year <= 2021:
            return "NeurIPS Proceedings", f"https://proceedings.neurips.cc/paper/{year}"
        if year == 2025:
            return "NeurIPS Proceedings", "https://proceedings.neurips.cc/paper_files/paper/2025/vol38-main-conference"
        return "NeurIPS Proceedings", f"https://proceedings.neurips.cc/paper_files/paper/{year}"
    if venue_id == "icml" and year in PMLR_VOLUMES:
        return "PMLR", f"https://proceedings.mlr.press/v{PMLR_VOLUMES[year]}/"
    if year in PMLR_OTHER.get(venue_id, {}):
        return "PMLR", f"https://proceedings.mlr.press/v{PMLR_OTHER[venue_id][year]}/"
    if year in ANTHOLOGY_VOLUMES.get(venue_id, {}):
        return "ACL Anthology", f"https://aclanthology.org/events/{venue_id}-{year}/"
    if venue_id in {"cvpr", "iccv", "wacv"} and 2020 <= year <= 2026:
        if venue_id == "iccv" and year % 2 == 0:
            return None
        if venue_id in {"cvpr", "wacv"} and year == 2020:
            return "CVF Open Access", f"https://openaccess.thecvf.com/{venue_id.upper()}{year}"
        return "CVF Open Access", f"https://openaccess.thecvf.com/{venue_id.upper()}{year}?day=all"
    return None


class ACLParser(HTMLParser):
    def __init__(self, year, venue_id="acl"):
        super().__init__(convert_charrefs=True)
        self.year = year
        self.venue_id = venue_id
        self.rows = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        if re.fullmatch(rf"/?{self.year}\.{re.escape(self.venue_id)}-(?:main|long|short)\.[1-9]\d*/?", href):
            self.current = {"url": urljoin("https://aclanthology.org", href), "title": ""}

    def handle_data(self, data):
        if self.current is not None:
            self.current["title"] += data

    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            self.current["title"] = html.unescape(self.current["title"]).strip()
            if self.current["title"]:
                self.rows.append({**self.current, "first_author": "Unknown", "code_url": None})
            self.current = None


def parse_acl(content, year, venue_id="acl"):
    parser = ACLParser(year, venue_id)
    parser.feed(content)
    return list({row["url"]: row for row in parser.rows}.values())


class CVFParser(HTMLParser):
    def __init__(self, venue_id, year):
        super().__init__(convert_charrefs=True)
        self.prefixes = (f"/content/{venue_id.upper()}{year}/html/", f"content_{venue_id.upper()}_{year}/html/")
        self.rows = []
        self.in_title = False
        self.current = None
        self.capture = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "dt" and "ptitle" in attrs.get("class", "").split():
            if self.current and self.current.get("title"):
                self.rows.append(self.current)
            self.current = None
            self.in_title = True
        elif self.in_title and tag == "a" and attrs.get("href", "").startswith(self.prefixes) and attrs.get("href", "").endswith(".html"):
            self.current = {"url": urljoin("https://openaccess.thecvf.com", attrs["href"]), "title": "", "first_author": "Unknown", "code_url": None}
            self.capture = True
        elif tag == "input" and self.current is not None and attrs.get("name") == "query_author":
            self.current["first_author"] = attrs.get("value") or "Unknown"

    def handle_data(self, data):
        if self.capture and self.current is not None:
            self.current["title"] += data

    def handle_endtag(self, tag):
        if tag == "a":
            self.capture = False
        elif tag == "dt":
            self.in_title = False


def parse_cvf(content, venue_id, year):
    parser = CVFParser(venue_id, year)
    parser.feed(content)
    if parser.current and parser.current.get("title"):
        parser.rows.append(parser.current)
    return [{**row, "title": html.unescape(row["title"]).strip()} for row in parser.rows if row.get("title")]


class NeurIPSParser(HTMLParser):
    def __init__(self, year):
        super().__init__(convert_charrefs=True)
        self.year = year
        self.rows = []
        self.current = None
        self.capture = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "li":
            track = attrs.get("data-track")
            self.current = {} if track == ("none" if self.year <= 2021 else "conference") else None
        if self.current is None:
            return
        if tag == "a" and attrs.get("title") == "paper title":
            url = attrs.get("href", "")
            if url.startswith(f"/paper_files/paper/{self.year}/hash/") and "-Abstract" in url:
                self.current["url"] = urljoin("https://proceedings.neurips.cc", url)
                self.capture = "title"
        elif tag == "span" and "paper-authors" in attrs.get("class", "").split():
            self.capture = "authors"

    def handle_data(self, data):
        if self.current is not None and self.capture:
            self.current[self.capture] = self.current.get(self.capture, "") + data

    def handle_endtag(self, tag):
        if tag in ("a", "span"):
            self.capture = None
        if tag == "li" and self.current is not None:
            if self.current.get("title") and self.current.get("url"):
                authors = html.unescape(self.current.get("authors", "")).strip()
                self.rows.append({"title": html.unescape(self.current["title"]).strip(), "url": self.current["url"],
                                  "first_author": authors.split(",", 1)[0].strip() or "Unknown", "code_url": None})
            self.current = None


def parse_neurips(content, year):
    parser = NeurIPSParser(year)
    parser.feed(content)
    return parser.rows


class PMLRParser(HTMLParser):
    def __init__(self, year, volume):
        super().__init__(convert_charrefs=True)
        self.year, self.volume = year, volume
        self.rows = []
        self.current = None
        self.depth = 0
        self.capture = None
        self.link = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div":
            if self.current is None and "paper" in attrs.get("class", "").split():
                self.current, self.depth = {}, 1
            elif self.current is not None:
                self.depth += 1
        if self.current is None:
            return
        if tag == "p" and "title" in attrs.get("class", "").split():
            self.capture = "title"
        elif tag == "span" and "authors" in attrs.get("class", "").split():
            self.capture = "authors"
        elif tag == "a":
            self.link = {"href": attrs.get("href", ""), "label": ""}

    def handle_data(self, data):
        if self.current is None:
            return
        if self.capture:
            self.current[self.capture] = self.current.get(self.capture, "") + data
        if self.link is not None:
            self.link["label"] += data

    def handle_endtag(self, tag):
        if self.current is None:
            return
        if tag == "a" and self.link is not None:
            label, href = self.link["label"].strip().lower(), self.link["href"]
            if label == "abs" and href.startswith(f"https://proceedings.mlr.press/v{self.volume}/"):
                self.current["url"] = href
            elif label == "software" and href.startswith("https://"):
                self.current["code_url"] = href
            self.link = None
        elif tag == "span" and self.capture == "authors":
            self.capture = None
        elif tag == "p" and self.capture == "title":
            self.capture = None
        elif tag == "div":
            self.depth -= 1
            if self.depth == 0:
                if self.current.get("title") and self.current.get("url"):
                    authors = html.unescape(self.current.get("authors", "")).strip()
                    self.rows.append({"title": html.unescape(self.current["title"]).strip(), "url": self.current["url"],
                                      "first_author": authors.split(",", 1)[0].strip() or "Unknown",
                                      "code_url": self.current.get("code_url")})
                self.current = None


def parse_pmlr(content, year, volume):
    parser = PMLRParser(year, volume)
    parser.feed(content)
    return parser.rows


def select_records(rows, cap, forced_urls=()):
    if cap <= 0:
        return []
    if len(rows) <= cap:
        return rows
    forced = set(forced_urls)
    chosen = [row for row in rows if row["url"] in forced]
    if len(chosen) > cap:
        raise ValueError("Curated proceedings records exceed the official cap")
    slots = cap - len(chosen)
    if slots:
        candidates = [row for row in rows if row["url"] not in forced]
        if slots == 1:
            chosen.append(candidates[len(candidates) // 2])
        else:
            chosen.extend(candidates[round(i * (len(candidates) - 1) / (slots - 1))] for i in range(slots))
    return chosen


def repo_slug(url):
    try:
        parsed = urlparse(url)
        parts = parsed.path.strip("/").split("/")
        if parsed.scheme != "https" or parsed.hostname != "github.com" or len(parts) < 2:
            return None
        owner, repo = parts[:2]
        repo = repo.removesuffix(".git")
        if not all(re.fullmatch(r"[A-Za-z0-9_.-]+", x) for x in (owner, repo)):
            return None
        return f"{owner}/{repo}"
    except (TypeError, ValueError, AttributeError):
        return None


def normalize_official(raw, venue, year, provider):
    now = datetime.now(timezone.utc).isoformat()
    prestige = 1 if venue["rank"] in ("A*", "A") else .75 if venue["rank"] == "B" else None
    repo = repo_slug(raw.get("code_url"))
    return {"id": raw["url"], "doi": None, "url": raw["url"], "proceedings_url": raw["url"],
            "title": raw["title"], "abstract": None, "year": year, "date": None,
            "venue": venue["name"], "venue_id": venue["id"], "area": venue["area"], "topic_rule": "official-main-proceedings",
            "first_author": raw.get("first_author") or "Unknown", "first_author_id": None,
            "first_author_sector": "Unknown", "first_author_affiliations": [], "countries": [],
            "all_institutions": [], "team_sector": "Unknown", "corresponding_authors": [],
            "senior_author": None, "senior_author_affiliations": [], "leadership": "Unknown",
            "award": None, "code_available": True if raw.get("code_url") else None,
            "code_url": raw.get("code_url"), "code_evidence_url": raw["url"] if raw.get("code_url") else None,
            "repository_url": f"https://github.com/{repo}" if repo else None,
            "repository_evidence_url": raw["url"] if repo else None, "github": None,
            "adoption_status": "Unknown", "adoption_evidence_url": None,
            "maintenance_status": "Unknown", "maintenance_evidence_url": None,
            "resources": None, "funding": None, "compute": {"gpu_type": None, "gpu_count": None,
              "gpu_hours": None, "accelerator_type": None, "training_flops": None,
              "model_parameters": None, "training_cost": None}, "compute_evidence": None,
            "citations": None, "citation_percentile": None, "fwci": None, "prestige": prestige,
            "ranking": {k: venue[k] for k in ("ranking_scheme", "edition", "rank", "rank_url")},
            "source": provider, "sources": [{"provider": provider, "url": raw["url"]}],
            "source_id": raw["url"], "checked_at": now}


def title_key(paper):
    normalized = unicodedata.normalize("NFKC", paper.get("title") or "").casefold()
    return paper.get("venue_id"), paper.get("year"), re.sub(r"[^\w]+", "", normalized)


def merge_official(papers, official):
    by_key = {title_key(paper): index for index, paper in enumerate(papers)}
    result = list(papers)
    for paper in official:
        key = title_key(paper)
        if key not in by_key:
            by_key[key] = len(result)
            result.append(paper)
            continue
        index = by_key[key]
        existing = dict(result[index])
        existing["proceedings_url"] = paper.get("proceedings_url") or paper["url"]
        existing["sources"] = list({entry["url"]: entry for entry in
            existing.get("sources", [{"provider": existing["source"], "url": existing["id"]}]) + paper["sources"]}.values())
        if paper.get("code_url"):
            existing.update({key: paper[key] for key in ("code_available", "code_url", "code_evidence_url", "repository_url", "repository_evidence_url")})
        result[index] = existing
    return result
