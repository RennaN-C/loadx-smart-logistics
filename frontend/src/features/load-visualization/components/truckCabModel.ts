import type { TruckSnapshot } from "../../load-planning/types";
import { SCENE_SCALE } from "./sceneGeometry";
import { CAB_LENGTH, type Wheel } from "./truckShell";

/**
 * Posicionamento da cabine DAF importada.
 *
 * Esta é a ÚNICA peça da cena que vem de um modelo pronto, e ela pôde vir
 * justamente porque já era constante: `CAB_LENGTH` nunca saiu da API — a cabine
 * não carrega informação sobre o espaço de carga. O baú, o chassi e os eixos
 * traseiros continuam derivados do cadastro, como `docs/11` exige. Trocar o
 * baú por arte faria um baú de 6 m e uma carreta de 12 m aparecerem iguais na
 * tela, e aí a visualização passaria a mentir sobre o espaço.
 *
 * O arquivo é gerado por `scripts/obj2glb.py` a partir do OBJ original.
 */

/** Caminho servido estaticamente; fora do bundle, carregado sob demanda. */
export const CAB_MODEL_URL = "/models/truck-cab-daf.glb";

/**
 * Medidas do GLB, nas unidades do arquivo. Todas MEDIDAS, não estimadas — se o
 * modelo for regerado com outro recorte, os testes que as repetem falham e
 * cobram a revisão.
 */
const MODEL_LENGTH = 2.945;
/** Largura do corpo, sem os braços dos retrovisores (que levam o total a 3,681). */
const MODEL_BODY_WIDTH = 3.25;
const MODEL_HEIGHT = 4.391;
/** Centro da roda dianteira, no referencial já normalizado do GLB. */
const MODEL_FRONT_AXLE_Z = 1.2634;
const MODEL_FRONT_AXLE_Y = 0.3262;
const MODEL_WHEEL_RADIUS = 0.6552;
const MODEL_HALF_TRACK = 1.615;
/**
 * Onde fica o solo no referencial do modelo: a base do pneu, e não o plano de
 * cenário que veio no arquivo. No modelo original o pneu para 1,3 centésimo
 * ACIMA daquele plano, e usá-lo deixava a roda flutuando um centímetro na
 * cena. O solo é, por definição, onde a roda toca.
 *
 * Negativo porque a normalização zerou a base da CABINE, que fica acima do
 * chão — caminhão nenhum tem cabine encostada no asfalto.
 */
const MODEL_GROUND_Y = MODEL_FRONT_AXLE_Y - MODEL_WHEEL_RADIUS;

/**
 * Escala FIXA, igual para todo caminhão.
 *
 * A cabine não se estica conforme o baú. Num caminhão real a cabine tem medida
 * própria — é a carroceria que varia —, e esticá-la junto com o cadastro dava
 * dois defeitos: deformava um modelo que tem proporção certa, e desalinhava as
 * rodas do arco de roda que o próprio modelo desenha.
 *
 * `CAB_LENGTH / MODEL_LENGTH` faz a cabine ocupar exatamente o vão que o
 * chassi e o para-choque já reservavam, e dá 2,54 m de largura por 3,43 m de
 * altura: medidas de cabine de caminhão de verdade.
 */
const SCALE = CAB_LENGTH / MODEL_LENGTH;

/** Altura em que a base da cabine se apoia, para a roda tocar o solo. */
const CAB_BASE = -MODEL_GROUND_Y * SCALE;

export const CAB_MODEL_WIDTH = MODEL_BODY_WIDTH * SCALE;
export const CAB_MODEL_TOP = CAB_BASE + MODEL_HEIGHT * SCALE;

export interface CabPlacement {
  scale: number;
  position: [number, number, number];
  /**
   * Meia volta em Y. No arquivo original a frente do caminhão aponta para +Z;
   * na cena, z = 0 é a parede frontal da carga e a cabine fica em z negativo.
   */
  rotationY: number;
}

export function cabPlacement(truck: TruckSnapshot): CabPlacement {
  const width = truck.widthCm * SCENE_SCALE;

  return {
    scale: SCALE,
    // Centrada na largura do caminhão e encostada na parede frontal da carga.
    position: [width / 2, CAB_BASE, 0],
    rotationY: Math.PI,
  };
}

/**
 * Eixo dianteiro, alinhado ao arco de roda que o modelo desenha.
 *
 * Não dá para reaproveitar o eixo dianteiro de `truckShell`: lá ele é posto em
 * fração de `CAB_LENGTH` e com a bitola colada nas faces do baú, o que fazia a
 * roda nascer atrás do arco e, em baú largo, do lado de fora da cabine. Aqui a
 * posição vem do próprio modelo. Os eixos TRASEIROS continuam em `truckShell`,
 * porque esses sim acompanham o comprimento do baú.
 */
export function cabFrontWheels(truck: TruckSnapshot): Wheel[] {
  const centerX = (truck.widthCm * SCENE_SCALE) / 2;
  const z = -MODEL_FRONT_AXLE_Z * SCALE;
  const y = CAB_BASE + MODEL_FRONT_AXLE_Y * SCALE;
  const radius = MODEL_WHEEL_RADIUS * SCALE;
  const halfTrack = MODEL_HALF_TRACK * SCALE;

  return [
    { position: [centerX - halfTrack, y, z], radius },
    { position: [centerX + halfTrack, y, z], radius },
  ];
}
