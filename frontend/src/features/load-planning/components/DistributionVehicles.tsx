import { Icon } from "../../../components/Icon";
import { StatusPill } from "../../../components/StatusPill";
import { PART_LABELS } from "./distributionLabels";
import type { DistributionPart } from "../types";

const number = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });

export function DistributionVehicles({ parts, selectedId, onSelect }: {
  readonly parts: DistributionPart[]; readonly selectedId: string; readonly onSelect: (id: string) => void;
}) {
  return <fieldset className="distribution-vehicles" aria-label="Caminhões da distribuição">
    {parts.map((part, index) => <button type="button" key={part.id} className="distribution-vehicle"
      aria-pressed={selectedId === part.id} aria-controls="distribution-vehicle-detail" onClick={() => onSelect(part.id)}>
      <span className="distribution-vehicle-heading"><span className="distribution-vehicle-icon"><Icon name="truck" size={22} /></span><span><small>Caminhão {index + 1}</small><strong>{part.truck.plate}</strong></span></span>
      <span className="distribution-vehicle-model">{part.truck.model}</span>
      <span className="distribution-vehicle-metrics"><span><strong>{part.loadPlan.loadedCount}</strong> {part.loadPlan.loadedCount === 1 ? "volume" : "volumes"}</span><span><strong>{number.format(part.loadPlan.totalWeightKg)}</strong> kg</span></span>
      <span className="distribution-vehicle-occupancy"><span>Ocupação</span><strong>{number.format(part.loadPlan.occupancyPercent)}%</strong></span>
      <span className="plan-occupancy" aria-hidden="true"><span className="plan-occupancy-fill" style={{ width: `${part.loadPlan.occupancyPercent}%` }} /></span>
      <StatusPill tone={part.status === "CANCELED" ? "warn" : "neutral"}>{PART_LABELS[part.status]}</StatusPill>
    </button>)}
  </fieldset>;
}
