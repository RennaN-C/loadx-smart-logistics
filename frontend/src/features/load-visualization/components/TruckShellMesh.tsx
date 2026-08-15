import type { Box } from "./sceneGeometry";
import { WHEEL_WIDTH, type TruckShell, type Wheel } from "./truckShell";

function Panel({ box, color, opacity = 1 }: { box: Box; color: string; opacity?: number }) {
  return (
    <mesh position={box.position}>
      <boxGeometry args={box.size} />
      <meshLambertMaterial color={color} transparent={opacity < 1} opacity={opacity} />
    </mesh>
  );
}

function Tyre({ wheel }: { wheel: Wheel }) {
  return (
    // cilindro nasce em pé no Three.js; girar em Z deita no eixo do caminhão
    <group position={wheel.position} rotation={[0, 0, Math.PI / 2]}>
      <mesh>
        <cylinderGeometry args={[wheel.radius, wheel.radius, WHEEL_WIDTH, 20]} />
        <meshLambertMaterial color="#2a2f36" />
      </mesh>
      <mesh>
        <cylinderGeometry args={[wheel.radius * 0.5, wheel.radius * 0.5, WHEEL_WIDTH + 0.02, 16]} />
        <meshLambertMaterial color="#8d8577" />
      </mesh>
    </group>
  );
}

/**
 * Exterior do caminhão desenhado a partir das medidas cadastradas.
 * Fica atrás da carga na leitura: cores neutras e cabine sem brilho, para o
 * olho continuar indo nos volumes coloridos.
 */
export function TruckShellMesh({ shell }: { shell: TruckShell }) {
  return (
    <group>
      <Panel box={shell.chassis} color="#3d4149" />
      <Panel box={shell.cab} color="#e8e4da" />
      <Panel box={shell.windshield} color="#1d2733" opacity={0.72} />
      <Panel box={shell.bumper} color="#5f5b52" />
      {shell.wheels.map((wheel) => (
        <Tyre key={`${wheel.position[0]}-${wheel.position[2]}`} wheel={wheel} />
      ))}
    </group>
  );
}
