import type { TruckSnapshot } from "../../load-planning/types";
import { SCENE_SCALE, type Box } from "./sceneGeometry";

/**
 * Exterior do caminhão (cabine, chassi, rodas) derivado das medidas REAIS do
 * baú cadastrado, em vez de um modelo pronto de proporção fixa.
 *
 * A razão é a mesma que rege o resto da cena: o valor da tela é a precisão
 * dimensional. Um modelo importado teria comprimento e altura próprios e
 * passaria a impressão errada sobre o caminhão que o usuário cadastrou.
 *
 * O que é derivado do cadastro: comprimento, largura e altura do baú, e tudo
 * que se apoia neles. O que é constante são medidas de chassi de caminhão que
 * não vêm da API e não afetam a carga — altura do piso, raio de roda, tamanho
 * de cabine. Elas posicionam o desenho; **nenhuma delas entra em cálculo de
 * encaixe**, que continua sendo exclusividade do backend (`docs/11`).
 */

/** Medidas de chassi em metros, típicas de caminhão de baú. */
export const DECK_HEIGHT = 1.15;
export const WHEEL_RADIUS = 0.5;
export const WHEEL_WIDTH = 0.28;
export const CHASSIS_HEIGHT = 0.18;
export const CAB_LENGTH = 2.3;
/** Altura do teto da cabine a partir do solo. */
export const CAB_TOP = 2.55;
/** Distância mínima entre eixos traseiros num rodado duplo. */
const TANDEM_GAP = 1.35;

export interface Wheel {
  position: [number, number, number];
  radius: number;
}

export interface TruckShell {
  /** Quanto a carga inteira sobe do solo: o piso do baú apoia no chassi. */
  deckHeight: number;
  cab: Box;
  windshield: Box;
  chassis: Box;
  bumper: Box;
  wheels: Wheel[];
}

export function truckShell(truck: TruckSnapshot): TruckShell {
  const width = truck.widthCm * SCENE_SCALE;
  const height = truck.heightCm * SCENE_SCALE;
  const length = truck.lengthCm * SCENE_SCALE;

  // A cabine fica ANTES do baú: z=0 é a parede frontal da carga (docs/02).
  const cabHeight = Math.min(CAB_TOP, DECK_HEIGHT + height) - 0.35;
  const cabCenterZ = -CAB_LENGTH / 2;

  const cab: Box = {
    position: [width / 2, 0.35 + cabHeight / 2, cabCenterZ],
    size: [width, cabHeight, CAB_LENGTH],
  };

  // Para-brisa: painel fino no terço superior da frente da cabine.
  const windshield: Box = {
    position: [width / 2, 0.35 + cabHeight * 0.76, -CAB_LENGTH + 0.06],
    size: [width * 0.86, cabHeight * 0.34, 0.06],
  };

  const chassis: Box = {
    position: [width / 2, DECK_HEIGHT - CHASSIS_HEIGHT / 2, (length - CAB_LENGTH) / 2],
    size: [width * 0.82, CHASSIS_HEIGHT, length + CAB_LENGTH],
  };

  const bumper: Box = {
    position: [width / 2, 0.4, -CAB_LENGTH - 0.12],
    size: [width * 0.96, 0.26, 0.24],
  };

  const wheels: Wheel[] = [];
  const addAxle = (z: number) => {
    // uma roda de cada lado, encostada na face externa do baú
    wheels.push({ position: [-WHEEL_WIDTH / 2, WHEEL_RADIUS, z], radius: WHEEL_RADIUS });
    wheels.push({ position: [width + WHEEL_WIDTH / 2, WHEEL_RADIUS, z], radius: WHEEL_RADIUS });
  };

  addAxle(-CAB_LENGTH * 0.62); // eixo dianteiro, sob a cabine
  // Eixo traseiro no fim do baú, deixando balanço. Baú longo ganha tandem.
  const rearZ = length * 0.78;
  addAxle(rearZ);
  if (length >= 6.5) {
    addAxle(rearZ - TANDEM_GAP);
  }

  return { deckHeight: DECK_HEIGHT, cab, windshield, chassis, bumper, wheels };
}

/** Câmera recuada o bastante para enquadrar cabine + baú + altura do chassi. */
export function shellCameraPosition(truck: TruckSnapshot): [number, number, number] {
  const width = truck.widthCm * SCENE_SCALE;
  const height = truck.heightCm * SCENE_SCALE + DECK_HEIGHT;
  const length = truck.lengthCm * SCENE_SCALE + CAB_LENGTH;
  const reach = Math.max(width, height, length);

  return [width / 2 + reach * 0.55, height + reach * 0.3, length * 0.85 + reach * 0.35];
}
