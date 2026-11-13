// Run from the repository root. PLAYWRIGHT_MODULE may point to an existing install.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const output = __dirname;
const base = process.env.LOGIN_URL || 'http://127.0.0.1:5174';
const report = { environment: 'Chromium; frontend real, API simulada; dados fictícios', viewports: [], flows: [], errors: [] };
const user = { id: '00000000-0000-4000-8000-000000000001', name: 'Pessoa de teste', email: 'login@example.test', role: 'ADMIN', active: true, created_at: '2026-11-12T12:00:00Z' };

async function mockApi(page) {
  const state = { mode: 'invalid', authenticated: false, verified: false, recovered: false, reset: false };
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const endpoint = new URL(request.url()).pathname.replace('/api/v1', '');
    const respond = (status, body) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
    const error = (code, message) => respond(401, { code, message, details: [] });
    if (endpoint === '/auth/me') return state.authenticated ? respond(200, user) : error('AUTH_INVALID_TOKEN', 'Sessão ausente.');
    if (endpoint === '/auth/login') {
      if (state.mode === 'invalid') return error('AUTH_INVALID_CREDENTIALS', 'Credenciais inválidas.');
      if (state.mode === 'mfa') return respond(200, { challenge_token: 'synthetic-browser-challenge', purpose: 'LOGIN', expires_at: new Date(Date.now() + 300000).toISOString(), trusted_device_days: 30 });
      state.authenticated = true;
      return respond(200, user);
    }
    if (endpoint === '/auth/mfa/verify') {
      const payload = request.postDataJSON();
      assert.equal(payload.trust_device, false);
      state.verified = true;
      state.authenticated = true;
      return respond(200, { user, recovery_codes: [] });
    }
    if (endpoint === '/auth/password-recovery') {
      state.recovered = true;
      return respond(202, {});
    }
    if (endpoint === '/auth/password-recovery/confirm') {
      state.reset = true;
      state.authenticated = false;
      return respond(200, {});
    }
    return respond(200, { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 });
  });
  page.on('pageerror', e => report.errors.push(e.message));
  return state;
}

async function ready(page) {
  await page.getByRole('heading', { name: 'Bem-vindo ao LoadX' }).waitFor();
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].map(image => image.decode().catch(() => {})));
  });
}

