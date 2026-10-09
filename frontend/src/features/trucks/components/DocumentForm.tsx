import { useState, type FormEvent } from "react";
import { AlertBanner } from "../../../components/AlertBanner";
import { ApiError } from "../../../types/api";
import { saveDocument, type DocumentKind, type TruckDocument } from "../api/documentsApi";
import { documentKinds } from "./documentLabels";

interface Props { readonly truckId: string; readonly replacing?: TruckDocument; readonly onSaved: () => Promise<void>; readonly onCancel: () => void }
function utc(value: string): string | null { return value ? new Date(value).toISOString() : null; }
export function DocumentForm({ truckId, replacing, onSaved, onCancel }: Props) {
  const [kind, setKind] = useState<DocumentKind>(replacing?.kind ?? "CRLV");
  const [reference, setReference] = useState(replacing?.reference ?? "");
  const [issued, setIssued] = useState("");
  const [expires, setExpires] = useState("");
  const [file, setFile] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault(); setPending(true); setError(null);
    try {
      await saveDocument(truckId, { kind, reference: reference.trim(), issued_at: utc(issued), expires_at: utc(expires), file_reference: file.trim() || null }, replacing?.id);
      await onSaved();
    } catch (failure) { setError(failure instanceof ApiError ? failure.message : "Não foi possível salvar o documento."); }
    finally { setPending(false); }
  }
  return <form onSubmit={(event) => void submit(event)} className="entity-form">
    <label>Tipo<select value={kind} onChange={(event) => setKind(event.target.value as DocumentKind)} disabled={pending || !!replacing}>{Object.entries(documentKinds).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
    <label>Número ou referência<input value={reference} onChange={(event) => setReference(event.target.value)} required maxLength={120} disabled={pending} /></label>
    <label>Emissão<input type="datetime-local" value={issued} onChange={(event) => setIssued(event.target.value)} disabled={pending} /></label>
    <label>Validade<input type="datetime-local" value={expires} onChange={(event) => setExpires(event.target.value)} disabled={pending} /></label>
    <label>Referência de arquivo (UUID)<input value={file} onChange={(event) => setFile(event.target.value)} pattern="[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}" disabled={pending} /></label>
    <p>Referência opcional de metadados. Upload e download de arquivos ainda não estão disponíveis.</p>
    {replacing ? <p>A versão anterior será preservada. Informe as datas e a referência de arquivo da nova versão.</p> : null}
    {error ? <AlertBanner>{error}</AlertBanner> : null}
    <button type="submit" disabled={pending}>{replacing ? "Confirmar renovação" : "Registrar documento"}</button>
    <button type="button" disabled={pending} onClick={onCancel}>Cancelar</button>
  </form>;
}
