import type { TruckSnapshot } from "../../load-planning/types";
import { vehicleBounds } from "./sceneBackdrop";
import { SCENE_SCALE } from "./sceneGeometry";
import { DECK_HEIGHT } from "./truckShell";

/**
 * Posições de câmera prontas. Girar até achar o ângulo certo é trabalho que a
 * tela pode poupar: conferir uma carga tem sempre os mesmos quatro ou cinco
 * pontos de vista, e cada um responde uma pergunta diferente.
 *
 * Tudo derivado das medidas do caminhão — um baú de 9 m precisa de mais recuo
 * que um de 4 m para caber no enquadramento.
 */
export const VIEW_PRESETS = ["isometric", "side", "top", "rear", "inside"] as const;

export type ViewPreset = (typeof VIEW_PRESETS)[number];

export const VIEW_LABELS: Record<ViewPreset, string> = {
  isometric: "Isométrica",
  side: "Lateral",
  top: "Topo",
  rear: "Traseira",
  inside: "Interna",
};

export const VIEW_HINTS: Record<ViewPreset, string> = {
  isometric: "Visão geral da carga e do caminhão.",
  side: "Mostra as camadas e a altura de empilhamento.",
  top: "Mostra o aproveitamento do piso.",
  rear: "É o que o conferente vê ao abrir a porta.",
  inside: "Câmera dentro do baú, olhando para o fundo.",
};

export interface CameraView {
  readonly position: [number, number, number];
  readonly target: [number, number, number];
}

type Vec3 = [number, number, number];

/** Abertura vertical da câmera, em graus. Precisa bater com o `fov` do Canvas. */
const FOV_Y = 45;

/**
 * Quanto do quadro o veículo ocupa. O resto é respiro.
 *
 * O valor antigo era implícito e saía perto de 0,5 — o caminhão ficava pequeno
 * no meio de um fundo vazio, que é metade da queixa de "mal alinhado".
 *
 * Não é o mesmo que a fração do quadro ocupada: o ajuste em perspectiva recua
 * a câmera para acomodar o canto MAIS PRÓXIMO, e numa vista de três quartos o
 * veículo atravessa o quadro na diagonal, gastando os dois eixos. Por isso o
 * valor é alto: o que sobra de margem real fica bem abaixo disto.
 */
const FILL = 0.95;

/** Proporção suposta quando o tamanho real do canvas ainda não é conhecido. */
const DEFAULT_ASPECT = 16 / 9;

function normalize(v: Vec3): Vec3 {
  const n = Math.hypot(v[0], v[1], v[2]);
  return [v[0] / n, v[1] / n, v[2] / n];
}

function cross(a: Vec3, b: Vec3): Vec3 {
  return [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ];
}

