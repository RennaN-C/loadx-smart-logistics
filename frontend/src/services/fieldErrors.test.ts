import { describe, expect, it } from "vitest";

import { ApiError } from "../types/api";
import { fieldErrorsFromApiError } from "./fieldErrors";

function validationError(details: unknown[]) {
  return new ApiError("VALIDATION_ERROR", "Os dados informados são inválidos.", details);
}

describe("fieldErrorsFromApiError", () => {
  it("separa por campo e tira o prefixo que o Pydantic acrescenta", () => {
    const erros = fieldErrorsFromApiError(
      validationError([
        { field: "document", message: "Value error, Informe um CPF válido.", type: "value_error" },
      ]),
    );

    expect(erros).toEqual({ document: "Informe um CPF válido." });
  });

  it("não joga mensagem em inglês na tela", () => {
    // `string_too_long` é restrição nativa do Pydantic e responde em inglês.
    const erros = fieldErrorsFromApiError(
      validationError([
        { field: "name", message: "String should have at most 160 characters", type: "string_too_long" },
      ]),
    );

    expect(erros.name).toBe("Valor inválido para este campo.");
  });

  it("fica com o primeiro erro de cada campo", () => {
    const erros = fieldErrorsFromApiError(
      validationError([
        { field: "phone", message: "Value error, O DDD não pode começar com zero.", type: "value_error" },
        { field: "phone", message: "Value error, outro problema.", type: "value_error" },
      ]),
    );

    expect(erros.phone).toBe("O DDD não pode começar com zero.");
  });

  it("ignora erro que não é de validação, para a faixa geral assumir", () => {
    expect(fieldErrorsFromApiError(new ApiError("AUTH_FORBIDDEN", "Acesso negado."))).toEqual({});
  });

  it("aguenta details fora do formato sem quebrar a tela", () => {
    expect(fieldErrorsFromApiError(validationError([null, "x", { field: "" }]))).toEqual({});
  });
});
