import type { TruckSnapshot } from "../../load-planning/types";
import { SCENE_SCALE } from "./sceneGeometry";
import { CAB_LENGTH, DECK_HEIGHT } from "./truckShell";

/**
 * Posicionamento da cabine DAF importada.
 *
 * Esta é a ÚNICA peça da cena que vem de um modelo pronto, e ela pôde vir
 * justamente porque já era constante: `CAB_LENGTH` e `CAB_TOP` nunca saíram da
 * API — a cabine não carrega informação sobre o espaço de carga. O baú, o
 * chassi e as rodas continuam derivados do cadastro, como `docs/11` exige.
 * Trocar o baú por arte faria um baú de 6 m e uma carreta de 12 m aparecerem
 * iguais na tela, e aí a visualização passaria a mentir sobre o espaço.
 *
 * O arquivo é gerado por `scripts/obj2glb.py` a partir do OBJ original.
 */

/** Caminho servido estaticamente; fora do bundle, carregado sob demanda. */
export const CAB_MODEL_URL = "/models/truck-cab-daf.glb";

/**
 * Largura do CORPO da cabine, sem os retrovisores.
 *
 * Medido no modelo: 95% dos vértices cabem em 3,25 e o total só chega a 3,681
 * por causa dos braços dos retrovisores. Escalar pelo total encolheria a
 * cabine, deixando-a mais estreita que o próprio caminhão.
 */
const MODEL_BODY_WIDTH = 3.25;
const MODEL_HEIGHT = 4.391;
const MODEL_LENGTH = 2.945;

/** Altura em que a cabine se apoia, a mesma da cabine desenhada em código. */
const CAB_BASE = 0.35;

export interface CabPlacement {
  /** Escala por eixo aplicada ao modelo. */
  scale: [number, number, number];
  position: [number, number, number];
  /**
   * Meia volta em Y. No arquivo original a frente do caminhão aponta para +Z;
   * na cena, z = 0 é a parede frontal da carga e a cabine fica em z negativo.
   */
  rotationY: number;
}

export function cabPlacement(truck: TruckSnapshot): CabPlacement {
  const width = truck.widthCm * SCENE_SCALE;
  const height = truck.heightCm * SCENE_SCALE;

  // A cabine acompanha a largura do caminhão; altura segue junto para o rosto
  // do veículo não distorcer, que é o ângulo de onde mais se olha.
  let uniform = width / MODEL_BODY_WIDTH;

  // Num baú baixo a cabine natural passaria do teto da carga e o caminhão
  // ficaria com cara de cavalo sem carreta. Aqui ela encolhe até caber.
  const boxTop = DECK_HEIGHT + height;
  if (CAB_BASE + MODEL_HEIGHT * uniform > boxTop) {
    uniform = (boxTop - CAB_BASE) / MODEL_HEIGHT;
  }

  return {
    // Só o comprimento é esticado à parte, para a cabine ocupar exatamente o
    // vão que o chassi e o para-choque já reservavam. São 6% num caminhão de
    // 2,4 m — o bastante para não sobrar fresta, pouco para se notar.
    scale: [uniform, uniform, CAB_LENGTH / MODEL_LENGTH],
    position: [width / 2, CAB_BASE, 0],
    rotationY: Math.PI,
  };
}
