import { useCallback, useState } from "react";
import { AlertBanner } from "../../../components/AlertBanner";
import { ArchiveFilter } from "../../../components/ArchiveFilter";
import { Pagination } from "../../../components/Pagination";
import { StatusPill } from "../../../components/StatusPill";
import { useRegistryList } from "../../../hooks/useRegistryList";
import type { ListParams } from "../../../services/pagination";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { canManageLogistics } from "../../auth/permissions";
import { listCustomerAddresses, updateCustomerAddress } from "../api/customerAddressesApi";
import type { CustomerAddress, CustomerAddressUpdateInput } from "../types";
import { CustomerAddressForm } from "./CustomerAddressForm";

export function CustomerAddressPanel({ customerId, onChanged }: { readonly customerId: string; readonly onChanged: () => Promise<void> }) {
  const { user } = useAuth();
  const canManage = canManageLogistics(user?.role);
  const load = useCallback((params: ListParams) => listCustomerAddresses(customerId, params), [customerId]);
  const { items, status, error, archiveStatus, setArchiveStatus, refetch, page, totalPages, goToPage } = useRegistryList(load);
  const [editing, setEditing] = useState<CustomerAddress | null>(null);
  const [creating, setCreating] = useState(false);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  async function changed() { setEditing(null); setCreating(false); await refetch(); await onChanged(); }
  async function update(address: CustomerAddress, input: CustomerAddressUpdateInput) {
    setPendingId(address.id); setActionError(null);
    try { await updateCustomerAddress(customerId, address.id, input); await changed(); }
    catch (failure) { setActionError(failure instanceof ApiError ? failure.message : "Não foi possível alterar o endereço."); }
    finally { setPendingId(null); }
  }
  if (editing || creating) return <CustomerAddressForm customerId={customerId} address={editing ?? undefined} onSaved={changed} onCancel={() => { setEditing(null); setCreating(false); }} />;
  return <div>
    <div className="entity-toolbar">
      <ArchiveFilter value={archiveStatus} onChange={setArchiveStatus} />
      {canManage ? <button type="button" className="btn-primary" onClick={() => setCreating(true)}>Novo endereço</button> : null}
    </div>
    {status === "loading" ? <p>Carregando endereços…</p> : null}
    {error ? <AlertBanner>{error.message}</AlertBanner> : null}
    {actionError ? <AlertBanner>{actionError}</AlertBanner> : null}
    {status === "success" && items.length === 0 ? <p>Nenhum endereço neste filtro.</p> : null}
    {status === "success" ? items.map((address) => <article key={address.id} className="contact-card">
      <div className="contact-card-head"><strong>{address.label}</strong><StatusPill tone={address.active ? "good" : "neutral"}>{address.active ? "Ativo" : "Arquivado"}</StatusPill>{address.isPrimary ? <StatusPill tone="good">Principal</StatusPill> : null}</div>
      <p>{address.address}</p><p>{address.city} · {address.state}{address.postalCode ? ` · CEP ${address.postalCode}` : ""}</p>
      {canManage ? <div className="contact-card-foot">
        <button className="btn-link" type="button" disabled={pendingId === address.id} onClick={() => setEditing(address)}>Editar endereço</button>
        {address.active && !address.isPrimary ? <button className="btn-link" type="button" disabled={pendingId === address.id} onClick={() => void update(address, { isPrimary: true })}>Tornar principal</button> : null}
        <button className="btn-link" type="button" disabled={pendingId === address.id} onClick={() => void update(address, { active: !address.active })}>{address.active ? "Arquivar endereço" : "Reativar endereço"}</button>
      </div> : null}
    </article>) : null}
    {status === "success" ? <Pagination page={page} totalPages={totalPages} onChange={goToPage} label="endereços" /> : null}
  </div>;
}
