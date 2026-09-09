import type { Box } from "./sceneGeometry";
import { WHEEL_WIDTH, type TruckShell, type Wheel } from "./truckShell";

function Panel({
  box,
  color,
  opacity = 1,
  metalness = 0.1,
  roughness = 0.7,
}: {
  box: Box;
  color: string;
  opacity?: number;
  metalness?: number;
  roughness?: number;
}) {
  return (
    <mesh position={box.position} castShadow receiveShadow>
      <boxGeometry args={box.size} />
      <meshStandardMaterial
        color={color}
        metalness={metalness}
        roughness={roughness}
        transparent={opacity < 1}
        opacity={opacity}
      />
    </mesh>
  );
}

function Tyre({ wheel }: { wheel: Wheel }) {
  return (
    // cilindro nasce em pé no Three.js; girar em Z deita no eixo do caminhão
    <group position={wheel.position} rotation={[0, 0, Math.PI / 2]}>
      <mesh castShadow>
        <cylinderGeometry args={[wheel.radius, wheel.radius, WHEEL_WIDTH, 24]} />
        <meshStandardMaterial color="#23272d" roughness={0.95} metalness={0} />
      </mesh>
      {/* aro */}
      <mesh>
        <cylinderGeometry args={[wheel.radius * 0.52, wheel.radius * 0.52, WHEEL_WIDTH + 0.02, 20]} />
        <meshStandardMaterial color="#9aa0a8" roughness={0.35} metalness={0.75} />
      </mesh>
      {/* cubo central: o detalhe que faz a roda parecer roda e não disco */}
      <mesh>
        <cylinderGeometry args={[wheel.radius * 0.18, wheel.radius * 0.18, WHEEL_WIDTH + 0.05, 12]} />
        <meshStandardMaterial color="#5e646c" roughness={0.4} metalness={0.6} />
      </mesh>
    </group>
  );
}

/**
 * Exterior do caminhão desenhado a partir das medidas cadastradas.
 *
 * A estrutura do baú — longarinas, montantes, batente da porta — não é enfeite:
 * sem ela o baú lê como caixa de papelão gigante, por mais correta que a medida
 * esteja. Os perfis ficam num tom mais escuro que a lataria, que é como se
 * distinguem num caminhão real.
 *
 * As cores continuam neutras de propósito: quem tem que puxar o olho é a carga.
 */
export function TruckShellMesh({ shell }: { shell: TruckShell }) {
  return (
    <group>
      <Panel box={shell.chassis} color="#33373d" roughness={0.8} metalness={0.3} />
      <Panel box={shell.cab} color="#eceae4" roughness={0.35} metalness={0.15} />
      <Panel box={shell.windshield} color="#1d2733" opacity={0.62} roughness={0.08} metalness={0.2} />
      <Panel box={shell.bumper} color="#4e535a" roughness={0.6} metalness={0.35} />
      <Panel box={shell.fuelTank} color="#aeb4bc" roughness={0.28} metalness={0.85} />
      <Panel box={shell.rearGuard} color="#4e535a" roughness={0.6} metalness={0.35} />

      {shell.roofRails.map((box, index) => (
        <Panel key={`rail-${index}`} box={box} color="#6f7681" roughness={0.5} metalness={0.5} />
      ))}
      {shell.cornerPosts.map((box, index) => (
        <Panel key={`post-${index}`} box={box} color="#6f7681" roughness={0.5} metalness={0.5} />
      ))}
      {shell.doorFrame.map((box, index) => (
        <Panel key={`door-${index}`} box={box} color="#5f666f" roughness={0.5} metalness={0.5} />
      ))}
      {shell.fenders.map((box, index) => (
        <Panel key={`fender-${index}`} box={box} color="#3c4046" roughness={0.75} metalness={0.2} />
      ))}
      {shell.sideSkirts.map((box, index) => (
        <Panel key={`skirt-${index}`} box={box} color="#d5d2ca" roughness={0.55} metalness={0.1} />
      ))}
      {shell.mirrors.map((box, index) => (
        <Panel key={`mirror-${index}`} box={box} color="#2f343a" roughness={0.3} metalness={0.4} />
      ))}

      {shell.wheels.map((wheel) => (
        <Tyre key={`${wheel.position[0]}-${wheel.position[2]}`} wheel={wheel} />
      ))}
    </group>
  );
}
