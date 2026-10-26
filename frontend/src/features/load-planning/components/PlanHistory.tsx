import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { Pagination } from "../../../components/Pagination";
import { StatusPill } from "../../../components/StatusPill";
import type { Page } from "../../../types/api";
import { listLoadPlans } from "../api/loadPlansApi";
import type { LoadPlanListItem, LoadPlanStatus } from "../types";
import { PlanOperationSummary } from "./PlanOperationSummary";
import { PLAN_STATUS_LABELS, planStatusTone } from "./loadPlanLabels";
import { DISTRIBUTION_LABELS } from "./distributionLabels";

const date = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

function PlanHistoryRow({ plan, canReadOrigin }: { readonly plan: LoadPlanListItem; readonly canReadOrigin: boolean }) {
  const destination = plan.distributionId ? `/planning/distributions/${plan.distributionId}` : `/planning/${plan.id}`;
  const isDistributionCanceled = plan.distributionStatus === "CANCELED";
  const isIncomplete = plan.distributionStatus === "INCOMPLETE" || plan.operation?.status === "INCOMPLETE";
  const isCanceled = isDistributionCanceled || (!isIncomplete &&
    (plan.partStatus === "CANCELED" || plan.operation?.status === "CANCELED"));
  const historicalVersion = plan.isCurrentPart === false;
  const lifecycleStatus = isDistributionCanceled ? "Cancelada"
    : isIncomplete ? "Incompleta"
      : isCanceled ? "Cancelada"
        : historicalVersion ? "Versão anterior"
          : plan.distributionStatus ? DISTRIBUTION_LABELS[plan.distributionStatus] : null;
  return <li className="plan-history-row">
    <div className="plan-history-identification">
      <div className="plan-history-title"><h3><Link to={destination}>Plano {plan.id.slice(0, 8).toLocaleUpperCase("pt-BR")}</Link></h3>{lifecycleStatus ? <StatusPill tone={isCanceled || historicalVersion ? "neutral" : plan.distributionStatus === "APPROVED" ? "good" : "warn"}>{isCanceled && !isDistributionCanceled && !isIncomplete ? "Operação" : plan.distributionId ? "Distribuição" : "Operação"}: {lifecycleStatus}</StatusPill> : <StatusPill tone={planStatusTone(plan.status)}>Plano: {PLAN_STATUS_LABELS[plan.status]}</StatusPill>}</div>
      <Link className="plan-history-plate" to={`/planning?truck=${plan.truckId}`} aria-label={`Filtrar planos do caminhão ${plan.truckPlate}`}>{plan.truckPlate}</Link>
      <p>{plan.truckModel}</p>
      {plan.distributionId ? <p>Parte da distribuição {plan.distributionId.slice(0, 8)}</p> : null}
      <time dateTime={plan.createdAt}>Criado em {date.format(new Date(plan.createdAt))}</time>
    </div>
    <div className="plan-history-summary">
      {isDistributionCanceled ? <p className="entity-form-help" role="status">Esta distribuição foi cancelada. A carga não está ativa; o cálculo permanece para consulta e auditoria.</p>
        : isCanceled ? <p className="entity-form-help" role="status">Esta operação foi cancelada. O registro está disponível apenas para consulta histórica.</p>
        : isIncomplete ? <p className="entity-form-help" role="status">Distribuição incompleta. Uma parte precisa ser reprocessada antes de continuar.</p>
          : historicalVersion ? <p className="entity-form-help">Versão substituída por um reprocessamento. Consulte a distribuição para ver a carga atual.</p>
            : plan.operation ? <PlanOperationSummary operation={plan.operation} /> : null}
      {lifecycleStatus ? <p className="entity-form-help">Resultado físico do cálculo: {PLAN_STATUS_LABELS[plan.status].toLowerCase()}.</p> : null}
      <p className="plan-history-facts"><span>{plan.orderCount} pedido(s)</span><span>{plan.loadedCount} volumes</span><span>{plan.totalWeightKg.toLocaleString("pt-BR")} kg</span></p>
      <div className="plan-history-occupancy"><span style={{ width: `${Math.min(plan.occupancyPercent, 100)}%` }} /><strong>{plan.occupancyPercent.toLocaleString("pt-BR")}% de ocupação</strong></div>
      {plan.unloadedCount > 0 ? <p className="plan-history-rejected">{plan.unloadedCount} volume(s) recusado(s)</p> : null}
      {plan.recalculatedFromId && canReadOrigin ? <Link to={`/planning/${plan.recalculatedFromId}`}>Ver plano de origem</Link> : null}
    </div>
    <Link className="btn-secondary" to={destination} aria-label={`Abrir plano ${plan.id.slice(0, 8)}`}>{plan.distributionId ? isCanceled || isIncomplete || historicalVersion ? "Ver histórico da distribuição" : "Abrir distribuição" : "Abrir planejamento"}</Link>
  </li>;
}

