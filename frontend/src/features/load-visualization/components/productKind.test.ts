import { describe, expect, it } from "vitest";

import { classifyProduct } from "./productKind";

describe("classifyProduct", () => {
  it("reconhece televisão escrita de várias formas", () => {
    expect(classifyProduct("TV 50 polegadas")).toBe("tv");
    expect(classifyProduct("Televisão LED")).toBe("tv");
    expect(classifyProduct("TELEVISOR SMART 4K")).toBe("tv");
    expect(classifyProduct("Monitor 27")).toBe("tv");
  });

  it("não se abala com acento nem com caixa", () => {
    expect(classifyProduct("televisão")).toBe("tv");
    expect(classifyProduct("TELEVISÃO")).toBe("tv");
    expect(classifyProduct("Fogão 4 bocas")).toBe("stove");
    expect(classifyProduct("FOGAO INDUSTRIAL")).toBe("stove");
  });

  it("trata hífen e ponto como espaço", () => {
    expect(classifyProduct("Micro-ondas 30L")).toBe("microwave");
    expect(classifyProduct("micro ondas")).toBe("microwave");
    expect(classifyProduct("MICROONDAS")).toBe("microwave");
  });

  it("dá preferência ao termo mais específico", () => {
    // "forno" sozinho é fogão, mas forno de micro-ondas é micro-ondas
    expect(classifyProduct("Forno de micro-ondas")).toBe("microwave");
    expect(classifyProduct("Forno elétrico")).toBe("stove");
  });

  it("reconhece linha branca", () => {
    expect(classifyProduct("Geladeira Frost Free")).toBe("fridge");
    expect(classifyProduct("Freezer horizontal")).toBe("fridge");
    expect(classifyProduct("Lavadora de roupas 12kg")).toBe("washer");
    expect(classifyProduct("Máquina de lavar")).toBe("washer");
  });

  it("casa por palavra inteira, não por pedaço de palavra", () => {
    // o perigo real: "tv" aparecendo dentro de outra palavra
    expect(classifyProduct("Estante MDF")).toBe("box");
    expect(classifyProduct("Camiseta")).toBe("box");
    expect(classifyProduct("Parafuso sextavado")).toBe("box");
  });

  it("cai em caixa quando não reconhece, que é o certo", () => {
    expect(classifyProduct("Volume padrão")).toBe("box");
    expect(classifyProduct("XPT-4412")).toBe("box");
    expect(classifyProduct("")).toBe("box");
  });
});
