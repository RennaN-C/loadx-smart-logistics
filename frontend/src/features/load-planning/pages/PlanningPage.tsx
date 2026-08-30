import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { Tabs, type TabItem } from "../../../components/Tabs";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { approveLoadPlan, getLoadPlan, recalculateLoadPlan } from "../api/loadPlansApi";
import { PlanBuilder } from "../components/PlanBuilder";
import { PlanItemsTable } from "../components/PlanItemsTable";
import { PlanSummary } from "../components/PlanSummary";
import { mapLoadPlanErrorToMessage } from "../components/loadPlansErrorMessages";
import type { LoadPlan } from "../types";
import "./PlanningPage.css";

/**
 * O three.js pesa ~600 kB. Carregar sob demanda mantém o pacote principal leve
 * para quem nunca abre a aba 3D — que é a maioria das visitas às outras telas.
 */
const LoadViewer = lazy(() =>
  import("../../load-visualization/components/LoadViewer").then((m) => ({ default: m.LoadViewer })),
);

type PlanTab = "summary" | "scene";

const PLAN_TABS: readonly TabItem<PlanTab>[] = [
  { id: "summary", label: "Resumo e sequência" },
  { id: "scene", label: "Visualização 3D" },
];

/**
 * O backend não tem listagem de planos — só criar e buscar por id. Por isso o
 * plano vive na URL (`/planning/:planId`): sem isso, recarregar a página perderia
 * o resultado sem nenhuma forma de recuperá-lo.
 */
export function PlanningPage() {
  const { planId } = useParams<{ planId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [plan, setPlan] = useState<LoadPlan | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isWorking, setIsWorking] = useState(false);
  const [tab, setTab] = useState<PlanTab>("summary");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const canManage = user?.role === "LOGISTICS_MANAGER";

  const toMessage = (error: unknown) =>
    mapLoadPlanErrorToMessage(
      error instanceof ApiError ? error : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado."),
    );

  useEffect(() => {
    if (!planId) {
      setPlan(null);
      return;
    }

    let active = true;
    setIsLoading(true);
    setErrorMessage(null);

    getLoadPlan(planId)
      .then((loaded) => {
        if (active) setPlan(loaded);
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
  }, [planId]);

  const handleCalculated = useCallback(
    (created: LoadPlan) => {
      setPlan(created);
      navigate(`/planning/${created.id}`);
    },
    [navigate],
  );

  async function runAction(action: (id: string) => Promise<LoadPlan>) {
    if (!plan) return;
    setErrorMessage(null);
    setIsWorking(true);

    try {
      const result = await action(plan.id);
      if (result.id === plan.id) {
        setPlan(result);
      } else {
        // Recalcular gera um plano NOVO. Só navegar já basta: o efeito carrega
        // pelo id da URL, e assim não existem duas fontes de verdade.
        navigate(`/planning/${result.id}`);
      }
    } catch (error) {
      setErrorMessage(toMessage(error));
    } finally {
      setIsWorking(false);
    }
  }

  return (
    <div className="entity-page">
      <header className="entity-header">
        <div>
          <h1>Planejamento de carga</h1>
          <p className="entity-lede">Escolha o caminhão e os pedidos; o otimizador monta a carga.</p>
        </div>
        {plan ? (
          <button type="button" className="btn-secondary" onClick={() => navigate("/planning")}>
            Novo plano
          </button>
        ) : null}
      </header>

      {errorMessage ? <AlertBanner>{errorMessage}</AlertBanner> : null}

      {isLoading ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando plano…</span>
        </p>
      ) : null}

      {!planId && !isLoading ? <PlanBuilder onCalculated={handleCalculated} /> : null}

      {plan && !isLoading ? (
        <>
          <PlanSummary
            plan={plan}
            canManage={canManage}
            isWorking={isWorking}
            onApprove={() => void runAction(approveLoadPlan)}
            onRecalculate={() => void runAction(recalculateLoadPlan)}
          />

          <Tabs items={PLAN_TABS} active={tab} onChange={setTab} label="Formato do resultado" />

          <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
            {tab === "summary" ? (
              <PlanItemsTable items={plan.items} />
            ) : (
              <Suspense
                fallback={
                  <p className="entity-state">
                    <span className="spinner" aria-hidden="true" />
                    <span>Carregando visualização 3D…</span>
                  </p>
                }
              >
                <LoadViewer planId={plan.id} plan={plan} />
              </Suspense>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}
