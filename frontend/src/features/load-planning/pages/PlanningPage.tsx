import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { Tabs, type TabItem } from "../../../components/Tabs";
import { ApiError } from "../../../types/api";
import { useAuth } from "../../auth/hooks/useAuth";
import { canManageLogistics } from "../../auth/permissions";
import { AuditTrail } from "../../audit/components/AuditTrail";
import { downloadLoadingReport } from "../../reports/api/reportsApi";
import { ReportDownloadButton } from "../../reports/components/ReportDownloadButton";
import { canReadReports } from "../../reports/permissions";
import { approveLoadPlan, getLoadPlan, recalculateLoadPlan } from "../api/loadPlansApi";
import { PlanHistory } from "../components/PlanHistory";
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

export function PlanningPage() {
  const { planId } = useParams<{ planId: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const isNew = searchParams.get("tab") === "new";
  const { user } = useAuth();
  const podeBaixarRelatorio = canReadReports(user?.role);

  const [storedPlan, setPlan] = useState<LoadPlan | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isWorking, setIsWorking] = useState(false);
  const [tab, setTab] = useState<PlanTab>("summary");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const mounted = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  const currentId = useRef(planId);
  currentId.current = planId;
  const plan = storedPlan?.id === planId ? storedPlan : null;

  const canManage = canManageLogistics(user?.role);

  const toMessage = (error: unknown) =>
    mapLoadPlanErrorToMessage(
      error instanceof ApiError ? error : new ApiError("UNKNOWN_ERROR", "Ocorreu um erro inesperado."),
    );

  useEffect(() => {
    setPlan(null);
    setIsWorking(false);
    setErrorMessage(null);
    if (!planId || !user?.active || !["ADMIN", "LOGISTICS_MANAGER", "CHECKER"].includes(user.role)) {
      setIsLoading(false);
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
  }, [planId, user?.role, user?.active]);

  const handleCalculated = useCallback(
    (created: LoadPlan) => {
      if (!mounted.current || currentId.current !== undefined) return;
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
      if (!mounted.current || currentId.current !== plan.id) return;
      if (result.id === plan.id) {
        setPlan(result);
      } else {
        // Recalcular gera um plano NOVO. Só navegar já basta: o efeito carrega
        // pelo id da URL, e assim não existem duas fontes de verdade.
        navigate(`/planning/${result.id}`);
      }
    } catch (error) {
      if (mounted.current && currentId.current === plan.id) setErrorMessage(toMessage(error));
    } finally {
      if (mounted.current && currentId.current === plan.id) setIsWorking(false);
    }
  }

  if (!user?.active || !["ADMIN", "LOGISTICS_MANAGER", "CHECKER"].includes(user.role)) {
    return <div className="entity-page"><h1>Planejamento de carga</h1><AlertBanner>Seu perfil não tem acesso ao planejamento.</AlertBanner><Link to="/">Voltar ao início</Link></div>;
  }

  return (
    <div className="entity-page">
      <nav className="entity-toolbar entity-page-nav" aria-label="Caminhos do planejamento">
        <Link to="/">Voltar ao início</Link>
        {user?.role !== "DRIVER" ? <Link to="/orders">Voltar aos pedidos</Link> : null}
        {planId && user?.role !== "DRIVER" ? <Link to="/planning">Voltar ao planejamento</Link> : null}
      </nav>
      <header className="entity-header">
        <div>
          <h1>Planejamento de carga</h1>
          <p className="entity-lede">Retome planos salvos ou prepare uma nova carga.</p>
        </div>
        {plan ? (
          <div className="entity-toolbar">
            {podeBaixarRelatorio ? (
              <ReportDownloadButton
                label="Relatório de carregamento"
                filename={`relatorio-carregamento-${plan.id}.pdf`}
                download={() => downloadLoadingReport(plan.id)}
              />
            ) : null}
            {canManage ? <button type="button" className="btn-secondary" onClick={() => navigate("/planning?tab=new")}>Novo plano</button> : null}
          </div>
        ) : null}
      </header>

      {errorMessage ? <AlertBanner>{errorMessage}</AlertBanner> : null}

      {isLoading ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando plano…</span>
        </p>
      ) : null}

      {!planId && !isLoading ? <>
        <nav className="plan-workspace-nav" aria-label="Área de planejamento">
          <Link to="/planning" aria-current={!isNew ? "page" : undefined}>Planos existentes</Link>
          {canManage ? <Link to="/planning?tab=new" aria-current={isNew ? "page" : undefined}>Novo planejamento</Link> : null}
        </nav>
        {isNew && canManage ? <><p className="entity-form-help">Seleções ainda não calculadas são rascunhos desta tela. O plano será salvo somente ao calcular (até 200 volumes).</p><PlanBuilder onCalculated={handleCalculated} /></>
          : <PlanHistory checker={user?.role === "CHECKER"} />}
      </> : null}

      {plan && !isLoading ? (
        <>
          <p className="entity-form-help">Plano {plan.id.slice(0, 8)} salvo. <Link to={`/planning/${plan.id}`}>Abrir este plano</Link> ou reencontre em <Link to="/planning">Planos existentes</Link>.</p>
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

          {user?.role === "ADMIN" || user?.role === "LOGISTICS_MANAGER" ? (
            <AuditTrail entityType="LOAD_PLAN" entityId={plan.id} title="Histórico do plano" />
          ) : null}
        </>
      ) : null}
    </div>
  );
}
