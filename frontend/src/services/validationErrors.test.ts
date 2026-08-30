import { describe, expect, it } from "vitest";

import { ApiError } from "../types/api";
import { validationMessage } from "./validationErrors";

const LABELS = {
  delivery_address: "Endereço de entrega",
  expected_delivery_at: "Previsão de entrega",
  "items.quantity": "Quantidade",
  "items.product_id": "Produto",
  priority: "Prioridade",
};

function validation(...details: { field: string; message: string; type: string }[]) {
  return new ApiError("VALIDATION_ERROR", "Os dados informados são inválidos.", details);
}

describe("validationMessage", () => {
  it("nomeia o campo em vez de dizer só que os dados são inválidos", () => {
    const message = validationMessage(
      validation({ field: "delivery_address", message: "Field required", type: "missing" }),
      LABELS,
    );

    expect(message).toBe("Endereço de entrega precisa ser preenchido.");
  });

  it("lê o limite numérico, que só existe na mensagem em inglês do Pydantic", () => {
    const message = validationMessage(
      validation({
        field: "items.0.quantity",
        message: "Input should be greater than 0",
        type: "greater_than",
      }),
      LABELS,
    );

    expect(message).toBe("Quantidade (item 1) precisa ser maior que 0.");
  });

  it("aponta a posição do item na lista", () => {
    const message = validationMessage(
      validation({ field: "items.2.product_id", message: "Field required", type: "missing" }),
      LABELS,
    );

    // índice 2 no backend é o terceiro item na tela
    expect(message).toBe("Produto (item 3) precisa ser preenchido.");
  });

  it("junta vários problemas numa lista legível", () => {
    const message = validationMessage(
      validation(
        { field: "delivery_address", message: "Field required", type: "missing" },
        { field: "items.0.quantity", message: "Input should be greater than 0", type: "greater_than" },
      ),
      LABELS,
    );

    expect(message).toBe(
      "Corrija 2 campos: Endereço de entrega precisa ser preenchido; Quantidade (item 1) precisa ser maior que 0.",
    );
  });

  it("resume quando são muitos, para não virar parede de texto", () => {
    const message = validationMessage(
      validation(
        { field: "a", message: "", type: "missing" },
        { field: "b", message: "", type: "missing" },
        { field: "c", message: "", type: "missing" },
        { field: "d", message: "", type: "missing" },
        { field: "e", message: "", type: "missing" },
      ),
      LABELS,
    );

    expect(message).toContain("Corrija 5 campos:");
    expect(message).toContain("e mais 2.");
  });

  it("não repete o mesmo problema duas vezes", () => {
    const message = validationMessage(
      validation(
        { field: "priority", message: "Field required", type: "missing" },
        { field: "priority", message: "Field required", type: "missing" },
      ),
      LABELS,
    );

    expect(message).toBe("Prioridade precisa ser preenchido.");
  });

  it("usa o nome cru do campo quando não há rótulo, que ainda é melhor que nada", () => {
    const message = validationMessage(
      validation({ field: "campo_novo", message: "Field required", type: "missing" }),
      {},
    );

    expect(message).toBe("campo_novo precisa ser preenchido.");
  });

  it("traduz o tipo, não o texto em inglês", () => {
    const casos: [string, string][] = [
      ["extra_forbidden", "não é aceito nesta operação"],
      ["datetime_parsing", "não é uma data e hora válida"],
      ["int_parsing", "precisa ser um número inteiro"],
      ["string_pattern_mismatch", "está fora do formato esperado"],
    ];

    for (const [type, esperado] of casos) {
      const message = validationMessage(validation({ field: "priority", message: "x", type }), LABELS);
      expect(message).toBe(`Prioridade ${esperado}.`);
    }
  });

  it("devolve null quando não é erro de validação", () => {
    expect(validationMessage(new ApiError("TRUCK_NOT_FOUND", "não achou"), LABELS)).toBeNull();
  });

  it("devolve null quando o 422 vem sem detalhe, preservando o texto original", () => {
    expect(validationMessage(validation(), LABELS)).toBeNull();
  });

  it("aguenta detalhe fora do formato sem quebrar a tela", () => {
    const error = new ApiError("VALIDATION_ERROR", "inválido", ["texto solto", null, 42]);

    expect(validationMessage(error, LABELS)).toBeNull();
  });
});
