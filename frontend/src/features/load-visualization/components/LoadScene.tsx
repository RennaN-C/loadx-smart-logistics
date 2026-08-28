import { Canvas } from "@react-three/fiber";
import { useMemo } from "react";
import { BackSide, BoxGeometry } from "three";

import type { PlacedItem, TruckSnapshot } from "../../load-planning/types";
import { cargoTextures } from "./cargoTexture";
import { CameraControls } from "./CameraControls";
import { cameraPosition, deliveryColor, itemBox, truckBox } from "./sceneGeometry";
import { classifyProduct } from "./productKind";
import { TruckShellMesh } from "./TruckShellMesh";
import { shellCameraPosition, truckShell } from "./truckShell";

/** Quanto o desenho do baú afunda para não coincidir com a base dos volumes. */
const SHELL_SINK = 0.012;

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
  // O nome cadastrado decide a aparência: "TV 50" vira tela, não caixa.
  const faces = realistic ? cargoTextures(classifyProduct(item.productName)) : null;
  // uma geometria por volume, reaproveitada entre quadros
  const geometria = useMemo(
    () => new BoxGeometry(box.size[0], box.size[1], box.size[2]),
    [box.size],
  );

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
          // um material por face: a frente do produto olha para a porta do baú
          faces.map((texture, index) => (
            <meshStandardMaterial
              key={`${item.id}-${index}`}
              attach={`material-${index}`}
              map={texture ?? undefined}
              // Sem `color`: tingir deixaria a TV laranja, e TV laranja não é
              // TV. A cor da entrega migrou para a aresta, logo abaixo.
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

      {/* Contorno: separa volumes encostados, que sem ele viram um bloco só.
          No modo realista ele ganha a COR DA ENTREGA — é assim que o
          agrupamento sobrevive sem pintar o produto, que precisa manter as
          cores dele para ser reconhecido.

          São as 12 ARESTAS, não uma caixa em modo arame. A caixa antiga ficava
          0,1% maior que o volume, o que dá dois décimos de milímetro num volume
          de 40 cm — dentro da margem de erro do buffer de profundidade, ou seja,
          piscava. Aresta não tem superfície e não entra nessa disputa. */}
      <lineSegments>
        <edgesGeometry args={[geometria]} />
        <lineBasicMaterial
          color={realistic ? color : "#14181d"}
          transparent
          opacity={dimmed ? 0.06 : realistic ? 0.75 : 0.35}
        />
      </lineSegments>

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
  /** Superfície do produto e sombras; desligado volta às cores chapadas. */
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

  // A sombra precisa enquadrar o baú inteiro, senão só parte da carga projeta.
  const alcance = Math.max(box.size[0], box.size[1], box.size[2]) * 1.2;

  // Reaproveitada entre renders: criar geometria a cada quadro vaza memória de GPU.
  const caixaDoBau = useMemo(
    () => new BoxGeometry(box.size[0], box.size[1], box.size[2]),
    [box.size],
  );

  return (
    <Canvas
      camera={{
        position: showTruck ? shellCameraPosition(truck) : cameraPosition(truck),
        fov: 45,
        // O padrão vai de 0,1 a 1000 e joga fora precisão de profundidade num
        // cenário de ~20 m. Apertar o alcance é o que dá margem para superfícies
        // próximas não brigarem.
        near: 0.05,
        far: 200,
      }}
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
        {/* Baú: caixa vista por dentro, para não tapar a carga.
            Afundado alguns milímetros de propósito. Com o piso exatamente na
            altura em que os volumes se apoiam, as duas superfícies disputavam o
            mesmo valor de profundidade e a placa alternava entre elas a cada
            quadro — o piso piscava ao girar a câmera. Os volumes NÃO se movem:
            quem desce é só o desenho do baú. */}
        <mesh position={[box.position[0], box.position[1] - SHELL_SINK, box.position[2]]} receiveShadow={realistic}>
          <boxGeometry args={box.size} />
          <meshLambertMaterial color="#d9d5c7" side={BackSide} transparent opacity={0.35} />
        </mesh>
        {/* Só as 12 arestas, em vez de uma segunda caixa em modo arame. A caixa
            duplicada era coplanar com a de cima — mesma briga —, e o arame ainda
            desenhava as diagonais de cada face, que não existem no baú. */}
        <lineSegments position={box.position}>
          <edgesGeometry args={[caixaDoBau]} />
          <lineBasicMaterial color="#5f5b52" />
        </lineSegments>

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
