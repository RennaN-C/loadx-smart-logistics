import type { Trip } from "../types";

const dateTime = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

interface TripSummaryProps {
  readonly trip: Trip;
  readonly pendingDeliveries: number;
}

/** Os quatro números da viagem: quantas paradas, quantas faltam, e o intervalo. */
export function TripSummary({ trip, pendingDeliveries }: TripSummaryProps) {
  return (
    <dl className="trip-meta">
      <div>
        <dt>PARADAS</dt>
        <dd>{trip.deliveries.length}</dd>
      </div>
      <div>
        <dt>EM ABERTO</dt>
        {/* o que falta é o que exige ação, então destoa dos outros */}
        <dd className={pendingDeliveries > 0 ? "trip-meta-warn" : undefined}>{pendingDeliveries}</dd>
      </div>
      <div>
        <dt>INÍCIO</dt>
        <dd>{trip.startedAt ? dateTime.format(new Date(trip.startedAt)) : "—"}</dd>
      </div>
      <div>
        <dt>FIM</dt>
        <dd>{trip.finishedAt ? dateTime.format(new Date(trip.finishedAt)) : "—"}</dd>
      </div>
    </dl>
  );
}
