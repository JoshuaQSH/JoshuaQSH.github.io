# AI Research Observatory: cross-area venue coverage and publication trends

Date: 2026-10-16

## Outcome and scope

Extend the pinned AI Research Tracker post and AI Research Observatory page from their current AI-facing inventory to include the 23 requested systems, architecture, compiler, parallel/distributed, and software-engineering conference series. Readers should see venue-wide main-track publication volume from 2020 onward separately from the AI-related papers used in the Observatory. Neither bibliography counts nor sampled records are organizer submission or acceptance figures. Keep selected arXiv-only work outside conference totals.

The 23 required series are PLDI, POPL, SOSP, OSDI, OOPSLA, PPoPP, SC, HPCA, ASPLOS, ISCA, USENIX ATC, EuroSys, CGO, CC, PACT, Euro-Par, ICDCS, IPDPS, MLSys, FSE, ASE, ICSE, and ISSTA. Preserve the existing 53-series catalog, and audit the CORE 2023 A*/A, CCF 2026 A/B, and TH-CPL AI A lists for other eligible AI-related venues in the same subject boundary. Exclude unrelated database, security, and other non-AI fields unless the user later changes that boundary. Store each actual ranking membership and source rather than assigning a rank to a requested venue by inference.

The rollout is evidence-first: publish each verified venue-year when ready and display unresolved cells as gaps. A 2026 edition not yet indexed, a non-meeting year, a source error, and a verified zero are different states. Do not imply the 2020-2026 ledger is a full census while any main-track source or AI classification remains incomplete.

## Chosen approach

Use source-tiered, venue-specific collection. An official main-track proceedings or journal issue index is preferred; a bounded DBLP query is a corroborating or fallback bibliography source; OpenAlex enriches matched works with abstracts, topics, citations, and paper-specific affiliations. DBLP's stream count alone is not an organizer acceptance count or automatic proof of main-track completeness. OpenAlex source counts remain independently labelled index matches, not a proceedings census.

OpenAlex-only mapping would reproduce the current false-gap problem. Downloading and maintaining a full DBLP dump would add substantial storage and operational cost to this Hugo/GitHub Pages site. The public snapshot stays compact: it publishes venue-year counts, provenance, and tracked AI-paper records, not every non-AI bibliographic record.

## Inventory and source rules

Extend `scripts/ai_research_venues.py` and its generated catalog with the required venue IDs, display names, areas, ranking evidence, AI-adjacent flag, and source-rule identifiers. Keep source rules separate from rank metadata. Each source rule identifies the main research track, event-year mapping, official index URL when available, DBLP stream or issue mapping, excluded companion/workshop/artifact/editorial material, and any editions that require a different rule.

Journal-published research tracks need explicit mappings: OOPSLA/POPL use the applicable PACMPL issues and FSE 2024 onward uses PACMSE research-track issues. Other track or publisher changes must be captured per edition, not hidden behind a generic venue query. For DBLP records, use the event year where supplied; verify year and track against the source before calling a count main-track. De-duplicate by DOI, then normalized title within a venue-year, retaining all source links. A source disagreement creates a review status instead of silently selecting the larger number.

For each venue-year, record:

- `main_track_total`: count only when a complete, verified main-track index exists; otherwise `null`.
- `bibliography_total`: DBLP or other indexed count when available, separately labelled and never substituted for `main_track_total` without track verification.
- `ai_matched_count`, `ai_reviewed_count`, and `ai_unresolved_count`: counts within the eligible bibliography, with classification rule/version, scanned-record denominator, and completeness status. `ai_matched_count` is an observed match count, not an assertion that every AI paper was found.
- `sampled_papers`: number of AI records published in the Observatory, distinct from all three totals above.
- `status`, `track_scope`, source URL/provider, checked-at time, and explanatory gap or conflict reason. Statuses distinguish verified, partial, unresolved, source-error, not-yet-published, and not-held.

Organizer submissions and acceptances remain in the manually reviewed conference-history file with their own organizer URL and track definition. Never derive them from DBLP, OpenAlex, proceedings page length, or a rounded acceptance rate.

## AI selection and paper evidence

