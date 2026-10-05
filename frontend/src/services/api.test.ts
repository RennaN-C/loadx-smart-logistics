import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../types/api";
import {
  api,
  notifyIfSessionInvalidated,
  setSessionInvalidatedHandler,
  toApiError,
} from "./api";
import { clearCsrfToken, getCsrfToken, setCsrfToken } from "./csrfToken";

function fakeAxiosError(overrides: { response?: unknown }): unknown {
  return { isAxiosError: true, ...overrides };
}

describe("toApiError", () => {
  it("repassa o corpo de erro quando já está no formato da API", () => {
    const error = fakeAxiosError({
      response: {
        data: {
          code: "VALIDATION_ERROR",
          message: "Campo inválido.",
          details: [{ field: "email" }],
        },
      },
    });

    const result = toApiError(error);

    expect(result).toBeInstanceOf(ApiError);
    expect(result).toBeInstanceOf(Error);
    expect(result.code).toBe("VALIDATION_ERROR");
    expect(result.message).toBe("Campo inválido.");
    expect(result.details).toEqual([{ field: "email" }]);
  });

  it("retorna NETWORK_ERROR quando o erro do axios não tem resposta", () => {
    const error = fakeAxiosError({});

    expect(toApiError(error).code).toBe("NETWORK_ERROR");
  });

  it("retorna UNKNOWN_ERROR para qualquer outro tipo de erro", () => {
    expect(toApiError(new Error("algo inesperado")).code).toBe("UNKNOWN_ERROR");
  });

  it("guarda o status mesmo quando o corpo NÃO está no formato da API", () => {
    // Um 404 do próprio FastAPI responde {"detail": "Not Found"}, fora do
    // envelope. Sem o status, a feature não teria como distinguir rota ausente
    // de erro interno — os dois chegariam como UNKNOWN_ERROR.
    const error = fakeAxiosError({ response: { status: 404, data: { detail: "Not Found" } } });

    const result = toApiError(error);

    expect(result.code).toBe("UNKNOWN_ERROR");
    expect(result.status).toBe(404);
  });

  it("guarda o status também quando o corpo está no formato da API", () => {
    const error = fakeAxiosError({
      response: { status: 403, data: { code: "AUTH_FORBIDDEN", message: "Negado.", details: [] } },
    });

    expect(toApiError(error).status).toBe(403);
  });

  it("falha de rede fica sem status: não houve resposta para ter um", () => {
    expect(toApiError(fakeAxiosError({})).status).toBeUndefined();
  });
});

describe("notifyIfSessionInvalidated", () => {
  afterEach(() => {
    setSessionInvalidatedHandler(null);
    clearCsrfToken();
  });

  it.each(["AUTH_INVALID_TOKEN", "AUTH_USER_INACTIVE"])(
    "aciona o handler para %s (sessão inválida)",
    (code) => {
      const handler = vi.fn();
      setSessionInvalidatedHandler(handler);

      notifyIfSessionInvalidated(new ApiError(code, "x"));

      expect(handler).toHaveBeenCalledWith(code);
    },
  );

  it.each(["AUTH_INVALID_CREDENTIALS", "AUTH_FORBIDDEN"])(
    "não aciona o handler para %s (login errado ou sem permissão, sessão continua válida)",
    (code) => {
      const handler = vi.fn();
      setSessionInvalidatedHandler(handler);

      notifyIfSessionInvalidated(new ApiError(code, "x"));

      expect(handler).not.toHaveBeenCalled();
    },
  );
});

describe("cookie session and CSRF", () => {
  afterEach(() => {
    clearCsrfToken();
  });

  it("envia cookies em todas as chamadas", () => {
    expect(api.defaults.withCredentials).toBe(true);
  });

  it("anexa X-CSRF-Token somente em métodos inseguros", async () => {
    setCsrfToken("csrf-da-sessao");
    let patchHeader: unknown;
    let getHeader: unknown;

    await api.request({
      method: "patch",
      url: "/resource",
      adapter: async (config) => {
        patchHeader = config.headers.get("X-CSRF-Token");
        return { data: {}, status: 200, statusText: "OK", headers: {}, config };
      },
    });
    await api.request({
      method: "get",
      url: "/resource",
      adapter: async (config) => {
        getHeader = config.headers.get("X-CSRF-Token");
        return { data: {}, status: 200, statusText: "OK", headers: {}, config };
      },
    });

    expect(patchHeader).toBe("csrf-da-sessao");
    expect(getHeader).toBeUndefined();
  });

  it("captura o CSRF devolvido pelo login ou /auth/me", async () => {
    await api.request({
      method: "get",
      url: "/auth/me",
      adapter: async (config) => ({
        data: {},
        status: 200,
        statusText: "OK",
        headers: { "x-csrf-token": "csrf-restaurado" },
        config,
      }),
    });

    expect(getCsrfToken()).toBe("csrf-restaurado");
  });
});
