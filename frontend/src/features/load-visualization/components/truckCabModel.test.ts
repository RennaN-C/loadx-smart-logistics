import { describe, expect, it } from "vitest";

import type { TruckSnapshot } from "../../load-planning/types";
import { cabPlacement } from "./truckCabModel";
import { CAB_LENGTH, DECK_HEIGHT } from "./truckShell";

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

/** Medidas naturais do GLB, repetidas aqui de propósito: se o arquivo for
 *  regerado com outras proporções, estes testes falham e cobram a revisão. */
const MODEL_HEIGHT = 4.391;
const MODEL_LENGTH = 2.945;

describe("cabPlacement", () => {
  it("acompanha a largura do caminhão, medida pelo CORPO e não pelos retrovisores", () => {
    const estreito = cabPlacement(truck({ widthCm: 200 }));
    const largo = cabPlacement(truck({ widthCm: 260 }));

    expect(largo.scale[0]).toBeGreaterThan(estreito.scale[0]);
    // 2,00 m de caminhão / 3,25 do corpo do modelo
    expect(estreito.scale[0]).toBeCloseTo(2 / 3.25, 5);
  });

  it("escala altura junto com largura: o rosto do caminhão não distorce", () => {
    const { scale } = cabPlacement(truck());

    expect(scale[1]).toBeCloseTo(scale[0], 10);
  });

  it("ocupa exatamente o vão que o chassi já reservava para a cabine", () => {
    const { scale } = cabPlacement(truck());

    expect(MODEL_LENGTH * scale[2]).toBeCloseTo(CAB_LENGTH, 10);
  });

  it("encolhe a cabine quando ela passaria do teto de um baú baixo", () => {
    // Baú de 1,40 m: a cabine natural (2,4/3,25 × 4,391 = 3,24 m) ficaria mais
    // alta que a carga e o caminhão pareceria cavalo sem carreta.
    const baixo = truck({ heightCm: 140 });
    const { scale, position } = cabPlacement(baixo);

    const topoDaCabine = position[1] + MODEL_HEIGHT * scale[1];
    const topoDoBau = DECK_HEIGHT + 1.4;

    expect(topoDaCabine).toBeCloseTo(topoDoBau, 10);
    expect(scale[1]).toBeLessThan(2.4 / 3.25);
  });

  it("não encolhe quando a cabine já cabe: um baú alto não mexe na escala", () => {
    const { scale } = cabPlacement(truck({ heightCm: 300 }));

    expect(scale[0]).toBeCloseTo(2.4 / 3.25, 10);
  });

  it("fica centrada na largura e encostada na parede frontal da carga", () => {
    const { position, rotationY } = cabPlacement(truck({ widthCm: 240 }));

    expect(position[0]).toBeCloseTo(1.2, 10);
    expect(position[2]).toBe(0);
    // meia volta: no arquivo a frente aponta para +Z, na cena ela fica em -Z
    expect(rotationY).toBeCloseTo(Math.PI, 10);
  });

  it("depois da meia volta a cabine cabe entre -CAB_LENGTH e a carga", () => {
    const { scale, position, rotationY } = cabPlacement(truck());

    // rotação de π em Y manda z para -z, então o modelo passa a ocupar
    // [-L·escala, 0] a partir da posição
    expect(rotationY).toBeCloseTo(Math.PI, 10);
    const frente = position[2] - MODEL_LENGTH * scale[2];
    expect(frente).toBeCloseTo(-CAB_LENGTH, 10);
  });
});
