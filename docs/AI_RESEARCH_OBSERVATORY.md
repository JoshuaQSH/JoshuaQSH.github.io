# AI Research Observatory

The native Hodgepodge page is `content/hodgepodge/ai-research-observatory.md` with a Hugo layout in `layouts/hodgepodge/ai-research-observatory.html`. The browser loads `static/data/ai-research-observatory.json`; no server or public write API is needed on GitHub Pages. UI behavior is split between `static/js/ai-research-observatory-core.js` (pure calculations) and `static/js/ai-research-observatory.js` (rendering), with site-aware styling in `static/css/ai-research-observatory.css`.

The pinned companion post is `content/posts/ai-research-tracker.md`. Its conference counts and award highlights are manually curated in `static/data/ai-research-conference-history.json`; its industry/university keyword chart reads the observatory snapshot. The post does not mistake those capped sample counts for official conference totals.

## Data flow

1. Edit `data/ai_research_observatory/venues.json` to add a verified conference source. Each row needs a source ID, official CORE/CCF scheme, edition, rank, and direct ranking URL. `ai_native: false` invokes the AI-adjacent keyword filter. The initial set is NeurIPS, ICML, ACL, CVPR, OSDI, and ASPLOS.
2. Run the dependency-free Python collector, which queries OpenAlex `conference-paper` works by `publication_year` and `primary_location.source.id`. It accepts a maximum of 100 works per venue-year per request (the current cap is 25), sorted by publication date. Raw responses are cached locally for six hours under `.cache/ai-research-observatory/`, and the coverage row records cache use. It records both source totals and scanned/included counts, including zero-result years and fetch errors. Source IDs are not a complete proceedings index; see limitations below.
3. The script normalizes paper-specific first-author and team affiliations, country codes, citation percentile, bibliographic details, and ranking evidence. It deduplicates by DOI or OpenAlex ID. A successfully queried venue-year replaces its previous sample; untouched or failed venue-years keep their previous records, while failed coverage is flagged.
4. Evidence-backed entries in `data/ai_research_observatory/reviews.json` override selected metadata during every refresh. The generated JSON is committed as the persistent, public snapshot. The dashboard never makes a live OpenAlex request or substitutes synthetic data.
   A review with `"exclude": true`, a reason in `review_note`, and an HTTPS source permanently suppresses an incorrect record even after the next refresh. To add a valid paper missed by the capped query, add its OpenAlex work ID, venue ID, year and official proceedings evidence URL to `data/ai_research_observatory/manual_works.json`. The collector fetches that work by ID and requires a matching OpenAlex source/year and the normal paper/topic filters. It retains an earlier verified copy if the API is temporarily unavailable; a never-verified addition fails the refresh. Inspect the actual proceedings as well, because OpenAlex can be wrong.
5. `.github/workflows/refresh-ai-research-observatory.yml` runs weekly and refreshes the current and previous calendar years. The `OPENALEX_API_KEY` repository secret is optional for this capped first-page collection, but a free key provides a larger OpenAlex budget. The workflow tests, builds, checks links, and commits only the snapshot.

To bootstrap or rebuild historical years:

```sh
python3 scripts/refresh_ai_research_observatory.py --from-year 2020 --to-year 2026 --cap 25
python3 -m unittest discover -s scripts -p 'test_ai_research_observatory.py'
node scripts/test_ai_research_observatory_core.cjs
./scripts/check_posts_have_tags.sh
python3 ./scripts/sync_llm_pricing_data.py
hugo --minify --cleanDestinationDir
./scripts/check_internal_links.sh public
```

