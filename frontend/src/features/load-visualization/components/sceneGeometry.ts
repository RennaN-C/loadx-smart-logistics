import type { PlacedItem, TruckSnapshot } from "../../load-planning/types";

/**
 * Ponte entre o sistema de coordenadas do backend e o do Three.js.
 *
 * O backend usa `x`=largura, `y`=altura, `z`=comprimento, com a origem no piso
 * frente-esquerda do baú (docs/02). O Three.js também tem Y para cima, então os
 * eixos coincidem — o que muda é a ANCORAGEM: o backend dá o canto do volume, e
 * o Three.js posiciona pelo centro.
 *
 * `RISCO IDENTIFICADO` em docs/11: o frontend não pode recalcular geometria.
 * Aqui só há conversão de unidade e de âncora; nenhuma decisão de encaixe.
 */

/** cm → metros, para a cena não trabalhar com milhares de unidades. */
export const SCENE_SCALE = 0.01;

export interface Box {
  /** Centro da caixa, em unidades de cena. */
  position: [number, number, number];
  /** Dimensões completas, em unidades de cena. */
  size: [number, number, number];
}

export function truckBox(truck: TruckSnapshot): Box {
  const w = truck.widthCm * SCENE_SCALE;
  const h = truck.heightCm * SCENE_SCALE;
  const l = truck.lengthCm * SCENE_SCALE;

  return { position: [w / 2, h / 2, l / 2], size: [w, h, l] };
}

export function itemBox(item: PlacedItem): Box {
  const w = item.widthCm * SCENE_SCALE;
  const h = item.heightCm * SCENE_SCALE;
  const l = item.lengthCm * SCENE_SCALE;

  return {
    // canto (backend) + metade da dimensão = centro (Three.js)
    position: [item.xCm * SCENE_SCALE + w / 2, item.yCm * SCENE_SCALE + h / 2, item.zCm * SCENE_SCALE + l / 2],
    size: [w, h, l],
  };
}

/** Posição inicial da câmera: recuada e acima, enquadrando o baú inteiro. */
export function cameraPosition(truck: TruckSnapshot): [number, number, number] {
  const w = truck.widthCm * SCENE_SCALE;
  const h = truck.heightCm * SCENE_SCALE;
  const l = truck.lengthCm * SCENE_SCALE;
  const reach = Math.max(w, h, l);

  return [w / 2 + reach * 0.9, h + reach * 0.5, l + reach * 0.6];
}

/**
 * Cor por sequência de ENTREGA, não de carregamento: quem olha a carga quer ver
 * quais volumes saem juntos na mesma parada. Tons do próprio tema, girando o
 * matiz a partir do âmbar da marca.
 */
export function deliveryColor(deliverySequence: number): string {
  const hue = (28 + (deliverySequence - 1) * 47) % 360;
  return `hsl(${hue}, 58%, 56%)`;
}

/**
 * Versão clara da mesma cor, para TINGIR o papelão. A textura já traz o kraft
 * e a luz; multiplicar pela cor cheia da legenda deixaria o volume escuro
 * demais para se distinguir do vizinho. Mesma matiz, luminosidade alta.
 */
export function deliveryTint(deliverySequence: number): string {
  const hue = (28 + (deliverySequence - 1) * 47) % 360;
  return `hsl(${hue}, 46%, 82%)`;
}

/** Sequências presentes na carga, ordenadas — alimenta a legenda. */
export function deliverySequences(items: readonly PlacedItem[]): number[] {
  return [...new Set(items.map((item) => item.deliverySequence))].sort((a, b) => a - b);
}
