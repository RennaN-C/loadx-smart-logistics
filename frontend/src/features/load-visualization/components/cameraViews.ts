import type { TruckSnapshot } from "../../load-planning/types";
import { SCENE_SCALE } from "./sceneGeometry";
import { CAB_LENGTH, DECK_HEIGHT } from "./truckShell";

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

/**
 * `deck` é o quanto a carga está levantada do chão — zero quando o exterior do
 * caminhão está desligado. Sem ele, as vistas mirariam o vazio abaixo do baú.
 */
export function viewCamera(truck: TruckSnapshot, preset: ViewPreset, deck: number): CameraView {
  const width = truck.widthCm * SCENE_SCALE;
  const height = truck.heightCm * SCENE_SCALE;
  const length = truck.lengthCm * SCENE_SCALE;

  const cx = width / 2;
  const cy = deck + height / 2;
  const cz = length / 2;
  const center: [number, number, number] = [cx, cy, cz];

  // Alcance considera o caminhão inteiro, cabine incluída: sem isso a vista
  // lateral de um baú curto cortaria a cabine fora do quadro.
  const reach = Math.max(width, height, length + CAB_LENGTH);

  switch (preset) {
    case "side":
      // de fora da lateral direita, na altura do meio da carga
      return { position: [cx + reach * 1.15, deck + height * 0.55, cz], target: center };

    case "top":
      // de cima, ligeiramente puxada para trás para o teto não achatar tudo
      return { position: [cx, deck + height + reach * 1.05, cz + 0.01], target: center };

    case "rear":
      // atrás do baú, na altura de quem abre a porta
      return { position: [cx, DECK_HEIGHT + height * 0.5, length + reach * 0.85], target: center };

    case "inside":
      // Dentro do baú, junto à porta, olhando para o fundo. A mira vai para a
      // parede da frente — é a única vista que não aponta para o centro.
      return {
        position: [cx, deck + height * 0.62, length - 0.35],
        target: [cx, deck + height * 0.42, 0],
      };

    case "isometric":
    default:
      return {
        position: [cx + reach * 0.62, deck + height + reach * 0.42, length + reach * 0.5],
        target: center,
      };
  }
}
