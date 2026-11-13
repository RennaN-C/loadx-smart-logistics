const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const path = require('node:path');
const data = file => 'data:image/png;base64,' + fs.readFileSync(file).toString('base64');
(async () => {
  if (!process.env.LOGIN_REFERENCE) throw new Error('Set LOGIN_REFERENCE to the approved PNG.');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1800, height: 550 }, deviceScaleFactor: 1 });
  for (const [name, first, label] of [
    ['comparison-reference.png', process.env.LOGIN_REFERENCE, 'Referência aprovada (conceito)'],
    ['comparison-before.png', path.join(__dirname, 'before-1600x900.png'), 'Antes: pentest-lab c4bd59e8'],
  ]) {
    await page.setContent(`<style>body{margin:0;background:#071725;color:#eaf1f8;font:16px system-ui;display:flex;gap:12px}figure{margin:0;width:894px}figcaption{padding:10px}img{width:100%;height:auto;display:block}</style><figure><figcaption>${label}</figcaption><img src="${data(first)}"></figure><figure><figcaption>Depois: Chromium real, HTML/SVG + cenário separado</figcaption><img src="${data(path.join(__dirname, 'login-1600x900.png'))}"></figure>`);
    await page.evaluate(() => Promise.all([...document.images].map(i => i.decode())));
    await page.screenshot({ path: path.join(__dirname, name), fullPage: true });
  }
  await browser.close();
})();
