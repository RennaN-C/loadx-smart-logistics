const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const digest = buffer => crypto.createHash('sha256').update(buffer).digest('hex');
const directory = __dirname;
const sizes = [[1366,768], [1600,900], [1920,1080], [2560,1440], [375,667]];

async function ready(page) {
  await page.mouse.move(0,0);
  await page.waitForLoadState('networkidle');
  await page.evaluate(async () => {
    await Promise.all([400,500,600,700].map(weight => document.fonts.load(`${weight} 16px Poppins`)));
    await document.fonts.ready;
    await Promise.all([...document.images].map(i => i.decode().catch(() => {})));
  });
}

async function mock(page) {
  await page.route('**/api/v1/**', route => {
    if (new URL(route.request().url()).pathname.endsWith('/auth/login')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ challenge_token: 'synthetic-visual-challenge', purpose: 'LOGIN', expires_at: '2099-01-01T00:00:00Z', trusted_device_days: 30 }) });
    }
    return route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ code: 'AUTH_INVALID_TOKEN', message: 'Sessão ausente.', details: [] }) });
  });
}

async function metrics(page) {
  return page.evaluate(() => {
    const box = selector => {
      const { x,y,width,height } = document.querySelector(selector).getBoundingClientRect();
      return { x,y,width,height };
    };
    const css = selector => {
      const style = getComputedStyle(document.querySelector(selector));
      return Object.fromEntries(['fontSize','lineHeight','padding','gap','borderRadius','minHeight'].map(name => [name,style[name]]));
    };
    return { card: box('.login-card'), column: box('.login-formside'), title: css('.login-card h2'), input: css('.login-card input'), submit: css('.login-card button[type="submit"]'), overflow: document.documentElement.scrollWidth > innerWidth };
  });
}

(async () => {
  const browser = await chromium.launch();
  const report = { browser: browser.version(), baseCommit: '44eb90b2', api: 'simulada, dados fictícios', comparisons: [], identity: [], errors: [] };
  for (const [width,height] of sizes) {
    const pair = {};
    for (const [phase,url] of [['before',process.env.BASELINE_URL || 'http://127.0.0.1:5175'], ['after',process.env.LOGIN_URL || 'http://127.0.0.1:5174']]) {
      const page = await browser.newPage({ viewport: { width,height }, colorScheme: 'dark', reducedMotion: 'reduce' });
      page.on('pageerror', e => report.errors.push(e.message));
      await mock(page);
      await page.goto(url + '/login');
      await page.getByRole('heading', { name: 'Bem-vindo ao LoadX' }).waitFor();
      await ready(page);
      const screenshot = await page.screenshot({ path: path.join(directory, `${phase}-${width}x${height}.png`), fullPage: true });
      // Exclude the right card's soft shadow, which spills across the column seam.
      const hideRight = await page.addStyleTag({ content: '.login-formside { visibility: hidden; }' });
      const leftHash = digest(await page.locator('.login-brand').screenshot());
      await hideRight.evaluate(e => e.remove());
      pair[phase] = { ...await metrics(page), leftHash, screenshotHash: digest(screenshot) };
      assert.equal(pair[phase].overflow, false);
      if (phase === 'after') {
        await page.getByLabel('E-mail', { exact: true }).focus();
        assert.equal(await page.evaluate(() => getComputedStyle(document.activeElement).outlineStyle), 'solid');
        await page.getByLabel('Senha', { exact: true }).fill('senha-ficticia-visual');
        await page.getByRole('button', { name: 'Mostrar senha' }).click();
        assert.equal(await page.locator('#password').getAttribute('type'), 'text');
        await page.getByRole('button', { name: 'Ocultar senha' }).click();
        assert.equal(await page.locator('#password').inputValue(), 'senha-ficticia-visual');
      }
      await page.close();
    }
    assert.equal(pair.before.leftHash, pair.after.leftHash, `Left panel changed at ${width}`);
    if (width > 820) {
      const card = pair.after.card;
      const column = pair.after.column;
      assert.ok(card.width <= 510 && card.width >= 450, `Card width at ${width}`);
      assert.ok(card.height < pair.before.card.height, `Card should shrink at ${width}`);
      assert.ok(card.height < height && card.y >= 0, `Notebook fit at ${width}`);
      assert.ok(Math.abs(card.x + card.width/2 - column.x - column.width/2) < 1, 'Horizontal centering');
      assert.ok(Math.abs(card.y + card.height/2 - height/2) < 1, 'Vertical centering');
      assert.ok(parseFloat(pair.after.title.fontSize) >= 28 && parseFloat(pair.after.title.fontSize) <= 34);
      assert.ok(parseFloat(pair.after.input.minHeight) >= 50);
      assert.ok(parseFloat(pair.after.submit.minHeight) >= 52);
    } else {
      assert.equal(pair.before.screenshotHash, pair.after.screenshotHash, 'Mobile screenshot must stay identical');
    }
    report.comparisons.push({ viewport: {width,height}, ...pair });
  }

  for (const width of [1366,1920]) {
    for (const flow of ['recovery','mfa']) {
      const pair = {};
      for (const [phase,url] of [['before',process.env.BASELINE_URL || 'http://127.0.0.1:5175'], ['after',process.env.LOGIN_URL || 'http://127.0.0.1:5174']]) {
        const page = await browser.newPage({ viewport: { width,height: 1080 }, colorScheme: 'dark', reducedMotion: 'reduce' });
        page.on('pageerror', e => report.errors.push(e.message));
        await mock(page);
        await page.goto(url + (flow === 'recovery' ? '/password-recovery' : '/login'));
        if (flow === 'mfa') {
          await page.getByRole('heading', { name: 'Bem-vindo ao LoadX' }).waitFor();
          await page.getByLabel('E-mail', { exact: true }).fill('visual@example.test');
          await page.getByLabel('Senha', { exact: true }).fill('senha-ficticia-visual');
          await page.getByRole('button', { name: 'Entrar', exact: true }).click();
        }
        await page.getByRole('heading', { name: flow === 'recovery' ? 'Esqueceu sua senha?' : 'Verificação em duas etapas' }).waitFor();
        await ready(page);
        await page.screenshot({path:path.join(directory,`${phase}-${flow}-${width}.png`),fullPage:true});
        pair[phase] = { ...await metrics(page), cardHash: digest(await page.locator('.identity-card').screenshot()) };
        await page.close();
      }
      assert.deepEqual(pair.after, pair.before, `${flow} appearance changed at ${width}`);
      report.identity.push({ width,flow, unchanged: true, ...pair });
    }
  }
  assert.deepEqual(report.errors, []);
  fs.writeFileSync(path.join(directory,'results.json'),JSON.stringify(report,null,2)+'\n');
  await browser.close();
  console.log('Passed: five sizes; left panel/mobile identical; recovery and MFA identical at 1366/1920; focus and password toggle preserved.');
})().catch(e => { console.error(e); process.exit(1); });
