import type { Group } from "three";

import type { TruckSnapshot } from "../../load-planning/types";
import { cabPlacement } from "./truckCabModel";

interface TruckCabMeshProps {
  readonly model: Group;
  readonly truck: TruckSnapshot;
}

export function TruckCabMesh({ model, truck }: TruckCabMeshProps) {
  const { scale, position, rotationY } = cabPlacement(truck);

  return (
    <group position={position} rotation={[0, rotationY, 0]} scale={scale}>
      <primitive object={model} />
    </group>
  );
}
