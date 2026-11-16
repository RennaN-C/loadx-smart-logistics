import { memo } from "react";
import type { BoxGeometry } from "three";
import type { Box } from "./sceneGeometry";
import { WHEEL_WIDTH, type TruckShell, type Wheel } from "./truckShell";

function Panel({
  box,
  color,
  opacity = 1,
  metalness = 0.1,
  roughness = 0.7,
  geometry,
}: {
  box: Box;
  color: string;
  opacity?: number;
  metalness?: number;
  roughness?: number;
  geometry?: BoxGeometry;
}) {
  return (
    <mesh position={box.position} geometry={geometry} scale={geometry ? box.size : undefined} castShadow receiveShadow>
      {!geometry ? <boxGeometry args={box.size} /> : null}
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
        <meshStandardMaterial color="#bcc5ce" roughness={0.22} metalness={0.92} />
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
interface TruckShellMeshProps {
  readonly shell: TruckShell;
  /**
   * Some com a cabine desenhada em código, junto do para-brisa, dos
   * retrovisores e do para-choque: o modelo importado traz os quatro, e
   * deixá-los acesos daria cabine dentro de cabine e para-choque dobrado.
   *
   * O resto do caminhão continua desenhado aqui, porque o resto É derivado das
   * medidas cadastradas.
   */
  readonly hideCab?: boolean;
  /**
   * Eixo dianteiro vindo do modelo da cabine, alinhado ao arco de roda que ele
   * desenha. Vazio quando a cabine é a desenhada em código.
   */
  readonly cabWheels?: readonly Wheel[];
  readonly sharedGeometry?: BoxGeometry;
}

export const TruckShellMesh = memo(function TruckShellMesh({
  shell,
  hideCab = false,
  cabWheels = [],
  sharedGeometry,
}: TruckShellMeshProps) {
  return (
    <group>
      <Panel geometry={sharedGeometry} box={shell.chassis} color="#33373d" roughness={0.8} metalness={0.3} />
      {hideCab ? null : (
        <>
          <Panel geometry={sharedGeometry} box={shell.cab} color="#eceae4" roughness={0.35} metalness={0.15} />
          <Panel
            box={shell.windshield}
            color="#1d2733"
            opacity={0.62}
            roughness={0.08}
            metalness={0.2}
          />
          <Panel geometry={sharedGeometry} box={shell.bumper} color="#4e535a" roughness={0.6} metalness={0.35} />
        </>
      )}
      <Panel geometry={sharedGeometry} box={shell.fuelTank} color="#aeb4bc" roughness={0.22} metalness={0.9} />
      <Panel geometry={sharedGeometry} box={shell.rearGuard} color="#4e535a" roughness={0.6} metalness={0.35} />
      {/* Reflectors and tail lamps remain outside the usable cargo compartment. */}
      <Panel geometry={sharedGeometry} box={{
        position: [shell.rearGuard.position[0], shell.rearGuard.position[1], shell.rearGuard.position[2] + 0.056],
        size: [shell.rearGuard.size[0] * 0.72, 0.035, 0.012],
      }} color="#dca350" roughness={0.32} metalness={0.3} />
      {[-1, 1].map((side) => <group key={`tail-${side}`} position={[
        shell.rearGuard.position[0] + side * shell.rearGuard.size[0] * 0.43,
        shell.rearGuard.position[1] + 0.22,
        shell.rearGuard.position[2],
      ]}>
        <mesh geometry={sharedGeometry} scale={[0.2, 0.12, 0.06]}>
          {!sharedGeometry ? <boxGeometry args={[1, 1, 1]} /> : null}
          <meshStandardMaterial color="#c34d45" emissive="#6e211d" emissiveIntensity={0.3} roughness={0.3} />
        </mesh>
      </group>)}

      {shell.roofRails.map((box, index) => (
        <Panel geometry={sharedGeometry} key={`rail-${index}`} box={box} color="#9ba8b4" roughness={0.3} metalness={0.8} />
      ))}
      {shell.cornerPosts.map((box, index) => (
        <Panel geometry={sharedGeometry} key={`post-${index}`} box={box} color="#9ba8b4" roughness={0.3} metalness={0.8} />
      ))}
      {shell.doorFrame.map((box, index) => (
        <Panel geometry={sharedGeometry} key={`door-${index}`} box={box} color="#5f666f" roughness={0.5} metalness={0.5} />
      ))}
      {/* Para-lama em z negativo fica sob a cabine, e o modelo importado já
          traz o próprio arco de roda ali. O critério é a posição e não a ordem
          do array: quem manda à frente da parede de carga é a cabine. */}
      {shell.fenders
        .filter((box) => !hideCab || box.position[2] >= 0)
        .map((box, index) => (
          <Panel geometry={sharedGeometry} key={`fender-${index}`} box={box} color="#3c4046" roughness={0.75} metalness={0.2} />
        ))}
      {shell.sideSkirts.map((box, index) => (
        <Panel geometry={sharedGeometry} key={`skirt-${index}`} box={box} color="#d5d2ca" roughness={0.55} metalness={0.1} />
      ))}
      {hideCab
        ? null
        : shell.mirrors.map((box, index) => (
            <Panel geometry={sharedGeometry} key={`mirror-${index}`} box={box} color="#2f343a" roughness={0.3} metalness={0.4} />
          ))}

      {/* Mesmo critério dos para-lamas: à frente da parede de carga quem manda
          é a cabine, e o eixo dianteiro dela vem alinhado ao próprio modelo. */}
      {[...shell.wheels.filter((w) => !hideCab || w.position[2] >= 0), ...cabWheels].map((wheel) => (
        <Tyre key={`${wheel.position[0]}-${wheel.position[2]}`} wheel={wheel} />
      ))}
    </group>
  );
});
