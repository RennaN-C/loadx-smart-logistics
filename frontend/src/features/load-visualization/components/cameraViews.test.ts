import { describe, expect, it } from "vitest";

import type { TruckSnapshot } from "../../load-planning/types";
import { VIEW_PRESETS, viewCamera } from "./cameraViews";

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

const DECK = 1.15;

describe("viewCamera", () => {
  it("mira o centro da carga em todas as vistas de fora", () => {
    for (const preset of VIEW_PRESETS) {
      if (preset === "inside") continue;

      const { target } = viewCamera(truck(), preset, DECK);
      expect(target).toEqual([1.2, DECK + 1.3, 3]);
    }
  });

  it("sobe a mira junto com a carga quando o caminhão está ligado", () => {
    const semCaminhao = viewCamera(truck(), "isometric", 0);
    const comCaminhao = viewCamera(truck(), "isometric", DECK);

    expect(comCaminhao.target[1] - semCaminhao.target[1]).toBeCloseTo(DECK, 6);
  });

  it("recua mais para um baú longo do que para um curto", () => {
    const curto = viewCamera(truck({ lengthCm: 400 }), "side", DECK);
    const longo = viewCamera(truck({ lengthCm: 900 }), "side", DECK);

    expect(longo.position[0]).toBeGreaterThan(curto.position[0]);
  });

  it("põe a vista de topo acima do teto do baú", () => {
    const { position } = viewCamera(truck(), "top", DECK);

    expect(position[1]).toBeGreaterThan(DECK + 2.6);
  });

  it("põe a vista traseira atrás da porta", () => {
    const { position } = viewCamera(truck({ lengthCm: 600 }), "rear", DECK);

    expect(position[2]).toBeGreaterThan(6);
  });

  it("põe a vista interna DENTRO do baú, mirando o fundo", () => {
    const { position, target } = viewCamera(truck({ lengthCm: 600 }), "inside", DECK);

    // dentro do comprimento e da largura, e olhando para a parede da frente
    expect(position[2]).toBeGreaterThan(0);
    expect(position[2]).toBeLessThan(6);
    expect(position[0]).toBeCloseTo(1.2, 6);
    expect(target[2]).toBe(0);
  });

  it("a lateral olha de lado, não de frente", () => {
    const { position, target } = viewCamera(truck(), "side", DECK);

    // afastada em X e alinhada em Z com o centro
    expect(Math.abs(position[0] - target[0])).toBeGreaterThan(3);
    expect(position[2]).toBeCloseTo(target[2], 6);
  });
});
