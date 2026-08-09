import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

const DEFAULT_API_URL = "http://localhost:8000/api/v1";

function getApiOrigin(apiUrl: string): string | null {
  try {
    const parsedUrl = new URL(apiUrl);
    return ["http:", "https:"].includes(parsedUrl.protocol) ? parsedUrl.origin : null;
  } catch {
    return null;
  }
}

function createSecurityHeaders(apiUrl: string): Record<string, string> {
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
    "script-src 'self'",
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

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiUrl = process.env.VITE_API_URL ?? env.VITE_API_URL ?? DEFAULT_API_URL;
  const securityHeaders = createSecurityHeaders(apiUrl);

  return {
    plugins: [react()],
    server: {
      headers: securityHeaders,
      watch: {
        usePolling: true,
      },
    },
    preview: {
      headers: securityHeaders,
    },
    test: {
      environment: "jsdom",
      setupFiles: ["./src/tests/setup.ts"],
    },
  };
});
