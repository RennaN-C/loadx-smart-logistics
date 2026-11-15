/*
 * Frontend-only WebGL E2E with synthetic API responses, never a backend/auth test.
 * Run against an isolated Vite/build preview, never the shared development server.
 * PLAYWRIGHT_MODULE_PATH may point at a separately installed QA tool directory.
 * node qa/browser/planner-professional.cjs --url http://127.0.0.1:5187 --phase before
 * node qa/browser/planner-professional.cjs --url http://127.0.0.1:5187 --phase after
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || "playwright");
const { createPlannerFixtures } = require("./plannerFixtures.cjs");

const option = (name, fallback) => {
  const index = process.argv.indexOf(name);
  return index < 0 ? fallback : process.argv[index + 1];
};
const baseUrl = option("--url", "http://127.0.0.1:5187");
const phase = option("--phase", "after");
const out = path.resolve(option("--out", `.tmp/planner-professional/${phase}`));
fs.mkdirSync(out, { recursive: true });
assert(["before", "after"].includes(phase));
const target = new URL(baseUrl);
assert(["http:", "https:"].includes(target.protocol));
const results = [];

async function createContext(browser, { width = 1600, theme = "dark", role = "CHECKER", empty = false, singleTruck = false, failVisualization = false } = {}) {
  const fixture = createPlannerFixtures({ empty, singleTruck });
  const context = await browser.newContext({
    viewport: { width, height: width < 600 ? 900 : 1000 },
    colorScheme: theme, reducedMotion: "reduce",
  });
  await context.addInitScript(() => {
    window.__plannerQa = { draws: 0, contextLosses: 0 };
    for (const kind of [window.WebGLRenderingContext, window.WebGL2RenderingContext]) {
      if (!kind) continue;
      for (const name of ["drawElements", "drawArrays", "drawElementsInstanced", "drawArraysInstanced"]) {
        const original = kind.prototype[name];
        if (!original) continue;
        kind.prototype[name] = function (...args) {
          window.__plannerQa.draws += 1;
          return original.apply(this, args);
        };
      }
    }
    document.addEventListener("webglcontextlost", () => { window.__plannerQa.contextLosses += 1; }, true);
  });
  const requests = [];
  const unknown = [];
  let visualizationBlocked = failVisualization;
  await context.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname.replace("/api/v1", "");
    requests.push({ method: request.method(), pathname });
    assert.equal(request.method(), "GET", `Visual inspection must never mutate API: ${pathname}`);
    let data;
    let status = 200;
    if (pathname === "/auth/me") data = { id: fixture.id(1), name: "Conta fictícia de inspeção", email: "qa@example.test", role, active: true, created_at: fixture.date };
    else if (pathname === `/load-distributions/${fixture.distribution.id}`) data = fixture.distribution;
    else if (/^\/load-plans\/[^/]+\/visualization$/.test(pathname)) {
      if (visualizationBlocked) {
        status = 503;
        data = { code: "SERVICE_UNAVAILABLE", message: "Indisponibilidade fictícia", details: [] };
      } else data = fixture.parts.find((part) => pathname.includes(part.load_plan.id))?.visualization;
    } else if (/^\/load-plans\/[^/]+\/continuity$/.test(pathname)) data = { loading_session: null, trip: null, operational_ready: false };
    else if (pathname === "/notifications/unread-count") data = { unread_count: 0 };
    else if (pathname === "/notifications") data = { items: [], total: 0, page: 1, page_size: 20, total_pages: 0, unread_count: 0 };
    else if (pathname === "/notifications/preferences") data = { items: [] };
    else if (pathname === "/company-profile") { status = 404; data = { code: "COMPANY_PROFILE_NOT_FOUND", message: "Cadastro fictício ausente", details: [] }; }
    else { unknown.push(pathname); status = 404; data = { code: "NOT_FOUND", message: "Fixture não definida", details: [] }; }
    await route.fulfill({ status, json: data, headers: { "X-CSRF-Token": "qa-fixture-only" } });
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  return { context, page, fixture, requests, errors, unknown, width, theme,
    recoverVisualization() { visualizationBlocked = false; } };
}

async function waitForScene(page) {
  const canvas = page.locator(".viewer canvas");
  await canvas.waitFor({ state: "visible", timeout: 45000 });
  await page.waitForFunction(() => window.__plannerQa.draws > 0, null, { timeout: 45000 });
  await page.waitForTimeout(650);
  return canvas;
}

async function record(state, name) {
  const { page, width, theme, errors, unknown, requests } = state;
  assert.deepEqual(errors, [], "Unhandled browser errors");
  assert.deepEqual(unknown, [], "Unexpected API calls require explicit fixture coverage");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  assert.equal(overflow, false, "Viewport must not scroll horizontally");
  const webgl = await page.locator(".viewer canvas").evaluate((canvas) => {
    const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
    return { width: canvas.width, height: canvas.height, version: gl?.getParameter(gl.VERSION), draws: window.__plannerQa.draws, contextLosses: window.__plannerQa.contextLosses };
  });
  assert(webgl.width > 0 && webgl.height > 0 && webgl.version, "Real WebGL scene must render");
  assert.equal(webgl.contextLosses, 0);
  await page.waitForTimeout(900);
  const idleBefore = await page.evaluate(() => window.__plannerQa.draws);
  await page.waitForTimeout(250);
  const idleDrawCalls = (await page.evaluate(() => window.__plannerQa.draws)) - idleBefore;
  if (phase === "after") assert.equal(idleDrawCalls, 0, "An idle scene must not keep drawing frames");
  const filename = `${name}-${theme}-${width}.png`;
  await page.screenshot({ path: path.join(out, filename), fullPage: true });
  results.push({ name, width, theme, overflow, webgl, idleDrawCalls, requests: requests.length, screenshot: filename });
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  try {
    for (const theme of ["dark", "light"]) for (const width of [1600, 375]) {
      const state = await createContext(browser, { theme, width });
      const { page, fixture } = state;
      await page.goto(`${baseUrl}/planning/distributions/${fixture.distribution.id}`);
      await waitForScene(page);
      await record(state, "multi-vehicle");
      const vehicleSelect = page.getByLabel("Caminhão para visualizar", { exact: true });
      if (await vehicleSelect.isVisible()) await vehicleSelect.selectOption(fixture.parts[1].id);
      else await page.getByRole("button", { name: /Caminhão 2/ }).click();
      await page.getByRole("heading", { name: "Carga de TST2B45" }).waitFor();
      await waitForScene(page);
      assert.equal(new URL(page.url()).searchParams.get("part"), fixture.parts[1].id);
      await record(state, "second-vehicle");
      assert.equal(await page.getByRole("button", { name: "Aprovar distribuição completa" }).count(), 0);
      if (phase === "after") {
        const select = page.getByLabel("Selecionar volume", { exact: true });
        await select.selectOption(fixture.parts[1].visualization.items[37].id);
        await page.locator(".viewer-detail").getByText("CX-2-038", { exact: true }).waitFor();
        await page.getByRole("button", { name: "Frontal", exact: true }).click();
        await page.getByRole("button", { name: "Centralizar câmera", exact: true }).click();
        await record(state, "selected-front");
        await page.getByRole("button", { name: "Limpar seleção", exact: true }).click();
        assert.equal(await select.inputValue(), "");
        await page.getByRole("button", { name: "Expandir visualização 3D" }).click();
        await page.getByRole("dialog", { name: "Visualização 3D da carga" }).waitFor();
        await record(state, "expanded");
        await page.keyboard.press("Escape");
        assert.equal(await page.getByRole("dialog").count(), 0);
      }
      await state.context.close();
    }
    if (phase === "after") {
      const full = await createContext(browser, { singleTruck: true });
      await full.page.goto(`${baseUrl}/planning/distributions/${full.fixture.distribution.id}`);
      await waitForScene(full.page);
      assert.equal(await full.page.getByLabel("Selecionar volume", { exact: true }).locator("option").count(), 201);
      await full.page.getByLabel("Selecionar volume", { exact: true }).selectOption(full.fixture.parts[0].visualization.items[199].id);
      await full.page.locator(".viewer-detail").getByText("CX-1-200", { exact: true }).waitFor();
      await record(full, "200-volumes");
      await full.context.close();

      const empty = await createContext(browser, { empty: true });
      await empty.page.goto(`${baseUrl}/planning/distributions/${empty.fixture.distribution.id}`);
      await empty.page.getByText(/Nenhum volume foi carregado/).waitFor();
      assert.equal(await empty.page.locator(".viewer canvas").count(), 0);
      await empty.context.close();

      const retry = await createContext(browser, { failVisualization: true });
      await retry.page.goto(`${baseUrl}/planning/distributions/${retry.fixture.distribution.id}`);
      const retryButton = retry.page.getByRole("button", { name: "Tentar carregar visualização novamente" });
      await retryButton.waitFor();
      const initialRequests = retry.requests.filter((request) => request.pathname.endsWith("/visualization")).length;
      retry.recoverVisualization();
      await retryButton.click();
      await waitForScene(retry.page);
      assert.equal(retry.requests.filter((request) => request.pathname.endsWith("/visualization")).length, initialRequests + 1);
      await record(retry, "retry-recovered");
      await retry.context.close();

      const denied = await createContext(browser, { role: "DRIVER" });
      await denied.page.goto(`${baseUrl}/planning/distributions/${denied.fixture.distribution.id}`);
      await denied.page.waitForTimeout(350);
      assert.equal(denied.requests.some((request) => request.pathname.startsWith("/load-distributions/")), false);
      assert.equal(await denied.page.locator(".viewer canvas").count(), 0);
      await denied.context.close();
      results.push({ name: "empty-error-retry-and-read-only-permissions", passed: true });
    }
    fs.writeFileSync(path.join(out, "results.json"), JSON.stringify({ phase, source: "Real frontend/WebGL; synthetic GET-only browser API fixtures. Does not prove backend authorization or optimizer correctness.", results }, null, 2));
    console.log(JSON.stringify({ phase, checks: results.length, output: out }));
  } finally { await browser.close(); }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
