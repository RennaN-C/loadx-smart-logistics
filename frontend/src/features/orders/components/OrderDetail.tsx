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
      <div className="order-detail-top">
        <div className="order-detail-identification">
          <span className="order-detail-caption">Referência do pedido</span>
          <p className="order-detail-reference">{orderId}</p>
        </div>
        <Link className="order-detail-permalink" to={`/orders?order=${encodeURIComponent(orderId)}`}>
          Link permanente do pedido
        </Link>
      </div>

      {error ? <AlertBanner>{mapOrderErrorToMessage(error)}</AlertBanner> : null}
      {!order && !error ? (
        <p className="entity-state" role="status">
          <span className="spinner" aria-hidden="true" />
          Carregando detalhes do pedido…
        </p>
      ) : null}

      {order?.id === orderId ? (
        <>
          <div className="order-detail-status">
            <span>Situação do pedido</span>
            <strong>{STATUS_LABELS[order.status]}</strong>
          </div>

          <section className="order-detail-section" aria-label="Entrega do pedido">
            <h3>Endereço de entrega registrado</h3>
            <p>{order.deliveryAddress}</p>
          </section>

          <section className="order-detail-section" aria-label="Produtos do pedido">
            <h3>Itens do pedido</h3>
            <ul className="order-detail-items">
              {order.items.map((item) => (
                <li key={item.id}>
                  <strong className="order-detail-item-name">
                    {products.find((product) => product.id === item.productId)?.name ?? item.productId}
                  </strong>
                  <span>Quantidade: {item.quantity}</span>
                  <span>Entrega: {item.deliverySequence}</span>
                </li>
              ))}
            </ul>
          </section>

          {canReadHistory ? <AuditTrail entityType="ORDER" entityId={order.id} title="Histórico do pedido" /> : null}
        </>
      ) : null}

      <div className="order-detail-actions">
        <button type="button" className="btn-secondary" onClick={onClose}>Voltar à lista de pedidos</button>
      </div>
    </div>
  );
}
