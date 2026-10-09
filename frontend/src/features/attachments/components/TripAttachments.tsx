import { useEffect, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { Modal } from "../../../components/Modal";
import type { Trip } from "../../deliveries/types";
import { listTripAttachmentOccurrences, type AttachmentResource } from "../api/attachmentsApi";
import { AttachmentPanel } from "./AttachmentPanel";

export function TripAttachments({ trip, canManage }: { trip: Trip; canManage: boolean }) {
  const [open, setOpen] = useState(false);
  const [occurrences, setOccurrences] = useState<{ id: string; type: string; description: string }[]>([]);
  const [selection, setSelection] = useState(`trips:${trip.id}`);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!open) return;
    let active = true;
    setLoading(true); setError(null);
    listTripAttachmentOccurrences(trip.id).then((rows) => { if (active) setOccurrences(rows); })
      .catch(() => { if (active) setError("Não foi possível consultar ocorrências para anexos."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [open, trip.id]);
  const [resource, resourceId] = selection.split(":") as [AttachmentResource, string];
  return <>
    <button type="button" className="btn-secondary" onClick={() => setOpen(true)}>Anexos da viagem e entregas</button>
    {open ? <Modal title="Anexos operacionais" onClose={() => setOpen(false)}>
      <label>Recurso do anexo <select value={selection} onChange={(event) => setSelection(event.target.value)}>
        <option value={`trips:${trip.id}`}>Viagem</option>
        {trip.deliveries.map((delivery) => <option key={delivery.id} value={`deliveries:${delivery.id}`}>Entrega {delivery.sequence}</option>)}
        {occurrences.map((occurrence) => <option key={occurrence.id} value={`occurrences:${occurrence.id}`}>Ocorrência {occurrence.type}: {occurrence.description}</option>)}
      </select></label>
      {loading ? <p role="status">Carregando ocorrências…</p> : null}
      {error ? <AlertBanner>{error}</AlertBanner> : null}
      <AttachmentPanel key={selection} resource={resource} resourceId={resourceId} canManage={canManage} />
    </Modal> : null}
  </>;
}
