import { useEffect, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { Modal } from "../../../components/Modal";
import type { Trip } from "../../deliveries/types";
import { listTripAttachmentOccurrences, type AttachmentResource } from "../api/attachmentsApi";
import { AttachmentPanel } from "./AttachmentPanel";

interface OccurrenceOption { id: string; type: string; description: string }
interface TripAttachmentAccess {
  readonly readDeliveries: boolean;
  readonly readOccurrences: boolean;
  readonly manageDeliveries: boolean;
  readonly manageOccurrences: boolean;
}
export function TripAttachments({ trip, canManage, access }: { readonly trip: Trip; readonly canManage: boolean; readonly access?: TripAttachmentAccess }) {
  const readDeliveries = access?.readDeliveries ?? true;
  const readOccurrences = access?.readOccurrences ?? true;
  const [open, setOpen] = useState(false);
  const [occurrences, setOccurrences] = useState<OccurrenceOption[]>([]);
  const [selection, setSelection] = useState(`trips:${trip.id}`);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!open || !readOccurrences) return;
    let active = true;
    setLoading(true); setError(null);
    listTripAttachmentOccurrences(trip.id).then((rows) => { if (active) setOccurrences(rows); })
      .catch(() => { if (active) setError("Não foi possível consultar ocorrências para anexos."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [open, trip.id, readOccurrences]);
  const [resource, resourceId] = selection.split(":") as [AttachmentResource, string];
  const writes: Record<AttachmentResource, boolean> = { orders: false, trips: canManage, deliveries: access?.manageDeliveries ?? canManage, occurrences: access?.manageOccurrences ?? canManage };
  return <>
    <button type="button" className="btn-secondary" onClick={() => setOpen(true)}>Anexos da viagem e entregas</button>
    {open ? <Modal title="Anexos operacionais" onClose={() => setOpen(false)}>
      <label>Recurso do anexo <select value={selection} onChange={(event) => setSelection(event.target.value)}>
        <AttachmentResourceOptions trip={trip} occurrences={occurrences} readDeliveries={readDeliveries} readOccurrences={readOccurrences} />
      </select></label>
      {readOccurrences && loading ? <output>Carregando ocorrências…</output> : null}
      {readOccurrences && error ? <AlertBanner>{error}</AlertBanner> : null}
      <AttachmentPanel key={selection} resource={resource} resourceId={resourceId} canManage={writes[resource]} />
    </Modal> : null}
  </>;
}

function AttachmentResourceOptions({ trip, occurrences, readDeliveries, readOccurrences }: { readonly trip: Trip; readonly occurrences: OccurrenceOption[]; readonly readDeliveries: boolean; readonly readOccurrences: boolean }) {
  return <>        <option value={`trips:${trip.id}`}>Viagem</option>
        {readDeliveries && trip.deliveries.map((delivery) => <option key={delivery.id} value={`deliveries:${delivery.id}`}>Entrega {delivery.sequence}</option>)}
        {readOccurrences && occurrences.map((occurrence) => <option key={occurrence.id} value={`occurrences:${occurrence.id}`}>Ocorrência {occurrence.type}: {occurrence.description}</option>)}</>;
}
