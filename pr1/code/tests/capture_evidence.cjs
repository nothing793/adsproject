// Capture actual browser renders of the evidence pages; no image synthesis.
// Set PLAYWRIGHT_MODULE to an installed Playwright path if it is not on NODE_PATH.
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '../..');
(async () => {
  const browser = await chromium.launch({channel: 'msedge', headless: true});
  const page = await browser.newPage({viewport: {width: 1440, height: 1000}, deviceScaleFactor: 1});
  const output = path.join(root, 'evidence/screenshots');
  fs.mkdirSync(output, {recursive: true});
  const records = [];
  for (let i = 1; i <= 8; i++) {
    const name = String(i).padStart(2, '0');
    const url = pathToFileURL(path.join(root, 'evidence/pages', name + '.html')).href;
    await page.goto(url, {waitUntil: 'load'});
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({path: path.join(output, name + '.png'), fullPage: true});
    records.push({screenshot: name + '.png', title: await page.title(), url,
                  capturedAt: new Date().toISOString(), browserVersion: browser.version()});
    process.stdout.write('Captured ' + name + '.png\n');
  }
  fs.writeFileSync(path.join(root, 'evidence/screenshot_capture.json'), JSON.stringify(records, null, 2));
  await browser.close();
})().catch(error => { process.stderr.write(String(error.stack)); process.exit(1); });
