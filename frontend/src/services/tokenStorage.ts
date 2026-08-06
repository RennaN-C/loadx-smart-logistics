const TOKEN_STORAGE_KEY = "loadx:auth:token";

function decodeBase64Url(segment: string): string {
  const base64 = segment.replace(/-/g, "+").replace(/_/g, "/");
  const padding = (4 - (base64.length % 4)) % 4;
  return atob(base64 + "=".repeat(padding));
}

// Confere apenas forma e expiração (3 segmentos + claim "exp" no futuro).
// O frontend não verifica a assinatura: quem garante a validade do token é o backend.
function isWellFormedJwt(token: string): boolean {
  const segments = token.split(".");

  if (segments.length !== 3) {
    return false;
  }

  try {
    const payload = JSON.parse(decodeBase64Url(segments[1])) as Record<string, unknown>;
    return typeof payload.exp === "number" && payload.exp * 1000 > Date.now();
  } catch {
    return false;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setToken(token: string): void {
  if (!isWellFormedJwt(token)) {
    throw new Error("Token recebido do servidor não é um JWT válido ou já está expirado.");
  }

  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}
