import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { memo, useEffect, useLayoutEffect, useMemo, useRef, useSyncExternalStore, type RefObject } from "react";
import { BackSide, type Group } from "three";

import type { PlacedItem, TruckSnapshot } from "../../load-planning/types";
import { useTruckCabModel } from "../hooks/useTruckCabModel";
import { Backdrop } from "./Backdrop";
import { cargoTextures, kraftVariant } from "./cargoTexture";
import { viewCamera, type ViewPreset } from "./cameraViews";
import { classifyProduct } from "./productKind";
import { SceneCamera } from "./SceneCamera";
import { vehicleBounds } from "./sceneBackdrop";
import { deliveryColor, itemBox, truckBox } from "./sceneGeometry";
import { createSceneResources, type SceneResources } from "./sceneResources";
import { TruckCabMesh } from "./TruckCabMesh";
import { cabFrontWheels } from "./truckCabModel";
import { truckShell } from "./truckShell";
import { TruckShellMesh } from "./TruckShellMesh";

const SHELL_SINK = 0.012;
const ENTRY_SECONDS = 0.55;
const ENTRY_MARGIN = 1.4;

function subscribeReducedMotion(listener: () => void) {
  const query = window.matchMedia("(prefers-reduced-motion: reduce)");
  query.addEventListener("change", listener);
  return () => query.removeEventListener("change", listener);
}
function reducedMotionSnapshot() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function EntryMotion({ group, finalZ, doorZ }: {
  readonly group: RefObject<Group>;
  readonly finalZ: number;
  readonly doorZ: number;
}) {
  const invalidate = useThree((state) => state.invalidate);
  const progress = useRef(0);
  useLayoutEffect(() => {
    const node = group.current;
    progress.current = 0;
    if (node) node.position.z = doorZ + ENTRY_MARGIN;
    invalidate();
    return () => {
      if (node) node.position.z = finalZ;
      invalidate();
    };
  }, [group, finalZ, doorZ, invalidate]);

  useFrame((_, delta) => {
    if (!group.current || progress.current >= 1) return;
    // A demand renderer can resume after being idle; don't consume idle time.
    progress.current = Math.min(1, progress.current + Math.min(delta, 0.05) / ENTRY_SECONDS);
    const eased = 1 - (1 - progress.current) ** 3;
    group.current.position.z = doorZ + ENTRY_MARGIN + (finalZ - doorZ - ENTRY_MARGIN) * eased;
    if (progress.current < 1) invalidate();
  });
  return null;
}

interface VolumeProps {
  readonly item: PlacedItem;
  readonly selected: boolean;
  readonly dimmed: boolean;
  readonly realistic: boolean;
  readonly fragile: boolean;
  readonly entering: boolean;
  readonly reducedMotion: boolean;
  readonly doorZ: number;
  readonly onSelect: (id: string) => void;
  readonly resources: SceneResources;
}

const Volume = memo(function Volume({ item, selected, dimmed, realistic, fragile, entering,
  reducedMotion, doorZ, onSelect, resources }: VolumeProps) {
  const box = itemBox(item);
  const group = useRef<Group>(null);
  const color = deliveryColor(item.deliverySequence);
  const faces = realistic ? cargoTextures(classifyProduct(item.productName), kraftVariant(item.productCode)) : null;

  return (
    <group ref={group} position={box.position} scale={box.size}>
      {entering && !reducedMotion ? <EntryMotion group={group} finalZ={box.position[2]} doorZ={doorZ} /> : null}
      <mesh geometry={resources.unitBox}
        material={faces ? resources.cargoMaterials(faces, dimmed) : resources.flatCargoMaterial(color, dimmed)}
        castShadow={realistic && !dimmed} receiveShadow={realistic && !dimmed}
        onClick={(event) => { event.stopPropagation(); onSelect(item.id); }}
        onPointerOver={(event) => {
          const canvas = event.nativeEvent.target;
          if (canvas instanceof HTMLCanvasElement) canvas.style.cursor = "pointer";
        }}
        onPointerOut={(event) => {
          const canvas = event.nativeEvent.target;
          if (canvas instanceof HTMLCanvasElement) canvas.style.cursor = "";
        }} />
      <lineSegments geometry={resources.unitEdges}>
        <lineBasicMaterial color={fragile ? "#e0685a" : color} transparent
          opacity={dimmed ? 0.07 : selected || fragile ? 1 : 0.68} />
      </lineSegments>
      {selected ? <lineSegments geometry={resources.unitEdges} scale={[1.012, 1.012, 1.012]} renderOrder={3}>
        <lineBasicMaterial color="#f0ad55" depthTest={false} transparent opacity={0.95} />
      </lineSegments> : null}
    </group>
  );
});

