// 使用现有 Edge 打印包含 LaTeX 矢量公式与语法高亮的报告；不截取公式位图。
const fs = require('fs');
const path = require('path');
const {pathToFileURL} = require('url');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async () => {
  const source = path.resolve(process.argv[2]);
  const destination = path.resolve(process.argv[3]);
  const options = {channel: 'msedge', headless: true};
  if (process.env.REPORT_PROXY) options.proxy = {server: process.env.REPORT_PROXY};
  const browser = await chromium.launch(options);
  try {
    const page = await browser.newPage({viewport: {width: 794, height: 1123}});
    await page.goto(pathToFileURL(source).href, {waitUntil: 'load', timeout: 90000});
    await page.waitForFunction(() => window.MathJax?.startup?.promise && window.hljs, null, {timeout: 90000});
    await page.evaluate(async () => {
      await MathJax.startup.promise;
      await MathJax.typesetPromise();
      hljs.highlightAll();
      await document.fonts.ready;
    });
    const statistics = await page.evaluate(() => ({
      formulas: document.querySelectorAll('mjx-container').length,
      displayFormulas: document.querySelectorAll('mjx-container[display="true"]').length,
      mathErrors: document.querySelectorAll('[data-mml-node="merror"]').length,
      highlightedBlocks: document.querySelectorAll('pre code.hljs').length,
      cKeywords: document.querySelectorAll('code.language-c .hljs-keyword').length,
      overflowing: [...document.querySelectorAll('mjx-container[display="true"] svg')].filter(x => x.getBoundingClientRect().width > document.body.getBoundingClientRect().width + 2).length
    }));
    if (!statistics.formulas || !statistics.displayFormulas || statistics.mathErrors || statistics.overflowing || !statistics.cKeywords) {
      throw new Error('公式或高亮校验失败: ' + JSON.stringify(statistics));
    }
    await page.emulateMedia({media: 'print'});
    await page.pdf({path: destination, format: 'A4', preferCSSPageSize: true, printBackground: true,
      displayHeaderFooter: true, headerTemplate: '<span></span>',
      footerTemplate: '<div style="width:100%;text-align:center;font:9px serif;color:#000"><span class="pageNumber"></span></div>'});
    // 保存已排版的 HTML，移除网络脚本；后续阅读无需重新加载 MathJax。
    await page.evaluate(() => document.querySelectorAll('script').forEach(x => x.remove()));
    fs.writeFileSync(source, await page.content(), 'utf8');
    console.log(JSON.stringify(statistics));
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error.message); process.exitCode = 1;});
