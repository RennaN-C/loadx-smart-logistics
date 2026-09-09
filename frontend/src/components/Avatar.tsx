import { initials } from "./initials";

interface AvatarProps {
  readonly name: string;
  /** Lado do quadrado, em pixels. A letra acompanha. */
  readonly size?: number;
}

/**
 * Âncora visual para uma pessoa ou empresa. Decorativo de propósito: onde ele
 * aparece o nome está escrito ao lado, então lê-lo de novo só atrapalharia.
 */
export function Avatar({ name, size = 32 }: AvatarProps) {
  return (
    <span
      className="avatar"
      style={{ width: size, height: size, fontSize: Math.round(size * 0.36) }}
      aria-hidden="true"
    >
      {initials(name)}
    </span>
  );
}
