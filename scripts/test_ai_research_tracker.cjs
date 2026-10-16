const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const { execFileSync } = require('node:child_process');

const repo = path.resolve(__dirname, '..');
const catalog = JSON.parse(fs.readFileSync(path.join(repo, 'data/ai_research_observatory/venues.json')));
const required = ['pldi', 'popl', 'sosp', 'osdi', 'oopsla', 'ppopp', 'sc', 'hpca', 'asplos', 'isca',
  'usenix-atc', 'eurosys', 'cgo', 'cc', 'pact', 'euro-par', 'icdcs', 'ipdps', 'mlsys', 'fse', 'ase', 'icse', 'issta'];
assert.equal(catalog.filter(venue => venue.source_rule_id).length, 35);
for (const id of required) assert.ok(catalog.some(venue => venue.id === id && venue.source_rule_id), `${id} in catalog`);

class Element {
  constructor(tag = 'div') {
    this.tagName = tag.toLowerCase(); this.children = []; this.attributes = {}; this.listeners = {};
    this.style = { setProperty() {} }; this.value = ''; this.dataset = {}; this._text = '';
  }
  set textContent(value) { this.children = []; this._text = String(value ?? ''); }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
  get firstChild() { return this.children[0] || null; }
  append(...items) { for (const item of items) this.children.push(typeof item === 'string' ? new Text(item) : item); }
  appendChild(item) { this.append(item); return item; }
  removeChild(item) { this.children.splice(this.children.indexOf(item), 1); }
  replaceChildren(...items) { this.children = []; this._text = ''; this.append(...items); }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  getAttribute(key) { return this.attributes[key]; }
  addEventListener(name, listener) { (this.listeners[name] ||= []).push(listener); }
  dispatch(name) { for (const listener of this.listeners[name] || []) listener({ target: this, preventDefault() {} }); }
  showModal() {} close() {} scrollIntoView() {}
}
class Text extends Element { constructor(value) { super('#text'); this._text = value; } }

