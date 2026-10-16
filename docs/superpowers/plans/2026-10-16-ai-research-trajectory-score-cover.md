# AI Research Trajectory, Score, And Cover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Observatory's publication trajectory a clear three-measure multi-series line chart, explain every score, and publish the user's new cover image.

**Architecture:** Keep calculations in the existing pure `AIResearchCore` module and rendering in the Observatory page script. The chart uses the tracked, first-author-sector-classified AI ledger; influence remains in its separate score comparison. Preserve the existing static Hugo layout and image front matter.

**Tech Stack:** Vanilla JavaScript/SVG, Hugo 0.136.5, Node 24 in GitHub Actions, PNG asset.

**Spec:** `docs/superpowers/specs/2026-10-16-ai-research-venue-expansion-design.md`

## Global Constraints

- Measure selector has exactly Paper count, Publication share (%), and Year-over-year growth (%).
- Use three thin, unfilled lines with small circular markers for Industry, University, and Research Institute; no area fill.
- Count means tracked classified AI papers, not all conference acceptances; unknown affiliations do not enter share denominators.
- A missing/zero prior-year denominator yields a gap, not zero or infinity; negative growth is valid.
- Influence stays separate; show the existing 0-6 score formula, component contributions, coverage, and omission reasons without treating unknown as zero.
- Use the user's existing cover PNG and front-matter edit; do not commit unrelated coffee-wall files.

## Review Focus

- A first year or zero prior-year sector count must yield no growth marker: Task 1 test.
- A decline must plot below zero without clipping: Task 2 chart test.
- A selected year filter must not silently compare that year with an excluded prior-year record: Task 2 test.
- A year with unknown source coverage or only unknown affiliations must be a gap, not a 0% share: Task 1 test.
- A stale GitHub check or expired maintenance review must be omitted from the breakdown denominator and explained: Task 3 test.

---

## File Map

- `static/js/ai-research-observatory-core.js`: pure trend and score arithmetic.
- `scripts/test_ai_research_observatory_core.cjs`: unit tests for count/share/growth and score breakdown.
- `static/js/ai-research-observatory.js`: SVG lines, markers, axes, tooltips, and per-paper score display.
- `layouts/hodgepodge/ai-research-observatory.html`: measure labels, chart note, score formula and legend.
- `static/css/ai-research-observatory.css`: stable responsive chart/score styling only.
- `content/hodgepodge/ai-research-observatory.md`, `static/images/hodgepodge/AI_Research_ Academia Meets Industry.png`: user-edited cover source and asset.
- `docs/AI_RESEARCH_OBSERVATORY.md`: plain-language chart denominators and score method.

### Task 1: Pure Publication Measures

**Files:** Modify `static/js/ai-research-observatory-core.js`, `scripts/test_ai_research_observatory_core.cjs`.

**Interfaces:** `trend(papers, weights, mode, lastCoveredYear, usableYears) -> Array<{year, Industry, University, "Research Institute", count, classifiedCount}>`; each sector value is a number or `null`. `mode` is `count`, `share`, or `growth`. `usableYears` is a `Set<number>` of years supported by the currently selected venue scope's source coverage; preserve the existing call with omitted `usableYears` for test compatibility.

- [ ] **Step 1: Write failing assertions** for counts `2024: Industry=2, University=1` and `2025: Industry=3, University=0`: shares 66.7/33.3 and 100/0; growth Industry +50%, University -100%; 2024 growth null; a previous 0 or unusable year null; all-unknown-sector year share null.
- [ ] **Step 2: Run** `node scripts/test_ai_research_observatory_core.cjs`; expect failure for missing growth/null semantics. Use the workflow's Node 24 runner if local Node is unavailable.
- [ ] **Step 3: Implement** mode-specific arithmetic in `trend`. The chart caller will supply a ledger filtered by all controls except year so the preceding-year baseline remains available; a selected year is only highlighted, not used to truncate the time series.
- [ ] **Step 4: Run** the same test; expect pass.
- [ ] **Step 5: Commit** core calculations and tests.

### Task 2: Thin-Line Chart And Controls

**Files:** Modify `static/js/ai-research-observatory-core.js`, `scripts/test_ai_research_observatory_core.cjs`, `static/js/ai-research-observatory.js`, `layouts/hodgepodge/ai-research-observatory.html`, `static/css/ai-research-observatory.css`.

