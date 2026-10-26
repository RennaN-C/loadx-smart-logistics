import { useCallback, useState } from "react";
import { Link } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { FormField } from "../../../components/FormField";
import { Pagination } from "../../../components/Pagination";
import { StatusPill } from "../../../components/StatusPill";
import { useResourceList } from "../../../hooks/useResourceList";
import type { ListParams } from "../../../services/pagination";
import { listDeliveries } from "../api/operationalListsApi";
import { DELIVERY_STATUS_LABELS, deliveryStatusTone } from "../components/tripLabels";
import { mapTripErrorToMessage } from "../components/tripsErrorMessages";
import "./TripListPage.css";

const dateTime = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

export function DeliveryListPage() {
  const [filter, setFilter] = useState("");
  const load = useCallback(
    (params: ListParams) => listDeliveries({ ...params, status: filter || undefined }),
    [filter],
  );
  const { items, status, error, refetch, page, total, totalPages, goToPage } = useResourceList(load);

  return <div className="entity-page operational-list">
    <header className="entity-header">
      <div><h1>Entregas</h1><p className="entity-lede">Acompanhe as entregas e abra a viagem para consultar os detalhes de cada parada.</p></div>
    </header>
    <div className="entity-toolbar operational-list-filters">
      <FormField id="delivery-list-status" label="Situação da entrega">
        <select id="delivery-list-status" value={filter} onChange={(event) => {
          setFilter(event.target.value);
          goToPage(1);
        }}>
          <option value="">Todas as situações</option>
          {Object.entries(DELIVERY_STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </FormField>
      {status === "success" && <p className="operational-list-count" role="status">{total} {total === 1 ? "entrega encontrada" : "entregas encontradas"}</p>}
    </div>
    {status === "loading" && <p className="entity-state" role="status"><span className="spinner" aria-hidden="true" />Carregando entregas…</p>}
    {status === "error" && <div className="operational-list-feedback"><AlertBanner>{error ? mapTripErrorToMessage(error) : "Não foi possível consultar as entregas."}</AlertBanner><button className="btn-secondary" type="button" onClick={() => void refetch()}>Tentar novamente</button></div>}
    {status === "success" && items.length === 0 && <p className="entity-state">{filter ? "Nenhuma entrega nesta situação. Selecione outra situação para continuar." : "Nenhuma entrega encontrada. As entregas ficam disponíveis nas viagens cadastradas."}</p>}
    {items.length > 0 && <>
      <p className="operational-list-scroll-hint" id="delivery-scroll-hint">Em telas menores, deslize a tabela para ver todas as informações.</p>
      <div className="trip-list-scroll" role="region" aria-label="Entregas" aria-describedby="delivery-scroll-hint" aria-busy={status === "loading"} tabIndex={0}>
        <table className="trip-list">
          <caption className="sr-only">Entregas e acesso à viagem de origem</caption>
          <thead><tr><th scope="col">Entrega</th><th scope="col">Situação</th><th scope="col">Parada</th><th scope="col">Entregue em</th><th scope="col">Ação</th></tr></thead>
          <tbody>{items.map((item) => <tr key={item.id}>
            <th scope="row"><span className="operational-list-reference">#{item.id.slice(0, 8)}</span><span className="operational-list-context">Pedido #{item.orderId.slice(0, 8)}</span></th>
            <td><StatusPill tone={deliveryStatusTone(item.status)}>{DELIVERY_STATUS_LABELS[item.status]}</StatusPill></td>
            <td className="trip-list-count">{item.sequence}</td>
            <td className="trip-list-date">{item.deliveredAt ? dateTime.format(new Date(item.deliveredAt)) : "—"}</td>
            <td><Link className="btn-link" to={`/trips/${item.tripId}`} aria-label={`Abrir viagem da entrega #${item.id.slice(0, 8)}`}>Abrir viagem</Link></td>
          </tr>)}</tbody>
        </table>
      </div>
    </>}
    {status === "success" && total > 0 && <Pagination page={page} totalPages={totalPages} onChange={goToPage} label="entregas" />}
  </div>;
}
