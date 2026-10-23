import { useCallback, useState } from "react";
import { Link } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { Pagination } from "../../../components/Pagination";
import { useResourceList } from "../../../hooks/useResourceList";
import type { ListParams } from "../../../services/pagination";
import { listLoadingSessions } from "../api/operationalListsApi";
import "./TripListPage.css";

export function LoadingListPage() {
  const [filter, setFilter] = useState("");
  const load = useCallback(
    (params: ListParams) => listLoadingSessions({ ...params, status: filter || undefined }),
    [filter],
  );
  const { items, status, error, refetch, page, total, totalPages, goToPage } = useResourceList(load);
  return <div className="entity-page">
    <header className="entity-header"><div><h1>Carregamentos</h1><p className="entity-lede">Sessões reais de carregamento, com acesso direto à conferência.</p></div></header>
    <label htmlFor="loading-list-status">Filtrar situação</label>
    <select id="loading-list-status" value={filter} onChange={(event) => {
      setFilter(event.target.value);
      goToPage(1);
    }}>
      <option value="">Todas</option>
      <option value="PENDING">Pendente</option>
      <option value="IN_PROGRESS">Em andamento</option>
      <option value="FINISHED">Finalizado</option>
    </select>
    {status === "loading" && <p role="status">Carregando sessões...</p>}
    {status === "error" && <><AlertBanner>{error?.message ?? "Não foi possível consultar os carregamentos."}</AlertBanner><button className="btn-secondary" type="button" onClick={() => void refetch()}>Tentar novamente</button></>}
    {status === "success" && items.length === 0 && <p className="entity-state">Nenhum carregamento encontrado.</p>}
    {items.length > 0 && <div className="trip-list-scroll" role="region" aria-label="Carregamentos" tabIndex={0}><table className="trip-list">
      <thead><tr><th scope="col">Situação</th><th scope="col">Início</th><th scope="col">Fim</th><th scope="col">Ação</th></tr></thead>
      <tbody>{items.map((item) => <tr key={item.id}><td>{item.status}</td><td>{item.startedAt ? new Date(item.startedAt).toLocaleString("pt-BR") : "—"}</td><td>{item.finishedAt ? new Date(item.finishedAt).toLocaleString("pt-BR") : "—"}</td><td><Link className="btn-link" to={`/loading/${item.id}`}>Abrir</Link></td></tr>)}</tbody>
    </table></div>}
    {status === "success" && total > 0 && <Pagination page={page} totalPages={totalPages} onChange={goToPage} label="carregamentos" />}
  </div>;
}