**Interfaces:** The three selector values are `count`, `share`, `growth`. Add pure `lineSegments(data: Array<object>, sector: string) -> Array<Array<object>>` and `trendRange(data: Array<object>, mode: string) -> [number, number]` helpers to core; rendering consumes them and `snapshot.coverage`, drawing a new polyline at each gap and small circles only for finite values.

- [ ] **Step 1: Write failing assertions** for `lineSegments` splitting at null, `trendRange` including negative growth and zero, and exactly three selector options. Record a browser check for `fill="none"`, stroke width at most 1.8, circle radius at most 2.8, raw count/denominator tooltips, and a selected year highlighting rather than erasing the prior-year baseline.
- [ ] **Step 2: Run** `node scripts/test_ai_research_observatory_core.cjs` with Node 24 (locally if available, otherwise in Actions); expect failure.
- [ ] **Step 3: Implement** thin SVG series, dynamic count/share/growth axes, source-coverage gaps, and a short on-page note that this is a tracked classified AI sample. Render trends from filters with `year: ""`, highlight the selected year, and keep controls/chart dimensions stable on mobile.
- [ ] **Step 4: Run** the JS tests and Hugo build; inspect desktop/mobile chart screenshots or browser rendering for clipped labels and nonblank series.
- [ ] **Step 5: Commit** chart/layout/style/tests.

### Task 3: Auditable Score Explanation

**Files:** Modify `static/js/ai-research-observatory-core.js`, `scripts/test_ai_research_observatory_core.cjs`, `static/js/ai-research-observatory.js`, `layouts/hodgepodge/ai-research-observatory.html`, `docs/AI_RESEARCH_OBSERVATORY.md`.

**Interfaces:** Extend `score(paper, weights, now)` with a `breakdown` array containing `{name, weight, value, contribution, included, reason}` while preserving existing `value`, `coverage`, and `components`. The displayed equation is `6 * sum(weight * available component value) / sum(available weights)`; coverage is available weight / selected weight.

- [ ] **Step 1: Write failing assertions** for a known paper's numerator, available weight, 0-6 result, missing-code omission, stale GitHub omission, expired maintenance omission, and zero selected weights. Ensure unknown is not recorded as a zero-valued component.
- [ ] **Step 2: Run** `node scripts/test_ai_research_observatory_core.cjs`; expect failure for absent breakdown.
- [ ] **Step 3: Implement** the shared breakdown in `score` and show its rows plus formula/coverage/threshold in the weight panel and per-paper dialog. Label the score an editorial proxy, not measured business adoption.
- [ ] **Step 4: Run** the JS tests, Hugo build, and inspect a paper with complete and incomplete evidence; expect arithmetic and omissions to match.
- [ ] **Step 5: Commit** score explanation, tests, and method docs.

### Task 4: Cover And End-To-End Verification

**Files:** Include the existing edits to `content/hodgepodge/ai-research-observatory.md` and `static/images/hodgepodge/AI_Research_ Academia Meets Industry.png`; modify only if URL encoding or accessible alt text requires it.

**Interfaces:** The Hodgepodge list renders the supplied PNG as the Observatory card cover; the generated image URL resolves despite spaces in the filename.

- [ ] **Step 1: Run** a Hugo build with the existing front matter and check the generated Hodgepodge card/image link; record whether it fails before changing the path.
- [ ] **Step 2: Set** a percent-encoded front-matter image URL only if the generated link fails; add `imageAlt` describing the supplied artwork if the rendered card lacks useful alternative text. Do not alter the PNG pixels.
- [ ] **Step 3: Run** `./scripts/check_posts_have_tags.sh`, `hugo --minify --cleanDestinationDir`, and `./scripts/check_internal_links.sh public`; inspect desktop/mobile cover and chart.
- [ ] **Step 4: Stage** only the Observatory front matter and PNG, inspect `git diff --cached --check`, then commit. Leave coffee files untouched.
- [ ] **Step 5: After the venue-backfill plan also passes, reconcile any remote refresh commit and push the combined work to `master`; confirm the live Hodgepodge card and Observatory page load.
