import { useEffect, useMemo } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

interface CameraControlsProps {
  readonly target: readonly [number, number, number];
}

export function CameraControls({ target }: CameraControlsProps) {
  const camera = useThree((state) => state.camera);
  const domElement = useThree((state) => state.gl.domElement);
  const controls = useMemo(
    () => new OrbitControls(camera, domElement),
    [camera, domElement],
  );

  useEffect(() => {
    controls.enableDamping = true;
    controls.target.set(...target);
    controls.update();
    return () => controls.dispose();
  }, [controls, target]);

  useFrame(() => controls.update());
  return null;
}
