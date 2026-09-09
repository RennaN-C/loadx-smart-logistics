import { describe, expect, it } from "vitest";

import type { PlacedItem, TruckSnapshot } from "../../load-planning/types";
import { cameraPosition, deliveryColor, deliverySequences, itemBox, truckBox } from "./sceneGeometry";

const TRUCK: TruckSnapshot = {
  id: "t1",
  plate: "ABC1D23",
  model: "Baú médio",
  widthCm: 240,
  heightCm: 260,
  lengthCm: 600,
  maxWeightKg: 8000,
};

function item(overrides: Partial<PlacedItem> = {}): PlacedItem {
  return {
    id: "li1",
    orderId: "o1",
    orderItemId: "oi1",
    productId: "p1",
    volumeIndex: 1,
    quantity: 1,
    deliverySequence: 1,
    productCode: "CX-100",
    productName: "Caixa média",
    originalWidthCm: 40,
    originalHeightCm: 30,
    originalLengthCm: 60,
    weightKg: 12.5,
    fragile: false,
    stackable: true,
    rotationAllowed: true,
    xCm: 0,
    yCm: 0,
    zCm: 0,
    widthCm: 40,
    heightCm: 30,
    lengthCm: 60,
    rotationCode: "XYZ",
    loadingSequence: 1,
    ...overrides,
  };
}

describe("truckBox", () => {
  it("converte cm para metros e centraliza a caixa", () => {
    // o backend descreve o baú a partir da origem; o Three.js posiciona pelo centro
    expect(truckBox(TRUCK)).toEqual({ position: [1.2, 1.3, 3], size: [2.4, 2.6, 6] });
  });
});

describe("itemBox", () => {
  it("dá a CADA volume o tamanho do seu próprio produto", () => {
    // conferência da observação de que os pacotes saíam todos iguais: se dois
    // itens chegam com medidas diferentes, a cena os desenha diferentes.
    const pequeno = itemBox(item({ widthCm: 20, heightCm: 15, lengthCm: 30 }));
    const grande = itemBox(item({ widthCm: 80, heightCm: 60, lengthCm: 120 }));

    expect(pequeno.size).toEqual([0.2, 0.15, 0.3]);
    expect(grande.size).toEqual([0.8, 0.6, 1.2]);
    expect(grande.size[0] / pequeno.size[0]).toBeCloseTo(4, 6);
  });

  it("desloca o canto do backend para o centro da caixa", () => {
    expect(itemBox(item())).toEqual({ position: [0.2, 0.15, 0.3], size: [0.4, 0.3, 0.6] });
  });

  it("respeita a posição informada, sem recalcular encaixe", () => {
    const box = itemBox(item({ xCm: 100, yCm: 30, zCm: 200 }));

    // comparação por proximidade: cm→m gera dízima binária (0.3/2 = 0.1499…)
    expect(box.position[0]).toBeCloseTo(1.2, 10);
    expect(box.position[1]).toBeCloseTo(0.45, 10);
    expect(box.position[2]).toBeCloseTo(2.3, 10);
  });

  it("usa as dimensões JÁ rotacionadas, não as originais", () => {
    // volume girado: original 40x30x60, colocado como 60x40x30
    const box = itemBox(item({ widthCm: 60, heightCm: 40, lengthCm: 30, rotationCode: "ZXY" }));

    expect(box.size).toEqual([0.6, 0.4, 0.3]);
  });

  it("mantém o volume dentro do baú quando o backend assim posicionou", () => {
    const truck = truckBox(TRUCK);
    const box = itemBox(item({ xCm: 200, yCm: 230, zCm: 540, widthCm: 40, heightCm: 30, lengthCm: 60 }));

    const maxX = box.position[0] + box.size[0] / 2;
    const maxY = box.position[1] + box.size[1] / 2;
    const maxZ = box.position[2] + box.size[2] / 2;

    expect(maxX).toBeLessThanOrEqual(truck.size[0] + 1e-9);
    expect(maxY).toBeLessThanOrEqual(truck.size[1] + 1e-9);
    expect(maxZ).toBeLessThanOrEqual(truck.size[2] + 1e-9);
  });
});

describe("cameraPosition", () => {
  it("fica fora do baú, para enquadrar a carga inteira", () => {
    const [x, y, z] = cameraPosition(TRUCK);

    expect(y).toBeGreaterThan(TRUCK.heightCm * 0.01);
    expect(z).toBeGreaterThan(TRUCK.lengthCm * 0.01);
    expect(x).toBeGreaterThan(TRUCK.widthCm * 0.01 * 0.5);
  });
});

describe("deliveryColor", () => {
  it("dá cores diferentes para entregas diferentes", () => {
    expect(deliveryColor(1)).not.toBe(deliveryColor(2));
  });

  it("é estável para a mesma entrega", () => {
    expect(deliveryColor(3)).toBe(deliveryColor(3));
  });
});

describe("deliverySequences", () => {
  it("lista as sequências presentes, sem repetir e em ordem", () => {
    const items = [item({ deliverySequence: 3 }), item({ deliverySequence: 1 }), item({ deliverySequence: 3 })];

    expect(deliverySequences(items)).toEqual([1, 3]);
  });
});
