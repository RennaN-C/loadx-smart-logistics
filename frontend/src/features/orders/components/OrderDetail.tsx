import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { AlertBanner } from "../../../components/AlertBanner";
import { AuditTrail } from "../../audit/components/AuditTrail";
import type { Product } from "../../products/types";
import { ApiError } from "../../../types/api";
import { getOrder } from "../api/ordersApi";
import type { Order } from "../types";
import { STATUS_LABELS } from "./orderLabels";
import { mapOrderErrorToMessage } from "./ordersErrorMessages";

interface OrderDetailProps {
  readonly orderId: string;
  readonly onClose: () => void;
  readonly products: readonly Product[];
  readonly canReadHistory: boolean;
}

/** Leitura independente da edição e da página atual da listagem. */
export function OrderDetail({ orderId, onClose, products, canReadHistory }: OrderDetailProps) {
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    let active = true;
    setOrder(null);
    setError(null);
    getOrder(orderId).then((result) => {
      if (active) setOrder(result);
    }).catch((failure: unknown) => {
      if (active) setError(failure instanceof ApiError ? failure : new ApiError("UNKNOWN_ERROR", "Não foi possível consultar o pedido."));
    });
    return () => { active = false; };
  }, [orderId]);

  return (
    <div className="order-detail">
      <Link to={`/orders?order=${encodeURIComponent(orderId)}`}>Link permanente do pedido</Link>
      <p className="entity-form-help">Referência: {orderId}</p>
      {error ? <AlertBanner>{mapOrderErrorToMessage(error)}</AlertBanner> : null}
      {!order && !error ? <p role="status">Carregando pedido…</p> : null}
      {order?.id === orderId ? <>
        <p>Situação: {STATUS_LABELS[order.status]}</p>
        <h3>Endereço de entrega registrado</h3>
        <p>{order.deliveryAddress}</p>
        <h3>Itens do pedido</h3>
        <ul className="order-detail-items">
          {order.items.map((item) => <li key={item.id}>
            Produto {products.find((product) => product.id === item.productId)?.name ?? item.productId} · Quantidade: {item.quantity} · Entrega: {item.deliverySequence}
          </li>)}
        </ul>
        {canReadHistory ? <AuditTrail entityType="ORDER" entityId={order.id} title="Histórico do pedido" /> : null}
      </> : null}
      <button type="button" className="btn-secondary" onClick={onClose}>Voltar à lista de pedidos</button>
    </div>
  );
}
