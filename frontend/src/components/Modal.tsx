import { useEffect, useId, type ReactNode } from "react";

interface ModalProps {
  readonly title: string;
  readonly subtitle?: string;
  readonly onClose: () => void;
  readonly children: ReactNode;
}

export function Modal({ title, subtitle, onClose, children }: ModalProps) {
  const titleId = useId();

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="modal-overlay">
      <button type="button" className="modal-backdrop" aria-label="Fechar" onClick={onClose} />
      <div className="modal-dialog" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <header className="modal-header">
          <h2 id={titleId}>{title}</h2>
          {subtitle ? <p className="modal-subtitle">{subtitle}</p> : null}
        </header>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}
