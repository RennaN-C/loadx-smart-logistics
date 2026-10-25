import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AlertBanner } from "../../../components/AlertBanner";
import { Pagination } from "../../../components/Pagination";
import type { Page } from "../../../types/api";
import { listLoadPlans } from "../api/loadPlansApi";
import type { LoadPlanListItem } from "../types";
import { PlanOperationSummary } from "./PlanOperationSummary";
import "../../../components/RegistryTable.css";

export function PlanExecution() {
  const [params, setParams] = useSearchParams();
  const requestedPage = Number(params.get("page") ?? 1);
  const page = Number.isSafeInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1;
  const scope = params.get("scope") === "completed" ? "completed" : params.get("scope") === "all" ? "all" : "ongoing";
  const [result, setResult] = useState<Page<LoadPlanListItem> | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setResult(null); setFailed(false);
    listLoadPlans({ page, pageSize: 20, status: "APPROVED", operationScope: scope }).then((data) => {
      if (active) setResult(data);
    }).catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [page, scope, attempt]);
  function change(key: string, value: string) {
    const next = new URLSearchParams(params);
    next.set("tab", "execution"); next.set(key, value);
    if (key !== "page") next.delete("page");
    setParams(next);
  }
  return <section className="plan-execution" aria-labelledby="plan-execution-title">
    <div className="entity-header"><div><h2 id="plan-execution-title">Execução dos planos</h2><p className="entity-lede">Acompanhe a operação dos planos aprovados, do carregamento à conclusão das entregas.</p></div></div>
    <div className="entity-toolbar"><label className="registry-filter-field">Situação operacional<select aria-label="Situação operacional" value={scope} onChange={(event) => change("scope", event.target.value)}><option value="ongoing">Em acompanhamento</option><option value="completed">Concluídas</option><option value="all">Todas as operações</option></select></label></div>
    {failed ? <div className="plan-builder-feedback"><AlertBanner>Não foi possível consultar a execução dos planos.</AlertBanner><button type="button" className="btn-secondary" onClick={() => setAttempt((value) => value + 1)}>Tentar novamente</button></div> : !result ? <p className="entity-state" role="status"><span className="spinner" aria-hidden="true" />Carregando execução…</p> : <>
      <p className="entity-summary">{result.total} plano(s) aprovado(s) nesta consulta.</p>
      {result.items.length === 0 ? <p className="entity-state">Nenhuma operação encontrada com esse filtro.</p> : <div className="registry-table-wrap"><table className="registry-table"><caption className="sr-only">Execução dos planos aprovados</caption>
        <thead><tr><th scope="col">Plano e veículo</th><th scope="col">Carga</th><th scope="col">Ocupação</th><th scope="col">Execução</th><th scope="col">Ações</th></tr></thead>
        <tbody>{result.items.map((plan) => <tr key={plan.id}>
          <td data-label="Plano e veículo"><strong>{plan.id.slice(0, 8).toUpperCase()}</strong><small>{plan.truckPlate} · {plan.truckModel}</small></td>
          <td data-label="Carga">{plan.loadedCount} volumes<small>{plan.totalWeightKg.toLocaleString("pt-BR")} kg</small></td>
          <td data-label="Ocupação">{plan.occupancyPercent.toLocaleString("pt-BR")}%</td>
          <td data-label="Execução">{plan.operation ? <PlanOperationSummary operation={plan.operation} showLinks={false} /> : "Situação não disponível"}</td>
          <td data-label="Ações"><div className="plan-operation-links"><Link to={plan.distributionId ? `/planning/distributions/${plan.distributionId}` : `/planning/${plan.id}`}>Abrir planejamento</Link>
            {plan.operation?.loading_session_id ? <Link to={`/loading/${plan.operation.loading_session_id}`}>Conferir carregamento</Link> : null}
            {plan.operation?.trip_id ? <Link to={`/trips/${plan.operation.trip_id}`}>Abrir viagem</Link> : null}
          </div></td>
        </tr>)}</tbody></table></div>}
      <Pagination page={result.page} totalPages={result.totalPages} onChange={(value) => change("page", String(value))} label="execução dos planos" />
    </>}
  </section>;
}
