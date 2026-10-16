# AI Research Observatory

The native Hodgepodge page is `content/hodgepodge/ai-research-observatory.md` with a Hugo layout in `layouts/hodgepodge/ai-research-observatory.html`. The browser loads `static/data/ai-research-observatory.json`; no server or public write API is needed on GitHub Pages. UI behavior is split between `static/js/ai-research-observatory-core.js` (pure calculations) and `static/js/ai-research-observatory.js` (rendering), with site-aware styling in `static/css/ai-research-observatory.css`.

The pinned companion post is `content/posts/ai-research-tracker.md`. Its verified organizer submission/acceptance figures and award highlights are manually curated in `static/data/ai-research-conference-history.json`. A separate per-venue chart reads indexed-paper counts from the observatory snapshot. Neither index counts nor sampled paper counts are called acceptances.

## Data flow

1. Edit `scripts/ai_research_venues.py` and regenerate `data/ai_research_observatory/venues.json` with `python3 scripts/ai_research_venues.py`. The 53-series inventory is the union of AI-facing CORE 2023 A*/A (FoR 4602/4603/4611), CCF 2026 AI A/B, and TH-CPL 2019 AI A, plus ranked AI-facing retrieval, recommender, multimedia, speech, and data-mining series from other ranking categories. Pure graphics (SIGGRAPH), geospatial (SIGSPATIAL), general database, security, and systems venues are excluded. The ranked memberships are separate fields; they are not collapsed into one supposed rank. A missing or sparse OpenAlex source ID is not imputed. `ai_native: false` invokes an AI-topic filter for cross-area venues.
2. Run the dependency-free collector. It samples OpenAlex works by year and verified conference source ID (default 25, maximum 100), accepting `article` and `conference-paper` types while excluding obvious non-paper titles. OpenAlex's [`conference-paper` classification](https://help.openalex.org/data/work-types/) is still rolling out, so filtering to that type alone produces false zero years. Independent NeurIPS main-track, PMLR ICML/AISTATS/COLT/UAI, ACL Anthology ACL/EMNLP/NAACL/EACL/COLING main-volume, and CVF CVPR/ICCV/WACV indexes contribute at most 250 records per venue-year. The index total is the number of entries parsed from that source, not an organizer acceptance total. `source_total` is OpenAlex source matches, not a proceedings census. OpenAlex responses are cached for six hours and official HTML for one day in `.cache/ai-research-observatory/`.
3. Paper records merge by normalized venue/year/title, retaining both source links. OpenAlex supplies paper-specific affiliations and citation percentiles where available; official-only papers keep those fields unknown. A successfully queried source replaces its sample. Failed sources retain previously verified papers and are flagged in coverage. `data/ai_research_observatory/featured_proceedings.json` forces verified official papers into a capped sample.
4. PMLR `Software` links establish paper-specific code evidence. The collector recognizes GitHub repository links and queries the GitHub API for stars, latest push, archive/fork state, and a checked-at timestamp within a request cap. GitHub stars and pushes do not prove business use or future maintenance. If GitHub is unavailable, metrics remain unknown or retain their dated previous snapshot.
5. Evidence-backed entries in `data/ai_research_observatory/reviews.json` override metadata on every refresh. An `"exclude": true` review with a reason and HTTPS evidence suppresses an incorrect record. To add an OpenAlex paper missed by the cap, use `data/ai_research_observatory/manual_works.json` with its work ID, venue, year and official evidence; the collector verifies its source/year/type. For an official-only paper, use `featured_proceedings.json` and key its review by the official URL. The generated JSON is committed as the public snapshot; the browser makes no live metadata requests.
6. `.github/workflows/refresh-ai-research-observatory.yml` runs weekly for the current and previous calendar years. Set a verified `OPENALEX_API_KEY` repository Actions secret for OpenAlex metadata refresh; without it, the weekly job refreshes only official proceedings and GitHub evidence because anonymous daily usage cannot reliably cover the catalog. In Actions, **Refresh AI Research Observatory** → **Run workflow** offers `refresh_scope: backfill-2020` to process 2020 through the current year; this mode requires the secret and does not fall back to a keyless run. `GITHUB_TOKEN` is supplied by Actions. NeurIPS index mappings stop at 2025 until the 2026 main-track volume is verified; ICML 2026 uses PMLR volume 306. The workflow tests, builds, checks links, and commits only the snapshot.

To bootstrap or rebuild historical years:

