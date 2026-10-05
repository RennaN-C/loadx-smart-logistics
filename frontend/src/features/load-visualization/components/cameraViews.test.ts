import { describe, expect, it } from "vitest";

import type { TruckSnapshot } from "../../load-planning/types";
import { CAB_LENGTH, DECK_HEIGHT } from "./truckShell";
import { viewCamera, type CameraView } from "./cameraViews";

type Vec3 = [number, number, number];

const FOV_Y = 45;

/**
 * O ponto aparece no quadro desta vista?
 *
 * A conta é refeita aqui de propósito: o código de produção calcula DISTÂNCIA,
 * e o teste verifica CONTENÇÃO. São perguntas diferentes, então um erro de um
 * lado não se esconde atrás do outro.
 */
function noQuadro(view: CameraView, ponto: Vec3, aspect: number): boolean {
  const frente: Vec3 = [
    view.target[0] - view.position[0],
    view.target[1] - view.position[1],
    view.target[2] - view.position[2],
  ];
  const n = Math.hypot(...frente);
  const f: Vec3 = [frente[0] / n, frente[1] / n, frente[2] / n];

  const ref: Vec3 = Math.abs(f[1]) > 0.95 ? [0, 0, 1] : [0, 1, 0];
  const cr = (a: Vec3, b: Vec3): Vec3 => [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ];
  const dir = cr(ref, f);
  const dn = Math.hypot(...dir);
  const direita: Vec3 = [dir[0] / dn, dir[1] / dn, dir[2] / dn];
  const cima = cr(direita, f);

  const v: Vec3 = [
    ponto[0] - view.position[0],
    ponto[1] - view.position[1],
    ponto[2] - view.position[2],
  ];
  const dot = (a: Vec3, b: Vec3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];

  const profundidade = dot(v, f);
  if (profundidade <= 0) return false;

  const meiaAltura = Math.tan((FOV_Y * Math.PI) / 360) * profundidade;
  const meiaLargura = meiaAltura * aspect;

  return Math.abs(dot(v, direita)) <= meiaLargura && Math.abs(dot(v, cima)) <= meiaAltura;
}

/** Os oito cantos do veículo inteiro, cabine incluída. */
function cantosDoVeiculo(l = 6, w = 2.4, topo = DECK_HEIGHT + 2.6): Vec3[] {
  const cantos: Vec3[] = [];
  for (const x of [0, w]) for (const y of [0, topo]) for (const z of [-CAB_LENGTH, l]) cantos.push([x, y, z]);
  return cantos;
}

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
  it("o caminhão INTEIRO cabe no quadro, cabine incluída", () => {
    // A mira era o centro da carga, e a cabine ocupa 2,3 m ANTES de z = 0:
    // o veículo nascia encostado numa borda. Agora as vistas de fora miram o
    // centro do veículo e recuam pela projeção real da caixa dele.
    for (const preset of ["isometric", "side", "top"] as const) {
      for (const aspect of [2.4, 1.6, 0.8]) {
        const view = viewCamera(truck(), preset, DECK, aspect);
        for (const canto of cantosDoVeiculo()) {
          expect(noQuadro(view, canto, aspect), `${preset} @ ${aspect}`).toBe(true);
        }
      }
    }
  });

  it("enche o quadro em vez de deixar o caminhão perdido no fundo", () => {
    // Antes a distância era um múltiplo fixo do tamanho, sem olhar a proporção
    // do canvas: num painel largo o veículo ocupava perto de metade da largura.
    const aspect = 2.0;
    const { position, target } = viewCamera(truck(), "side", DECK, aspect);

    const distancia = Math.hypot(
      position[0] - target[0],
      position[1] - target[1],
      position[2] - target[2],
    );
    const larguraVisivel = 2 * distancia * Math.tan((FOV_Y * Math.PI) / 360) * aspect;
    const comprimentoDoVeiculo = 6 + CAB_LENGTH;

    expect(comprimentoDoVeiculo / larguraVisivel).toBeGreaterThan(0.7);
  });

  it("sobe a mira quando o caminhão está ligado: a carga deixa de estar no chão", () => {
    const semCaminhao = viewCamera(truck(), "isometric", 0);
    const comCaminhao = viewCamera(truck(), "isometric", DECK);

    expect(comCaminhao.target[1]).toBeGreaterThan(semCaminhao.target[1]);
  });

  it("a traseira mira a carga, e não o centro do veículo: o assunto é a porta", () => {
    const { target } = viewCamera(truck(), "rear", DECK);

    expect(target).toEqual([1.2, DECK + 1.3, 3]);
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