For the 23 cross-area series, read all available main-track titles/DOIs for a year before selecting AI candidates; do not use the existing capped OpenAlex sample as the AI denominator. Show scanned/eligible records and mark an incomplete scan partial; apply any public paper cap only after classification. Match DOI/title to OpenAlex when possible. A reproducible, versioned relevance rule uses explicit AI title/abstract/topic evidence, including ML systems, model inference/training, AI compilers, and AI-assisted software engineering. Ambiguous title-only matches enter a review queue rather than a confirmed AI subset. Evidence-backed manual include/exclude decisions override the rule and survive refreshes. Publish the rule and a per-venue-year reviewed/unknown tally so sparse samples are visible.

The published paper ledger contains only AI-matched records with provenance. First-author sector and country require paper-specific affiliation evidence; missing affiliations stay unknown and do not enter sector shares. Official-only works may lack citation or affiliation metadata. Preserve the existing separate arXiv-only section, with no conference acceptance implication.

Repository association requires a paper-specific source. A GitHub 404 or rate limit means accessibility, stars, activity, and maintenance evidence are unknown; it does not invalidate the paper or prove code never existed. Keep reviewed adoption and maintenance evidence separate from stars and pushes. Retain previously verified records on transient source failures, but mark their checked-at time and status.

## Page behavior

The pinned `ai-research-tracker.md` remains on the home page. Its organizer submission/acceptance plot remains separate. The venue plot gains clearly labelled main-track and AI-matched series, source links, track scope, and visible gaps. Venue, year, area, and ranking filters keep 76-plus series navigable. Do not plot a bibliography fallback as a verified main-track total.

The Observatory remains an analysis of tracked AI papers, not of every paper in cross-area venues. Its coverage view exposes the venue-year status and all distinct count types. Keyword, geography, sector, and impact views use only the AI ledger and state their sample/affiliation denominators. The arXiv-only selection remains separate.

Replace the Publication trajectory chart with three thin, unfilled lines and small circular markers: Industry, University, and Research Institute. The measure selector has exactly three choices: Paper count, Publication share (%), and Year-over-year growth (%). Count means tracked, sector-classified AI papers, not all conference acceptances. Share is a sector's count divided by all classified sector counts in that year. Growth is `(current count - previous count) / previous count * 100`; the first year, a missing year, or a zero/unusable previous count produces a gap rather than zero or infinity. Negative growth is supported. Missing source coverage is not connected through as if observed. Tooltips disclose counts, denominators, year, and measure. Influence stays in the separate score comparison, not a scored-papers-only trend filter.

Show the score equation prominently near the existing weight controls: `score = 6 * sum(weight * available component value) / sum(available weights)`. Also show `evidence coverage = sum(available weights) / sum(selected weights)`, the existing minimum-evidence rule, and each paper's component value, weight, contribution, and omission reason in its detail panel. Unknown components are omitted, never treated as zero. The formula explains the existing editorial 0-6 proxy; it does not turn score into a calibrated impact or industry-use probability.

Use the user's existing `static/images/hodgepodge/AI_Research_ Academia Meets Industry.png` as the Observatory cover via its already edited front matter. Verify that its generated URL and Hodgepodge card render correctly. Preserve unrelated local coffee-wall changes.

## Refresh, validation, and release

Add focused, cached source adapters and tests for track/year boundary cases, including journal issues, companion exclusions, source disagreements, non-meeting years, and missing editions. Rate-limit DBLP/OpenAlex/GitHub requests and make partial refreshes non-destructive. The scheduled workflow updates recent years; `backfill-2020` refreshes historical years with the existing OpenAlex secret. Keep one snapshot writer at a time to avoid competing auto-commits and rebase conflicts. Manual ranking, organizer-count, award, relevance, adoption, and maintenance reviews remain manual.

Before publication, verify that all 23 required series are catalogued with actual rank evidence or an explicit unranked status; every calendar cell from 2020 through the current year has a source-backed count or a truthful gap reason; no index count is labelled an organizer acceptance; and every published AI-paper record has venue/year provenance. Audit additional ranked AI-related venues and document inclusion decisions. Test aggregation and score-breakdown arithmetic, run Python and JavaScript tests, build Hugo, check tags and internal links, and inspect desktop/mobile rendering of the cover and charts. Commit only intended source, snapshot, documentation, and cover files, then push to `master` after reconciling any remote refresh commit without force-pushing.
