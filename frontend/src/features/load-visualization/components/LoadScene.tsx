import { Canvas } from "@react-three/fiber";
import { useEffect } from "react";
import { BackSide } from "three";

import type { PlacedItem, TruckSnapshot } from "../../load-planning/types";
import { cargoTextures, disposeCargoTextures } from "./cargoTexture";
import { CameraControls } from "./CameraControls";
import { cameraPosition, deliveryColor, deliveryTint, itemBox, truckBox } from "./sceneGeometry";
import { TruckShellMesh } from "./TruckShellMesh";
import { shellCameraPosition, truckShell } from "./truckShell";

interface VolumeProps {
  readonly item: PlacedItem;
  readonly selected: boolean;
  readonly dimmed: boolean;
  readonly realistic: boolean;
  readonly onSelect: (id: string) => void;
}

function Volume({ item, selected, dimmed, realistic, onSelect }: VolumeProps) {
  // As medidas vêm do item, JÁ ROTACIONADAS pelo backend. Volume grande é
  // grande na cena; se todos aparecem iguais, é porque foram cadastrados iguais.
  const box = itemBox(item);
  const color = deliveryColor(item.deliverySequence);
  const faces = realistic ? cargoTextures(item.productCode) : null;

  return (
    <group position={box.position}>
      <mesh
        castShadow={realistic && !dimmed}
        receiveShadow={realistic && !dimmed}
        onClick={(event) => {
          event.stopPropagation();
          onSelect(item.id);
        }}
      >
        <boxGeometry args={box.size} />
        {faces ? (
          // um material por face: fita na de cima, etiqueta na da frente
          faces.map((texture, index) => (
            <meshStandardMaterial
              key={`${item.id}-${index}`}
              attach={`material-${index}`}
              map={texture ?? undefined}
              color={selected ? "#ffffff" : deliveryTint(item.deliverySequence)}
              roughness={0.82}
              metalness={0}
              transparent={dimmed}
              opacity={dimmed ? 0.12 : 1}
            />
          ))
        ) : (
          <meshLambertMaterial
            color={selected ? "#ffffff" : color}
            transparent
            opacity={dimmed ? 0.12 : 0.92}
          />
        )}
      </mesh>

      {/* Contorno separa volumes encostados, que sem ele viram um bloco só. No
          modo realista a quina já vem do vinco da textura e da sombra, então o
          traço fica bem mais discreto para não devolver o aspecto de diagrama. */}
      <mesh>
        <boxGeometry args={[box.size[0] * 1.001, box.size[1] * 1.001, box.size[2] * 1.001]} />
        <meshBasicMaterial
          color={realistic ? "#4a3a24" : "#14181d"}
          wireframe
          transparent
          opacity={dimmed ? 0.06 : realistic ? 0.14 : 0.35}
        />
      </mesh>

      {/* Selecionado ganha uma gaiola de acento: com textura, clarear o volume
          deixou de ser sinal suficiente. */}
      {selected ? (
        <mesh>
          <boxGeometry args={[box.size[0] * 1.02, box.size[1] * 1.02, box.size[2] * 1.02]} />
          <meshBasicMaterial color="#c97a22" wireframe />
        </mesh>
      ) : null}
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
  /** Papelão texturizado e sombras; desligado volta ao esquema de cores chapadas. */
  readonly realistic: boolean;
}

export function LoadScene({
  truck,
  items,
  selectedId,
  onSelect,
  visibleIds,
  showTruck,
  realistic,
}: LoadSceneProps) {
  const box = truckBox(truck);
  const shell = truckShell(truck);
  // A carga sobe junto com o piso do baú. As coordenadas dos volumes seguem
  // intactas dentro do grupo — nenhuma conversão a mais, nenhuma chance de
  // divergir do que o backend calculou.
  const deck = showTruck ? shell.deckHeight : 0;
  const alvo: [number, number, number] = [box.position[0], box.position[1] + deck, box.position[2]];

  // As texturas vivem na GPU e são compartilhadas entre volumes do mesmo
  // produto; sem isto elas vazam ao trocar de plano de carga.
  useEffect(() => disposeCargoTextures, []);

  // A sombra precisa enquadrar o baú inteiro, senão só parte da carga projeta.
  const alcance = Math.max(box.size[0], box.size[1], box.size[2]) * 1.2;

  return (
    <Canvas
      camera={{ position: showTruck ? shellCameraPosition(truck) : cameraPosition(truck), fov: 45 }}
      shadows={realistic}
      onPointerMissed={() => onSelect(null)}
    >
      {realistic ? (
        <>
          {/* Céu por cima, chão quente por baixo: dá volume às caixas sem
              precisar de mapa de ambiente, que custaria bytes no chunk. */}
          <hemisphereLight args={["#dfe7f2", "#6b5b46", 0.85]} />
          <directionalLight
            position={[alcance * 0.8, alcance * 1.3, alcance * 0.7]}
            intensity={1.5}
            castShadow
            shadow-mapSize={[1024, 1024]}
            shadow-camera-left={-alcance}
            shadow-camera-right={alcance}
            shadow-camera-top={alcance}
            shadow-camera-bottom={-alcance}
            shadow-camera-far={alcance * 4}
            shadow-bias={-0.0012}
          />
          <directionalLight position={[-alcance, alcance * 0.5, -alcance]} intensity={0.35} />
        </>
      ) : (
        <>
          <ambientLight intensity={0.75} />
          <directionalLight position={[6, 10, 8]} intensity={1.1} />
          <directionalLight position={[-6, 4, -6]} intensity={0.35} />
        </>
      )}

      {showTruck ? <TruckShellMesh shell={shell} /> : null}

      <group position={[0, deck, 0]}>
        {/* baú: caixa vista por dentro, para não tapar a carga */}
        <mesh position={box.position} receiveShadow={realistic}>
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
            realistic={realistic}
            onSelect={onSelect}
          />
        ))}
      </group>

      <gridHelper args={[Math.max(box.size[0], box.size[2]) * 2.4, 14, "#a09b8f", "#d9d5c7"]} />
      <CameraControls target={alvo} />
    </Canvas>
  );
}
