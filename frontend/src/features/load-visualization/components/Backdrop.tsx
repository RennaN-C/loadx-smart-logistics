import { useEffect, useMemo } from "react";
import { useThree } from "@react-three/fiber";
import { Color, DoubleSide } from "three";

import { useDarkScheme } from "../hooks/useDarkScheme";
import { backdropPalette, skyTexture, type VehicleBounds } from "./sceneBackdrop";

interface BackdropProps {
  readonly bounds: VehicleBounds;
  readonly realistic: boolean;
}

/**
 * Céu, chão e grade — o cenário em volta do caminhão.
 *
 * A grade é centrada no VEÍCULO e não na origem. A origem é a parede frontal
 * da carga, não o centro de nada: o baú cresce para z positivo e a cabine ocupa
 * z negativo, então uma grade centrada em zero nascia torta em relação ao
 * caminhão por um valor que mudava com o comprimento do baú.
 *
 * As células têm 1 metro. Grade decorativa só enche o fundo; com passo
 * conhecido ela passa a dizer tamanho, que é justamente o assunto da tela.
 */
export function Backdrop({ bounds, realistic }: BackdropProps) {
  const scene = useThree((state) => state.scene);
  const dark = useDarkScheme();
  const palette = useMemo(() => backdropPalette(dark), [dark]);

  const [cx, , cz] = bounds.center;
  const alcance = Math.max(bounds.spanX, bounds.spanZ);

  useEffect(() => {
    const ceu = skyTexture(palette);
    // Sem canvas (jsdom) fica a cor lisa do horizonte: ainda assim melhor que
    // o preto da página aparecendo por trás.
    scene.background = ceu ?? new Color(palette.horizon);

    return () => {
      scene.background = null;
      ceu?.dispose();
    };
  }, [scene, palette]);

  return (
    <>
      {/* Começa BEM depois do caminhão: névoa sobre a carga lavaria justamente
          o que a tela existe para mostrar. Fecha na cor do horizonte, que é o
          que dissolve a grade em vez de deixá-la terminar num corte reto. */}
      <fog attach="fog" args={[palette.horizon, alcance * 2.2, alcance * 7]} />

      <mesh
        position={[cx, 0, cz]}
        rotation={[-Math.PI / 2, 0, 0]}
        receiveShadow={realistic}
      >
        {/* Enorme de propósito. Num plano apenas grande a BORDA dele aparece
            contra o céu como uma diagonal no alto do quadro — foi o que
            apareceu no primeiro teste. Com esta medida a borda cai muito além
            da névoa, e o chão termina onde deve: no horizonte. */}
        <planeGeometry args={[alcance * 60, alcance * 60]} />
        <meshStandardMaterial color={palette.ground} roughness={0.95} metalness={0} side={DoubleSide} />
      </mesh>

      {/* Levantada meio centímetro do chão: coplanar com ele, as duas
          superfícies disputariam o mesmo valor de profundidade e a grade
          piscaria ao girar a câmera — o mesmo defeito já corrigido no piso do
          baú e na frente do caminhão. */}
      <gridHelper
        position={[cx, 0.005, cz]}
        args={[
          Math.ceil(alcance * 2.2),
          Math.ceil(alcance * 2.2),
          palette.gridEdge,
          palette.gridLine,
        ]}
      />
    </>
  );
}
