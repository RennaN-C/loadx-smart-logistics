import "./Modal.css";
import { useDialogLifecycle } from "./useDialogLifecycle";
import { useId, useRef, type ReactNode } from "react";

interface ModalProps {
  readonly title: string;
  readonly active?: boolean;
  readonly subtitle?: string;
  readonly onClose: () => void;
  readonly children: ReactNode;
}

export function Modal({ title, subtitle, onClose, children, active = true }: ModalProps) {
  const titleId = useId();

  const dialogRef = useRef<HTMLDivElement>(null);
  useDialogLifecycle(dialogRef, active, onClose);

  return (
    <div className="modal-overlay" hidden={!active}>
      <button type="button" className="modal-backdrop" tabIndex={-1} aria-label="Fechar" onClick={onClose} />
      <div ref={dialogRef} tabIndex={-1} className="modal-dialog" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <header className="modal-header">
          <h2 id={titleId}>{title}</h2>
          {subtitle ? <p className="modal-subtitle">{subtitle}</p> : null}
        </header>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}
