import { useMemo, useState } from "react";

import { AlertBanner } from "../../../components/AlertBanner";
import { Modal } from "../../../components/Modal";
import { useResourceList } from "../../../hooks/useResourceList";
import { useAuth } from "../../auth/hooks/useAuth";
import { listCustomers } from "../../customers/api/customersApi";
import { listProducts } from "../../products/api/productsApi";
import { listOrders } from "../api/ordersApi";
import { OrderCard } from "../components/OrderCard";
import { OrderForm } from "../components/OrderForm";
import { STATUS_LABELS } from "../components/orderLabels";
import { mapOrderErrorToMessage } from "../components/ordersErrorMessages";
import { ORDER_STATUSES, type Order, type OrderStatus } from "../types";
import "./OrderListPage.css";

type StatusFilter = OrderStatus | "all";

export function OrderListPage() {
  const { user } = useAuth();
  const { status, items: orders, error, refetch } = useResourceList(listOrders);
  // O pedido só traz customer_id e product_id, e não existe endpoint de busca:
  // as duas listas são carregadas inteiras para resolver os nomes no cliente.
  const { items: customers } = useResourceList(listCustomers);
  const { items: products } = useResourceList(listProducts);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [editingOrder, setEditingOrder] = useState<Order | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const canManage = user?.role === "LOGISTICS_MANAGER";
  const isFormOpen = isCreating || editingOrder !== null;

  const customerNames = useMemo(
    () => new Map(customers.map((customer) => [customer.id, customer.name])),
    [customers],
  );
  const productLabels = useMemo(
    () => new Map(products.map((product) => [product.id, `${product.code} — ${product.name}`])),
    [products],
  );

  const nameOf = (customerId: string) => customerNames.get(customerId) ?? "Cliente não encontrado";
  const productLabelOf = (productId: string) => productLabels.get(productId) ?? "Produto não encontrado";

  const visibleOrders = useMemo(() => {
    const term = search.trim().toLowerCase();

    return orders.filter((order) => {
      const matchesTerm =
        term === "" ||
        nameOf(order.customerId).toLowerCase().includes(term) ||
        order.deliveryAddress.toLowerCase().includes(term);
      const matchesStatus = statusFilter === "all" || order.status === statusFilter;

      return matchesTerm && matchesStatus;
    });
    // nameOf depende de customerNames, que já está nas dependências
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orders, search, statusFilter, customerNames]);

  function closeForm() {
    setIsCreating(false);
    setEditingOrder(null);
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
          aria-label="Buscar por cliente ou endereço"
          placeholder="Buscar por cliente ou endereço"
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

      {status === "loading" ? (
        <p className="entity-state">
          <span className="spinner" aria-hidden="true" />
          <span>Carregando pedidos…</span>
        </p>
      ) : null}

      {status === "error" && error ? <AlertBanner>{mapOrderErrorToMessage(error)}</AlertBanner> : null}

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
              customerName={nameOf(order.customerId)}
              productLabelOf={productLabelOf}
              canManage={canManage}
              onEdit={setEditingOrder}
            />
          ))}
        </div>
      ) : null}

      {isFormOpen ? (
        <Modal
          title={editingOrder ? "Editar pedido" : "Novo pedido"}
          subtitle="Itens e entrega"
          onClose={closeForm}
        >
          <OrderForm
            order={editingOrder ?? undefined}
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
