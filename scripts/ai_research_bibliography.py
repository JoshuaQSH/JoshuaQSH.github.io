"""Bounded venue-year bibliography collection with explicit track evidence."""
from __future__ import annotations

import hashlib
import html
import json
import re
import tempfile
import time
import unicodedata
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


SPARQL_URL = "https://sparql.dblp.org/sparql"
MAX_ROWS = 1000
DBLP_INTERVAL_SECONDS = 1.0
CACHE_TTL_SECONDS = 24 * 3600
_last_dblp_request = 0.0
_EXCLUDED_CONTAINER = re.compile(
    r"\b(?:workshops?|companion|posters?|demonstrations?|artifacts?|short papers?|"
    r"industry track|operational systems|doctoral symposium|student research|keynote)\b", re.I)
_WORKSHOP_TOC = re.compile(r"/(?:[^/]*20\d{2}[wc]|[^/]*workshop[^/]*|[^/]*companion[^/]*)(?:\.html)?$", re.I)
_EXCLUDED_TITLE = re.compile(
    r"^(?:editorial|preface|front matter|table of contents|organization|message from the|"
    r"proceedings of the|workshop report)\b", re.I)


class SourceFormatError(ValueError):
    """A source changed shape or omitted required publication evidence."""


def _binding(row: dict, key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    if not isinstance(value, dict) or not isinstance(value.get("value"), str):
        raise SourceFormatError(f"Invalid DBLP {key} binding")
    return value["value"]


def _doi(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value.strip(), flags=re.I).lower() or None


def _title_key(title: str) -> str:
    return re.sub(r"[^\w]+", "", unicodedata.normalize("NFKC", title).casefold())


def _excluded_material(rule: dict, edition: dict) -> tuple[str, ...]:
    terms = []
    for configured in (rule.get("excluded_material", []), edition.get("excluded_material", [])):
        if not isinstance(configured, list) or any(
                not isinstance(term, str) or not term.strip() for term in configured):
            raise ValueError("Excluded material must be a list of nonempty labels")
        terms.extend(configured)
    return tuple(dict.fromkeys(terms))


def _container_excluded(book: str | None, toc: str | None, terms: tuple[str, ...]) -> bool:
    container = " ".join((book or "", toc or ""))
    if _EXCLUDED_CONTAINER.search(container) or (toc and _WORKSHOP_TOC.search(toc)):
        return True
    normalized = f" {re.sub(r'[^a-z0-9]+', ' ', container.casefold()).strip()} "
    for term in terms:
        label = re.sub(r"[^a-z0-9]+", " ", term.casefold()).strip()
        if f" {label} " in normalized:
            return True
        if label == "industrial track proceedings":
            # DBLP labels Middleware's industrial volume "Industry" and its TOC with an i suffix.
            if re.search(r"\bindustri(?:al|y)(?:[- ]track)?\b", book or "", re.I) or (
                    toc and re.search(r"/[^/]*20\d{2}i(?:\.html)?$", toc, re.I)):
                return True
        elif label == "short demo" and re.search(r"\b(?:short|demos?|demonstrations?)\b", book or "", re.I):
            return True
    return False


def _edition(rule: dict, year: int) -> dict:
    try:
        edition = rule["years"][str(year)]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Missing source rule for {year}") from exc
    if edition.get("status") not in {"unresolved", "partial", "verified", "source-error",
                                      "not-yet-published", "not-held"}:
        raise ValueError(f"Unsupported edition status for {year}")
    return edition


def _stream_and_issues(rule: dict, edition: dict) -> tuple[str, tuple[str, ...], bool]:
    stream = edition.get("dblp_stream", rule.get("dblp_stream"))
    family = edition.get("source_family", rule.get("source_family"))
    if not isinstance(stream, str) or not re.fullmatch(r"https://dblp\.org/streams/(?:conf|journals)/[A-Za-z0-9_-]+", stream):
        raise ValueError("A bounded DBLP stream is required")
    journal = family == "acm-journal-issue"
    issues = edition.get("dblp_issues")
    if journal:
        if edition.get("dblp_issue_field") != "publishedInJournalVolumeIssue":
            raise ValueError("Journal years require an issue selector")
        if not isinstance(issues, list) or not issues or any(
                not isinstance(issue, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", issue) for issue in issues):
            raise ValueError("Journal issue selectors must be explicit")
    elif issues:
        raise ValueError("Unexpected journal issue selector on proceedings stream")
    return stream, tuple(issues or ()), journal


def _sparql_query(stream: str, issues: tuple[str, ...], year: int) -> str:
    issue_clause = ("VALUES ?issue { " + " ".join(json.dumps(issue) for issue in issues) + " }\n"
                    "  ?pub dblp:publishedInJournalVolumeIssue ?issue .") if issues else (
                        "OPTIONAL { ?pub dblp:publishedInJournalVolumeIssue ?issue }")
    return f"""PREFIX dblp: <https://dblp.org/rdf/schema#>
SELECT ?pub ?title ?doi ?eventYear ?publicationYear ?issue ?book ?toc ?type WHERE {{
  ?pub dblp:publishedInStream <{stream}> ; dblp:title ?title ;
       dblp:yearOfPublication ?publicationYear ; dblp:bibtexType ?type .
  {issue_clause}
  OPTIONAL {{ ?pub dblp:yearOfEvent ?eventYear }}
  OPTIONAL {{ ?pub dblp:doi ?doi }}
  OPTIONAL {{ ?pub dblp:publishedInBook ?book }}
  OPTIONAL {{ ?pub dblp:listedOnTocPage ?toc }}
  FILTER((BOUND(?eventYear) && STR(?eventYear) = "{year}") ||
         (!BOUND(?eventYear) && STR(?publicationYear) = "{year}"))
}} ORDER BY ?pub LIMIT {MAX_ROWS + 1}"""


def _fetch(url: str, cache_dir: Path, *, query: str | None = None) -> bytes:
    global _last_dblp_request
    payload = query.encode() if query is not None else None
    key = hashlib.sha256(url.encode() + b"\n" + (payload or b"")).hexdigest()
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"bibliography-{key}.cache"
    if path.exists() and time.time() - path.stat().st_mtime < CACHE_TTL_SECONDS:
        return path.read_bytes()
    if query is not None:
        elapsed = time.monotonic() - _last_dblp_request
        if elapsed < DBLP_INTERVAL_SECONDS:
            time.sleep(DBLP_INTERVAL_SECONDS - elapsed)
    request = Request(url, data=payload, headers={
        "User-Agent": "AI-Research-Observatory/1.0 (bibliography research)",
        "Accept": "application/sparql-results+json" if query is not None else "text/html",
        **({"Content-Type": "application/sparql-query"} if query is not None else {})})
    try:
        with urlopen(request, timeout=30) as response:
            content = response.read()
    finally:
        if query is not None:
            _last_dblp_request = time.monotonic()
    if not content:
        raise SourceFormatError(f"Empty source response: {url}")
    with tempfile.NamedTemporaryFile(dir=cache_dir, prefix="bibliography-", delete=False) as temp:
        temp.write(content)
        temp_path = Path(temp.name)
    temp_path.replace(path)
    return content


def _dblp_rows(raw: bytes, venue_id: str, year: int, stream: str,
               issues: tuple[str, ...], journal: bool,
               excluded_material: tuple[str, ...], book_labels: tuple[str, ...],
               record_prefix: str | None) -> tuple[list[dict], bool]:
    try:
        payload = json.loads(raw)
        bindings = payload["results"]["bindings"]
    except (ValueError, KeyError, TypeError) as exc:
        raise SourceFormatError("DBLP SPARQL response format changed") from exc
    if not isinstance(bindings, list):
        raise SourceFormatError("DBLP SPARQL bindings are not a list")
    truncated = len(bindings) > MAX_ROWS
    rows = []
    for binding in bindings[:MAX_ROWS]:
        if not isinstance(binding, dict):
            raise SourceFormatError("Invalid DBLP row")
        pub, title = _binding(binding, "pub"), _binding(binding, "title")
        publication_year = _binding(binding, "publicationYear")
        event_year = _binding(binding, "eventYear")
        kind = (_binding(binding, "type") or "").rsplit("#", 1)[-1]
        issue, book, toc = (_binding(binding, key) for key in ("issue", "book", "toc"))
        if not pub or not pub.startswith("https://dblp.org/rec/") or not title or not publication_year:
            raise SourceFormatError("DBLP row lacks publication identity")
        if not re.fullmatch(r"\d{4}", publication_year) or (
                event_year and not re.fullmatch(r"\d{4}", event_year)) or not kind:
            raise SourceFormatError("DBLP row has malformed year or publication type")
        if journal and not issue:
            raise SourceFormatError("DBLP journal row lacks issue binding")
        if (event_year or publication_year) != str(year):
            continue
        if journal:
            if issue not in issues or kind != "Article":
                continue
        elif kind != "Inproceedings":
            continue
        if record_prefix and not pub.startswith(record_prefix):
            continue
        if not journal and book_labels and book not in book_labels:
            continue
        if _EXCLUDED_TITLE.search(title.strip()):
            continue
        if not journal:
            if not book and not toc:
                raise SourceFormatError("Proceedings row lacks a track container")
            if _container_excluded(book, toc, excluded_material):
                continue
        evidence = {"source": "DBLP", "stream": stream, "issue": issue if journal else None,
                    "book": book if not journal else None, "toc": toc, "event_year_basis":
                    "yearOfEvent" if event_year else "yearOfPublication"}
        rows.append({"title": html.unescape(title).strip(), "doi": _doi(_binding(binding, "doi")),
                     "url": pub, "venue_id": venue_id, "event_year": year,
                     "track_evidence": evidence, "source_urls": [pub], "source_evidence": [evidence]})
    return _deduplicate(rows), truncated


class _UsenixParser(HTMLParser):
    def __init__(self, prefix: str):
        super().__init__(convert_charrefs=True)
        self.prefix = prefix
        self.rows = []
        self.depth = 0
        self.in_heading = False
        self.href = None
        self.title = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article":
            if self.depth:
                self.depth += 1
            elif "node-paper" in attrs.get("class", "").split():
                self.depth = 1
        elif self.depth and tag == "h2":
            self.in_heading = True
        elif self.depth and self.in_heading and tag == "a":
            href = attrs.get("href", "")
            if href.startswith(self.prefix):
                self.href = href
                self.title = ""

    def handle_data(self, data):
        if self.href is not None:
            self.title += data

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            title = html.unescape(self.title).strip()
            if not title:
                raise SourceFormatError("USENIX paper title is empty")
            self.rows.append((title, urljoin("https://www.usenix.org", self.href)))
            self.href = None
        elif tag == "h2":
            self.in_heading = False
        elif tag == "article" and self.depth:
            self.depth -= 1
            if not self.depth:
                self.in_heading = False


def _official_rows(raw: bytes, venue_id: str, year: int, edition: dict) -> list[dict]:
    if edition.get("official_index_type") != "usenix-technical-sessions":
        raise ValueError("Unsupported official index adapter")
    url = edition["official_url"]
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "www.usenix.org" or not re.fullmatch(
            r"/conference/[a-z]+\d{2}/technical-sessions", parsed.path):
        raise ValueError("USENIX index URL must name a technical-sessions page")
    slug = parsed.path.split("/")[2]
    parser = _UsenixParser(f"/conference/{slug}/presentation/")
    try:
        parser.feed(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise SourceFormatError("USENIX index encoding changed") from exc
    if not parser.rows:
        raise SourceFormatError("USENIX technical sessions contain no recognizable paper links")
    return _deduplicate([{"title": title, "doi": None, "url": paper_url, "venue_id": venue_id,
                          "event_year": year, "track_evidence": {"source": "official", "index_url": url,
                          "track_scope": edition["track_scope"]}, "source_urls": [paper_url],
                          "source_evidence": [{"source": "official", "index_url": url}]}
                         for title, paper_url in parser.rows])


def _merge(left: dict, right: dict) -> dict:
    combined = dict(left)
    combined["doi"] = left["doi"] or right["doi"]
    combined["source_urls"] = list(dict.fromkeys(left["source_urls"] + right["source_urls"]))
    combined["source_evidence"] = left["source_evidence"] + right["source_evidence"]
    if right["track_evidence"]["source"] == "official":
        combined["url"] = right["url"]
        combined["track_evidence"] = right["track_evidence"]
    return combined


def _deduplicate(rows: list[dict]) -> list[dict]:
    dois_by_title: dict[str, set[str]] = {}
    for row in rows:
        if row["doi"]:
            dois_by_title.setdefault(_title_key(row["title"]), set()).add(row["doi"])
    result = []
    for row in rows:
        title = _title_key(row["title"])
        title_matches = [index for index, existing in enumerate(result)
                         if _title_key(existing["title"]) == title]
        doi_matches = [index for index, existing in enumerate(result)
                       if row["doi"] and existing["doi"] == row["doi"]]
        if len(dois_by_title.get(title, ())) > 1:
            # An unlabelled row cannot resolve two distinct DOI identities.
            if row["doi"]:
                title_matches = []
            else:
                title_matches = [index for index in title_matches if not result[index]["doi"]]
        matches = sorted(set(doi_matches + title_matches))
        if not matches:
            result.append(row)
            continue
        merged = result[matches[0]]
        for index in reversed(matches[1:]):
            merged = _merge(merged, result.pop(index))
        result[matches[0]] = _merge(merged, row)
    return result


def collect_venue_year(venue: dict, year: int, rule: dict,
                       cache_dir: Path) -> tuple[list[dict], dict]:
    """Return eligible rows and evidence-labelled venue-year coverage.

    Only an explicitly verified official index that reconciles with DBLP can
    yield a main-track total. All DBLP-only counts remain bibliography totals.
    """
    edition = _edition(rule, year)
    source_urls = list(dict.fromkeys([edition.get("dblp_stream", rule.get("dblp_stream")),
                                      edition.get("official_url"),
                                      *edition.get("provenance_urls", [])]))
    source_urls = [url for url in source_urls if url]
    coverage = {"venue_id": venue["id"], "year": year, "main_track_total": None,
                "bibliography_total": None, "scanned_count": 0, "status": edition["status"],
                "track_scope": edition.get("track_scope"), "source_urls": source_urls,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "gap_reason": edition.get("gap_reason")}
    if edition["status"] in {"not-held", "not-yet-published"}:
        return [], coverage
    if edition.get("match_rule"):
        coverage.update(status="unresolved", gap_reason=edition["match_rule"])
        return [], coverage
    stream, issues, journal = _stream_and_issues(rule, edition)
    excluded_material = _excluded_material(rule, edition)
    configured_labels = edition.get("dblp_book_labels", rule.get("dblp_book_labels", []))
    if not isinstance(configured_labels, list) or any(
            not isinstance(label, str) or not label.strip() for label in configured_labels):
        raise ValueError("DBLP book labels must be a list of nonempty strings")
    book_labels = tuple(configured_labels)
    record_prefix = edition.get("dblp_record_prefix", rule.get("dblp_record_prefix"))
    if record_prefix is not None and (not isinstance(record_prefix, str) or
            not record_prefix.startswith("https://dblp.org/rec/")):
        raise ValueError("DBLP record prefix must be a DBLP record URL prefix")
    dblp_rows, official_rows = [], []
    errors = []
    truncated = False
    try:
        dblp_rows, truncated = _dblp_rows(_fetch(SPARQL_URL, cache_dir,
                                                 query=_sparql_query(stream, issues, year)),
                                          venue["id"], year, stream, issues, journal,
                                          excluded_material, book_labels, record_prefix)
    except (HTTPError, URLError, TimeoutError, OSError, SourceFormatError) as exc:
        errors.append(f"DBLP: {exc}")
    if edition.get("official_index_verified"):
        if not edition.get("official_url") or not edition.get("official_index_type"):
            raise ValueError("Verified official index needs a URL and adapter type")
        try:
            official_rows = _official_rows(_fetch(edition["official_url"], cache_dir), venue["id"],
                                           year, edition)
        except (HTTPError, URLError, TimeoutError, OSError, SourceFormatError) as exc:
            errors.append(f"Official index: {exc}")
    rows = _deduplicate(dblp_rows + official_rows)
    coverage["scanned_count"] = len(rows)
    if dblp_rows and not truncated and not any(error.startswith("DBLP:") for error in errors):
        coverage["bibliography_total"] = len(dblp_rows)
    if errors:
        coverage.update(status="source-error", gap_reason="; ".join(errors))
    elif truncated:
        coverage.update(status="partial", gap_reason=f"DBLP query exceeded {MAX_ROWS} rows")
    elif edition.get("official_index_verified"):
        official_keys = {_title_key(row["title"]) for row in official_rows}
        dblp_keys = {_title_key(row["title"]) for row in dblp_rows}
        if len(official_rows) == len(dblp_rows) and official_keys == dblp_keys:
            coverage.update(status="verified", main_track_total=len(official_rows), gap_reason=None)
        else:
            coverage.update(status="unresolved", gap_reason="Official/DBLP index conflict: "
                            f"{len(official_rows)} official vs {len(dblp_rows)} DBLP rows")
    elif rows:
        coverage.update(status="partial", gap_reason="DBLP bibliography is not main-track verification")
    else:
        coverage.update(status="unresolved", gap_reason="No indexed bibliography rows; zero is unverified")
    return rows, coverage
