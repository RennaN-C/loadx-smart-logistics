import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const config = JSON.parse(
  readFileSync(new URL("../vercel.json", import.meta.url), "utf8"),
);

assert.deepEqual(
  config.rewrites?.[0],
  {
    source: "/api/:path*",
    destination: "https://loadx-pentest-api.onrender.com/api/:path*",
  },
  "A API precisa ser encaminhada sob a mesma origem antes do fallback SPA.",
);
assert.deepEqual(
  config.rewrites?.at(-1),
  { source: "/:path*", destination: "/index.html" },
  "O fallback SPA precisa vir depois do proxy da API.",
);

const securityHeaders = config.headers?.flatMap((rule) => rule.headers ?? []) ?? [];
const csp = securityHeaders.find((header) => header.key === "Content-Security-Policy")?.value;
assert.ok(csp?.includes("connect-src 'self'"), "A política CSP deve preservar conexões de mesma origem.");
assert.ok(csp?.includes("script-src 'self'"), "A política CSP não pode permitir scripts arbitrários.");
assert.ok(
  securityHeaders.some((header) => header.key === "X-Content-Type-Options" && header.value === "nosniff"),
  "A proteção nosniff precisa permanecer ativa.",
);

const apiUrl = process.env.VITE_API_URL || "/api/v1";
assert.equal(
  apiUrl,
  "/api/v1",
  "VITE_API_URL deve ser /api/v1 para utilizar o proxy de mesma origem e cookies de sessão.",
);
console.log("Rotas Vercel, fallback SPA, CSP e URL da API validados.");
