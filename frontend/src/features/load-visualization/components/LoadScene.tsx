import { Canvas } from "@react-three/fiber";
import { BackSide } from "three";

import type { PlacedItem, TruckSnapshot } from "../../load-planning/types";
import { CameraControls } from "./CameraControls";
import { cameraPosition, deliveryColor, itemBox, truckBox } from "./sceneGeometry";
import { TruckShellMesh } from "./TruckShellMesh";
import { shellCameraPosition, truckShell } from "./truckShell";

interface VolumeProps {
  readonly item: PlacedItem;
  readonly selected: boolean;
  readonly dimmed: boolean;
  readonly onSelect: (id: string) => void;
}

function Volume({ item, selected, dimmed, onSelect }: VolumeProps) {
  const box = itemBox(item);
  const color = deliveryColor(item.deliverySequence);

  return (
    <group position={box.position}>
      <mesh
        onClick={(event) => {
          event.stopPropagation();
          onSelect(item.id);
        }}
      >
        <boxGeometry args={box.size} />
        <meshLambertMaterial
          color={selected ? "#ffffff" : color}
          transparent
          opacity={dimmed ? 0.12 : 0.92}
        />
      </mesh>
      {/* contorno separa volumes encostados, que sem ele viram um bloco só */}
      <mesh>
        <boxGeometry args={[box.size[0] * 1.001, box.size[1] * 1.001, box.size[2] * 1.001]} />
        <meshBasicMaterial color="#14181d" wireframe transparent opacity={dimmed ? 0.06 : 0.35} />
      </mesh>
    </group>
  );
}

export interface LoadSceneProps {
  readonly truck: TruckSnapshot;
  readonly items: readonly PlacedItem[];
  readonly selectedId: string | null;
  readonly onSelect: (id: string | null) => void;
  /** Itens visíveis; usado pela animação de carregamento (OC33). */
  readonly visibleIds: ReadonlySet<string> | null;
  /** Exterior do caminhão ligado; desligado mostra só o baú e a carga. */
  readonly showTruck: boolean;
}

export function LoadScene({ truck, items, selectedId, onSelect, visibleIds, showTruck }: LoadSceneProps) {
  const box = truckBox(truck);
  const shell = truckShell(truck);
  // A carga sobe junto com o piso do baú. As coordenadas dos volumes seguem
  // intactas dentro do grupo — nenhuma conversão a mais, nenhuma chance de
  // divergir do que o backend calculou.
  const deck = showTruck ? shell.deckHeight : 0;
  const alvo: [number, number, number] = [box.position[0], box.position[1] + deck, box.position[2]];

  return (
    <Canvas
      camera={{ position: showTruck ? shellCameraPosition(truck) : cameraPosition(truck), fov: 45 }}
      onPointerMissed={() => onSelect(null)}
    >
      <ambientLight intensity={0.75} />
      <directionalLight position={[6, 10, 8]} intensity={1.1} />
      <directionalLight position={[-6, 4, -6]} intensity={0.35} />

      {showTruck ? <TruckShellMesh shell={shell} /> : null}

      <group position={[0, deck, 0]}>
        {/* baú: caixa vista por dentro, para não tapar a carga */}
        <mesh position={box.position}>
          <boxGeometry args={box.size} />
          <meshLambertMaterial color="#d9d5c7" side={BackSide} transparent opacity={0.35} />
        </mesh>
        <mesh position={box.position}>
          <boxGeometry args={box.size} />
          <meshBasicMaterial color="#5f5b52" wireframe />
        </mesh>

        {items.map((item) => (
          <Volume
            key={item.id}
            item={item}
            selected={item.id === selectedId}
            dimmed={visibleIds !== null && !visibleIds.has(item.id)}
            onSelect={onSelect}
          />
        ))}
      </group>

      <gridHelper args={[Math.max(box.size[0], box.size[2]) * 2.4, 14, "#a09b8f", "#d9d5c7"]} />
      <CameraControls target={alvo} />
    </Canvas>
  );
}