export interface LoadSceneProps {
  readonly truck: TruckSnapshot;
  readonly items: readonly PlacedItem[];
  readonly selectedId: string | null;
  readonly onSelect: (id: string | null) => void;
  readonly visibleIds: ReadonlySet<string> | null;
  readonly showTruck: boolean;
  readonly realistic: boolean;
  readonly view: ViewPreset;
  readonly highlightFragile: boolean;
  readonly enteringId: string | null;
  readonly resetToken?: number;
}

function SceneContent({ truck, items, selectedId, onSelect, visibleIds, showTruck, realistic,
  view, highlightFragile, enteringId, resetToken = 0 }: LoadSceneProps) {
  const resources = useMemo(createSceneResources, []);
  useEffect(() => () => resources.dispose(), [resources]);
  const reducedMotion = useSyncExternalStore(subscribeReducedMotion, reducedMotionSnapshot, () => true);
  const box = truckBox(truck);
  const shell = useMemo(() => truckShell(truck), [truck]);
  const cabModel = useTruckCabModel();
  const cabWheels = useMemo(() => cabModel ? cabFrontWheels(truck) : [], [cabModel, truck]);
  const deck = showTruck ? shell.deckHeight : 0;
  const bounds = vehicleBounds(truck, showTruck);
  const reach = Math.max(...box.size) * 1.2;
  const cx = box.position[0];

  return <>
    <Backdrop bounds={bounds} realistic={realistic} />
    <hemisphereLight args={["#e4edf5", "#5a5046", realistic ? 1.15 : 1.4]} />
    <directionalLight position={[reach * 0.8, reach * 1.3, reach * 0.7]} intensity={realistic ? 1.8 : 1.1}
      castShadow={realistic} shadow-mapSize={items.length > 300 ? [1024, 1024] : [2048, 2048]}
      shadow-camera-left={-reach} shadow-camera-right={reach} shadow-camera-top={reach}
      shadow-camera-bottom={-reach} shadow-camera-far={reach * 4} shadow-bias={-0.0006} shadow-normalBias={0.018} />
    <directionalLight position={[-reach, reach * 0.65, -reach]} intensity={0.55} color="#c2d8ee" />
    <directionalLight position={[cx, reach * 0.5, -reach * 0.8]} intensity={0.32} color="#f2d2a5" />
    {showTruck ? <TruckShellMesh shell={shell} hideCab={cabModel !== null}
      sharedGeometry={resources.unitBox} cabWheels={cabWheels} /> : null}
    {showTruck && cabModel ? <TruckCabMesh model={cabModel} truck={truck} /> : null}

    <group position={[0, deck, 0]}>
      <mesh geometry={resources.unitBox} position={[box.position[0], -0.055, box.position[2]]}
        scale={[box.size[0], 0.05, box.size[2]]} receiveShadow={realistic}>
        <meshStandardMaterial color="#8e9aa3" roughness={0.78} metalness={0.22} />
      </mesh>
      <mesh geometry={resources.unitBox} position={[box.position[0], box.position[1] - SHELL_SINK, box.position[2]]}
        scale={box.size}>
        <meshLambertMaterial color="#c8d6df" side={BackSide} transparent opacity={0.15} depthWrite={false} />
      </mesh>
      <lineSegments geometry={resources.unitEdges} position={box.position} scale={box.size}>
        <lineBasicMaterial color="#8c9cab" transparent opacity={0.78} />
      </lineSegments>
      {items.map((item) => <Volume key={item.id} item={item} selected={item.id === selectedId}
        dimmed={visibleIds !== null && !visibleIds.has(item.id)} realistic={realistic}
        fragile={highlightFragile && item.fragile} entering={item.id === enteringId}
        reducedMotion={reducedMotion} doorZ={box.size[2]} onSelect={onSelect} resources={resources} />)}
    </group>
    <SceneCamera truck={truck} view={view} deck={deck} resetToken={resetToken} />
  </>;
}

export function LoadScene(props: LoadSceneProps) {
  const deck = props.showTruck ? truckShell(props.truck).deckHeight : 0;
  const camera = viewCamera(props.truck, props.view, deck);
  return <Canvas frameloop="demand" dpr={[1, 1.5]} shadows={props.realistic}
    camera={{ position: camera.position, fov: 45, near: 0.05, far: 200 }}
    onPointerMissed={() => props.onSelect(null)}
    role="img" aria-label={`Carga em 3D do caminhão ${props.truck.plate}`}>
    <SceneContent {...props} />
  </Canvas>;
}
