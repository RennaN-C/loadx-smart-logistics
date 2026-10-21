import { useCallback, useState } from "react";
import { Link } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { Pagination } from "../../../components/Pagination";
import { useResourceList } from "../../../hooks/useResourceList";
import type { ListParams } from "../../../services/pagination";
import { listDeliveries } from "../api/operationalListsApi";
import "./TripListPage.css";

export function DeliveryListPage() {
  const [filter, setFilter] = useState("");
  const load = useCallback(
    (params: ListParams) => listDeliveries({ ...params, status: filter || undefined }),
    [filter],
  );
  const { items, status, error, refetch, page, total, totalPages, goToPage } = useResourceList(load);
  return <div className="entity-page">
    <header className="entity-header"><div><h1>Entregas</h1><p className="entity-lede">Paradas reais das viagens, incluindo partes de pedidos multi-caminhão.</p></div></header>
    <label htmlFor="delivery-list-status">Filtrar situação</label>
    <select id="delivery-list-status" value={filter} onChange={(event) => {
      setFilter(event.target.value);
      goToPage(1);
    }}>
      <option value="">Todas</option>
      <option value="PENDING">Pendente</option>
      <option value="IN_DELIVERY">Em entrega</option>
      <option value="DELIVERED">Entregue</option>
    </select>
    {status === "loading" && <p role="status">Carregando entregas...</p>}
    {status === "error" && <><AlertBanner>{error?.message ?? "Não foi possível consultar as entregas."}</AlertBanner><button className="btn-secondary" type="button" onClick={() => void refetch()}>Tentar novamente</button></>}
    {status === "success" && items.length === 0 && <p className="entity-state">Nenhuma entrega encontrada.</p>}
    {items.length > 0 && <div className="trip-list-scroll" role="region" aria-label="Entregas" tabIndex={0}><table className="trip-list">
      <thead><tr><th scope="col">Situação</th><th scope="col">Sequência</th><th scope="col">Concluída</th><th scope="col">Ação</th></tr></thead>
      <tbody>{items.map((item) => <tr key={item.id}><td>{item.status}</td><td>{item.sequence}</td><td>{item.deliveredAt ? new Date(item.deliveredAt).toLocaleString("pt-BR") : "—"}</td><td><Link className="btn-link" to={`/trips/${item.tripId}`}>Abrir viagem</Link></td></tr>)}</tbody>
    </table></div>}
    {status === "success" && total > 0 && <Pagination page={page} totalPages={totalPages} onChange={goToPage} label="entregas" />}
  </div>;
}
