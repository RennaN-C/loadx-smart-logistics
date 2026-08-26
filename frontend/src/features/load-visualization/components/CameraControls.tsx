import { useEffect, useMemo } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

interface CameraControlsProps {
  readonly target: readonly [number, number, number];
}

export function CameraControls({ target }: CameraControlsProps) {
  const camera = useThree((state) => state.camera);
  const domElement = useThree((state) => state.gl.domElement);
  const controls = useMemo(() => new OrbitControls(camera, domElement), [camera, domElement]);

  /**
   * O descarte acompanha o OBJETO, não o alvo.
   *
   * Amarrar isto ao `target` matava os controles: o alvo é um array novo a cada
   * render, então o efeito reexecutava e chamava `dispose()`, que remove os
   * ouvintes do canvas. O `useMemo` não recriava o objeto, e a cena ficava com
   * controles mortos — não girava mais, e a roda do mouse passava a rolar a
   * página em vez de aproximar.
   */
  useEffect(() => {
    controls.enableDamping = true;
    return () => controls.dispose();
  }, [controls]);

  // Desestruturado em números: assim o efeito só roda quando o alvo REALMENTE
  // muda de lugar, e não toda vez que o array é remontado.
  const [x, y, z] = target;
  useEffect(() => {
    controls.target.set(x, y, z);
    controls.update();
  }, [controls, x, y, z]);

  useFrame(() => controls.update());
  return null;
}