function PlanHistoryContent({ failed, result, page, retry, onPage, checker }: {
  readonly failed: boolean;
  readonly checker: boolean;
  readonly result: Page<LoadPlanListItem> | null;
  readonly page: number;
  readonly retry: () => void;
  readonly onPage: (page: number) => void;
}) {
  if (failed) return <div className="plan-builder-feedback">
    <AlertBanner>Não foi possível consultar os planos. Seus registros persistidos continuam no servidor.</AlertBanner>
    <button className="btn-secondary" type="button" onClick={retry}>Tentar novamente</button>
  </div>;
  if (!result) return <output className="entity-state"><span className="spinner" aria-hidden="true" />Carregando planos…</output>;
  return <>
          <p className="entity-form-help">{result.total} plano(s) encontrado(s) · página {result.page}</p>
          {result.items.length === 0 ? <div className="plan-history-empty"><h3>Nenhum plano nesta consulta</h3><p>Altere os filtros ou a página. Um novo planejamento só será salvo após calcular.</p></div>
            : <ul className="plan-history-list">{result.items.map((plan) => <PlanHistoryRow key={plan.id} plan={plan} canReadOrigin={!checker} />)}</ul>}
          {result.items.length === 0 && page > 1 ? <button className="btn-secondary" type="button" onClick={() => onPage(1)}>Voltar à primeira página</button> : null}
          <Pagination page={result.page} totalPages={result.totalPages} onChange={onPage} label="planos" />
        </>;
}

export function PlanHistory({ checker, canReadOperations = false }: { readonly checker: boolean; readonly canReadOperations?: boolean }) {
  const [params, setParams] = useSearchParams();
  const rawPage = Number(params.get("page") ?? 1);
  const page = Number.isSafeInteger(rawPage) && rawPage > 0 ? rawPage : 1;
  const truckId = params.get("truck") || undefined;
  const rawScope = params.get("scope");
  const requestedScope = rawScope === "completed" || rawScope === "all" ? rawScope : "ongoing";
  const operationScope = canReadOperations ? requestedScope : undefined;
  const rawStatus = params.get("status");
  const status = ["CALCULATED", "APPROVED", "REJECTED"].includes(rawStatus ?? "") ? rawStatus as LoadPlanStatus : undefined;
  const sortOrder = params.get("sort") === "asc" ? "asc" : "desc";
  const [result, setResult] = useState<Page<LoadPlanListItem> | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setResult(null);
    setFailed(false);
    listLoadPlans({ page, status, sortOrder, ...(operationScope ? { operationScope } : {}), ...(truckId ? { truckId } : {}) }).then((data) => {
      if (active) setResult(data);
    }).catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [page, status, sortOrder, truckId, checker, attempt, operationScope]);

  function change(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    if (key !== "page") next.delete("page");
    setParams(next);
  }
  return <section className="plan-history" aria-label="Planos existentes">
    {canReadOperations ? <fieldset className="plan-operation-filters" aria-label="Filtrar situação logística"><legend className="sr-only">Filtrar situação logística</legend>
      {([['ongoing', 'Em andamento'], ['completed', 'Concluídos'], ['all', 'Todos (inclui cancelados)']] as const).map(([key, title]) => <button type="button" key={key} aria-pressed={operationScope === key} onClick={() => change("scope", key)}>{title}</button>)}
    </fieldset> : null}
    <div className="plan-history-toolbar">
      <div><h2>Planos de carga</h2><p className="entity-lede">Retome planejamentos persistidos e acompanhe o estado real de cada operação.</p><p className="entity-form-help">Cancelamentos e versões substituídas ficam fora de Em andamento. Para consultar registros históricos, selecione Todos (inclui cancelados).</p></div>
      <div className="plan-history-filters">
        {!checker ? <label>Situação<select value={status ?? ""} onChange={(event) => change("status", event.target.value)}>
          <option value="">Todas as situações</option>
          <option value="CALCULATED">Calculado</option><option value="APPROVED">Aprovado</option><option value="REJECTED">Rejeitado</option>
        </select></label> : <p className="entity-form-help">Você consulta somente planos aprovados.</p>}
        <label>Ordenação<select value={sortOrder} onChange={(event) => change("sort", event.target.value)}>
          <option value="desc">Mais recentes primeiro</option><option value="asc">Mais antigos primeiro</option>
        </select></label>
      </div>
    </div>
    {truckId ? <p className="entity-form-help">Filtro de caminhão ativo. <button type="button" className="btn-secondary" onClick={() => change("truck", "")}>Limpar filtro de caminhão</button></p> : null}
    <PlanHistoryContent checker={checker} failed={failed} result={result} page={page}
      retry={() => setAttempt((value) => value + 1)} onPage={(value) => change("page", String(value))} />
  </section>;
}
