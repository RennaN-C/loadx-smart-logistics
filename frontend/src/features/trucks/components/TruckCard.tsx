import { RecordLifecycleAction } from "../../../components/RecordLifecycleAction";
import { StatusPill } from "../../../components/StatusPill";
import type { Truck } from "../types";
const weightFormatter = new Intl.NumberFormat("pt-BR");
const volumeFormatter = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

interface TruckCardProps {
  readonly onDocuments?: (truck: Truck) => void;
  readonly onMaintenance?: (truck: Truck) => void;
  readonly truck: Truck;
  readonly canManage: boolean;
  readonly onChanged: () => Promise<void>;
  readonly onEdit: (truck: Truck) => void;
}

export function TruckCard({ truck, canManage, onEdit, onChanged, onMaintenance, onDocuments }: TruckCardProps) {
  const volumeM3 = truck.internalWidthCm * truck.internalHeightCm * truck.internalLengthCm / 1_000_000;
  return (
    <tr className="truck-card">
      <td data-label="Placa"><strong className="truck-card-plate">{truck.plate}</strong></td>
      <td data-label="Veículo"><strong className="truck-card-model">{truck.model}</strong><small>{truck.internalWidthCm} × {truck.internalHeightCm} × {truck.internalLengthCm} cm</small></td>
      <td data-label="Capacidade"><span className="truck-card-weight"><strong>{weightFormatter.format(truck.maxWeightKg)} kg</strong></span></td>
      <td data-label="Volume interno">{volumeFormatter.format(volumeM3)} m³</td>
      <td data-label="Situação"><StatusPill tone={truck.active ? "good" : "neutral"}>{truck.active ? "Ativo" : "Arquivado"}</StatusPill></td>
      <td data-label="Ações">
        <div className="truck-card-actions" role="group" aria-label={`Ações do caminhão ${truck.plate}`}>
            {onDocuments ? (
              <button type="button" className="btn-link" onClick={() => onDocuments(truck)}>
                Documentos
              </button>
            ) : null}
            {onMaintenance ? (
              <button type="button" className="btn-link" onClick={() => onMaintenance(truck)}>
                Manutenções
              </button>
            ) : null}
            {canManage ? (
              <>
                <button type="button" className="btn-link" onClick={() => onEdit(truck)}>
                  Editar
                </button>
                <RecordLifecycleAction resource="trucks" id={truck.id} active={truck.active} onChanged={onChanged} />
              </>
            ) : null}
        </div>
      </td>
    </tr>
  );
}
