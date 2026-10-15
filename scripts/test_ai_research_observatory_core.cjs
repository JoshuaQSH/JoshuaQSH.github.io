const assert = require('node:assert/strict');
require('../static/js/ai-research-observatory-core.js');

const core = globalThis.AIResearchCore;
const weights = { citation: 55, venue: 25, award: 15, code: 5 };
const reviewed = { citation_percentile: .8, prestige: 1, award: true, code_available: false };
const scored = core.score(reviewed, weights);
assert.equal(scored.coverage, 1);
assert.ok(Math.abs(scored.value - 5.04) < 1e-9);
assert.equal(scored.components.code, 0);

const unknown = core.score({ citation_percentile: .8, prestige: 1, award: null, code_available: null }, weights);
assert.equal(unknown.coverage, .8);
assert.ok(Math.abs(unknown.value - 5.175) < 1e-9);
assert.equal(core.score({ prestige: 1 }, weights).value, null);
assert.equal(core.score(reviewed, { citation: 0, venue: 0, award: 0, code: 0 }).value, null);

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