Use `--venues asplos` or another venue ID for a scoped refresh. No API key is printed in the snapshot. OpenAlex [authentication and rate limits](https://help.openalex.org/api/authentication/) may change; watch action failures and coverage errors.

## Reviewed corrections

GitHub Pages is static. To correct a classification or attach award/code/leadership evidence, edit `data/ai_research_observatory/reviews.json` in a pull request or local commit and regenerate the snapshot. Use the OpenAlex ID as the key; a DOI key also works. Every correction **requires an HTTPS evidence URL**. Example:

```json
{
  "https://openalex.org/W123": {
    "leadership": "Joint",
    "award": true,
    "code_available": true,
    "resources": "8 NVIDIA H100 GPUs; source states 320 GPU-hours",
    "compute": {"gpu_type": "NVIDIA H100", "gpu_count": 8, "gpu_hours": 320, "accelerator_type": null, "training_flops": null, "model_parameters": null, "training_cost": null},
    "funding": "Institutional grant acknowledged in paper",
    "review_note": "Leadership supported by author-contribution statement.",
    "reviewer": "Your name",
    "date": "2026-10-15",
    "evidence_url": "https://example.org/paper-or-official-award-page"
  }
}
```

Only use `award: false` or `code_available: false` after an actual review that supports the negative, not because metadata lacks a link. A leadership correction needs explicit project-role evidence, not merely first-author affiliation or compute usage. Reviews are versioned through git history, not via a browser form. The current review file is empty; those fields remain unknown.

## Updating the pinned research tracker

Edit `static/data/ai-research-conference-history.json` for conference counts and award records. Each `counts` entry needs a venue ID, year, integer (or `null`) submitted and accepted counts, the exact track scope, and a direct organizer source URL. Do not infer submissions by dividing acceptances by a rounded acceptance rate. Keep missing years as gaps, never zero. Each `awards` entry needs the organizer-confirmed paper title and award, venue, year, a short editorial field and topic list, and a source URL. The keyword cloud counts only those selected award labels. The industry/university plot uses explicit title-keyword regexes in `static/js/ai-research-tracker.js`, first-author sectors from the current OpenAlex snapshot, and a year/sector denominator. Review both the keyword rule and source coverage before interpreting a change.

As of 2026-10-15, NeurIPS 2022 is omitted from the plotted ledger because its own 2022 fact sheet's 9,634 submissions/2,905 acceptances disagree with its stated 20% acceptance rate and the later NeurIPS 2023 comparison table's 10,411 main-track submissions. The CVPR 2025 organizer's technical-program release says 13,008/2,872; its later wrap-up says 12,008 submissions even though it also claims a 13% rise from 11,532 in 2024. The ledger uses the internally consistent technical-program release and records that conflict in `scope`. ICML 2025 has 3,260 main-track papers in its fact sheet, but no exact submission count there, so submitted is `null`. Other missing conference-years remain unplotted until an organizer source and comparable scope can be verified.

When asked to refresh the tracker, audit existing records first, remove incorrect ones, add newly confirmed organizer figures and awards, update `reviewed_at` and the post's `lastmod`, then regenerate the observatory snapshot if its records or classifications changed. Run the tests/build/link checks above and commit the resulting source and snapshot. The weekly action refreshes OpenAlex metadata, not organizer counts or award curation; those require manual review. GitHub Pages cannot perform an authoritative live conference-count refresh in the browser.

## Method and interpretation

- Venue inclusion uses the linked [CORE conference portal](https://portal.core.edu.au/conf-ranks/) or official [CCF list](https://www.ccf.org.cn/Academic_Evaluation/By_category/). The selected `CORE 2023` and `CCF 2022` editions are stated per venue; rankings can change. A*/A are mapped to prestige 1.0, B to 0.75. This is an explicit editorial mapping, not an official cross-system equivalence.
- NeurIPS, ICML, ACL, and CVPR are treated as AI-native. OSDI and ASPLOS require the `AI_WORDS` keyword match against title or OpenAlex topic/keyword metadata; the record stores the rule used. This heuristic has unmeasured precision and recall.
- First-author sector uses only the first byline author's paper affiliations. Both company and education yield `Mixed`. All author affiliations yield team sector `Joint` if company and education both occur. Team sector does **not** imply jointly led work. Unknown affiliations stay unknown. Corresponding and senior author names are recorded when OpenAlex exposes them; they do not determine leadership.
- A paper with multiple first-author affiliation countries contributes `1 / n` to each map count. The institution counter counts distinct displayed institution names, not consolidated legal entities.
- Score: `6 × sum(weight × verified component) / sum(available weights)`, where components are OpenAlex field/year normalized citation percentile, rank mapping, sourced award, and sourced public code. Defaults are 55/25/15/5. Scores require at least two components and 55% of selected weight available. Missing awards and code are not zero. The bar chart is the mean of scored papers, and displays scored/all counts. Impact share is a sum of scored values within classified first-author records; it is **not** a population estimate.
- Trend counts are tracked sample counts. Percentages use classified first-author records in the filtered sample; impact contribution uses scored values in that same classified set. Filters affect charts, map, metrics, and table. The table and exports include the filtered set and currently selected weights.
- GPT-3, ChatGPT, LLaMA/GPT-4, Llama 3, DeepSeek-R1/GPT-5 are contextual releases linked to their originators. No causal effect is inferred. There is no verified GPT-6 milestone in this dataset; 2026 is labelled a research watch, not a release assertion.

## Limits before any research conclusion

This is **not a census**. The initial cap selects up to 25 earliest-dated works per venue-year from a single OpenAlex source ID. OpenAlex source IDs miss some years or switch across proceedings series; the initial OSDI source, for example, yields zero matches in sampled years. A zero means *no matches under this query*, not zero conference papers. Other venue-years are capped; title and topic filters can drop true positives or admit false positives. OpenAlex can mislabel proceedings types or include workshop material. A DOI-level comparison against official proceedings and [DBLP](https://dblp.org/) is needed before estimating conference-wide shares. Recent-year counts and citations have collection/publication lag.

Landmark corporate technical reports outside peer-reviewed proceedings are excluded, so this page cannot fully answer whether industry dominates **all** AI research. Unknown project leadership and award/code evidence prevent reliable claims about RQ2 and a complete RQ3. The dashboard deliberately reports missingness rather than filling it with guesses. Revisit source identity, proceedings track, title/DOI reconciliation, institution parentage, and audited keyword precision before publication-grade inference.

The map outline derives from the provided prototype's `assets/world.svg` (Basemap-bundled geography, as noted in its README). Country markers are approximate; the sortable country list includes countries without mapped coordinates.
