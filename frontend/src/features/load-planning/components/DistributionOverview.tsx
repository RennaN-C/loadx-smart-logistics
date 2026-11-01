import { useState } from "react";
import { StatusPill } from "../../../components/StatusPill";
import type { LoadDistribution } from "../types";
import { DISTRIBUTION_LABELS } from "./distributionLabels";

function distributionGuidance(status: LoadDistribution["status"]): string {
  switch (status) {
    case "APPROVED": return "Distribuição aprovada. Consulte o carregamento e as viagens de cada caminhão.";
    case "CANCELED": return "Distribuição cancelada. Os volumes foram liberados e este registro permanece apenas como histórico. Para planejar novamente, crie uma nova distribuição.";
    case "INCOMPLETE": return "Distribuição interrompida: reprocesse as partes canceladas para retomar. Nenhuma operação será liberada antes da aprovação completa.";
    default: return "Proposta salva, mas ainda não aprovada. Revise cada veículo antes de iniciar o carregamento.";
  }
}

export function DistributionOverview({ distribution, canApprove, working, disabled, onAction }: {
  readonly distribution: LoadDistribution; readonly canApprove: boolean;
  readonly working: boolean; readonly disabled: boolean;
  readonly onAction: (action: "approve" | "cancel") => void;
}) {
  const [confirmCancel, setConfirmCancel] = useState(false);
  const mutable = distribution.status !== "APPROVED" && distribution.status !== "CANCELED";
  return (
      <section className="distribution-overview" aria-label="Resumo da distribuição" aria-busy={working}>
        <div className="distribution-overview-heading"><div><span className="distribution-eyebrow">Distribuição {distribution.id.slice(0, 8)}</span><h2>{distribution.truckCount} {distribution.truckCount === 1 ? "caminhão" : "caminhões"} para esta carga</h2></div><StatusPill tone={distribution.status === "APPROVED" ? "good" : distribution.status === "CANCELED" ? "neutral" : "warn"}>{DISTRIBUTION_LABELS[distribution.status]}</StatusPill></div>
        <div className="distribution-totals"><span><strong>{distribution.orderIds.length}</strong> {distribution.orderIds.length === 1 ? "pedido" : "pedidos"}</span><span><strong>{distribution.volumeCount}</strong> volumes físicos</span><span>Salva em {new Date(distribution.createdAt).toLocaleString("pt-BR")}</span></div>
        <details className="distribution-method"><summary>Como a distribuição foi calculada</summary><p>{distribution.truckCount === 1 ? "A solução persistida acomoda toda a necessidade em um caminhão." : "A solução persistida distribui a necessidade entre estes veículos. A busca tenta um caminhão antes de ampliar a frota, respeitando as regras físicas no servidor."} A busca é heurística; não representa garantia de ótimo global.</p></details>
        <p className="entity-form-help">{distributionGuidance(distribution.status)}</p>
        {canApprove && mutable ? <div className="entity-form-actions">
          <button type="button" className="btn-secondary" disabled={disabled} onClick={() => setConfirmCancel(true)}>Cancelar distribuição</button>
          <button type="button" className="btn-primary" disabled={disabled || distribution.status === "INCOMPLETE"} onClick={() => onAction("approve")}>{working ? "Processando…" : "Aprovar distribuição completa"}</button>
        </div> : null}
        {distribution.status === "INCOMPLETE" ? <p className="distribution-notice">Reprocesse as partes canceladas antes da aprovação completa.</p> : null}
        {confirmCancel ? <fieldset className="distribution-confirm" aria-label="Confirmar cancelamento da distribuição"><p>Cancelar toda a distribuição? Os volumes serão liberados para uma nova proposta. O histórico será preservado.</p><button type="button" className="btn-secondary" disabled={disabled} onClick={() => setConfirmCancel(false)}>Manter distribuição</button><button type="button" className="btn-secondary" disabled={disabled} onClick={() => { setConfirmCancel(false); onAction("cancel"); }}>Confirmar cancelamento</button></fieldset> : null}
      </section>
  );
}
