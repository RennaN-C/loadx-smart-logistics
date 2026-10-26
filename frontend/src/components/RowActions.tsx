import { useRef, type ReactNode } from "react";

/** Native disclosure keeps row actions available to pointer and keyboard users. */
export function RowActions({ label, children }: { readonly label: string; readonly children: ReactNode }) {
  const ref = useRef<HTMLDetailsElement>(null);
  return <details className="row-actions" name="registry-row-actions" ref={ref} onKeyDown={(event) => {
    if (event.key === "Escape" && ref.current?.open) {
      event.preventDefault();
      ref.current.open = false;
      ref.current.querySelector("summary")?.focus();
    }
  }}>
    <summary aria-label={label} title={label}><span aria-hidden="true">⋮</span><span className="sr-only">{label}</span></summary>
    <div className="row-actions-content">{children}</div>
  </details>;
}
