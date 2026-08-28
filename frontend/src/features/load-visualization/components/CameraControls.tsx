import { useEffect, useMemo } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

interface CameraControlsProps {
  readonly target: readonly [number, number, number];
  /** Para onde a câmera pula quando a vista muda. */
  readonly position: readonly [number, number, number];
}

export function CameraControls({ target, position }: CameraControlsProps) {
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

  // Mesma desestruturação em números do alvo: só reposiciona quando a vista
  // muda de verdade, senão a câmera saltaria de volta a cada render e o usuário
  // não conseguiria girar.
  const [px, py, pz] = position;
  useEffect(() => {
    camera.position.set(px, py, pz);
    controls.update();
  }, [camera, controls, px, py, pz]);

  useFrame(() => controls.update());
  return null;
}
