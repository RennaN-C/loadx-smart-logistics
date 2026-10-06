import { describe, expect, it } from "vitest";

import { maskCep, maskDocument, maskPhone, onlyDigits } from "./masks";

describe("maskDocument", () => {
  it("formata o CPF do roteiro exatamente como pedido", () => {
    expect(maskDocument("12345678901")).toBe("123.456.789-01");
  });

  it("formata o CNPJ do roteiro exatamente como pedido", () => {
    expect(maskDocument("12345678000199")).toBe("12.345.678/0001-99");
  });

  it("formata enquanto se digita, sem esperar o campo completar", () => {
    // é isso que evita o campo dar um pulo visual ao chegar no último dígito
    expect(maskDocument("1")).toBe("1");
    expect(maskDocument("123")).toBe("123");
    expect(maskDocument("1234")).toBe("123.4");
    expect(maskDocument("1234567")).toBe("123.456.7");
    expect(maskDocument("1234567890")).toBe("123.456.789-0");
  });

  it("vira CNPJ ao passar de 11 dígitos", () => {
    expect(maskDocument("123456789012")).toBe("12.345.678/9012");
  });

  it("descarta o que passa de 14 dígitos em vez de deformar a máscara", () => {
    expect(maskDocument("1234567800019999999")).toBe("12.345.678/0001-99");
  });

  it("aceita entrada já pontuada sem duplicar a pontuação", () => {
    // acontece ao colar de outro sistema
    expect(maskDocument("123.456.789-01")).toBe("123.456.789-01");
    expect(maskDocument("12.345.678/0001-99")).toBe("12.345.678/0001-99");
  });

  it("ignora letras", () => {
    expect(maskDocument("12a34b567c890d1")).toBe("123.456.789-01");
  });

  it("não quebra com campo vazio", () => {
    expect(maskDocument("")).toBe("");
  });
});

describe("maskPhone", () => {
  it("formata o celular do roteiro exatamente como pedido", () => {
    expect(maskPhone("42999998888")).toBe("(42) 99999-8888");
  });

  it("formata fixo de dez dígitos", () => {
    expect(maskPhone("4233334444")).toBe("(42) 3333-4444");
  });

  it("formata enquanto se digita", () => {
    expect(maskPhone("4")).toBe("4");
    expect(maskPhone("42")).toBe("42");
    expect(maskPhone("429")).toBe("(42) 9");
    expect(maskPhone("429999")).toBe("(42) 9999");
    expect(maskPhone("4299999")).toBe("(42) 9999-9");
  });

  it("descarta o que passa de 11 dígitos", () => {
    expect(maskPhone("4299999888899")).toBe("(42) 99999-8888");
  });

  it("aceita entrada já pontuada", () => {
    expect(maskPhone("(42) 99999-8888")).toBe("(42) 99999-8888");
  });
});

describe("onlyDigits", () => {
  it("devolve o que viaja para a API: dígitos, sem pontuação", () => {
    expect(onlyDigits("123.456.789-01")).toBe("12345678901");
    expect(onlyDigits("(42) 99999-8888")).toBe("42999998888");
  });
});

describe("maskCep", () => {
  it("formata enquanto se digita", () => {
    expect(maskCep("0")).toBe("0");
    expect(maskCep("01234")).toBe("01234");
    expect(maskCep("012345")).toBe("01234-5");
    expect(maskCep("01234567")).toBe("01234-567");
  });

  it("preserva zero à esquerda, que é CEP de verdade", () => {
    expect(maskCep("01001000")).toBe("01001-000");
  });

  it("descarta o que passa de 8 dígitos", () => {
    expect(maskCep("012345678999")).toBe("01234-567");
  });

  it("aceita entrada já pontuada", () => {
    expect(maskCep("01234-567")).toBe("01234-567");
  });
});
