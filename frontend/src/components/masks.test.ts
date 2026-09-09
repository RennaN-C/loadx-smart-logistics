import { describe, expect, it } from "vitest";

import {
  documentKind,
  isCompleteDocument,
  isCompletePhone,
  maskDocument,
  maskPhone,
  onlyDigits,
} from "./masks";

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

describe("isCompleteDocument", () => {
  it("aceita CPF e CNPJ completos", () => {
    expect(isCompleteDocument("123.456.789-01")).toBe(true);
    expect(isCompleteDocument("12.345.678/0001-99")).toBe(true);
  });

  it("recusa documento pela metade, que é o caso do roteiro", () => {
    expect(isCompleteDocument("123.456")).toBe(false);
    expect(isCompleteDocument("123456789")).toBe(false);
    expect(isCompleteDocument("")).toBe(false);
  });

  it("recusa comprimento entre CPF e CNPJ", () => {
    expect(isCompleteDocument("123456789012")).toBe(false);
  });

  it("NÃO confere dígito verificador, e isso é proposital", () => {
    // O backend guarda texto livre; conferir o dígito aqui recusaria documento
    // fictício de teste e deixaria o frontend mais rígido que o contrato.
    expect(isCompleteDocument("00000000000")).toBe(true);
    expect(isCompleteDocument("11111111111111")).toBe(true);
  });
});

describe("isCompletePhone", () => {
  it("aceita fixo e celular", () => {
    expect(isCompletePhone("(42) 3333-4444")).toBe(true);
    expect(isCompletePhone("(42) 99999-8888")).toBe(true);
  });

  it("recusa telefone incompleto", () => {
    expect(isCompletePhone("(42) 9999")).toBe(false);
    expect(isCompletePhone("")).toBe(false);
  });
});

describe("documentKind", () => {
  it("diz o que o documento já é, e nada enquanto está curto", () => {
    expect(documentKind("123.456.789-01")).toBe("CPF");
    expect(documentKind("12.345.678/0001-99")).toBe("CNPJ");
    expect(documentKind("123.456")).toBeNull();
  });
});

describe("onlyDigits", () => {
  it("devolve o que viaja para a API: dígitos, sem pontuação", () => {
    expect(onlyDigits("123.456.789-01")).toBe("12345678901");
    expect(onlyDigits("(42) 99999-8888")).toBe("42999998888");
  });
});
