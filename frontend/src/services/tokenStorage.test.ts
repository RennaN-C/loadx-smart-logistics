import { afterEach, describe, expect, it } from "vitest";

import { clearToken, getToken, setToken } from "./tokenStorage";

function base64Url(value: unknown): string {
  return btoa(JSON.stringify(value)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function makeJwt(expiresInSeconds: number): string {
  const header = base64Url({ alg: "HS256", typ: "JWT" });
  const payload = base64Url({ sub: "user-1", exp: Math.floor(Date.now() / 1000) + expiresInSeconds });
  return `${header}.${payload}.fake-signature`;
}

describe("tokenStorage", () => {
  afterEach(() => {
    clearToken();
  });

  it("armazena um JWT bem formado e ainda válido", () => {
    const token = makeJwt(3600);

    setToken(token);

    expect(getToken()).toBe(token);
  });

  it("rejeita com um Error uma string que não tem o formato de JWT", () => {
    expect(() => setToken("nao-eh-um-token")).toThrow(Error);
    expect(getToken()).toBeNull();
  });

  it("rejeita com um Error um token já expirado", () => {
    const expiredToken = makeJwt(-60);

    expect(() => setToken(expiredToken)).toThrow(Error);
    expect(getToken()).toBeNull();
  });

  it("clearToken remove o token armazenado", () => {
    setToken(makeJwt(3600));

    clearToken();

    expect(getToken()).toBeNull();
  });
});
