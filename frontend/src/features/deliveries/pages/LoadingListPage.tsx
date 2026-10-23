import { useCallback, useState } from "react";
import { Link } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { FormField } from "../../../components/FormField";
import { Pagination } from "../../../components/Pagination";
import { StatusPill } from "../../../components/StatusPill";
import { useResourceList } from "../../../hooks/useResourceList";
import type { ListParams } from "../../../services/pagination";
import { LOADING_STATUS_LABELS, loadingStatusTone } from "../../loading-operation/components/loadingLabels";
import { mapLoadingErrorToMessage } from "../../loading-operation/components/loadingErrorMessages";
import { listLoadingSessions } from "../api/operationalListsApi";
import "./TripListPage.css";

const dateTime = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

export function LoadingListPage() {
  const [filter, setFilter] = useState("");
  const load = useCallback(
    (params: ListParams) => listLoadingSessions({ ...params, status: filter || undefined }),
    [filter],
  );
  const { items, status, error, refetch, page, total, totalPages, goToPage } = useResourceList(load);

  return <div className="entity-page operational-list">
    <header className="entity-header">
      <div><h1>Carregamentos</h1><p className="entity-lede">Encontre um carregamento e acompanhe a conferência dos volumes.</p></div>
    </header>
    <div className="entity-toolbar operational-list-filters">
      <FormField id="loading-list-status" label="Situação do carregamento">
        <select id="loading-list-status" value={filter} onChange={(event) => {
          setFilter(event.target.value);
          goToPage(1);
        }}>
          <option value="">Todas as situações</option>
          {Object.entries(LOADING_STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </FormField>
      {status === "success" && <p className="operational-list-count" role="status">{total} {total === 1 ? "carregamento encontrado" : "carregamentos encontrados"}</p>}
    </div>
    {status === "loading" && <p className="entity-state" role="status"><span className="spinner" aria-hidden="true" />Carregando carregamentos…</p>}
    {status === "error" && <div className="operational-list-feedback"><AlertBanner>{error ? mapLoadingErrorToMessage(error) : "Não foi possível consultar os carregamentos."}</AlertBanner><button className="btn-secondary" type="button" onClick={() => void refetch()}>Tentar novamente</button></div>}
    {status === "success" && items.length === 0 && <p className="entity-state">{filter ? "Nenhum carregamento nesta situação. Selecione outra situação para continuar." : "Nenhum carregamento encontrado. Os carregamentos ficam disponíveis após a aprovação de um plano."}</p>}
    {items.length > 0 && <>
      <p className="operational-list-scroll-hint" id="loading-scroll-hint">Em telas menores, deslize a tabela para ver todas as informações.</p>
      <div className="trip-list-scroll" role="region" aria-label="Carregamentos" aria-describedby="loading-scroll-hint" aria-busy={status === "loading"} tabIndex={0}>
        <table className="trip-list">
          <caption className="sr-only">Carregamentos e acesso à conferência</caption>
          <thead><tr><th scope="col">Carregamento</th><th scope="col">Situação</th><th scope="col">Iniciado em</th><th scope="col">Concluído em</th><th scope="col">Ação</th></tr></thead>
          <tbody>{items.map((item) => <tr key={item.id}>
            <th scope="row"><span className="operational-list-reference">#{item.id.slice(0, 8)}</span><span className="operational-list-context">Plano #{item.loadPlanId.slice(0, 8)}</span></th>
            <td><StatusPill tone={loadingStatusTone(item.status)}>{LOADING_STATUS_LABELS[item.status]}</StatusPill></td>
            <td className="trip-list-date">{item.startedAt ? dateTime.format(new Date(item.startedAt)) : "Não iniciado"}</td>
            <td className="trip-list-date">{item.finishedAt ? dateTime.format(new Date(item.finishedAt)) : "—"}</td>
            <td><Link className="btn-link" to={`/loading/${item.id}`} aria-label={`Abrir carregamento #${item.id.slice(0, 8)}`}>Abrir conferência</Link></td>
          </tr>)}</tbody>
        </table>
      </div>
    </>}
    {status === "success" && total > 0 && <Pagination page={page} totalPages={totalPages} onChange={goToPage} label="carregamentos" />}
  </div>;
}
