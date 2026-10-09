import { useCallback, useEffect, useState, type FormEvent } from "react";
import { AlertBanner } from "../../../components/AlertBanner";
import { Pagination } from "../../../components/Pagination";
import { StatusPill } from "../../../components/StatusPill";
import { documentStatuses } from "../../../components/documentStatusLabels";
import { useResourceList } from "../../../hooks/useResourceList";
import type { ListParams } from "../../../services/pagination";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { canManageLogistics } from "../../auth/permissions";
import { approveDocumentType, listDocuments, listDocumentTypes, listDocumentPolicies, type DocumentType, type DocumentPolicy, type DriverDocument } from "../api/documentsApi";
import type { DriverListItem } from "../types";
import { DocumentForm } from "./DocumentForm";
import { DocumentPolicies } from "./DocumentPolicies";
function date(value: string | null) { return value ? new Date(value).toLocaleString("pt-BR") : "não informada"; }
export function DocumentsPanel({ driver, onChanged }: { readonly driver: DriverListItem; readonly onChanged: () => Promise<void> }) {
  const { user } = useAuth(); const canManage = canManageLogistics(user?.role) && driver.active;
  const load = useCallback((params: ListParams) => listDocuments(driver.id, params), [driver.id]);
  const { items, status, error, refetch, page, totalPages, goToPage } = useResourceList(load);
  const [types, setTypes] = useState<DocumentType[]>([]); const [policies, setPolicies] = useState<DocumentPolicy[]>([]);
  const [catalogStatus, setCatalogStatus] = useState<"loading"|"success"|"error">("loading");
  const [creating, setCreating] = useState(false); const [replacing, setReplacing] = useState<DriverDocument>();
  const [code, setCode] = useState(""); const [name, setName] = useState(""); const [pending, setPending] = useState(false); const [actionError, setActionError] = useState<string | null>(null);
  useEffect(() => { let live = true; Promise.all([listDocumentTypes(), listDocumentPolicies(driver.id)]).then(([catalog, rows]) => { if(live) {setTypes(catalog); setPolicies(rows); setCatalogStatus("success");} }).catch(() => {if(live) {setCatalogStatus("error"); setActionError("Não foi possível consultar tipos e políticas.");} }); return () => {live=false;}; }, [driver.id]);
  async function changed() { setCreating(false); setReplacing(undefined); await refetch(); await onChanged(); }
  async function policySaved(row: DocumentPolicy) { setPolicies((old) => [...old.filter((item) => item.document_type_id !== row.document_type_id), row]); await onChanged(); }
  async function approve(event: FormEvent) { event.preventDefault(); setPending(true); setActionError(null); try { const row = await approveDocumentType(code.trim().toUpperCase(), name.trim()); setTypes((old) => [...old,row]); setCode(""); setName(""); } catch(error_) { setActionError(error_ instanceof ApiError ? error_.message : "Não foi possível aprovar o tipo."); } finally {setPending(false);} }
  if(creating || replacing) return <DocumentForm driverId={driver.id} types={types} replacing={replacing} onSaved={changed} onCancel={() => {setCreating(false);setReplacing(undefined);}} />;
  return <div><h3>Elegibilidade documental</h3><p>Exigências são explícitas. CNH exigida precisa de validade e categoria conhecidas. Alertas não enviam notificações.</p>
    {catalogStatus === "loading" ? <output>Carregando tipos e políticas…</output> : null}
    {catalogStatus === "success" ? types.map((type) => <DocumentPolicies key={type.id} driverId={driver.id} type={type} policy={policies.find((row) => row.document_type_id === type.id)} canManage={canManage} onSaved={policySaved} />) : null}
    {canManage && catalogStatus === "success" ? <><button type="button" onClick={() => setCreating(true)}>Novo documento</button><form onSubmit={(event) => void approve(event)}><label>Código do tipo adicional<input value={code} onChange={(event) => setCode(event.target.value.toUpperCase())} required pattern="[A-Z][A-Z0-9_]*" maxLength={32} disabled={pending}/></label><label>Nome do tipo adicional<input value={name} onChange={(event) => setName(event.target.value)} required maxLength={120} disabled={pending}/></label><button type="submit" disabled={pending}>Aprovar tipo adicional</button></form></> : null}
    {actionError ? <AlertBanner>{actionError}</AlertBanner> : null}{status === "loading" ? <output>Carregando documentos…</output> : null}{error ? <AlertBanner>{error.message}</AlertBanner> : null}
    {status === "success" && items.length === 0 ? <p>Nenhum documento registrado.</p> : null}
    {items.map((row) => <article key={row.id} className="contact-card"><strong>{types.find((type) => type.id === row.document_type_id)?.name ?? "Documento"} — {row.reference}</strong><StatusPill tone={row.status === "VALID" ? "good" : "warn"}>{documentStatuses[row.status]}</StatusPill><p>Categoria: {row.category ?? "não informada"} · Emissão: {date(row.issued_at)} · Validade: {date(row.expires_at)}</p><p>Registrado: {date(row.created_at)} · Substituído: {date(row.superseded_at)}</p>{canManage && catalogStatus === "success" && !row.superseded_at ? <button type="button" onClick={() => setReplacing(row)}>Renovar documento</button> : null}</article>)}
    {status === "success" ? <Pagination page={page} totalPages={totalPages} onChange={goToPage} label="documentos de motoristas"/> : null}
  </div>;
}
