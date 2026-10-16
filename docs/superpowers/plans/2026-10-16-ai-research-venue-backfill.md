# AI Research Venue Backfill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the requested 23 cross-area venues and evidence-labelled 2020-current venue-wide and AI-related counts to both research pages.

**Architecture:** Extend the existing Python catalog and static snapshot. Venue/year source rules separate ranking evidence from bibliography acquisition; official indexes verify main-track totals, DBLP supplies a distinct fallback count, and OpenAlex enriches selected AI records. Hugo remains static.

**Tech Stack:** Python 3.11 standard library, DBLP SPARQL, OpenAlex API, Hugo 0.136.5, vanilla JavaScript, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-16-ai-research-venue-expansion-design.md`

## Global Constraints

- Include all 23 named series and audit other eligible CORE 2023 A*/A, CCF 2026 A/B, and TH-CPL AI A series; never invent rank membership.
- Keep organizer submitted/accepted, verified main-track totals, bibliography fallback counts, AI matches, and public paper samples distinct.
- Publish verified years and truthful gaps; a missing, non-meeting, source-error, or unpublished year is not zero.
- Cross-area AI classification scans all available eligible titles before any public paper cap; uncertain matches remain unresolved.
- Preserve unrelated coffee-wall edits; do not expose `OPENALEX_API_KEY` or force-push.

## Review Focus

- OOPSLA/POPL/FSE journal-issue articles must map to the event year and exclude companion material: Task 2 fixture test.
- A biennial non-meeting year must show `not-held`, not zero or a failed request: Task 1 source-rule test.
- Official/DBLP disagreement must not become a verified total: Task 2 conflict test.
- A 404 repository must leave live GitHub metrics unknown without deleting the paper: Task 4 test.
- A source 429 or timeout must retain dated previous papers/counts and mark the refresh partial: Task 4 test.

---

## File Map

- `scripts/ai_research_venues.py`, `data/ai_research_observatory/venues.json`: ranked catalog; no acquisition logic.
- `data/ai_research_observatory/cross_area_sources.json`: source and edition audit for the 23 series, one explicit status per 2020-current cell.
- `scripts/ai_research_bibliography.py`: source-rule validation, bounded DBLP/official index acquisition, track filtering, DOI/title reconciliation, coverage counts.
- `scripts/ai_research_relevance.py`: cross-area AI match/uncertain/exclude classification with reviewed overrides.
- `scripts/refresh_ai_research_observatory.py`: merges bibliography coverage and AI records into the existing public schema.
- `scripts/ai_research_sources.py`: reuse normalization and paper-source merging; change only where a specific adapter needs it.
- `static/js/ai-research-tracker.js`, `layouts/posts/ai-research-tracker.html`, `static/css/ai-research-tracker.css`: separate main-track and AI-matched venue history; organizer chart stays separate.
- `.github/workflows/refresh-ai-research-observatory.yml`, `docs/AI_RESEARCH_OBSERVATORY.md`: refresh controls and method.
- `scripts/test_ai_research_venues.py`, `scripts/test_ai_research_bibliography.py`, `scripts/test_ai_research_relevance.py`, `scripts/test_ai_research_observatory.py`, `scripts/test_ai_research_tracker.cjs`: focused regression tests and fixtures.

### Task 1: Ranked Inventory And Source Manifest

**Files:** Modify `scripts/ai_research_venues.py`; create `data/ai_research_observatory/cross_area_sources.json`, `scripts/test_ai_research_venues.py`; regenerate `data/ai_research_observatory/venues.json`.

**Interfaces:** `build_catalog() -> list[dict]` remains public. `cross_area_sources.json` maps venue ID to DBLP stream, source family, per-year `official_url`, `track_scope`, `status`, and provenance URLs; the status is explicit for each 2020-current year.

- [ ] **Step 1: Write failing tests.** Assert all 23 IDs occur exactly once, each has `ai_native: false` and rank evidence or explicit unranked status, and the manifest covers every year; test SOSP's non-meeting year as `not-held` only after primary schedule verification.
- [ ] **Step 2: Run** `python3 -m unittest scripts.test_ai_research_venues -v`; expect failure for missing entries/manifest.
- [ ] **Step 3: Implement** the catalog and manifest, checking actual ranking and track URLs against CORE/CCF/TH-CPL and organizer sources. Record additional eligible ranked venues and excluded candidates in the method doc; never assign unsupported rank values.
- [ ] **Step 4: Run** the same test and `python3 scripts/ai_research_venues.py`; expect pass and a deterministic JSON catalog.
- [ ] **Step 5: Commit** only catalog, manifest, test, and generated catalog.

### Task 2: Full-Year Bibliography And Track Boundaries

**Files:** Create `scripts/ai_research_bibliography.py`, `scripts/test_ai_research_bibliography.py`; modify the manifest when an edition needs a special source rule.

**Interfaces:** `collect_venue_year(venue: dict, year: int, rule: dict, cache_dir: Path) -> tuple[list[dict], dict]` returns de-duplicated eligible bibliography rows and coverage containing `main_track_total`, `bibliography_total`, source URLs, scanned count, and status. Each row carries title, DOI if available, URL, venue ID, event year, and track evidence. No OpenAlex dependency here.

- [ ] **Step 1: Write failing fixture tests** for a DBLP SPARQL result; a PACMPL/PACMSE main issue with companion/article exclusions; DOI-before-title deduplication; not-held year; and conflicting official/DBLP totals. Assert `main_track_total is None` for an unverified or conflicting index and no workshop rows survive.
- [ ] **Step 2: Run** `python3 -m unittest scripts.test_ai_research_bibliography -v`; expect failure for the missing module.
- [ ] **Step 3: Implement** bounded/cached SPARQL requests and the source-family adapters needed by verified editions. Request only configured streams/issues, honor DBLP rate limits, use event-year mapping, and treat a publisher/page format change as an error rather than a zero.
- [ ] **Step 4: Run** the test; expect pass. Probe one verified edition per source family against live primary indexes without freezing mutable live counts into unit tests.
- [ ] **Step 5: Commit** adapter, fixtures/tests, and audited source-rule corrections.

### Task 3: AI Subset And Repository Evidence

**Files:** Create `scripts/ai_research_relevance.py`, `scripts/test_ai_research_relevance.py`; modify `scripts/ai_research_sources.py` and `scripts/refresh_ai_research_observatory.py` only for normalized evidence fields.

**Interfaces:** `classify_ai_work(row: dict, metadata: dict | None, review: dict | None) -> tuple[str, str]` returns `matched`, `unresolved`, or `not-ai` plus a versioned rule/evidence label. `summarize_ai_scan(rows, classifications) -> dict` returns matched/reviewed/unresolved/scanned counts. Existing `reviews.json` HTTPS-evidence overrides survive refreshes.

- [ ] **Step 1: Write failing tests** for explicit LLM inference and ML compiler matches, generic GPU/compiler titles remaining unresolved or non-AI, reviewed include/exclude precedence, and incomplete scan status.
- [ ] **Step 2: Run** `python3 -m unittest scripts.test_ai_research_relevance -v`; expect failure.
- [ ] **Step 3: Implement** high-precision classification and the scan summary; link bibliography rows to OpenAlex by DOI/title for metadata enrichment without making OpenAlex the bibliography denominator. Preserve paper-to-code evidence and distinguish repository association from current accessibility.
- [ ] **Step 4: Run** relevance and existing source/collector tests; expect pass.
- [ ] **Step 5: Commit** classifier and evidence tests/code.

### Task 4: Snapshot Integration And Refresh Safety

**Files:** Modify `scripts/refresh_ai_research_observatory.py`, `.github/workflows/refresh-ai-research-observatory.yml`, `scripts/test_ai_research_observatory.py`.

**Interfaces:** Each `snapshot.coverage` row adds the Task 2 and Task 3 fields without changing `source_total`/`official_total` meanings. Existing paper consumers still read `snapshot.papers`; new cross-area papers are only matched AI records.

- [ ] **Step 1: Write failing tests** for one verified and one unresolved venue-year, complete-title scan before public sampling, old-paper retention on 429/timeout, GitHub 404 leaving stars/activity unknown without dropping the paper, and repeated refresh idempotence.
- [ ] **Step 2: Run** `python3 -m unittest scripts.test_ai_research_observatory -v`; expect failure.
- [ ] **Step 3: Integrate** the new adapters with the current refresh loop, preserving previous records on source failure and marking stale status/timestamps. Add workflow concurrency so simultaneous scheduled/manual refreshes cannot race over the snapshot; keep the secret out of logs.
- [ ] **Step 4: Run** all `test_ai_research*.py` tests and a `--venues` scoped cached/backfill run; expect valid JSON and truthful coverage statuses.
- [ ] **Step 5: Commit** collector, workflow, and tests.

### Task 5: Tracker Presentation And Reproducibility

**Files:** Modify `static/js/ai-research-tracker.js`, `layouts/posts/ai-research-tracker.html`, `static/css/ai-research-tracker.css`, `content/posts/ai-research-tracker.md`, the coverage/inventory region of `layouts/hodgepodge/ai-research-observatory.html` and `static/js/ai-research-observatory.js`, `docs/AI_RESEARCH_OBSERVATORY.md`; create `scripts/test_ai_research_tracker.cjs`.

**Interfaces:** A venue-year chart point is `{year, main_track_total, bibliography_total, ai_matched_count, status, source_url, track_scope}`. The main-track line reads only verified totals, the AI line is explicitly labelled an observed match count, and organizer submissions/acceptances remain unchanged.

- [ ] **Step 1: Write failing JS/HTML assertions** that an unresolved year creates a line gap, a DBLP fallback is labelled bibliography rather than main-track, both pages show the 23 venues and count provenance, and organizer counts are not replaced.
- [ ] **Step 2: Run** `node scripts/test_ai_research_tracker.cjs` under local Node or the Actions Node 24 runner; expect failure.
- [ ] **Step 3: Implement** filters and accessible tooltips/coverage copy on both pages. Keep all AI-only charts filtered to matched papers and the arXiv section outside conference totals.
- [ ] **Step 4: Run** `node scripts/test_ai_research_tracker.cjs`, Hugo build, tag and internal-link checks; expect pass.
- [ ] **Step 5: Commit** page, documentation, and test changes.

### Task 6: Historical Backfill And Release Audit

**Files:** Update `static/data/ai-research-observatory.json`, the source manifest, and `docs/AI_RESEARCH_OBSERVATORY.md` only when evidence changes them.

**Interfaces:** `backfill-2020` processes every catalog venue-year; 23 required series have seven explicit 2020-2026 status cells, including justified gaps.

- [ ] **Step 1: Run** a scoped backfill for representative systems, architecture, compiler, and software-engineering venues; inspect the 2020-2026 status/scan totals and correct source rules with evidence.
- [ ] **Step 2: Run** `python3 -m unittest discover -s scripts -p 'test_ai_research*.py'`, the JS checks, tag check, `hugo --minify --cleanDestinationDir`, and `./scripts/check_internal_links.sh public`; inspect desktop/mobile pages. Once this and the companion UI plan pass, reconcile remote commits and push code/cover to `master` so Actions uses the new collector.
- [ ] **Step 3: Run** the full `backfill-2020` workflow with the existing Actions secret; fetch its snapshot commit and audit every required venue-year, AI scan denominator, and source URL. Do not mark a partial scan verified.
- [ ] **Step 4: Commit** evidence-backed data/docs corrections, rerun tests/build, and push without force. Confirm the live tracker/Observatory and workflow result before calling the release complete.
