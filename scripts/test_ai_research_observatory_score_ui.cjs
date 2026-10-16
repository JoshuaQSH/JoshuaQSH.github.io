const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const snapshot = require('../static/data/ai-research-observatory.json');

const url = process.env.AI_OBSERVATORY_URL;
if (!url) throw new Error('Set AI_OBSERVATORY_URL to the Hugo Observatory page');
const viewportWidth = Number(process.env.AI_OBSERVATORY_VIEWPORT_WIDTH || 390);

const paper = { ...snapshot.papers[0], id: 'https://example.org/score-ui-fixture', title: 'Score UI fixture paper' };

async function main() {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: viewportWidth, height: 844 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/data/ai-research-observatory.json', route => route.fulfill({
      contentType: 'application/json', body: JSON.stringify({ ...snapshot, papers: [paper] })
    }));
    const response = await page.goto(url);
    assert.ok(response?.ok(), `Hugo page did not load: ${response?.status()}`);
    await page.locator('#aro-table-body button').first().waitFor();
    await page.locator('.aro-weights summary').click();

    await page.locator('#aro-search').fill('no matching score fixture paper');
    const panel = page.locator('.aro-weights');
    assert.match(await panel.innerText(), /score = 6 × sum\(weight × available component value\) \/ sum\(available weights\)/);
    assert.match(await panel.innerText(), /evidence coverage = sum\(available weights\) \/ sum\(selected weights\)/);
    assert.match(await panel.innerText(), /Minimum evidence: 2 available components and 55% coverage/);
    assert.match(await page.locator('#aro-weight-score').innerText(), /No paper matches these filters/);
    assert.equal(await page.locator('#aro-weight-score .aro-score-breakdown li').count(), 0);

    await page.locator('#aro-search').fill('');
    await page.locator('#aro-table-body button').first().waitFor();
    await page.evaluate(() => {
      for (const input of document.querySelectorAll('.aro-weight-grid input')) {
        input.value = '0';
        input.dispatchEvent(new Event('input', { bubbles: true }));
      }
    });
    assert.match(await page.locator('#aro-weight-score').innerText(), /Evidence coverage: no weights selected; ratio undefined/);
    assert.match(await page.locator('#aro-weight-score').innerText(), /No components selected/);
    await page.locator('#aro-table-body button').first().click();
    const detail = page.locator('#aro-detail');
    assert.equal(await detail.getAttribute('aria-labelledby'), 'aro-detail-title');
    assert.equal(await detail.locator('#aro-detail-title').innerText(), paper.title);
    const detailValue = label => detail.locator('dt').filter({ hasText: new RegExp(`^${label}$`) })
      .evaluate(element => element.nextElementSibling.textContent);
    assert.equal(await detailValue('Score'), 'No weights selected');
    assert.equal(await detailValue('Score availability'), 'No weights selected; evidence coverage undefined');
    assert.match(await detail.locator('.aro-score-explanation').innerText(), /Evidence coverage: no weights selected; ratio undefined/);
    assert.deepEqual(errors, []);
    assert.equal(await page.evaluate(() => document.body.scrollWidth <= innerWidth), true);
    console.log(`${viewportWidth}px: empty-filter method and zero-weight panel/dialog states passed.`);
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
