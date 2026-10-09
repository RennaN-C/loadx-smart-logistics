import { useEffect, useId, useRef, type ReactNode } from "react";

interface ModalProps {
  readonly title: string;
  readonly subtitle?: string;
  readonly onClose: () => void;
  readonly children: ReactNode;
}

let openModalCount = 0;
let previousBodyOverflow = "";

export function Modal({ title, subtitle, onClose, children }: ModalProps) {
  const titleId = useId();

  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    const dialog = dialogRef.current;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    if (openModalCount++ === 0) {
      previousBodyOverflow = document.body.style.overflow;
      document.body.style.overflow = "hidden";
    }
    const focusables = () => Array.from(dialog?.querySelectorAll<HTMLElement>(
      'button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href], [tabindex]:not([tabindex="-1"])',
    ) ?? []).filter((element) => !element.closest('[hidden], [aria-hidden="true"]'));
    (focusables()[0] ?? dialog)?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      const dialogs = document.querySelectorAll('[role="dialog"]');
      if (dialogs[dialogs.length - 1] !== dialog) return;
      if (event.key === "Escape") {
        event.preventDefault();
        closeRef.current();
      }
      if (event.key !== "Tab") return;
      const elements = focusables();
      const first = elements[0];
      const last = elements[elements.length - 1];
      if (!first || !last) { event.preventDefault(); dialog?.focus(); return; }
      if (!dialog?.contains(document.activeElement) || (event.shiftKey && document.activeElement === first)) {
        event.preventDefault(); (event.shiftKey ? last : first).focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      if (--openModalCount === 0) document.body.style.overflow = previousBodyOverflow;
      if (previousFocus?.isConnected) previousFocus.focus();
    };
  }, []);

  return (
    <div className="modal-overlay">
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
