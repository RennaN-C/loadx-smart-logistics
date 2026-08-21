import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { clearCsrfToken, getCsrfToken, setCsrfToken } from "./csrfToken";

describe("csrfToken", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    clearCsrfToken();
  });

  it("mantém o token somente na memória do módulo", () => {
    setCsrfToken("csrf-da-sessao");

    expect(getCsrfToken()).toBe("csrf-da-sessao");
    expect(localStorage.length).toBe(0);
  });

  it("limpa o token ao encerrar ou invalidar a sessão", () => {
    setCsrfToken("csrf-da-sessao");

    clearCsrfToken();

    expect(getCsrfToken()).toBeNull();
  });
});
