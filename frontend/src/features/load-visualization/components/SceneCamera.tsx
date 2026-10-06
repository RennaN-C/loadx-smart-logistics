import { useThree } from "@react-three/fiber";

import type { TruckSnapshot } from "../../load-planning/types";
import { CameraControls } from "./CameraControls";
import { viewCamera, type ViewPreset } from "./cameraViews";

interface SceneCameraProps {
  readonly truck: TruckSnapshot;
  readonly view: ViewPreset;
  readonly deck: number;
}

/**
 * Enquadra a vista escolhida com a proporção REAL do canvas.
 *
 * Mora dentro do `Canvas` porque é o único lugar que conhece esse tamanho. Sem
 * ele a distância vinha de uma proporção suposta, e num painel largo o
 * caminhão ficava pequeno no meio de um fundo vazio.
 *
 * `size` muda em redimensionamento de verdade, não a cada quadro, então a
 * câmera não volta ao preset enquanto a pessoa gira a cena.
 */
export function SceneCamera({ truck, view, deck }: SceneCameraProps) {
  const size = useThree((state) => state.size);
  const aspect = size.height > 0 ? size.width / size.height : 1;

  const { position, target } = viewCamera(truck, view, deck, aspect);

  return <CameraControls target={target} position={position} />;
}
