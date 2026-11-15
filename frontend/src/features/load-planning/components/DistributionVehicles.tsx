import { useId } from "react";
import { Icon } from "../../../components/Icon";
import { StatusPill } from "../../../components/StatusPill";
import { PART_LABELS } from "./distributionLabels";
import type { DistributionPart } from "../types";

const number = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });

export function DistributionVehicles({ parts, selectedId, onSelect }: {
  readonly parts: DistributionPart[]; readonly selectedId: string; readonly onSelect: (id: string) => void;
}) {
  const selectId = useId();
  const selected = parts.find((part) => part.id === selectedId);
  return <fieldset className={`distribution-vehicles distribution-fleet-selector${parts.length > 3 ? " distribution-vehicles-many" : ""}`} aria-label="Caminhões da distribuição">
    <legend>Veículos da distribuição <span>{parts.length}</span></legend>
    <div className="distribution-fleet-heading"><p>Selecione um caminhão para inspecionar sua carga.</p><output aria-live="polite">Visualizando <strong>{selected?.truck.plate}</strong></output></div>
    <div className="distribution-vehicle-select"><label htmlFor={selectId}>Caminhão para visualizar</label><select id={selectId} value={selectedId} onChange={(event) => onSelect(event.target.value)}>{parts.map((part) => <option key={part.id} value={part.id}>{part.truck.plate} · {part.truck.model} · {part.loadPlan.loadedCount} volumes · {number.format(part.loadPlan.totalWeightKg)} kg · {number.format(part.loadPlan.occupancyPercent)}% · {PART_LABELS[part.status]}</option>)}</select></div>
    {parts.length <= 3 ? <div className="distribution-vehicle-list">{parts.map((part, index) => <button type="button" key={part.id} className="distribution-vehicle"
      aria-pressed={selectedId === part.id} aria-controls="distribution-vehicle-detail" onClick={() => onSelect(part.id)}>
      <span className="distribution-vehicle-heading"><span className="distribution-vehicle-icon"><Icon name="truck" size={22} /></span><span><small>Caminhão {index + 1}</small><strong>{part.truck.plate}</strong></span></span>
      <span className="distribution-vehicle-model">{part.truck.model}</span>
      <span className="distribution-vehicle-metrics"><span><strong>{part.loadPlan.loadedCount}</strong> {part.loadPlan.loadedCount === 1 ? "volume" : "volumes"}</span><span><strong>{number.format(part.loadPlan.totalWeightKg)}</strong> kg</span></span>
      <span className="distribution-vehicle-occupancy"><span>Ocupação</span><strong>{number.format(part.loadPlan.occupancyPercent)}%</strong></span>
      <span className="plan-occupancy" aria-hidden="true"><span className="plan-occupancy-fill" style={{ width: `${part.loadPlan.occupancyPercent}%` }} /></span>
      <StatusPill tone={part.status === "CANCELED" ? "warn" : "neutral"}>{PART_LABELS[part.status]}</StatusPill>
    </button>)}</div> : null}
  </fieldset>;
}
