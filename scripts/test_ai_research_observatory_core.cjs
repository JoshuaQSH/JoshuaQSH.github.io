const assert = require('node:assert/strict');
require('../static/js/ai-research-observatory-core.js');

const core = globalThis.AIResearchCore;
const weights = { citation: 40, venue: 15, award: 10, code: 5, stars: 5, activity: 5, maintenance: 10, adoption: 10 };
const reviewed = { citation_percentile: .8, prestige: 1, award: true, code_available: false };
const scored = core.score(reviewed, weights);
assert.equal(scored.coverage, .7);
assert.ok(Math.abs(scored.value - (6 * (40 * .8 + 15 + 10) / 70)) < 1e-9);
assert.equal(scored.components.code, 0);

const unknown = core.score({ citation_percentile: .8, prestige: 1, award: null, code_available: null }, weights);
assert.equal(unknown.coverage, .55);
assert.ok(Math.abs(unknown.value - (6 * (40 * .8 + 15) / 55)) < 1e-9);
assert.equal(core.score({ prestige: 1 }, weights).value, null);
assert.equal(core.score(reviewed, Object.fromEntries(Object.keys(weights).map(key => [key, 0]))).value, null);

const evidence = { ...reviewed, github: { stars: 1000, pushed_at: '2026-09-10T00:00:00Z', checked_at: '2026-10-15T00:00:00Z', archived: false, fork: false }, maintenance_status: 'active', maintenance_evidence_url: 'https://github.com/org/repo/releases', review: { date: '2026-10-15' }, adoption_status: 'integration', adoption_evidence_url: 'https://pytorch.org/blog/example/' };
const impact = core.score(evidence, weights, new Date('2026-10-15T00:00:00Z'));
assert.equal(impact.coverage, 1);
assert.equal(impact.components.stars, 1);
assert.equal(impact.components.activity, 1);
assert.equal(impact.components.maintenance, 1);
assert.equal(impact.components.adoption, .6);
const officialImpact = core.score({ ...evidence, citation_percentile: null, award: null }, weights, new Date('2026-10-15T00:00:00Z'));
assert.equal(officialImpact.coverage, .5);
assert.ok(officialImpact.value !== null);
assert.equal(core.score({ ...evidence, citation_percentile: null, award: null, adoption_status: 'Unknown', maintenance_status: 'Unknown' }, weights, new Date('2026-10-15T00:00:00Z')).value, null);
assert.equal(core.score({ ...evidence, adoption_status: 'production', adoption_evidence_url: null }, weights).components.adoption, undefined);
assert.equal(core.score({ ...evidence, github: { ...evidence.github, checked_at: '2024-01-01T00:00:00Z' } }, weights).components.stars, undefined);
assert.equal(core.score({ ...evidence, github: { ...evidence.github, pushed_at: null } }, weights).components.activity, undefined);
assert.equal(core.score({ ...evidence, review: { date: '2024-01-01' } }, weights, new Date('2026-10-15T00:00:00Z')).components.maintenance, undefined);

const papers = [
  { title: 'Paper A', year: 2025, area: 'AI', venue_id: 'acl', first_author: 'One', first_author_sector: 'Industry',
    first_author_affiliations: ['Research Lab'], countries: ['GB', 'US'], team_sector: 'Joint', ...reviewed },
  { title: 'Paper B', year: 2024, area: 'Systems', venue_id: 'asplos', first_author: 'Two', first_author_sector: 'University',
    first_author_affiliations: ['University'], countries: ['GB'], team_sector: 'University', citation_percentile: .5, prestige: 1 }
];
assert.equal(core.filterPapers(papers, { country: 'US' }).length, 1);
assert.equal(core.filterPapers(papers, { sector: 'Joint' }).length, 1);
assert.equal(core.filterPapers(papers, { search: 'research lab' }).length, 1);
assert.equal(core.sectorStats(papers, weights).find(x => x.sector === 'Joint').scored, 1);
assert.equal(core.geography(papers).find(x => x.code === 'GB').count, 1.5);
assert.equal(core.trend(papers, weights, 'count').find(x => x.year === 2025).Industry, 1);
assert.equal(core.trend(papers, weights, 'count').at(-1).year, 2025);

const publicationPapers = [
  { year: 2024, first_author_sector: 'Industry' },
  { year: 2024, first_author_sector: 'Industry' },
  { year: 2024, first_author_sector: 'University' },
  { year: 2024, first_author_sector: 'Unknown' },
  { year: 2025, first_author_sector: 'Industry' },
  { year: 2025, first_author_sector: 'Industry' },
  { year: 2025, first_author_sector: 'Industry' },
  { year: 2025, first_author_sector: null },
  { year: 2026, first_author_sector: 'Unknown' }
];
assert.equal(core.trend(publicationPapers, weights, 'growth', 2026).find(row => row.year === 2024).Industry, null);
const publicationCount = core.trend(publicationPapers, weights, 'count', 2026);
assert.deepEqual(publicationCount.find(row => row.year === 2024), {
  year: 2024, Industry: 2, University: 1, 'Research Institute': 0, count: 4, classifiedCount: 3
});
assert.deepEqual(publicationCount.find(row => row.year === 2025), {
  year: 2025, Industry: 3, University: 0, 'Research Institute': 0, count: 4, classifiedCount: 3
});

