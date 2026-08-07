import { useMemo, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { Modal } from "../../../components/Modal";
import { Pagination } from "../../../components/Pagination";
import { useEditTarget } from "../../../hooks/useEditTarget";
import { useResourceList } from "../../../hooks/useResourceList";
import { useAuth } from "../../auth/hooks/useAuth";
import { listCustomers } from "../../customers/api/customersApi";
import { listProducts } from "../../products/api/productsApi";
import { getOrder, listOrders } from "../api/ordersApi";
import { OrderCard } from "../components/OrderCard";
import { OrderForm } from "../components/OrderForm";
import { STATUS_LABELS } from "../components/orderLabels";
import { mapOrderErrorToMessage } from "../components/ordersErrorMessages";
import { ORDER_STATUSES, type Order, type OrderStatus } from "../types";
import "./OrderListPage.css";

type StatusFilter = OrderStatus | "all";

export function OrderListPage() {
  const { user } = useAuth();
  const {
    status,
    items: orders,
    error,
    refetch,
    page,
    total,
    totalPages,
    goToPage,
  } = useResourceList(listOrders);
  // O pedido só traz customer_id: a listagem de clientes resolve o nome. Ela é
  // paginada, então nomes fora da primeira página podem não resolver — por isso
  // o fallback explícito no lugar de um espaço vazio.
  const { items: customers } = useResourceList(listCustomers);
  const { items: products } = useResourceList(listProducts);
  const edit = useEditTarget<Order>(getOrder);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [isCreating, setIsCreating] = useState(false);

  const canManage = user?.role === "LOGISTICS_MANAGER";
  const isFormOpen = isCreating || edit.target !== null;

  const customerNames = useMemo(
    () => new Map(customers.map((customer) => [customer.id, customer.name])),
    [customers],
  );

  const visibleOrders = useMemo(() => {
    const term = search.trim().toLowerCase();

    return orders.filter((order) => {
      const name = customerNames.get(order.customerId) ?? "";
      const matchesTerm = term === "" || name.toLowerCase().includes(term);
      const matchesStatus = statusFilter === "all" || order.status === statusFilter;

      return matchesTerm && matchesStatus;
    });
  }, [orders, search, statusFilter, customerNames]);

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
            + Novo pedido
          </button>
        ) : null}
      </header>

      <div className="entity-toolbar">
        <input
          type="search"
          aria-label="Buscar por cliente"
          placeholder="Buscar por cliente"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <select
          aria-label="Filtrar por situação"
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
        >
          <option value="all">Todas as situações</option>
          {ORDER_STATUSES.map((value) => (
            <option key={value} value={value}>
              {STATUS_LABELS[value]}
            </option>
          ))}
        </select>
      </div>

      {status === "success" && total > 0 ? (
        <p className="entity-summary">
          Exibindo {orders.length} de {total} pedidos. Busca e filtro atuam nesta página.
        </p>
      ) : null}

      {status === "loading" ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando pedidos…</span>
        </p>
      ) : null}

      {status === "error" && error ? <AlertBanner>{mapOrderErrorToMessage(error)}</AlertBanner> : null}
      {edit.error ? <AlertBanner>{mapOrderErrorToMessage(edit.error)}</AlertBanner> : null}

      {status === "success" && visibleOrders.length === 0 ? (
        <p className="entity-state">
          {orders.length === 0
            ? "Nenhum pedido cadastrado ainda."
            : "Nenhum pedido encontrado com esses filtros."}
        </p>
      ) : null}

      {visibleOrders.length > 0 ? (
        <div className="entity-grid">
          {visibleOrders.map((order) => (
            <OrderCard
              key={order.id}
              order={order}
              customerName={customerNames.get(order.customerId) ?? "Cliente não encontrado"}
              canManage={canManage}
              isOpening={edit.loadingId === order.id}
              onEdit={(id) => void edit.open(id)}
            />
          ))}
        </div>
      ) : null}

      {status === "success" ? (
        <Pagination page={page} totalPages={totalPages} onChange={goToPage} label="pedidos" />
      ) : null}

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
