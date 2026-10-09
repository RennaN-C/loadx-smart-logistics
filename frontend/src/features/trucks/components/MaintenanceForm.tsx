import { useState, type FormEvent } from "react";
import { AlertBanner } from "../../../components/AlertBanner";
import { FormField } from "../../../components/FormField";
import { ApiError } from "../../../types/api";
import { closeMaintenance, createMaintenance } from "../api/maintenanceApi";
import type { Truck, TruckMaintenance } from "../types";

function localNow() { const now = new Date(); return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0,16); }
export function MaintenanceForm({ truck, closing, onSaved, onCancel }: { readonly truck: Truck; readonly closing?: TruckMaintenance; readonly onSaved: () => Promise<void>; readonly onCancel: () => void }) {
  const [kind, setKind] = useState<TruckMaintenance["kind"]>("PREVENTIVE");
  const [start, setStart] = useState(localNow);
  const [end, setEnd] = useState("");
  const [description, setDescription] = useState("");
  const [workshop, setWorkshop] = useState("");
  const [notes, setNotes] = useState("");
  const [cost, setCost] = useState("");
  const [km, setKm] = useState(truck.odometerKm?.toString() ?? "");
  const [nextAt, setNextAt] = useState("");
  const [nextKm, setNextKm] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault(); setPending(true); setError(null);
    try {
      const odometerKm = km === "" ? undefined : Number(km);
      if (closing) await closeMaintenance(truck.id, closing.id, { odometerKm, ...(nextAt ? { nextServiceAt: new Date(nextAt).toISOString() } : {}), ...(nextKm ? { nextServiceKm: Number(nextKm) } : {}) });
      else await createMaintenance(truck.id, { kind, startsAt: new Date(start).toISOString(), endsAt: end ? new Date(end).toISOString() : null, description: description.trim(), workshop: workshop.trim() || null, notes: notes.trim() || null, cost: cost === "" ? null : Number(cost), odometerKm });
      await onSaved();
    } catch (error_) { setError(error_ instanceof ApiError ? error_.message : "Não foi possível salvar a manutenção."); }
    finally { setPending(false); }
  }
  return <form className="entity-form" onSubmit={(event) => void submit(event)}>
    {error ? <AlertBanner>{error}</AlertBanner> : null}
    <fieldset className="entity-form-fieldset" disabled={pending}>
      {closing ? <p>Encerrar libera este bloqueio. Para um período futuro, a ação cancela a indisponibilidade programada. Outros bloqueios permanecem.</p> : <>
        <FormField id="maintenance-kind" label="TIPO"><select id="maintenance-kind" value={kind} onChange={(e) => setKind(e.target.value as TruckMaintenance["kind"])}><option value="PREVENTIVE">Preventiva</option><option value="CORRECTIVE">Corretiva</option></select></FormField>
        <FormField id="maintenance-start" label="INÍCIO"><input id="maintenance-start" type="datetime-local" required value={start} onChange={(e) => setStart(e.target.value)} /></FormField>
        <FormField id="maintenance-end" label="FIM PROGRAMADO (OPCIONAL)"><input id="maintenance-end" type="datetime-local" min={start} value={end} onChange={(e) => setEnd(e.target.value)} /></FormField>
        <FormField id="maintenance-description" label="DESCRIÇÃO"><textarea id="maintenance-description" required maxLength={2000} value={description} onChange={(e) => setDescription(e.target.value)} /></FormField>
        <FormField id="maintenance-workshop" label="OFICINA"><input id="maintenance-workshop" maxLength={160} value={workshop} onChange={(e) => setWorkshop(e.target.value)} /></FormField>
        <FormField id="maintenance-notes" label="OBSERVAÇÃO"><textarea id="maintenance-notes" maxLength={2000} value={notes} onChange={(e) => setNotes(e.target.value)} /></FormField>
        <FormField id="maintenance-cost" label="CUSTO (OPCIONAL)"><input id="maintenance-cost" type="number" min={0} step="0.01" value={cost} onChange={(e) => setCost(e.target.value)} /></FormField>
      </>}
      <FormField id="maintenance-km" label="QUILOMETRAGEM (KM)"><input id="maintenance-km" type="number" min={truck.odometerKm ?? 0} step={1} value={km} onChange={(e) => setKm(e.target.value)} /></FormField>
      {closing ? <>
        <FormField id="maintenance-next-date" label="PRÓXIMA REVISÃO (DATA)"><input id="maintenance-next-date" type="datetime-local" value={nextAt} onChange={(e) => setNextAt(e.target.value)} /></FormField>
        <FormField id="maintenance-next-km" label="PRÓXIMA REVISÃO (KM)"><input id="maintenance-next-km" type="number" min={0} step={1} value={nextKm} onChange={(e) => setNextKm(e.target.value)} /></FormField>
        <p>Campos de revisão em branco mantêm a programação existente.</p>
      </> : null}
    </fieldset>
    <div className="entity-form-actions"><button type="button" className="btn-secondary" disabled={pending} onClick={onCancel}>Voltar</button><button type="submit" className="btn-primary" disabled={pending}>{pending ? "Salvando…" : closing ? "Confirmar encerramento" : "Registrar manutenção"}</button></div>
  </form>;
}