async function capture(page, filename) {
  await page.screenshot({ path: path.join(output, filename), fullPage: true });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  report.browser = browser.version();
  const sizes = [[1366,768], [1600,900], [1920,1080], [2560,1440], [820,1180], [375,667], [320,568]];
  for (const [width,height] of sizes) {
    const context = await browser.newContext({ viewport: { width, height }, colorScheme: width === 1920 ? 'light' : 'dark', reducedMotion: 'reduce' });
    const page = await context.newPage();
    await mockApi(page);
    await page.goto(base + '/login');
    await ready(page);
    const metrics = await page.evaluate(() => {
      const box = selector => { const {x,y,width,height} = document.querySelector(selector).getBoundingClientRect(); return {x,y,width,height}; };
      const image = document.querySelector('.login-scene-photo');
      return {
        viewport: { width: innerWidth, height: innerHeight },
        scrollWidth: document.documentElement.scrollWidth,
        card: box('.login-card'), heading: box('.login-brand-main h1'), scene: box('.login-scene-photo'),
        liveCopyVisible: getComputedStyle(document.querySelector('.login-brand-main')).display !== 'none',
        photo: { source: image.currentSrc.split('/').pop(), fit: getComputedStyle(image).objectFit, filter: getComputedStyle(image).filter },
        logo: document.querySelector('.login-access-mark').getAttribute('src'),
        formFont: getComputedStyle(document.querySelector('#email')).fontFamily,
      };
    });
    assert.ok(metrics.scrollWidth <= width, `Overflow at ${width}`);
    assert.ok(metrics.card.x >= 0 && metrics.card.x + metrics.card.width <= width + 1);
    assert.equal(metrics.photo.fit, 'cover');
    assert.equal(metrics.photo.filter, 'none');
    assert.ok(metrics.logo.endsWith('.svg'));
    if (width > 820) {
      assert.equal(metrics.liveCopyVisible, true);
      assert.ok(metrics.card.y + metrics.card.height <= height + 1);
      // Reference anchor proportions; tolerance allows the requested explanatory subtitle.
      assert.ok(Math.abs(metrics.heading.x / width - .053) < .01);
      assert.ok(Math.abs(metrics.card.x / width - .615) < .025);
      assert.ok(Math.abs(metrics.scene.y / height - .35) < .005);
    }
    report.viewports.push(metrics);
    await capture(page, `login-${width}x${height}.png`);
    await page.getByLabel('E-mail', { exact: true }).focus();
    assert.equal(await page.evaluate(() => getComputedStyle(document.activeElement).outlineStyle), 'solid');
    if (width === 375) {
      const password = page.getByLabel('Senha', { exact: true });
      await password.fill('senha-ficticia-visual');
      await page.getByRole('button', { name: 'Mostrar senha' }).click();
      assert.equal(await password.getAttribute('type'), 'text');
      await page.getByRole('button', { name: 'Ocultar senha' }).click();
      assert.equal(await password.inputValue(), 'senha-ficticia-visual');
    }
    await context.close();
  }

  const context = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  const page = await context.newPage();
  const state = await mockApi(page);
  await page.goto(base + '/login');
  await ready(page);
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  assert.equal(await page.locator('#email').evaluate(e => e.validity.valueMissing), true);
  report.flows.push('Validação nativa de campos obrigatórios');
  await page.getByLabel('E-mail', { exact: true }).fill(user.email);
  await page.getByLabel('Senha', { exact: true }).fill('senha-ficticia-de-teste');
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await page.getByRole('alert').waitFor();
  assert.match(await page.getByRole('alert').textContent(), /E-mail ou senha inválidos/);
  await capture(page, 'login-error-1366.png');
  report.flows.push('Erro de credenciais e formulário liberado para nova tentativa');

  await page.getByRole('link', { name: 'Esqueci minha senha' }).click();
  await page.getByRole('heading', { name: 'Esqueceu sua senha?' }).waitFor();
  await page.getByLabel('E-mail', { exact: true }).fill(user.email);
  await page.getByRole('button', { name: 'Solicitar recuperação' }).click();
  await page.getByText(/Se a conta for elegível/).waitFor();
  assert.equal(state.recovered, true);
  await capture(page, 'recovery-1366.png');
  report.flows.push('Recuperação: envio ao contrato existente e resposta neutra');

  await page.goto(base + '/password-reset#token=synthetic-reset-token');
  await page.getByLabel('Nova senha', { exact: true }).fill('senha-ficticia-para-redefinir');
  await page.getByLabel('Confirmar nova senha').fill('senha-ficticia-para-redefinir');
  assert.equal(new URL(page.url()).hash, '');
  await page.getByRole('button', { name: 'Redefinir senha' }).click();
  await page.getByText(/Senha redefinida/).waitFor();
  assert.equal(state.reset, true);
  report.flows.push('Redefinição: fragmento removido e confirmação sem autenticação automática');

  state.mode = 'mfa';
  await page.goto(base + '/customers');
  await ready(page);
  await page.getByLabel('E-mail', { exact: true }).fill(user.email);
  await page.getByLabel('Senha', { exact: true }).fill('senha-ficticia-de-teste');
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await page.getByRole('heading', { name: 'Verificação em duas etapas' }).waitFor();
  assert.equal(await page.getByRole('checkbox').isChecked(), false);
  await capture(page, 'mfa-1366.png');
  await page.getByLabel('Código do autenticador ou de recuperação').fill('123456');
  await page.getByRole('button', { name: 'Verificar e continuar' }).click();
  await page.waitForURL(url => url.pathname !== '/login');
  assert.equal(state.verified, true);
  report.flows.push('MFA: desafio em memória, opt-in desmarcado, verificação e redirecionamento');
  state.authenticated = false;
  state.mode = 'success';
  await page.goto(base + '/customers');
  await ready(page);
  await page.getByLabel('E-mail', { exact: true }).fill(user.email);
  await page.getByLabel('Senha', { exact: true }).fill('senha-ficticia-de-teste');
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await page.waitForURL(url => url.pathname === '/customers');
  report.flows.push('Login: retorno ao destino protegido solicitado');
  await context.close();

  if (process.env.BASELINE_URL) {
    const before = await browser.newPage({ viewport: { width: 1600, height: 900 } });
    await mockApi(before);
    await before.goto(process.env.BASELINE_URL + '/login');
    await ready(before);
    await capture(before, 'before-1600x900.png');
    await before.close();
  }
  assert.deepEqual(report.errors, []);
  fs.writeFileSync(path.join(output, 'browser-results.json'), JSON.stringify(report, null, 2) + '\n');
  await browser.close();
  console.log(`Passed: ${report.viewports.length} viewports, ${report.flows.length} flows, no uncaught page errors.`);
})().catch(error => { console.error(error); process.exit(1); });