```sh
python3 scripts/ai_research_venues.py
read -rsp 'OpenAlex API key: ' OPENALEX_API_KEY; echo; export OPENALEX_API_KEY
python3 scripts/refresh_ai_research_observatory.py --from-year 2020 --cap 40 --official-cap 250 --github-cap 30
unset OPENALEX_API_KEY
python3 -m unittest discover -s scripts -p 'test_ai_research*.py'
node scripts/test_ai_research_observatory_core.cjs
./scripts/check_posts_have_tags.sh
python3 ./scripts/sync_llm_pricing_data.py
hugo --minify --cleanDestinationDir
./scripts/check_internal_links.sh public
```

Keep the API key out of command history, logs, and committed files. Use `--venues neurips icml` for a scoped refresh, `--skip-openalex` to backfill official proceedings while retaining existing OpenAlex records, or `--cached-only` for an offline partial rebuild. Inspect all 371 venue-year calendar cells before claiming a full corpus; biennial conferences also have non-meeting years. HTTP 429 stops further OpenAlex calls in that run; missing results remain marked rather than set to zero. A successful backfill is still a **capped sample**, not a complete paper census: five catalog venues have no verified OpenAlex source ID and most venues lack independent proceedings parsers. The 2026-10-16 anonymous-budget build has only partial OpenAlex coverage and must not be presented as a complete multi-venue census. OpenAlex [authentication and limits](https://help.openalex.org/api/authentication/) and GitHub [rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api) may change.

## Reviewed corrections

GitHub Pages is static. To correct a classification or attach award/code/leadership evidence, edit `data/ai_research_observatory/reviews.json` and regenerate the snapshot. Use the OpenAlex ID, DOI, or official proceedings URL as the key. Every correction **requires an HTTPS evidence URL**. Example:

```json
{
  "https://openalex.org/W123": {
    "leadership": "Joint",
    "award": true,
    "repository_url": "https://github.com/org/repo",
    "repository_evidence_url": "https://example.org/paper-that-links-the-repository",
    "adoption_status": "integration",
    "adoption_evidence_url": "https://example.org/integrator-release-notes",
    "maintenance_status": "active",
    "maintenance_evidence_url": "https://github.com/org/repo/releases",
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

Only use `award: false` or `code_available: false` after an actual review supporting the negative. A repository needs a paper-to-repository association URL; a matching name alone is insufficient. Adoption is `Unknown`, `integration`, `pilot`, or `production`: use `production` only for explicit deployment or case-study evidence, never stars or a library integration alone. Maintenance is `Unknown`, `active`, or `inactive`, with dated release/maintainer evidence and a `date` field; its score expires after 365 days unless re-reviewed. `active` is an assessment at review time, not a promise. Leadership needs explicit project-role evidence. Reviews are versioned in git. The current reviewed example is FlashAttention; its PyTorch integration does not prove business deployment.

## Updating the pinned research tracker

Edit `static/data/ai-research-conference-history.json` for conference counts and award records. Each `counts` entry needs a venue ID, year, integer (or `null`) submitted and accepted counts, the exact track scope, and a direct organizer source URL. Do not infer submissions by dividing acceptances by a rounded acceptance rate. Keep missing years as gaps, never zero. Each `awards` entry needs the organizer-confirmed paper title and award, venue, year, a short editorial field and topic list, and a source URL. The keyword cloud counts only those selected award labels. The industry/university plot uses explicit title-keyword regexes in `static/js/ai-research-tracker.js`, classified first-author sectors from the merged snapshot, and a year/sector denominator. Official-only papers without affiliations are excluded from those curves. Review both the keyword rule and source coverage before interpreting a change.

As of 2026-10-15, NeurIPS 2022 is omitted from the plotted ledger because its own 2022 fact sheet's 9,634 submissions/2,905 acceptances disagree with its stated 20% acceptance rate and the later NeurIPS 2023 comparison table's 10,411 main-track submissions. The CVPR 2025 organizer's technical-program release says 13,008/2,872; its later wrap-up says 12,008 submissions even though it also claims a 13% rise from 11,532 in 2024. The ledger uses the internally consistent technical-program release and records that conflict in `scope`. ICML 2025 has 3,260 main-track papers in its fact sheet, but no exact submission count there, so submitted is `null`. Other missing conference-years remain unplotted until an organizer source and comparable scope can be verified.

When asked to refresh the tracker, audit existing records first, remove incorrect ones, add newly confirmed organizer figures and awards, update `reviewed_at` and the post's `lastmod`, then regenerate the observatory snapshot if its records or classifications changed. Run the tests/build/link checks above and commit the resulting source and snapshot. The weekly action refreshes sampled publication and GitHub metadata, not organizer counts, award curation, or production/maintenance reviews; those require manual review. GitHub Pages cannot perform an authoritative live conference-count refresh in the browser.

## Method and interpretation

- Venue inclusion uses the linked [CORE 2023 export](https://portal.core.edu.au/conf-ranks/?by=all&page=1&search=&sort=arank&source=CORE2023), [CCF 2026 recommended-list PDF](https://lib.ecnu.edu.cn/_upload/article/files/e2/d9/dd45764345088869915f6b3617a4/28891f1f-eb8a-4000-a279-6e7141d92488.pdf), and [TH-CPL PDF](https://numbda.cs.tsinghua.edu.cn/~yuwj/TH-CPL.pdf). Ranked memberships and editions are preserved independently. A*/A are mapped to prestige 1.0, B to 0.75. This is an editorial score proxy, not an official cross-system equivalence.
- AI-native venues accept their indexed conference-paper metadata. AI-adjacent multimedia, retrieval, recommender, and data-mining venues require the `AI_WORDS` match against title or OpenAlex topic/keyword metadata; each record stores the applied rule. This heuristic has unmeasured precision and recall. The catalog excludes non-AI systems venues even if individual papers there are AI-related.
- First-author sector uses only the first byline author's paper affiliations. Both company and education yield `Mixed`. All author affiliations yield team sector `Joint` if company and education both occur. Team sector does **not** imply jointly led work. Unknown affiliations stay unknown. Corresponding and senior author names are recorded when OpenAlex exposes them; they do not determine leadership.
- A paper with multiple first-author affiliation countries contributes `1 / n` to each map count. The institution counter counts distinct displayed institution names, not consolidated legal entities.
- Score: `6 × sum(weight × available component) / sum(available weights)`. Defaults are citation percentile 40, venue 15, award 10, public code 5, GitHub stars 5, recent repository activity 5, reviewed maintenance 10, and reviewed adoption 10. Stars use a capped log scale (`log(1+stars)/log(1001)`); activity is 1 for a push within 180 days and declines to 0 by 365 days. GitHub metrics are eligible only from an un-forked repository checked within 45 days. Reviewed maintenance is active 1 / inactive 0 with evidence no older than 365 days; reviewed adoption is pilot .35 / integration .6 / production 1. These ordinal mappings are **editorial proxies**, not calibrated outcome probabilities. A score needs two components and 55% selected-weight coverage, or four including code and reviewed use/maintenance with 50% coverage. Available components are renormalized; show coverage beside each score because differently evidenced records are not directly comparable. Unknown evidence is omitted, not zero. Scored impact share is not a population estimate.
- Trend counts are tracked sample counts. Percentages use classified first-author records in the filtered sample; impact contribution uses scored values in that same classified set. Filters affect charts, map, metrics, and table. The table and exports include the filtered set and currently selected weights.
- GPT-3, ChatGPT, LLaMA/GPT-4, Llama 3, DeepSeek-R1/GPT-5 are contextual releases linked to their originators. No causal effect is inferred. There is no verified GPT-6 milestone in this dataset; 2026 is labelled a research watch, not a release assertion.

## Limits before any research conclusion

This is **not a census**. The rank catalog is complete for the defined AI-area boundary, but indexed-paper coverage is not: OpenAlex source IDs miss papers and entire years, and some venues lack a verified source mapping. Independent NeurIPS/PMLR/ACL/CVF proceedings indexes fill some gaps, but their 250-record paper sample cap remains a sample; the parsed index total is only a source-page count. Merging by normalized title can miss differing titles or rarely combine collisions. Official index totals are not interchangeable with organizer acceptance totals. Missing affiliation/citation data on official-only records makes sector and impact comparisons selective. OpenAlex can mislabel paper types or include workshops. DOI-level reconciliation against official proceedings and [DBLP](https://dblp.org/) remains necessary before conference-wide estimates. Recent-year counts and citations have lag.

Landmark corporate technical reports outside peer-reviewed proceedings are excluded, so this page cannot answer whether industry dominates **all** AI research. GitHub stars may be unrelated to adoption; a recent push can be automation; a public repository does not prove deployed business use. Adoption and maintenance reviews are sparse and time-sensitive. The dashboard reports missingness instead of guessing. Revisit track identity, DOI/title reconciliation, institution parentage, code association, industry-use claims, and audited keyword precision before publication-grade inference.

The map outline derives from the provided prototype's `assets/world.svg` (Basemap-bundled geography, as noted in its README). Country markers are approximate; the sortable country list includes countries without mapped coordinates.
