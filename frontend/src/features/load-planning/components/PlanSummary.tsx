import { StatusPill } from "../../../components/StatusPill";
import { PlanContinuity } from "./PlanContinuity";
import type { LoadPlan } from "../types";
import { PLAN_STATUS_LABELS, planStatusTone } from "./loadPlanLabels";

const percent = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const weight = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const volume = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });

interface PlanSummaryProps {
  readonly plan: LoadPlan;
  readonly canManage: boolean;
  readonly approvalAllowed?: boolean;
  readonly isWorking: boolean;
  readonly showContinuity?: boolean;
  readonly onApprove: () => void;
  readonly onRecalculate: () => void;
}

export function PlanSummary({ plan, canManage, approvalAllowed = canManage, isWorking, onApprove, onRecalculate, showContinuity = true }: PlanSummaryProps) {
  const hasRejections = plan.unloadedCount > 0;
  const inactiveDistribution = inactive(plan);
  const canApprove = !inactiveDistribution && approvalAllowed && plan.status === "CALCULATED" && !hasRejections && plan.ordersReadyForApproval !== false;

  return (
    <section className="plan-summary">
      <header className="plan-summary-head">
        <div>
          <h2>Resultado do cálculo</h2>
          <p className="entity-lede">
            Algoritmo {plan.algorithmVersion}
            {plan.recalculatedFromId ? " · recalculado de um plano anterior" : ""}
          </p>
        </div>
        <StatusPill tone={inactiveDistribution ? "neutral" : planStatusTone(plan.status)}>
          {plan.distributionStatus === "CANCELED" ? "Distribuição cancelada"
            : plan.distributionStatus === "INCOMPLETE" ? "Distribuição incompleta"
              : plan.isCurrentPart === false ? "Versão anterior do plano"
                : PLAN_STATUS_LABELS[plan.status]}
        </StatusPill>
      </header>

      {inactiveDistribution ? <p className="entity-form-help" role="status">
        Este plano não integra uma distribuição ativa. O resultado físico
        ({PLAN_STATUS_LABELS[plan.status].toLowerCase()}) permanece disponível para consulta histórica,
        mas a operação deve ser retomada pela distribuição ou por um novo planejamento.
      </p> : null}

      <dl className="plan-metrics">
        <div>
          <dt>APROVEITAMENTO</dt>
          <dd className="plan-metric-strong">{percent.format(plan.occupancyPercent)}%</dd>
        </div>
        <div>
          <dt>VOLUME USADO</dt>
          <dd>
            {volume.format(plan.usedVolumeCm3 / 1_000_000)} de{" "}
            {volume.format(plan.internalVolumeCm3 / 1_000_000)} m³
          </dd>
        </div>
        <div>
          <dt>PESO TOTAL</dt>
          <dd>{weight.format(plan.totalWeightKg)} kg</dd>
        </div>
        <div>
          <dt>CARREGADOS</dt>
          <dd>{plan.loadedCount}</dd>
        </div>
        <div>
          <dt>DE FORA</dt>
          <dd className={hasRejections ? "plan-metric-warn" : undefined}>{plan.unloadedCount}</dd>
        </div>
      </dl>

      <div className="plan-occupancy" aria-hidden="true">
        <div className="plan-occupancy-fill" style={{ width: `${Math.min(plan.occupancyPercent, 100)}%` }} />
      </div>

      {showContinuity ? <PlanOperationalContinuity plan={plan} canManage={canManage} /> : null}

      {plan.status === "CALCULATED" && plan.ordersReadyForApproval === false ? <output className="entity-form-help">Os pedidos deste cálculo já saíram da fila de planejamento. Consulte o estado atual em Pedidos; este plano permanece disponível como histórico e não pode ser aprovado novamente.</output> : null}
      {(canManage || approvalAllowed) && plan.status !== "APPROVED" ? (
        <div className="entity-form-actions">
          {canManage && <button type="button" className="btn-secondary" disabled={isWorking || plan.ordersReadyForApproval === false} onClick={onRecalculate}>
            Recalcular
          </button>}
          <button
            type="button"
            className="btn-primary"
            disabled={!canApprove || isWorking}
            title={
              hasRejections
                ? "O backend recusa aprovar plano com volume de fora"
                : undefined
            }
            onClick={onApprove}
          >
            {isWorking ? (
              <>
                <span className="spinner" aria-hidden="true" />
                <span>Processando…</span>
              </>
            ) : (
              <span>Aprovar plano</span>
            )}
          </button>
        </div>
      ) : null}

      {hasRejections && plan.status === "CALCULATED" ? (
        <p className="entity-form-help">
          Plano com volume de fora não pode ser aprovado. Tire um pedido da seleção, escolha um caminhão
          maior ou revise o cadastro dos produtos recusados.
        </p>
      ) : null}
    </section>
  );
}

function inactive(plan: LoadPlan): boolean {
  return plan.distributionStatus === "CANCELED" ||
    plan.distributionStatus === "INCOMPLETE" || plan.partStatus === "CANCELED" ||
    plan.isCurrentPart === false;
}

export function PlanOperationalContinuity({ plan, canManage }: { readonly plan: LoadPlan; readonly canManage: boolean }) {
  return plan.status === "APPROVED" && !inactive(plan) ? <PlanContinuity key={plan.id} planId={plan.id} canManage={canManage} /> : null;
}
