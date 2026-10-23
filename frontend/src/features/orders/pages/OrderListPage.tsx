import { AttachmentPanel } from "../../attachments/components/AttachmentPanel";
import { useCallback, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { OrderDetail } from "../components/OrderDetail";

import { AlertBanner } from "../../../components/AlertBanner";
import { Modal } from "../../../components/Modal";
import { Pagination } from "../../../components/Pagination";
import { useEditTarget } from "../../../hooks/useEditTarget";
import { MAX_SEARCH_LENGTH, type ListParams } from "../../../services/pagination";
import { useResourceList } from "../../../hooks/useResourceList";
import { useAuth } from "../../auth/hooks/useAuth";
import { canManageLogistics, hasPermission } from "../../auth/permissions";
import { listCustomers } from "../../customers/api/customersApi";
import { listProducts } from "../../products/api/productsApi";
import { getOrder, listOrders } from "../api/ordersApi";
import { OrderCard } from "../components/OrderCard";
import { OrderForm } from "../components/OrderForm";
import { STATUS_LABELS } from "../components/orderLabels";
import { mapOrderErrorToMessage } from "../components/ordersErrorMessages";
import { ORDER_STATUSES, type Order, type OrderStatus } from "../types";
import "./OrderListPage.css";
import { Icon } from "../../../components/Icon";

type StatusFilter = OrderStatus | "all";

const listHistoricalCustomers = (params: ListParams) => listCustomers({ ...params, archiveStatus: "all" });

export function OrderListPage() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const search = (searchParams.get("search") ?? "").slice(0, MAX_SEARCH_LENGTH);
  const requestedStatus = searchParams.get("status");
  const statusFilter: StatusFilter = ORDER_STATUSES.includes(requestedStatus as OrderStatus)
    ? requestedStatus as OrderStatus : "all";
  const filteredLoad = useCallback((params: ListParams) => listOrders({
    ...params,
    search,
    status: statusFilter === "all" ? undefined : statusFilter,
  }), [search, statusFilter]);
  const detailId = searchParams.get("order");
  function closeDetail() {
    const next = new URLSearchParams(searchParams);
    next.delete("order");
    setSearchParams(next);
  }

  function changeStatusFilter(nextStatus: StatusFilter) {
    goToPage(1);
    const next = new URLSearchParams(searchParams);
    if (nextStatus === "all") next.delete("status");
    else next.set("status", nextStatus);
    setSearchParams(next);
  }
  function changeSearch(nextSearch: string) {
    goToPage(1);
    const next = new URLSearchParams(searchParams);
    if (nextSearch) next.set("search", nextSearch);
    else next.delete("search");
    setSearchParams(next);
  }
  function clearFilters() {
    goToPage(1);
    const next = new URLSearchParams(searchParams);
    next.delete("search");
    next.delete("status");
    setSearchParams(next);
  }
  const {
    status,
    items: orders,
    error,
    refetch,
    page,
    total,
    totalPages,
    goToPage,
  } = useResourceList(filteredLoad);
  // O pedido só traz customer_id: a listagem de clientes resolve o nome. Ela é
  // paginada, então nomes fora da primeira página podem não resolver — por isso
  // o fallback explícito no lugar de um espaço vazio.
  const { items: customers } = useResourceList(listHistoricalCustomers, hasPermission(user, "loadx.customers.read"));
  const { items: products } = useResourceList(listProducts, hasPermission(user, "loadx.products.read"));
  const edit = useEditTarget<Order>(getOrder);

  const [attachmentOrderId, setAttachmentOrderId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const canManage = canManageLogistics(user, "orders");
  const canReadCustomers = hasPermission(user, "loadx.customers.read");
  const isFormOpen = isCreating || edit.target !== null;

  const customerNames = useMemo(
    () => new Map(customers.map((customer) => [customer.id, customer.name])),
    [customers],
  );

  function closeForm() {
    setIsCreating(false);
    edit.close();
  }

  async function handleSaved() {
    closeForm();
    await refetch();
  }

  return (
    <div className="entity-page">
      <header className="entity-header">
        <div>
          <h1>Pedidos</h1>
          <p className="entity-lede">O que precisa ser entregue, e em que ordem.</p>
        </div>
        {canManage ? (
          <button type="button" className="btn-primary" onClick={() => setIsCreating(true)}>
            <Icon name="plus" size={16} />
            Novo pedido
          </button>
        ) : null}
      </header>

      <div className="order-status-shortcuts" role="group" aria-label="Acesso rápido aos pedidos">
        <button type="button" aria-pressed={statusFilter === "all"} onClick={() => changeStatusFilter("all")}>Todos os pedidos</button>
        <button type="button" aria-pressed={statusFilter === "DELIVERED"} onClick={() => changeStatusFilter("DELIVERED")}>Pedidos entregues</button>
      </div>

      <div className="entity-toolbar order-filters">
        <label className="order-filter order-filter-search">
          <span>Buscar pedidos</span>
          <input
            type="search"
            placeholder={canReadCustomers ? "Cliente ou referência" : "Referência do pedido"}
            value={search}
            onChange={(event) => changeSearch(event.target.value)}
            maxLength={MAX_SEARCH_LENGTH}
          />
        </label>
        <label className="order-filter">
          <span>Situação</span>
          <select
            value={statusFilter}
            onChange={(event) => changeStatusFilter(event.target.value as StatusFilter)}
          >
            <option value="all">Todas as situações</option>
            {ORDER_STATUSES.map((value) => (
              <option key={value} value={value}>
                {STATUS_LABELS[value]}
              </option>
            ))}
          </select>
        </label>
        {search || statusFilter !== "all" ? <button type="button" className="btn-secondary order-clear-filters" onClick={clearFilters}>Limpar filtros</button> : null}
      </div>

      {status === "success" && total > 0 ? (
        <p className="entity-summary">
          Exibindo {orders.length} de {total} {total === 1 ? "pedido" : "pedidos"}. Busca e filtros consideram toda a lista.
        </p>
      ) : null}

      {status === "loading" ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando pedidos…</span>
        </p>
      ) : null}

      {status === "error" && error ? <div className="order-error"><AlertBanner>{mapOrderErrorToMessage(error)}</AlertBanner><button type="button" className="btn-secondary" onClick={() => void refetch()}>Tentar novamente</button></div> : null}
      {edit.error ? <AlertBanner>{mapOrderErrorToMessage(edit.error)}</AlertBanner> : null}

      {status === "success" && orders.length === 0 ? (
        <p className="entity-state">
          {search.trim() === "" && statusFilter === "all" && total === 0
            ? "Nenhum pedido cadastrado ainda."
            : "Nenhum pedido encontrado com esses filtros."}
        </p>
      ) : null}

      {orders.length > 0 ? (
        <div className="entity-grid">
          {orders.map((order) => (
            <OrderCard
              key={order.id}
              order={order}
              customerName={customerNames.get(order.customerId) ?? (canReadCustomers ? "Cliente não disponível" : "Cliente do pedido")}
              canManage={canManage}
              isOpening={edit.loadingId === order.id}
              onAttachments={setAttachmentOrderId}
              onEdit={(id) => void edit.open(id)}
            />
          ))}
        </div>
      ) : null}

      {status === "success" ? (
        <Pagination page={page} totalPages={totalPages} onChange={goToPage} label="pedidos" />
      ) : null}

      {detailId ? <Modal title="Detalhes do pedido" onClose={closeDetail}><OrderDetail key={detailId} orderId={detailId} products={products} canReadHistory={hasPermission(user, "loadx.audit.read")} onClose={closeDetail} /></Modal> : null}

      {attachmentOrderId ? <Modal title="Anexos do pedido" onClose={() => setAttachmentOrderId(null)}><AttachmentPanel key={attachmentOrderId} resource="orders" resourceId={attachmentOrderId} canManage={canManage} /></Modal> : null}

      {isFormOpen ? (
        <Modal
          title={edit.target ? "Editar pedido" : "Novo pedido"}
          subtitle="Itens e entrega"
          onClose={closeForm}
        >
          <OrderForm
            order={edit.target ?? undefined}
            customers={customers}
            products={products}
            onSaved={handleSaved}
            onCancel={closeForm}
          />
        </Modal>
      ) : null}
    </div>
  );
}
