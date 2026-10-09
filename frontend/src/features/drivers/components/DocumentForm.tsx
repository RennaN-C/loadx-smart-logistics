import { useState, type FormEvent } from "react";
import { AlertBanner } from "../../../components/AlertBanner";
import { ApiError } from "../../../types/api";
import { saveDocument, type DocumentType, type DriverDocument } from "../api/documentsApi";
interface Props { readonly driverId: string; readonly types: DocumentType[]; readonly replacing?: DriverDocument; readonly onSaved: () => Promise<void>; readonly onCancel: () => void }
function utc(value: string) { return value ? new Date(value).toISOString() : null; }
export function DocumentForm({ driverId, types, replacing, onSaved, onCancel }: Props) {
  const [typeId, setTypeId] = useState(replacing?.document_type_id ?? types[0]?.id ?? "");
  const [reference, setReference] = useState(replacing?.reference ?? ""); const [category, setCategory] = useState(replacing?.category ?? "");
  const [issued, setIssued] = useState(""); const [expires, setExpires] = useState("");
  const [pending, setPending] = useState(false); const [error, setError] = useState<string | null>(null);
  const cnh = types.some((row) => row.id === typeId && row.code === "CNH");
  async function submit(event: FormEvent) {
    event.preventDefault(); setPending(true); setError(null);
    try { await saveDocument(driverId, { document_type_id: typeId, reference: reference.trim(), category: cnh ? category || null : null, issued_at: utc(issued), expires_at: utc(expires) }, replacing?.id); await onSaved(); }
    catch (error_) { setError(error_ instanceof ApiError ? error_.message : "Não foi possível salvar o documento."); }
    finally { setPending(false); }
  }
  return <form className="entity-form" onSubmit={(event) => void submit(event)}>
    <label>Tipo aprovado<select value={typeId} onChange={(event) => setTypeId(event.target.value)} disabled={pending || !!replacing} required>{types.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
    <label>Número ou referência<input value={reference} onChange={(event) => setReference(event.target.value)} required maxLength={120} disabled={pending} /></label>
    {cnh ? <label>Categoria<select value={category} onChange={(event) => setCategory(event.target.value)} disabled={pending}><option value="">Não informada</option>{["C","D","E","AC","AD","AE"].map((value) => <option key={value}>{value}</option>)}</select></label> : null}
    <label>Emissão<input type="datetime-local" value={issued} onChange={(event) => setIssued(event.target.value)} disabled={pending} /></label>
    <label>Validade<input type="datetime-local" value={expires} onChange={(event) => setExpires(event.target.value)} required={cnh} disabled={pending} /></label>
    <p>Informe os dados da nova versão. A anterior será preservada no histórico. Arquivos e notificações externas não fazem parte deste cadastro.</p>
    {error ? <AlertBanner>{error}</AlertBanner> : null}
    <button type="submit" disabled={pending || !typeId}>{replacing ? "Confirmar renovação" : "Registrar documento"}</button><button type="button" disabled={pending} onClick={onCancel}>Cancelar</button>
  </form>;
}
