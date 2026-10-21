import { Link } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { Pagination } from "../../../components/Pagination";
import { StatusPill } from "../../../components/StatusPill";
import { useResourceList } from "../../../hooks/useResourceList";
import { useAuth } from "../../auth/hooks/useAuth";
import { listTrips } from "../api/tripsApi";
import { TRIP_STATUS_LABELS, tripStatusTone } from "../components/tripLabels";
import { mapTripErrorToMessage } from "../components/tripsErrorMessages";
import "./TripListPage.css";

const dateTime = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

/**
 * Lista de viagens (parte da OC93).
 *
 * `CONFIRMADO`: até aqui a única forma de abrir uma viagem era conhecer o UUID
 * ou chegar pelo plano que a gerou — que é exatamente a "dependência de entrar
 * por fluxos indiretos" que a OC93 existe para eliminar.
 *
 * O recorte por perfil é do backend: `GET /trips` devolve todas para quem
 * gerencia e somente as próprias para o motorista. Esta tela não filtra nada —
 * repetir o recorte aqui duplicaria no cliente uma regra de acesso que já é
 * aplicada onde importa.
 *
 * `RISCO IDENTIFICADO`: a OC93 pede o mesmo para **Carregamentos** e
 * **Entregas**, e esses dois não têm rota de listagem no backend —
 * `/loading-sessions` só expõe `/{session_id}`, e entregas só aparecem dentro
 * de uma viagem. Enquanto isso não existir, só este terço da ocorrência é
 * construível.
 */
export function TripListPage() {
  const { user } = useAuth();
  const { status, items, error, refetch, page, total, totalPages, goToPage } =
    useResourceList(listTrips);

  const isDriver = user?.role === "DRIVER";

  return (
    <div className="entity-page">
      <header className="entity-header">
        <div>
          <h1>Viagens</h1>
          <p className="entity-lede">
            {isDriver
              ? "As viagens atribuídas a você."
              : "Viagens criadas a partir dos planos aprovados."}
          </p>
        </div>
      </header>

      {status === "loading" ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando viagens…</span>
        </p>
      ) : null}

      {status === "error" && error ? (
        <>
          <AlertBanner>{mapTripErrorToMessage(error)}</AlertBanner>
          <button type="button" className="btn-secondary" onClick={() => void refetch()}>
            Tentar novamente
          </button>
        </>
      ) : null}

      {status === "success" && items.length === 0 ? (
        <p className="entity-state">
          {isDriver
            ? "Você ainda não tem viagens atribuídas."
            : "Nenhuma viagem criada ainda. Elas nascem de um plano de carga aprovado."}
        </p>
      ) : null}

      {items.length > 0 ? (
        <div className="trip-list-scroll" role="region" aria-label="Viagens" tabIndex={0}>
          <table className="trip-list">
            <caption className="sr-only">Viagens, da mais recente para a mais antiga</caption>
            <thead>
              <tr>
                <th scope="col">Situação</th>
                <th scope="col">Paradas</th>
                <th scope="col">Criada em</th>
                <th scope="col">Início</th>
                <th scope="col">Ação</th>
              </tr>
            </thead>
            <tbody>
              {items.map((trip) => (
                <tr key={trip.id}>
                  <td>
                    <StatusPill tone={tripStatusTone(trip.status)}>
                      {TRIP_STATUS_LABELS[trip.status]}
                    </StatusPill>
                  </td>
                  <td className="trip-list-count">
                    {trip.deliveryCount} {trip.deliveryCount === 1 ? "parada" : "paradas"}
                  </td>
                  <td className="trip-list-date">
                    {dateTime.format(new Date(trip.createdAt))}
                  </td>
                  <td className="trip-list-date">
                    {trip.startedAt ? dateTime.format(new Date(trip.startedAt)) : "—"}
                  </td>
                  <td>
                    <Link className="btn-link" to={`/trips/${trip.id}`}>
                      Abrir
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {status === "success" && total > 0 ? (
        <Pagination page={page} totalPages={totalPages} onChange={goToPage} label="viagens" />
      ) : null}
    </div>
  );
}
