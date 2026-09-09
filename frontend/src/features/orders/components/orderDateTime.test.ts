import { describe, expect, it } from "vitest";

import { isoToLocalInput, localInputToIso } from "./orderDateTime";

describe("orderDateTime", () => {
  it("sempre devolve um ISO com fuso, que é o que o backend exige", () => {
    const iso = localInputToIso("2026-08-10T14:30");

    expect(iso).not.toBeNull();
    // toISOString termina em Z: o backend rejeita datetime ingênuo
    expect(iso).toMatch(/Z$/);
  });

  it("faz ida e volta sem perder o horário local digitado", () => {
    // independente do fuso da máquina: o valor local tem que voltar igual
    const original = "2026-08-10T14:30";

    expect(isoToLocalInput(localInputToIso(original))).toBe(original);
  });

  it("trata campo vazio como ausência de previsão", () => {
    expect(localInputToIso("")).toBeNull();
    expect(localInputToIso("   ")).toBeNull();
    expect(isoToLocalInput(null)).toBe("");
  });

  it("não quebra com data inválida", () => {
    expect(localInputToIso("não é data")).toBeNull();
    expect(isoToLocalInput("não é data")).toBe("");
  });
});
