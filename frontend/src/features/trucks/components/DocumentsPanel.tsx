import { useCallback, useEffect, useState } from "react";
import { AlertBanner } from "../../../components/AlertBanner";
import { Pagination } from "../../../components/Pagination";
import { StatusPill } from "../../../components/StatusPill";
import { useResourceList } from "../../../hooks/useResourceList";
import type { ListParams } from "../../../services/pagination";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { canManageLogistics } from "../../auth/permissions";
import { listDocuments, listDocumentPolicies, setDocumentPolicy, type DocumentKind, type DocumentPolicy, type TruckDocument } from "../api/documentsApi";
import type { Truck } from "../types";
import { DocumentForm } from "./DocumentForm";
import { documentKinds, documentStatuses } from "./documentLabels";

function date(value: string | null) { return value ? new Date(value).toLocaleString("pt-BR") : "não informada"; }
export function DocumentsPanel({ truck, onChanged }: { readonly truck: Truck; readonly onChanged: () => Promise<void> }) {
  const { user } = useAuth(); const canManage = canManageLogistics(user?.role) && truck.active;
  const load = useCallback((params: ListParams) => listDocuments(truck.id, params), [truck.id]);
  const { items, status, error, refetch, page, totalPages, goToPage } = useResourceList(load);
  const [policies, setPolicies] = useState<DocumentPolicy[]>([]);
  const [policyLoaded, setPolicyLoaded] = useState(false);
  const [creating, setCreating] = useState(false);
  const [replacing, setReplacing] = useState<TruckDocument>();
  const [pending, setPending] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    setPolicyLoaded(false);
    listDocumentPolicies(truck.id).then((rows) => { if (live) { setPolicies(rows); setPolicyLoaded(true); } }).catch(() => { if (live) setActionError("Não foi possível consultar a política documental."); });
    return () => { live = false; };
  }, [truck.id]);
  async function changed() { setCreating(false); setReplacing(undefined); await refetch(); await onChanged(); }
  async function toggle(kind: DocumentKind, required: boolean) {
    setPending(true); setActionError(null);
    try {
      const row = await setDocumentPolicy(truck.id, kind, required);
      setPolicies((old) => [...old.filter((item) => item.kind !== kind), row]);
      await onChanged();
    } catch (failure) { setActionError(failure instanceof ApiError ? failure.message : "Não foi possível alterar a política documental."); }
    finally { setPending(false); }
  }
  if (creating || replacing) return <DocumentForm truckId={truck.id} replacing={replacing} onSaved={changed} onCancel={() => { setCreating(false); setReplacing(undefined); }} />;
  return <div>
    <h3>Elegibilidade documental</h3>
    <p>Tipos exigidos bloqueiam novas operações quando ausentes, vencidos ou com emissão futura. Alertas não enviam notificações.</p>
    {!policyLoaded ? <output>Carregando política documental…</output> : Object.entries(documentKinds).map(([kind, label]) => <label key={kind}><input type="checkbox" checked={policies.some((row) => row.kind === kind && row.required)} disabled={!canManage || pending} onChange={(event) => void toggle(kind as DocumentKind, event.target.checked)} />Exigir {label}</label>)}
    {canManage ? <button type="button" onClick={() => setCreating(true)}>Novo documento</button> : null}
    {actionError ? <AlertBanner>{actionError}</AlertBanner> : null}
    {status === "loading" ? <output>Carregando documentos…</output> : null}
    {error ? <AlertBanner>{error.message}</AlertBanner> : null}
    {status === "success" && items.length === 0 ? <p>Nenhum documento registrado.</p> : null}
    {items.map((row) => <article key={row.id} className="contact-card">
      <strong>{documentKinds[row.kind]} — {row.reference}</strong>
      <StatusPill tone={row.status === "VALID" ? "good" : "warn"}>{documentStatuses[row.status]}</StatusPill>
      <p>Emissão: {date(row.issued_at)} · Validade: {date(row.expires_at)}</p>
      <p>Registrado: {date(row.created_at)}{row.superseded_at ? ` · Substituído: ${date(row.superseded_at)}` : ""}</p>
      {row.file_reference ? <p>Referência de arquivo: {row.file_reference}</p> : null}
      {canManage && !row.superseded_at ? <button type="button" onClick={() => setReplacing(row)}>Renovar {documentKinds[row.kind]}</button> : null}
    </article>)}
    {status === "success" ? <Pagination page={page} totalPages={totalPages} onChange={goToPage} label="documentos" /> : null}
  </div>;
}