function descendants(element, predicate) {
  return [element, ...element.children.flatMap(child => descendants(child, predicate))].filter(predicate);
}
function pageFixture(html, snapshot, history) {
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
  const elements = Object.fromEntries(ids.map(id => [id, new Element()]));
  const embedded = html.match(/<script id="ai-research-catalog-data" type="application\/json">([\s\S]*?)<\/script>/);
  assert.ok(embedded, 'rendered page embeds the complete ranked catalog');
  const publishedCatalog = JSON.parse(embedded[1]);
  assert.equal(publishedCatalog.filter(venue => venue.source_rule_id).length, 35, 'all 35 new cross-area series reach the page');
  for (const id of required) assert.ok(publishedCatalog.some(venue => venue.id === id), `${id} reaches the page`);
  elements['ai-research-catalog-data'].textContent = embedded[1];
  const root = elements.observatory || new Element();
  root.dataset = { snapshot: '/data/ai-research-observatory.json', historyUrl: '/data/ai-research-conference-history.json', observatoryUrl: '/data/ai-research-observatory.json' };
  for (const [id, value] of Object.entries({ 'research-count-mode': 'both', 'research-index-venue': 'neurips',
    'research-topic': 'language', 'aro-trend-mode': 'count', 'aro-sort': 'score' })) if (elements[id]) elements[id].value = value;
  const document = {
    getElementById: id => elements[id] || null,
    querySelector: selector => selector === '.research-tracker' ? root : null,
    createElement: tag => new Element(tag), createElementNS: (_, tag) => new Element(tag),
    createTextNode: value => new Text(value)
  };
  const fetch = async url => ({ ok: true, json: async () => String(url).includes('conference-history') ? history : snapshot });
  return { document, elements, fetch, catalog: publishedCatalog };
}
async function run(script, fixture, includeCore = false) {
  const context = { document: fixture.document, fetch: fixture.fetch, Intl, Date, URL, setTimeout };
  context.window = context;
  vm.createContext(context);
  if (includeCore) vm.runInContext(fs.readFileSync(path.join(repo, 'static/js/ai-research-observatory-core.js'), 'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(repo, script), 'utf8'), context);
  await new Promise(resolve => setImmediate(resolve));
}

async function main() {
  const destination = fs.mkdtempSync(path.join(os.tmpdir(), 'ai-research-task5-'));
  try {
    execFileSync('hugo', ['--destination', destination], { cwd: repo, stdio: 'pipe' });
    const trackerHtml = fs.readFileSync(path.join(destination, 'posts/ai-research-tracker/index.html'), 'utf8');
    const observatoryHtml = fs.readFileSync(path.join(destination, 'hodgepodge/ai-research-observatory/index.html'), 'utf8');
    for (const html of [trackerHtml, observatoryHtml]) {
      assert.match(html, /main-track/i);
      assert.match(html, /bibliography/i);
      assert.match(html, /observed AI/i);
    }
    assert.match(trackerHtml, /id="research-count-rows"/, 'organizer ledger stays separate');
    assert.match(trackerHtml, /OpenAlex source matches/);
    assert.match(trackerHtml, /Publisher index entries/);
    assert.match(observatoryHtml, /Standalone arXiv reports/, 'arXiv stays outside conference totals');

    const history = { reviewed_at: '2026-10-16', conferences: [{ id: 'neurips', name: 'NeurIPS', color: '#123456' }],
      counts: [{ venue: 'neurips', year: 2024, submitted: 12000, accepted: 3000, scope: 'main program', source: 'https://example.org/organizer' }], awards: [] };
    const rows = [
      { venue_id: 'pldi', venue: 'PLDI', year: 2022, status: 'verified', main_track_total: 100, bibliography_total: 100,
        ai_matched_count: 12, scanned_count: 100, eligible_count: 100, ai_scan_status: 'complete', track_scope: 'research papers', source_urls: ['https://example.org/official'] },
      { venue_id: 'pldi', venue: 'PLDI', year: 2023, status: 'unresolved', main_track_total: null, bibliography_total: null,
        ai_matched_count: null, track_scope: 'research papers', gap_reason: 'issue mapping unresolved' },
      { venue_id: 'pldi', venue: 'PLDI', year: 2024, status: 'verified', main_track_total: 120, bibliography_total: 120,
        ai_matched_count: 14, scanned_count: 120, eligible_count: 120, ai_scan_status: 'complete', track_scope: 'research papers', source_urls: ['https://example.org/official-2024'] },
      { venue_id: 'pldi', venue: 'PLDI', year: 2025, status: 'partial', main_track_total: null, bibliography_total: 130,
        ai_matched_count: 9, scanned_count: 130, eligible_count: 130, scanned: 25, ai_scan_status: 'complete',
        track_scope: 'research papers', source_urls: ['https://dblp.org/db/conf/pldi/'] }
    ];
    const snapshot = { generated_at: '2026-10-16T00:00:00Z', venues: catalog.filter(v => v.id === 'neurips'), coverage: rows, papers: [], scope: {} };
    const tracker = pageFixture(trackerHtml, snapshot, history);
    await run('static/js/ai-research-tracker.js', tracker);
    assert.equal(tracker.elements['research-index-venue'].children.filter(option => catalog.some(venue => venue.source_rule_id && venue.id === option.value)).length, 35,
      'Tracker venue selector exposes all new cross-area series');
    tracker.elements['research-index-venue'].value = 'pldi';
    tracker.elements['research-index-venue'].dispatch('change');
    const chart = tracker.elements['research-index-chart'];
    const verifiedLines = descendants(chart, el => el.tagName === 'line' && el.attributes.class?.includes('main-track'));
    assert.equal(verifiedLines.length, 0, 'unresolved year breaks the verified main-track line');
    const mainPoints = descendants(chart, el => el.tagName === 'circle' && el.attributes.class?.includes('main-track'));
    assert.equal(mainPoints.length, 2, 'only verified main-track values are plotted');
    assert.ok(mainPoints.every(point => !point.attributes['aria-label'].includes('2025')));
    const bibliography = descendants(chart, el => el.tagName === 'circle' && el.attributes.class?.includes('bibliography'));
    assert.equal(bibliography.length, 1, 'DBLP fallback is a separate bibliography observation');
    assert.match(bibliography[0].attributes['aria-label'], /bibliography/i);
    assert.match(mainPoints[0].attributes['aria-label'], /verified main-track/i);
    assert.match(tracker.elements['research-index-detail'].textContent, /2023.*unresolved/i);
    assert.match(tracker.elements['research-count-rows'].textContent, /12,000.*3,000.*Organizer/s);
    assert.match(tracker.elements['research-catalog-rows'].textContent, /PLDI/);

    const oldSnapshot = { ...snapshot, coverage: [], venues: snapshot.venues };
    const oldTracker = pageFixture(trackerHtml, oldSnapshot, history);
    await run('static/js/ai-research-tracker.js', oldTracker);
    oldTracker.elements['research-index-venue'].value = 'pldi'; oldTracker.elements['research-index-venue'].dispatch('change');
    assert.equal(descendants(oldTracker.elements['research-index-chart'], el => el.tagName === 'circle').length, 0, 'old snapshot creates no invented points');
    assert.match(oldTracker.elements['research-index-detail'].textContent, /not yet available/i);
    const legacySnapshot = { ...snapshot, coverage: [
      { venue_id: 'neurips', venue: 'NeurIPS', year: 2023, source_total: 280, scanned: 24,
        official_total: 480, official_sampled: 150, official_provider: 'NeurIPS proceedings', status: 'sample',
        source_id: 'https://openalex.org/S1', official_url: 'https://example.org/neurips/2023' },
      { venue_id: 'neurips', venue: 'NeurIPS', year: 2024, source_total: 300, scanned: 25,
        official_total: 500, official_sampled: 175, official_provider: 'NeurIPS proceedings', status: 'sample',
        source_id: 'https://openalex.org/S1', official_url: 'https://example.org/neurips/2024' }
    ] };
    const legacyTracker = pageFixture(trackerHtml, legacySnapshot, history);
    await run('static/js/ai-research-tracker.js', legacyTracker);
    assert.match(legacyTracker.elements['research-catalog-rows'].textContent, /NeurIPS.*legacy index/s,
      'legacy OpenAlex records are not collapsed into unknown availability');
    const legacyChart = legacyTracker.elements['research-index-chart'];
    const openalexPoints = descendants(legacyChart, el => el.tagName === 'circle' && el.attributes.class?.includes('legacy-openalex'));
    const publisherPoints = descendants(legacyChart, el => el.tagName === 'circle' && el.attributes.class?.includes('legacy-publisher'));
    assert.equal(openalexPoints.length, 2, 'default venue plots two published OpenAlex source-match years');
    assert.equal(publisherPoints.length, 2, 'default venue plots two published publisher-index years');
    assert.notEqual(openalexPoints[0].attributes.fill, publisherPoints[0].attributes.fill, 'legacy series have distinct colors');
    assert.match(openalexPoints[0].attributes['aria-label'], /OpenAlex source matches/i);
    assert.match(publisherPoints[0].attributes['aria-label'], /publisher index entries/i);
    assert.ok([...openalexPoints, ...publisherPoints].every(point => Number(point.attributes.cy) >= 18 && Number(point.attributes.cy) <= 267),
      'legacy series participate in the chart scale');
    assert.equal(descendants(legacyChart, el => el.tagName === 'circle' && el.attributes.class?.includes('main-track')).length, 0,
      'legacy index values never become verified main-track points');
    assert.match(legacyTracker.elements['research-index-detail'].textContent, /legacy index.*not organizer acceptances/i);
    assert.match(legacyTracker.elements['research-index-rows'].textContent, /OpenAlex source matches: 300.*publisher index entries: 500/s,
      'the source table retains both legacy totals for one year');

    const staleLegacySnapshot = { ...legacySnapshot, coverage: [legacySnapshot.coverage[0],
      { ...legacySnapshot.coverage[1], stale: true, last_successful_checked_at: '2026-10-01T00:00:00Z' }] };
    const staleLegacyTracker = pageFixture(trackerHtml, staleLegacySnapshot, history);
    await run('static/js/ai-research-tracker.js', staleLegacyTracker);
    staleLegacyTracker.elements['research-catalog-year'].value = '2024';
    staleLegacyTracker.elements['research-catalog-year'].dispatch('change');
    assert.match(staleLegacyTracker.elements['research-catalog-rows'].textContent, /NeurIPS.*stale/s);
    assert.doesNotMatch(staleLegacyTracker.elements['research-catalog-rows'].textContent, /publisher index: 500 entries/s,
      'a stale index total must not be presented as a current catalog count');
    assert.equal(descendants(staleLegacyTracker.elements['research-index-chart'], el => el.tagName === 'circle' && el.attributes['aria-label']?.includes('2024')).length, 0,
      'stale legacy index totals remain absent from plotted series');
    assert.match(staleLegacyTracker.elements['research-index-rows'].textContent,
      /OpenAlex source matches: 300 \(last known\).*publisher index entries: 500 \(last known\)/s,
      'retained source totals in the detailed ledger are explicitly last-known');

    const zeroIndexSnapshot = { ...snapshot, coverage: [
      { venue_id: 'neurips', venue: 'NeurIPS', year: 2020, source_total: 0,
        status: 'no-index-records', partial: true },
      { venue_id: 'neurips', venue: 'NeurIPS', year: 2026, source_total: 0,
        official_total: 4042, status: 'no-index-records', partial: true }
    ] };
    const zeroIndexTracker = pageFixture(trackerHtml, zeroIndexSnapshot, history);
    await run('static/js/ai-research-tracker.js', zeroIndexTracker);
    zeroIndexTracker.elements['research-catalog-year'].value = '2020';
    zeroIndexTracker.elements['research-catalog-year'].dispatch('change');
    assert.match(zeroIndexTracker.elements['research-catalog-rows'].textContent, /NeurIPS.*no-index-records/s,
      'zero OpenAlex source matches are a gap, not zero venue publications');
    zeroIndexTracker.elements['research-catalog-year'].value = '2026';
    zeroIndexTracker.elements['research-catalog-year'].dispatch('change');
    assert.match(zeroIndexTracker.elements['research-catalog-rows'].textContent,
      /NeurIPS.*publisher index: 4,042 entries; not verified main-track/s,
      'a publisher index is not hidden behind zero OpenAlex source matches');
    const zeroIndexChart = zeroIndexTracker.elements['research-index-chart'];
    assert.equal(descendants(zeroIndexChart, el => el.tagName === 'circle' && el.attributes.class?.includes('legacy-openalex')).length, 0,
      'zero OpenAlex matches do not become chart points');

    const observatory = pageFixture(observatoryHtml, snapshot, history);
    await run('static/js/ai-research-observatory.js', observatory, true);
    assert.equal(observatory.elements['aro-coverage-venue'].children.filter(option => catalog.some(venue => venue.source_rule_id && venue.id === option.value)).length, 35,
      'Observatory coverage selector exposes all new cross-area series');
    observatory.elements['aro-coverage-venue'].value = 'pldi'; observatory.elements['aro-coverage-venue'].dispatch('change');
    const coverageText = observatory.elements['aro-coverage'].textContent;
    assert.match(coverageText, /2023.*unresolved.*issue mapping unresolved/s);
    assert.match(coverageText, /2025.*bibliography.*130.*observed AI.*9.*130/s);
    assert.match(coverageText, /2025.*observed AI matches: 9 \/ 130 scanned eligible records.*25 OpenAlex sampled records.*not AI scan/s,
      'legacy OpenAlex sample size is not used as the AI classification denominator');
    assert.match(observatory.elements['aro-ranked-venues'].textContent, /PLDI/);
    assert.match(observatory.elements['aro-paper-count'].textContent, /^0$/, 'venue totals do not enter the AI paper ledger');
    const oldObservatory = pageFixture(observatoryHtml, oldSnapshot, history);
    await run('static/js/ai-research-observatory.js', oldObservatory, true);
    oldObservatory.elements['aro-coverage-venue'].value = 'pldi'; oldObservatory.elements['aro-coverage-venue'].dispatch('change');
    assert.match(oldObservatory.elements['aro-coverage'].textContent, /not yet available/i);
    const legacyObservatory = pageFixture(observatoryHtml, legacySnapshot, history);
    await run('static/js/ai-research-observatory.js', legacyObservatory, true);
    legacyObservatory.elements['aro-coverage-venue'].value = 'neurips'; legacyObservatory.elements['aro-coverage-venue'].dispatch('change');
    assert.match(legacyObservatory.elements['aro-ranked-venues'].textContent, /NeurIPS.*legacy index/s);
    assert.match(legacyObservatory.elements['aro-coverage'].textContent,
      /2024.*OpenAlex: 300 indexed matches.*25 OpenAlex sampled records.*index: 500 records.*175 publisher sampled records/s,
      'legacy sample sizes remain separately labelled from index totals and AI scans');
    console.log('Tracker and Observatory HTML/fixture checks passed.');
  } finally { fs.rmSync(destination, { recursive: true, force: true }); }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
