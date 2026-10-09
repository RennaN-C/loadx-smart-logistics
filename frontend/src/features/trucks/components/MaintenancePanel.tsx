import { useCallback, useState, type FormEvent } from "react";
import { AlertBanner } from "../../../components/AlertBanner";
import { Pagination } from "../../../components/Pagination";
import { StatusPill } from "../../../components/StatusPill";
import { useResourceList } from "../../../hooks/useResourceList";
import type { ListParams } from "../../../services/pagination";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { canManageLogistics } from "../../auth/permissions";
import { listMaintenances } from "../api/maintenanceApi";
import { getTruck, updateTruck } from "../api/trucksApi";
import type { Truck, TruckMaintenance } from "../types";
import { MaintenanceForm } from "./MaintenanceForm";
function date(value: string) { return new Date(value).toLocaleString("pt-BR"); }
function maintenanceLabel(record: TruckMaintenance): string {
  if (record.closedAt) return new Date(record.closedAt) < new Date(record.startsAt) ? "Cancelada" : "Encerrada";
  if (new Date(record.startsAt) > new Date()) return "Programada";
  if (record.endsAt && new Date(record.endsAt) <= new Date()) return "Período concluído";
  return "Em manutenção";
}
export function MaintenancePanel({ truck: initial, onChanged }: { readonly truck: Truck; readonly onChanged: () => Promise<void> }) {
  const [truck, setTruck] = useState(initial);
  const { user } = useAuth(); const canManage = canManageLogistics(user?.role);
  const load = useCallback((params: ListParams) => listMaintenances(initial.id, params), [initial.id]);
  const { items, status, error, refetch, page, totalPages, goToPage } = useResourceList(load);
  const [creating, setCreating] = useState(false); const [closing, setClosing] = useState<TruckMaintenance | undefined>();
  const [km, setKm] = useState(initial.odometerKm?.toString() ?? ""); const [pending, setPending] = useState(false); const [actionError, setActionError] = useState<string | null>(null);
  async function changed() { setCreating(false); setClosing(undefined); const fresh = await getTruck(truck.id); setTruck(fresh); setKm(fresh.odometerKm?.toString() ?? ""); await refetch(); await onChanged(); }
  async function saveKm(event: FormEvent) { event.preventDefault(); setPending(true); setActionError(null); try { await updateTruck(truck.id, { odometerKm: Number(km) }); await changed(); } catch(error_) { setActionError(error_ instanceof ApiError ? error_.message : "Não foi possível atualizar a quilometragem."); } finally { setPending(false); } }
  if (creating || closing) return <MaintenanceForm truck={truck} closing={closing} onSaved={changed} onCancel={() => { setCreating(false); setClosing(undefined); }} />;
  const overdue = !!((truck.nextServiceAt && new Date(truck.nextServiceAt) <= new Date()) || (truck.nextServiceKm != null && truck.odometerKm != null && truck.odometerKm >= truck.nextServiceKm));
  return <div>
    <p>Quilometragem atual: {truck.odometerKm ?? "não informada"}{truck.odometerKm != null ? " km" : ""}</p>
    <p>Próxima revisão: {truck.nextServiceAt ? date(truck.nextServiceAt) : "data não informada"} · {truck.nextServiceKm != null ? `${truck.nextServiceKm} km` : "quilometragem não informada"}</p>
    {overdue ? <StatusPill tone="warn">Revisão vencida</StatusPill> : null}
    {canManage ? <><form onSubmit={(e) => void saveKm(e)}><label>Atualizar quilometragem<input aria-label="Atualizar quilometragem" type="number" min={truck.odometerKm ?? 0} step={1} required value={km} onChange={(e) => setKm(e.target.value)} disabled={pending} /></label><button type="submit" disabled={pending}>Salvar quilometragem</button></form>{truck.active ? <button type="button" className="btn-primary" onClick={() => setCreating(true)}>Nova manutenção</button> : null}</> : null}
    {actionError ? <AlertBanner>{actionError}</AlertBanner> : null}
    {status === "loading" ? <output>Carregando manutenções…</output> : null}
    {error ? <AlertBanner>{error.message}</AlertBanner> : null}
    {status === "success" && items.length === 0 ? <p>Nenhuma manutenção registrada.</p> : null}
    {items.map((record) => <article key={record.id} className="contact-card"><strong>{record.kind === "PREVENTIVE" ? "Preventiva" : "Corretiva"}</strong><StatusPill tone={record.closedAt ? "neutral" : "warn"}>{maintenanceLabel(record)}</StatusPill><p>{record.description}</p><p>{date(record.startsAt)} até {record.endsAt ? date(record.endsAt) : "fim não informado"}</p><p>Oficina: {record.workshop ?? "não informada"} · Custo: {record.cost == null ? "não informado" : record.cost.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</p>{record.notes ? <p>{record.notes}</p> : null}<p>Km inicial: {record.odometerKm ?? "não informado"} · Km final: {record.completionOdometerKm ?? "não informado"}</p>{record.closedAt ? <p>Encerramento: {date(record.closedAt)} · Próxima revisão: {record.nextServiceAt ? date(record.nextServiceAt) : "sem data"} / {record.nextServiceKm ?? "sem km"}</p> : canManage ? <button type="button" className="btn-link" onClick={() => setClosing(record)}>Encerrar manutenção</button> : null}</article>)}
    {status === "success" ? <Pagination page={page} totalPages={totalPages} onChange={goToPage} label="manutenções" /> : null}
  </div>;
}
