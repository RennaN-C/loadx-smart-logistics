import { useEffect, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

interface CameraControlsProps {
  readonly target: readonly [number, number, number];
  readonly position: readonly [number, number, number];
  readonly resetToken?: number;
}

export function CameraControls({ target, position, resetToken = 0 }: CameraControlsProps) {
  const camera = useThree((state) => state.camera);
  const domElement = useThree((state) => state.gl.domElement);
  const invalidate = useThree((state) => state.invalidate);
  const controls = useRef<OrbitControls | null>(null);

  // Construct/dispose together so StrictMode can reconnect the listeners safely.
  useEffect(() => {
    const orbit = new OrbitControls(camera, domElement);
    orbit.enableDamping = true;
    orbit.dampingFactor = 0.12;
    orbit.screenSpacePanning = true;
    orbit.minDistance = 0.15;
    orbit.maxPolarAngle = Math.PI / 2;
    const requestFrame = () => invalidate();
    orbit.addEventListener("change", requestFrame);
    controls.current = orbit;
    invalidate();
    return () => {
      orbit.removeEventListener("change", requestFrame);
      orbit.dispose();
      controls.current = null;
    };
  }, [camera, domElement, invalidate]);

  const [x, y, z] = target;
  const [px, py, pz] = position;
  useEffect(() => {
    const orbit = controls.current;
    if (!orbit) return;
    orbit.enableDamping = false;
    orbit.update();
    orbit.target.set(x, y, z);
    camera.position.set(px, py, pz);
    orbit.maxDistance = Math.max(10, Math.hypot(px - x, py - y, pz - z) * 8);
    orbit.update();
    orbit.enableDamping = true;
    invalidate();
  }, [camera, invalidate, x, y, z, px, py, pz, resetToken]);

  // Damping emits change, scheduling another frame only while movement lasts.
  useFrame(() => controls.current?.update());
  return null;
}
