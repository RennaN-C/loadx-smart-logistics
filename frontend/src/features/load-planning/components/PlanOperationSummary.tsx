import { Link } from "react-router-dom";

import { StatusPill, type StatusTone } from "../../../components/StatusPill";
import { TRIP_STATUS_LABELS } from "../../deliveries/components/tripLabels";
import type { PlanOperation, PlanOperationStatus } from "../types";

const labels: Record<PlanOperationStatus, string> = {
  NOT_STARTED: "Operação não iniciada", IN_PROGRESS: "Operação em andamento",
  PARTIALLY_DELIVERED: "Entrega parcial", COMPLETED: "Operação concluída", INCOMPLETE: "Distribuição incompleta", CANCELED: "Operação cancelada",
};
const tones: Partial<Record<PlanOperationStatus, StatusTone>> = { COMPLETED: "good", PARTIALLY_DELIVERED: "warn", CANCELED: "neutral", INCOMPLETE: "warn" };
const loadingLabels = { PENDING: "Pendente", IN_PROGRESS: "Em andamento", FINISHED: "Concluído" };

export function PlanOperationSummary({ operation, showLinks = true }: { readonly operation: PlanOperation; readonly showLinks?: boolean }) {
  const tone: StatusTone = tones[operation.status] ?? "neutral";
  return <div className="plan-operation-summary" aria-label="Situação logística">
    <StatusPill tone={tone}>{labels[operation.status]}</StatusPill>
    <p>Pedidos entregues: {operation.delivered_order_count} de {operation.order_count}
      {operation.partial_order_count > 0 ? ` · ${operation.partial_order_count} com entrega parcial` : ""}</p>
    {operation.loading_status ? <p>Carregamento: {loadingLabels[operation.loading_status]}</p> : null}
    {operation.trip_status ? <p>Viagem: {TRIP_STATUS_LABELS[operation.trip_status]}</p> : null}
    {showLinks ? <div className="plan-operation-links">
      {operation.trip_id ? <Link to={`/trips/${operation.trip_id}`}>Abrir viagem existente</Link> : null}
      {operation.loading_session_id ? <Link to={`/loading/${operation.loading_session_id}`}>Abrir carregamento</Link> : null}
      {operation.delivered_order_count > 0 ? <Link to="/orders?status=DELIVERED">Consultar pedidos entregues</Link> : null}
    </div> : null}
  </div>;
}
