const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const path = require('node:path');
const image = name => 'data:image/png;base64,' + fs.readFileSync(path.join(__dirname,name)).toString('base64');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1800,height: 550 } });
  for (const size of ['1366x768','1600x900','2560x1440']) {
    await page.setContent(`<style>body{margin:0;background:#071725;color:#eaf1f8;font:16px system-ui;display:flex;gap:12px}figure{margin:0;width:894px}figcaption{padding:10px}img{width:100%;height:auto;display:block}</style><figure><figcaption>Antes · pentest-lab 44eb90b2 · ${size}</figcaption><img src="${image('before-'+size+'.png')}"></figure><figure><figcaption>Depois · proporções compactas · ${size}</figcaption><img src="${image('after-'+size+'.png')}"></figure>`);
    await page.evaluate(() => Promise.all([...document.images].map(i => i.decode())));
    await page.screenshot({path:path.join(__dirname,'comparison-'+size+'.png'),fullPage:true});
  }
  await browser.close();
})();