const publicationShare = core.trend(publicationPapers, weights, 'share', 2026);
assert.equal(Math.round(publicationShare.find(row => row.year === 2024).Industry * 10) / 10, 66.7);
assert.equal(Math.round(publicationShare.find(row => row.year === 2024).University * 10) / 10, 33.3);
assert.equal(publicationShare.find(row => row.year === 2025).Industry, 100);
assert.equal(publicationShare.find(row => row.year === 2025).University, 0);
assert.equal(publicationShare.find(row => row.year === 2026).Industry, null);
assert.equal(publicationShare.find(row => row.year === 2026).University, null);
assert.equal(publicationShare.find(row => row.year === 2026).classifiedCount, 0);
assert.equal(core.trend(publicationPapers, weights, 'growth', 2026).find(row => row.year === 2026).Industry, null);

const publicationGrowth = core.trend(publicationPapers, weights, 'growth', 2026);
assert.equal(publicationGrowth.find(row => row.year === 2025).Industry, 50);
assert.equal(publicationGrowth.find(row => row.year === 2025).University, -100);
assert.equal(publicationGrowth.find(row => row.year === 2025)['Research Institute'], null);

const zeroBaseline = core.trend([
  { year: 2024, first_author_sector: 'University' },
  { year: 2025, first_author_sector: 'Industry' }
], weights, 'growth', 2025);
assert.equal(zeroBaseline.find(row => row.year === 2025).Industry, null);

const coveredYears = new Set([2025]);
const coveredCount = core.trend(publicationPapers, weights, 'count', 2026, coveredYears);
assert.equal(coveredCount.find(row => row.year === 2024).Industry, null);
assert.equal(coveredCount.find(row => row.year === 2025).Industry, 3);
assert.equal(coveredCount.find(row => row.year === 2026).Industry, null);
const coveredGrowth = core.trend(publicationPapers, weights, 'growth', 2026, coveredYears);
assert.equal(coveredGrowth.find(row => row.year === 2025).Industry, null);
assert.equal(coveredGrowth.find(row => row.year === 2026).Industry, null);

const segmentRows = [
  { year: 2020, Industry: 2 }, { year: 2021, Industry: 3 },
  { year: 2022, Industry: null }, { year: 2023, Industry: -1 },
  { year: 2024, Industry: NaN }, { year: 2025, Industry: 0 }
];
assert.deepEqual(core.lineSegments(segmentRows, 'Industry').map(segment => segment.map(row => row.year)),
  [[2020, 2021], [2023], [2025]]);
assert.deepEqual(core.trendRange(segmentRows, 'growth'), [-1, 3]);
assert.deepEqual(core.trendRange([{ Industry: -40, University: -10, 'Research Institute': null }], 'growth'), [-40, 0]);
assert.deepEqual(core.trendRange([{ Industry: 3, University: 2, 'Research Institute': null }], 'count'), [0, 3]);
assert.deepEqual(core.trendRange([{ Industry: 25, University: 75, 'Research Institute': null }], 'share'), [0, 100]);

const trendCatalog = [
  { id: 'alpha', area: 'AI' }, { id: 'beta', area: 'AI' }, { id: 'gamma', area: 'AI' }
];
const trendCoverage = [
  { venue_id: 'alpha', year: 2024, status: 'verified', ai_scan_status: 'complete', sampled_papers: 1 },
  { venue_id: 'alpha', year: 2025, status: 'verified', ai_scan_status: 'complete', sampled_papers: 2 },
  { venue_id: 'beta', year: 2025, status: 'source-error', ai_scan_status: 'source-error', stale: true, sampled_papers: 4 },
  { venue_id: 'gamma', year: 2025, status: 'unresolved', ai_scan_status: 'partial', sampled_papers: 3 },
  { venue_id: 'alpha', year: 2026, status: 'verified', ai_scan_status: 'complete', sampled_papers: 0 }
];
const trendPapers = [
  { title: 'baseline', venue_id: 'alpha', year: 2024, area: 'AI', first_author_sector: 'Industry' },
  { title: 'industry', venue_id: 'alpha', year: 2025, area: 'AI', first_author_sector: 'Industry' },
  { title: 'university', venue_id: 'alpha', year: 2025, area: 'AI', first_author_sector: 'University' },
  { title: 'stale industry', venue_id: 'beta', year: 2025, area: 'AI', first_author_sector: 'Industry' },
  { title: 'unresolved industry', venue_id: 'gamma', year: 2025, area: 'AI', first_author_sector: 'Industry' }
];
const trendSelection = core.trendSelection(trendPapers, trendCoverage, trendCatalog, { area: 'AI', year: '2025', sector: 'Industry' });
assert.deepEqual(trendSelection.papers.map(paper => paper.title), ['baseline', 'industry', 'university']);
assert.deepEqual([...trendSelection.usableYears], [2024, 2025, 2026]);
const selectedShares = core.trend(trendSelection.papers, weights, 'share', 2026, trendSelection.usableYears);
assert.equal(selectedShares.find(row => row.year === 2025).Industry, 50);
assert.equal(selectedShares.find(row => row.year === 2025).classifiedCount, 2);
const selectedCounts = core.trend(trendSelection.papers, weights, 'count', 2026, trendSelection.usableYears);
assert.equal(selectedCounts.find(row => row.year === 2025).Industry, 1);
assert.equal(selectedCounts.find(row => row.year === 2026).Industry, 0);
assert.equal(core.trend(trendSelection.papers, weights, 'share', 2026, trendSelection.usableYears).find(row => row.year === 2026).Industry, null);
assert.equal(core.trend(trendSelection.papers, weights, 'growth', 2026, trendSelection.usableYears).find(row => row.year === 2026).Industry, null);

console.log('Observatory scoring and aggregation checks passed.');
