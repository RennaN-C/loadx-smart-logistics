import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { StatusPill } from "../../../components/StatusPill";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { downloadTripReport } from "../../reports/api/reportsApi";
import { ReportDownloadButton } from "../../reports/components/ReportDownloadButton";
import { changeDeliveryStatus, changeTripStatus, getTrip } from "../api/tripsApi";
import {
  DELIVERY_ACTION_LABELS,
  DELIVERY_STATUS_LABELS,
  TRIP_ACTION_LABELS,
  TRIP_STATUS_LABELS,
  deliveryStatusTone,
  tripStatusTone,
} from "../components/tripLabels";
import { mapTripErrorToMessage } from "../components/tripsErrorMessages";
import { DELIVERY_TRANSITIONS, TRIP_TRANSITIONS, type Trip } from "../types";
import "./TripPage.css";

const dateTime = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

/**
 * Acompanhamento de uma viagem (OC34).
 *
 * Assim como os planos, o backend **não lista viagens** — só `POST /trips` e
 * `GET /trips/{id}`. Por isso a tela é sempre `/trips/:tripId`: chega-se aqui a
 * partir do plano aprovado que gerou a viagem.
 */
/** Só quem lê relatório no backend: ADMIN e LOGISTICS_MANAGER (reports/router.py). */
const REPORT_READERS = ["ADMIN", "LOGISTICS_MANAGER"];

export function TripPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const { user } = useAuth();
  const podeBaixarRelatorio = user !== null && REPORT_READERS.includes(user.role);

  const [trip, setTrip] = useState<Trip | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isWorking, setIsWorking] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Motorista opera a própria viagem; o backend confere o vínculo users.driver_id.
  const canOperate = user?.role === "LOGISTICS_MANAGER" || user?.role === "DRIVER";

  const toMessage = (error: unknown) =>
    mapTripErrorToMessage(
      error instanceof ApiError ? error : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado."),
    );

  useEffect(() => {
    if (!tripId) return;

    let active = true;
    setIsLoading(true);
    setErrorMessage(null);

    getTrip(tripId)
      .then((loaded) => {
        if (active) setTrip(loaded);
      })
      .catch((error) => {
        if (active) setErrorMessage(toMessage(error));
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [tripId]);

  async function run(action: () => Promise<Trip>) {
    setErrorMessage(null);
    setIsWorking(true);

    try {
      setTrip(await action());
    } catch (error) {
      setErrorMessage(toMessage(error));
    } finally {
      setIsWorking(false);
    }
  }

  const nextTripStatus = trip ? TRIP_TRANSITIONS[trip.status] : undefined;
  const pendingDeliveries = trip?.deliveries.filter((d) => d.status !== "DELIVERED").length ?? 0;
  const canFinish = trip?.status !== "IN_ROUTE" || pendingDeliveries === 0;

  return (
    <div className="entity-page">
      <header className="entity-header">
        <div>
          <h1>Acompanhamento da viagem</h1>
          <p className="entity-lede">Rota, paradas e situação de cada entrega.</p>
        </div>
        {trip ? (
          <div className="entity-toolbar">
            {podeBaixarRelatorio ? (
              <ReportDownloadButton
                label="Relatório de viagem"
                filename={`relatorio-viagem-${trip.id}.pdf`}
                download={() => downloadTripReport(trip.id)}
              />
            ) : null}
            <StatusPill tone={tripStatusTone(trip.status)}>
              {TRIP_STATUS_LABELS[trip.status]}
            </StatusPill>
          </div>
        ) : null}
      </header>

      {errorMessage ? <AlertBanner>{errorMessage}</AlertBanner> : null}

      {isLoading ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando viagem…</span>
        </p>
      ) : null}

      {trip && !isLoading ? (
        <>
          <section className="trip-head">
            <dl className="trip-meta">
              <div>
                <dt>PARADAS</dt>
                <dd>{trip.deliveries.length}</dd>
              </div>
              <div>
                <dt>EM ABERTO</dt>
                <dd className={pendingDeliveries > 0 ? "trip-meta-warn" : undefined}>
                  {pendingDeliveries}
                </dd>
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

            {canOperate && nextTripStatus ? (
              <button
                type="button"
                className="btn-primary"
                disabled={isWorking || !canFinish}
                title={!canFinish ? "A viagem só finaliza com todas as entregas concluídas" : undefined}
                onClick={() => void run(() => changeTripStatus(trip.id, nextTripStatus))}
              >
                {isWorking ? (
                  <>
                    <span className="spinner" aria-hidden="true" />
                    <span>Processando…</span>
                  </>
                ) : (
                  <span>{TRIP_ACTION_LABELS[trip.status]}</span>
                )}
              </button>
            ) : null}
          </section>

          {trip.status === "SCHEDULED" ? (
            <p className="entity-form-help">
              As entregas só podem ser movimentadas depois que a viagem entrar em rota.
            </p>
          ) : null}

          <ol className="trip-stops">
            {[...trip.deliveries]
              .sort((a, b) => a.sequence - b.sequence)
              .map((delivery) => {
                const next = DELIVERY_TRANSITIONS[delivery.status];
                const enabled = canOperate && next !== undefined && trip.status === "IN_ROUTE";

                return (
                  <li key={delivery.id} className="trip-stop">
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
                        disabled={!enabled || isWorking}
                        onClick={() => void run(() => changeDeliveryStatus(delivery.id, next))}
                      >
                        {DELIVERY_ACTION_LABELS[delivery.status]}
                      </button>
                    ) : null}
                  </li>
                );
              })}
          </ol>
        </>
      ) : null}
    </div>
  );
}
