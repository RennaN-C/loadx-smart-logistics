import { describe, expect, it } from "vitest";

import type { TruckSnapshot } from "../../load-planning/types";
import { CAB_MODEL_TOP, CAB_MODEL_WIDTH, cabFrontWheels, cabPlacement } from "./truckCabModel";
import { CAB_LENGTH } from "./truckShell";

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

/** Medidas do GLB, repetidas de propósito: se o arquivo for regerado com
 *  outro recorte, estes testes falham e cobram a revisão. */
const MODEL_LENGTH = 2.945;

describe("cabPlacement", () => {
  it("NÃO se estica conforme o caminhão: a escala é a mesma para todos", () => {
    // Numa carreta real a cabine tem medida própria; quem varia é a carroceria.
    // Esticar junto deformava um modelo de proporção certa e ainda desalinhava
    // a roda do arco que o próprio modelo desenha.
    const escalas = [
      cabPlacement(truck({ widthCm: 200, heightCm: 180, lengthCm: 400 })).scale,
      cabPlacement(truck({ widthCm: 240, heightCm: 260, lengthCm: 600 })).scale,
      cabPlacement(truck({ widthCm: 300, heightCm: 320, lengthCm: 1200 })).scale,
    ];

    expect(new Set(escalas).size).toBe(1);
  });

  it("ocupa exatamente o vão que o chassi já reservava para a cabine", () => {
    expect(MODEL_LENGTH * cabPlacement(truck()).scale).toBeCloseTo(CAB_LENGTH, 10);
  });

  it("tem medidas de cabine de caminhão de verdade", () => {
    expect(CAB_MODEL_WIDTH).toBeGreaterThan(2.4);
    expect(CAB_MODEL_WIDTH).toBeLessThan(2.7);
    expect(CAB_MODEL_TOP).toBeGreaterThan(3.2);
    expect(CAB_MODEL_TOP).toBeLessThan(3.8);
  });

  it("fica centrada na largura e encostada na parede frontal da carga", () => {
    const { position, rotationY } = cabPlacement(truck({ widthCm: 240 }));

    expect(position[0]).toBeCloseTo(1.2, 10);
    expect(position[2]).toBe(0);
    // meia volta: no arquivo a frente aponta para +Z, na cena ela fica em -Z
    expect(rotationY).toBeCloseTo(Math.PI, 10);
  });

  it("depois da meia volta a cabine cabe entre -CAB_LENGTH e a carga", () => {
    const { scale, position } = cabPlacement(truck());

    expect(position[2] - MODEL_LENGTH * scale).toBeCloseTo(-CAB_LENGTH, 10);
  });
});

describe("cabFrontWheels", () => {
  it("encosta no chão: é o solo do próprio modelo que diz quanto levantar", () => {
    // A base da cabine foi zerada na normalização, e cabine não toca o chão —
    // sem usar o plano de solo do arquivo, a roda ficaria flutuando.
    for (const roda of cabFrontWheels(truck())) {
      expect(roda.position[1] - roda.radius).toBeCloseTo(0, 6);
    }
  });

  it("nasce sob a cabine, não atrás dela", () => {
    const [esquerda] = cabFrontWheels(truck());

    expect(esquerda.position[2]).toBeLessThan(0);
    expect(esquerda.position[2]).toBeGreaterThan(-CAB_LENGTH);
  });

  it("acompanha a bitola da cabine, e não as faces do baú", () => {
    // Num baú largo a regra antiga punha a roda colada na face da carga, ou
    // seja, do lado de fora da cabine — que tem largura própria e fixa.
    const largo = truck({ widthCm: 320 });
    const [esquerda, direita] = cabFrontWheels(largo);
    const centro = 3.2 / 2;

    expect(centro - esquerda.position[0]).toBeCloseTo(direita.position[0] - centro, 10);
    expect(direita.position[0] - esquerda.position[0]).toBeLessThan(3.2);
  });

  it("segue o centro do caminhão, que é onde a cabine está", () => {
    const [esq, dir] = cabFrontWheels(truck({ widthCm: 260 }));

    expect((esq.position[0] + dir.position[0]) / 2).toBeCloseTo(1.3, 10);
  });

  it("as duas rodas têm o mesmo raio e a mesma altura", () => {
    const [esq, dir] = cabFrontWheels(truck());

    expect(esq.radius).toBeCloseTo(dir.radius, 10);
    expect(esq.position[1]).toBeCloseTo(dir.position[1], 10);
  });
});