function dot(a: Vec3, b: Vec3): number {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

interface Aabb {
  readonly min: Vec3;
  readonly max: Vec3;
}

/**
 * Distância em que a caixa cabe no quadro, pelos DOIS eixos.
 *
 * Multiplicar o tamanho do caminhão por uma constante, como antes, ignora a
 * proporção do canvas: num painel largo sobra espaço nas laterais e o veículo
 * encolhe; num estreito ele é cortado. Aqui os oito cantos são projetados nos
 * eixos da tela e a distância sai da maior sobra real.
 */
function fitDistance(box: Aabb, target: Vec3, dir: Vec3, aspect: number): number {
  // Olhando de cima, o "para cima" do mundo é paralelo à direção e o produto
  // vetorial degenera; aí a referência passa a ser o eixo do comprimento.
  const referencia: Vec3 = Math.abs(dir[1]) > 0.95 ? [0, 0, 1] : [0, 1, 0];
  const direita = normalize(cross(referencia, dir));
  const cima = cross(dir, direita);

  const meiaAltura = Math.tan((FOV_Y * Math.PI) / 360) * FILL;
  const meiaLargura = meiaAltura * aspect;

  // A sobra do quadro cresce com a PROFUNDIDADE, não com a distância ao alvo:
  // um canto mais perto da câmera tem menos espaço. Medir tudo no plano do
  // alvo é a aproximação ortográfica, e ela deixava o canto da frente da vista
  // isométrica escapar do quadro. Por isso cada canto pede a sua distância —
  // `dot(v, dir)` é o quanto ele avança em direção à câmera.
  let distancia = 0;
  for (const x of [box.min[0], box.max[0]]) {
    for (const y of [box.min[1], box.max[1]]) {
      for (const z of [box.min[2], box.max[2]]) {
        const v: Vec3 = [x - target[0], y - target[1], z - target[2]];
        const pedida =
          Math.max(Math.abs(dot(v, direita)) / meiaLargura, Math.abs(dot(v, cima)) / meiaAltura) +
          dot(v, dir);
        distancia = Math.max(distancia, pedida);
      }
    }
  }

  return distancia;
}

function place(target: Vec3, dir: Vec3, distancia: number): CameraView {
  return {
    position: [
      target[0] + dir[0] * distancia,
      target[1] + dir[1] * distancia,
      target[2] + dir[2] * distancia,
    ],
    target,
  };
}

/**
 * `deck` é o quanto a carga está levantada do chão — zero quando o exterior do
 * caminhão está desligado. Sem ele, as vistas mirariam o vazio abaixo do baú.
 * É também o que diz se a cabine entra no enquadramento.
 *
 * `aspect` é a proporção do canvas. Tem padrão para quem só precisa da direção,
 * mas quem desenha deve passar a real — é o que decide o quanto recuar.
 */
export function viewCamera(
  truck: TruckSnapshot,
  preset: ViewPreset,
  deck: number,
  aspect: number = DEFAULT_ASPECT,
): CameraView {
  const width = truck.widthCm * SCENE_SCALE;
  const height = truck.heightCm * SCENE_SCALE;
  const length = truck.lengthCm * SCENE_SCALE;

  const cargoCenter: Vec3 = [width / 2, deck + height / 2, length / 2];
  // O veículo inteiro, cabine incluída. Mirar só a carga deixava o caminhão
  // encostado numa borda do quadro, porque a cabine ocupa 2,3 m ANTES de z = 0.
  const bounds = vehicleBounds(truck, deck > 0);
  const vehicleCenter = bounds.center as Vec3;
  const vehicle: Aabb = {
    min: [0, 0, bounds.minZ],
    max: [bounds.spanX, bounds.spanY, bounds.maxZ],
  };

  switch (preset) {
    case "side": {
      // de fora da lateral direita, quase no nível da carga
      const dir = normalize([1, 0.08, 0]);
      return place(vehicleCenter, dir, fitDistance(vehicle, vehicleCenter, dir, aspect));
    }

    case "top": {
      // de cima, ligeiramente puxada para trás para o teto não achatar tudo
      const dir = normalize([0, 1, 0.08]);
      return place(vehicleCenter, dir, fitDistance(vehicle, vehicleCenter, dir, aspect));
    }

    case "rear": {
      // Atrás da porta, na altura de quem abre. O recuo é medido pela BOCA do
      // baú, não pelo centro da carga: a boca é a face mais próxima, e caber o
      // centro deixaria a moldura fora do quadro.
      const porta: Aabb = { min: [0, deck, length], max: [width, deck + height, length] };
      const portaCentro: Vec3 = [width / 2, deck + height / 2, length];
      const recuo = fitDistance(porta, portaCentro, [0, 0, 1], aspect);

      return {
        position: [width / 2, DECK_HEIGHT + height * 0.5, length + recuo],
        target: cargoCenter,
      };
    }

    case "inside":
      // Dentro do baú, junto à porta, olhando para o fundo. A mira vai para a
      // parede da frente — é a única vista que não aponta para o centro.
      return {
        position: [width / 2, deck + height * 0.62, length - 0.35],
        target: [width / 2, deck + height * 0.42, 0],
      };

    case "isometric":
    default: {
      // Mais de LADO que de trás. Com o eixo Z dominando, o comprimento do
      // caminhão ia para a profundidade e o veículo encolhia no meio de um
      // quadro largo; puxando para o lado ele atravessa a tela.
      const dir = normalize([0.95, 0.44, 0.6]);
      return place(vehicleCenter, dir, fitDistance(vehicle, vehicleCenter, dir, aspect));
    }
  }
}
