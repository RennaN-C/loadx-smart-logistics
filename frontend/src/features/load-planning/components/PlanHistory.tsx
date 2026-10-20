import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { Pagination } from "../../../components/Pagination";
import { StatusPill } from "../../../components/StatusPill";
import type { Page } from "../../../types/api";
import { listLoadPlans } from "../api/loadPlansApi";
import type { LoadPlanListItem, LoadPlanStatus } from "../types";
import { PLAN_STATUS_LABELS, planStatusTone } from "./loadPlanLabels";

const date = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

function PlanHistoryRow({ plan, canReadOrigin }: { readonly plan: LoadPlanListItem; readonly canReadOrigin: boolean }) {
  const destination = plan.distributionId ? `/planning/distributions/${plan.distributionId}` : `/planning/${plan.id}`;
  return <li className="plan-history-row">
    <div className="plan-history-identification">
      <Link className="plan-history-plate" to={`/planning?truck=${plan.truckId}`} aria-label={`Filtrar planos do caminhão ${plan.truckPlate}`}>{plan.truckPlate}</Link>
      <h3><Link to={destination}>Plano {plan.id.slice(0, 8)}</Link></h3>
      <p>{plan.truckModel}</p>
      {plan.distributionId ? <p>Parte da distribuição {plan.distributionId.slice(0, 8)}</p> : null}
      <time dateTime={plan.createdAt}>{date.format(new Date(plan.createdAt))}</time>
    </div>
    <div className="plan-history-summary">
      <StatusPill tone={planStatusTone(plan.status)}>{PLAN_STATUS_LABELS[plan.status]}</StatusPill>
      <p>{plan.orderCount} pedido(s) · {plan.loadedCount} volumes aceitos · {plan.unloadedCount} recusados</p>
      <p>{plan.occupancyPercent.toLocaleString("pt-BR")}% de ocupação · {plan.totalWeightKg.toLocaleString("pt-BR")} kg</p>
      {plan.recalculatedFromId && canReadOrigin ? <Link to={`/planning/${plan.recalculatedFromId}`}>Ver plano de origem</Link> : null}
    </div>
    <Link className="btn-secondary" to={destination} aria-label={`Abrir plano ${plan.id.slice(0, 8)}`}>{plan.distributionId ? "Abrir distribuição" : "Abrir planejamento"}</Link>
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

export function PlanHistory({ checker }: { readonly checker: boolean }) {
  const [params, setParams] = useSearchParams();
  const rawPage = Number(params.get("page") ?? 1);
  const page = Number.isSafeInteger(rawPage) && rawPage > 0 ? rawPage : 1;
  const truckId = params.get("truck") || undefined;
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
    listLoadPlans({ page, status, sortOrder, ...(truckId ? { truckId } : {}) }).then((data) => {
      if (active) setResult(data);
    }).catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [page, status, sortOrder, truckId, checker, attempt]);

  function change(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    if (key !== "page") next.delete("page");
    setParams(next);
  }
  return <section className="plan-history" aria-label="Planos existentes">
    <div className="plan-history-toolbar">
      <div><h2>Retome uma carga</h2><p className="entity-lede">Planos salvos no servidor, disponíveis após sair da tela ou entrar novamente.</p></div>
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
