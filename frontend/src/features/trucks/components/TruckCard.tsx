import { StatusPill } from "../../../components/StatusPill";
import type { Truck } from "../types";
import { TruckSchematic } from "./TruckSchematic";

const weightFormatter = new Intl.NumberFormat("pt-BR");

interface TruckCardProps {
  readonly truck: Truck;
  readonly canManage: boolean;
  readonly onEdit: (truck: Truck) => void;
}

export function TruckCard({ truck, canManage, onEdit }: TruckCardProps) {
  return (
    <article className="truck-card">
      <div className="truck-card-figure">
        <TruckSchematic
          view="side"
          variant="card"
          dimensions={{
            widthCm: truck.internalWidthCm,
            heightCm: truck.internalHeightCm,
            lengthCm: truck.internalLengthCm,
          }}
        />
      </div>

      <div className="truck-card-body">
        <div className="truck-card-head">
          <div>
            <p className="truck-card-plate">{truck.plate}</p>
            <p className="truck-card-model">{truck.model}</p>
          </div>
          <StatusPill tone={truck.active ? "good" : "neutral"}>{truck.active ? "Ativo" : "Inativo"}</StatusPill>
        </div>

        <dl className="truck-card-specs">
          <div>
            <dt>LARGURA</dt>
            <dd>{truck.internalWidthCm} cm</dd>
          </div>
          <div>
            <dt>ALTURA</dt>
            <dd>{truck.internalHeightCm} cm</dd>
          </div>
          <div>
            <dt>COMPR.</dt>
            <dd>{truck.internalLengthCm} cm</dd>
          </div>
        </dl>

        <div className="truck-card-foot">
          <span className="truck-card-weight">
            Peso máx. <strong>{weightFormatter.format(truck.maxWeightKg)} kg</strong>
          </span>
          {canManage ? (
            <button type="button" className="btn-link" onClick={() => onEdit(truck)}>
              Editar
            </button>
          ) : null}
        </div>
      </div>
    </article>
  );
}
