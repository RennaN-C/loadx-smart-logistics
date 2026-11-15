import { useEffect } from "react";
import { useThree } from "@react-three/fiber";
import { PMREMGenerator } from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";

/** Baked studio reflections: no network assets or per-frame reflection pass. */
export function StudioEnvironment() {
  const { gl, scene, invalidate } = useThree();
  useEffect(() => {
    const previous = scene.environment;
    const previousIntensity = scene.environmentIntensity;
    const room = new RoomEnvironment();
    const generator = new PMREMGenerator(gl);
    const target = generator.fromScene(room, 0.04, 0.1, 100);
    room.dispose();
    generator.dispose();
    scene.environment = target.texture;
    scene.environmentIntensity = 0.28;
    invalidate();
    return () => {
      scene.environment = previous;
      scene.environmentIntensity = previousIntensity;
      target.dispose();
      invalidate();
    };
  }, [gl, scene, invalidate]);
  return null;
}
