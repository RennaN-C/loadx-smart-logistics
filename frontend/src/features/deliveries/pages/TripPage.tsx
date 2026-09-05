import { useParams } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { StatusPill } from "../../../components/StatusPill";
import { useAuth } from "../../auth/hooks/useAuth";
import { downloadTripReport } from "../../reports/api/reportsApi";
import { ReportDownloadButton } from "../../reports/components/ReportDownloadButton";
import { canReadReports } from "../../reports/permissions";
import { changeDeliveryStatus, changeTripStatus } from "../api/tripsApi";
import { TRIP_ACTION_LABELS, TRIP_STATUS_LABELS, tripStatusTone } from "../components/tripLabels";
import { TripStops } from "../components/TripStops";
import { TripSummary } from "../components/TripSummary";
import { useTripPage } from "../hooks/useTripPage";
import { TRIP_TRANSITIONS, type Trip } from "../types";
import "./TripPage.css";

/** Frase única: a viagem só fecha com todas as entregas concluídas. */
const FINISH_BLOCKED = "A viagem só finaliza com todas as entregas concluídas";

interface TripActionProps {
  readonly trip: Trip;
  readonly nextStatus: Trip["status"];
  readonly canFinish: boolean;
  readonly isWorking: boolean;
  readonly onRun: (action: () => Promise<Trip>) => void;
}

function TripAction({ trip, nextStatus, canFinish, isWorking, onRun }: TripActionProps) {
  return (
    <button
      type="button"
      className="btn-primary"
      disabled={isWorking || !canFinish}
      title={canFinish ? undefined : FINISH_BLOCKED}
      onClick={() => onRun(() => changeTripStatus(trip.id, nextStatus))}
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
  );
}

/**
 * Acompanhamento de uma viagem (OC34).
 *
 * Chega-se aqui pela lista de viagens ou pelo plano aprovado que a gerou.
 *
 * O componente só desenha: carregamento e transições moram em `useTripPage`, e
 * o resumo e as paradas em componentes próprios. Isso é o que mantém esta
 * função legível — antes ela concentrava busca, transições, resumo, botão de
 * ação e a lista inteira num corpo só.
 */
export function TripPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const { user } = useAuth();
  const { trip, isLoading, isWorking, errorMessage, run } = useTripPage(tripId);

  // Motorista opera a própria viagem; o backend confere o vínculo users.driver_id.
  const canOperate = user?.role === "LOGISTICS_MANAGER" || user?.role === "DRIVER";
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
            {canReadReports(user?.role) ? (
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
            <TripSummary trip={trip} pendingDeliveries={pendingDeliveries} />
            {canOperate && nextTripStatus ? (
              <TripAction
                trip={trip}
                nextStatus={nextTripStatus}
                canFinish={canFinish}
                isWorking={isWorking}
                onRun={(action) => void run(action)}
              />
            ) : null}
          </section>

          {trip.status === "SCHEDULED" ? (
            <p className="entity-form-help">
              As entregas só podem ser movimentadas depois que a viagem entrar em rota.
            </p>
          ) : null}

          <TripStops
            trip={trip}
            canOperate={canOperate}
            isWorking={isWorking}
            onAdvance={(delivery, next) =>
              void run(() => changeDeliveryStatus(delivery.id, next))
            }
          />
        </>
      ) : null}
    </div>
  );
}
