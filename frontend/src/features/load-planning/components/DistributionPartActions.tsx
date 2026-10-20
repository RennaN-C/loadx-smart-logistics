import { useEffect, useState } from "react";
import { preflightDistribution } from "../api/distributionsApi";
import type { DistributionNeed, DistributionPart, LoadDistribution } from "../types";
import { DistributionFeedback } from "./DistributionFeedback";

export function DistributionPartActions({ distribution, part, canApprove, canCreate, disabled, onAction, onReprocess }: {
  readonly distribution: LoadDistribution; readonly part: DistributionPart;
  readonly canApprove: boolean; readonly canCreate: boolean; readonly disabled: boolean;
  readonly onAction: (action: "approve" | "cancel", partId?: string) => void;
  readonly onReprocess: (truckId: string) => void;
}) {
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [need, setNeed] = useState<DistributionNeed | null>(null);
  const [truckId, setTruckId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!attempt) return;
    let active = true;
    setLoading(true); setError(null); setNeed(null); setTruckId("");
    preflightDistribution(distribution.orderIds).then((result) => {
      if (active) setNeed(result);
    }).catch((failure) => { if (active) setError(failure); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [attempt, distribution.orderIds]);
  const usedTruckIds = new Set(distribution.parts.filter((p) => p.id !== part.id).map((p) => p.loadPlan.truckId));
  const eligible = need?.eligibleTrucks.filter((truck) => !usedTruckIds.has(truck.id)) ?? [];
  if (distribution.status === "APPROVED" || distribution.status === "CANCELED") return null;
  return <section className="distribution-part-actions" aria-label="Ações da parte">
    {part.status === "CANCELED" ? <>
      <p>Os volumes desta parte continuam vinculados à necessidade. Reprocesse para obter um novo plano e aprová-lo novamente.</p>
      {canCreate ? <>
        <button className="btn-secondary" type="button" disabled={disabled || loading} onClick={() => setAttempt((value) => value + 1)}>
          {loading ? "Consultando frota…" : "Consultar caminhões para reprocessar"}
        </button>
        <DistributionFeedback error={error} />
        {need ? <div className="distribution-reprocess">
          <label htmlFor="reprocess-truck">Caminhão elegível<select id="reprocess-truck" value={truckId} disabled={disabled} onChange={(event) => setTruckId(event.target.value)}>
            <option value="">Selecione um caminhão</option>
            {eligible.map((truck) => <option key={truck.id} value={truck.id}>{truck.plate} — {truck.model}</option>)}
          </select></label>
          {eligible.length === 0 ? <p>Nenhum caminhão elegível nesta consulta. Atualize a disponibilidade e tente novamente.</p> : null}
          <p className="entity-form-help">O servidor validará novamente capacidade e disponibilidade. A identidade dos volumes será preservada.</p>
          <button type="button" className="btn-primary" disabled={!truckId || disabled} onClick={() => onReprocess(truckId)}>Reprocessar esta parte</button>
        </div> : null}
      </> : null}
    </> : canApprove ? <>
      <div className="entity-form-actions">
        {part.status === "PENDING" ? <button className="btn-secondary" type="button" disabled={disabled} onClick={() => onAction("approve", part.id)}>Aceitar esta parte</button> : null}
        <button className="btn-secondary" type="button" disabled={disabled} onClick={() => setConfirmCancel(true)}>Cancelar esta parte</button>
      </div>
      <p className="entity-form-help">Aceitar uma parte não libera carregamento. Aceitar a última parte pendente conclui a aprovação total.</p>
      {confirmCancel ? <div className="distribution-confirm" role="group" aria-label="Confirmar cancelamento da parte">
        <p>Cancelar somente {part.truck.plate}? A distribuição ficará incompleta até o reprocessamento desta parte.</p>
        <button className="btn-secondary" type="button" disabled={disabled} onClick={() => setConfirmCancel(false)}>Manter parte</button>
        <button className="btn-secondary" type="button" disabled={disabled} onClick={() => { setConfirmCancel(false); onAction("cancel", part.id); }}>Confirmar cancelamento da parte</button>
      </div> : null}
    </> : null}
  </section>;
}
