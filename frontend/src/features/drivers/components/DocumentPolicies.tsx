import { useState, type FormEvent } from "react";
import { AlertBanner } from "../../../components/AlertBanner";
import { ApiError } from "../../../types/api";
import { setDocumentPolicy, type DocumentType, type DocumentPolicy } from "../api/documentsApi";
interface Props { readonly driverId: string; readonly type: DocumentType; readonly policy?: DocumentPolicy; readonly canManage: boolean; readonly onSaved: (row: DocumentPolicy) => Promise<void> }
export function DocumentPolicies({ driverId, type, policy, canManage, onSaved }: Props) {
  const [required, setRequired] = useState(policy?.required ?? false); const [categories, setCategories] = useState(policy?.allowed_categories ?? []);
  const [pending, setPending] = useState(false); const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) { event.preventDefault(); setPending(true); setError(null); try { await onSaved(await setDocumentPolicy(driverId, type.id, required, categories)); } catch(error_) { setError(error_ instanceof ApiError ? error_.message : "Não foi possível salvar a política."); } finally { setPending(false); } }
  return <form onSubmit={(event) => void submit(event)}><fieldset disabled={!canManage || pending}><legend>{type.name}</legend>
    <label><input type="checkbox" checked={required} onChange={(event) => setRequired(event.target.checked)} />Exigir {type.name}</label>
    {type.code === "CNH" ? <><p>Categorias aceitas: vazio aceita o catálogo atual; seleção exige correspondência exata, sem inferir classe de veículo.</p>{["C","D","E","AC","AD","AE"].map((value) => <label key={value}><input type="checkbox" checked={categories.includes(value)} onChange={(event) => setCategories(event.target.checked ? [...categories, value] : categories.filter((item) => item !== value))} />Aceitar {value}</label>)}</> : null}
    {canManage ? <button type="submit">Salvar política {type.name}</button> : null}
  </fieldset>{error ? <AlertBanner>{error}</AlertBanner> : null}</form>;
}
