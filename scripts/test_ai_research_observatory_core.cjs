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

console.log('Observatory scoring and aggregation checks passed.');
