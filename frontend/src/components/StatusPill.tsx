import type { ReactNode } from "react";

export type StatusTone = "good" | "neutral";

interface StatusPillProps {
  readonly tone: StatusTone;
  readonly children: ReactNode;
}

export function StatusPill({ tone, children }: StatusPillProps) {
  return (
    <span className={`status-pill status-pill-${tone}`}>
      <span className="status-pill-dot" aria-hidden="true" />
      <span>{children}</span>
    </span>
  );
}
