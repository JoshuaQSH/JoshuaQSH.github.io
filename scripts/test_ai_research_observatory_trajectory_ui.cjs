const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const snapshot = require('../static/data/ai-research-observatory.json');

const url = process.env.AI_OBSERVATORY_URL;
if (!url) throw new Error('Set AI_OBSERVATORY_URL to the Hugo Observatory page');

const papers = [
  [2024, 'Industry'], [2024, 'Industry'], [2024, 'University'],
  [2025, 'Industry'], [2025, 'University']
].map(([year, first_author_sector], index) => ({ ...snapshot.papers[0],
  id: `https://example.org/trajectory-${index}`, title: `Trajectory fixture ${index}`,
  venue_id: 'acl', venue: 'ACL', area: 'LLMs / NLP', year, first_author_sector }));
const coverage = [2024, 2025].map(year => ({ venue_id: 'acl', year, status: 'verified',
  ai_scan_status: 'complete', sampled_papers: papers.filter(paper => paper.year === year).length }));

async function main() {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1000, height: 844 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/data/ai-research-observatory.json', route => route.fulfill({
      contentType: 'application/json', body: JSON.stringify({ ...snapshot, papers, coverage })
    }));
    const response = await page.goto(url);
    assert.ok(response?.ok(), `Hugo page did not load: ${response?.status()}`);
    const points = page.locator('#aro-trend-chart circle[tabindex="0"]');
    assert.equal(await points.count(), 6, 'covered count values, including zero, are keyboard targets');
    assert.equal(await page.getByRole('img', { name: /2024 Industry: 2 tracked classified AI papers/ }).count(), 1);
    assert.match(await points.nth(4).getAttribute('aria-label'), /2024 Research Institute: 0 tracked classified AI papers/);
    await page.locator('#aro-trend-mode').focus();
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement?.tagName.toLowerCase()), 'circle');
    assert.match(await page.evaluate(() => document.activeElement?.getAttribute('aria-label')), /2024 Industry: 2 tracked/);
    await page.keyboard.press('Tab');
    assert.match(await page.evaluate(() => document.activeElement?.getAttribute('aria-label')), /2025 Industry: 1 tracked/);

    await page.locator('#aro-trend-mode').selectOption('growth');
    const growthPoints = page.locator('#aro-trend-chart circle[tabindex="0"]');
    assert.match(await growthPoints.first().getAttribute('aria-label'), /2025 Industry: -50% year-over-year growth/);
    assert.match(await growthPoints.nth(1).getAttribute('aria-label'), /2025 University: 0% year-over-year growth/);
    assert.deepEqual(errors, []);
    console.log('Trajectory keyboard and signed/zero value labels passed.');
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
