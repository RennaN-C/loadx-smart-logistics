import { useRef, useState, type FormEvent } from "react";
import { FormField } from "../../../components/FormField";
import { IMAGE_ACCEPT, readImageAsBase64 } from "../../../services/imageFile";
import { registerDeliveryEvidence } from "../api/evidencesApi";
import type { EvidenceKind } from "../types";
import { evidenceError } from "../hooks/useDeliveryEvidence";

interface PendingUpload { file: File; eventId: string; kind: EvidenceKind; attempted: boolean }
interface Props {
  readonly deliveryId: string;
  readonly disabled: boolean;
  readonly onRegistered: () => Promise<void>;
  readonly onError: (message: string) => void;
}

export function DeliveryEvidenceUpload({ deliveryId, disabled, onRegistered, onError }: Props) {
  const [kind, setKind] = useState<EvidenceKind>("PHOTO");
  const [pending, setPending] = useState<PendingUpload | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const working = useRef(false);
  const fileInput = useRef<HTMLInputElement>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!pending || working.current || disabled) return;
    working.current = true; setBusy(true); setFailed(false); onError("");
    let content: string;
    try { content = await readImageAsBase64(pending.file); }
    catch (e) { onError(e instanceof Error ? e.message : "Arquivo inválido."); working.current = false; setBusy(false); return; }
    const intent = { ...pending, attempted: true };
    setPending(intent);
    try {
      await registerDeliveryEvidence(deliveryId, { eventId: intent.eventId, kind: intent.kind, contentBase64: content });
      setPending(null);
      if (fileInput.current) fileInput.current.value = "";
      await onRegistered();
    } catch (e) { setFailed(true); onError(evidenceError(e)); }
    finally { working.current = false; setBusy(false); }
  }
  return <form className="evidence-form" onSubmit={event => void submit(event)} aria-label="Registrar evidência" aria-busy={busy}>
    <FormField id="evidence-kind" label="TIPO" narrow>
      <select id="evidence-kind" value={kind} disabled={disabled || busy || !!pending?.attempted} onChange={event => {
        const selected = event.target.value as EvidenceKind; setKind(selected);
        if (pending) setPending({ ...pending, kind: selected, eventId: crypto.randomUUID() });
      }}><option value="PHOTO">Foto</option><option value="SIGNATURE">Assinatura</option></select>
    </FormField>
    <FormField id="evidence-file" label="IMAGEM" hint="PNG ou JPEG, até 5 MiB. O servidor valida e remove metadados.">
      <input id="evidence-file" ref={fileInput} type="file" accept={IMAGE_ACCEPT} disabled={disabled || busy} onChange={event => {
        const file = event.target.files?.[0]; setPending(file ? { file, eventId: crypto.randomUUID(), kind, attempted: false } : null); setFailed(false); onError("");
      }} />
    </FormField>
    {pending?.attempted && <p className="evidence-upload-hint">Repetir esta tentativa mantém arquivo, tipo e identificação. Selecionar outro arquivo inicia um novo registro.</p>}
    <button type="submit" className="btn-primary" disabled={disabled || !pending || busy}>{busy ? "Enviando…" : failed ? "Tentar novamente" : "Registrar evidência"}</button>
  </form>;
}
