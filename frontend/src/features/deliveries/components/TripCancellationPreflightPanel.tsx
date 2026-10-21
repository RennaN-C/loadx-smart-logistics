import { useRef, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import {
  cancelScheduledTrip,
  getCancellationPreflight,
  type CancellationPreflight,
} from "../api/cancellationPreflightApi";

const reasons: Record<string, string> = {
  TRIP_ALREADY_STARTED_OR_FINISHED: "A viagem já começou ou foi finalizada.",
  LOADING_SESSION_EXISTS: "Existe uma sessão de carregamento, inclusive se pendente.",
  DELIVERY_ALREADY_STARTED_OR_MISSING: "Há entrega iniciada, concluída ou nenhuma entrega.",
  MULTI_TRUCK_PART_REQUIRES_RECONCILIATION: "A distribuição possui partes em outros caminhões.",
};

interface Props {
  readonly tripId: string;
  readonly canCancel?: boolean;
  readonly onCanceled?: () => Promise<void>;
}

/** Only a read-only preflight. Never renders a button to mutate operations. */
export function TripCancellationPreflightPanel({ tripId, canCancel = true, onCanceled }: Props) {
  const [report, setReport] = useState<CancellationPreflight | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [reason, setReason] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const requestKey = useRef<string | null>(null);

  async function check() {
    setLoading(true);
    setError("");
    setReport(null);
    setConfirming(false);
    try {
      setReport(await getCancellationPreflight(tripId));
    } catch {
      setError("Não foi possível verificar a elegibilidade do cancelamento.");
    } finally {
      setLoading(false);
    }
  }

  async function cancel() {
    if (!report?.safe_for_cancellation_workflow || reason.trim().length < 8) return;
    setSubmitting(true);
    setError("");
    if (!requestKey.current) requestKey.current = crypto.randomUUID();
    try {
      await cancelScheduledTrip(tripId, reason.trim(), requestKey.current);
      setReport(null);
      setConfirming(false);
      setReason("");
      requestKey.current = null;
      await onCanceled?.();
    } catch {
      setError("Cancelamento não confirmado. Refaça a consulta de elegibilidade.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="entity-section" aria-label="Análise de cancelamento">
      <h2>Verificação de cancelamento</h2>
      <p className="entity-form-help">
        Consulta os bloqueios operacionais sem cancelar a viagem nem liberar
        caminhões. O cancelamento exige motivo, confirmação e uma nova validação transacional.
      </p>
      <button type="button" className="btn-secondary" disabled={loading} onClick={() => void check()}>
        {loading ? "Verificando..." : "Verificar bloqueios"}
      </button>
      {error ? <AlertBanner>{error}</AlertBanner> : null}
      {report ? (
        <div role="status">
          {report.safe_for_cancellation_workflow ? (
            <p>
              Pré-validação aprovada. O servidor revalidará tudo ao confirmar.
            </p>
          ) : (
            <>
              <p>Cancelamento bloqueado neste momento:</p>
              <ul>
                {report.blocking_reasons.map((reason) => (
                  <li key={reason}>{reasons[reason] ?? reason}</li>
                ))}
              </ul>
            </>
          )}
          {report.safe_for_cancellation_workflow && canCancel ? (
            confirming ? (
              <div>
                <label htmlFor="cancel-reason">Motivo do cancelamento</label>
                <textarea
                  id="cancel-reason"
                  rows={3}
                  maxLength={500}
                  value={reason}
                  disabled={submitting}
                  onChange={(event) => {
                    setReason(event.target.value);
                    requestKey.current = null;
                  }}
                />
                <p className="entity-form-help">
                  Viagens divididas serão encaminhadas para reprocessamento da parte.
                </p>
                <button type="button" className="btn-secondary"
                  disabled={submitting} onClick={() => setConfirming(false)}>Voltar</button>
                <button type="button" className="btn-primary"
                  disabled={submitting || reason.trim().length < 8}
                  onClick={() => void cancel()}>
                  {submitting ? "Cancelando..." : "Confirmar cancelamento"}
                </button>
              </div>
            ) : (
              <button type="button" className="btn-secondary"
                onClick={() => setConfirming(true)}>Solicitar cancelamento</button>
            )
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
