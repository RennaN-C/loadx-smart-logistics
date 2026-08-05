import { describe, expect, it } from "vitest";

import { toApiErrorResponse } from "./api";

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
