import { StatusPill } from "../../../components/StatusPill";
import type { LoadPlan } from "../types";
import { PLAN_STATUS_LABELS, planStatusTone } from "./loadPlanLabels";

const percent = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const weight = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const volume = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });

interface PlanSummaryProps {
  readonly plan: LoadPlan;
  readonly canManage: boolean;
  readonly isWorking: boolean;
  readonly onApprove: () => void;
  readonly onRecalculate: () => void;
}

export function PlanSummary({ plan, canManage, isWorking, onApprove, onRecalculate }: PlanSummaryProps) {
  const hasRejections = plan.unloadedCount > 0;
  const canApprove = canManage && plan.status === "CALCULATED" && !hasRejections;

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
        <StatusPill tone={planStatusTone(plan.status)}>{PLAN_STATUS_LABELS[plan.status]}</StatusPill>
      </header>

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

      {canManage ? (
        <div className="entity-form-actions">
          <button type="button" className="btn-secondary" disabled={isWorking} onClick={onRecalculate}>
            Recalcular
          </button>
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
