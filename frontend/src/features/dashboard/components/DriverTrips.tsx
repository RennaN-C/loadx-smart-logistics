import { Link } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { StatusPill } from "../../../components/StatusPill";
import { useResourceList } from "../../../hooks/useResourceList";
import { listTrips } from "../../deliveries/api/tripsApi";
import { TRIP_STATUS_LABELS, tripStatusTone } from "../../deliveries/components/tripLabels";
import { mapTripErrorToMessage } from "../../deliveries/components/tripsErrorMessages";

const dateTime = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

/**
 * As viagens do motorista, na tela inicial dele.
 *
 * `GET /trips` recorta por perfil no backend: o motorista recebe SOMENTE as
 * viagens dele. Este componente não filtra nada — filtrar aqui seria repetir no
 * frontend uma regra de acesso que já é aplicada onde importa.
 */
export function DriverTrips() {
  const { status, items, error, refetch } = useResourceList(listTrips);

  if (status === "loading") {
    return (
      <p className="entity-state">
        <span className="spinner" aria-hidden="true" />
        <span>Carregando suas viagens…</span>
      </p>
    );
  }

  if (status === "error" && error) {
    return (
      <>
        <AlertBanner>{mapTripErrorToMessage(error)}</AlertBanner>
        <button type="button" className="btn-secondary" onClick={refetch}>
          Tentar novamente
        </button>
      </>
    );
  }

  if (items.length === 0) {
    return (
      <p className="entity-state">
        Você ainda não tem viagens atribuídas. Quando a operação criar uma, ela aparece aqui.
      </p>
    );
  }

  return (
    <ul className="dash-orders">
      {items.map((trip) => (
        <li key={trip.id}>
          <div>
            <p className="dash-order-customer">
              {trip.deliveryCount} {trip.deliveryCount === 1 ? "parada" : "paradas"}
            </p>
            <p className="dash-order-meta">
              {trip.startedAt
                ? `iniciada em ${dateTime.format(new Date(trip.startedAt))}`
                : `criada em ${dateTime.format(new Date(trip.createdAt))}`}
            </p>
          </div>
          <StatusPill tone={tripStatusTone(trip.status)}>
            {TRIP_STATUS_LABELS[trip.status]}
          </StatusPill>
          <Link className="btn-link" to={`/trips/${trip.id}`}>
            Abrir
          </Link>
        </li>
      ))}
    </ul>
  );
}
