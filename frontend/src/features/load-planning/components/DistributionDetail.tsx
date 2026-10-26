import { lazy, Suspense, useState } from "react";
import { Link } from "react-router-dom";
import { Tabs } from "../../../components/Tabs";
import type { DistributionPart, LoadDistribution } from "../types";
import { DistributionPartActions } from "./DistributionPartActions";
import { PART_LABELS } from "./distributionLabels";
import { PlanContinuity } from "./PlanContinuity";
import { PlanItemsTable } from "./PlanItemsTable";
import { PlanAIExplanation } from "./PlanAIExplanation";

const LoadViewer = lazy(() => import("../../load-visualization/components/LoadViewer").then((m) => ({ default: m.LoadViewer })));
const RESULT_TABS = [{ id: "summary", label: "Volumes e sequência" }, { id: "scene", label: "Visualização 3D" }] as const;

export function DistributionDetail({ distribution, part, canApprove, canCreate, disabled, onAction, onReprocess }: {
  readonly distribution: LoadDistribution; readonly part: DistributionPart;
  readonly canApprove: boolean; readonly canCreate: boolean; readonly disabled: boolean;
  readonly onAction: (action: "approve" | "cancel", partId?: string) => void;
  readonly onReprocess: (truckId: string) => void;
}) {
  const [tab, setTab] = useState<"summary" | "scene">("summary");
  return (
      <section id="distribution-vehicle-detail" className="distribution-detail" aria-label={`Carga de ${part.truck.plate}`}>
        <header className="distribution-detail-heading"><div><span className="distribution-eyebrow">Parte {part.id.slice(0, 8)} · Plano {part.loadPlan.id.slice(0, 8)}</span><h2>Carga de {part.truck.plate}</h2><p>{PART_LABELS[part.status]} · {part.truck.model}</p></div><Link className="btn-secondary" to={`/planning/${part.loadPlan.id}`}>Abrir plano desta parte</Link></header>
        <p className="entity-form-help">Baú {part.truck.lengthCm} × {part.truck.widthCm} × {part.truck.heightCm} cm · Capacidade {part.truck.maxWeightKg.toLocaleString("pt-BR")} kg · {part.loadPlan.unloadedCount} volumes rejeitados.</p>
        <DistributionPartActions key={`${part.id}-${part.loadPlan.id}-${part.status}`} distribution={distribution} part={part} canApprove={canApprove} canCreate={canCreate} disabled={disabled}
          onAction={(action, partId) => onAction(action, partId)}
          onReprocess={(truckId) => onReprocess(truckId)} />
        <PlanAIExplanation key={part.loadPlan.id} planId={part.loadPlan.id} />
        <Tabs items={RESULT_TABS} active={tab} onChange={setTab} label="Detalhes da carga selecionada" />
        <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
          {tab === "summary" ? <PlanItemsTable items={part.loadPlan.items} /> : <Suspense fallback={<p className="entity-state">Carregando visualização 3D…</p>}><LoadViewer key={part.loadPlan.id} planId={part.loadPlan.id} plan={part.loadPlan} /></Suspense>}
        </div>
        {distribution.status === "APPROVED" ? <PlanContinuity key={part.loadPlan.id} planId={part.loadPlan.id} canManage={canCreate} /> : null}
      </section>
  );
}
