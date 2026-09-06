import { StatusPill } from "../../../components/StatusPill";
import {
  DELIVERY_ACTION_LABELS,
  DELIVERY_STATUS_LABELS,
  deliveryStatusTone,
} from "./tripLabels";
import { DELIVERY_TRANSITIONS, type Delivery, type Trip } from "../types";

const dateTime = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

interface TripStopProps {
  readonly delivery: Delivery;
  /** Já resolvido por quem chama: perfil pode operar E a viagem está em rota. */
  readonly canAdvance: boolean;
  readonly isWorking: boolean;
  readonly onAdvance: (delivery: Delivery, next: Delivery["status"]) => void;
}

function TripStop({ delivery, canAdvance, isWorking, onAdvance }: TripStopProps) {
  const next = DELIVERY_TRANSITIONS[delivery.status];

  return (
    <li className="trip-stop">
      <span className="trip-stop-seq">{delivery.sequence}</span>
      <div className="trip-stop-body">
        <StatusPill tone={deliveryStatusTone(delivery.status)}>
          {DELIVERY_STATUS_LABELS[delivery.status]}
        </StatusPill>
        {delivery.deliveredAt ? (
          <span className="trip-stop-time">
            entregue em {dateTime.format(new Date(delivery.deliveredAt))}
          </span>
        ) : null}
      </div>
      {next ? (
        <button
          type="button"
          className="btn-secondary"
          disabled={!canAdvance || isWorking}
          onClick={() => onAdvance(delivery, next)}
        >
          {DELIVERY_ACTION_LABELS[delivery.status]}
        </button>
      ) : null}
    </li>
  );
}

interface TripStopsProps {
  readonly trip: Trip;
  readonly canOperate: boolean;
  readonly isWorking: boolean;
  readonly onAdvance: (delivery: Delivery, next: Delivery["status"]) => void;
}

/**
 * As paradas na ordem de descarga.
 *
 * A ordenação é feita numa cópia: `sort` altera o array no lugar, e mexer no
 * que veio da resposta faria a lista mudar de ordem em rerenders futuros.
 */
export function TripStops({ trip, canOperate, isWorking, onAdvance }: TripStopsProps) {
  const inRoute = trip.status === "IN_ROUTE";

  return (
    <ol className="trip-stops">
      {[...trip.deliveries]
        .sort((a, b) => a.sequence - b.sequence)
        .map((delivery) => (
          <TripStop
            key={delivery.id}
            delivery={delivery}
            canAdvance={canOperate && inRoute}
            isWorking={isWorking}
            onAdvance={onAdvance}
          />
        ))}
    </ol>
  );
}
