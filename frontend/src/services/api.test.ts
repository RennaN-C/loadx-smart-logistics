import { afterEach, describe, expect, it, vi } from "vitest";

import { notifyIfSessionInvalidated, setSessionInvalidatedHandler, toApiErrorResponse } from "./api";

function fakeAxiosError(overrides: { response?: unknown }): unknown {
  return { isAxiosError: true, ...overrides };
}

describe("toApiErrorResponse", () => {
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

    expect(toApiErrorResponse(error)).toEqual({
      code: "VALIDATION_ERROR",
      message: "Campo inválido.",
      details: [{ field: "email" }],
    });
  });

  it("retorna NETWORK_ERROR quando o erro do axios não tem resposta", () => {
    const error = fakeAxiosError({});

    expect(toApiErrorResponse(error).code).toBe("NETWORK_ERROR");
  });

  it("retorna UNKNOWN_ERROR para qualquer outro tipo de erro", () => {
    expect(toApiErrorResponse(new Error("algo inesperado")).code).toBe("UNKNOWN_ERROR");
  });
});

describe("notifyIfSessionInvalidated", () => {
  afterEach(() => {
    setSessionInvalidatedHandler(null);
  });

  it.each(["AUTH_INVALID_TOKEN", "AUTH_USER_INACTIVE"])(
    "aciona o handler para %s (sessão inválida)",
    (code) => {
      const handler = vi.fn();
      setSessionInvalidatedHandler(handler);

      notifyIfSessionInvalidated({ code, message: "x", details: [] });

      expect(handler).toHaveBeenCalledWith(code);
    },
  );

  it.each(["AUTH_INVALID_CREDENTIALS", "AUTH_FORBIDDEN"])(
    "não aciona o handler para %s (login errado ou sem permissão, sessão continua válida)",
    (code) => {
      const handler = vi.fn();
      setSessionInvalidatedHandler(handler);

      notifyIfSessionInvalidated({ code, message: "x", details: [] });

      expect(handler).not.toHaveBeenCalled();
    },
  );
});
