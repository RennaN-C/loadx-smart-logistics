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
/** Folga entre o topo do chassi e o piso do baú, para os dois não coincidirem. */
const CHASSIS_CLEARANCE = 0.03;
/** Recuo das pontas do chassi, para não encostarem na cabine nem no baú. */
const END_CLEARANCE = 0.18;
/** Espessura dos perfis estruturais do baú: longarina, montante, batente. */
const PROFILE = 0.07;
/** Folga entre o topo do pneu e o para-lama. */
const FENDER_GAP = 0.09;
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
  /** Estrutura do baú: o que faz ele parecer construído e não uma caixa. */
  roofRails: Box[];
  cornerPosts: Box[];
  doorFrame: Box[];
  fenders: Box[];
  sideSkirts: Box[];
  fuelTank: Box;
  rearGuard: Box;
  mirrors: Box[];
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

  // Para-brisa: painel fino SALIENTE na frente da cabine. Antes ficava 3 cm
  // para dentro dela, ou seja, invisível — a cabine tapava o próprio vidro.
  const windshield: Box = {
    position: [width / 2, 0.35 + cabHeight * 0.76, -CAB_LENGTH - 0.02],
    size: [width * 0.86, cabHeight * 0.34, 0.05],
  };

  // O topo do chassi NÃO pode cair no mesmo plano do piso do baú: duas
  // superfícies coplanares brigam pelo mesmo valor de profundidade e a placa de
  // vídeo alterna entre elas a cada quadro — é o piscar ao girar a câmera.
  // As pontas ficam RECUADAS das faces da cabine e do baú. Encostadas, as três
  // superfícies caíam no mesmo plano em z = -CAB_LENGTH e brigavam pelo mesmo
  // valor de profundidade — era o piscar na frente do caminhão.
  const chassisFront = -CAB_LENGTH + END_CLEARANCE;
  const chassisRear = length - END_CLEARANCE;
  const chassis: Box = {
    position: [
      width / 2,
      DECK_HEIGHT - CHASSIS_HEIGHT / 2 - CHASSIS_CLEARANCE,
      (chassisFront + chassisRear) / 2,
    ],
    size: [width * 0.82, CHASSIS_HEIGHT, chassisRear - chassisFront],
  };

  // Entra alguns centímetros DENTRO da cabine em vez de encostar nela: sólidos
  // que se interpenetram não brigam, sólidos que se tocam brigam.
  const bumper: Box = {
    position: [width / 2, 0.4, -CAB_LENGTH - 0.09],
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

  // ---- estrutura do baú ----
  // Um baú real tem esqueleto aparente: longarinas no teto, montantes nas
  // quinas e o batente da porta atrás. Sem isso ele lê como caixa de papelão
  // gigante, por mais correta que a medida esteja.
  const topo = DECK_HEIGHT + height;
  const traseira = length;

  const roofRails: Box[] = [
    { position: [PROFILE / 2, topo + PROFILE / 2, length / 2], size: [PROFILE, PROFILE, length] },
    {
      position: [width - PROFILE / 2, topo + PROFILE / 2, length / 2],
      size: [PROFILE, PROFILE, length],
    },
  ];

  const cornerPosts: Box[] = [0, traseira].flatMap((z) =>
    [PROFILE / 2, width - PROFILE / 2].map((x) => ({
      position: [x, DECK_HEIGHT + height / 2, z] as [number, number, number],
      size: [PROFILE, height, PROFILE] as [number, number, number],
    })),
  );

  // batente da porta: moldura em U no fim do baú
  const doorFrame: Box[] = [
    {
      position: [width / 2, topo + PROFILE / 2, traseira],
      size: [width, PROFILE, PROFILE],
    },
    {
      position: [width / 2, DECK_HEIGHT - PROFILE / 2, traseira],
      size: [width, PROFILE, PROFILE],
    },
  ];

  // para-lama sobre cada roda: acompanha a posição dos eixos que já existem
  const fenders: Box[] = wheels.map((wheel) => ({
    position: [wheel.position[0], wheel.radius + FENDER_GAP, wheel.position[2]],
    size: [WHEEL_WIDTH * 1.5, 0.07, wheel.radius * 2.5],
  }));

  // saia lateral entre os eixos, que é o que fecha o vão do chassi
  const skirtZ = (length * 0.78 - CAB_LENGTH * 0.62) / 2;
  const sideSkirts: Box[] = [0.02, width - 0.02].map((x) => ({
    position: [x, DECK_HEIGHT - 0.42, skirtZ],
    size: [0.05, 0.55, length * 0.52],
  }));

  const fuelTank: Box = {
    position: [width + 0.16, DECK_HEIGHT - 0.4, CAB_LENGTH * 0.3],
    size: [0.34, 0.44, 1.15],
  };

  const rearGuard: Box = {
    position: [width / 2, 0.52, traseira + 0.14],
    size: [width * 0.92, 0.12, 0.1],
  };

  const mirrors: Box[] = [-0.14, width + 0.14].map((x) => ({
    position: [x, 0.35 + cabHeight * 0.78, -CAB_LENGTH + 0.34],
    size: [0.06, 0.34, 0.14],
  }));

  return {
    deckHeight: DECK_HEIGHT,
    cab,
    windshield,
    chassis,
    bumper,
    wheels,
    roofRails,
    cornerPosts,
    doorFrame,
    fenders,
    sideSkirts,
    fuelTank,
    rearGuard,
    mirrors,
  };
}

/** Câmera recuada o bastante para enquadrar cabine + baú + altura do chassi. */
export function shellCameraPosition(truck: TruckSnapshot): [number, number, number] {
  const width = truck.widthCm * SCENE_SCALE;
  const height = truck.heightCm * SCENE_SCALE + DECK_HEIGHT;
  const length = truck.lengthCm * SCENE_SCALE + CAB_LENGTH;
  const reach = Math.max(width, height, length);

  return [width / 2 + reach * 0.55, height + reach * 0.3, length * 0.85 + reach * 0.35];
}
