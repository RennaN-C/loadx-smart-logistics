import { CanvasTexture, SRGBColorSpace, type Texture } from "three";

import type { TruckSnapshot } from "../../load-planning/types";
import { SCENE_SCALE } from "./sceneGeometry";
import { CAB_MODEL_TOP } from "./truckCabModel";
import { CAB_LENGTH, DECK_HEIGHT } from "./truckShell";

/**
 * Cenário em volta do caminhão: céu, chão e névoa.
 *
 * Antes não havia nenhum: o `Canvas` deixava passar a cor da página, e no tema
 * escuro a cena ficava num preto chapado onde o caminhão parecia recortado e
 * colado. Um gradiente vertical resolve isso sem custar byte de asset — mesma
 * conta que desenhou as caixas em canvas (`cargoTexture.ts`) em vez de carregar
 * foto.
 *
 * A névoa não é enfeite: sem ela a grade do chão termina num corte reto no
 * meio do nada, e é esse corte que faz a cena parecer inacabada.
 */

export interface BackdropPalette {
  /** Topo do céu. */
  readonly zenith: string;
  /** Faixa do horizonte, onde a névoa dissolve o chão. */
  readonly horizon: string;
  readonly ground: string;
  readonly gridLine: string;
  readonly gridEdge: string;
}

/**
 * Duas paletas, seguindo os tokens do app (`--paper`, `--line`, `--muted`).
 * O tema do LoadX é decidido só por `prefers-color-scheme`, sem alternador.
 */
const DARK: BackdropPalette = {
  zenith: "#0c1014",
  horizon: "#2b333d",
  ground: "#1a1f25",
  // Discreta de propósito: a grade dá escala, não é o assunto. No primeiro
  // ajuste ela ficou clara demais e disputava atenção com a carga.
  gridLine: "#262d36",
  gridEdge: "#333c47",
};

const LIGHT: BackdropPalette = {
  zenith: "#cdd4dc",
  horizon: "#f2efe7",
  ground: "#e6e3d8",
  gridLine: "#d0cbbb",
  gridEdge: "#b3ad9b",
};

export function backdropPalette(dark: boolean): BackdropPalette {
  return dark ? DARK : LIGHT;
}

/**
 * Altura da textura do céu. Só o eixo vertical tem informação — a largura é 2
 * pixels porque o gradiente não varia na horizontal, e esticar 2 px pela tela
 * inteira custa o mesmo que esticar 2000.
 */
const SKY_HEIGHT = 256;

/**
 * `null` quando não há canvas (jsdom na suíte de testes). Sem textura a cena
 * cai na cor lisa do horizonte, que continua melhor que o preto.
 */
export function skyTexture(palette: BackdropPalette): Texture | null {
  if (typeof document === "undefined") return null;

  const canvas = document.createElement("canvas");
  canvas.width = 2;
  canvas.height = SKY_HEIGHT;

  const ctx = canvas.getContext("2d");
  if (ctx === null) return null;

  const gradiente = ctx.createLinearGradient(0, 0, 0, SKY_HEIGHT);
  gradiente.addColorStop(0, palette.zenith);
  // A parada do meio não é média das pontas: o céu escurece rápido perto do
  // topo e fica quase parado perto do horizonte, que é como o olho espera.
  gradiente.addColorStop(0.62, palette.horizon);
  gradiente.addColorStop(1, palette.horizon);

  ctx.fillStyle = gradiente;
  ctx.fillRect(0, 0, 2, SKY_HEIGHT);

  const textura = new CanvasTexture(canvas);
  textura.colorSpace = SRGBColorSpace;
  return textura;
}

export interface VehicleBounds {
  /** Centro do veículo INTEIRO, cabine incluída. */
  readonly center: [number, number, number];
  readonly spanX: number;
  readonly spanY: number;
  readonly spanZ: number;
  /** Extremos em Z: a cabine fica antes da parede frontal da carga. */
  readonly minZ: number;
  readonly maxZ: number;
}

/**
 * Medidas do veículo inteiro.
 *
 * A grade ficava centrada na ORIGEM, que não é o centro de nada: o baú vai de
 * z = 0 ao comprimento e a cabine ocupa z negativo. O chão nascia torto em
 * relação ao caminhão, e era isso que dava a impressão de desalinhamento.
 *
 * `deck` é zero quando o exterior está desligado — aí o veículo é só a carga.
 */
export function vehicleBounds(truck: TruckSnapshot, showTruck: boolean): VehicleBounds {
  const width = truck.widthCm * SCENE_SCALE;
  const height = truck.heightCm * SCENE_SCALE;
  const length = truck.lengthCm * SCENE_SCALE;

  const minZ = showTruck ? -CAB_LENGTH : 0;
  const maxZ = length;
  const topo = showTruck ? Math.max(CAB_MODEL_TOP, DECK_HEIGHT + height) : height;

  return {
    center: [width / 2, topo / 2, (minZ + maxZ) / 2],
    spanX: width,
    spanY: topo,
    spanZ: maxZ - minZ,
    minZ,
    maxZ,
  };
}
