import { useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import {
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
}

/** Only a read-only preflight. Never renders a button to mutate operations. */
export function TripCancellationPreflightPanel({ tripId }: Props) {
  const [report, setReport] = useState<CancellationPreflight | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function check() {
    setLoading(true);
    setError("");
    setReport(null);
    try {
      setReport(await getCancellationPreflight(tripId));
    } catch {
      setError("Não foi possível verificar a elegibilidade do cancelamento.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="entity-section" aria-label="Análise de cancelamento">
      <h2>Verificação de cancelamento</h2>
      <p className="entity-form-help">
        Consulta os bloqueios operacionais sem cancelar a viagem nem liberar
        caminhões. O cancelamento efetivo ainda não está habilitado.
      </p>
      <button type="button" className="btn-secondary" disabled={loading} onClick={() => void check()}>
        {loading ? "Verificando..." : "Verificar bloqueios"}
      </button>
      {error ? <AlertBanner>{error}</AlertBanner> : null}
      {report ? (
        <div role="status">
          {report.safe_for_cancellation_workflow ? (
            <p>
              Não foram identificados bloqueios iniciais. A execução ainda
              depende de reconciliação transacional e nova verificação.
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
        </div>
      ) : null}
    </section>
  );
}
