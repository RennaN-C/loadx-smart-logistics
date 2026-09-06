import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

const DEFAULT_API_URL = "/api/v1";
const DEFAULT_DEV_API_PROXY_TARGET = "http://localhost:8000";

function getApiOrigin(apiUrl: string): string | null {
  try {
    const parsedUrl = new URL(apiUrl);
    return ["http:", "https:"].includes(parsedUrl.protocol) ? parsedUrl.origin : null;
  } catch {
    return null;
  }
}

function createSecurityHeaders(
  apiUrl: string,
  { allowInlineScripts = false }: { allowInlineScripts?: boolean } = {},
): Record<string, string> {
  const connectSources = ["'self'", "ws://localhost:*", "ws://127.0.0.1:*"];
  const apiOrigin = getApiOrigin(apiUrl);
  if (apiOrigin) {
    connectSources.push(apiOrigin);
  }

  const contentSecurityPolicy = [
    "default-src 'self'",
    "base-uri 'self'",
    `connect-src ${connectSources.join(" ")}`,
    "font-src 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "img-src 'self' data: blob:",
    "object-src 'none'",
    // Em desenvolvimento o Vite injeta inline o preamble do React Fast Refresh.
    // Com `script-src 'self'` puro ele é bloqueado, o React não inicializa e
    // NENHUMA tela carrega. Produção (Caddy) e o preview do build servem apenas
    // scripts com hash de arquivo e seguem sem `'unsafe-inline'`.
    allowInlineScripts ? "script-src 'self' 'unsafe-inline'" : "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "worker-src 'self' blob:",
  ].join("; ");

  return {
    "Content-Security-Policy": contentSecurityPolicy,
    "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
  };
}

export function createDevApiProxyOptions(target: string, origin?: string) {
  return {
    target,
    ...(origin ? { headers: { Origin: origin } } : {}),
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiUrl = process.env.VITE_API_URL ?? env.VITE_API_URL ?? DEFAULT_API_URL;
  const devApiProxyTarget =
    process.env.DEV_API_PROXY_TARGET ??
    env.DEV_API_PROXY_TARGET ??
    DEFAULT_DEV_API_PROXY_TARGET;
  const devApiProxyOrigin =
    process.env.DEV_API_PROXY_ORIGIN ?? env.DEV_API_PROXY_ORIGIN;

  return {
    plugins: [react()],
    server: {
      // só o dev server precisa de inline; ver createSecurityHeaders
      headers: createSecurityHeaders(apiUrl, { allowInlineScripts: true }),
      proxy: {
        "/api": createDevApiProxyOptions(devApiProxyTarget, devApiProxyOrigin),
      },
      watch: {
        usePolling: true,
      },
    },
    preview: {
      headers: createSecurityHeaders(apiUrl),
    },
    build: {
      chunkSizeWarningLimit: 850,
    },
    test: {
      environment: "jsdom",
      setupFiles: ["./src/tests/setup.ts"],
    },
  };
});
