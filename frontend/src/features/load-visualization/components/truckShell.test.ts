import { describe, expect, it } from "vitest";

import type { TruckSnapshot } from "../../load-planning/types";
import { CAB_LENGTH, DECK_HEIGHT, WHEEL_RADIUS, truckShell } from "./truckShell";

function truck(overrides: Partial<TruckSnapshot> = {}): TruckSnapshot {
  return {
    id: "t1",
    plate: "ABC1D23",
    model: "Baú médio",
    widthCm: 240,
    heightCm: 260,
    lengthCm: 600,
    maxWeightKg: 8000,
    ...overrides,
  };
}

describe("truckShell", () => {
  it("acompanha as medidas cadastradas: baú mais longo, chassi mais longo", () => {
    const curto = truckShell(truck({ lengthCm: 400 }));
    const longo = truckShell(truck({ lengthCm: 900 }));

    // 5 m a mais de baú viram 5 m a mais de chassi
    expect(longo.chassis.size[2] - curto.chassis.size[2]).toBeCloseTo(5, 6);
  });

  it("acompanha a largura cadastrada", () => {
    const estreito = truckShell(truck({ widthCm: 200 }));
    const largo = truckShell(truck({ widthCm: 260 }));

    expect(largo.cab.size[0] - estreito.cab.size[0]).toBeCloseTo(0.6, 6);
  });

  it("põe a cabine ANTES da carga, porque z=0 é a parede frontal do baú", () => {
    const shell = truckShell(truck());
    const fundoDaCabine = shell.cab.position[2] + shell.cab.size[2] / 2;

    expect(fundoDaCabine).toBeCloseTo(0, 6);
    expect(shell.cab.position[2]).toBeLessThan(0);
  });

  it("apoia todas as rodas no chão, nenhuma enterrada ou flutuando", () => {
    const shell = truckShell(truck());

    for (const wheel of shell.wheels) {
      expect(wheel.position[1]).toBeCloseTo(wheel.radius, 6);
    }
  });

  it("mantém o piso do baú acima do topo das rodas", () => {
    const shell = truckShell(truck());

    expect(shell.deckHeight).toBeGreaterThan(WHEEL_RADIUS * 2);
  });

  it("usa tandem só em baú longo", () => {
    expect(truckShell(truck({ lengthCm: 400 })).wheels).toHaveLength(4); // 2 eixos
    expect(truckShell(truck({ lengthCm: 900 })).wheels).toHaveLength(6); // 3 eixos
  });

  it("põe o eixo traseiro na metade de trás do baú, com balanço", () => {
    const shell = truckShell(truck({ lengthCm: 600 }));
    const comprimento = 6;
    const traseiro = Math.max(...shell.wheels.map((w) => w.position[2]));

    expect(traseiro).toBeGreaterThan(comprimento / 2);
    expect(traseiro).toBeLessThan(comprimento);
  });

  it("não deixa a cabine ultrapassar a altura de um caminhão real", () => {
    // baú muito alto não pode esticar a cabine junto
    const shell = truckShell(truck({ heightCm: 400 }));
    const topoDaCabine = shell.cab.position[1] + shell.cab.size[1] / 2;

    expect(topoDaCabine).toBeLessThanOrEqual(2.6);
  });

  it("mantém a cabine dentro do vão entre solo e teto do baú", () => {
    const shell = truckShell(truck());
    const baseDaCabine = shell.cab.position[1] - shell.cab.size[1] / 2;

    expect(baseDaCabine).toBeGreaterThan(0);
  });

  it("mantém o topo do chassi FORA do plano do piso do baú", () => {
    // Regressão do piscar: com o topo do chassi exatamente em DECK_HEIGHT, ele e
    // o piso do baú disputavam o mesmo valor de profundidade e a placa alternava
    // entre os dois a cada quadro ao girar a câmera.
    const shell = truckShell(truck());
    const topoDoChassi = shell.chassis.position[1] + shell.chassis.size[1] / 2;

    expect(topoDoChassi).toBeLessThan(DECK_HEIGHT);
    // folga suficiente para o buffer de profundidade distinguir os dois
    expect(DECK_HEIGHT - topoDoChassi).toBeGreaterThanOrEqual(0.02);
  });

  it("estende o chassi por baixo da cabine e do baú inteiros", () => {
    const shell = truckShell(truck({ lengthCm: 600 }));

    expect(shell.chassis.size[2]).toBeCloseTo(6 + CAB_LENGTH, 6);
    expect(shell.chassis.position[1]).toBeLessThan(DECK_HEIGHT);
  });
});
